# H5c robustness checks (post hoc, not preregistered)

## 1. Classifier precision

| family | scenario | explicit legal | explicit neutral | difference |
|---|---|---|---|---|
| claude-haiku-5.5 | pooled observed, 5/12 both | 0.051 | 0.280 | +0.229 |
| claude-haiku-5.5 | per framing observed, 2/6 legal, 3/6 neutral | 0.041 | 0.336 | +0.295 |
| claude-haiku-5.5 | legal perfect, neutral 3/6 | 0.122 | 0.336 | +0.214 |
| claude-haiku-5.5 | adversarial: legal perfect, neutral 1/3 | 0.122 | 0.224 | +0.102 |
| llama-3.3-70b | pooled observed, 5/12 both | 0.120 | 0.354 | +0.234 |
| llama-3.3-70b | per framing observed, 2/6 legal, 3/6 neutral | 0.096 | 0.425 | +0.329 |
| llama-3.3-70b | legal perfect, neutral 3/6 | 0.288 | 0.425 | +0.137 |
| llama-3.3-70b | adversarial: legal perfect, neutral 1/3 | 0.288 | 0.283 | -0.004 |

## 2. Differential attrition (missing neutral supergames counted as 0 explicit)

| family | missing | explicit neutral (worst case) | p, one-sided MW |
|---|---|---|---|
| claude-haiku-5.5 | 4 (1, 4, 12, 13) | 0.538 | 0.00039 |

## 3. Markup difference

| family | Δ legal | Δ neutral | neutral − legal | 95% bootstrap CI | CI in price units |
|---|---|---|---|---|---|
| claude-haiku-5.5 | 0.968 | 0.930 | -0.038 | [-0.088, +0.013] | [-0.53, +0.08] |
| llama-3.3-70b | 0.776 | 0.807 | +0.031 | [-0.025, +0.086] | [-0.15, +0.52] |

## 4. Data timing (Amendment 1: 2026-10-24 22:42 CEST (commit 444b33a))

| family | arm | run | periods.jsonl last written (local time) |
|---|---|---|---|
| claude-haiku-5.5 | legal | lee_haiku55 | 2026-10-24 21:31 |
| claude-haiku-5.5 | neutral | confirm_haiku55 | 2026-10-24 22:48 |
| llama-3.3-70b | legal | lee_llama33_70b | 2026-10-24 19:14 |
| llama-3.3-70b | neutral | confirm_llama33_70b | 2026-10-24 23:02 |

Only the neutral arms were collected after Amendment 1; the legal arms are baseline cells.
