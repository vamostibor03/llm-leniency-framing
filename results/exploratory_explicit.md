# Exploratory (pre-amendment): E1 legal vs neutral, classifier labels

| family | n | explicit legal | explicit neutral | explicit+implicit legal | explicit+implicit neutral | Δ legal | Δ neutral | audit-only guilty legal | audit-only guilty neutral |
|---|---|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 20 | 0.270 | 0.932 | 0.765 | 0.997 | 0.653 | 0.842 | 2/4 | 0/0 |
| gpt-4.1-mini | 20 | 0.375 | 0.988 | 0.805 | 0.997 | 0.858 | 0.767 | 4/15 | 7/7 |
| gemini-3.5-flash-lite | 20 | 0.838 | 0.835 | 0.922 | 0.915 | 0.643 | 0.567 | 2/3 | 5/9 |
| llama-3.3-70b | 20 | 0.202 | 0.753 | 0.823 | 0.925 | 0.769 | 0.601 | 16/32 | 13/13 |
| claude-haiku-5.5 | 19 | 0.108 | 0.516 | 0.495 | 0.771 | 0.988 | 0.982 | 5/40 | 26/39 |
