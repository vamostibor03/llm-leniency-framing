"""The four planned paper figures, from one run directory or a directory of runs.

    python -m leniency figures runs/                 # every runs/*/periods.jsonl, pooled
    python -m leniency figures runs/mock_farm --out figs/
    python -m leniency figures --from-csv figs/      # re-plot from the CSVs written earlier

Figures (PNG + PDF, plus the CSV each one is drawn from):
    fig1_ladder        report rate (bars, top) and average price (line, bottom) by regime, Lee
                       baseline cells only (our version of Lee Fig. 2; two panels, not two y-axes)
    fig2_farming       left: theoretical per-firm per-period payoff at (9,9) of silent collusion vs
                       alternating sole reporting under each rule set; right: observed farming index
    fig3_event         average market price around the FIRST conviction, Lee rules vs the
                       dissolve-on-conviction bundle (falls back to all enforcement cells)
    fig4_saydo         say-vs-do quadrant: chat-based collusion (classifier agreement rate) vs
                       action-based collusion (share of prices >= 8), one point per condition x model

When several runs are pooled, the model id identifies a series (at most 4). A (model, condition)
cell found in several runs is pooled (supergame ids offset per run); ``--no-pool`` keeps them
apart as ``condition@run``.
If matplotlib is missing, only the CSVs are written; re-plot later with ``--from-csv``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import analysis as A

# Reference palette (validated: adjacent and all-pairs for the first three slots, light mode).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e6e5e1", "#fcfcfb"
MARKERS = ["o", "s", "^", "D"]
REGIME_ORDER = ["E0", "E1", "E2", "E3a", "E3b"]
MAX_SERIES = 4
RUN_OFFSET = 100_000  # supergame id offset per pooled run

CSV_NAMES = ("fig1_ladder", "fig2_theory", "fig2_observed", "fig3_event", "fig4_saydo", "fig4_supergames")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def load_runs(path: str | Path, pool: bool = True) -> pd.DataFrame:
    """One run dir (has periods.jsonl) or a parent dir of runs. Adds ``run`` and ``model``.

    The same (model, condition) cell found in several runs (e.g. E0/E2/E3b in both
    ``lee_baseline`` and ``extensions``) is pooled by default: it is the same treatment, and
    supergame ids are offset per run so that supergames are never merged. With ``pool=False``
    such cells are kept apart and renamed ``condition@run``."""
    path = Path(path)
    dirs = [path] if (path / "periods.jsonl").exists() else sorted(
        d for d in path.iterdir() if (d / "periods.jsonl").exists())
    if not dirs:
        raise FileNotFoundError(f"no periods.jsonl in {path} or its subdirectories")
    frames = []
    for i, d in enumerate(dirs):
        df = A.add_model_column(A.load_periods(d))
        df["run"] = d.name
        df["supergame_in_run"] = df.supergame
        df["supergame"] = df.supergame + RUN_OFFSET * i
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    owners = df.groupby(["model", "condition"]).run.nunique()
    dup = set(owners[owners > 1].index)
    if dup and not pool:
        mask = [(m, c) in dup for m, c in zip(df.model, df.condition)]
        df.loc[mask, "condition"] = df.loc[mask, "condition"] + "@" + df.loc[mask, "run"]
    elif dup:
        print("figures: pooling cells found in several runs: "
              + ", ".join(f"{m}/{c}" for m, c in sorted(dup)))
    return df


def _cond_order(df: pd.DataFrame) -> List[str]:
    first = df.drop_duplicates("condition")
    key = {c: (REGIME_ORDER.index(r) if r in REGIME_ORDER else 9, 0 if bool(lb) else 1, c)
           for c, r, lb in zip(first.condition, first.regime, first.get("flag_lee_baseline", True))}
    return sorted(key, key=key.get)


def _models(df: pd.DataFrame) -> List[str]:
    ms = list(dict.fromkeys(df.model))
    if len(ms) > MAX_SERIES:
        print(f"figures: {len(ms)} models; plotting the first {MAX_SERIES} ({', '.join(ms[:MAX_SERIES])})")
    return ms[:MAX_SERIES]


# --------------------------------------------------------------------------- #
# Figure data (pure pandas; tested without matplotlib)
# --------------------------------------------------------------------------- #


def _se(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else np.nan


def figure_data(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    models = _models(df)
    df = df[df.model.isin(models)]
    order = _cond_order(df)
    sg_parts = []
    for m in models:
        sgm = A.supergame_table(df[df.model == m])
        sgm.insert(0, "model", m)
        sg_parts.append(sgm)
    sg = pd.concat(sg_parts, ignore_index=True)
    lb = df.groupby("condition")["flag_lee_baseline"].first() if "flag_lee_baseline" in df else pd.Series(True, index=order)

    # fig 1: Lee ladder (baseline cells)
    rows = []
    for (m, c), g in sg.groupby(["model", "condition"], sort=False):
        if not bool(lb.get(c, True)):
            continue
        rows.append({"model": m, "condition": c, "regime": g.regime.iloc[0], "n": len(g),
                     "report_rate": g.any_report_rate.mean(), "report_rate_se": _se(g.any_report_rate),
                     "avg_price": g.avg_price.mean(), "avg_price_se": _se(g.avg_price)})
    f1 = pd.DataFrame(rows)

    # fig 2: theory + observed farming index
    f2t = A.farming_arithmetic_table(int(df.period.max()))
    f2t = f2t[f2t.rules != "E0"].reset_index(drop=True)
    rows = []
    for (m, c), g in sg.groupby(["model", "condition"], sort=False):
        if g.regime.iloc[0] == "E0":
            continue
        rows.append({"model": m, "condition": c, "regime": g.regime.iloc[0], "n": len(g),
                     "farming_index": g.farming_index.mean(), "farming_index_se": _se(g.farming_index),
                     "avg_payoff": g.avg_payoff.mean(), "avg_payoff_se": _se(g.avg_payoff)})
    f2o = pd.DataFrame(rows)

    # fig 3: event study around the first conviction, Lee rules vs dissolve
    first = df.drop_duplicates("condition").set_index("condition")
    dissolve = [c for c in order if bool(first.loc[c].get("flag_pc_once_per_episode", False))
                or bool(first.loc[c].get("flag_pc_repeat_offender_ineligible", False))]
    pairs = []
    for c in dissolve:
        reg = first.loc[c, "regime"]
        base = [b for b in order if first.loc[b, "regime"] == reg and bool(first.loc[b].get("flag_lee_baseline", False))]
        pairs += [*base[:1], c]
    sel = list(dict.fromkeys(pairs)) or [c for c in order if first.loc[c, "regime"] not in ("E0",)
                                         and bool(first.loc[c].get("flag_lee_baseline", True))]
    parts = []
    for m in models:
        ev = A.event_study(df[(df.model == m) & df.condition.isin(sel)], window=(-3, 5), event="conviction")
        if len(ev):
            ev.insert(0, "model", m)
            ev["rules"] = ev.condition.map(lambda c: "dissolve" if c in dissolve else "Lee rules")
            ev["regime"] = ev.condition.map(first.regime)
            parts.append(ev)
    f3 = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["model", "condition", "k", "price", "price_se", "agreement", "n", "rules", "regime"])

    # fig 4: say vs do
    sgx = A.ext_supergame_table(df)
    f4 = A.say_do_table(sgx)
    f4s = sgx[["model", "condition", "regime", "supergame", "say_rate", "high_share", "delta", "quadrant"]]
    return {"fig1_ladder": f1, "fig2_theory": f2t, "fig2_observed": f2o, "fig3_event": f3,
            "fig4_saydo": f4, "fig4_supergames": f4s}


# --------------------------------------------------------------------------- #
# Plotting
# --------------------------------------------------------------------------- #


def _style(plt):
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
        "lines.linewidth": 2,
    })


def _save(fig, out: Path, name: str) -> List[Path]:
    paths = [out / f"{name}.png", out / f"{name}.pdf"]
    fig.savefig(paths[0], dpi=200, bbox_inches="tight")
    fig.savefig(paths[1], bbox_inches="tight")
    return paths


def _bar_x(n_groups: int, n_series: int, width_total=0.8):
    w = width_total / max(n_series, 1)
    return w, [np.arange(n_groups) - width_total / 2 + w * (i + 0.5) for i in range(n_series)]


def plot_fig1(plt, d: pd.DataFrame, out: Path) -> List[Path]:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5.2, 4.6), sharex=True, gridspec_kw={"height_ratios": [1, 1]})
    if d.empty:
        ax1.text(0.5, 0.5, "no Lee-baseline cells", ha="center", transform=ax1.transAxes)
        return _save(fig, out, "fig1_ladder")
    conds = sorted(d.condition.unique(), key=lambda c: (REGIME_ORDER.index(d[d.condition == c].regime.iloc[0])
                                                         if d[d.condition == c].regime.iloc[0] in REGIME_ORDER else 9, c))
    models = list(dict.fromkeys(d.model))
    w, xs = _bar_x(len(conds), len(models))
    for i, m in enumerate(models):
        dm = d[d.model == m].set_index("condition").reindex(conds)
        ax1.bar(xs[i], dm.report_rate, w * 0.9, yerr=dm.report_rate_se, color=SERIES[i], label=m,
                error_kw={"ecolor": INK2, "elinewidth": 0.8, "capsize": 2})
        ax2.errorbar(np.arange(len(conds)), dm.avg_price, yerr=dm.avg_price_se, color=SERIES[i],
                     marker=MARKERS[i], markersize=6, capsize=2, label=m)
    ax1.set_ylabel("share of periods with a report")
    ax1.set_title("Reporting rises with enforcement ...", loc="left")
    ax2.set_title("... does the price fall?", loc="left")
    for y, lab in ((3, "Bertrand–Nash (3)"), (9, "joint-profit max (9)")):
        ax2.axhline(y, color=MUTED, lw=1, ls="--")
        ax2.text(len(conds) - 0.5, y + 0.15, lab, color=INK2, ha="right", va="bottom", fontsize=8)
    ax2.set_ylim(0, 12.5)
    ax2.set_ylabel("average price")
    ax2.set_xticks(np.arange(len(conds)), conds, rotation=30 if len(conds) > 6 else 0,
                   ha="right" if len(conds) > 6 else "center")
    if len(models) > 1:
        ax1.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    return _save(fig, out, "fig1_ladder")


def plot_fig2(plt, theory: pd.DataFrame, obs: pd.DataFrame, out: Path) -> List[Path]:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.4), gridspec_kw={"width_ratios": [1.1, 1]})
    rules = list(theory.rules)
    w, xs = _bar_x(len(rules), 2)
    for i, (col, lab) in enumerate((("silent", "silent collusion (audits only)"), ("alternate", "alternating sole reporter"))):
        bars = ax1.bar(xs[i], theory[col], w * 0.9, color=SERIES[i], label=lab)
        for b, v in zip(bars, theory[col]):
            ax1.text(b.get_x() + b.get_width() / 2, v + (8 if v >= 0 else -8), f"{v:.0f}", ha="center",
                     va="bottom" if v >= 0 else "top", fontsize=7, color=INK2)
    ax1.axhline(180, color=MUTED, lw=1, ls="--", label="market profit at (9,9) = 180")
    ax1.axhline(0, color=INK2, lw=0.8)
    ax1.set_xticks(np.arange(len(rules)), [r.replace("_", "\n") for r in rules])
    ax1.set_ylabel("per-firm payoff per period")
    ax1.set_title("Farming arithmetic at (9,9)", loc="left")
    ax1.legend(loc="lower left", fontsize=7)
    lo = min(0.0, float(np.nanmin(theory[["silent", "alternate"]].values)))
    ax1.set_ylim(lo * 1.25 - 20, 340)
    if obs.empty:
        ax2.text(0.5, 0.5, "no enforcement cells", ha="center", transform=ax2.transAxes)
    else:
        conds = _sorted_conds(obs)
        models = list(dict.fromkeys(obs.model))
        w2, xs2 = _bar_x(len(conds), len(models))
        for i, m in enumerate(models):
            dm = obs[obs.model == m].set_index("condition").reindex(conds)
            ax2.barh(xs2[i], dm.farming_index, w2 * 0.9, xerr=dm.farming_index_se, color=SERIES[i],
                     label=m, error_kw={"ecolor": INK2, "elinewidth": 0.8, "capsize": 2})
        ax2.set_yticks(np.arange(len(conds)), conds)
        ax2.invert_yaxis()
        ax2.set_xlim(0, 1.05)
        ax2.set_xlabel("farming index (share of reward paid in alternating sole-reporter convictions)")
        ax2.set_title("Observed", loc="left")
        if len(models) > 1:
            ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=min(len(models), 4), fontsize=7)
    fig.tight_layout()
    return _save(fig, out, "fig2_farming")


def _sorted_conds(d: pd.DataFrame) -> List[str]:
    first = d.drop_duplicates("condition").set_index("condition").regime
    return sorted(first.index, key=lambda c: (REGIME_ORDER.index(first[c]) if first[c] in REGIME_ORDER else 9, len(c), c))


def plot_fig3(plt, d: pd.DataFrame, out: Path) -> List[Path]:
    models = list(dict.fromkeys(d.model)) if len(d) else []
    n = max(len(models), 1)
    fig, axes = plt.subplots(1, n, figsize=(4.4 * n, 3.2), squeeze=False, sharey=True)
    if not models:
        axes[0, 0].text(0.5, 0.5, "no convictions", ha="center", transform=axes[0, 0].transAxes)
    for ax, m in zip(axes[0], models):
        dm = d[d.model == m]
        for i, c in enumerate(_sorted_conds(dm)):
            dc = dm[dm.condition == c].sort_values("k")
            ax.errorbar(dc.k, dc.price, yerr=dc.price_se, color=SERIES[i % len(SERIES)], marker=MARKERS[i % 4],
                        markersize=5, capsize=2, label=f"{c} ({dc.rules.iloc[0]})")
        ax.axvline(0, color=MUTED, lw=1, ls="--")
        ax.axhline(3, color=MUTED, lw=0.8, ls=":")
        ax.set_xlabel("periods relative to first conviction")
        ax.set_title(m if len(models) > 1 else "Price around the first conviction", loc="left")
        ax.set_ylim(0, 12.5)
        ax.legend(loc="lower left", fontsize=7)
    axes[0, 0].set_ylabel("average market price")
    fig.tight_layout()
    return _save(fig, out, "fig3_event")


def plot_fig4(plt, d: pd.DataFrame, sgs: pd.DataFrame, out: Path) -> List[Path]:
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    ax.axvline(A.SAY_THRESHOLD, color=MUTED, lw=1)
    ax.axhline(A.HIGH_THRESHOLD, color=MUTED, lw=1)
    for (x, y, lab, ha) in ((0.98, 0.98, "direct", "right"), (0.98, 0.02, "attempted\n(\"on paper\")", "right"),
                            (0.02, 0.98, "hidden", "left"), (0.02, 0.02, "benign", "left")):
        ax.text(x, y, lab, transform=ax.transAxes, ha=ha, va="top" if y > 0.5 else "bottom", color=MUTED,
                fontsize=9, fontweight="bold")
    models = list(dict.fromkeys(d.model))
    rng = np.random.default_rng(0)
    for i, m in enumerate(models):
        s = sgs[sgs.model == m]
        jx, jy = rng.uniform(-0.012, 0.012, len(s)), rng.uniform(-0.012, 0.012, len(s))
        ax.scatter(np.clip(s.say_rate + jx, -0.02, 1.02), np.clip(s.high_share + jy, -0.02, 1.02), s=8,
                   color=SERIES[i], alpha=0.18, linewidths=0, zorder=2)
        dm = d[d.model == m]
        ax.scatter(dm.say_rate, dm.high_share, s=64, color=SERIES[i], marker=MARKERS[i], edgecolors=SURFACE,
                   linewidths=1.5, zorder=3, label=m)
        # direct labels; stack labels of coincident points
        seen: Dict[tuple, int] = {}
        for _, r in dm.iterrows():
            key = (round(r.say_rate, 2), round(r.high_share, 2))
            k = seen.get(key, 0)
            seen[key] = k + 1
            ax.annotate(r.condition, (r.say_rate, r.high_share), xytext=(7, -9 * k - 3),
                        textcoords="offset points", fontsize=7, color=INK2, zorder=4)
    ax.set_xlim(-0.05, 1.08)
    ax.set_ylim(-0.05, 1.08)
    ax.set_xlabel("say: share of periods with an agreement in chat (classifier)")
    ax.set_ylabel(f"do: share of prices ≥ {A.HIGH_PRICE}")
    ax.set_title("Say vs do (large marks: condition means; dots: supergames)", loc="left", fontsize=9)
    if len(models) > 1:
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=min(len(models), 4), fontsize=7)
    fig.tight_layout()
    return _save(fig, out, "fig4_saydo")


def plot_all(data: Dict[str, pd.DataFrame], out: Path) -> List[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _style(plt)
    paths = []
    paths += plot_fig1(plt, data["fig1_ladder"], out)
    paths += plot_fig2(plt, data["fig2_theory"], data["fig2_observed"], out)
    paths += plot_fig3(plt, data["fig3_event"], out)
    paths += plot_fig4(plt, data["fig4_saydo"], data["fig4_supergames"], out)
    plt.close("all")
    return paths


def make_figures(src: str | Path, out: Optional[str | Path] = None, from_csv: bool = False,
                 pool: bool = True) -> Dict[str, list]:
    src = Path(src)
    out = Path(out) if out else (src if from_csv else src / "figures")
    out.mkdir(parents=True, exist_ok=True)
    if from_csv:
        data = {k: pd.read_csv(src / f"{k}.csv") for k in CSV_NAMES}
        csvs = []
    else:
        data = figure_data(load_runs(src, pool=pool))
        csvs = []
        for k, v in data.items():
            p = out / f"{k}.csv"
            v.to_csv(p, index=False)
            csvs.append(p)
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print(f"matplotlib not importable: wrote CSVs only. Re-plot with: python -m leniency figures --from-csv {out}")
        return {"csv": csvs, "figures": []}
    return {"csv": csvs, "figures": plot_all(data, out)}
