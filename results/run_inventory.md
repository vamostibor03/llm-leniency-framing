# Run inventory and API cost

| run | agent model | conditions | supergames done | failed | API calls | input tokens | output tokens | est. cost ($) |
|---|---|---|---|---|---|---|---|---|
| smoke_gpt41mini | openai/gpt-4.1-mini | E0, E2, E2_chat-none, E3b, E3b_dissolve, E3b_neutral, E3b_reason-free, E3b_reveal-explicit | 16 | 2 | 560 | 605,716 | 50,042 | 0.32 |
| lee_gpt41mini | openai/gpt-4.1-mini | E0, E1, E2, E3a, E3b | 150 | 0 | 26,618 | 32,946,390 | 1,579,067 | 15.71 |
| screen_gpt4omini | openai/gpt-4o-mini | E0, E1, E3b | 50 | 0 | 8,776 | 10,684,892 | 521,939 | 2.24 |
| screen_qwen3_14b | qwen/qwen3-14b | E0, E1, E3b | 30 | 0 | 4,893 | 7,040,436 | 294,466 | 1.09 |
| screen_llama33_70b | meta-llama/llama-3.3-70b-instruct | E0, E1, E3b | 30 | 0 | 5,077 | 6,965,548 | 418,931 | 1.04 |
| lee_llama33_70b | meta-llama/llama-3.3-70b-instruct | E0, E1, E2, E3a, E3b | 150 | 0 | 26,105 | 36,198,732 | 2,216,163 | 5.40 |
| screen_gemini35fl | google/gemini-3.5-flash-lite | E0, E1, E3b | 40 | 0 | 6,555 | 8,017,133 | 436,284 | 3.43 |
| screen_haiku55 | anthropic/claude-haiku-5.5 | E0, E1, E3b | 30 | 0 | 5,069 | 7,600,995 | 575,154 | 1.21 |
| lee_haiku55 | anthropic/claude-haiku-5.5 | E0, E1, E2, E3a, E3b | 149 | 1 | 21,172 | 32,320,102 | 2,474,002 | 5.14 |
| reflex_gpt4omini | openai/gpt-4o-mini | E1_neutral, E3b_neutral | 40 | 0 | 6,402 | 7,782,977 | 329,823 | 1.61 |
| reflex_gpt41mini | openai/gpt-4.1-mini | E1_neutral | 20 | 0 | 3,519 | 4,283,836 | 200,713 | 2.03 |
| reflex_gemini35fl | google/gemini-3.5-flash-lite | E1_neutral | 20 | 0 | 3,713 | 4,511,806 | 244,867 | 1.93 |
| reflex_llama33_70b | meta-llama/llama-3.3-70b-instruct | E1_neutral | 20 | 0 | 3,480 | 4,653,886 | 288,947 | 0.74 |
| reflex_haiku55 | anthropic/claude-haiku-5.5 | E1_neutral | 19 | 1 | 3,683 | 5,696,211 | 481,902 | 0.92 |
| confirm_haiku55 | anthropic/claude-haiku-5.5 | E3b_neutral | 16 | 4 | 3,723 | 5,894,914 | 604,453 | 1.01 |
| confirm_llama33_70b | meta-llama/llama-3.3-70b-instruct | E3b_neutral | 20 | 0 | 3,244 | 4,371,799 | 279,353 | 0.74 |

**Total estimated API cost of the game runs: $44.56**, plus the comprehension probe (400 calls, not metered; under $0.20 at these prices).

Failed = supergames aborted on repeated unparseable replies and excluded (lee_haiku55: 1 after a re-run with more retries recovered 6 of 7; see PREREGISTRATION.md §0). `smoke_gpt41mini` used 4-period supergames.
Prices: OpenRouter list prices on 2026-10-25; agents use the agent model, authority and classifier use gpt-4.1-mini. `screen_llama33_70b` was not pinned to a provider, so its cost is a lower bound.
