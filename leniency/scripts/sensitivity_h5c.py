"""Post-hoc robustness checks for H5c, requested in review (NOT preregistered).

    python scripts/sensitivity_h5c.py            # writes runs/sensitivity_h5c.md

1. Classifier precision: rescale each arm's explicit share by an assumed precision of the classifier's
   'explicit' label (recall assumed 1: the hand-check found 0 of 20 misses). Scenarios use the hand-check
   counts (results/handcheck): pooled 5/12, per framing 2/6 legal and 3/6 neutral, and two adversarial ones.
2. Differential attrition (Haiku): the neutral supergames lost to parse failures are counted as 0 explicit.
3. Markups: bootstrap 95% CI (10,000 resamples, seed 0) of mean Δ(neutral) − mean Δ(legal) over supergames.
4. Data timing: when each arm's periods.jsonl was last written, against the Amendment 1 commit time.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parent))
from confirm_analysis import PRIMARY  # noqa: E402
from reflex_analysis import RUNS, delta, matched, per_sg, rows  # noqa: E402

AMENDMENT = "2026-10-24 22:42 CEST (commit 444b33a)"
SCENARIOS = [("pooled observed, 5/12 both", 5 / 12, 5 / 12), ("per framing observed, 2/6 legal, 3/6 neutral", 2 / 6, 3 / 6),
             ("legal perfect, neutral 3/6", 1.0, 3 / 6), ("adversarial: legal perfect, neutral 1/3", 1.0, 1 / 3)]


def explicit(r) -> bool:
    return r.get("agreement") == "explicit"


def main():
    rng = np.random.default_rng(0)
    out = ["# H5c robustness checks (post hoc, not preregistered)", ""]
    out += ["## 1. Classifier precision", "", "| family | scenario | explicit legal | explicit neutral | difference |", "|---|---|---|---|---|"]
    attr, marg, timing = [], [], []
    for fam, ((lr, lc), (nr, nc)) in PRIMARY.items():
        L, N = rows(lr, lc), rows(nr, nc)
        el, en = map(np.array, matched(per_sg(L, explicit), per_sg(N, explicit)))
        for lab, pl, pn in SCENARIOS:
            out.append(f"| {fam} | {lab} | {el.mean() * pl:.3f} | {en.mean() * pn:.3f} | {en.mean() * pn - el.mean() * pl:+.3f} |")
        allsg = sorted(s for s in per_sg(L, explicit) if s < 20)
        nmap = per_sg(N, explicit)
        miss = [s for s in allsg if s not in nmap]
        if miss:
            lf = [per_sg(L, explicit)[s] for s in allsg]
            nf = [nmap.get(s, 0.0) for s in allsg]
            attr.append(f"| {fam} | {len(miss)} ({', '.join(map(str, miss))}) | {np.mean(nf):.3f} | "
                        f"{mannwhitneyu(lf, nf, alternative='less').pvalue:.2g} |")
        dl, dn = map(np.array, matched(per_sg(L, delta), per_sg(N, delta)))
        b = [rng.choice(dn, len(dn)).mean() - rng.choice(dl, len(dl)).mean() for _ in range(10_000)]
        lo, hi = np.percentile(b, [2.5, 97.5])
        marg.append(f"| {fam} | {dl.mean():.3f} | {dn.mean():.3f} | {dn.mean() - dl.mean():+.3f} | [{lo:+.3f}, {hi:+.3f}] | [{lo * 6:+.2f}, {hi * 6:+.2f}] |")
        for arm, run in (("legal", lr), ("neutral", nr)):
            t = dt.datetime.fromtimestamp((RUNS / run / "periods.jsonl").stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            timing.append(f"| {fam} | {arm} | {run} | {t} |")
    out += ["", "## 2. Differential attrition (missing neutral supergames counted as 0 explicit)", "",
            "| family | missing | explicit neutral (worst case) | p, one-sided MW |", "|---|---|---|---|", *attr]
    out += ["", "## 3. Markup difference", "",
            "| family | Δ legal | Δ neutral | neutral − legal | 95% bootstrap CI | CI in price units |", "|---|---|---|---|---|---|", *marg]
    out += ["", f"## 4. Data timing (Amendment 1: {AMENDMENT})", "", "| family | arm | run | periods.jsonl last written (local time) |",
            "|---|---|---|---|", *timing, "", "Only the neutral arms were collected after Amendment 1; the legal arms are baseline cells."]
    text = "\n".join(out)
    (RUNS / "sensitivity_h5c.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
