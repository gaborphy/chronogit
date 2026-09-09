"""Charts for the time-dimension dependency-popularity analysis:
output/deps/charts_time/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deps_time_analysis import TIME_DIR, DEPS_DIR  # noqa: E402

CHARTS_DIR = DEPS_DIR / "charts_time"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
})


def _trend_line(ax, x, y, color, label=None):
    mask = ~np.isnan(y)
    slope, intercept = np.polyfit(x[mask], y[mask], 1)
    xs = np.array([x.min(), x.max()])
    ax.plot(xs, slope * xs + intercept, color=color, ls="--", lw=1.2, alpha=0.7, label=label)


def chart_concentration_naive_vs_rarefied() -> None:
    from scipy import stats as _stats

    by_y = pd.read_csv(TIME_DIR / "by_year_all.csv")
    raref = pd.read_csv(TIME_DIR / "rarefied_diversity_by_year.csv")
    n_draw = int(raref["n_draw"].iloc[0])
    rho, p = _stats.spearmanr(raref["year"], raref["rarefied_unique_at_n"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    x = by_y["year"].values
    ax1.plot(x, by_y["unique_ratio"], "o-", color="#2b6cb0", label="unique_ratio (unique deps / edges)")
    _trend_line(ax1, x, by_y["unique_ratio"].values, "#2b6cb0")
    ax1b = ax1.twinx()
    ax1b.plot(x, by_y["hhi"], "s-", color="#c53030", label="HHI (concentration)")
    _trend_line(ax1b, x, by_y["hhi"].values, "#c53030")
    ax1.set_title("Naive: looks like rising concentration")
    ax1.set_ylabel("unique_ratio (higher = more diverse)", color="#2b6cb0")
    ax1b.set_ylabel("HHI (higher = more concentrated)", color="#c53030")
    ax1.set_xlabel("cohort year")

    x2 = raref["year"].values
    ax2.plot(x2, raref["rarefied_unique_at_n"], "o-", color="#38a169",
             label=f"unique deps recovered in a fixed {n_draw}-edge sample")
    ax2.fill_between(
        x2,
        raref["rarefied_unique_at_n"] - raref["rarefied_unique_std"],
        raref["rarefied_unique_at_n"] + raref["rarefied_unique_std"],
        color="#38a169", alpha=0.15,
    )
    _trend_line(ax2, x2, raref["rarefied_unique_at_n"].values, "#38a169")
    ax2.set_title(f"Corrected for sample size: flat\n(rarefied to {n_draw} edges/year, Spearman ρ={rho:.2f}, p={p:.2f})")
    ax2.set_ylabel(f"unique dependency names per {n_draw} edges")
    ax2.set_xlabel("cohort year")

    fig.suptitle("Is dependency diversity really shrinking over time, or is that just more data per year?", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "concentration_naive_vs_rarefied.png", dpi=150)
    plt.close(fig)


def chart_popularity_over_time() -> None:
    by_y = pd.read_csv(TIME_DIR / "by_year_all.csv")
    fig, ax = plt.subplots(figsize=(10, 5))
    x = by_y["year"].values

    series = {
        "median_dep_stars": ("Median stars of chosen dependencies", "#2b6cb0"),
        "median_dep_forks": ("Median forks", "#805ad5"),
        "median_dep_committers": ("Median lifetime committers", "#c53030"),
    }
    for col, (label, color) in series.items():
        y = by_y[col].values
        y_idx = y / y[0] * 100
        ax.plot(x, y_idx, "o-", color=color, label=label)

    ax.axhline(100, color="black", lw=0.8, ls=":")
    ax.set_ylabel("index (2014 = 100)")
    ax.set_xlabel("newborn package's birth year")
    ax.set_title("Popularity of chosen dependencies by cohort year (indexed to 2014)\n"
                  "caveat: stars/forks/committers measured TODAY, not at time of choice -- see report")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "popularity_over_time.png", dpi=150)
    plt.close(fig)


def chart_ai_sdk_adoption() -> None:
    from deps_time_analysis import load_data, AI_SDK_PACKAGES

    edges, pop, top20 = load_data()
    ai_edges = edges[edges["dependency_name"].isin(AI_SDK_PACKAGES)]
    by_year = ai_edges.groupby("year").size().reindex(range(2014, 2027), fill_value=0)
    total_by_year = edges.groupby("year").size().reindex(range(2014, 2027), fill_value=0)
    share = (by_year / total_by_year * 100).fillna(0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.bar(by_year.index, by_year.values, color="#2b6cb0")
    ax1.set_title("Edges to an AI/genAI SDK package, by year")
    ax1.set_xlabel("year")
    ax1.set_ylabel("# edges")
    ax1.axvline(2022.9, color="#c53030", ls="--", lw=1, label="ChatGPT public release (Nov 2022)")
    ax1.legend(fontsize=7)

    ax2.bar(share.index, share.values, color="#38a169")
    ax2.set_title("Same, as % of that year's total dependency edges")
    ax2.set_xlabel("year")
    ax2.set_ylabel("%")
    ax2.axvline(2022.9, color="#c53030", ls="--", lw=1)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "ai_sdk_adoption.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_concentration_naive_vs_rarefied()
    chart_popularity_over_time()
    chart_ai_sdk_adoption()
    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
