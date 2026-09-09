"""Charts for the self-disclosed AI-tool-usage analysis:
output/ai_signal/charts/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_signal_analysis import ANALYSIS_DIR, AI_SIGNAL_DIR  # noqa: E402

CHARTS_DIR = AI_SIGNAL_DIR / "charts"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
})


def chart_adoption_rate() -> None:
    by_year = pd.read_csv(ANALYSIS_DIR / "adoption_by_year.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    ax1.bar(by_year["year"], by_year["adoption_rate"] * 100, color="#2b6cb0")
    ax1.axvline(2022.9, color="#c53030", ls="--", lw=1, label="ChatGPT public release")
    ax1.set_title("% of newborn packages with a self-disclosed\nAI-tool trailer or config file, by birth year")
    ax1.set_ylabel("%")
    ax1.set_xlabel("cohort year")
    ax1.legend(fontsize=7)

    ax2.plot(by_year["year"], by_year["mean_ai_commit_fraction_all"] * 100, "o-",
             color="#38a169", label="mean over all packages")
    ax2.plot(by_year["year"], by_year["mean_ai_commit_fraction_among_positive"] * 100, "s--",
             color="#805ad5", label="mean among packages with any AI-attributed commit")
    ax2.axvline(2022.9, color="#c53030", ls="--", lw=1)
    ax2.set_title("Mean share of a package's commits\nself-attributed to an AI tool")
    ax2.set_ylabel("%")
    ax2.set_xlabel("cohort year")
    ax2.legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "adoption_rate.png", dpi=150)
    plt.close(fig)


def chart_tool_breakdown() -> None:
    tools = pd.read_csv(ANALYSIS_DIR / "tool_breakdown_by_year.csv")
    tool_cols = [c for c in tools.columns if c not in ("year", "n_packages")]
    fig, ax = plt.subplots(figsize=(11, 5))
    bottom = pd.Series(0, index=tools.index, dtype=float)
    colors = plt.cm.tab10.colors
    for i, col in enumerate(tool_cols):
        vals = tools[col].fillna(0)
        if vals.sum() == 0:
            continue
        ax.bar(tools["year"], vals, bottom=bottom, label=col, color=colors[i % len(colors)])
        bottom += vals
    ax.set_title("Which tool self-identifies in commit trailers, by cohort year\n(packages can show more than one)")
    ax.set_ylabel("# packages with that tool's trailer")
    ax.set_xlabel("cohort year")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "tool_breakdown.png", dpi=150)
    plt.close(fig)


def chart_adoption_vs_sdk() -> None:
    cmp = pd.read_csv(ANALYSIS_DIR / "adoption_vs_sdk_timeline.csv")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(cmp["year"], cmp["adoption_rate"] * 100, "o-", color="#2b6cb0",
             label="self-disclosed AI-tool usage (commit trailer / config file)")
    ax.plot(cmp["year"], cmp["ai_sdk_edge_share"] * 100, "s-", color="#dd6b20",
             label="depends on an AI/genAI SDK package")
    ax.axvline(2022.9, color="#c53030", ls="--", lw=1, label="ChatGPT public release")
    ax.set_ylabel("%")
    ax.set_xlabel("cohort year")
    ax.set_title("Two different \"AI-relatedness\" signals: usage vs. topic")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "adoption_vs_sdk_timeline.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_adoption_rate()
    chart_tool_breakdown()
    chart_adoption_vs_sdk()
    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
