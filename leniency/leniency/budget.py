"""Budget estimates from a (mock) run.

Input tokens are measured from the real prompts, which the mock run renders in full (history
grows over the supergame exactly as in a real run). Output tokens come from mocks that answer
tersely, so they are replaced by per-phase assumptions (``OUTPUT_TOKENS``), deliberately
generous. Calls per supergame depend on behaviour: the public-report stage only runs when no
secret report was filed, and the authority only runs when someone reports or an audit fires.
So the estimate is given for two behavioural scenarios measured by mock policies:

    collude  (no reports: public stage every period, authority only on audits, ~10%)
    snitch   (secret report every period: no public stage, authority every period)

    python -m leniency budget runs/mock_collude runs/mock_snitch --supergames 30 --conditions 8
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .llm import PRICES_PER_M

# assumed completion tokens per call (generous; JSON + one sentence)
OUTPUT_TOKENS = {"chat": 45, "price": 70, "public": 45, "authority": 90, "classifier": 90}
OUTPUT_TOKENS_FREE_REASONING = {**OUTPUT_TOKENS, "price": 350}

BUDGET_MODELS = ["openai/gpt-4.1-mini", "openai/gpt-4o-mini", "qwen/qwen3-14b", "meta-llama/llama-3.3-70b-instruct"]


def _phase_group(phase: str) -> str:
    return "chat" if phase.startswith("chat") else phase


def per_supergame(run_dir: Path) -> Dict[str, Dict[str, float]]:
    """{phase_group: {"calls": per supergame, "input_tokens": per supergame}} (fresh calls only)."""
    usage = json.loads((run_dir / "usage.json").read_text())
    n = usage["supergames_run"] + usage.get("supergames_skipped_already_done", 0)
    if not n:
        raise ValueError(f"{run_dir}: no supergames")
    out: Dict[str, Dict[str, float]] = {}
    for r in usage["by_role_phase_model"]:
        g = _phase_group(r["phase"])
        d = out.setdefault(g, {"calls": 0.0, "input_tokens": 0.0})
        d["calls"] += r["calls"] / n
        d["input_tokens"] += r["input_tokens"] / n
    return out


def cost_per_supergame(ps: Dict[str, Dict[str, float]], model: str, free_reasoning: bool = False,
                       prices: Dict[str, Tuple[float, float]] = PRICES_PER_M) -> Tuple[float, float, float]:
    """(calls, tokens_in, USD) per supergame with every role on ``model``."""
    pin, pout = prices[model]
    outs = OUTPUT_TOKENS_FREE_REASONING if free_reasoning else OUTPUT_TOKENS
    calls = sum(d["calls"] for d in ps.values())
    tin = sum(d["input_tokens"] for d in ps.values())
    tout = sum(d["calls"] * outs.get(g, 60) for g, d in ps.items())
    return calls, tin, (tin * pin + tout * pout) / 1e6


def budget_table(run_dirs: List[Path], supergames: int, conditions: int, models: Optional[List[str]] = None,
                 overhead: float = 1.10) -> str:
    """Markdown table. ``overhead`` covers parse retries / empty-chat retries (10%)."""
    models = models or BUDGET_MODELS
    lines = [
        f"Experiment: {supergames} supergames x {conditions} conditions = {supergames * conditions} supergames "
        f"(20 periods each); +{(overhead - 1):.0%} retry overhead. All roles on the same model.",
        "",
        "| scenario | phase | calls / supergame | input tokens / supergame |",
        "|---|---|---|---|",
    ]
    measured = {}
    for d in run_dirs:
        ps = per_supergame(d)
        measured[d.name] = ps
        for g, v in sorted(ps.items()):
            lines.append(f"| {d.name} | {g} | {v['calls']:.1f} | {v['input_tokens']:,.0f} |")
        tot_c = sum(v["calls"] for v in ps.values())
        tot_t = sum(v["input_tokens"] for v in ps.values())
        lines.append(f"| {d.name} | **total** | **{tot_c:.1f}** | **{tot_t:,.0f}** |")
    lines += ["", "| model | $/M in | $/M out | scenario | calls (full matrix) | $ / supergame | $ full matrix |",
              "|---|---|---|---|---|---|---|"]
    n_sg = supergames * conditions
    for m in models:
        pin, pout = PRICES_PER_M[m]
        for name, ps in measured.items():
            calls, _, usd = cost_per_supergame(ps, m)
            lines.append(
                f"| {m} | {pin:.2f} | {pout:.2f} | {name} | {calls * n_sg * overhead:,.0f} | "
                f"{usd * overhead:.3f} | {usd * n_sg * overhead:,.2f} |"
            )
    lines += ["", "Prices are approximate OpenRouter list prices (check https://openrouter.ai/models). "
              "qwen/qwen3-14b assumes thinking disabled (`extra_body: {reasoning: {enabled: false}}`); "
              "with thinking on, add ~2-4k output tokens per call (x20-50 cost, hours of latency)."]
    return "\n".join(lines)
