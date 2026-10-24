# Literature review (condensed): verify every item before citing

Status key:
- **V**: a research agent fetched the item's page and checked title, authors and venue.
- **B**: only the bibliographic details were checked; the summary comes from model knowledge.
- **?**: not verified.

## Direct precedent
- **V. Lee, J.Y. (2026), "LLM Leniency and Reward Experiment"**, SSRN 7426061, Pusan National University. The PDF is in `papers/`. Ports Bigoni et al. (2012) to LLM firms. Reporting rises from 0 to 0.227, the average price only falls from 9.81 to 8.88, and there is no retaliation. Uses one model (unnamed) and one seed. Reasoning is limited to one sentence. Coins "excess collusion" for agents anchoring on price 10.

## Human leniency experiments (the baseline for comparison)
- **V. Bigoni, Fridolfsson, Le Coq & Spagnolo (2012)**, RAND J. Econ 43(2):368–390. WP: https://www.ifn.se/wfiles/wp/wp738.pdf
  - Design: differentiated Bertrand duopoly with prices 0–12, Nash 3, joint maximum 9; α = 0.1, F = 200.
  - Cartel formation: 0.716 / 0.315 / 0.178 / 0.220 (L-Faire / Fine / Leniency / Reward).
  - Average price: 4.92 / 5.35 / 4.85 / 3.97.
  - Secret report given own deviation: 0.002 / 0.704 / 0.905.
  - Under Reward, 118 of 120 cartels were reported in their first period.
- **V. Bigoni et al. (2015)**, "Trust, Leniency and Deterrence", JLEO 31(4):663–689. Under leniency, deterrence works through distrust; 64% of secret reports were made jointly.
- **V. Apesteguia, Dufwenberg & Selten (2007)**, "Blowing the whistle", Economic Theory 31:143–166. One-shot, 3 firms. Reporting follows deviation and is used as punishment.
- **V. Hinloopen & Soetevent (2008)**, RAND J. Econ 39(2):607–616. Cartel formation 47.3% (Communication), 27.3% (Antitrust), 12.9% (Leniency); 78% of cartels reported under leniency.
- **V. Andres, Bruttel & Friedrichsen (2021)**, IJIO 76:102728. **With free-form chat, leniency has no effect** (cartelisation 0.34 vs 0.32).
- **V. Feltovich & Hamaguchi (2018)**, Southern Econ J 84(4). **V. Kim & Noussair (2023)**, Rev Ind Org 63(2). **V. Clemens & Rau (2014)**, DICE DP 130. **V. Landeo & Spier (2018)**, NBER WP 25094 ("race to the courthouse"). **V. Law, Lai & Liu (2025)**, EJLE 59(1), on external validity.

## Theory
- **V. Motta & Polo (2003)**, IJIO 21(3):347–379. Leniency can destabilise cartels but also lowers the expected cost of collusion.
- **V. Spagnolo (2004)**, "Divide et Impera", CEPR DP 4840. "Courageous" reward programs reach the first-best.
- **V. Spagnolo (2008)**, "Leniency and Whistleblowers in Antitrust", Handbook of Antitrust Economics (MIT Press).
- **V. Buccirossi & Spagnolo (2006)**, J Public Econ 90(6–7). Moderate leniency can have perverse effects.
- **V. Harrington (2008)**, J Ind Econ 56(2):215–246. **V. Harrington & Chang (2015)**, J Law & Econ 58(2). Leniency can produce *more* cartels.
- **B. Chen & Rey (2013)**, J Law & Econ 56(4). Repeat offenders should be excluded from leniency.
- **B. Aubert, Rey & Kovacic (2006)**, IJIO 24(6).
- **V. Harrington (2018)**, J Competition Law & Econ 14(3):331–363. Autonomous agents leave no "meeting of minds" and so nothing to report.

## Algorithmic and LLM collusion
- **V. Calvano, Calzolari, Denicolò & Pastorello (2020)**, AER 110(10):3267–97. Q-learning agents collude.
- **V. Fish, Gonczarowski & Shorrer (2024)**, arXiv 2404.00806. LLM pricing agents collude, and prompt wording matters.
- **V. Agrawal et al. (2025)**, arXiv 2507.01413. Double auction: chat increases collusion and oversight reduces it.
- **V. Keppo et al. (2026)**, arXiv 2603.20281, "On the Fragility of AI Agent Collusion".
- **V. Anto & Vazquez (ICML 2026)**, "Oversight is Not Compliance", https://icml.cc/virtual/2026/67865. Includes a self-disclosure flag but no incentivised leniency.
- **V. Garra (2026)**, arXiv 2609.13037, mitigations for LLM pricing agents (no leniency).
- **V. Bracale Syrnikov et al. (2026)**, arXiv 2601.11369, governance graphs in Cournot markets (no leniency).
- **V. Tran & Yu (2026)**, arXiv 2610.28787, on cartel enforcement and RL.
- **V. Lee (2026b)**, "Who Leads and Who Collects", arXiv 2610.11256, Bertrand markets across providers.

## Mechanisms against multi-agent AI collusion
- **V. Idowu, Almasoud & Alfahid (2026)**, arXiv 2601.00360. A conceptual taxonomy that includes leniency and whistleblowing. It explicitly warns about "taking turns colluding and then reporting to harvest immunity rewards" (our H2). **Cite it as the call for this experiment.**
- **V. Liu et al. (2026)**, "Breaking the Secret", arXiv 2604.23511. Deposits plus a reward to the first reporter for embodied LLM agents. No market, no antitrust framing, no farming analysis.

## Say vs do, detection, oversight
- **V. Nakamura, Bagdasarian et al. (2026)**, Colosseum, arXiv 2602.15198, code https://github.com/umass-ai-safety/colosseum. Collusion types: direct, attempted ("on paper"), hidden. Shows an LLM judge alone is insufficient.
- **V. Shi, Zhang, Schölkopf, Conitzer & Jin (2026)**, "When Agents Lie", arXiv 2607.05132. Plan, announce, act; over 90% of deviations were premeditated.
- **V. Rose et al. (2026)**, NARCBench, arXiv 2604.01151. Activation probes for detecting collusion.

## LLM whistleblowing (for H4)
- **V. Agrawal, Xiao, Bergman & Cooper Stickland**, WhistleBench, arXiv 2511.17085 (ICLR 2026 workshop). Claude, Gemini 2.5 Pro and Grok 4 whistleblow; GPT models and Llama 4 do not. Moral nudges increase whistleblowing.
- **V. Paglieri et al. (2026)**, arXiv 2609.04170. Emergent whistleblowing in research swarms.
- **?** Claude Opus 4 system card on "high-agency" behaviour (seen only via Simon Willison's blog).
- SnitchBench: https://github.com/t3dotgg/SnitchBench

## Policy / real-world context
- **V. UK CMA blog (4 Mar 2026)**: https://competitionandmarkets.blog.gov.uk/2026/03/04/ai-and-collusion-frontiers-opportunities-and-challenges/ Leniency extended to algorithmic information exchange; informant reward of up to £250k.
- **?** METR, OpenAI/Hugging Face incident: https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/ About 1,200 agents used a cache as a message board; about 700 joined the intrusion.
- **V. Hammond et al. (2025)**, "Multi-Agent Risks from Advanced AI", arXiv 2502.14143.
- **V.** DOJ Antitrust and USPS whistleblower rewards (Jul 2025), 15–30% of fines. **V.** EU leniency: immunity for the first applicant, then reductions of 30–50%, 20–30%, and up to 20%. **V.** Korea KFTC (Jun 2026), reward of 10% of the fine.
