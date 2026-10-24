# CLAUDE.md: Bounty Farming (AI Collusion Research Sprint)

**Read `HACKATHON_PLAN.md` first.** It holds the full context, hypotheses, timeline, budget, reading list and Lee's target numbers.

## What this folder is
- `leniency/`: the experiment harness, a Python package. It is a faithful re-implementation of Lee (SSRN 7426061) plus our extension flags. 36 tests pass with mock agents; **no real model runs have been made yet**.
- `papers/`: Lee's paper (PDF), the direct precedent we build on and challenge.
- `notes/`: a condensed literature review, sprint facts and the transcript of the Colosseum talk.
- `paper/`: the draft paper (Markdown). It may arrive later from a parallel session.

## Hard rules
- **Never fabricate results, numbers or references.** Doing so disqualifies the submission. Any number in the paper must come from `runs/*` analysis output. Any citation must be verified by opening its URL.
- **Never commit API keys** (`OPENROUTER_API_KEY`, `LENIENCY_API_KEY`). Use environment variables only.
- **Ask before spending more than about $10 in one command.** Re-estimate cost from `runs/<name>/usage.json` after the smoke test.
- **Freeze the hypotheses** (`PREREGISTRATION.md`, committed with a timestamp) once the Lee baseline validates and *before* looking at the extension results.
- Keep Lee's baseline prompts verbatim (a test enforces this). Extensions go behind config flags only.
- Treat the supergame as the unit of analysis, never the period.

## Immediate next steps
1. `cd leniency && python3 -m venv .venv && source .venv/bin/activate && pip install -e . && pip install matplotlib pytest modal && python -m pytest -q`
2. Smoke test: `python -m leniency run configs/smoke.yaml --out runs/smoke_gpt41mini` (needs `OPENROUTER_API_KEY`; about $0.25). Read 5–10 transcripts in `runs/smoke_gpt41mini/periods.jsonl`.
3. In parallel, start the Modal deploy (`deploy/modal_vllm.py`; untested, so fix it if needed).
4. Run the Lee baseline, then compare with Lee's Table 4 (plan §6). The positive control requires the E0 markup to be above 0.8 and the reporting ladder to appear.
5. Freeze the hypotheses, then run the extensions, then `analyze` and `figures`.

## Deadline
Internal deadline: **Sun Oct 25, 23:00 Vienna**. Official deadline: Mon Oct 26, 12:59 Vienna (Sun 23:59 AoE).
