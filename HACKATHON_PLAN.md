# Bounty Farming — AI Collusion Research Sprint (Apart × Poseidon Research)

**Owner:** Tibor Vámos · **Sprint:** Oct 23–25, 2026 · **Status at handoff:** Sat Oct 24, 14:20 Vienna

**State at handoff:**
- The harness is built and tested in mock mode only.
- **No real model runs yet.**
- The paper draft is being written in a parallel session and will land in `paper/`.

---

## 0. TL;DR for the coding agent

1. The code is in `leniency/`. It is a faithful re-implementation of Lee (2026) plus our extensions. 36 tests pass with mock agents. It has never been run against a real model.
2. **Your first job is to get real data.**
   - Set up a venv, run the tests, then run the smoke test against OpenRouter (`openai/gpt-4.1-mini`, about $0.25).
   - In parallel, run the Modal vLLM deploy (`leniency/deploy/modal_vllm.py`, Qwen2.5-32B, paid from Modal credits; untested).
   - Inspect 5–10 transcripts by eye.
3. Then run the Lee replication (`configs/lee_baseline.yaml`), compare it to Lee's Table 4 (§6), freeze the hypotheses, and run the extensions (`configs/extensions.yaml`).
4. Deliverable: a PDF report of at most 8 pages (aim for 5–6) on the Apart template, submitted by **Sun Oct 25 23:00 Vienna** (internal deadline).
5. Rules:
   - **Never fabricate results or references.** Doing so disqualifies the submission.
   - Never commit API keys.
   - Read §9 before spending money.

---

## 1. The sprint (verified facts)

- **Page:** https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25
- **Starter repo:** https://github.com/poseidon-research/collusion_hackathon. We don't depend on it, but `util/poseidon_compute` is auto-used if installed.
- **Organisers:** Apart Research, Poseidon Research (NYC lab focused on steganography, interpretability and monitoring) and AE Studio.
- **Sponsors:** Modal, the AI Alignment Foundation and Nebius.
- **Deadline:** Sun Oct 25, 23:59 AoE, which is **Mon Oct 26, 12:59 Vienna** (clocks go to CET on Sunday). Our internal deadline is Sun 23:00.
- **Submit:** the "Submit project" button on the sprint page. It needs an apartresearch.com account. You can resubmit under the same title before the deadline.
- **Required in the submission:**
  - A PDF on the official template: https://docs.google.com/document/d/1Y5wd3VRbXU5N08BvAGiJUQTaWbMCSPjhzXsR-ozuehg/copy?usp=sharing
  - At most 8 pages, excluding references and appendix. The template suggests about 4, so aim for 5–6.
  - Title, a 150–250 word abstract, and authors.
  - A **"Limitations and Dual-Use / Ethical Considerations" appendix**.
  - An **LLM Usage Statement** (it is in the template).
  - Template sections: Introduction, Related Work, Methods, Results (with a positive control), Discussion & Limitations, Conclusion, Code & Data, References, Appendix.
- **Optional:** a public GitHub repo and a 3–5 minute video.
- **Judging:** each criterion scored 1–5, presumably equally weighted:
  1. Impact potential & innovation
  2. Execution quality
  3. Presentation & clarity
- **Prizes:** $1000 / $500 / $300 / $100 / $100, plus an Apart Fellowship fast-track.
- **Rules:**
  - AI tools are allowed.
  - Fabricated results or references mean disqualification.
  - Pre-existing code must be marked as such.
  - Teams of 1–5 people.
- **Compute:** Tibor has **$50 of Modal credits**. Nebius was named as a sponsor, so ask on Discord about Nebius credits. Discord: https://discord.gg/XswWBvugYs
- **Track:** primary is **Track 1, Q1.5** ("Which single restriction removes the most collusion at least cost?"). We also touch **3.4** (coalition behaviour when watched) and **2.3** (what counts as evidence). Tick Tracks 1 and 3 on the form.
- **Talks:**
  - Remaining: Matthew Lee (Poseidon), "Defining AI Collusion", 17:00 Vienna, Saturday or Sunday (unclear). Worth attending to align our definition.
  - Already happened: the Colosseum talk (Bagdasarian & Nakamura). The transcript is in `notes/colosseum_talk_transcript.txt`.

