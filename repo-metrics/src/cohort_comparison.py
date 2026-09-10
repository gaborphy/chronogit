"""Does removing the star-sampling bias change any conclusion?

Compares the original GitHub-star-ranked vintage cohort
(output/vintage/packages.csv, output/ai_signal/ai_signals.csv) against
the new unbiased cohort sampled directly from the full PyPI population
(output/vintage_unbiased/packages.csv, output/ai_signal_unbiased/ai_signals.csv)
-- same target size (30/quarter), same extraction machinery, same
metrics, different discovery source. See vintage_discover_unbiased.py
and vintage_extract_unbiased.py for the discovery/extraction method and
its deliberate differences from the original (PyPI-release-anchored
vintage instead of first-git-commit-anchored).

Two questions, matching the two halves of the existing report pair:
  1. Structural/flow trend comparison (vs. VINTAGE_REPORT.md) -- do the
     same metrics move the same way over calendar time in both cohorts?
  2. AI-tool self-disclosed adoption-rate comparison (vs.
     AI_USAGE_REPORT.md) -- same adoption curve, or does star-sampling
     bias distort it (e.g. more-visible repos disclosing AI usage at a
     different rate than the true population)?

Deliberately does NOT re-run the dependency-popularity case-control
study (DEPENDENCY_REPORT.md) or the AI-dependency-network comparison
(AI_DEPENDENCY_NETWORK_REPORT.md) on the unbiased cohort -- both need an
additional deps_extract.py + deps_popularity.py pass (per-dependency
ecosyste.ms lookups), a separately-scoped, separately-expensive step not
attempted here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import percentile  # noqa: E402
from vintage_analysis import METRICS, build_vintage_quarterly  # noqa: E402
from ai_signal_analysis import load as load_ai_signals, cohort_adoption  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "cohort_comparison"


def compare_vintage_trends() -> pd.DataFrame:
    star = pd.read_csv(ROOT / "output" / "vintage" / "packages.csv")
    unbiased = pd.read_csv(ROOT / "output" / "vintage_unbiased" / "packages.csv")

    star_vq = build_vintage_quarterly(star)
    unbiased_vq = build_vintage_quarterly(unbiased)

    rows = []
    for m in METRICS:
        merged = star_vq[["vintage_quarter", f"{m}__median"]].merge(
            unbiased_vq[["vintage_quarter", f"{m}__median"]],
            on="vintage_quarter", suffixes=("_star", "_unbiased"),
        ).dropna()
        if len(merged) < 10:
            continue
        x = np.arange(len(star_vq))
        y_star = star_vq[f"{m}__median"].values.astype(float)
        mask_star = ~np.isnan(y_star)
        rho_star, p_star = stats.spearmanr(x[mask_star], y_star[mask_star])

        x2 = np.arange(len(unbiased_vq))
        y_unb = unbiased_vq[f"{m}__median"].values.astype(float)
        mask_unb = ~np.isnan(y_unb)
        rho_unb, p_unb = stats.spearmanr(x2[mask_unb], y_unb[mask_unb])

        # do the two cohorts' quarterly medians move together?
        cross_rho, cross_p = stats.spearmanr(
            merged[f"{m}__median_star"], merged[f"{m}__median_unbiased"]
        )
        early_star = np.nanmedian(y_star[:8])
        late_star = np.nanmedian(y_star[-8:])
        early_unb = np.nanmedian(y_unb[:8])
        late_unb = np.nanmedian(y_unb[-8:])
        rows.append({
            "metric": m,
            "star_trend_rho": rho_star, "star_trend_p": p_star,
            "star_pct_change": (late_star - early_star) / early_star * 100 if early_star else np.nan,
            "unbiased_trend_rho": rho_unb, "unbiased_trend_p": p_unb,
            "unbiased_pct_change": (late_unb - early_unb) / early_unb * 100 if early_unb else np.nan,
            "same_trend_direction": np.sign(rho_star) == np.sign(rho_unb),
            "cross_cohort_quarterly_rho": cross_rho, "cross_cohort_quarterly_p": cross_p,
            "n_quarters_compared": len(merged),
        })
    return pd.DataFrame(rows)


def compare_ai_adoption() -> pd.DataFrame:
    star = load_ai_signals()  # default paths point at output/ai_signal
    star_by_year = cohort_adoption(star, "year")

    unbiased_path = ROOT / "output" / "ai_signal_unbiased" / "ai_signals.csv"
    unb = pd.read_csv(unbiased_path)
    unb["year"] = unb["vintage_quarter"].str[:4].astype(int)
    unb["has_ai_commit"] = unb["ai_commits"] > 0
    unb["has_marker_file"] = unb["marker_files_found"].fillna("").str.len() > 0
    unb["has_any_signal"] = unb["has_ai_commit"] | unb["has_marker_file"]
    unb_by_year = cohort_adoption(unb, "year")

    merged = star_by_year[["year", "n_packages", "adoption_rate"]].merge(
        unb_by_year[["year", "n_packages", "adoption_rate"]],
        on="year", suffixes=("_star", "_unbiased"),
    )
    merged["diff_pp"] = (merged["adoption_rate_unbiased"] - merged["adoption_rate_star"]) * 100
    return merged


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trend_cmp = compare_vintage_trends()
    trend_cmp.to_csv(OUT_DIR / "vintage_trend_comparison.csv", index=False)
    pd.set_option("display.width", 200)
    print("=== Vintage structural/flow trend comparison (star-sampled vs. unbiased) ===")
    print(trend_cmp.to_string(index=False))

    ai_cmp = compare_ai_adoption()
    ai_cmp.to_csv(OUT_DIR / "ai_adoption_comparison.csv", index=False)
    print("\n=== AI self-disclosed adoption rate by year (star-sampled vs. unbiased) ===")
    print(ai_cmp.to_string(index=False))


if __name__ == "__main__":
    main()
