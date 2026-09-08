"""Turn the raw Panel A/B CSVs into the aggregates the report needs:

  - quarterly rollups of Panel A (pooled + excluding the top-volume
    contributor + a contributor-count series), partial trailing quarter
    dropped
  - Panel B combined across repos, partial trailing quarter kept but
    flagged (callers decide whether to show it)
  - repo-fixed-effects pooled series for any metric column
  - simple pre/post break-detection scan across a handful of candidate
    dates, for the event study

Nothing here plots anything -- see charts.py. Nothing here writes prose --
see report.py. This module only produces numbers, and is safe to re-import
and re-run interactively while iterating on the report.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"

_SINCE_TS = pd.Timestamp(config.SINCE, tz="UTC").timestamp()

REPO_ORDER = [
    "pandas", "numpy", "scipy", "scikit-learn", "matplotlib",
    "django", "sqlalchemy", "sympy", "ipython", "pytest",
]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_panel_a(repo: str) -> pd.DataFrame:
    """Load raw Panel A rows for *repo*, strictly clipped to >= config.SINCE.

    `git log --since` does not strictly filter on non-linear history (it
    stops walking a branch once it hits an old-enough commit, but a merged
    branch can still contribute a few commits dated earlier than the
    cutoff) -- consistently under 1% of rows per repo in this sample, not
    a parser bug. The raw CSV keeps them (it's an honest record of what
    `git log` returned); every aggregation clips them here instead.
    """
    df = pd.read_csv(OUTPUT_DIR / f"{repo}_panel_a.csv")
    df = df[df["unix_ts"] >= _SINCE_TS].copy()
    df["dt"] = pd.to_datetime(df["unix_ts"], unit="s", utc=True)
    df["quarter"] = df["dt"].dt.year.astype(str) + "Q" + df["dt"].dt.quarter.astype(str)
    return df


def load_panel_b(repo: str) -> pd.DataFrame:
    df = pd.read_csv(OUTPUT_DIR / f"{repo}_panel_b.csv")
    df["repo"] = repo
    return df


def load_all_panel_b() -> pd.DataFrame:
    return pd.concat([load_panel_b(r) for r in REPO_ORDER], ignore_index=True)


def partial_quarter_for(repo: str, panel_b: Optional[pd.DataFrame] = None) -> Optional[str]:
    """The quarter label Panel B flagged as partial for this repo, if any."""
    df = panel_b if panel_b is not None else load_panel_b(repo)
    partial = df.loc[df["is_partial_quarter"] == 1, "quarter"]
    return partial.iloc[0] if len(partial) else None


# ---------------------------------------------------------------------------
# Top-volume contributor per repo (whole window, all quarters incl. partial)
# ---------------------------------------------------------------------------

def top_contributor(panel_a: pd.DataFrame) -> Dict[str, object]:
    counts = panel_a["author"].value_counts()
    total = len(panel_a)
    top_author = counts.index[0]
    top_n = int(counts.iloc[0])
    return {
        "author": top_author,
        "commits": top_n,
        "total_commits": total,
        "share": top_n / total if total else 0.0,
    }


def build_top_contributors_table() -> pd.DataFrame:
    rows = []
    for repo in REPO_ORDER:
        pa = load_panel_a(repo)
        tc = top_contributor(pa)
        rows.append({"repo": repo, **tc})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Panel A quarterly rollup (pooled + excl-top-contributor + contributor counts)
# ---------------------------------------------------------------------------

def _rollup_group(g: pd.DataFrame) -> dict:
    n_commits = len(g)
    n_contributors = g["author"].nunique()

    total_added_comment_lines = int(g["added_comment_lines"].sum())
    total_added_comment_chars = int(g["added_comment_chars"].sum())
    mean_added_comment_len = (
        total_added_comment_chars / total_added_comment_lines
        if total_added_comment_lines else np.nan
    )

    hunked = g[g["n_hunks"] > 0]
    per_commit_hunk_size = (hunked["hunk_added_sum"] / hunked["n_hunks"]) if len(hunked) else pd.Series(dtype=float)
    median_hunk_size = per_commit_hunk_size.median() if len(per_commit_hunk_size) else np.nan
    mean_hunk_size = per_commit_hunk_size.mean() if len(per_commit_hunk_size) else np.nan

    median_added_code_lines = g["added_code_lines"].median()
    mean_added_code_lines = g["added_code_lines"].mean()

    return {
        "n_commits": n_commits,
        "n_contributors": n_contributors,
        "mean_added_comment_len": mean_added_comment_len,
        "median_hunk_added": median_hunk_size,
        "mean_hunk_added": mean_hunk_size,
        "median_added_code_lines_per_commit": median_added_code_lines,
        "mean_added_code_lines_per_commit": mean_added_code_lines,
        "total_added_code_lines": int(g["added_code_lines"].sum()),
        "total_added_comment_lines": total_added_comment_lines,
        "total_added_blank_lines": int(g["added_blank_lines"].sum()),
        "total_raw_added_lines": int(g["added_lines"].sum()),
        "total_raw_deleted_lines": int(g["deleted_lines"].sum()),
        "total_raw_n_files": int(g["n_files"].sum()),
    }


def quarterly_rollup(repo: str) -> pd.DataFrame:
    """One row per (repo, quarter): pooled_* and excltop_* columns side by
    side, plus n_contributors. Partial trailing quarter is dropped.
    """
    pa = load_panel_a(repo)
    pb = load_panel_b(repo)
    partial_q = partial_quarter_for(repo, pb)
    if partial_q is not None:
        pa = pa[pa["quarter"] != partial_q]

    tc = top_contributor(load_panel_a(repo))  # identified over the FULL window, incl. partial
    top_author = tc["author"]

    rows = []
    for quarter, g in pa.groupby("quarter"):
        pooled = _rollup_group(g)
        excl = _rollup_group(g[g["author"] != top_author])
        row = {"repo": repo, "quarter": quarter}
        row.update({f"pooled_{k}": v for k, v in pooled.items()})
        row.update({f"excltop_{k}": v for k, v in excl.items()})
        row["top_contributor"] = top_author
        row["top_contributor_share_overall"] = tc["share"]
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("quarter").reset_index(drop=True)
    return df


def build_panel_a_quarterly_all() -> pd.DataFrame:
    return pd.concat([quarterly_rollup(r) for r in REPO_ORDER], ignore_index=True)


# ---------------------------------------------------------------------------
# Repo-fixed-effects pooling: within-repo demean, average across repos,
# add back the grand mean. Keeps a common time trend without letting any
# one repo's absolute level dominate.
# ---------------------------------------------------------------------------

def fixed_effects_pool(df: pd.DataFrame, value_col: str, repo_col: str = "repo",
                        quarter_col: str = "quarter") -> pd.DataFrame:
    d = df[[repo_col, quarter_col, value_col]].dropna(subset=[value_col]).copy()
    repo_means = d.groupby(repo_col)[value_col].transform("mean")
    d["demeaned"] = d[value_col] - repo_means
    grand_mean = d.groupby(repo_col)[value_col].mean().mean()
    pooled = d.groupby(quarter_col)["demeaned"].mean() + grand_mean
    n_repos = d.groupby(quarter_col)[repo_col].nunique()
    out = pd.DataFrame({"quarter": pooled.index, "pooled_fe": pooled.values})
    out = out.merge(n_repos.rename("n_repos").reset_index(), on="quarter")
    return out.sort_values("quarter").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Break scan: for a handful of candidate split dates, compare each repo's
# pre/post mean and report how many repos move, and in which direction.
# ---------------------------------------------------------------------------

CANDIDATE_BREAKS = ["2018Q1", "2020Q1", "2022Q4", "2023Q1"]


def break_scan(df: pd.DataFrame, value_col: str, repo_col: str = "repo",
                quarter_col: str = "quarter") -> pd.DataFrame:
    """For each candidate break quarter, per repo: pre-mean, post-mean,
    pct change, and whether it moved by more than 10% in a consistent
    direction. Returns one row per (candidate, repo).
    """
    rows = []
    for cand in CANDIDATE_BREAKS:
        for repo, g in df.groupby(repo_col):
            g = g.dropna(subset=[value_col]).sort_values(quarter_col)
            pre = g[g[quarter_col] < cand][value_col]
            post = g[g[quarter_col] >= cand][value_col]
            if len(pre) < 4 or len(post) < 4:
                continue
            pre_mean, post_mean = pre.mean(), post.mean()
            pct_change = (post_mean - pre_mean) / pre_mean if pre_mean else np.nan
            rows.append({
                "candidate": cand, "repo": repo,
                "pre_mean": pre_mean, "post_mean": post_mean,
                "pct_change": pct_change,
            })
    return pd.DataFrame(rows)


def break_summary(scan: pd.DataFrame, threshold: float = 0.10) -> pd.DataFrame:
    """Per candidate: how many repos moved >threshold in the same direction."""
    rows = []
    for cand, g in scan.groupby("candidate"):
        up = (g["pct_change"] > threshold).sum()
        down = (g["pct_change"] < -threshold).sum()
        n = len(g)
        rows.append({
            "candidate": cand, "n_repos": n,
            "n_up": int(up), "n_down": int(down),
            "median_pct_change": g["pct_change"].median(),
        })
    return pd.DataFrame(rows).sort_values("candidate")


# ---------------------------------------------------------------------------
# Normalize each repo to its own pre-break mean, for the event-study plot
# ---------------------------------------------------------------------------

def normalize_to_pre_break(df: pd.DataFrame, value_col: str, break_quarter: str,
                            repo_col: str = "repo", quarter_col: str = "quarter") -> pd.DataFrame:
    rows = []
    for repo, g in df.groupby(repo_col):
        g = g.dropna(subset=[value_col]).sort_values(quarter_col)
        pre = g[g[quarter_col] < break_quarter][value_col]
        if len(pre) < 4:
            continue
        pre_mean = pre.mean()
        if not pre_mean:
            continue
        out = g.copy()
        out["normalized"] = out[value_col] / pre_mean
        rows.append(out[[repo_col, quarter_col, "normalized"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=[repo_col, quarter_col, "normalized"])


# ---------------------------------------------------------------------------
# Entry point: build everything and cache to output/analysis/*.csv
# ---------------------------------------------------------------------------

def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Panel B for all repos ...")
    panel_b_all = load_all_panel_b()
    panel_b_all.to_csv(ANALYSIS_DIR / "panel_b_all.csv", index=False)

    print("Building top-contributors table ...")
    top_df = build_top_contributors_table()
    top_df.to_csv(ANALYSIS_DIR / "top_contributors.csv", index=False)
    print(top_df.to_string(index=False))

    print("Building Panel A quarterly rollup (pooled + excl-top) ...")
    a_quarterly = build_panel_a_quarterly_all()
    a_quarterly.to_csv(ANALYSIS_DIR / "panel_a_quarterly.csv", index=False)
    print(f"  {len(a_quarterly)} repo-quarter rows.")

    print("Done. Wrote to", ANALYSIS_DIR)


if __name__ == "__main__":
    main()
