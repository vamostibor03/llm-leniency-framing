# CLAUDE.md: LLM leniency study (AI Collusion Research Sprint)

**Start with `README.md`** for the result and repo map. Then read `PREREGISTRATION.md`, which lists what was observed and when. `HACKATHON_PLAN.md` is the original plan (bounty farming); the project pivoted away from it, as recorded in the preregistration.

## Status (Oct 25, 2026)
- **All experiments are done.** 16 runs, 754 supergames, six agent families; the inventory and cost are in `results/run_inventory.md`.
- **Preregistered results:**
  - H1 and H2 are not supported;
  - H3: agents understand the cost of reporting;
  - H5c (Amendment 1) is supported in both families.
- **Hand-check done:** one human rater (`results/handcheck/`).
- **Paper:** `paper/draft.md` (full) and `paper/apart_submission.md` (template version). All numbers trace to `results/`, and the citations were verified on Oct 25.
- **Open items:**
  - confirm Lee's SSRN number in a browser;
  - make the repo public;
  - paste into the Apart template and submit. Internal deadline: Sun Oct 25, 23:00 Vienna; official: Mon Oct 26, 12:59 Vienna.

## Hard rules
- **Never fabricate results, numbers or references.** Every number in the paper must come from `results/` (generated from `leniency/runs/`). Every citation must be checked against its source.
- **Never commit API keys.** `OPENROUTER_API_KEY` lives in `leniency/.env`, which is gitignored.
- **Ask before spending.** Ask before spending more than about $10 in one command; the OpenRouter credit is nearly used up.
- **Don't edit frozen material.** Never change `PREREGISTRATION.md` above its "Amendments" section, or a committed analysis script after its data exist. Changes go in a new dated amendment.
- **Keep Lee's prompts verbatim.** A test enforces this, and extensions go behind config flags.
- **The supergame is the unit of analysis,** never the period.
- **Don't publish third-party material.** `notes/colosseum_talk_transcript.txt` is kept locally and gitignored.

## Environment
- **Python:** 3.12 venv at `leniency/.venv` (the system Python is 3.9, which is too old).
- **Running:** load the key with `set -a; . leniency/.env; set +a` before `python -m leniency run ...`.
- **Git:** remote is `origin` = github.com/vamostibor03/llm-leniency-framing, branch `main`.
