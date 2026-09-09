"""For each vintage quarter, walk its star-ranked GitHub candidates
(from vintage_discover.py) until 10 turn out to be real packages, take one
early snapshot of each (~180 days after its own first commit, or "now" if
younger), and record state (Panel-B-style) + flow (Panel-A-style, rolled
up over its whole pre-snapshot history) in one row per package.

Same clone --no-checkout -> measure -> rm -rf discipline as driver.py, and
resumable per-repo via output/vintage/progress.json (a repo that already
succeeded or is known to fail is never retried).
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from analysis import _rollup_group  # noqa: E402
from common import is_excluded_path  # noqa: E402
from panel_a import stream_panel_a  # noqa: E402
from panel_b import commit_at_or_before, process_snapshot  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VINTAGE_DIR = ROOT / "output" / "vintage"
CANDIDATES_PATH = VINTAGE_DIR / "candidates.json"
PROGRESS_PATH = VINTAGE_DIR / "progress.json"
PACKAGES_CSV = VINTAGE_DIR / "packages.csv"
CLONES_DIR = ROOT / "clones-vintage"

TARGET_PER_QUARTER = 30
MIN_PY_FILES = 2
MANIFEST_NAMES = {"setup.py", "pyproject.toml", "setup.cfg"}
CLONE_TIMEOUT_S = 180

STATE_FIELDS = [
    "n_files", "parsed_files", "parse_rate", "total_lines", "n_functions",
    "mean_comment_len", "median_comment_len", "p90_comment_len",
    "mean_complexity", "median_complexity", "p90_complexity",
    "mean_func_len", "median_func_len", "p90_func_len",
    "mean_body_len", "median_body_len", "p90_body_len",
    "mean_docstring_len", "median_docstring_len", "p90_docstring_len",
    "frac_functions_with_docstring",
]
FLOW_FIELDS = [
    "n_commits", "n_contributors",
    "mean_added_comment_len", "median_hunk_added", "mean_hunk_added",
    "median_added_code_lines_per_commit", "mean_added_code_lines_per_commit",
    "total_added_code_lines", "total_added_comment_lines", "total_added_blank_lines",
    "total_raw_added_lines", "total_raw_deleted_lines", "total_raw_n_files",
]
ROW_FIELDNAMES = (
    ["vintage_quarter", "repo_full_name", "clone_url", "stars_at_discovery",
     "archived_at_discovery", "created_at_github", "first_commit_date",
     "snapshot_date", "snapshot_sha", "age_days_at_snapshot", "is_young_partial"]
    + [f"state_{f}" for f in STATE_FIELDS]
    + [f"flow_{f}" for f in FLOW_FIELDS]
)

_EMPTY_PANEL_A_COLUMNS = [
    "repo", "sha", "unix_ts", "author", "n_files", "n_hunks", "added_lines",
    "deleted_lines", "hunk_added_sum", "added_code_lines", "added_code_chars",
    "added_comment_lines", "added_comment_chars", "added_blank_lines",
]


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text())
    return {"success_by_quarter": {}, "failed": {}}


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2))


def ensure_packages_csv_header() -> None:
    if not PACKAGES_CSV.exists():
        with open(PACKAGES_CSV, "w", newline="") as fh:
            csv.DictWriter(fh, fieldnames=ROW_FIELDNAMES).writeheader()


def append_row(row: dict) -> None:
    with open(PACKAGES_CSV, "a", newline="") as fh:
        csv.DictWriter(fh, fieldnames=ROW_FIELDNAMES).writerow(row)


def check_package_signals(repo_dir: str, sha: str) -> tuple[bool, int]:
    root = subprocess.check_output(
        ["git", "-C", repo_dir, "ls-tree", "--name-only", sha], text=True
    ).splitlines()
    has_manifest = any(e in MANIFEST_NAMES for e in root)
    all_paths = subprocess.check_output(
        ["git", "-C", repo_dir, "ls-tree", "-r", "--name-only", sha], text=True
    ).splitlines()
    n_py = sum(1 for p in all_paths if p and not is_excluded_path(p))
    return has_manifest, n_py


def try_extract(cand: dict, quarter: str) -> tuple[bool, str, Optional[dict]]:
    full_name = cand["full_name"]
    safe_name = full_name.replace("/", "__")
    clone_dir = CLONES_DIR / safe_name
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    try:
        try:
            subprocess.run(
                ["git", "clone", "--no-checkout", "--quiet", cand["clone_url"], str(clone_dir)],
                check=True, timeout=CLONE_TIMEOUT_S,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            return False, f"clone_failed:{e.stderr.decode(errors='replace')[:120]}", None
        except subprocess.TimeoutExpired:
            return False, "clone_timeout", None

        head_sha = subprocess.check_output(
            ["git", "-C", str(clone_dir), "rev-parse", "HEAD"], text=True
        ).strip()

        has_manifest, n_py = check_package_signals(str(clone_dir), head_sha)
        if not has_manifest:
            return False, "no_manifest", None
        if n_py < MIN_PY_FILES:
            return False, f"too_few_py_files:{n_py}", None

        # NOTE: `git log --reverse ... -1` does NOT give the oldest commit --
        # `-1`/`--max-count` limits the (newest-first) traversal *before*
        # `--reverse` reorders whatever survived that limit, so it silently
        # returns HEAD's date instead. Confirmed on a live repo during
        # validation (wagtail: buggy command gave today's date instead of
        # its real 2014-01-22 first commit). Fetch the full reversed date
        # list and take the first line instead.
        first_iso_lines = subprocess.check_output(
            ["git", "-C", str(clone_dir), "log", "--reverse", "--format=%cI", head_sha],
            text=True,
        ).splitlines()
        if not first_iso_lines:
            return False, "no_commits", None
        first_iso = first_iso_lines[0]
        first_dt = datetime.fromisoformat(first_iso)

        # GitHub's repo `created_at` can lag far behind the git history's
        # real first commit -- e.g. an existing project rehosted/imported
        # into a new GitHub repo with its original commit dates preserved
        # (confirmed during validation: google-api-python-client's repo
        # reads as "created 2014Q1" on GitHub but its first commit is from
        # 2010). That's pre-existing code, not a newly-created package --
        # reject it rather than silently measuring a 4-year-old codebase
        # as a "6-months-old" one.
        # Same check both directions: first commit far *before* created_at
        # means pre-existing code was imported (see google-api-python-client
        # above); first commit far *after* created_at means the repo slot
        # sat empty/was transferred before real development started (seen
        # on SeleniumBase: "created" 2014-03-04 on GitHub, real first
        # commit 2015-12-04) -- either way the GitHub-search vintage bucket
        # doesn't reflect when the code was actually born.
        created_at_dt = datetime.fromisoformat(cand["created_at"].replace("Z", "+00:00"))
        gap_days = (created_at_dt - first_dt).days
        if abs(gap_days) > 180:
            return False, f"created_vs_first_commit_gap:{gap_days}d", None
        now = datetime.now(timezone.utc)
        snapshot_target = first_dt + timedelta(days=180)
        snapshot_dt = min(snapshot_target, now)
        is_young = snapshot_target > now
        age_days = (snapshot_dt - first_dt).days

        snapshot_sha = commit_at_or_before(str(clone_dir), snapshot_dt.date().isoformat())
        if snapshot_sha is None:
            snapshot_sha = head_sha

        state = process_snapshot(str(clone_dir), snapshot_sha)
        # MIN_PY_FILES was already checked at HEAD (today) above, but the
        # actual measurement is at the early snapshot, which can be far
        # sparser -- caught live: vinta/awesome-python (a curated markdown
        # list, not a package) passed the HEAD-level check but had exactly
        # 1 in-scope .py file 180 days after its first commit. Check again
        # at the snapshot itself.
        if state["n_files"] < MIN_PY_FILES:
            return False, f"snapshot_too_few_py_files:{state['n_files']}", None

        buf = io.StringIO()
        stream_panel_a(
            str(clone_dir), full_name,
            since=first_dt.date().isoformat(),
            out_fh=buf,
            until=(snapshot_dt.date() + timedelta(days=1)).isoformat(),
        )
        buf.seek(0)
        pa_df = pd.read_csv(buf)
        if pa_df.empty:
            pa_df = pd.DataFrame(columns=_EMPTY_PANEL_A_COLUMNS)
        flow = _rollup_group(pa_df)

        row = {
            "vintage_quarter": quarter,
            "repo_full_name": full_name,
            "clone_url": cand["clone_url"],
            "stars_at_discovery": cand["stars"],
            "archived_at_discovery": int(bool(cand["archived"])),
            "created_at_github": cand["created_at"],
            "first_commit_date": first_dt.isoformat(),
            "snapshot_date": snapshot_dt.date().isoformat(),
            "snapshot_sha": snapshot_sha,
            "age_days_at_snapshot": age_days,
            "is_young_partial": int(is_young),
        }
        row.update({f"state_{k}": state.get(k) for k in STATE_FIELDS})
        row.update({f"flow_{k}": flow.get(k) for k in FLOW_FIELDS})
        return True, "ok", row
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)


def process_quarter(quarter: str, candidates: list[dict], progress: dict) -> None:
    have = list(progress["success_by_quarter"].get(quarter, []))
    if len(have) >= TARGET_PER_QUARTER:
        log(f"{quarter}: already has {len(have)}/{TARGET_PER_QUARTER}, skipping (resumable no-op).")
        return

    log(f"{quarter}: have {len(have)}/{TARGET_PER_QUARTER}, scanning {len(candidates)} candidates ...")
    for cand in candidates:
        if len(have) >= TARGET_PER_QUARTER:
            break
        full_name = cand["full_name"]
        if full_name in have or full_name in progress["failed"]:
            continue

        ok, reason, row = try_extract(cand, quarter)
        if ok:
            append_row(row)
            have.append(full_name)
            progress["success_by_quarter"][quarter] = have
            log(f"  [{quarter}] OK  {full_name} (stars={cand['stars']}, "
                f"age_days={row['age_days_at_snapshot']}, n_files={row['state_n_files']}) "
                f"-> {len(have)}/{TARGET_PER_QUARTER}")
        else:
            progress["failed"][full_name] = reason
            log(f"  [{quarter}] skip {full_name}: {reason}")
        save_progress(progress)

    if len(have) < TARGET_PER_QUARTER:
        log(f"{quarter}: only found {len(have)}/{TARGET_PER_QUARTER} -- candidates exhausted.")


def main() -> None:
    if not CANDIDATES_PATH.exists():
        raise SystemExit("Run vintage_discover.py first.")
    candidates_by_quarter = json.loads(CANDIDATES_PATH.read_text())

    CLONES_DIR.mkdir(parents=True, exist_ok=True)
    ensure_packages_csv_header()
    progress = load_progress()

    for quarter in sorted(candidates_by_quarter.keys()):
        process_quarter(quarter, candidates_by_quarter[quarter], progress)

    total = sum(len(v) for v in progress["success_by_quarter"].values())
    log(f"Done. {total} packages across {len(progress['success_by_quarter'])} quarters. "
        f"{len(progress['failed'])} candidates rejected/failed total.")


if __name__ == "__main__":
    main()
