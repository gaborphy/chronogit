"""Plan A from the cl_ecosystem_networks synthesis: do AI-flagged newborn
packages build their dependency networks differently than otherwise-
comparable non-flagged ones, restricted to the 2024-2026 window (before
that, self-disclosed AI-tool usage is ~0%, so an unrestricted comparison
would just reproduce the calendar-time trend already documented in
DEPENDENCY_REPORT.md's time-dimension section, not test this hypothesis).

Critical confound, checked and handled explicitly: within 2024-2026,
"AI-flagged" and "later quarter" are nearly the same variable (2024Q1 has
0/30 flagged; 2026Q1 has 25/30). A pooled comparison across the whole
window would mostly measure the already-known time trend, not an AI
effect. Two views, both reported:

  1. Naive pooled 2024-2026 comparison -- shown for transparency, labeled
     confounded, not trusted as the answer.
  2. Stratified-by-quarter comparison (2025Q1-2026Q3, the 8 quarters with
     a usable number of packages in BOTH groups): compute the flagged-vs-
     non-flagged difference WITHIN each quarter separately, then test
     whether the direction is consistent across quarters (Wilcoxon
     signed-rank on paired per-quarter medians) -- this is the
     deconfounded test.

Also compares WHICH specific packages each group depends on (Jaccard
overlap of top dependencies per quarter) -- directly addresses "evolving
in a different dependency network way," not just "different popularity."
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import percentile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEPS_DIR = ROOT / "output" / "deps"
AI_SIGNAL_DIR = ROOT / "output" / "ai_signal"
OUT_DIR = DEPS_DIR / "analysis_ai_comparison"

STRATIFIED_QUARTERS = [f"{y}Q{q}" for y in (2025, 2026) for q in (1, 2, 3, 4)
                       if not (y == 2026 and q == 4)]  # 2025Q1..2026Q3


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sig = pd.read_csv(AI_SIGNAL_DIR / "ai_signals.csv")
    sig["has_signal"] = (sig["ai_commits"] > 0) | (sig["marker_files_found"].fillna("").str.len() > 0)
    edges = pd.read_csv(DEPS_DIR / "edges.csv")
    pop = pd.read_csv(DEPS_DIR / "dependency_popularity.csv")
    pop_map = pop.set_index("name")[["stargazers_count", "forks_count", "total_committers"]]

    merged = edges.merge(sig[["repo_full_name", "has_signal"]],
                          left_on="newborn_repo", right_on="repo_full_name", how="inner")
    merged = merged.merge(pop_map, left_on="dependency_name", right_index=True, how="left")
    return sig, edges, merged


def group_summary(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for flagged, g in df.groupby("has_signal"):
        row = {"group": "AI-flagged" if flagged else "non-flagged", "n_edges": len(g),
               "n_packages": g["newborn_repo"].nunique()}
        for m in metrics:
            row[f"{m}_median"] = g[m].median()
            row[f"{m}_mean"] = g[m].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def mannwhitney_two_group(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    a = df[df["has_signal"]]
    b = df[~df["has_signal"]]
    rows = []
    for m in metrics:
        x, y = a[m].dropna(), b[m].dropna()
        if len(x) < 5 or len(y) < 5:
            continue
        u, p = stats.mannwhitneyu(x, y, alternative="two-sided")
        cle = u / (len(x) * len(y))
        rows.append({
            "metric": m, "ai_flagged_median": x.median(), "non_flagged_median": y.median(),
            "ai_flagged_n": len(x), "non_flagged_n": len(y),
            "mannwhitney_p": p, "common_language_effect_size": cle,
        })
    return pd.DataFrame(rows)


def diversity_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for flagged, g in df.groupby("has_signal"):
        counts = g["dependency_name"].value_counts()
        n_edges = len(g)
        n_unique = g["dependency_name"].nunique()
        shares = counts / counts.sum()
        rows.append({
            "group": "AI-flagged" if flagged else "non-flagged",
            "n_edges": n_edges, "n_unique_deps": n_unique,
            "unique_ratio": n_unique / n_edges if n_edges else np.nan,
            "hhi": float((shares ** 2).sum()),
        })
    return pd.DataFrame(rows)


def rarefied_diversity_two_group(df: pd.DataFrame, n_draw: int, n_reps: int = 500, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    out = {}
    for flagged, g in df.groupby("has_signal"):
        names = g["dependency_name"].to_numpy()
        label = "AI-flagged" if flagged else "non-flagged"
        if len(names) < n_draw:
            out[label] = None
            continue
        counts = [len(np.unique(rng.choice(names, size=n_draw, replace=False))) for _ in range(n_reps)]
        out[label] = {"n_available": len(names), "rarefied_unique_at_n": float(np.mean(counts)),
                       "rarefied_unique_std": float(np.std(counts))}
    return out


def stratified_test(edges_full: pd.DataFrame, sig: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Within each quarter in STRATIFIED_QUARTERS, compute AI-flagged vs
    non-flagged group medians separately, then Wilcoxon signed-rank on the
    paired per-quarter differences -- deconfounds the AI signal from the
    calendar-time trend already documented elsewhere in this project.
    """
    pop = pd.read_csv(DEPS_DIR / "dependency_popularity.csv").set_index("name")
    sig_q = sig[["repo_full_name", "vintage_quarter", "has_signal"]]

    e = edges_full.merge(sig_q.rename(columns={"repo_full_name": "newborn_repo"}),
                          on="newborn_repo", how="inner", suffixes=("", "_sig"))
    e = e[e["vintage_quarter"].isin(STRATIFIED_QUARTERS)]
    e = e.merge(pop[["stargazers_count", "forks_count", "total_committers"]],
                left_on="dependency_name", right_index=True, how="left")

    per_quarter = []
    for q in STRATIFIED_QUARTERS:
        qg = e[e["vintage_quarter"] == q]
        flagged = qg[qg["has_signal"]]
        nonflagged = qg[~qg["has_signal"]]
        if flagged["newborn_repo"].nunique() < 3 or nonflagged["newborn_repo"].nunique() < 3:
            continue
        row = {"quarter": q,
               "n_pkgs_flagged": flagged["newborn_repo"].nunique(),
               "n_pkgs_nonflagged": nonflagged["newborn_repo"].nunique()}
        for m in metrics:
            row[f"{m}_flagged_median"] = flagged[m].median()
            row[f"{m}_nonflagged_median"] = nonflagged[m].median()
            row[f"{m}_diff"] = flagged[m].median() - nonflagged[m].median()
        per_quarter.append(row)

    return pd.DataFrame(per_quarter)


