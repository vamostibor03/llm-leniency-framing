"""Comprehension probe (PREREGISTRATION.md, H3): do agents know what filing costs them?

Each model gets the real agent system prompt (payoff table + regime market rules, legal or neutral
framing) and one multiple-choice question: "you file, the competitor does not, the ruling is
guilty / Positive: what fine / deduction do YOU pay?"  Correct: E1 -> 200 (C), E3b -> 0 (A).

    python scripts/comprehension_probe.py --out runs/probe [--n 20]

Writes one JSON line per sample to <out>/results.jsonl and prints accuracy per cell.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from leniency import prompts as P
from leniency.config import Condition
from leniency.llm import extract_json

MODELS = {
    "openai/gpt-4o-mini": {},
    "openai/gpt-4.1-mini": {},
    "google/gemini-3.5-flash-lite": {"reasoning": {"effort": "minimal"}},
    "meta-llama/llama-3.3-70b-instruct": {"provider": {"order": ["DeepInfra"], "allow_fallbacks": False}},
    "anthropic/claude-haiku-5.5": {"reasoning": {"enabled": False}},
}
CORRECT = {"E1": "C", "E3b": "A"}
QUESTION = {
    "legal": ("Comprehension check before play (you do not set a price now). Suppose that in some period "
              "you file a SECRET report, your competitor files nothing, and the authority rules guilty. "
              "What fine do YOU pay that period?"),
    "neutral": ("Comprehension check before play (you do not set a price now). Suppose that in some period "
                "you submit Form R1, your competitor submits nothing, and the reviewer's outcome is Positive. "
                "What deduction do YOU pay that period?"),
}
OPTIONS = ' Answer with exactly one letter: A) 0, B) 100, C) 200. Return JSON: {"answer":"A"|"B"|"C"}.'


def ask(model: str, extra: dict, system: str, user: str) -> str:
    body = {"model": model, "temperature": 1.0, "max_tokens": 400,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], **extra}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    return r["choices"][0]["message"]["content"] or ""


def one(job):
    model, framing, regime, i = job
    cond = Condition(regime=regime, framing=framing)
    system = P.system_prompt(cond.regime_spec, cond, None)
    try:
        raw = ask(model, MODELS[model], system, QUESTION[framing] + OPTIONS)
        ans = str(extract_json(raw).get("answer", "")).strip().upper()[:1] or None
    except Exception as e:  # recorded, never imputed
        raw, ans = f"ERROR: {e}", None
    return {"model": model, "framing": framing, "regime": regime, "i": i, "answer": ans,
            "correct": ans == CORRECT[regime], "raw": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/probe")
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(m, f, r, i) for m in MODELS for f in ("legal", "neutral") for r in ("E1", "E3b") for i in range(a.n)]
    with ThreadPoolExecutor(16) as ex:
        rows = list(ex.map(one, jobs))
    with open(out / "results.jsonl", "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    print(f"{'model':36s} {'framing':8s} {'regime':6s} acc   n  unparsed")
    for m in MODELS:
        for f in ("legal", "neutral"):
            for r in ("E1", "E3b"):
                g = [x for x in rows if (x["model"], x["framing"], x["regime"]) == (m, f, r)]
                print(f"{m:36s} {f:8s} {r:6s} {sum(x['correct'] for x in g) / len(g):.2f} {len(g):3d} "
                      f"{sum(x['answer'] is None for x in g):3d}")


if __name__ == "__main__":
    main()
