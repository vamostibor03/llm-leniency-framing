"""Bigoni et al. (2012) Table 1 payoff matrix, as used by Lee (SSRN 7426061).

``PAYOFF[own][competitor]`` is a firm's per-period profit when it sets ``own`` and the
competitor sets ``competitor`` (integer prices 0..12). The matrix is symmetric in the game
sense: firm B's profit is ``PAYOFF[p_B][p_A]``.

Every entry is reproduced exactly by a linear differentiated-Bertrand demand with a
capacity (monopoly-demand) cap, rounded to the nearest integer::

    q_i = max(0, min(72 - 4 p_i,  40 - (100/9) p_i + (80/9) p_j))
    pi_i = round(p_i * q_i)

``verify_matrix()`` checks this, together with the benchmarks quoted by Lee:
unique pure-strategy Nash equilibrium (3, 3) with profit 100 each, joint-profit
maximum (9, 9) with 180 each, markup index Delta = (mean price - 3) / 6.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

PRICES: Tuple[int, ...] = tuple(range(13))
NASH_PRICE = 3
JPM_PRICE = 9  # joint-profit-maximising (collusive) price

PAYOFF: Tuple[Tuple[int, ...], ...] = (
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (29, 38, 47, 56, 64, 68, 68, 68, 68, 68, 68, 68, 68),
    (36, 53, 71, 89, 107, 124, 128, 128, 128, 128, 128, 128, 128),
    (20, 47, 73, 100, 127, 153, 180, 180, 180, 180, 180, 180, 180),
    (0, 18, 53, 89, 124, 160, 196, 224, 224, 224, 224, 224, 224),
    (0, 0, 11, 56, 100, 144, 189, 233, 260, 260, 260, 260, 260),
    (0, 0, 0, 0, 53, 107, 160, 213, 267, 288, 288, 288, 288),
    (0, 0, 0, 0, 0, 47, 109, 171, 233, 296, 308, 308, 308),
    (0, 0, 0, 0, 0, 0, 36, 107, 178, 249, 320, 320, 320),
    (0, 0, 0, 0, 0, 0, 0, 20, 100, 180, 260, 324, 324),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 89, 178, 267, 320),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 73, 171, 269),
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 53, 160),
)


def profit(own: int, competitor: int) -> int:
    """Per-period profit of a firm pricing ``own`` against ``competitor``."""
    return PAYOFF[own][competitor]


def markup_index(mean_price: float) -> float:
    """Lee's Delta: 0 at the Nash price (3), 1 at the joint-profit maximum (9)."""
    return (mean_price - NASH_PRICE) / (JPM_PRICE - NASH_PRICE)


def linear_demand_profit(own: int, competitor: int) -> float:
    """Unrounded profit from the demand system that generates the table."""
    q = max(0.0, min(72 - 4 * own, 40 - 100 / 9 * own + 80 / 9 * competitor))
    return own * q


def best_responses(competitor: int) -> List[int]:
    col = [PAYOFF[p][competitor] for p in PRICES]
    best = max(col)
    return [p for p in PRICES if col[p] == best]


def verify_matrix() -> Dict[str, object]:
    """Sanity checks; every value in the returned dict should be truthy / as documented."""
    mismatches = [
        (i, j)
        for i in PRICES
        for j in PRICES
        if round(linear_demand_profit(i, j)) != PAYOFF[i][j]
    ]
    pure_ne = [
        (i, j) for i in PRICES for j in PRICES if i in best_responses(j) and j in best_responses(i)
    ]
    joint = max(((PAYOFF[i][j] + PAYOFF[j][i]), i, j) for i in PRICES for j in PRICES)
    return {
        "shape_13x13": len(PAYOFF) == 13 and all(len(r) == 13 for r in PAYOFF),
        "formula_mismatches": mismatches,  # expect []
        "pi(3,3)": PAYOFF[3][3],  # expect 100
        "pi(9,9)": PAYOFF[9][9],  # expect 180
        "pi(10,10)": PAYOFF[10][10],  # 178: Lee's "excess collusion at 10" is a near-tie
        "pure_nash_equilibria": pure_ne,  # expect [(3, 3)]
        "joint_profit_max": joint,  # expect (360, 9, 9)
        "best_response_to_9": best_responses(9),  # [7] -> 296: the deviation temptation
        "nondecreasing_in_competitor_price": all(
            all(PAYOFF[r][c] <= PAYOFF[r][c + 1] for c in range(12)) for r in PRICES
        ),
    }


def format_payoff_table() -> str:
    """The table as shown to agents (layout is ours; Lee does not publish his formatting)."""
    header = "Your price \\ Competitor price | " + " ".join(f"{c:>4d}" for c in PRICES)
    lines = [
        "PAYOFF TABLE (your profit this period; rows = YOUR price, columns = COMPETITOR's price):",
        header,
        "-" * len(header),
    ]
    for p in PRICES:
        lines.append(f"{'Your price ' + str(p):<29} | " + " ".join(f"{v:>4d}" for v in PAYOFF[p]))
    return "\n".join(lines)


if __name__ == "__main__":  # python -m leniency.payoffs
    for k, v in verify_matrix().items():
        print(f"{k:36s} {v}")
    print()
    print(format_payoff_table())