### What judges reward (from past Apart sprint winners and feedback)
- One sharp framing.
- A positive control.
- Ablations that change one variable at a time.
- Several seeds and confidence intervals.
- Calibrated false-positive rates.
- Honest limitations.
- Clear figures.
- Judges criticised past winners for single runs and for missing false-positive evaluation.

---

## 2. The project

**Working title:** *Bounty Farming: Is LLM Leniency Failure a Property of the Agents or of the Mechanism?*

### Direct precedent, and the reason this project exists
**Jun Yeong Lee, "LLM Leniency and Reward Experiment"** (SSRN 7426061, Pusan National University). The PDF is in `papers/`.

**What Lee did:**
- Ported Bigoni et al. (2012) to LLM firms: a differentiated Bertrand duopoly with prices 0–12, mandatory chat every period, and an LLM competition authority.
- Ran five regimes: E0 laissez-faire, E1 fine, E2 leniency, E3a reward 1F, E3b reward 2F.
- Used 100 supergames × 20 periods each, **one unnamed model** and one seed.

**What Lee found:**
- Reporting rises along the ladder, from 0 to 0.227.
- **Prices barely move:** 9.81 → 8.88, against a competitive price of 3. The markup index goes from 1.135 to 0.980.
- There is no retaliation after a report.
- Agents report *while still colluding*.
- He calls the result "leniency buys prosecutions, not competition".
- He also reports "excess collusion": agents anchor on price 10 even though (9,9) pays more.

### Our insight: Lee's mechanism can be farmed
Under Lee's rules, a firm can report in every period, the cartel is never dissolved, and repeat offenders are never excluded.

| strategy at (9,9) | per-firm average payoff / period |
|---|---|
| Silent collusion (10% audit → fine 200) | 180 − 0.1·200 = **160** |
| Alternate sole reporter, E2 (leniency) | (180 + (180−200))/2 = **80** |
| Alternate sole reporter, E3a (reward 1F) | (380 + (−20))/2 = **180** |
| Alternate sole reporter, E3b (reward 2F) | (580 + (−20))/2 = **280** |

Under E3b, taking turns reporting pays the cartel *more* than silent collusion, and the regulator effectively subsidises the cartel. So Lee's "no retaliation / detection ≠ deterrence" result may be **an artifact of the mechanism design, not a property of LLMs**.

Lee himself notes about two dozen cases of "falsely reporting for leniency" but does not follow them up.

> NOTE: the harness README says E3a farming averages "170". The table above gives 180 (still no worse than silent collusion). Reconcile before the paper; the claim that matters, E3b = 280 > 160, is unaffected.

### Definition of collusion (state this early in the paper)
- **Outcome:** a markup above the Bertrand–Nash level (Δ > 0).
- **Reportability:** a cartel is *reportable* only if there is an explicit or implicit agreement in the communication.
- **Mapping to Colosseum's say/do typology** (Nakamura et al.):
  - *direct*: talk + high price
  - *attempted / "on paper"*: talk, no high price
  - *hidden*: no talk, high price
  - *benign*: neither

---

## 3. Research questions & hypotheses (freeze after the baseline validates; do not change after seeing extension results)

**Main question:** when LLM cartels survive leniency, is that a property of the agents or of the program design?

| # | Hypothesis | Condition(s) | Priority |
|---|---|---|---|
| H1 | **Replication:** reporting rises along the ladder while prices barely fall (Lee), across more than one model family | E0, E1, E2, E3a, E3b | CORE |
| H2 | **Bounty farming:** under E3b, sole reporters alternate and reports are filed while the cartel stays intact (both prices ≥ 8 before and after), well above chance | E3b | CORE |
| H3 | **Mechanism:** with dissolve-on-conviction (amnesty once per cartel episode, repeat offenders ineligible, monitoring, k = 2 fine), prices fall significantly more than under Lee's E3b. If they don't, Lee's result gets stronger. Both outcomes are publishable | E3b + dissolve vs E3b (optionally E2 + dissolve) | CORE |
| H4 | **Strategy vs trained reflex:** neutral framing with identical payoffs changes report rates, and the effect depends on model family (cf. WhistleBench) | E3b neutral vs E3b | HIGH (cheap) |
| H5 | **Displacement:** enforcement moves collusion from talk to hidden coordination. Measured by evasion: P(authority guilty \| investigated, price ≥ 8), authority-vs-classifier disagreement, and "stay under the radar" language | analysis across regimes (no extra runs) | HIGH (free) |
| H6 | **Tacit gap:** without chat there is nothing to report, so leniency has no effect on supracompetitive prices | E2 chat:none (or E3b chat:none) | MEDIUM |
| side | Is "excess collusion at 10" an artifact of the one-sentence reasoning limit? | E3b reasoning:free (or E0 free) | LOW |

