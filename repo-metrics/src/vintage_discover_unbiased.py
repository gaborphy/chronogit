"""Discovery for the unbiased vintage cohort: random-sample from cl_ecosystem_networks'
full PyPI packages.parquet instead of GitHub-star-ranked search.

Removes the GitHub-search discovery bottleneck entirely (rate limits,
"is this a package" false positives, star-popularity selection bias) by
querying an already-known-good population directly: real, published PyPI
packages with a GitHub repository_url on file, sampled uniformly at
random per quarter by first PyPI release date rather than ranked by
stars. One DuckDB query against the external parquet file, no network
calls, runs in seconds.

Deliberate methodology difference from the star-sampled cohort, stated
plainly (see vintage_extract_unbiased.py for the rest): vintage here is
anchored to first PyPI RELEASE date, not first git commit -- the natural
"birth" signal for a *package* when you have reliable publish-date
metadata, vs. first commit being what GitHub-only discovery had to use
as a proxy.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "vintage_unbiased"
CANDIDATES_PATH = OUT_DIR / "candidates.json"

PACKAGES_PARQUET = "/Users/molnar/Documents_alt/Research/ecosystem_networks/data/parquet/packages.parquet"
SINCE = "2014-01-01"
UNTIL = "2026-09-09"  # matches this session's extraction date for the star-sampled cohort
OVERSAMPLE_PER_QUARTER = 300  # generous buffer; query cost is trivial

# Exactly https://github.com/<owner>/<repo>, no extra path segments (rules
# out /tree/, /blob/, profile-only URLs, trailing cruft).
_GITHUB_REPO_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


def _quarters(since: str, until: str):
    y, m = int(since[:4]), int(since[5:7])
    q = (m - 1) // 3 + 1
    until_d = date.fromisoformat(until)
    while True:
        qstart_month = (q - 1) * 3 + 1
        qstart = date(y, qstart_month, 1)
        if qstart > until_d:
            break
        qend_month = q * 3
        if qend_month == 12:
            qend = date(y, 12, 31)
        else:
            import calendar
            last_day = calendar.monthrange(y, qend_month)[1]
            qend = date(y, qend_month, last_day)
        qend = min(qend, until_d)
        yield f"{y}Q{q}", qstart, qend
        q += 1
        if q > 4:
            q = 1
            y += 1


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    quarters = list(_quarters(SINCE, UNTIL))
    print(f"Querying {PACKAGES_PARQUET} for {len(quarters)} quarters ...")

    # One combined query: bucket every eligible package into its quarter,
    # rank randomly within each quarter (seeded via setseed for
    # reproducibility), keep the top OVERSAMPLE_PER_QUARTER per quarter.
    quarter_case = " ".join(
        f"WHEN first_release_published_at >= '{qstart.isoformat()}' "
        f"AND first_release_published_at <= '{qend.isoformat()} 23:59:59' THEN '{label}'"
        for label, qstart, qend in quarters
    )

    # Materialize the eligible-rows CTE into a real temp table before the
    # windowed query. Chaining CASE(51 branches) -> WHERE -> window
    # function -> outer SELECT as nested CTEs hit a duckdb 1.5.1
    # bug on this ~500K-row intermediate: with everything inlined into one
    # query plan, the "quarter" column silently returned
    # first_release_published_at values instead (row values from the
    # wrong column), and adding `ORDER BY quarter, rn` outright segfaulted.
    # Materializing breaks the plan into two steps and avoids both.
    con.execute("SELECT setseed(0.42)")
    con.execute(f"""
        CREATE TEMP TABLE eligible AS
        SELECT
            name,
            repository_url,
            first_release_published_at,
            downloads,
            versions_count,
            CASE {quarter_case} ELSE NULL END AS quarter
        FROM read_parquet('{PACKAGES_PARQUET}')
        WHERE ecosystem = 'pypi'
          AND status IS NULL
          AND repository_url LIKE 'https://github.com/%'
          AND first_release_published_at IS NOT NULL
          AND CASE {quarter_case} ELSE NULL END IS NOT NULL
    """)
    query = f"""
    WITH bucketed AS (
        SELECT
            name, repository_url, first_release_published_at, downloads, versions_count, quarter,
            row_number() OVER (PARTITION BY quarter ORDER BY random()) AS rn
        FROM eligible
    )
    SELECT quarter, name, repository_url, first_release_published_at, downloads, versions_count
    FROM bucketed
    WHERE rn <= {OVERSAMPLE_PER_QUARTER}
    """
    df = con.execute(query).df()
    print(f"Got {len(df)} raw candidate rows across all quarters.")

    candidates: dict[str, list[dict]] = {label: [] for label, _, _ in quarters}
    skipped_bad_url = 0
    for row in df.itertuples(index=False):
        m = _GITHUB_REPO_RE.match(row.repository_url.strip())
        if not m:
            skipped_bad_url += 1
            continue
        owner, repo = m.group(1), m.group(2)
        full_name = f"{owner}/{repo}"
        candidates[row.quarter].append({
            "full_name": full_name,
            "clone_url": f"https://github.com/{full_name}.git",
            "pypi_name": row.name,
            "first_pypi_release": str(row.first_release_published_at),
            "downloads": int(row.downloads) if pd.notna(row.downloads) else None,
            "versions_count": int(row.versions_count) if pd.notna(row.versions_count) else None,
        })

    for label, _, _ in quarters:
        print(f"  {label}: {len(candidates[label])} candidates")
    print(f"Skipped {skipped_bad_url} rows with an unparseable repository_url "
          f"(profile links, extra path segments, etc.)")

    CANDIDATES_PATH.write_text(json.dumps(candidates, indent=2))
    print(f"Wrote {CANDIDATES_PATH}")


if __name__ == "__main__":
    main()
