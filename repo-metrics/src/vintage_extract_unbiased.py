"""Extraction for the unbiased vintage cohort, paired with
vintage_discover_unbiased.py. Reuses vintage_extract.py's validated
clone -> measure -> rm -rf machinery unmodified (check_package_signals,
commit_at_or_before, process_snapshot, stream_panel_a, _rollup_group);
only the discovery source and the resulting birth/snapshot-anchor logic
change. vintage_extract.py itself is untouched -- this is a parallel
script writing to output/vintage_unbiased/, not a variant of the
existing already-published pipeline.

**Deliberate methodology difference from the star-sampled cohort**,
stated plainly rather than hidden:

- Star-sampled cohort (vintage_extract.py): vintage quarter = quarter of
  the repo's first git commit, discovered only after cloning, because
  GitHub-search discovery has no reliable "package birth" date to sample
  on up front -- first commit was the best available proxy for a
  package's public appearance.
- This cohort: vintage quarter = quarter of first PyPI release, known
  directly from packages.parquet at discovery time. This is arguably a
  *more* natural "birth" event for a distributed *package* specifically
  (a git repo can exist privately for a long time before anything is
  published; a PyPI release is unambiguously the package becoming real
  in the ecosystem this whole project studies). Snapshot timing follows
  the same anchor for consistency: first_pypi_release + 180 days (or
  now, if younger), not first_commit + 180 days.

This also changes the pre-existing-code sanity check. The star-sampled
cohort's check was symmetric (reject if |github_created_at -
first_commit| > 180 days) because for that source both dates *should*
be close together (a repo is normally created right when work starts).
That symmetry doesn't hold here: a package's first git commit can
legitimately predate its first PyPI release by months or years of
private development -- completely normal, not a red flag. What *would*
be a red flag is the opposite: a first commit dated *after* the first
PyPI release (impossible under honest data -- code can't be released
before it's written -- and a sign the repository_url doesn't actually
match this PyPI package), or a first commit implausibly far before the
release. So the check here is asymmetric: reject if first_commit is
more than 7 days after first_pypi_release (small buffer for
release-tooling/clock lag), or more than
MAX_COMMIT_BEFORE_RELEASE_DAYS before it.

That second bound needed to be tight, and was found empirically, not
guessed: a first validation pass at 10 years turned up
`open-telemetry/opentelemetry-python` (gap 1,473 days) and
`autoresearch/autora` (gap 2,726 days) sailing through -- both are a
distinct pattern this source is newly exposed to that the star-sampled
cohort mostly didn't hit: **one shared, already-mature monorepo
publishing many separately-versioned PyPI sub-packages over its
lifetime.** Sampling "packages first released in quarter X" surfaces
each new sub-package release as if it were a new package being born,
when the actual codebase (and its git history) is years old. Measuring
"180 days after this release" on one of those would silently score a
mature, many-contributor monorepo as a newborn small package -- the
exact confound this whole study exists to avoid. The other 8 packages
in that same validation batch all had gaps of 0-407 days -- solo/small
-team private development before a first release, the normal case this
bound is meant to allow. 730 days (2 years) is set as a generous but
much tighter line between "normal pre-release development" and "this is
an old monorepo's incidental new release," informed directly by that
split.
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
from vintage_extract import (  # noqa: E402
    CLONE_TIMEOUT_S, MANIFEST_NAMES, MIN_PY_FILES, STATE_FIELDS, FLOW_FIELDS,
    _EMPTY_PANEL_A_COLUMNS, check_package_signals, log,
)
from panel_a import stream_panel_a  # noqa: E402
from panel_b import commit_at_or_before, process_snapshot  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VINTAGE_DIR = ROOT / "output" / "vintage_unbiased"
CANDIDATES_PATH = VINTAGE_DIR / "candidates.json"
PROGRESS_PATH = VINTAGE_DIR / "progress.json"
PACKAGES_CSV = VINTAGE_DIR / "packages.csv"
CLONES_DIR = ROOT / "clones-vintage-unbiased"

TARGET_PER_QUARTER = 30
MAX_COMMIT_AFTER_RELEASE_DAYS = 7
MAX_COMMIT_BEFORE_RELEASE_DAYS = 730  # 2 years; see module docstring

ROW_FIELDNAMES = (
    ["vintage_quarter", "repo_full_name", "clone_url", "pypi_name",
     "downloads_at_discovery", "versions_count_at_discovery", "first_pypi_release",
     "first_commit_date", "commit_vs_release_gap_days",
     "snapshot_date", "snapshot_sha", "age_days_at_snapshot", "is_young_partial"]
    + [f"state_{f}" for f in STATE_FIELDS]
    + [f"flow_{f}" for f in FLOW_FIELDS]
)


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

        try:
            head_sha = subprocess.check_output(
                ["git", "-C", str(clone_dir), "rev-parse", "HEAD"], text=True,
                stderr=subprocess.PIPE,
            ).strip()
        except subprocess.CalledProcessError:
            # Empty repo / unborn HEAD (no commits at all). GitHub-search
            # discovery rarely surfaces these; direct PyPI-population
            # sampling isn't filtered by any GitHub-side "has commits"
            # signal, so this shows up here where it didn't in
            # vintage_extract.py's candidate pool.
            return False, "empty_repo_or_no_head", None

        has_manifest, n_py = check_package_signals(str(clone_dir), head_sha)
        if not has_manifest:
            return False, "no_manifest", None
        if n_py < MIN_PY_FILES:
            return False, f"too_few_py_files:{n_py}", None

        first_iso_lines = subprocess.check_output(
            ["git", "-C", str(clone_dir), "log", "--reverse", "--format=%cI", head_sha],
            text=True,
        ).splitlines()
        if not first_iso_lines:
            return False, "no_commits", None
        first_dt = datetime.fromisoformat(first_iso_lines[0])

        release_dt = datetime.fromisoformat(cand["first_pypi_release"]).replace(tzinfo=timezone.utc)
        first_dt_utc = first_dt.astimezone(timezone.utc)
        gap_days = (release_dt - first_dt_utc).days  # positive: commit before release (normal)
        if gap_days < -MAX_COMMIT_AFTER_RELEASE_DAYS:
            return False, f"commit_after_release:{gap_days}d", None
        if gap_days > MAX_COMMIT_BEFORE_RELEASE_DAYS:
            return False, f"commit_too_far_before_release:{gap_days}d", None

        now = datetime.now(timezone.utc)
        snapshot_target = release_dt + timedelta(days=180)
        snapshot_dt = min(snapshot_target, now)
        is_young = snapshot_target > now
        age_days = (snapshot_dt - release_dt).days

        snapshot_sha = commit_at_or_before(str(clone_dir), snapshot_dt.date().isoformat())
        if snapshot_sha is None:
            snapshot_sha = head_sha

        state = process_snapshot(str(clone_dir), snapshot_sha)
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
            "pypi_name": cand["pypi_name"],
            "downloads_at_discovery": cand["downloads"],
            "versions_count_at_discovery": cand["versions_count"],
            "first_pypi_release": cand["first_pypi_release"],
            "first_commit_date": first_dt.isoformat(),
            "commit_vs_release_gap_days": gap_days,
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
            log(f"  [{quarter}] OK  {full_name} "
                f"(age_days={row['age_days_at_snapshot']}, n_files={row['state_n_files']}) "
                f"-> {len(have)}/{TARGET_PER_QUARTER}")
        else:
            progress["failed"][full_name] = reason
            log(f"  [{quarter}] skip {full_name}: {reason}")
        save_progress(progress)

    if len(have) < TARGET_PER_QUARTER:
        log(f"{quarter}: only found {len(have)}/{TARGET_PER_QUARTER} -- candidates exhausted.")


def main() -> None:
    if not CANDIDATES_PATH.exists():
        raise SystemExit("Run vintage_discover_unbiased.py first.")
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
