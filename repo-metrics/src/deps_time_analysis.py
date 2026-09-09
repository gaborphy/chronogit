"""Is the popularity effect from DEPENDENCY_REPORT.md getting stronger over
time, and specifically: are recent newborn-package cohorts converging on a
smaller set of already-famous dependencies rather than spreading their
choices across a more diverse set, the way older cohorts did?

Two distinct things, deliberately kept separate:

  1. POPULARITY of chosen dependencies, by cohort. Confounded and flagged
     as such: stars are measured *today* (2026), not at the moment each
     cohort actually chose its dependencies, so a rising trend here
     partly reflects "the packages people picked back then went on to
     become popular since" as much as "people increasingly pick already-
     popular packages." Presented anyway because it's the natural first
     look, with the confound stated up front rather than after the chart.

  2. CONCENTRATION of chosen dependencies, by cohort -- how many distinct
     packages a cohort's edges spread across, independent of any point-in-
     time popularity measurement at all. This is the less-confounded test
     of "are newer cohorts converging on the same handful of packages":
     it only needs *this dataset's own* edge counts, no historical star
     data. Herfindahl-Hirschman Index (HHI) of each cohort's dependency-
     name shares, plus the share of a cohort's edges going to the (global,
     all-cohort) top-20 most-depended-on packages from
     output/deps/analysis/top20_most_depended_on.csv.

A robustness check re-runs both after excluding a curated list of LLM/genAI
SDK packages (openai, transformers, langchain, ...) -- if concentration is
rising only because more *recent packages are themselves AI wrappers* that
mechanically share 2-3 SDK imports, that's a topic-composition effect, not
evidence of AI-assisted authorship converging imports across the board.
Both are left in the report; this dataset can't distinguish "written by an
AI coding assistant" from "written by a human building on top of an AI
API" -- neither is measured here (that needs the function-level AI
detector elsewhere in this project, not this corpus-wide edge count).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DEPS_DIR = ROOT / "output" / "deps"
ANALYSIS_DIR = DEPS_DIR / "analysis"
TIME_DIR = DEPS_DIR / "analysis_time"

# LLM/genAI SDK packages, for the "is this just topic composition" check.
# Deliberately excludes generic ML frameworks (torch, tensorflow, scikit-learn)
# that predate and extend well beyond the recent LLM-app wave.
AI_SDK_PACKAGES = {
    "openai", "anthropic", "transformers", "langchain", "langchain-core",
    "langchain-community", "langchain-openai", "llama-index", "llama-index-core",
    "tiktoken", "huggingface-hub", "sentence-transformers", "cohere",
    "mistralai", "google-generativeai", "ollama", "chromadb", "pinecone-client",
    "faiss-cpu", "accelerate", "diffusers", "openai-whisper", "guidance",
    "instructor", "litellm", "vllm", "google-genai", "groq",
}


def load_data():
    edges = pd.read_csv(DEPS_DIR / "edges.csv")
    pop = pd.read_csv(DEPS_DIR / "dependency_popularity.csv")
    top20 = set(pd.read_csv(ANALYSIS_DIR / "top20_most_depended_on.csv")["dependency_name"])
    edges["year"] = edges["vintage_quarter"].str[:4].astype(int)
    return edges, pop, top20


def _hhi(counts: pd.Series) -> float:
    shares = counts / counts.sum()
    return float((shares ** 2).sum())


def cohort_stats(edges: pd.DataFrame, pop: pd.DataFrame, top20: set, group_col: str) -> pd.DataFrame:
    pop_map = pop.set_index("name")
    rows = []
    for cohort, g in edges.groupby(group_col):
        counts = g["dependency_name"].value_counts()
        n_edges = len(g)
        n_unique = g["dependency_name"].nunique()

        merged = g.merge(pop_map[["stargazers_count", "forks_count", "total_committers"]],
                          left_on="dependency_name", right_index=True, how="left")

        rows.append({
            group_col: cohort,
            "n_edges": n_edges,
            "n_unique_deps": n_unique,
            "unique_ratio": n_unique / n_edges,
            "hhi": _hhi(counts),
            "share_edges_to_global_top20": g["dependency_name"].isin(top20).mean(),
            "median_dep_stars": merged["stargazers_count"].median(),
            "mean_dep_stars": merged["stargazers_count"].mean(),
            "median_dep_forks": merged["forks_count"].median(),
            "median_dep_committers": merged["total_committers"].median(),
        })
    return pd.DataFrame(rows).sort_values(group_col).reset_index(drop=True)


def rarefied_diversity(edges: pd.DataFrame, group_col: str, n_draw: int = 140,
                        n_reps: int = 500, seed: int = 42) -> pd.DataFrame:
    """Controls for the sample-size confound in unique_ratio: as edge count
    grows, unique-names/edges shrinks almost mechanically even under a
    UNCHANGED selection process (more draws -> more repeat collisions on
    already-seen names, a birthday-paradox effect), so a naive ratio trend
    can look like "rising concentration" when it's really just "more data."
    Standard ecological fix: repeatedly subsample the SAME number of edges
    from every cohort and compare the average unique-name count recovered
    at that fixed sample size -- an apples-to-apples diversity comparison.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for cohort, g in edges.groupby(group_col):
        names = g["dependency_name"].to_numpy()
        if len(names) < n_draw:
            continue
        unique_counts = [
            len(np.unique(rng.choice(names, size=n_draw, replace=False)))
            for _ in range(n_reps)
        ]
        rows.append({
            group_col: cohort,
            "n_draw": n_draw,
            "n_edges_available": len(names),
            "rarefied_unique_at_n": float(np.mean(unique_counts)),
            "rarefied_unique_std": float(np.std(unique_counts)),
        })
    return pd.DataFrame(rows).sort_values(group_col).reset_index(drop=True)


