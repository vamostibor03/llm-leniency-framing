# leniency: LLM cartels under leniency and whistleblower-reward programmes

A faithful, extensible re-implementation of **Lee, "LLM Leniency and Reward Experiment" (SSRN
7426061)**, which runs the Bigoni et al. (2012) leniency experiment with LLM firms. With every
extension flag off, the harness *is* Lee's protocol. The extensions are opt-in config flags, so
each one can be compared against its own Lee baseline cell.

```
pip install -e .            # pyyaml, numpy, pandas, scipy. HTTP uses the stdlib (no openai SDK)
python -m leniency check    # payoff-matrix sanity checks
python -m pytest -q         # 36 key-free tests (mock agents + a local fake OpenAI server)

# key-free end-to-end run (scripted agents), then Lee's Table 4
python -m leniency run configs/extensions.yaml --mock farm --out runs/mock_farm -y
python -m leniency analyze runs/mock_farm

# real run (OpenRouter): set OPENROUTER_API_KEY, or LENIENCY_BASE_URL + LENIENCY_API_KEY
python -m leniency run configs/smoke.yaml --out runs/smoke_gpt41mini           # ~530 calls, ~$0.25
python -m leniency run configs/lee_baseline.yaml --out runs/lee_gpt41mini      # replication
python -m leniency run configs/extensions.yaml --out runs/ext_gpt41mini
python -m leniency prompts --regime E3b --framing neutral --dissolve          # print the exact prompts
python -m leniency budget runs/mock_collude runs/mock_snitch --supergames 30 --conditions 8
```

If the Poseidon starter repo's `util/` package (`poseidon_compute`) is installed, its endpoint
and key are used automatically. Otherwise the default is OpenRouter.

## Protocol (Lee baseline)

* **Market.** A differentiated Bertrand duopoly with integer prices 0..12 and the Bigoni Table 1
  payoff matrix (`leniency/payoffs.py`). The stage-game Nash equilibrium is (3,3) at 100 each,
  and the joint-profit maximum is (9,9) at 180 each. Markup index Δ = (mean price − 3)/6.
* **Supergames.** 20 periods each, horizon not told to agents. A fresh agent pair per supergame
  (agents are stateless: every call is rebuilt from the history). The history shows the last 40
  periods.
* **Each period:**
  1. Mandatory chat: 2 rounds × 1 message per firm, with a random first speaker each period.
     An empty message is retried up to 3×.
  2. Simultaneous price and secret report.
  3. Prices are revealed.
  4. If nobody filed a secret report, each firm makes a simultaneous public-report decision.
  5. If anyone reported, or a random audit fires (α = 0.10), the authority LLM rules
     guilty/not_guilty on the conversation only.
  6. Settlement: u = π − fine + reward.
* **Regimes:**

  | regime | rule |
  |---|---|
  | E0 | Laissez-faire. No authority, no reporting. |
  | E1 | Fine F = 200; reporting gives no exemption. |
  | E2 | Leniency: sole reporter pays 0, non-reporter pays F, both reporters pay F/2. |
  | E3a | Leniency plus reward R = 1·F to a sole reporter. |
  | E3b | Leniency plus reward R = 2·F to a sole reporter. |

* **Prompts.** System, chat, price, public and authority prompts are Lee's, verbatim
  (`prompts.LEE_*`). Tests assert the baseline prompts equal them exactly.

### Our choices where Lee is silent (check against the paper or with the author)

