"""Command line.

    python -m leniency check                                   # payoff-matrix sanity checks
    python -m leniency run configs/lee_baseline.yaml --mock collude --out runs/mock
    python -m leniency run configs/lee_baseline.yaml --out runs/lee_gpt41mini   # real calls
    python -m leniency analyze runs/lee_gpt41mini
    python -m leniency figures runs/                             # the 4 paper figures (pooled runs)
    python -m leniency budget runs/mock_collude runs/mock_snitch --supergames 30 --conditions 8
    python -m leniency prompts --regime E2 --framing neutral     # print the prompts a firm sees

Useful overrides on ``run``: --supergames N, --periods T, --only E2,E3a, --model <id> (all roles),
--concurrency K, --mock <policy>[,<policy_b>], -y (skip the cost confirmation).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path

from . import prompts as P
from .analysis import analyze, to_markdown
from .budget import budget_table, cost_per_supergame
from .config import Condition, ExperimentConfig, ModelSpec, Models, load_config, with_mock_models
from .llm import MOCK_POLICIES, PRICES_PER_M
from .payoffs import verify_matrix
from .runner import run_experiment


def _calls_upper_bound(cfg: ExperimentConfig) -> int:
    per_period = 0
    total = 0
    for c in cfg.conditions:
        chat = 0 if c.chat == "none" else 2 * c.chat_rounds
        per_period = chat + 2 + (2 if c.regime_spec.reporting else 0) + (1 if c.regime_spec.authority else 0) + (
            1 if cfg.models.classifier and c.chat != "none" else 0)
        total += per_period * cfg.periods * cfg.supergames
    return total


def cmd_run(a) -> None:
    cfg = load_config(a.config)
    if a.supergames is not None:
        cfg.supergames = a.supergames
    if a.periods is not None:
        cfg.periods = a.periods
    if a.concurrency is not None:
        cfg.concurrency = a.concurrency
    if a.only:
        keep = set(a.only.split(","))
        cfg.conditions = [c for c in cfg.conditions if c.name in keep or c.regime in keep]
        if not cfg.conditions:
            sys.exit(f"--only {a.only}: no matching condition")
    if a.model:
        m = cfg.models
        cfg.models = Models(replace(m.agent_a, model=a.model), replace(m.agent_b, model=a.model),
                            replace(m.authority, model=a.model),
                            replace(m.classifier, model=a.model) if m.classifier else None)
    if a.mock:
        pol = a.mock.split(",")
        for p in pol:
            if p not in MOCK_POLICIES:
                sys.exit(f"unknown mock policy {p!r}; choose from {list(MOCK_POLICIES)}")
        cfg = with_mock_models(cfg, pol[0], pol[1] if len(pol) > 1 else None)
    out = Path(a.out or f"runs/{cfg.name}{'_mock_' + a.mock.replace(',', '-') if a.mock else ''}")
    ub = _calls_upper_bound(cfg)
    models = sorted({s.model for s in cfg.models.by_role().values() if s})
    print(f"{len(cfg.conditions)} condition(s) x {cfg.supergames} supergames x {cfg.periods} periods; "
          f"<= {ub:,} model calls (+retries). Models: {', '.join(models)}")
    real = [m for m in models if not m.startswith("mock")]
    if real and not a.yes and sys.stdin.isatty():
        if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            sys.exit("aborted")
    usage = asyncio.run(run_experiment(cfg, out, quiet=a.quiet))
    t = usage["total"]
    print(f"\ndone: {usage['supergames_run']} supergames ({usage['supergames_failed']} failed, "
          f"{usage['supergames_skipped_already_done']} already done) in {usage['wall_seconds']}s; "
          f"{t['calls']:,} calls ({t['cached']:,} cached), {t['input_tokens']:,} in / {t['output_tokens']:,} out tokens"
          + (f", ${usage['cost_usd']:.2f}" if usage.get("cost_usd") is not None else ", cost: unknown model price"))
    print(f"output: {out}/periods.jsonl  ->  python -m leniency analyze {out}")


def cmd_analyze(a) -> None:
    res = analyze(a.run_dir, a.reference)
    print(to_markdown(res["table4"]))
    print(f"\nwritten to {Path(a.run_dir) / 'analysis'}")


def cmd_figures(a) -> None:
    from .figures import make_figures

    res = make_figures(a.src, a.out, from_csv=a.from_csv, pool=not a.no_pool)
    for p in res["csv"] + res["figures"]:
        print(p)


def cmd_budget(a) -> None:
    print(budget_table([Path(d) for d in a.run_dirs], a.supergames, a.conditions))


def cmd_check(a) -> None:
    ok = True
    for k, v in verify_matrix().items():
        print(f"{k:36s} {v}")
    v = verify_matrix()
    ok &= v["formula_mismatches"] == [] and v["pi(3,3)"] == 100 and v["pi(9,9)"] == 180
    ok &= v["pure_nash_equilibria"] == [(3, 3)] and v["joint_profit_max"] == (360, 9, 9)
    print("\nOK" if ok else "\nMISMATCH")
    sys.exit(0 if ok else 1)


def cmd_prompts(a) -> None:
    from .config import PostConviction

    cond = Condition(regime=a.regime, framing=a.framing, chat=a.chat, reasoning=a.reasoning,
                     reveal_reporter=a.reveal,
                     post_conviction=PostConviction.dissolve_on_conviction() if a.dissolve else PostConviction())
    reg = cond.regime_spec
    conv = 'You: "Let\'s both price at 9." | Competitor: "Agreed, 9 it is."'
    print("=== SYSTEM ===\n" + P.system_prompt(reg, cond))
    print("\n=== CHAT ===\n" + P.chat_prompt(cond, 1, "(none yet, this is the first period)", "(no messages yet)"))
    print("\n=== PRICE ===\n" + P.price_prompt(reg, cond, 1, "(none yet, this is the first period)", conv))
    if reg.reporting:
        print("\n=== PUBLIC ===\n" + P.public_prompt(cond, 1, 9, 9, conv))
    if a.dissolve:
        print("\n=== MONITORING NOTICE ===\n" + P.monitoring_notice(cond, cond.post_conviction, 4, reg, 0.1))
    print("\n=== AUTHORITY ===\n" + P.authority_prompt(conv))
    print("\n=== CLASSIFIER (ours) ===\n" + P.classifier_prompt(conv))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="leniency", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("config")
    r.add_argument("--out")
    r.add_argument("--mock", help=f"scripted agents, no API: {', '.join(MOCK_POLICIES)} (A,B for two policies)")
    r.add_argument("--model", help="override every role's model id")
    r.add_argument("--supergames", type=int)
    r.add_argument("--periods", type=int)
    r.add_argument("--concurrency", type=int)
    r.add_argument("--only", help="comma-separated condition names or regimes")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("-y", "--yes", action="store_true")
    r.set_defaults(fn=cmd_run)
    an = sub.add_parser("analyze")
    an.add_argument("run_dir")
    an.add_argument("--reference", help="reference condition for p-values (default E0)")
    an.set_defaults(fn=cmd_analyze)
    fg = sub.add_parser("figures", help="write the 4 planned paper figures (+ their CSVs)")
    fg.add_argument("src", help="a run dir, a dir of run dirs, or (with --from-csv) a dir of figure CSVs")
    fg.add_argument("--out", help="output dir (default: <src>/figures)")
    fg.add_argument("--from-csv", action="store_true", help="re-plot from CSVs written by an earlier call")
    fg.add_argument("--no-pool", action="store_true",
                    help="keep a (model, condition) cell found in several runs apart as condition@run")
    fg.set_defaults(fn=cmd_figures)
    b = sub.add_parser("budget")
    b.add_argument("run_dirs", nargs="+")
    b.add_argument("--supergames", type=int, default=30)
    b.add_argument("--conditions", type=int, default=8)
    b.set_defaults(fn=cmd_budget)
    c = sub.add_parser("check")
    c.set_defaults(fn=cmd_check)
    pp = sub.add_parser("prompts")
    pp.add_argument("--regime", default="E2")
    pp.add_argument("--framing", default="legal", choices=["legal", "neutral"])
    pp.add_argument("--chat", default="mandatory", choices=["mandatory", "optional", "none"])
    pp.add_argument("--reasoning", default="one_sentence", choices=["one_sentence", "free"])
    pp.add_argument("--reveal", default="implicit", choices=["implicit", "explicit", "hidden"])
    pp.add_argument("--dissolve", action="store_true")
    pp.set_defaults(fn=cmd_prompts)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
