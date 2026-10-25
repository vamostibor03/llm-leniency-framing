"""Run inventory and API cost (paper Appendix C).

    python scripts/run_inventory.py              # writes runs/run_inventory.md

Tokens come from each run's cache.jsonl, which holds one row per paid API response across every
invocation (usage.json is overwritten by each resume/top-up, so it undercounts). A row's role is
inferred from its JSON keys: "ruling" = authority, "agreement" = classifier, anything else = agent.
Cost = tokens x OpenRouter list price fetched 2026-10-25 (below); billed amounts can differ slightly.
"""

from __future__ import annotations

import json
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"
PRICE = {  # $ per 1M tokens (input, output), OpenRouter list prices on 2026-10-25
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "qwen/qwen3-14b": (0.12, 0.24),
    "meta-llama/llama-3.3-70b-instruct": (0.10, 0.32),  # DeepInfra; screen_llama33_70b was not pinned
    "google/gemini-3.5-flash-lite": (0.30, 2.50),
    "anthropic/claude-haiku-5.5": (0.10, 0.50),
}
JUDGE = "openai/gpt-4.1-mini"
ORDER = ["smoke_gpt41mini", "lee_gpt41mini", "screen_gpt4omini", "screen_qwen3_14b", "screen_llama33_70b",
         "lee_llama33_70b", "screen_gemini35fl", "screen_haiku55", "lee_haiku55", "reflex_gpt4omini",
         "reflex_gpt41mini", "reflex_gemini35fl", "reflex_llama33_70b", "reflex_haiku55",
         "confirm_haiku55", "confirm_llama33_70b"]
ACCOUNT2 = {"lee_haiku55", "reflex_gpt4omini", "reflex_gpt41mini", "reflex_gemini35fl", "reflex_llama33_70b",
            "reflex_haiku55", "confirm_haiku55", "confirm_llama33_70b"}  # plus the top-ups below and the probe
TOPUP_AFTER_SWITCH = {"screen_gpt4omini", "screen_gemini35fl"}  # E1/E3b cells extended to 20 supergames


def role(text: str) -> str:
    try:
        obj = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except ValueError:
        return "agent"
    if isinstance(obj, dict) and "ruling" in obj:
        return "authority"
    if isinstance(obj, dict) and "agreement" in obj:
        return "classifier"
    return "agent"


def main():
    out = ["# Run inventory and API cost", "",
           "| run | agent model | conditions | supergames done | failed | API calls | input tokens | output tokens | est. cost ($) |",
           "|---|---|---|---|---|---|---|---|---|"]
    tot = 0.0
    for name in ORDER:
        d = RUNS / name
        cfg = json.loads((d / "config.json").read_text())
        agent = cfg["models"]["agent_a"]["model"]
        conds = sorted({json.loads(l)["condition"] for l in (d / "periods.jsonl").read_text().splitlines()})
        sgs = {(r["condition"], r["supergame"]) for r in map(json.loads, (d / "periods.jsonl").read_text().splitlines())}
        failed = len((d / "errors.jsonl").read_text().splitlines()) if (d / "errors.jsonl").exists() else 0
        calls, cost, tin, tout = 0, 0.0, 0, 0
        for line in (d / "cache.jsonl").read_text().splitlines():
            r = json.loads(line)
            m = agent if role(r.get("text") or "") == "agent" else JUDGE
            pi, po = PRICE[m]
            calls += 1
            tin += r.get("inp") or 0
            tout += r.get("out") or 0
            cost += (r.get("inp") or 0) * pi / 1e6 + (r.get("out") or 0) * po / 1e6
        tot += cost
        out.append(f"| {name} | {agent} | {', '.join(conds)} | {len(sgs)} | {failed} | {calls:,} | {tin:,} | {tout:,} | {cost:.2f} |")
    out += ["", f"**Total estimated API cost of the game runs: ${tot:.2f}**, plus the comprehension probe "
                "(400 calls, not metered; under $0.20 at these prices).", "",
            "Failed = supergames aborted on repeated unparseable replies and excluded (lee_haiku55: 1 after a re-run "
            "with more retries recovered 6 of 7; see PREREGISTRATION.md §0). `smoke_gpt41mini` used 4-period supergames.",
            "Prices: OpenRouter list prices on 2026-10-25; agents use the agent model, authority and classifier use "
            "gpt-4.1-mini. `screen_llama33_70b` was not pinned to a provider, so its cost is a lower bound."]
    text = "\n".join(out)
    (RUNS / "run_inventory.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