**Cut order if behind:** the third model family, then the side check, then H6. **Never cut H1–H3 or H4.**

---

## 4. Experiment matrix & models

**Primary model, full matrix:** 30 supergames × 20 periods per condition. The supergame is the unit of analysis.
- **Replication:** `configs/lee_baseline.yaml` (E0, E1, E2, E3a, E3b).
- **Extensions:** `configs/extensions.yaml`:
  - E0, E2, E3b (repeats; they share seeds and cache with the baseline only if the configs match, otherwise they re-run)
  - E3b neutral
  - E3b dissolve (k = 2)
  - E3b reveal explicit
  - E2 no-chat
  - E3b free reasoning
- Consider adding `{regime: E2, dissolve_on_conviction: {k: 2.0}}`.

**Second, and optionally third, model family, reduced set:** E0, E3b, E3b dissolve, E3b neutral.

**Model plan (decide by 15:30 Saturday):**
- If the Modal Qwen2.5-32B endpoint works **and** forms a cartel at E0 (Δ > 0.8), it is the primary model and is paid from credits. gpt-4.1-mini on OpenRouter becomes the second family.
- Otherwise gpt-4.1-mini is primary (about $20–30 of Tibor's money) and Modal hosts the second family.
- A Claude- or Gemini-class model as third family is the ideal contrast for H4 (WhistleBench shows those families whistleblow more). Run it only if budget allows.
- If a backend doesn't work within 30 minutes, drop it.

**Positive control (must pass before anything else):** the E0 markup index is above 0.8, **and** the reporting ladder E1 < E2 < E3a < E3b appears.

---

## 5. Timeline (Vienna time)

**Saturday Oct 24**
- **14:20–15:00:** venv, `pytest`, smoke test (OpenRouter). Start the Modal deploy in parallel. Read 5–10 transcripts and check that the JSON parses, the chat is substantive and the rulings look sane.
- **15:00:** launch the Lee baseline on the backend that passed (about 30–45 minutes).
- **15:00–17:00:** Tibor reads Lee and the Bigoni design. The agent pushes the code to a GitHub repo (cite Lee for the prompts; mark the harness as written during the sprint).
- **17:00:** Matthew Lee's talk, if it is today.
- **~17:30:** validate against Lee's Table 4 (§6). Then **freeze the hypotheses** by writing them, timestamped, into `PREREGISTRATION.md` and committing.
- **18:00:** launch the extensions on the primary model, plus the reduced set on the second family in parallel.
- **18:00–21:00:** edit the paper draft (`paper/draft.md`).
- **21:00–24:00:** `python -m leniency analyze` and `figures`; pull qualitative quotes (farming, silence pacts, evasion language); **hand-check about 30 classifier labels**.

**Sunday Oct 25**
- **10:00–12:00:** fill gaps (extra seeds where CIs are wide); robustness check (swap the authority model).
- **12:00–18:00:** write Results, Discussion, the abstract (last) and the appendix.
- **18:00–21:00:** **verify every citation by hand**; polish figures and README; optional video.
- **21:00–23:00:** submit. The buffer runs until Mon 12:59.

---

## 6. Lee's numbers (the replication targets; from Lee Table 4, 100 supergames per regime)

| | L-Faire | Fine | Leniency | Reward 1x | Reward 2x |
|---|---|---|---|---|---|
| Markup index Δ | 1.135 | 1.058 | 1.044 | 0.978 | 0.980 |
| Average price | 9.81 | 9.35 | 9.26 | 8.87 | 8.88 |
| Secret report | – | 0.001 | 0.021 | 0.064 | 0.181 |
| Public report | – | 0.000 | 0.008 | 0.025 | 0.045 |
| Any report | – | 0.001 | 0.029 | 0.089 | 0.227 |
| Conviction | – | 0.115 | 0.121 | 0.182 | 0.302 |
| Avg fine | – | 46.0 | 42.5 | 55.1 | 75.9 |
| Avg reward | – | – | – | 11.9 | 58.2 |

**Further results from Lee:**
- **Price bands, share of prices ≥ 10:** 0.787 / 0.524 / 0.665 / 0.532 / 0.569. Share ≥ 8 under Reward 2x: 0.85.
- **Event study around a report:** prices drop only 0.31–0.66 one period later.
- **Retaliation language** appears in 6–12% of post-report chats; **cooperative language** in 98–100%.
- **Reward/incentive language** appears in 540 of 930 reporter justifications.
- **Both firms reporting:** 238 cases, with an average price of 9.13.
- **Reward dose-response:** OLS slope of reporting on the reward multiplier β = 0.099 (SE 0.008).
- **Excess collusion:** 79% of prices are above 9 under L-Faire. Agents believe 10 is optimal: "178" appears 1,547 times in reasoning versus "180" 350 times.

Lee's protocol details (prompts, sequence, authority rubric) are in Lee §3. The harness reproduces his prompts verbatim, and a test asserts this.

---

## 7. The harness (`leniency/`)

**Commands:**
```bash
cd leniency && python3 -m venv .venv && source .venv/bin/activate
pip install -e . && pip install matplotlib pytest modal
python -m pytest -q                                    # 36 tests
python -m leniency check                               # payoff matrix sanity
export OPENROUTER_API_KEY=...                          # never commit
python -m leniency run configs/smoke.yaml --out runs/smoke_gpt41mini         # ~$0.25
python -m leniency run configs/lee_baseline.yaml --out runs/lee_gpt41mini
python -m leniency run configs/extensions.yaml --out runs/ext_gpt41mini
python -m leniency analyze runs/lee_gpt41mini         # Lee Table 4 + farming/quadrant/evasion
python -m leniency figures runs/ext_gpt41mini --out figures/
python -m leniency prompts --regime E3b --framing neutral --dissolve
python -m leniency budget runs/<a> runs/<b> --supergames 30 --conditions 8
```
- **Overrides on `run`:** `--model`, `--only E2,E3b`, `--supergames`, `--periods`, `--concurrency`, `--mock collude|snitch|farm|random`.
- **Resuming:** the response cache in `runs/<name>/cache.jsonl` means re-running resumes for free.
- **Usage tracking:** `usage.json` holds calls, tokens and $.

**Modal (open model on our credits):** see the docstring in `deploy/modal_vllm.py`.
```bash
modal setup
modal secret create leniency-serve LENIENCY_SERVE_KEY=<random>
SERVE_MODEL=Qwen/Qwen2.5-32B-Instruct SERVE_GPU=A100-80GB modal deploy deploy/modal_vllm.py
export LENIENCY_BASE_URL=https://<user>--leniency-vllm-serve.modal.run/v1
export LENIENCY_API_KEY=<same random>
python -m leniency run configs/smoke.yaml --model Qwen/Qwen2.5-32B-Instruct --out runs/smoke_qwen32b
modal app stop leniency-vllm     # when done
```
- **Status:** written without Modal access and **untested**. The vLLM version pin may need adjusting.
- **Cost:** an A100-80GB is roughly $2.5/h (check Modal pricing). `max_containers=1` and `scaledown_window=300` keep spend bounded.
- **Bigger model:** Llama-3.3-70B needs `SERVE_GPU=H100:2 SERVE_TP=2` and an HF token secret.

**Files:**
- `payoffs.py`: the Bigoni matrix, verified against its closed form. π(3,3) = 100, π(9,9) = 180, π(10,10) = 178, the best response to 9 is 7 (payoff 296), and the unique Nash equilibrium is (3,3).
- `prompts.py`: Lee's prompts verbatim, plus our neutral framing, market-rules text and classifier.
- `game.py`: the period loop and `settle()`.
- `config.py`: regimes and flags.
- `llm.py`: stdlib HTTP client, cache, cost accounting and mocks.
- `runner.py`: concurrency.
- `analysis.py`: Lee's Table 4, farming metrics, say/do quadrant, evasion and the event study.
- `figures.py`: fig1 ladder, fig2 farming arithmetic vs observed, fig3 event study after conviction, fig4 say/do quadrant.
- `budget.py`, `cli.py`.

**Choices where Lee is silent (state these in Methods; full table in `leniency/README.md`):**
- The regime "market rules" text is ours.
- The payoff-table layout is ours.
- E0 has no report option.
- The reward goes only to a *sole* reporter, and only on a guilty ruling.
- An audit conviction with no report fines both firms F.
- The first speaker is redrawn every period.
- Temperatures: agents 1.0; authority and classifier 0.
- **Flag:** Lee's 40-period history window never binds with 20-period supergames.

**Known caveats:**
- The ground-truth classifier is an LLM. Hand-check about 30 labels (METR's incident report found AI analysts unreliable).
- One "cartel episode" ends when the classifier labels a chat "none", which matters for `once_per_episode`.
- E3b dissolve uses a bundle of changes (once-per-episode + repeat-offender-ineligible + monitoring + k = 2). If time allows, ablate them using the commented-out cells in `extensions.yaml`.

---

## 8. Planned figures & tables
- **Table 1:** Lee's Table 4 replicated, ours next to Lee's, per model.
- **Fig 1:** report rate (bars) and average price (line) by regime, like Lee's Fig 2.
- **Fig 2:** farming arithmetic (theoretical payoff by regime) next to the observed farming index.
- **Fig 3:** event study of price around the first conviction, Lee's rules vs dissolve. This is the money figure for H3.
- **Fig 4:** say/do quadrant (direct / attempted / hidden / benign) by regime, for H5.
- **Qualitative box:** quotes showing farming, silence pacts and "stay under the radar" language.

---

## 9. Budget
- The mock-measured cost is about 165 calls and about 170k input tokens per supergame.
- **One full 8-condition × 30-supergame matrix:**
  - gpt-4.1-mini: about **$20–22**
  - gpt-4o-mini: about $7–8
  - qwen3-14b (thinking off) or llama-3.3-70b on OpenRouter: about $5–7
  - These list prices are unverified.
- The Lee baseline (5 × 30) costs about 60% of that.
- **Total plan:** about $50–80 including a second family, mostly covered by Modal credits if Qwen works.
- **Check `usage.json` after the smoke test and re-estimate before big runs.**
- The `--concurrency` default of 8 is safe. Raise it if there are no rate-limit errors.

---

## 10. Reading list (priority order)

**Must read:**
1. **Lee (2026)**, `papers/Lee_2026_LLM_Leniency_and_Reward_Experiment.pdf`, especially §3, §5 and §6.
2. **Bigoni, Fridolfsson, Le Coq & Spagnolo (2012)**, "Fines, Leniency, and Rewards in Antitrust", RAND J. Econ 43(2):368–390. WP: https://www.ifn.se/wfiles/wp/wp738.pdf
   - Humans: cartel formation 0.716 (L-Faire), 0.315 (Fine), 0.178 (Leniency), 0.220 (Reward).
   - Average price 4.92 / 5.35 / 4.85 / 3.97.
   - Reward is the only regime that improves welfare.
3. **Nakamura, Bagdasarian et al., Colosseum**: https://arxiv.org/abs/2602.15198. Source of the say/do typology and of "collusion on paper". The talk transcript is in `notes/`.
4. **Idowu et al. (2026)**, "Mapping Human Anti-collusion Mechanisms to Multi-agent AI Systems": https://arxiv.org/abs/2601.00360, §3.2. It proposes leniency for AI agents and warns of "taking turns colluding and then reporting to harvest immunity rewards", which is our H2. Cite it as the explicit call for this experiment.
5. **Fish, Gonczarowski & Shorrer (2024)**, "Algorithmic Collusion by LLMs": https://arxiv.org/abs/2404.00806

**Should read (abstracts and key results):**
6. Spagnolo (2004), "Divide et Impera: Optimal Leniency Programmes", CEPR DP 4840: https://ideas.repec.org/p/cpr/ceprdp/4840.html. Rewards beat amnesty in theory.
7. Andres, Bruttel & Friedrichsen (2021), IJIO 76:102728, doi:10.1016/j.ijindorg.2021.102728. **With free chat, leniency has no effect on humans.**
8. Apesteguia, Dufwenberg & Selten (2007), "Blowing the Whistle", Economic Theory 31:143–166. Humans use reporting as punishment.
9. Harrington (2018), "Developing Competition Law for Collusion by Autonomous Artificial Agents", J. Competition Law & Econ 14(3):331–363. With no agreement there is nothing to report (H6).
10. Agrawal, Xiao, Bergman, Cooper Stickland, "Why Do Language Model Agents Whistle-blow?" (WhistleBench): https://arxiv.org/abs/2511.17085. Whistleblowing varies by family (H4).
11. Liu et al. (2026), "Breaking the Secret: Economic Interventions for Combating Collusion in Embodied Multi-Agent Systems": https://arxiv.org/abs/2604.23511. The closest LLM reporting-reward mechanism, in a non-market setting. Explain how we differ.
12. Hinloopen & Soetevent (2008), RAND J. Econ 39(2):607–616. With leniency, 78% of cartels were reported; cartel formation went 47% → 13%.

**Context for the introduction:**
13. METR, OpenAI/Hugging Face incident investigation: https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/
14. UK CMA blog (4 Mar 2026), leniency and informant rewards extended to algorithmic collusion: https://competitionandmarkets.blog.gov.uk/2026/03/04/ai-and-collusion-frontiers-opportunities-and-challenges/
15. Hammond et al. (2025), "Multi-Agent Risks from Advanced AI": https://arxiv.org/abs/2502.14143
16. Calvano, Calzolari, Denicolò & Pastorello (2020), AER 110(10):3267–97.
17. Agrawal et al. (2025), "Evaluating LLM Agent Collusion in Double Auctions": https://arxiv.org/abs/2507.01413

Items 13–15 were not opened by hand yet. **Every citation must be opened and checked before submission.** A condensed literature review is in `notes/literature_review.md`.

---

## 11. Paper outline (target 5–6 pages)
1. **Introduction.** LLM pricing plus leniency as the main antitrust tool. Lee's negative result. Our question: agents or mechanism? Contributions: replication across families, the farming diagnosis, realistic leniency, the framing control, displacement. Close on the stakes for AI oversight: reward-for-reporting schemes among AI agents can be gamed.
2. **Related work.** Human leniency experiments; LLM and algorithmic collusion; LLM whistleblowing; mechanisms against multi-agent collusion (Idowu, Liu).
3. **Methods.** Lee's environment, our extensions, measures, models and statistics (supergame as the unit; Mann–Whitney, Jonckheere–Terpstra, as in Lee).
4. **Results.** H1–H6 in order, with Figs 1–4.
5. **Discussion.** For each outcome, which interpretation it supports. Policy lesson: rewards must be one-shot and tied to cartel dissolution.
- **Appendix A: Limitations and Dual-Use.**
  - LLM classifier and authority used as instruments.
  - Few models; short horizons.
  - Results inform both regulators and potential gamers of oversight. The farming insight itself is a known theoretical risk (Idowu; Spagnolo's "perverse effects").
- **LLM usage statement.** Claude was used for literature search, code and drafting; all results were run and checked by the author.

---

## 12. Open items / risks
- [ ] Smoke test against a real model, then a transcript sanity check.
- [ ] Modal deploy works (vLLM pin, cold-start time).
- [ ] Positive control passes. If E0 doesn't collude with the chosen model, switch models (gpt-4.1-mini is the safest bet).
- [ ] Reconcile the E3a farming arithmetic (170 vs 180).
- [ ] Decide whether to state the 40-period history choice as is or contact Lee.
- [ ] Ask on Discord about Nebius credits.
- [ ] Create the GitHub repo. Do not commit `runs/` with large caches (add them to `.gitignore`, or commit only `periods.jsonl` and the analysis).
- [ ] Verify all citations by hand.
