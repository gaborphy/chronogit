"""Render every chart the report embeds, into output/charts/*.png."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis import (
    ANALYSIS_DIR, OUTPUT_DIR, REPO_ORDER,
    load_all_panel_b, fixed_effects_pool,
)

CHARTS_DIR = OUTPUT_DIR / "charts"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "font.size": 8,
})


def _grid(n=10, ncols=5, figsize_per=(2.6, 2.0)):
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(figsize_per[0] * ncols, figsize_per[1] * nrows),
                              sharex=False)
    return fig, axes.flatten()


def _xticks_sparse(ax, quarters, every=4):
    idx = list(range(0, len(quarters), every))
    ax.set_xticks(idx)
    ax.set_xticklabels([quarters[i] for i in idx], rotation=90, fontsize=6)


# ---------------------------------------------------------------------------
# Family small multiples
# ---------------------------------------------------------------------------

def chart_family1_comment_length(panel_a_q: pd.DataFrame, panel_b: pd.DataFrame) -> None:
    b = panel_b[panel_b["is_partial_quarter"] == 0]
    fig, axes = _grid()
    for i, repo in enumerate(REPO_ORDER):
        ax = axes[i]
        gb = b[b["repo"] == repo].sort_values("quarter")
        ga = panel_a_q[panel_a_q["repo"] == repo].sort_values("quarter")
        quarters = gb["quarter"].tolist()
        ax.plot(range(len(gb)), gb["mean_comment_len"], color="#2b6cb0", lw=1.4, label="state (Panel B)")
        ax.plot(range(len(ga)), ga["pooled_mean_added_comment_len"], color="#dd6b20", lw=1.0,
                ls="--", label="flow, newly added (Panel A)")
        ax.set_title(repo, fontsize=8)
        _xticks_sparse(ax, quarters)
    for j in range(len(REPO_ORDER), len(axes)):
        axes[j].axis("off")
    axes[0].legend(fontsize=6, loc="upper left")
    fig.suptitle("Family 1 — comment length: mean chars per # comment\n"
                 "solid = whole codebase at quarter-end (Panel B)   dashed = only comments newly added that quarter (Panel A)",
                 fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "family1_comment_length.png", dpi=150)
    plt.close(fig)


def chart_family2_complexity(panel_b: pd.DataFrame) -> None:
    b = panel_b[panel_b["is_partial_quarter"] == 0]
    fig, axes = _grid()
    for i, repo in enumerate(REPO_ORDER):
        ax = axes[i]
        g = b[b["repo"] == repo].sort_values("quarter")
        quarters = g["quarter"].tolist()
        ax.plot(range(len(g)), g["mean_complexity"], color="#2b6cb0", lw=1.4, label="mean")
        ax2 = ax.twinx()
        ax2.plot(range(len(g)), g["p90_complexity"], color="#c53030", lw=1.0, ls="--", label="p90")
        ax2.tick_params(labelsize=6)
        ax.set_title(repo, fontsize=8)
        _xticks_sparse(ax, quarters)
    for j in range(len(REPO_ORDER), len(axes)):
        axes[j].axis("off")
    fig.legend(["mean complexity (left axis)", "p90 complexity (right axis)"],
               loc="upper left", fontsize=6, bbox_to_anchor=(0.01, 0.98))
    fig.suptitle("Family 2 — McCabe complexity per function (state, Panel B)\n"
                 "solid = mean (left axis)   dashed = p90 (right axis, tail behavior)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "family2_complexity.png", dpi=150)
    plt.close(fig)


def chart_family3_function_length(panel_b: pd.DataFrame) -> None:
    b = panel_b[panel_b["is_partial_quarter"] == 0]
    fig, axes = _grid()
    for i, repo in enumerate(REPO_ORDER):
        ax = axes[i]
        g = b[b["repo"] == repo].sort_values("quarter")
        quarters = g["quarter"].tolist()
        ax.plot(range(len(g)), g["mean_func_len"], color="#2b6cb0", lw=1.4, label="mean_func_len (incl. docstring)")
        ax.plot(range(len(g)), g["mean_body_len"], color="#38a169", lw=1.4, ls="--", label="mean_body_len (excl. docstring)")
        ax.set_title(repo, fontsize=8)
        _xticks_sparse(ax, quarters)
    for j in range(len(REPO_ORDER), len(axes)):
        axes[j].axis("off")
    axes[0].legend(fontsize=6, loc="upper left")
    fig.suptitle("Family 3 — function length, lines (state, Panel B)\n"
                 "solid = total function span (incl. docstring)   dashed = body only (docstring subtracted)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "family3_function_length.png", dpi=150)
    plt.close(fig)


def chart_family4_added_part_size(panel_a_q: pd.DataFrame) -> None:
    fig, axes = _grid()
    for i, repo in enumerate(REPO_ORDER):
        ax = axes[i]
        g = panel_a_q[panel_a_q["repo"] == repo].sort_values("quarter")
        quarters = g["quarter"].tolist()
        ax.plot(range(len(g)), g["pooled_median_hunk_added"], color="#2b6cb0", lw=1.4,
                label="median added lines / hunk")
        ax.plot(range(len(g)), g["pooled_median_added_code_lines_per_commit"], color="#805ad5", lw=1.0,
                ls="--", label="median added code lines / commit")
        ax.set_title(repo, fontsize=8)
        _xticks_sparse(ax, quarters)
    for j in range(len(REPO_ORDER), len(axes)):
        axes[j].axis("off")
    axes[0].legend(fontsize=6, loc="upper left")
    fig.suptitle("Family 4 — size of added parts, pooled all authors (flow, Panel A)\n"
                 "solid = median added lines per hunk (\"one contiguous edit\")   dashed = median added code lines per commit",
                 fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "family4_added_part_size.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Pooled, repo-fixed-effects overview (normalized to each series' own 2014Q1
# level so different units can share one axis)
# ---------------------------------------------------------------------------

def _fe_indexed(df, col):
    fe = fixed_effects_pool(df, col)
    base = fe["pooled_fe"].iloc[0]
    fe["index100"] = fe["pooled_fe"] / base * 100
    return fe


def chart_pooled_fixed_effects(panel_a_q: pd.DataFrame, panel_b: pd.DataFrame) -> None:
    b = panel_b[panel_b["is_partial_quarter"] == 0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    state_series = {
        "mean_func_len": ("Function length (mean)", "#2b6cb0"),
        "mean_body_len": ("Function body length (mean)", "#38a169"),
        "mean_complexity": ("McCabe complexity (mean)", "#c53030"),
        "mean_comment_len": ("Comment length, state (mean)", "#805ad5"),
    }
    quarters = sorted(b["quarter"].unique())
    for col, (label, color) in state_series.items():
        fe = _fe_indexed(b, col)
        fe = fe.set_index("quarter").reindex(quarters)
        ax1.plot(range(len(quarters)), fe["index100"], label=label, color=color, lw=1.6)
    ax1.set_title("Codebase state (Panel B), repo-fixed-effects pooled\nindexed to 2014Q1 = 100")
    ax1.legend(fontsize=7)
    _xticks_sparse(ax1, quarters, every=4)
    ax1.set_ylabel("index (2014Q1 = 100)")

    flow_series = {
        "pooled_median_hunk_added": ("Median added lines / hunk", "#2b6cb0"),
        "pooled_median_added_code_lines_per_commit": ("Median added code lines / commit", "#805ad5"),
        "pooled_mean_added_comment_len": ("Comment length, newly added (mean)", "#dd6b20"),
    }
    quarters_a = sorted(panel_a_q["quarter"].unique())
    for col, (label, color) in flow_series.items():
        fe = _fe_indexed(panel_a_q, col)
        fe = fe.set_index("quarter").reindex(quarters_a)
        ax2.plot(range(len(quarters_a)), fe["index100"], label=label, color=color, lw=1.6)
    ax2.set_title("Commit flow (Panel A, pooled all authors), repo-fixed-effects pooled\nindexed to 2014Q1 = 100")
    ax2.legend(fontsize=7)
    _xticks_sparse(ax2, quarters_a, every=4)

    fig.suptitle("No single repo drives these -- each series is within-repo demeaned before pooling", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(CHARTS_DIR / "pooled_fixed_effects.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Author decomposition: pooled vs excluding top-volume contributor, small
# multiples, plus a contributor-count series.
# ---------------------------------------------------------------------------

def chart_author_decomposition(panel_a_q: pd.DataFrame) -> None:
    fig, axes = _grid()
    for i, repo in enumerate(REPO_ORDER):
        ax = axes[i]
        g = panel_a_q[panel_a_q["repo"] == repo].sort_values("quarter")
        quarters = g["quarter"].tolist()
        top = g["top_contributor"].iloc[0]
        share = g["top_contributor_share_overall"].iloc[0]
        ax.plot(range(len(g)), g["pooled_mean_added_comment_len"], color="#2b6cb0", lw=1.4, label="pooled (all authors)")
        ax.plot(range(len(g)), g["excltop_mean_added_comment_len"], color="#dd6b20", lw=1.2, ls="--",
                label=f"excl. top ({share:.0%} of commits)")
        ax.set_title(repo, fontsize=8)
        _xticks_sparse(ax, quarters)
    for j in range(len(REPO_ORDER), len(axes)):
        axes[j].axis("off")
    axes[0].legend(fontsize=6, loc="upper left")
    fig.suptitle("Author-controlled decomposition: mean added-comment length, pooled vs. excluding each repo's top-volume contributor",
                 fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "author_decomposition_comment_len.png", dpi=150)
    plt.close(fig)


def chart_contributor_counts(panel_a_q: pd.DataFrame) -> None:
    fig, axes = _grid()
    for i, repo in enumerate(REPO_ORDER):
        ax = axes[i]
        g = panel_a_q[panel_a_q["repo"] == repo].sort_values("quarter")
        quarters = g["quarter"].tolist()
        ax.plot(range(len(g)), g["pooled_n_contributors"], color="#2b6cb0", lw=1.4)
        ax.set_title(repo, fontsize=8)
        _xticks_sparse(ax, quarters)
    for j in range(len(REPO_ORDER), len(axes)):
        axes[j].axis("off")
    fig.suptitle("Distinct contributors per quarter (Panel A)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "contributor_counts.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Event-study diagnostic: fit each repo's own PRE-break linear trend, plot
# actual / trend-predicted ratio through time -- a real break shows up as a
# level jump away from 1.0 that persists; pure trend growth stays near 1.0.
# ---------------------------------------------------------------------------

def chart_event_study(panel_b: pd.DataFrame, metric: str, break_quarter: str, title: str, fname: str) -> pd.DataFrame:
    b = panel_b[panel_b["is_partial_quarter"] == 0].copy()
    quarters = sorted(b["quarter"].unique())
    qidx = {q: i for i, q in enumerate(quarters)}
    b["qi"] = b["quarter"].map(qidx)
    break_i = qidx[break_quarter]

    fig, ax = plt.subplots(figsize=(9, 5))
    ratio_by_quarter = {q: [] for q in quarters}

    for repo, g in b.groupby("repo"):
        g = g.sort_values("qi")
        pre = g[g["qi"] < break_i]
        if len(pre) < 6:
            continue
        slope, intercept = np.polyfit(pre["qi"], pre[metric], 1)
        predicted = slope * g["qi"] + intercept
        ratio = g[metric].values / predicted.values
        ax.plot(g["qi"], ratio, color="#a0aec0", lw=0.9, alpha=0.8)
        for qi, r in zip(g["qi"], ratio):
            ratio_by_quarter[quarters[qi]].append(r)

    mean_ratio = pd.Series({q: np.mean(v) for q, v in ratio_by_quarter.items() if v}).reindex(quarters)
    ax.plot(range(len(quarters)), mean_ratio.values, color="#c53030", lw=2.2, label="mean across repos")
    ax.axhline(1.0, color="black", lw=0.8, ls=":")
    ax.axvline(break_i, color="black", lw=1.0, ls="--", label=f"{break_quarter} (candidate break)")
    ax.set_ylabel("actual / pre-break-trend-predicted")
    _xticks_sparse(ax, quarters, every=4)
    ax.legend(fontsize=8)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / fname, dpi=150)
    plt.close(fig)

    return mean_ratio.to_frame("mean_actual_over_trend")


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    panel_a_q = pd.read_csv(ANALYSIS_DIR / "panel_a_quarterly.csv")
    panel_b = load_all_panel_b()

    print("Family small multiples ...")
    chart_family1_comment_length(panel_a_q, panel_b)
    chart_family2_complexity(panel_b)
    chart_family3_function_length(panel_b)
    chart_family4_added_part_size(panel_a_q)

    print("Pooled fixed-effects overview ...")
    chart_pooled_fixed_effects(panel_a_q, panel_b)

    print("Author decomposition ...")
    chart_author_decomposition(panel_a_q)
    chart_contributor_counts(panel_a_q)

    print("Event-study diagnostics ...")
    for metric, fname_suffix in [
        ("mean_complexity", "complexity"),
        ("mean_func_len", "func_len"),
        ("mean_body_len", "body_len"),
        ("mean_comment_len", "comment_len"),
    ]:
        df = chart_event_study(
            panel_b, metric, "2022Q4",
            title=f"Event-study diagnostic: {metric} vs. each repo's own pre-2022Q4 trend",
            fname=f"event_study_{fname_suffix}.png",
        )
        df.to_csv(ANALYSIS_DIR / f"event_study_{fname_suffix}.csv")

    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
