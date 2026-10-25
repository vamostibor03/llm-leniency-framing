# Hand-check of classifier labels

Labelled: 32 of 32; missing: none

### All (n = 32)

- agreement (3 classes): 0.47; Cohen's kappa: 0.20
- agreement on explicit vs not: 0.78; kappa: 0.47
- classifier says explicit, human does not: 7; human says explicit, classifier does not: 0

| human \ classifier | explicit | implicit | none |
|---|---|---|---|
| explicit | 5 | 0 | 0 |
| implicit | 6 | 6 | 4 |
| none | 1 | 6 | 4 |

### Framing: legal (n = 16)

- agreement (3 classes): 0.62; Cohen's kappa: 0.44
- agreement on explicit vs not: 0.75; kappa: 0.38
- classifier says explicit, human does not: 4; human says explicit, classifier does not: 0

| human \ classifier | explicit | implicit | none |
|---|---|---|---|
| explicit | 2 | 0 | 0 |
| implicit | 3 | 5 | 1 |
| none | 1 | 1 | 3 |

### Framing: neutral (n = 16)

- agreement (3 classes): 0.31; Cohen's kappa: -0.02
- agreement on explicit vs not: 0.81; kappa: 0.56
- classifier says explicit, human does not: 3; human says explicit, classifier does not: 0

| human \ classifier | explicit | implicit | none |
|---|---|---|---|
| explicit | 3 | 0 | 0 |
| implicit | 3 | 1 | 3 |
| none | 0 | 5 | 1 |

### Family: claude-haiku-5.5 (n = 16)

- agreement (3 classes): 0.50; Cohen's kappa: 0.24
- agreement on explicit vs not: 0.88; kappa: 0.71
- classifier says explicit, human does not: 2; human says explicit, classifier does not: 0

| human \ classifier | explicit | implicit | none |
|---|---|---|---|
| explicit | 4 | 0 | 0 |
| implicit | 2 | 3 | 3 |
| none | 0 | 3 | 1 |

### Family: llama-3.3-70b (n = 16)

- agreement (3 classes): 0.44; Cohen's kappa: 0.17
- agreement on explicit vs not: 0.69; kappa: 0.20
- classifier says explicit, human does not: 5; human says explicit, classifier does not: 0

| human \ classifier | explicit | implicit | none |
|---|---|---|---|
| explicit | 1 | 0 | 0 |
| implicit | 4 | 3 | 1 |
| none | 1 | 3 | 3 |

