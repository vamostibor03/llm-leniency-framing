"""Confirmatory test of H5c (PREREGISTRATION.md, Amendment 1): legal framing makes collusion talk covert.

    python scripts/confirm_analysis.py           # prints markdown, writes runs/confirm_analysis.md

Primary: per-supergame share of periods the classifier labels 'explicit', E3b legal vs E3b neutral,
matched supergames 0-19; Mann-Whitney one-sided (legal < neutral) per family, Holm across Haiku and
Llama; supported only if both are significant after correction.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reflex_analysis import RUNS, delta, holm, matched, per_sg, reported, rows  # noqa: E402

PRIMARY = {
    "claude-haiku-5.5": (("lee_haiku55", "E3b"), ("confirm_haiku55", "E3b_neutral")),
    "llama-3.3-70b": (("lee_llama33_70b", "E3b"), ("confirm_llama33_70b", "E3b_neutral")),
}
SECONDARY = {  # collected before Amendment 1, not examined for this metric
    "gpt-4o-mini (pre-amendment data)": (("screen_gpt4omini", "E3b"), ("reflex_gpt4omini", "E3b_neutral")),
}


def explicit(r) -> bool:
    return r.get("agreement") == "explicit"


def audit_only_guilty(rs):
    aud = [r for r in rs if r.get("audit") and r.get("report_type") == "none"]
    return sum(r["authority_ruling"] == "guilty" for r in aud), len(aud)


def describe(legal_rs, neutral_rs):
    e_l, e_n = matched(per_sg(legal_rs, explicit), per_sg(neutral_rs, explicit))
    d_l, d_n = matched(per_sg(legal_rs, delta), per_sg(neutral_rs, delta))
    r_l, r_n = matched(per_sg(legal_rs, reported), per_sg(neutral_rs, reported))
    return e_l, e_n, d_l, d_n, r_l, r_n


def main():
    out = ["# H5c: legal framing makes collusion talk covert (Amendment 1, confirmatory)", "",
           "| family | n (matched) | explicit share, legal | explicit share, neutral | p (one-sided, raw) | p (Holm) | "
           "Δ legal | Δ neutral | any report legal | any report neutral | audit-only guilty legal | audit-only guilty neutral |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    res = []
    for fam, ((lr, lc), (nr, nc)) in PRIMARY.items():
        L, N = rows(lr, lc), rows(nr, nc)
        if not N:
            out.append(f"| {fam} | not run |" + " – |" * 10)
            continue
        e_l, e_n, d_l, d_n, r_l, r_n = describe(L, N)
        p = mannwhitneyu(e_l, e_n, alternative="less").pvalue
        res.append((fam, len(e_l), e_l, e_n, d_l, d_n, r_l, r_n, audit_only_guilty(L), audit_only_guilty(N), p))
    adj = holm([x[-1] for x in res])
    for (fam, n, e_l, e_n, d_l, d_n, r_l, r_n, gl, gn, p), pa in zip(res, adj):
        out.append(f"| {fam} | {n} | {np.mean(e_l):.3f} | {np.mean(e_n):.3f} | {p:.2g} | {pa:.2g} | {np.mean(d_l):.3f} | "
                   f"{np.mean(d_n):.3f} | {np.mean(r_l):.3f} | {np.mean(r_n):.3f} | {gl[0]}/{gl[1]} | {gn[0]}/{gn[1]} |")
    sig = sum(a < 0.05 for a in adj)
    out += ["", f"Decision rule (both families significant after Holm): **{sig} of {len(adj)}, so H5c is "
                f"{'SUPPORTED' if len(adj) == 2 and sig == 2 else 'NOT SUPPORTED'}**.", "",
            "## Secondary (descriptive; data collected before Amendment 1, not examined for this metric)", "",
            "| family | n | explicit share, legal | explicit share, neutral | Δ legal | Δ neutral |", "|---|---|---|---|---|---|"]
    for fam, ((lr, lc), (nr, nc)) in SECONDARY.items():
        L, N = rows(lr, lc), rows(nr, nc)
        if L and N:
            e_l, e_n, d_l, d_n, *_ = describe(L, N)
            out.append(f"| {fam} | {len(e_l)} | {np.mean(e_l):.3f} | {np.mean(e_n):.3f} | {np.mean(d_l):.3f} | {np.mean(d_n):.3f} |")
    text = "\n".join(out)
    (RUNS / "confirm_analysis.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
