"""Charts for the dependency-popularity hypothesis test:
output/deps/charts/*.png
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
from deps_analysis import DEPS_DIR, ANALYSIS_DIR, METRICS, load_data, fan_in_table  # noqa: E402

CHARTS_DIR = DEPS_DIR / "charts"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
})


def chart_ecdf(pop_found: pd.DataFrame, baseline_found: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, m, title in zip(
        axes, METRICS, ["Stars", "Forks", "Total committers (lifetime)"]
    ):
        for label, df, color in [
            ("Used as a dependency", pop_found, "#2b6cb0"),
            ("Random PyPI baseline", baseline_found, "#c53030"),
        ]:
            vals = np.sort(df[m].dropna().values + 1)  # +1 so log(0) is fine
            if len(vals) == 0:
                continue
            y = np.arange(1, len(vals) + 1) / len(vals)
            ax.plot(vals, 1 - y, label=label, color=color, lw=1.8)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(f"{title} + 1 (log)")
        ax.set_ylabel("P(X > x)  [log]")
        ax.set_title(title)
        ax.legend(fontsize=8)
    fig.suptitle("Survival curves: dependency-set vs. random-PyPI-baseline popularity", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(CHARTS_DIR / "ecdf_comparison.png", dpi=150)
    plt.close(fig)


def chart_tiers(pop_found: pd.DataFrame, baseline_found: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    bins = (0, 10, 100, 1000, 10_000, np.inf)
    labels = ("0-10", "10-100", "100-1k", "1k-10k", "10k+")
    for ax, m, title in zip(axes, ["stargazers_count", "forks_count"], ["Stars", "Forks"]):
        dep_t = pd.cut(pop_found[m].fillna(0), bins=bins, labels=labels, right=False).value_counts(normalize=True).reindex(labels).fillna(0)
        base_t = pd.cut(baseline_found[m].fillna(0), bins=bins, labels=labels, right=False).value_counts(normalize=True).reindex(labels).fillna(0)
        x = np.arange(len(labels))
        w = 0.38
        ax.bar(x - w / 2, dep_t.values * 100, width=w, label="Used as a dependency", color="#2b6cb0")
        ax.bar(x + w / 2, base_t.values * 100, width=w, label="Random PyPI baseline", color="#c53030")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylabel("% of packages in group")
        ax.set_title(f"{title} tier distribution")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "tier_breakdown.png", dpi=150)
    plt.close(fig)


def chart_fan_in_scatter(pop_found: pd.DataFrame, fan_in: pd.DataFrame) -> None:
    merged = pop_found.merge(fan_in, left_on="name", right_on="dependency_name", how="inner")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, m, title in zip(axes, ["stargazers_count", "forks_count"], ["Stars", "Forks"]):
        sub = merged.dropna(subset=[m, "fan_in"])
        ax.scatter(sub[m] + 1, sub["fan_in"], alpha=0.35, s=14, color="#2b6cb0")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(f"{title} + 1 (log)")
        ax.set_ylabel("fan-in (# newborn packages depending on it, log)")
        ax.set_title(f"Fan-in vs. {title.lower()}, within the dependency set")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "fan_in_vs_popularity.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    edges, pop, baseline = load_data()
    pop_found = pop[pop["found"] == True].copy()  # noqa: E712
    baseline_found = baseline[baseline["found"] == True].copy()  # noqa: E712
    fan_in = fan_in_table(edges)

    chart_ecdf(pop_found, baseline_found)
    chart_tiers(pop_found, baseline_found)
    chart_fan_in_scatter(pop_found, fan_in)
    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
