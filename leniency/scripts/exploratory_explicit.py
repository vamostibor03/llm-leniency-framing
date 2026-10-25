"""Exploratory E1 observation that motivated H5c (PREREGISTRATION.md, Amendment 1).

    python scripts/exploratory_explicit.py     # writes runs/exploratory_explicit.md

Per family, E1 legal vs E1 neutral (matched supergames 0-19): share of periods the classifier labels
explicit, explicit+implicit, Δ, and the authority's guilty rate in audit-only periods.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reflex_analysis import CELLS, RUNS, cell, matched, per_sg  # noqa: E402


def main():
    out = ["# Exploratory (pre-amendment): E1 legal vs neutral, classifier labels", "",
           "| family | n | explicit legal | explicit neutral | explicit+implicit legal | explicit+implicit neutral | "
           "Δ legal | Δ neutral | audit-only guilty legal | audit-only guilty neutral |", "|---|---|---|---|---|---|---|---|---|---|"]
    for fam in CELLS:
        rl, *_, = cell(fam, "legal", "E1")
        rn, *_, = cell(fam, "neutral", "E1")
        if not rn:
            continue
        stats = []
        for f in (lambda r: r.get("agreement") == "explicit",
                  lambda r: r.get("agreement") in ("explicit", "implicit"),
                  lambda r: ((r["price_a"] + r["price_b"]) / 2 - 3) / 6):
            a, b = matched(per_sg(rl, f), per_sg(rn, f))
            stats += [np.mean(a), np.mean(b)]
        aud = []
        for rs in (rl, rn):
            x = [r for r in rs if r.get("audit") and r.get("report_type") == "none"]
            aud.append(f"{sum(r['authority_ruling'] == 'guilty' for r in x)}/{len(x)}")
        out.append(f"| {fam} | {len(matched(per_sg(rl, len), per_sg(rn, len))[0])} | " + " | ".join(f"{s:.3f}" for s in stats) + f" | {aud[0]} | {aud[1]} |")
    text = "\n".join(out)
    (RUNS / "exploratory_explicit.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
