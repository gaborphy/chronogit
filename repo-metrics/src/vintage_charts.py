"""Charts for the vintage-cohort study: output/vintage/charts/*.png.

One line per metric across all 51 vintage quarters (median across that
quarter's ~10 sampled packages), shaded p25-p75 band, faint scatter of the
individual packages for texture. Not small multiples -- there's no "same
10 repos" dimension here, each point is a different sample of packages.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vintage_analysis import ANALYSIS_DIR, VINTAGE_DIR  # noqa: E402

CHARTS_DIR = VINTAGE_DIR / "charts"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
})


def _xticks(ax, quarters, every=4):
    idx = list(range(0, len(quarters), every))
    ax.set_xticks(idx)
    ax.set_xticklabels([quarters[i] for i in idx], rotation=90, fontsize=7)


def _band_plot(ax, vq: pd.DataFrame, col: str, label: str, color: str, pkgs: pd.DataFrame | None = None,
                pkg_col: str | None = None):
    x = range(len(vq))
    ax.plot(x, vq[f"{col}__median"], color=color, lw=1.8, label=label)
    ax.fill_between(x, vq[f"{col}__p25"], vq[f"{col}__p75"], color=color, alpha=0.15)
    if pkgs is not None and pkg_col is not None:
        qpos = {q: i for i, q in enumerate(vq["vintage_quarter"])}
        xs = pkgs["vintage_quarter"].map(qpos)
        ax.scatter(xs, pkgs[pkg_col], color=color, s=6, alpha=0.25, zorder=0)


def chart_family1(vq, pkgs):
    fig, ax = plt.subplots(figsize=(11, 5))
    _band_plot(ax, vq, "state_mean_comment_len", "state: mean comment length (codebase at snapshot)",
               "#2b6cb0", pkgs, "state_mean_comment_len")
    _band_plot(ax, vq, "flow_mean_added_comment_len", "flow: mean length of comments added pre-snapshot",
               "#dd6b20", pkgs, "flow_mean_added_comment_len")
    ax.set_title("Family 1 — comment length by package vintage\n"
                 "line = median across that quarter's ~10 sampled packages, band = 25th-75th pct, dots = individual packages")
    ax.legend(fontsize=8)
    _xticks(ax, vq["vintage_quarter"].tolist())
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vintage_family1_comment_length.png", dpi=150)
    plt.close(fig)


def chart_family2(vq, pkgs):
    fig, ax = plt.subplots(figsize=(11, 5))
    _band_plot(ax, vq, "state_mean_complexity", "mean McCabe complexity per function",
               "#2b6cb0", pkgs, "state_mean_complexity")
    ax.plot(range(len(vq)), vq["state_median_complexity__median"], color="#c53030", lw=1.4, ls="--",
            label="median complexity (of medians)")
    ax.set_title("Family 2 — code complexity by package vintage")
    ax.legend(fontsize=8)
    _xticks(ax, vq["vintage_quarter"].tolist())
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vintage_family2_complexity.png", dpi=150)
    plt.close(fig)


def chart_family3(vq, pkgs):
    fig, ax = plt.subplots(figsize=(11, 5))
    _band_plot(ax, vq, "state_mean_func_len", "mean function length (incl. docstring)",
               "#2b6cb0", pkgs, "state_mean_func_len")
    _band_plot(ax, vq, "state_mean_body_len", "mean body length (excl. docstring)",
               "#38a169", pkgs, "state_mean_body_len")
    ax.set_title("Family 3 — function length by package vintage")
    ax.legend(fontsize=8)
    _xticks(ax, vq["vintage_quarter"].tolist())
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vintage_family3_function_length.png", dpi=150)
    plt.close(fig)


def chart_family4(vq, pkgs):
    fig, ax = plt.subplots(figsize=(11, 5))
    _band_plot(ax, vq, "flow_median_hunk_added", "median added lines / hunk (own within-package median)",
               "#2b6cb0", pkgs, "flow_median_hunk_added")
    _band_plot(ax, vq, "flow_median_added_code_lines_per_commit", "median added code lines / commit",
               "#805ad5", pkgs, "flow_median_added_code_lines_per_commit")
    ax.set_yscale("symlog")
    ax.set_title("Family 4 — size of added parts by package vintage (log scale: young packages are outlier-prone)")
    ax.legend(fontsize=8)
    _xticks(ax, vq["vintage_quarter"].tolist())
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vintage_family4_added_part_size.png", dpi=150)
    plt.close(fig)


def chart_docstring_and_contributors(vq, pkgs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    _band_plot(ax1, vq, "state_frac_functions_with_docstring", "fraction of functions with a docstring",
               "#2b6cb0", pkgs, "state_frac_functions_with_docstring")
    ax1.set_title("Fraction of functions carrying a docstring, by vintage")
    ax1.legend(fontsize=8)
    _xticks(ax1, vq["vintage_quarter"].tolist())

    _band_plot(ax2, vq, "flow_n_contributors", "distinct contributors in first ~180 days",
               "#c53030", pkgs, "flow_n_contributors")
    ax2.set_title("Contributor count in first ~180 days, by vintage\n"
                  "(confounded with GitHub's own growth -- see report)")
    ax2.legend(fontsize=8)
    _xticks(ax2, vq["vintage_quarter"].tolist())

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vintage_docstring_and_contributors.png", dpi=150)
    plt.close(fig)


def chart_sample_health(vq):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    ax1.bar(range(len(vq)), vq["n_packages"], color="#718096")
    ax1.axhline(10, color="black", lw=0.8, ls=":")
    ax1.set_title("Packages successfully sampled per vintage quarter (target 10)")
    _xticks(ax1, vq["vintage_quarter"].tolist())

    ax2.plot(range(len(vq)), vq["state_parse_rate__median"], color="#2b6cb0", lw=1.6)
    ax2.set_ylim(0, 1.05)
    ax2.set_title("Median parse_rate at snapshot, by vintage")
    _xticks(ax2, vq["vintage_quarter"].tolist())

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vintage_sample_health.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    vq = pd.read_csv(ANALYSIS_DIR / "vintage_quarterly.csv")
    pkgs = pd.read_csv(VINTAGE_DIR / "packages.csv")

    chart_family1(vq, pkgs)
    chart_family2(vq, pkgs)
    chart_family3(vq, pkgs)
    chart_family4(vq, pkgs)
    chart_docstring_and_contributors(vq, pkgs)
    chart_sample_health(vq)
    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
