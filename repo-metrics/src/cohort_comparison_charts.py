"""Charts for cohort_comparison.py: output/cohort_comparison/charts/*.png"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cohort_comparison import OUT_DIR  # noqa: E402
from vintage_analysis import build_vintage_quarterly  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = OUT_DIR / "charts"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
})


def chart_ai_adoption() -> None:
    cmp = pd.read_csv(OUT_DIR / "ai_adoption_comparison.csv")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(cmp["year"], cmp["adoption_rate_star"] * 100, "o-", color="#2b6cb0",
            label="star-sampled cohort (VINTAGE_REPORT.md / AI_USAGE_REPORT.md)")
    ax.plot(cmp["year"], cmp["adoption_rate_unbiased"] * 100, "s-", color="#c53030",
            label="unbiased cohort (random from full PyPI population)")
    ax.axvline(2022.9, color="#718096", ls="--", lw=1, label="ChatGPT public release")
    ax.set_ylabel("% of newborn packages with a self-disclosed AI-tool signal")
    ax.set_xlabel("cohort year")
    ax.set_title("Self-disclosed AI-tool adoption: star-sampled vs. unbiased newborn-package cohorts")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "ai_adoption_comparison.png", dpi=150)
    plt.close(fig)


def chart_contributor_divergence() -> None:
    star = pd.read_csv(ROOT / "output" / "vintage" / "packages.csv")
    unbiased = pd.read_csv(ROOT / "output" / "vintage_unbiased" / "packages.csv")
    star_vq = build_vintage_quarterly(star)
    unb_vq = build_vintage_quarterly(unbiased)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(star_vq["vintage_quarter"], star_vq["flow_n_contributors__median"], "o-",
            color="#2b6cb0", label="star-sampled cohort", markersize=3)
    ax.plot(unb_vq["vintage_quarter"], unb_vq["flow_n_contributors__median"], "s-",
            color="#c53030", label="unbiased cohort", markersize=3)
    ax.set_ylabel("median contributors in first 180 days")
    ax.set_xlabel("vintage quarter")
    ax.set_title("Contributor-count growth: a star-selection artifact\n(star-sampled +253% vs. unbiased ~flat, ns)")
    ax.set_xticks(ax.get_xticks()[::4])
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "contributor_divergence.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_ai_adoption()
    chart_contributor_divergence()
    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
