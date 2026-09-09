"""Test the hypothesis: packages with more stars/forks/contributors are
more likely to show up in a newborn package's dependency list.

Design: case-control, not just description. "Dependencies are popular" is
almost true by construction (of course requests/numpy/click show up) --
the actual test is whether the SET of packages used as a dependency is
drawn from a more popular population than a random PyPI package would be.
That needs the baseline sample, not just the dependency list on its own.

Two complementary views:
  1. Case-control: dependency-set popularity distribution vs. baseline
     popularity distribution (Mann-Whitney U + common-language effect size,
     since both are extremely heavy-tailed -- means/t-tests would be
     dominated by a handful of giants like requests/numpy).
  2. Fan-in: among only the dependency set, does a package used by MORE
     newborn packages (higher fan-in) tend to have more stars/forks/
     committers than one used by just one? (Spearman correlation --
     monotonic, not linear, again because of the heavy tail.)
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
ANALYSIS_DIR = DEPS_DIR / "analysis"

METRICS = ["stargazers_count", "forks_count", "total_committers"]


def load_data():
    edges = pd.read_csv(DEPS_DIR / "edges.csv")
    pop = pd.read_csv(DEPS_DIR / "dependency_popularity.csv")
    baseline = pd.read_csv(DEPS_DIR / "baseline_popularity.csv")
    return edges, pop, baseline


def fan_in_table(edges: pd.DataFrame) -> pd.DataFrame:
    fan_in = (
        edges.groupby("dependency_name")["newborn_repo"]
        .nunique()
        .rename("fan_in")
        .reset_index()
    )
    return fan_in.sort_values("fan_in", ascending=False)


def summarize(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"n": 0, "mean": np.nan, "median": np.nan, "p25": np.nan, "p75": np.nan, "p90": np.nan}
    return {
        "n": len(s),
        "mean": s.mean(),
        "median": s.median(),
        "p25": percentile(list(s), 25),
        "p75": percentile(list(s), 75),
        "p90": percentile(list(s), 90),
    }


def case_control_test(dep_pop: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for m in METRICS:
        a = dep_pop[m].dropna()
        b = baseline[m].dropna()
        if len(a) < 5 or len(b) < 5:
            continue
        u_stat, p_value = stats.mannwhitneyu(a, b, alternative="greater")
        # common-language effect size: P(a random dependency > a random baseline package)
        cle = u_stat / (len(a) * len(b))
        rows.append({
            "metric": m,
            "dep_n": len(a), "dep_median": a.median(), "dep_mean": a.mean(),
            "baseline_n": len(b), "baseline_median": b.median(), "baseline_mean": b.mean(),
            "median_ratio": (a.median() / b.median()) if b.median() else np.nan,
            "mannwhitney_p": p_value,
            "common_language_effect_size": cle,
        })
    return pd.DataFrame(rows)


def fan_in_correlation(dep_pop: pd.DataFrame, fan_in: pd.DataFrame) -> pd.DataFrame:
    merged = dep_pop.merge(fan_in, left_on="name", right_on="dependency_name", how="inner")
    rows = []
    for m in METRICS:
        sub = merged.dropna(subset=[m, "fan_in"])
        if len(sub) < 10:
            continue
        rho, p = stats.spearmanr(sub["fan_in"], sub[m])
        rows.append({"metric": m, "n": len(sub), "spearman_rho": rho, "p_value": p})
    return pd.DataFrame(rows)


def tier_breakdown(dep_pop: pd.DataFrame, baseline: pd.DataFrame, metric: str,
                    bins=(0, 10, 100, 1000, 10_000, np.inf),
                    labels=("0-10", "10-100", "100-1k", "1k-10k", "10k+")) -> pd.DataFrame:
    def tiered(df):
        s = pd.cut(df[metric].fillna(0), bins=bins, labels=labels, right=False)
        return s.value_counts(normalize=True).reindex(labels).fillna(0)

    dep_t = tiered(dep_pop)
    base_t = tiered(baseline)
    return pd.DataFrame({"dependency_set": dep_t, "baseline_set": base_t})


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    edges, pop, baseline = load_data()

    pop_found = pop[pop["found"] == True].copy()  # noqa: E712
    baseline_found = baseline[baseline["found"] == True].copy()  # noqa: E712
    print(f"Dependency names resolved: {len(pop_found)}/{len(pop)}")
    print(f"Baseline packages resolved: {len(baseline_found)}/{len(baseline)}")

    fan_in = fan_in_table(edges)
    fan_in.to_csv(ANALYSIS_DIR / "fan_in.csv", index=False)

    summary_rows = []
    for label, df in [("dependency_set", pop_found), ("baseline_set", baseline_found)]:
        for m in METRICS:
            summary_rows.append({"group": label, "metric": m, **summarize(df[m])})
    pd.DataFrame(summary_rows).to_csv(ANALYSIS_DIR / "group_summary.csv", index=False)

    cc = case_control_test(pop_found, baseline_found)
    cc.to_csv(ANALYSIS_DIR / "case_control_test.csv", index=False)
    print("\nCase-control test (dependency set vs. random-PyPI baseline):")
    pd.set_option("display.width", 160)
    print(cc.to_string(index=False))

    fic = fan_in_correlation(pop_found, fan_in)
    fic.to_csv(ANALYSIS_DIR / "fan_in_correlation.csv", index=False)
    print("\nFan-in vs. popularity (Spearman, within the dependency set only):")
    print(fic.to_string(index=False))

    for m in ["stargazers_count", "forks_count"]:
        tiers = tier_breakdown(pop_found, baseline_found, m)
        tiers.to_csv(ANALYSIS_DIR / f"tiers_{m}.csv")
        print(f"\n{m} tier breakdown:")
        print(tiers.to_string())

    top20 = fan_in.merge(pop_found, left_on="dependency_name", right_on="name", how="left").head(20)
    top20.to_csv(ANALYSIS_DIR / "top20_most_depended_on.csv", index=False)
    print("\nTop 20 most-depended-on packages:")
    print(top20[["dependency_name", "fan_in", "stargazers_count", "forks_count", "total_committers"]].to_string(index=False))


if __name__ == "__main__":
    main()
