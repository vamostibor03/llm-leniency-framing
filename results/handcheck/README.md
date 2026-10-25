# Hand-check of the LLM classifier (H5c cells)

- `items.json`: the 32 blinded transcripts shown to the rater (drawn by `leniency/scripts/handcheck_sample.py`, seed 2026; 8 per family x framing cell of the H5c test, stratified 3 explicit / 3 implicit / 2 none by classifier label).
- `key.json`: unblinding key (run, supergame, round, framing, family, classifier label). Never shown to the rater.
- `human_labels.json`: labels by one human rater (the author), entered on a blinded labelling page on 2026-10-25, 09:55-10:17 UTC; no notes were recorded.
- `handcheck_score.md`: output of `leniency/scripts/handcheck_score.py`, unchanged since commit bf6eda1 (written before any labels existed).
