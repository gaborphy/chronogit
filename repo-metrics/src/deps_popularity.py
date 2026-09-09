"""Two things, both via ecosyste.ms (mirrors GitHub stars/forks/committer
counts in one call per package -- no GitHub API involved, so none of the
unauthenticated 60/hour core-API pain from the vintage study applies here;
ecosyste.ms's own limit is 5000/window):

  1. Popularity metrics for every unique dependency name found in edges.csv
  2. A baseline sample of ~400 PyPI packages picked WITHOUT regard to
     popularity (default/unsorted listing, many widely-spaced random
     pages), to test whether the dependency set is more popular than a
     typical package -- not just to describe popular dependencies, which
     would be true almost by construction.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
DEPS_DIR = ROOT / "output" / "deps"

BASE = "https://packages.ecosyste.ms/api/v1/registries/pypi.org/packages"
TOTAL_PACKAGES = 933_217
BASELINE_N = 400
REQUEST_DELAY_S = 0.15


def _get(url: str, params: Optional[dict] = None, timeout: int = 20):
    for attempt in range(1, 4):
        try:
            r = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as e:
            print(f"  network error (attempt {attempt}): {e}")
            time.sleep(3 * attempt)
            continue
        if r.status_code == 200:
            return r
        if r.status_code == 404:
            return None
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 10))
            print(f"  rate-limited, waiting {wait}s ...")
            time.sleep(wait)
            continue
        print(f"  unexpected status {r.status_code} for {url}")
        time.sleep(2)
    return None


def fetch_package_popularity(name: str) -> Optional[dict]:
    r = _get(f"{BASE}/{name}")
    if r is None:
        return None
    d = r.json()
    rm = d.get("repo_metadata") or {}
    cs = rm.get("commit_stats") or {}
    return {
        "name": name,
        "found": True,
        "repository_url": d.get("repository_url"),
        "downloads": d.get("downloads"),
        "stargazers_count": rm.get("stargazers_count"),
        "forks_count": rm.get("forks_count"),
        "subscribers_count": rm.get("subscribers_count"),
        "open_issues_count": rm.get("open_issues_count"),
        "total_committers": cs.get("total_committers"),
        "total_commits": cs.get("total_commits"),
        "archived": rm.get("archived"),
    }


def fetch_dependency_popularity(edges_path: Path, out_path: Path) -> None:
    edges = pd.read_csv(edges_path)
    unique_names = sorted(edges["dependency_name"].unique())
    print(f"{len(unique_names)} unique dependency names to resolve ...")

    rows = []
    n_found = 0
    for i, name in enumerate(unique_names):
        info = fetch_package_popularity(name)
        if info is None:
            rows.append({"name": name, "found": False})
        else:
            rows.append(info)
            n_found += 1
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(unique_names)} resolved, {n_found} found on PyPI ...")
        time.sleep(REQUEST_DELAY_S)

    df = pd.DataFrame(rows)
    df.to_csv(out_path, index=False)
    print(f"Done: {n_found}/{len(unique_names)} dependency names resolved. Wrote {out_path}")


def fetch_baseline_sample(out_path: Path, n: int = BASELINE_N, per_page: int = 5) -> None:
    print(f"Sampling ~{n} baseline PyPI packages (popularity-blind) ...")
    n_pages_available = TOTAL_PACKAGES // per_page
    seen_pages = set()
    rows = []

    while len(rows) < n:
        page = random.randint(1, n_pages_available)
        if page in seen_pages:
            continue
        seen_pages.add(page)

        r = _get(BASE, params={"page": page, "per_page": per_page})
        if r is None:
            continue
        items = r.json()
        if not isinstance(items, list):
            continue

        for it in items:
            rm = it.get("repo_metadata") or {}
            cs = rm.get("commit_stats") or {}
            rows.append({
                "name": it.get("name"),
                "found": True,
                "repository_url": it.get("repository_url"),
                "downloads": it.get("downloads"),
                "stargazers_count": rm.get("stargazers_count"),
                "forks_count": rm.get("forks_count"),
                "subscribers_count": rm.get("subscribers_count"),
                "open_issues_count": rm.get("open_issues_count"),
                "total_committers": cs.get("total_committers"),
                "total_commits": cs.get("total_commits"),
                "archived": rm.get("archived"),
            })

        if len(seen_pages) % 20 == 0:
            print(f"  {len(rows)}/{n} baseline packages collected ({len(seen_pages)} pages sampled) ...")
        time.sleep(REQUEST_DELAY_S)

    df = pd.DataFrame(rows[:n])
    df.to_csv(out_path, index=False)
    print(f"Done. Wrote {len(df)} baseline packages to {out_path}")


def main() -> None:
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    edges_path = DEPS_DIR / "edges.csv"
    if not edges_path.exists():
        raise SystemExit("Run deps_extract.py first.")

    fetch_dependency_popularity(edges_path, DEPS_DIR / "dependency_popularity.csv")
    fetch_baseline_sample(DEPS_DIR / "baseline_popularity.csv")


if __name__ == "__main__":
    main()
