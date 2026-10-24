"""Preregistered analysis of the reflex study (PREREGISTRATION.md, frozen at commit b491bb6).

    python scripts/reflex_analysis.py            # prints markdown, writes runs/reflex_analysis.md

H1  E1 any-report rate, legal vs neutral, per reflexive family (Mann-Whitney, one-sided, Holm);
    Llama and Haiku two-sided, exploratory.
H2  gpt-4o-mini framing x regime interaction on any-report rate (permutation test of the
    difference-in-differences, 10,000 permutations, seed 0, framing permuted within regime).
H3  comprehension-probe accuracy with Wilson 95% CIs.
H4  keyword coding of E1 legal filing justifications in the reflexive families.
Unit: supergame; legal and neutral cells compared on matched supergames 0-19.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

RUNS = Path(__file__).resolve().parent.parent / "runs"
SG = 20

# family -> {(framing, regime): (run dir, condition name)}
CELLS = {
    "gpt-4o-mini": {("legal", "E1"): ("screen_gpt4omini", "E1"), ("neutral", "E1"): ("reflex_gpt4omini", "E1_neutral"),
                    ("legal", "E3b"): ("screen_gpt4omini", "E3b"), ("neutral", "E3b"): ("reflex_gpt4omini", "E3b_neutral")},
    "gpt-4.1-mini": {("legal", "E1"): ("lee_gpt41mini", "E1"), ("neutral", "E1"): ("reflex_gpt41mini", "E1_neutral")},
    "gemini-3.5-flash-lite": {("legal", "E1"): ("screen_gemini35fl", "E1"), ("neutral", "E1"): ("reflex_gemini35fl", "E1_neutral")},
    "llama-3.3-70b": {("legal", "E1"): ("lee_llama33_70b", "E1"), ("neutral", "E1"): ("reflex_llama33_70b", "E1_neutral")},
    "claude-haiku-5.5": {("legal", "E1"): ("lee_haiku55", "E1"), ("neutral", "E1"): ("reflex_haiku55", "E1_neutral")},
}
REFLEXIVE = ["gpt-4o-mini", "gpt-4.1-mini", "gemini-3.5-flash-lite"]
EXPLORATORY = ["llama-3.3-70b", "claude-haiku-5.5"]

KEYWORDS = {
    "legality/compliance": r"illegal|unlawful|\blaw|legal|compl(y|ian)|antitrust|violat",
    "own payoff/avoid fine": r"avoid (the )?fine|avoid penalt|protect|safeguard|reduce (the )?fine|leniency",
    "punish partner": r"punish|retaliat|deter|betray|cheat|defect",
}


def rows(run: str, cond: str):
    path = RUNS / run / "periods.jsonl"
    if not path.exists():
        return []
    return [r for r in map(json.loads, path.read_text().splitlines())
            if r["condition"] == cond and r["supergame"] < SG]


def reported(r) -> bool:
    return bool(r.get("secret_a") or r.get("secret_b") or r.get("public_a") or r.get("public_b"))


def per_sg(rs, f):
    d = {}
    for r in rs:
        d.setdefault(r["supergame"], []).append(f(r))
    return {s: float(np.mean(v)) for s, v in d.items()}


def delta(r) -> float:
    return ((r["price_a"] + r["price_b"]) / 2 - 3) / 6


def cell(family, framing, regime):
    run, cond = CELLS[family][(framing, regime)]
    rs = rows(run, cond)
    return rs, per_sg(rs, reported), per_sg(rs, delta), per_sg(rs, lambda r: r["authority_ruling"] == "guilty")


def matched(a: dict, b: dict):
    keys = sorted(set(a) & set(b))
    return [a[k] for k in keys], [b[k] for k in keys]


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, running = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = running
    return adj


def wilson(k, n, z=1.96):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def main():
    out = ["# Reflex study: preregistered analysis", "",
           "Frozen prereg: commit b491bb6. Unit: supergame; matched supergames 0-19. "
           "'Any report' = share of periods with at least one report.", ""]

    # ---------------- H1 ----------------
    out += ["## H1: E1 any-report rate, legal vs neutral framing", "",
            "| family | n (matched) | legal | neutral | difference | test | p (raw) | p (Holm) |", "|---|---|---|---|---|---|---|---|"]
    h1 = []
    for fam in REFLEXIVE + EXPLORATORY:
        _, rl, _, _ = cell(fam, "legal", "E1")
        _, rn, _, _ = cell(fam, "neutral", "E1")
        if not rn:
            out.append(f"| {fam} | – | – | – | – | not run | – | – |")
            continue
        a, b = matched(rl, rn)
        alt = "greater" if fam in REFLEXIVE else "two-sided"
        p = mannwhitneyu(a, b, alternative=alt).pvalue
        h1.append((fam, len(a), np.mean(a), np.mean(b), alt, p))
    conf = [x for x in h1 if x[0] in REFLEXIVE]
    adj = dict(zip([x[0] for x in conf], holm([x[5] for x in conf])))
    for fam, n, ml, mn, alt, p in h1:
        lab = "MW one-sided (legal > neutral)" if alt == "greater" else "MW two-sided (exploratory)"
        out.append(f"| {fam} | {n} | {ml:.3f} | {mn:.3f} | {mn - ml:+.3f} | {lab} | {p:.2g} | "
                   f"{adj[fam]:.2g} |" if fam in adj else
                   f"| {fam} | {n} | {ml:.3f} | {mn:.3f} | {mn - ml:+.3f} | {lab} | {p:.2g} | – |")
    sig = sum(adj[f] < 0.05 for f in adj)
    out += ["", f"H1 decision rule (>= 2 of 3 reflexive families significant after Holm): "
                f"**{sig} of {len(adj)} significant, so H1 is {'SUPPORTED' if sig >= 2 else 'NOT SUPPORTED'}**.", ""]

    # ---------------- H2 ----------------
    fam = "gpt-4o-mini"
    c = {(f, g): matched_vals for (f, g) in CELLS[fam] for matched_vals in [cell(fam, f, g)[1]]}
    if all(c.values()):
        means = {k: np.mean(list(v.values())) for k, v in c.items()}
        did = (means[("neutral", "E3b")] - means[("neutral", "E1")]) - (means[("legal", "E3b")] - means[("legal", "E1")])
        rng = np.random.default_rng(0)
        pools = {g: (list(c[("legal", g)].values()), list(c[("neutral", g)].values())) for g in ("E1", "E3b")}
        null = []
        for _ in range(10_000):
            d = {}
            for g, (L, N) in pools.items():
                allv = np.array(L + N)
                rng.shuffle(allv)
                d[g] = allv[len(L):].mean() - allv[:len(L)].mean()  # neutral - legal within regime
            null.append(d["E3b"] - d["E1"])
        p2 = (1 + sum(x >= did for x in null)) / (1 + len(null))
        out += ["## H2: gpt-4o-mini framing × regime interaction (any-report rate)", "",
                "| | E1 | E3b | E3b − E1 |", "|---|---|---|---|",
                f"| legal | {means[('legal','E1')]:.3f} | {means[('legal','E3b')]:.3f} | {means[('legal','E3b')]-means[('legal','E1')]:+.3f} |",
                f"| neutral | {means[('neutral','E1')]:.3f} | {means[('neutral','E3b')]:.3f} | {means[('neutral','E3b')]-means[('neutral','E1')]:+.3f} |",
                "", f"Difference-in-differences = {did:+.3f}; permutation p (one-sided, 10,000 permutations, seed 0) = {p2:.4f}, "
                    f"so **H2 is {'SUPPORTED' if p2 < 0.05 else 'NOT SUPPORTED'}**.", ""]

    # ---------------- H3 ----------------
    pr = RUNS / "probe" / "results.jsonl"
    if pr.exists():
        res = [json.loads(l) for l in pr.read_text().splitlines()]
        out += ["## H3: comprehension probe (correct: E1 = pay 200, E3b sole filer = pay 0)", "",
                "| model | framing | regime | accuracy | 95% CI (Wilson) | n |", "|---|---|---|---|---|---|"]
        for m in dict.fromkeys(r["model"] for r in res):
            for f in ("legal", "neutral"):
                for g in ("E1", "E3b"):
                    gg = [r for r in res if (r["model"], r["framing"], r["regime"]) == (m, f, g)]
                    k = sum(r["correct"] for r in gg)
                    lo, hi = wilson(k, len(gg))
                    out.append(f"| {m.split('/')[1]} | {f} | {g} | {k/len(gg):.2f} | [{lo:.2f}, {hi:.2f}] | {len(gg)} |")
        out += ["", "Interpretation rule (reflexive families, E1 question): ≥ 0.8 means 'reports despite understanding the cost'.", ""]

    # ---------------- H4 ----------------
    out += ["## H4: stated reasons for E1 filings under legal framing (reflexive families)", "",
            "| family | filing decisions | " + " | ".join(KEYWORDS) + " |", "|---|---|" + "---|" * len(KEYWORDS)]
    for fam in REFLEXIVE:
        rs, *_ = cell(fam, "legal", "E1")
        texts = []
        for r in rs:
            for x in ("a", "b"):
                if r.get(f"secret_{x}"):
                    texts.append(str(r.get(f"reasoning_{x}") or ""))
                if r.get(f"public_{x}"):
                    texts.append(str(r.get(f"public_reasoning_{x}") or ""))
        shares = [np.mean([bool(re.search(p, t, re.I)) for t in texts]) if texts else math.nan for p in KEYWORDS.values()]
        out.append(f"| {fam} | {len(texts)} | " + " | ".join(f"{s:.2f}" for s in shares) + " |")
    out.append("")

    # ---------------- secondary ----------------
    out += ["## Secondary: prices and convictions per cell (descriptive)", "",
            "| family | framing | regime | n | Δ | conviction rate | any report |", "|---|---|---|---|---|---|---|"]
    for fam, cells in CELLS.items():
        for (f, g) in cells:
            rs, rep, dl, cv = cell(fam, f, g)
            if rs:
                out.append(f"| {fam} | {f} | {g} | {len(dl)} | {np.mean(list(dl.values())):.3f} | "
                           f"{np.mean(list(cv.values())):.3f} | {np.mean(list(rep.values())):.3f} |")
    text = "\n".join(out)
    (RUNS / "reflex_analysis.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
