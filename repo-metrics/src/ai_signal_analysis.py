"""Aggregate output/ai_signal/ai_signals.csv into cohort-level adoption
rates, and compare against the AI/genAI-SDK-dependency timeline from
deps_time_analysis.py -- does self-disclosed AI-tool usage lead, lag, or
track the "package depends on an AI SDK" signal?
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
AI_SIGNAL_DIR = ROOT / "output" / "ai_signal"
ANALYSIS_DIR = AI_SIGNAL_DIR / "analysis"
DEPS_TIME_DIR = ROOT / "output" / "deps" / "analysis_time"


def load() -> pd.DataFrame:
    df = pd.read_csv(AI_SIGNAL_DIR / "ai_signals.csv")
    df["year"] = df["vintage_quarter"].str[:4].astype(int)
    df["has_ai_commit"] = df["ai_commits"] > 0
    df["has_marker_file"] = df["marker_files_found"].fillna("").str.len() > 0
    df["has_any_signal"] = df["has_ai_commit"] | df["has_marker_file"]
    return df


def cohort_adoption(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for cohort, g in df.groupby(group_col):
        positives = g[g["has_any_signal"]]
        rows.append({
            group_col: cohort,
            "n_packages": len(g),
            "n_with_any_signal": len(positives),
            "adoption_rate": len(positives) / len(g),
            "n_with_commit_evidence": g["has_ai_commit"].sum(),
            "n_with_marker_file": g["has_marker_file"].sum(),
            "mean_ai_commit_fraction_all": g["ai_commit_fraction"].mean(),
            "mean_ai_commit_fraction_among_positive": (
                positives["ai_commit_fraction"].mean() if len(positives) else np.nan
            ),
            "median_total_commits": g["total_commits"].median(),
        })
    return pd.DataFrame(rows).sort_values(group_col).reset_index(drop=True)


def trend_test(df: pd.DataFrame, x_col: str, metrics: list[str]) -> pd.DataFrame:
    x = np.arange(len(df))
    rows = []
    for m in metrics:
        y = df[m].values.astype(float)
        mask = ~np.isnan(y)
        if mask.sum() < 5:
            continue
        slope, intercept, r, p, se = stats.linregress(x[mask], y[mask])
        rho, rho_p = stats.spearmanr(x[mask], y[mask])
        rows.append({
            "metric": m, "first_value": y[mask][0], "last_value": y[mask][-1],
            "ols_slope_per_period": slope, "ols_r2": r ** 2, "ols_p": p,
            "spearman_rho": rho, "spearman_p": rho_p,
        })
    return pd.DataFrame(rows)


def tool_breakdown_by_year(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in df.groupby("year"):
        counter = Counter()
        for tools in g["tools_matched"].fillna(""):
            for t in tools.split(";"):
                if t:
                    counter[t] += 1
        row = {"year": year, "n_packages": len(g)}
        row.update(counter)
        rows.append(row)
    return pd.DataFrame(rows).fillna(0).sort_values("year").reset_index(drop=True)


def compare_with_sdk_timeline(adoption_by_year: pd.DataFrame) -> pd.DataFrame:
    sdk = pd.read_csv(DEPS_TIME_DIR / "by_year_all.csv")[["year", "share_edges_to_global_top20"]]
    # rebuild AI-SDK share by year straight from edges (already computed, but grab n edges too)
    edges = pd.read_csv(ROOT / "output" / "deps" / "edges.csv")
    edges["year"] = edges["vintage_quarter"].str[:4].astype(int)
    from deps_time_analysis import AI_SDK_PACKAGES
    ai_edges = edges[edges["dependency_name"].isin(AI_SDK_PACKAGES)]
    sdk_share = (
        ai_edges.groupby("year").size() / edges.groupby("year").size()
    ).rename("ai_sdk_edge_share").reset_index()

    merged = adoption_by_year.merge(sdk_share, on="year", how="left")
    return merged[["year", "adoption_rate", "ai_sdk_edge_share"]]


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    df = load()
    print(f"Loaded {len(df)} packages. {df['has_any_signal'].sum()} show some AI-tool signal "
          f"({df['has_any_signal'].mean():.1%}).")

    by_year = cohort_adoption(df, "year")
    by_year.to_csv(ANALYSIS_DIR / "adoption_by_year.csv", index=False)
    by_quarter = cohort_adoption(df, "vintage_quarter")
    by_quarter.to_csv(ANALYSIS_DIR / "adoption_by_quarter.csv", index=False)

    metrics = ["adoption_rate", "mean_ai_commit_fraction_all", "median_total_commits"]
    t_year = trend_test(by_year, "year", metrics)
    t_year.to_csv(ANALYSIS_DIR / "trend_by_year.csv", index=False)

    pd.set_option("display.width", 160)
    print("\n=== Adoption by year ===")
    print(by_year.to_string(index=False))
    print("\n=== Trend test (year) ===")
    print(t_year.to_string(index=False))

    tools = tool_breakdown_by_year(df)
    tools.to_csv(ANALYSIS_DIR / "tool_breakdown_by_year.csv", index=False)
    print("\n=== Tool breakdown by year ===")
    print(tools.to_string(index=False))

    cmp = compare_with_sdk_timeline(by_year)
    cmp.to_csv(ANALYSIS_DIR / "adoption_vs_sdk_timeline.csv", index=False)
    print("\n=== Self-disclosed adoption vs. AI-SDK-dependency share, by year ===")
    print(cmp.to_string(index=False))

    outliers = df.sort_values("ai_commit_fraction", ascending=False).head(15)
    outliers.to_csv(ANALYSIS_DIR / "top15_ai_attributed.csv", index=False)
    print("\n=== Top 15 by AI-attributed commit fraction ===")
    print(outliers[["repo_full_name", "vintage_quarter", "ai_commits", "total_commits",
                     "ai_commit_fraction", "tools_matched"]].to_string(index=False))


if __name__ == "__main__":
    main()
