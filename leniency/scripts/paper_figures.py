"""Paper figures, drawn only from run outputs.

    python scripts/paper_figures.py              # writes ../paper/figures/fig{1,2,3}.{png,pdf}

fig1  H5c: explicit-agreement share and markup Δ, E3b legal vs neutral (Haiku, Llama), per supergame.
fig2  H1: E1 any-report rate, legal vs neutral framing, five families (dumbbell).
fig3  Baselines: any-report rate by regime for the three families with a full Lee baseline, with Lee's
      published values (Lee 2026, Table 4) as a reference line.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from confirm_analysis import PRIMARY  # noqa: E402
from reflex_analysis import cell, delta, matched, per_sg, rows  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "paper" / "figures"
LEGAL, NEUTRAL = "#2a78d6", "#eb6834"          # categorical slots 1-2 (validated: CVD ΔE 24.7)
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.dpi": 200})


def strip(ax, x, vals, color, label=None):
    rng = np.random.default_rng(0)
    ax.scatter(x + rng.uniform(-0.09, 0.09, len(vals)), vals, s=14, color=color, alpha=0.45, linewidths=0, zorder=2)
    m = np.mean(vals)
    se = np.std(vals, ddof=1) / np.sqrt(len(vals))
    ax.vlines(x, m - 1.96 * se, m + 1.96 * se, color=color, lw=2, zorder=3)
    ax.scatter([x], [m], s=64, color=color, edgecolor=SURFACE, lw=2, zorder=4, label=label)
    return m


def fig1():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    explicit = lambda r: r.get("agreement") == "explicit"
    for k, (fam, ((lr, lc), (nr, nc))) in enumerate(PRIMARY.items()):
        L, N = rows(lr, lc), rows(nr, nc)
        for ax, f in zip(axes, (explicit, delta)):
            a, b = matched(per_sg(L, f), per_sg(N, f))
            strip(ax, k * 1.0 - 0.17, a, LEGAL, "legal framing" if k == 0 else None)
            strip(ax, k * 1.0 + 0.17, b, NEUTRAL, "neutral framing" if k == 0 else None)
    names = [f.replace("claude-", "Claude ").replace("llama-3.3-70b", "Llama-3.3-70B").replace("haiku-5.5", "Haiku 5.5")
             for f in PRIMARY]
    for ax, title, ylab in zip(axes, ("A  Chats with an explicit agreement", "B  Markup index Δ"),
                               ("share of periods (classifier)", "Δ = (p̄ − 3) / 6")):
        ax.set_xticks([0, 1], names)
        ax.set_xlim(-0.6, 1.6)
        ax.set_title(title, loc="left", fontsize=9.5, color=INK, fontweight="bold")
        ax.set_ylabel(ylab)
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylim(0, 1)
    axes[1].set_ylim(0.4, 1.2)
    axes[1].axhline(1, color=MUTED, lw=0.8, ls=(0, (3, 3)))
    axes[1].text(1.58, 1.01, "joint-profit max", ha="right", va="bottom", fontsize=7.5, color=MUTED)
    axes[0].legend(frameon=False, loc="upper left", fontsize=8)
    fig.tight_layout()
    save(fig, "fig1")


def fig2():
    fams = ["gpt-4o-mini", "gemini-3.5-flash-lite", "gpt-4.1-mini", "llama-3.3-70b", "claude-haiku-5.5"]
    fig, ax = plt.subplots(figsize=(5.6, 2.5))
    for y, fam in enumerate(fams):
        _, rl, _, _ = cell(fam, "legal", "E1")
        _, rn, _, _ = cell(fam, "neutral", "E1")
        a, b = matched(rl, rn)
        ml, mn = np.mean(a), np.mean(b)
        ax.plot([ml, mn], [y, y], color=GRID, lw=3, zorder=1, solid_capstyle="round")
        ax.scatter([ml], [y], s=60, color=LEGAL, edgecolor=SURFACE, lw=2, zorder=3, label="legal framing" if y == 0 else None)
        ax.scatter([mn], [y], s=60, color=NEUTRAL, edgecolor=SURFACE, lw=2, zorder=3, label="neutral framing" if y == 0 else None)
        if abs(ml - mn) < 0.03:
            ax.text(max(ml, mn) + 0.03, y, f"legal {ml:.3f}, neutral {mn:.3f}", va="center", fontsize=7.5, color=MUTED)
    ax.set_yticks(range(len(fams)), fams)
    ax.invert_yaxis()
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("E1 (fine only): share of periods with a report")
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    fig.tight_layout()
    save(fig, "fig2")


def fig3():
    base = pd.read_csv(OUT.parents[1] / "results" / "table_baselines.csv")
    regs = ["E1", "E2", "E3a", "E3b"]
    lee = [0.001, 0.029, 0.089, 0.227]  # Lee (2026), Table 4, "Any report"
    fams = [("gpt-4.1-mini", "#1baf7a", "o"), ("llama-3.3-70b", "#6250d6", "s"), ("claude-haiku-5.5", "#eda100", "D")]
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    x = np.arange(len(regs))
    ax.plot(x, lee, color=MUTED, lw=1.5, ls=(0, (4, 3)), marker="o", ms=4, label="Lee (2026), unnamed model")
    for fam, col, mk in fams:
        g = base[(base.family == fam) & base.cond.isin(regs)].set_index("cond").loc[regs]
        ax.vlines(x, g.report - 1.96 * g.report_se, g.report + 1.96 * g.report_se, color=col, lw=1.5)
        ax.plot(x, g.report, color=col, lw=2, marker=mk, ms=6, mec=SURFACE, mew=1.5, label=fam)
    ax.set_xticks(x, ["E1\nfine", "E2\nleniency", "E3a\nreward 1F", "E3b\nreward 2F"])
    ax.set_ylabel("share of periods with a report")
    ax.set_ylim(0, 0.85)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2)
    fig.tight_layout()
    save(fig, "fig3")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / f"{name}.png")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
