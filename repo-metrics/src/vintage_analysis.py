"""Aggregate output/vintage/packages.csv (one row per package, ~10 per
vintage quarter) into one row per vintage quarter: median/mean/IQR across
that quarter's sampled packages, for each metric.

Median is the headline statistic here, not mean: with only 7-10 packages
per quarter, a handful of commits per young package, and metrics like hunk
size that are already outlier-prone even at full-history scale (see
REPORT.md's Family 4 discussion in the calendar-time study), one unlucky
package's early bulk-import commit can dominate a per-quarter mean. Medians
survive that; the code still reports both.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import percentile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VINTAGE_DIR = ROOT / "output" / "vintage"
ANALYSIS_DIR = VINTAGE_DIR / "analysis"

METRICS = [
    "state_mean_func_len", "state_mean_body_len",
    "state_mean_complexity", "state_median_complexity",
    "state_mean_comment_len", "state_parse_rate",
    "state_mean_docstring_len", "state_frac_functions_with_docstring",
    "flow_mean_added_comment_len", "flow_median_hunk_added",
    "flow_median_added_code_lines_per_commit", "flow_n_commits",
    "flow_n_contributors",
]


def _agg_col(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"mean": np.nan, "median": np.nan, "p25": np.nan, "p75": np.nan}
    return {
        "mean": s.mean(),
        "median": s.median(),
        "p25": percentile(list(s), 25),
        "p75": percentile(list(s), 75),
    }


def build_vintage_quarterly(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for quarter, g in df.groupby("vintage_quarter"):
        row = {"vintage_quarter": quarter, "n_packages": len(g)}
        for m in METRICS:
            stats = _agg_col(g[m])
            row.update({f"{m}__{k}": v for k, v in stats.items()})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("vintage_quarter").reset_index(drop=True)


def trend_summary(vq: pd.DataFrame) -> pd.DataFrame:
    """Simple linear trend (slope per quarter-index, and total % change
    first-decile vs last-decile of quarters) per metric, for the headline
    numbers in the report.
    """
    quarters = vq["vintage_quarter"].tolist()
    x = np.arange(len(quarters))
    rows = []
    for m in METRICS:
        y = vq[f"{m}__median"].values
        mask = ~np.isnan(y)
        if mask.sum() < 10:
            continue
        slope, intercept = np.polyfit(x[mask], y[mask], 1)
        early = np.nanmedian(y[:8])
        late = np.nanmedian(y[-8:])
        pct_change = (late - early) / early * 100 if early else np.nan
        rows.append({
            "metric": m, "early_median(first 8Q)": early, "late_median(last 8Q)": late,
            "pct_change": pct_change, "slope_per_quarter": slope,
        })
    return pd.DataFrame(rows)


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(VINTAGE_DIR / "packages.csv")
    print(f"Loaded {len(df)} packages across {df['vintage_quarter'].nunique()} vintage quarters.")

    vq = build_vintage_quarterly(df)
    vq.to_csv(ANALYSIS_DIR / "vintage_quarterly.csv", index=False)
    print(f"Wrote {len(vq)} vintage-quarter rows.")

    trend = trend_summary(vq)
    trend.to_csv(ANALYSIS_DIR / "vintage_trend_summary.csv", index=False)
    pd.set_option("display.width", 160)
    print(trend.to_string(index=False))


if __name__ == "__main__":
    main()
