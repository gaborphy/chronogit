"""Orchestrator: for each repo, clone --no-checkout -> run both panels ->
write CSVs -> rm -rf the clone. One repo at a time (disk, not CPU, is the
constraint here). Resumable: a repo whose two CSVs + meta already exist is
skipped.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from panel_a import stream_panel_a  # noqa: E402
from panel_b import run_panel_b  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
CLONES_DIR = ROOT / "clones"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def du_bytes(path: Path) -> int:
    out = subprocess.check_output(["du", "-sk", str(path)], text=True)
    kb = int(out.split()[0])
    return kb * 1024


def human_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def already_done(name: str) -> bool:
    a = OUTPUT_DIR / f"{name}_panel_a.csv"
    b = OUTPUT_DIR / f"{name}_panel_b.csv"
    m = OUTPUT_DIR / f"{name}_meta.json"
    return a.exists() and b.exists() and m.exists()


def run_repo(name: str, url: str, since: str, until: date) -> None:
    if already_done(name):
        log(f"{name}: outputs already exist, skipping (resumable no-op).")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CLONES_DIR.mkdir(parents=True, exist_ok=True)
    clone_dir = CLONES_DIR / name
    if clone_dir.exists():
        log(f"{name}: stale clone dir found, removing before re-clone.")
        shutil.rmtree(clone_dir)

    log(f"{name}: cloning (--no-checkout) from {url} ...")
    t0 = time.time()
    subprocess.run(
        ["git", "clone", "--no-checkout", "--quiet", url, str(clone_dir)],
        check=True,
    )
    clone_elapsed = time.time() - t0
    clone_size = du_bytes(clone_dir)
    log(f"{name}: clone done in {clone_elapsed:.0f}s, size {human_bytes(clone_size)}.")

    head_sha = subprocess.check_output(
        ["git", "-C", str(clone_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    head_date = subprocess.check_output(
        ["git", "-C", str(clone_dir), "log", "-1", "--format=%cI", head_sha], text=True
    ).strip()

    a_path = OUTPUT_DIR / f"{name}_panel_a.csv"
    a_tmp = a_path.with_suffix(".csv.tmp")
    log(f"{name}: running Panel A (commit flow) ...")
    t0 = time.time()
    with open(a_tmp, "w", newline="") as fh:
        n_a = stream_panel_a(str(clone_dir), name, since, fh)
    a_tmp.rename(a_path)
    log(f"{name}: Panel A wrote {n_a} commit rows in {time.time() - t0:.0f}s.")

    b_path = OUTPUT_DIR / f"{name}_panel_b.csv"
    b_tmp = b_path.with_suffix(".csv.tmp")
    log(f"{name}: running Panel B (codebase state, quarterly) ...")
    t0 = time.time()
    since_date = date.fromisoformat(since)
    with open(b_tmp, "w", newline="") as fh:
        n_b = run_panel_b(str(clone_dir), name, since_date, until, fh, log=log)
    b_tmp.rename(b_path)
    log(f"{name}: Panel B wrote {n_b} quarter rows in {time.time() - t0:.0f}s.")

    meta = {
        "repo": name,
        "url": url,
        "head_sha": head_sha,
        "head_committer_date": head_date,
        "since": since,
        "until": until.isoformat(),
        "extraction_date_utc": datetime.now(timezone.utc).isoformat(),
        "clone_size_bytes": clone_size,
        "clone_elapsed_s": round(clone_elapsed, 1),
        "panel_a_rows": n_a,
        "panel_b_rows": n_b,
    }
    (OUTPUT_DIR / f"{name}_meta.json").write_text(json.dumps(meta, indent=2))

    log(f"{name}: removing clone ({human_bytes(clone_size)} freed).")
    shutil.rmtree(clone_dir)
    log(f"{name}: done.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="Comma-separated repo names to run (default: all in config.REPOS).")
    args = ap.parse_args()

    until = date.fromisoformat(config.UNTIL) if config.UNTIL else datetime.now(timezone.utc).date()
    wanted = set(args.only.split(",")) if args.only else None

    for name, url in config.REPOS:
        if wanted is not None and name not in wanted:
            continue
        run_repo(name, url, config.SINCE, until)


if __name__ == "__main__":
    main()
