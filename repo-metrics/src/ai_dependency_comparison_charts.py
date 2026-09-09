"""Charts for the AI-flagged vs. non-flagged dependency comparison
(Plan A from the cl_ecosystem_networks synthesis):
output/deps/charts_ai_comparison/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_dependency_comparison import OUT_DIR, DEPS_DIR  # noqa: E402

CHARTS_DIR = DEPS_DIR / "charts_ai_comparison"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
})


def chart_naive_vs_stratified() -> None:
    naive_mw = pd.read_csv(OUT_DIR / "naive_mannwhitney.csv")
    per_q = pd.read_csv(OUT_DIR / "stratified_per_quarter.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    metrics = ["stargazers_count", "forks_count", "total_committers"]
    labels = ["Stars", "Forks", "Committers"]
    naive_ratio = [naive_mw.set_index("metric").loc[m, "ai_flagged_median"] /
                   naive_mw.set_index("metric").loc[m, "non_flagged_median"] for m in metrics]
    naive_p = [naive_mw.set_index("metric").loc[m, "mannwhitney_p"] for m in metrics]

    colors = ["#c53030" if p < 0.05 else "#a0aec0" for p in naive_p]
    ax1.bar(labels, naive_ratio, color=colors)
    ax1.axhline(1.0, color="black", lw=0.8, ls=":")
    for i, p in enumerate(naive_p):
        ax1.text(i, naive_ratio[i] + 0.02, f"p={p:.3f}", ha="center", fontsize=8)
    ax1.set_ylabel("AI-flagged median / non-flagged median")
    ax1.set_title("Naive pooled 2024-2026\n(confounded with calendar time -- red = nominally significant)")

    x = range(len(per_q))
    ax2.axhline(0, color="black", lw=0.8, ls=":")
    ax2.plot(x, per_q["stargazers_count_diff"], "o-", label="Stars (flagged - non-flagged)", color="#2b6cb0")
    ax2.plot(x, per_q["forks_count_diff"], "s-", label="Forks (flagged - non-flagged)", color="#805ad5")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(per_q["quarter"], rotation=45)
    ax2.set_ylabel("median difference (AI-flagged minus non-flagged)")
    ax2.set_title("Stratified by quarter, 2025Q1-2026Q3\nno consistent direction (Wilcoxon p=0.69 both)")
    ax2.legend(fontsize=8)

    fig.suptitle("Does the naive popularity gap survive controlling for calendar time? No.", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(CHARTS_DIR / "naive_vs_stratified.png", dpi=150)
    plt.close(fig)


def chart_top20_overlap() -> None:
    import json
    with open(OUT_DIR / "top20_overlap.json") as f:
        data = json.load(f)["stratified_2025Q1_2026Q3"]

    ai_only = data["ai_only"]
    non_only = data["non_flagged_only"]
    shared_n = len(data["shared"])

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.axis("off")
    ax.set_title(f"Top-20 most-depended-on packages, AI-flagged vs. non-flagged\n"
                 f"(2025Q1-2026Q3, Jaccard similarity = {data['jaccard']:.2f}, {shared_n}/20 shared)",
                 fontsize=11)

    col_x = [0.02, 0.36, 0.70]
    headers = [f"AI-flagged only ({len(ai_only)})", f"Shared ({shared_n})", f"Non-flagged only ({len(non_only)})"]
    cols = [ai_only, data["shared"], non_only]
    colors = ["#2b6cb0", "#718096", "#dd6b20"]

    for cx, header, col, color in zip(col_x, headers, cols, colors):
        ax.text(cx, 0.95, header, fontsize=10, fontweight="bold", color=color, transform=ax.transAxes)
        for i, name in enumerate(sorted(col)):
            ax.text(cx, 0.88 - i * 0.06, name, fontsize=9, transform=ax.transAxes)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "top20_overlap.png", dpi=150)
    plt.close(fig)


def main() -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_naive_vs_stratified()
    chart_top20_overlap()
    print("Wrote charts to", CHARTS_DIR)


if __name__ == "__main__":
    main()
