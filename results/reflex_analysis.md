# Reflex study: preregistered analysis

Frozen prereg: commit b491bb6. Unit: supergame; matched supergames 0-19. 'Any report' = share of periods with at least one report.

## H1: E1 any-report rate, legal vs neutral framing

| family | n (matched) | legal | neutral | difference | test | p (raw) | p (Holm) |
|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 20 | 0.942 | 1.000 | +0.058 | MW one-sided (legal > neutral) | 1 | 1 |
| gpt-4.1-mini | 20 | 0.583 | 0.840 | +0.258 | MW one-sided (legal > neutral) | 1 | 1 |
| gemini-3.5-flash-lite | 20 | 0.890 | 0.802 | -0.088 | MW one-sided (legal > neutral) | 0.00037 | 0.0011 |
| llama-3.3-70b | 20 | 0.175 | 0.625 | +0.450 | MW two-sided (exploratory) | 5.8e-08 | – |
| claude-haiku-5.5 | 19 | 0.011 | 0.003 | -0.008 | MW two-sided (exploratory) | 0.16 | – |

H1 decision rule (>= 2 of 3 reflexive families significant after Holm): **1 of 3 significant, so H1 is NOT SUPPORTED**.

## H2: gpt-4o-mini framing × regime interaction (any-report rate)

| | E1 | E3b | E3b − E1 |
|---|---|---|---|
| legal | 0.942 | 0.950 | +0.008 |
| neutral | 1.000 | 1.000 | +0.000 |

Difference-in-differences = -0.008; permutation p (one-sided, 10,000 permutations, seed 0) = 0.6603, so **H2 is NOT SUPPORTED**.

## H3: comprehension probe (correct: E1 = pay 200, E3b sole filer = pay 0)

| model | framing | regime | accuracy | 95% CI (Wilson) | n |
|---|---|---|---|---|---|
| gpt-4o-mini | legal | E1 | 1.00 | [0.84, 1.00] | 20 |
| gpt-4o-mini | legal | E3b | 0.10 | [0.03, 0.30] | 20 |
| gpt-4o-mini | neutral | E1 | 1.00 | [0.84, 1.00] | 20 |
| gpt-4o-mini | neutral | E3b | 1.00 | [0.84, 1.00] | 20 |
| gpt-4.1-mini | legal | E1 | 1.00 | [0.84, 1.00] | 20 |
| gpt-4.1-mini | legal | E3b | 1.00 | [0.84, 1.00] | 20 |
| gpt-4.1-mini | neutral | E1 | 1.00 | [0.84, 1.00] | 20 |
| gpt-4.1-mini | neutral | E3b | 1.00 | [0.84, 1.00] | 20 |
| gemini-3.5-flash-lite | legal | E1 | 1.00 | [0.84, 1.00] | 20 |
| gemini-3.5-flash-lite | legal | E3b | 1.00 | [0.84, 1.00] | 20 |
| gemini-3.5-flash-lite | neutral | E1 | 1.00 | [0.84, 1.00] | 20 |
| gemini-3.5-flash-lite | neutral | E3b | 1.00 | [0.84, 1.00] | 20 |
| llama-3.3-70b-instruct | legal | E1 | 1.00 | [0.84, 1.00] | 20 |
| llama-3.3-70b-instruct | legal | E3b | 1.00 | [0.84, 1.00] | 20 |
| llama-3.3-70b-instruct | neutral | E1 | 1.00 | [0.84, 1.00] | 20 |
| llama-3.3-70b-instruct | neutral | E3b | 1.00 | [0.84, 1.00] | 20 |
| claude-haiku-5.5 | legal | E1 | 1.00 | [0.84, 1.00] | 20 |
| claude-haiku-5.5 | legal | E3b | 1.00 | [0.84, 1.00] | 20 |
| claude-haiku-5.5 | neutral | E1 | 1.00 | [0.84, 1.00] | 20 |
| claude-haiku-5.5 | neutral | E3b | 1.00 | [0.84, 1.00] | 20 |

Interpretation rule (reflexive families, E1 question): ≥ 0.8 means 'reports despite understanding the cost'.

## H4: stated reasons for E1 filings under legal framing (reflexive families)

| family | filing decisions | legality/compliance | own payoff/avoid fine | punish partner |
|---|---|---|---|---|
| gpt-4o-mini | 599 | 0.39 | 0.28 | 0.00 |
| gpt-4.1-mini | 369 | 0.94 | 0.42 | 0.29 |
| gemini-3.5-flash-lite | 555 | 0.59 | 0.21 | 0.03 |

## Secondary: prices and convictions per cell (descriptive)

| family | framing | regime | n | Δ | conviction rate | any report |
|---|---|---|---|---|---|---|
| gpt-4o-mini | legal | E1 | 20 | 0.653 | 0.565 | 0.942 |
| gpt-4o-mini | neutral | E1 | 20 | 0.842 | 0.980 | 1.000 |
| gpt-4o-mini | legal | E3b | 20 | 0.634 | 0.605 | 0.950 |
| gpt-4o-mini | neutral | E3b | 20 | 0.801 | 0.985 | 1.000 |
| gpt-4.1-mini | legal | E1 | 20 | 0.858 | 0.450 | 0.583 |
| gpt-4.1-mini | neutral | E1 | 20 | 0.767 | 0.853 | 0.840 |
| gemini-3.5-flash-lite | legal | E1 | 20 | 0.643 | 0.810 | 0.890 |
| gemini-3.5-flash-lite | neutral | E1 | 20 | 0.567 | 0.760 | 0.802 |
| llama-3.3-70b | legal | E1 | 20 | 0.769 | 0.158 | 0.175 |
| llama-3.3-70b | neutral | E1 | 20 | 0.601 | 0.590 | 0.625 |
| claude-haiku-5.5 | legal | E1 | 20 | 0.981 | 0.017 | 0.010 |
| claude-haiku-5.5 | neutral | E1 | 19 | 0.982 | 0.071 | 0.003 |
