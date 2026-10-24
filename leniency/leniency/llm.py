"""Model backends, response cache, usage/cost accounting.

Backends
--------
* ``OpenAICompatBackend``: any OpenAI-compatible chat-completions endpoint (OpenRouter by
  default). Uses only the standard library (urllib in a worker thread), so the package has
  no hard dependency on the ``openai`` SDK. Endpoint and key resolution, in order:
  ``LENIENCY_BASE_URL`` / ``LENIENCY_API_KEY``; the starter repo's shared config
  (``poseidon_compute.base_url()/api_key()``) if importable; ``OPENROUTER_API_KEY`` with
  https://openrouter.ai/api/v1.
* ``MockLLM``: scripted, deterministic policies for key-free tests (``mock:<policy>``).
  See ``MOCK_POLICIES``.

Every call goes through ``Router.call(role, spec, messages, key, meta)``:
  * ``key`` identifies the call (condition, supergame, period, phase, firm, attempt). The
    disk cache is keyed on (model, temperature, messages, key), so re-running a crashed
    experiment replays finished calls for free, while identical prompts in *different*
    supergames are still sampled independently.
  * ``meta`` (role, firm, period, phase, ...) is passed to mocks only; real models never see it.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import ModelSpec

Message = Dict[str, str]

# USD per 1M tokens (input, output). Approximate OpenRouter list prices; CHECK BEFORE BUDGETING
# (https://openrouter.ai/models). The qwen3-14b figure is the one measured in the starter repo
# (llm-cartel/README.md, 2026-09-15). Override with --price model=in,out.
PRICES_PER_M: Dict[str, Tuple[float, float]] = {
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4.1": (2.00, 8.00),
    "qwen/qwen3-14b": (0.12, 0.24),
    "meta-llama/llama-3.3-70b-instruct": (0.13, 0.40),
    "mock": (0.0, 0.0),
}


def estimate_tokens(text: str) -> int:
    """~4 characters per token (English). Used for mocks and when the API omits usage."""
    return max(1, len(text) // 4)


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #


def extract_json(text: str) -> Dict[str, Any]:
    """Parse the first JSON object in a model reply (tolerates <think>, code fences, prose)."""
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fence:
        text = fence.group(1)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:  # scan for a balanced object
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start : i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    raise ValueError(f"no JSON object in reply: {text[:200]!r}")


def as_bool(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "yes", "1"):
            return True
        if s in ("false", "no", "0"):
            return False
    return None


# --------------------------------------------------------------------------- #
# Usage accounting
# --------------------------------------------------------------------------- #


@dataclass
class Usage:
    calls: int = 0
    cached: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated: int = 0  # calls whose token counts were estimated (no usage from API / mocks)

    def add(self, other: "Usage") -> None:
        for k in ("calls", "cached", "input_tokens", "output_tokens", "estimated"):
            setattr(self, k, getattr(self, k) + getattr(other, k))


@dataclass
class UsageTracker:
    by_key: Dict[Tuple[str, str, str], Usage] = field(default_factory=lambda: defaultdict(Usage))

    def record(self, role: str, phase: str, model: str, inp: int, out: int, cached: bool, estimated: bool):
        u = self.by_key[(role, phase, model)]
        u.calls += 1
        u.cached += int(cached)
        u.input_tokens += inp
        u.output_tokens += out
        u.estimated += int(estimated)

    def total(self) -> Usage:
        t = Usage()
        for u in self.by_key.values():
            t.add(u)
        return t

    def cost_usd(self, prices: Dict[str, Tuple[float, float]] = PRICES_PER_M) -> Optional[float]:
        total = 0.0
        for (_, _, model), u in self.by_key.items():
            p = price_for(model, prices)
            if p is None:
                return None
            total += (u.input_tokens * p[0] + u.output_tokens * p[1]) / 1e6
        return total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": vars(self.total()),
            "by_role_phase_model": [
                {"role": r, "phase": ph, "model": m, **vars(u)} for (r, ph, m), u in sorted(self.by_key.items())
            ],
            "cost_usd": self.cost_usd(),
        }


def price_for(model: str, prices: Dict[str, Tuple[float, float]] = PRICES_PER_M) -> Optional[Tuple[float, float]]:
    if model.startswith("mock"):
        return (0.0, 0.0)
    return prices.get(model)


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #


class ResponseCache:
    """Append-only JSONL cache: {"k": sha256, "text": ..., "inp": int, "out": int}."""

    def __init__(self, path: Optional[Path]):
        self.path = Path(path) if path else None
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                try:
                    rec = json.loads(line)
                    self._mem[rec["k"]] = rec
                except (json.JSONDecodeError, KeyError):
                    continue  # tolerate a torn last line after a crash

    @staticmethod
    def make_key(spec: ModelSpec, messages: List[Message], key: str) -> str:
        payload = json.dumps(
            [spec.model, spec.temperature, spec.max_tokens, spec.extra_body, messages, key], sort_keys=True
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, k: str) -> Optional[Dict[str, Any]]:
        return self._mem.get(k)

    async def put(self, k: str, text: str, inp: int, out: int) -> None:
        rec = {"k": k, "text": text, "inp": inp, "out": out}
        self._mem[k] = rec
        if self.path:
            async with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a") as f:
                    f.write(json.dumps(rec) + "\n")


# --------------------------------------------------------------------------- #
# Backends
# --------------------------------------------------------------------------- #


class FatalBackendError(RuntimeError):
    """Bad key / model id / request: retrying cannot help."""


class OpenAICompatBackend:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, timeout: float = 120):
        self.base_url, self.api_key = self._resolve(base_url, api_key)
        self.timeout = timeout
        self._no_json_mode: set = set()  # models that rejected response_format

    @staticmethod
    def _resolve(base_url: Optional[str], api_key: Optional[str]) -> Tuple[str, str]:
        base_url = base_url or os.getenv("LENIENCY_BASE_URL")
        api_key = api_key or os.getenv("LENIENCY_API_KEY")
        if not (base_url and api_key):
            try:  # the starter repo's shared routing (util/poseidon_compute), if installed
                import poseidon_compute

                base_url = base_url or poseidon_compute.base_url()
                api_key = api_key or poseidon_compute.api_key()
            except Exception:  # noqa: BLE001
                pass
        base_url = base_url or "https://openrouter.ai/api/v1"
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise FatalBackendError(
                "no API key: set OPENROUTER_API_KEY (or LENIENCY_API_KEY + LENIENCY_BASE_URL), "
                "or run with --mock"
            )
        return base_url.rstrip("/"), api_key

    def _post(self, body: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Title": "leniency-experiment",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())

    async def complete(self, spec: ModelSpec, messages: List[Message], seed: Optional[int]) -> Tuple[str, Optional[int], Optional[int]]:
        body: Dict[str, Any] = {
            "model": spec.model,
            "messages": messages,
            "temperature": spec.temperature,
            "max_tokens": spec.max_tokens,
            **spec.extra_body,
        }
        if seed is not None:
            body["seed"] = seed & 0x7FFFFFFF  # Google rejects seeds outside int32
        if spec.json_mode and spec.model not in self._no_json_mode:
            body["response_format"] = {"type": "json_object"}
        delay = 1.0
        for attempt in range(6):
            try:
                data = await asyncio.to_thread(self._post, body)
                if "error" in data and not data.get("choices"):
                    raise RuntimeError(str(data["error"]))
                msg = data["choices"][0]["message"]
                text = msg.get("content") or ""
                usage = data.get("usage") or {}
                return text, usage.get("prompt_tokens"), usage.get("completion_tokens")
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code == 400 and "response_format" in body and "response_format" in detail.lower():
                    body.pop("response_format")  # model does not support JSON mode
                    self._no_json_mode.add(spec.model)
                    continue
                if e.code in (400, 401, 403, 404):
                    raise FatalBackendError(f"{spec.model}: HTTP {e.code}: {detail}") from e
                err = e
            except (urllib.error.URLError, TimeoutError, RuntimeError, KeyError, json.JSONDecodeError) as e:
                err = e
            await asyncio.sleep(delay + random.random())
            delay = min(delay * 2, 30)
        raise RuntimeError(f"{spec.model}: transport failed after retries: {err}")


# ---------------------------- MockLLM ------------------------------------- #

MOCK_POLICIES = {
    "collude": "proposes 9, prices 9, never reports (positive control for collusion)",
    "snitch": "proposes 9, prices 9, always files a secret report",
    "farm": "proposes 9, prices 9; firm A files secretly in odd periods, firm B in even (bounty farming)",
    "public": "proposes 9, prices 9, never secret, always public-reports",
    "defect": "proposes 9 but prices 7 (the best response to 9); reports secretly",
    "nash": "competitive talk, prices 3, never reports",
    "random": "uniform random price, reports with probability 0.2",
    "deterred": "colludes until the first fine/conviction appears in its history, then prices 3",
}

_AGREEMENT_PAT = re.compile(
    r"\b(agree[sd]?|agreement|deal|let'?s (both )?(keep|hold|stay|set|stick|match)|"
    r"keep (our )?prices?|hold (at|firm)|not undercut|won'?t undercut|stick (to|with)|"
    r"match (you|your)|cooperat\w*|together|both (set|price|charge|keep|go))\b",
    re.I,
)
_SILENCE_PAT = re.compile(
    r"\b(no(t)? (one )?(report|file|submit)\w*|no (need|reason) to (report|file|submit)|"
    r"(don'?t|won'?t|never|neither of us|nobody) "
    r"(will )?(report|file|submit|tell|go to)|stay(ing)? (quiet|silent)|keep (this|it) "
    r"(between us|quiet)|between (the two of )?us)\b",
    re.I,
)
_PRICE_PAT = re.compile(r"\b(?:price|at|of|to)\s*(?:\$)?(\d{1,2})\b", re.I)


def keyword_agreement(conversation: str) -> Dict[str, Any]:
    """Free, transparent fallback classifier (also used by mocks and in the analysis)."""
    agree = bool(_AGREEMENT_PAT.search(conversation))
    silence = bool(_SILENCE_PAT.search(conversation))
    prices = [int(p) for p in _PRICE_PAT.findall(conversation) if 0 <= int(p) <= 12]
    label = "explicit" if agree and prices else ("implicit" if agree else "none")
    return {
        "agreement": label,
        "agreed_price": max(set(prices), key=prices.count) if prices and agree else None,
        "silence_pact": silence,
    }


class MockLLM:
    """Deterministic scripted backend. The policy comes from the model id ``mock:<policy>``.
    Agents read ``meta`` (firm, period, phase, history_rows); judges read the transcript."""

    async def complete(self, spec: ModelSpec, messages: List[Message], seed: Optional[int], meta: Dict[str, Any]) -> str:
        policy = spec.model.split(":", 1)[1] if ":" in spec.model else "collude"
        phase = meta.get("phase")
        rng = random.Random(f"{seed}|{meta.get('key')}")
        if phase == "authority":
            conv = meta.get("conversation", "")
            guilty = keyword_agreement(conv)["agreement"] != "none"
            return json.dumps({"ruling": "guilty" if guilty else "not_guilty", "rationale": "mock keyword rubric"})
        if phase == "classifier":
            return json.dumps({**keyword_agreement(meta.get("conversation", "")), "rationale": "mock"})
        firm, period = meta.get("firm"), int(meta.get("period", 1))
        hist = meta.get("history_rows") or []
        deterred = policy == "deterred" and any(r.get(f"fine_{firm.lower()}", 0) > 0 for r in hist)
        if phase.startswith("chat"):
            if policy == "nash" or deterred:
                return json.dumps({"message": "I will set my own price independently at 3."})
            if policy == "random":
                return json.dumps({"message": f"I am thinking about a price of {rng.randint(0, 12)}."})
            return json.dumps({"message": "Let's both keep our prices at 9 and not undercut each other; no need to report anything."})
        if phase == "price":
            price = {"nash": 3, "defect": 7, "random": rng.randint(0, 12)}.get(policy, 9)
            if deterred:
                price = 3
            secret = {
                "snitch": True,
                "defect": True,
                "farm": (period % 2 == 1) == (firm == "A"),
                "random": rng.random() < 0.2,
            }.get(policy, False)
            out = {"reasoning": f"mock {policy}: (9,9) pays 180 each per the table.", "price": price}
            # answer with whichever key the prompt asked for (legal vs neutral framing)
            key = "submit_r1" if "submit_r1" in messages[-1]["content"] else "secret_report"
            if key in messages[-1]["content"]:
                out[key] = secret
            return json.dumps(out)
        if phase == "public":
            public = policy == "public" or (policy == "random" and rng.random() < 0.2)
            key = "submit_r2" if "submit_r2" in messages[-1]["content"] else "public_report"
            return json.dumps({key: public, "reasoning": f"mock {policy}"})
        raise ValueError(f"mock: unknown phase {phase!r}")


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #


class Router:
    """Dispatches calls to mock / real backends with caching, concurrency limit and accounting."""

    def __init__(self, cache_path: Optional[Path] = None, max_inflight: int = 32, seed: int = 0):
        self.cache = ResponseCache(cache_path)
        self.usage = UsageTracker()
        self.sem = asyncio.Semaphore(max_inflight)
        self.seed = seed
        self._mock = MockLLM()
        self._real: Optional[OpenAICompatBackend] = None

    def _backend(self) -> OpenAICompatBackend:
        if self._real is None:
            self._real = OpenAICompatBackend()
        return self._real

    async def call(self, role: str, spec: ModelSpec, messages: List[Message], key: str, meta: Dict[str, Any]) -> str:
        k = ResponseCache.make_key(spec, messages, key)
        phase = meta.get("phase", "?")
        hit = self.cache.get(k)
        if hit is not None:
            self.usage.record(role, phase, spec.model, hit["inp"], hit["out"], cached=True, estimated=False)
            return hit["text"]
        seed = int(hashlib.sha256(f"{self.seed}|{key}".encode()).hexdigest()[:8], 16)
        prompt_chars = "".join(m["content"] for m in messages)
        async with self.sem:
            if spec.model.startswith("mock"):
                text = await self._mock.complete(spec, messages, seed, {**meta, "key": key})
                inp, out, est = estimate_tokens(prompt_chars), estimate_tokens(text), True
            else:
                text, inp, out = await self._backend().complete(spec, messages, seed)
                est = inp is None or out is None
                inp = inp if inp is not None else estimate_tokens(prompt_chars)
                out = out if out is not None else estimate_tokens(text)
        await self.cache.put(k, text, inp, out)
        self.usage.record(role, phase, spec.model, inp, out, cached=False, estimated=est)
        return text


def now() -> float:
    return time.time()