| item | our choice | where |
|---|---|---|
| Regime "market rules" text | written by us; states exactly the payoffs `settle()` applies | `prompts.market_rules` |
| Payoff-table layout in the prompt | rows = own price, columns = competitor price, plain text grid | `payoffs.format_payoff_table` |
| E0 | no authority **and** no report option (report clause removed from the price prompt) | `config.REGIMES` |
| Reward timing | paid only on a guilty ruling, only to a *sole* reporter (both reporting means F/2 each, no reward) | `game.settle` |
| Audit conviction under E2/E3 | nobody reported, so both pay F | `game.settle` |
| First speaker | redrawn every period | `Supergame._chat` |
| Chat still empty after 3 retries | logged as silent; the period continues | `Supergame._chat` |
| Unparseable price/report after 3 retries | supergame aborted and logged in `errors.jsonl` (never imputed) | `Supergame._ask_json` |
| History contents | own price, competitor price, own profit, own fine, own reward, own net payoff | `prompts.render_history` |
| Temperatures | agents 1.0; authority and classifier 0 | `configs/*.yaml` |

**Flag:** a 40-period history window with 20-period supergames and fresh agents never binds.
Either Lee's history carries over across supergames, or the 40 is simply non-binding. Worth
confirming before claiming a faithful replication.

## Extensions (all off = Lee)

| flag | values | what it tests |
|---|---|---|
| `framing` | `legal` \| `neutral` | Neutral swaps every legal/moral term for *Form R1/R2, reviewer, criterion Q, outcome Positive, deduction, bonus*, and renames the JSON keys (`submit_r1`, `submit_r2`). Payoffs are identical (tested: same numbers in both rule texts, no legal words in any agent-facing neutral text). Separates payoff-driven from RLHF "reporting is good" reporting. The authority and classifier prompts stay unchanged (they are instruments). |
| `dissolve_on_conviction` / `post_conviction` | `once_per_episode`, `repeat_offender_ineligible`, `recidivism_multiplier` k, `monitoring_notice`, `monitored_audit_prob` | "Realistic leniency": (a) amnesty/reward at most once per cartel episode (an episode ends when the classifier says the conversation has no agreement); (b) repeat offenders lose eligibility (Chen & Rey); (c) a monitoring notice and a k·F fine for a second conviction. Tests whether Lee's "no retaliation / detection ≠ deterrence" result is about LLMs or about a farmable bounty. |
| `reveal_reporter` | `implicit` (Lee) \| `explicit` \| `hidden` | Explicit adds the trigger (who filed / audit) and the ruling to history. Hidden shows only the net payoff. |
| `chat` | `mandatory` (Lee) \| `optional` \| `none` | `none` is the tacit condition: there is nothing to convict, so the authority call is skipped and the ruling is not guilty. |
| `chat_rounds` | int (Lee: 2) | Number of chat rounds per period. |
| `reasoning` | `one_sentence` (Lee) \| `free` | Is Lee's "excess collusion at 10" (π(10,10) = 178 vs π(9,9) = 180) an artifact of the one-sentence limit? |
| models per role | `agent_a`, `agent_b`, `authority`, `classifier` | Cross-model pairs; the judge models are separate from the agents. |
| `false_report_penalty` | float (Lee: 0) | Hook for penalising reports the authority rejects. |

**Why the bounty matters (from the payoff table).** Under E3b, a firm that reports an *intact*
(9,9) cartel gets 180 + 400 = 580, while its partner gets 180 − 200 = −20. If the two firms
alternate the reporter, each averages **280 per period, more than the 180 from silent
collusion**, without ever cutting the price. Under E3a the same scheme averages 170, and under
E2 it averages 80, so neither is profitable. Only E3b admits a jointly profitable "farming"
cartel. The analysis measures it directly (`sole_switch_rate`, `report_no_deviation_rate`,
`farming_index`), and `dissolve_on_conviction` removes it.

## Ground truth Cₜ

A separate classifier call (ours, `prompts.CLASSIFIER`) labels each conversation
`explicit | implicit | none`, plus `agreed_price` and `silence_pact` (an agreement not to report
or file, in any wording). It never affects payoffs, except for the episode boundary in
`once_per_episode`. Set `classifier: null` in the config to use the free keyword classifier
(`llm.keyword_agreement`) instead. `analysis/authority_vs_ct.csv` cross-tabulates authority
rulings against Cₜ.

