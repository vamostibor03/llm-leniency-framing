"""Unblind the hand-check and score the classifier against the human labels.

    python scripts/handcheck_score.py runs/handcheck/human_labels.json

human_labels.json: {"item01": "explicit" | "implicit" | "none", ...} (exported from the labelling page).
Reports, overall and per framing: raw agreement, Cohen's kappa (3 classes), and agreement on the H5c
metric (explicit vs not explicit), plus the full confusion table. A classifier that reads one framing
more generously would show up as more classifier-only 'explicit' calls in that framing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

LABELS = ("explicit", "implicit", "none")


def kappa(pairs, classes):
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in classes) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def block(name, pairs):
    n = len(pairs)
    exp = [(a == "explicit", b == "explicit") for a, b in pairs]
    out = [f"### {name} (n = {n})", "",
           f"- agreement (3 classes): {sum(a == b for a, b in pairs) / n:.2f}; Cohen's kappa: {kappa(pairs, LABELS):.2f}",
           f"- agreement on explicit vs not: {sum(a == b for a, b in exp) / n:.2f}; kappa: {kappa(exp, (True, False)):.2f}",
           f"- classifier says explicit, human does not: {sum(c and not h for h, c in exp)}; "
           f"human says explicit, classifier does not: {sum(h and not c for h, c in exp)}", "",
           "| human \\ classifier | " + " | ".join(LABELS) + " |", "|---|---|---|---|"]
    for h in LABELS:
        out.append(f"| {h} | " + " | ".join(str(sum(1 for a, b in pairs if a == h and b == c)) for c in LABELS) + " |")
    return out + [""]


def main():
    human = json.loads(Path(sys.argv[1]).read_text())
    key = json.loads((Path(__file__).resolve().parent.parent / "runs" / "handcheck" / "key.json").read_text())
    rows = [(human[i], key[i]["classifier"], key[i]) for i in sorted(key) if human.get(i) in LABELS]
    missing = sorted(set(key) - {i for i in human if human[i] in LABELS})
    out = ["# Hand-check of classifier labels", "", f"Labelled: {len(rows)} of {len(key)}; missing: {missing or 'none'}", ""]
    out += block("All", [(h, c) for h, c, _ in rows])
    for fr in ("legal", "neutral"):
        out += block(f"Framing: {fr}", [(h, c) for h, c, k in rows if k["framing"] == fr])
    for fam in sorted({k["family"] for *_, k in rows}):
        out += block(f"Family: {fam}", [(h, c) for h, c, k in rows if k["family"] == fam])
    text = "\n".join(out)
    (Path(sys.argv[1]).parent / "handcheck_score.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
