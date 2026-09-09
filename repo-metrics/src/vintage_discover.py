"""Find candidate packages "born" in each quarter since 2014.

Uses GitHub's search API (`language:Python fork:false created:<range>`,
sorted by stars) -- one request per quarter, well within the unauthenticated
search rate limit (10/min). Deliberately does NOT call the contents API to
check for setup.py/pyproject.toml here: that endpoint shares the much
stingier unauthenticated *core* rate limit (60/hour), and 51 quarters x 20+
candidates would blow through it in minutes. The "is this actually a
package" check happens after a cheap --no-checkout clone instead (see
vintage_extract.py) using a local `git ls-tree`, which costs nothing but
time.

"Created in quarter X" = GitHub repo creation date. Ranking by accumulated
stars is a weaker signal for recent quarters (less time to accumulate) --
documented in VINTAGE_REPORT.md, not hidden.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from common import quarter_end_date  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VINTAGE_DIR = ROOT / "output" / "vintage"
CANDIDATES_PATH = VINTAGE_DIR / "candidates.json"

PER_PAGE = 100  # GitHub search API max per page
REQUEST_DELAY_S = 7.0
SEARCH_URL = "https://api.github.com/search/repositories"


def _quarters(since: str, until: date):
    y = int(since[:4])
    q = (int(since[5:7]) - 1) // 3 + 1
    while True:
        qstart = date(y, (q - 1) * 3 + 1, 1)
        if qstart > until:
            break
        qend = min(quarter_end_date(y, q), until)
        yield f"{y}Q{q}", qstart, qend
        q += 1
        if q > 4:
            q = 1
            y += 1


def _search_quarter(qstart: date, qend: date) -> List[dict]:
    query = f"language:Python fork:false created:{qstart.isoformat()}..{qend.isoformat()}"
    for attempt in range(1, 5):
        r = requests.get(
            SEARCH_URL,
            params={"q": query, "sort": "stars", "order": "desc", "per_page": PER_PAGE},
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return [
                {
                    "full_name": it["full_name"],
                    "clone_url": it["clone_url"],
                    "created_at": it["created_at"],
                    "stars": it["stargazers_count"],
                    "archived": it["archived"],
                }
                for it in data.get("items", [])
            ]
        if r.status_code in (403, 429):
            wait = 30 * attempt
            print(f"  rate-limited (status {r.status_code}), waiting {wait}s ...")
            time.sleep(wait)
            continue
        raise RuntimeError(f"GitHub search failed: {r.status_code} {r.text[:300]}")
    raise RuntimeError("GitHub search: exhausted retries")


def main() -> None:
    VINTAGE_DIR.mkdir(parents=True, exist_ok=True)

    candidates = {}
    if CANDIDATES_PATH.exists():
        candidates = json.loads(CANDIDATES_PATH.read_text())
        print(f"Loaded {len(candidates)} already-discovered quarters.")

    until = date.fromisoformat(config.UNTIL) if config.UNTIL else datetime.now(timezone.utc).date()

    for quarter, qstart, qend in _quarters(config.SINCE, until):
        if quarter in candidates:
            continue
        print(f"{quarter} ({qstart}..{qend}): querying GitHub search ...")
        items = _search_quarter(qstart, qend)
        candidates[quarter] = items
        print(f"  -> {len(items)} candidates, top stars: "
              f"{[c['stars'] for c in items[:5]]}")
        CANDIDATES_PATH.write_text(json.dumps(candidates, indent=2))
        time.sleep(REQUEST_DELAY_S)

    print(f"Done. {len(candidates)} quarters written to {CANDIDATES_PATH}")


if __name__ == "__main__":
    main()