def trend_test(df: pd.DataFrame, x_col: str, metrics: list[str]) -> pd.DataFrame:
    x = df[x_col].astype(float).values if df[x_col].dtype != object else np.arange(len(df))
    if df[x_col].dtype == object:
        x = np.arange(len(df))  # quarter labels -> ordinal index
    rows = []
    for m in metrics:
        y = df[m].values
        mask = ~np.isnan(y)
        if mask.sum() < 5:
            continue
        slope, intercept, r, p, se = stats.linregress(x[mask], y[mask])
        rho, rho_p = stats.spearmanr(x[mask], y[mask])
        rows.append({
            "metric": m,
            "first_value": y[mask][0], "last_value": y[mask][-1],
            "ols_slope_per_period": slope, "ols_r2": r ** 2, "ols_p": p,
            "spearman_rho": rho, "spearman_p": rho_p,
        })
    return pd.DataFrame(rows)


def main() -> None:
    TIME_DIR.mkdir(parents=True, exist_ok=True)
    edges, pop, top20 = load_data()

    metrics = ["unique_ratio", "hhi", "share_edges_to_global_top20",
               "median_dep_stars", "mean_dep_stars", "median_dep_forks", "median_dep_committers"]

    print("=== By vintage quarter (all edges) ===")
    by_q = cohort_stats(edges, pop, top20, "vintage_quarter")
    by_q.to_csv(TIME_DIR / "by_quarter_all.csv", index=False)
    t_q = trend_test(by_q, "vintage_quarter", metrics)
    t_q.to_csv(TIME_DIR / "trend_by_quarter_all.csv", index=False)
    pd.set_option("display.width", 160)
    print(t_q.to_string(index=False))

    print("\n=== By year (all edges) ===")
    by_y = cohort_stats(edges, pop, top20, "year")
    by_y.to_csv(TIME_DIR / "by_year_all.csv", index=False)
    t_y = trend_test(by_y, "year", metrics)
    t_y.to_csv(TIME_DIR / "trend_by_year_all.csv", index=False)
    print(t_y.to_string(index=False))
    print(by_y.to_string(index=False))

    print("\n=== Rarefied diversity (fixed sample size, controls for volume growth) ===")
    raref = rarefied_diversity(edges, "year", n_draw=400)  # smallest year (2015) has 404 edges at 30/quarter scale
    raref.to_csv(TIME_DIR / "rarefied_diversity_by_year.csv", index=False)
    t_raref = trend_test(raref, "year", ["rarefied_unique_at_n"])
    t_raref.to_csv(TIME_DIR / "trend_rarefied_diversity.csv", index=False)
    print(raref.to_string(index=False))
    print(t_raref.to_string(index=False))

    print("\n=== Robustness: excluding AI/genAI SDK packages ===")
    edges_no_ai = edges[~edges["dependency_name"].isin(AI_SDK_PACKAGES)].copy()
    n_ai_edges = len(edges) - len(edges_no_ai)
    print(f"Excluded {n_ai_edges}/{len(edges)} edges pointing at an AI/genAI SDK package.")

    by_y_no_ai = cohort_stats(edges_no_ai, pop, top20, "year")
    by_y_no_ai.to_csv(TIME_DIR / "by_year_no_ai_sdk.csv", index=False)
    t_y_no_ai = trend_test(by_y_no_ai, "year", metrics)
    t_y_no_ai.to_csv(TIME_DIR / "trend_by_year_no_ai_sdk.csv", index=False)
    print(t_y_no_ai.to_string(index=False))

    # how much of the AI-SDK edges are concentrated in recent years?
    ai_edges = edges[edges["dependency_name"].isin(AI_SDK_PACKAGES)]
    print("\nAI/genAI SDK edges by year:")
    print(ai_edges.groupby("year").size().to_string())


if __name__ == "__main__":
    main()
