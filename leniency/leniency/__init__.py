"""LLM leniency experiment: a faithful, extensible harness of Lee (SSRN 7426061),
"LLM Leniency and Reward Experiment", itself built on Bigoni et al. (2012).

Modules:
    payoffs   Bigoni Table 1 payoff matrix + sanity checks
    config    regimes E0-E3b, extension flags (framing, chat, reasoning, reveal, post-conviction)
    prompts   Lee's prompts verbatim + our regime rules text + extension edits
    llm       OpenAI-compatible backend (stdlib only), MockLLM, cache, cost accounting
    game      one supergame (period loop, settlement)
    runner    concurrent conditions x supergames, resumable JSONL output
    analysis  Lee's Table 4 metrics + bounty farming, event study, silence pacts
    budget    calls / tokens / $ estimates
    cli       ``python -m leniency {run,analyze,budget,check}``
"""

__version__ = "0.1.0"