## Output

`runs/<name>/periods.jsonl` has one row per period. It holds Lee's fields (condition,
supergame, round, price_a/b, base_a/b, secret_a/b, public_a/b, report_type, reporters, audit,
authority_ruling, agreement Cₜ, fine_a/b, reward_a/b, payoff_a/b, chat, reasoning_a/b) plus
investigated, authority/classifier rationales, agreed_price, silence_pact, eligibility,
prior convictions, cartel episode, monitored, first speaker, raw replies, parse retries, models
and every condition flag (`flag_*`).

Other files in the run directory:

* `usage.json`: calls, tokens and $ by role × phase × model.
* `cache.jsonl`: response cache. Re-running the same command resumes and replays finished calls
  for free. Finished supergames are skipped.
* `config.json`: the resolved configuration.
* `errors.jsonl`: supergames that aborted.

## Analysis (`python -m leniency analyze <run>`)

* **Table 4 per condition.** The supergame is the unit of observation; we report mean, s.e. and
  Mann–Whitney p vs E0. Columns: Δ, average price, secret/public/any report rate, conviction
  rate, average fine and reward, price bands (0–2, 3, 4–8, 9, 10–12; our bands), agreement
  rate, silence-pact rate.
* **Bounty farming.** Both-report rate, sole-reporter switch rate, reports filed while the
  cartel is intact, and farming index (share of reward paid in alternating sole-reporter
  convictions).
* **Behaviour after reports.** Retaliation (the non-reporter's price change after a sole
  report, relative to quiet periods) and time to the first report or conviction.
* **Event study.** Market price at k = −3..+5 around the first report (`event_study.csv`).

## Cost (measured prompts; see `python -m leniency budget`)

Calls per supergame (20 periods):

| condition | colluding pair, never reports | always reports |
|---|---|---|
| E0 | 140 | 140 |
| E1–E3b | ≈182 (public stage every period, authority on ~10% audits) | 160 (authority every period, no public stage) |
| `chat: none` | 80 | 40 |

That is about 7–8k input tokens per period, because the system prompt carries the full payoff
table and the history grows.

Estimated cost for 30 supergames × 8 conditions (`configs/extensions.yaml`, all roles on the same
model, +10% retries):

| model (OpenRouter) | $/M in / out | calls | $ total |
|---|---|---|---|
| openai/gpt-4.1-mini | 0.40 / 1.60 | 38–43k | **$19–22** |
| openai/gpt-4o-mini | 0.15 / 0.60 | 38–43k | **$7–8** |
| qwen/qwen3-14b (thinking off) | 0.12 / 0.24 | 38–43k | **$5–6** |
| meta-llama/llama-3.3-70b-instruct | 0.13 / 0.40 | 38–43k | **$6–7** |

Prices are approximate list prices; check them before budgeting (`llm.PRICES_PER_M`). Wall
time is about 7 sequential calls per period, so roughly 3 min per supergame for gpt-4.1-mini;
at `concurrency: 30`, the 240 supergames take about 30 min.

## Layout

```
leniency/payoffs.py   matrix + checks          leniency/game.py      period loop + settle()
leniency/config.py    regimes, flags, YAML     leniency/runner.py    concurrency, resume, JSONL
leniency/prompts.py   Lee verbatim + ours      leniency/analysis.py  Table 4, farming, events
leniency/llm.py       HTTP backend, MockLLM,   leniency/budget.py    cost estimates
                      cache, cost accounting   leniency/cli.py       run/analyze/budget/check/prompts
configs/              lee_baseline, extensions, smoke
tests/                settlement, prompts, parsing, mock pipeline, HTTP backend
```

**Mock policies** (`--mock A[,B]`): collude, snitch, farm, public, defect, nash, random, deterred.
The judges use a keyword rubric. Mocks exist only to test the pipeline. They are not a model of
LLM behaviour.
