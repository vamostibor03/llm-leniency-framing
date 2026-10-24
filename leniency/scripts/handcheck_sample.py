"""Draw the blinded hand-check sample of classifier labels (PREREGISTRATION.md section 4, Amendment 1).

    python scripts/handcheck_sample.py           # writes runs/handcheck/items.json and key.json

32 conversations from the H5c cells (E3b legal vs neutral, Haiku and Llama, matched supergames):
8 per family x framing cell, stratified by the classifier's label (3 explicit, 3 implicit, 2 none),
shown in random order. items.json holds only the transcript; key.json (never shown to the rater)
maps each item to its run, period, framing, family and classifier label.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reflex_analysis import RUNS, rows  # noqa: E402

CELLS = {
    ("claude-haiku-5.5", "legal"): ("lee_haiku55", "E3b"),
    ("claude-haiku-5.5", "neutral"): ("confirm_haiku55", "E3b_neutral"),
    ("llama-3.3-70b", "legal"): ("lee_llama33_70b", "E3b"),
    ("llama-3.3-70b", "neutral"): ("confirm_llama33_70b", "E3b_neutral"),
}
PER_LABEL = {"explicit": 3, "implicit": 3, "none": 2}
SEED = 2026


def main():
    rng = random.Random(SEED)
    data = {k: rows(*v) for k, v in CELLS.items()}
    for fam in {f for f, _ in CELLS}:  # matched supergames only, as in the H5c test
        common = {r["supergame"] for r in data[(fam, "legal")]} & {r["supergame"] for r in data[(fam, "neutral")]}
        for fr in ("legal", "neutral"):
            data[(fam, fr)] = [r for r in data[(fam, fr)] if r["supergame"] in common]
    picks = []
    for (fam, fr), rs in data.items():
        for label, k in PER_LABEL.items():
            pool = [r for r in rs if r.get("agreement") == label and r.get("chat")]
            picks += [(fam, fr, r) for r in rng.sample(pool, k)]
    rng.shuffle(picks)
    items, key = [], {}
    for i, (fam, fr, r) in enumerate(picks, 1):
        iid = f"item{i:02d}"
        items.append({"id": iid, "chat": [{"firm": m["speaker"], "text": m["text"]} for m in r["chat"]]})
        key[iid] = {"family": fam, "framing": fr, "run": CELLS[(fam, fr)][0], "condition": r["condition"],
                    "supergame": r["supergame"], "round": r["round"], "classifier": r["agreement"],
                    "classifier_rationale": r.get("classifier_rationale")}
    out = RUNS / "handcheck"
    out.mkdir(exist_ok=True)
    (out / "items.json").write_text(json.dumps(items, indent=1))
    (out / "key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(items)} items -> {out}/items.json (blinded), key.json (hidden)")


if __name__ == "__main__":
    main()