def wilcoxon_on_diffs(per_quarter: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for m in metrics:
        diffs = per_quarter[f"{m}_diff"].dropna()
        if len(diffs) < 4:
            continue
        n_pos = (diffs > 0).sum()
        n_neg = (diffs < 0).sum()
        try:
            stat, p = stats.wilcoxon(diffs)
        except ValueError:
            stat, p = np.nan, np.nan
        rows.append({"metric": m, "n_quarters": len(diffs), "n_quarters_ai_higher": int(n_pos),
                     "n_quarters_ai_lower": int(n_neg), "median_diff": diffs.median(),
                     "wilcoxon_p": p})
    return pd.DataFrame(rows)


def dependency_breadth(sig: pd.DataFrame, edges: pd.DataFrame, quarters: list[str]) -> pd.DataFrame:
    """Mean/median number of dependencies declared per package, flagged vs not."""
    counts = edges.groupby("newborn_repo").size().rename("n_deps")
    s = sig[sig["vintage_quarter"].isin(quarters)][["repo_full_name", "has_signal"]].copy()
    s = s.merge(counts, left_on="repo_full_name", right_index=True, how="left")
    s["n_deps"] = s["n_deps"].fillna(0)
    rows = []
    for flagged, g in s.groupby("has_signal"):
        rows.append({"group": "AI-flagged" if flagged else "non-flagged",
                      "n_packages": len(g), "mean_n_deps": g["n_deps"].mean(),
                      "median_n_deps": g["n_deps"].median(), "frac_zero_deps": (g["n_deps"] == 0).mean()})
    return pd.DataFrame(rows)


def top_dependency_overlap(df: pd.DataFrame, k: int = 20) -> dict:
    tops = {}
    for flagged, g in df.groupby("has_signal"):
        label = "AI-flagged" if flagged else "non-flagged"
        tops[label] = set(g["dependency_name"].value_counts().head(k).index)
    a, b = tops.get("AI-flagged", set()), tops.get("non-flagged", set())
    jaccard = len(a & b) / len(a | b) if (a | b) else np.nan
    return {"ai_flagged_top20": sorted(a), "non_flagged_top20": sorted(b),
            "shared": sorted(a & b), "ai_only": sorted(a - b), "non_flagged_only": sorted(b - a),
            "jaccard": jaccard}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sig, edges, merged = load()
    metrics = ["stargazers_count", "forks_count", "total_committers"]

    recent = merged[merged["vintage_quarter"].str[:4].astype(int) >= 2024]
    print(f"2024-2026 window: {recent['newborn_repo'].nunique()} packages, {len(recent)} edges")

    print("\n=== NAIVE pooled 2024-2026 comparison (CONFOUNDED with time -- see stratified test below) ===")
    naive_summary = group_summary(recent, metrics)
    naive_summary.to_csv(OUT_DIR / "naive_group_summary.csv", index=False)
    print(naive_summary.to_string(index=False))

    naive_mw = mannwhitney_two_group(recent, metrics)
    naive_mw.to_csv(OUT_DIR / "naive_mannwhitney.csv", index=False)
    print(naive_mw.to_string(index=False))

    naive_div = diversity_stats(recent)
    naive_div.to_csv(OUT_DIR / "naive_diversity.csv", index=False)
    print(naive_div.to_string(index=False))

    n_draw = int(recent.groupby("has_signal").size().min())
    n_draw = max(50, n_draw - 10)
    raref = rarefied_diversity_two_group(recent, n_draw=n_draw)
    print(f"\nRarefied diversity (naive pooled, n_draw={n_draw}):", raref)

    print("\n=== STRATIFIED-BY-QUARTER comparison (deconfounded), 2025Q1-2026Q3 ===")
    per_q = stratified_test(edges, sig, metrics)
    per_q.to_csv(OUT_DIR / "stratified_per_quarter.csv", index=False)
    print(per_q.to_string(index=False))

    wilcoxon_res = wilcoxon_on_diffs(per_q, metrics)
    wilcoxon_res.to_csv(OUT_DIR / "stratified_wilcoxon.csv", index=False)
    print("\nWilcoxon signed-rank on paired per-quarter (flagged - non-flagged) differences:")
    print(wilcoxon_res.to_string(index=False))

    print("\n=== Dependency breadth (# deps declared per package) ===")
    breadth_all = dependency_breadth(sig, edges, sig[sig["vintage_quarter"].str[:4].astype(int) >= 2024]["vintage_quarter"].unique().tolist())
    breadth_all.to_csv(OUT_DIR / "breadth_naive_2024_2026.csv", index=False)
    print("Naive (2024-2026):")
    print(breadth_all.to_string(index=False))

    breadth_strat = dependency_breadth(sig, edges, STRATIFIED_QUARTERS)
    breadth_strat.to_csv(OUT_DIR / "breadth_stratified.csv", index=False)
    print("\nStratified window (2025Q1-2026Q3):")
    print(breadth_strat.to_string(index=False))

    print("\n=== Top-20 dependency overlap: same packages, or different ones? ===")
    overlap_naive = top_dependency_overlap(recent)
    print(f"Naive pooled 2024-2026: Jaccard={overlap_naive['jaccard']:.3f}")
    print("AI-only top20:", overlap_naive["ai_only"])
    print("Non-flagged-only top20:", overlap_naive["non_flagged_only"])

    recent_strat = merged[merged["vintage_quarter"].isin(STRATIFIED_QUARTERS)]
    overlap_strat = top_dependency_overlap(recent_strat)
    print(f"\nStratified window 2025Q1-2026Q3: Jaccard={overlap_strat['jaccard']:.3f}")
    print("AI-only top20:", overlap_strat["ai_only"])
    print("Non-flagged-only top20:", overlap_strat["non_flagged_only"])

    import json
    with open(OUT_DIR / "top20_overlap.json", "w") as f:
        json.dump({"naive_2024_2026": overlap_naive, "stratified_2025Q1_2026Q3": overlap_strat}, f, indent=2)


if __name__ == "__main__":
    main()
