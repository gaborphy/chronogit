"""Panel B -- codebase state: one row per repo-quarter, read straight out of
git objects (ls-tree + cat-file --batch), never `git checkout`.
"""
from __future__ import annotations

import ast
import csv
import io
import statistics
import subprocess
import sys
import tokenize
from pathlib import Path
from typing import IO, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    comment_body_and_length,
    function_shape,
    is_excluded_path,
    iter_functions,
    iter_quarters_with_partial,
    percentile,
)

FIELDNAMES = [
    "repo", "quarter", "quarter_end_date", "snapshot_sha", "is_partial_quarter",
    "n_files", "parsed_files", "parse_rate", "total_lines", "n_functions",
    "mean_comment_len", "median_comment_len", "p90_comment_len",
    "mean_complexity", "median_complexity", "p90_complexity",
    "mean_func_len", "median_func_len", "p90_func_len",
    "mean_body_len", "median_body_len", "p90_body_len",
    "mean_docstring_len", "median_docstring_len", "p90_docstring_len",
    "frac_functions_with_docstring",
]


def commit_at_or_before(repo_dir: str, date_str: str) -> Optional[str]:
    try:
        out = subprocess.check_output(
            [
                "git", "-C", repo_dir, "log", "--first-parent",
                f"--before={date_str} 23:59:59", "-1", "--format=%H", "HEAD",
            ],
            text=True, errors="replace", stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None
    return out or None


def list_py_paths(repo_dir: str, sha: str) -> List[str]:
    out = subprocess.check_output(
        ["git", "-C", repo_dir, "ls-tree", "-r", "--name-only", sha],
        text=True, errors="replace",
    )
    return [p for p in out.splitlines() if p and not is_excluded_path(p)]


def _cat_file_batch_once(repo_dir: str, specs: List[str]) -> List[Optional[bytes]]:
    if not specs:
        return []
    proc = subprocess.Popen(
        ["git", "-C", repo_dir, "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    input_data = ("\n".join(specs) + "\n").encode()
    out, err = proc.communicate(input_data)
    if proc.returncode != 0:
        raise RuntimeError(f"git cat-file failed: {err.decode(errors='replace')}")

    results: List[Optional[bytes]] = []
    pos = 0
    n = len(out)
    for _ in specs:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode(errors="replace")
        pos = nl + 1
        parts = header.split()
        if len(parts) >= 2 and parts[-1] == "missing":
            results.append(None)
            continue
        size = int(parts[2])
        content = out[pos:pos + size]
        pos += size
        if pos < n and out[pos:pos + 1] == b"\n":
            pos += 1
        results.append(content)
    return results


def batch_cat_file_objects(repo_dir: str, specs: List[str], chunk_size: int = 300) -> List[Optional[bytes]]:
    results: List[Optional[bytes]] = []
    for i in range(0, len(specs), chunk_size):
        results.extend(_cat_file_batch_once(repo_dir, specs[i:i + chunk_size]))
    return results


def process_snapshot(repo_dir: str, sha: str) -> dict:
    paths = list_py_paths(repo_dir, sha)
    specs = [f"{sha}:{p}" for p in paths]
    contents = batch_cat_file_objects(repo_dir, specs)

    n_files = 0
    parsed_files = 0
    total_lines = 0
    comment_lens: List[int] = []
    func_lens: List[int] = []
    body_lens: List[int] = []
    complexities: List[int] = []
    docstring_lens: List[int] = []
    n_with_docstring = 0

    for content in contents:
        if content is None:
            continue
        n_files += 1
        text = content.decode("utf-8", errors="replace")
        total_lines += text.count("\n") + (1 if text and not text.endswith("\n") else 0)

        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                if tok.type == tokenize.COMMENT:
                    clen = comment_body_and_length(tok.string)
                    if clen is not None:
                        comment_lens.append(clen)
        except Exception:
            pass

        try:
            tree = ast.parse(text)
        except Exception:
            continue
        parsed_files += 1

        for func in iter_functions(tree):
            shape = function_shape(func)
            func_lens.append(shape.total_len)
            body_lens.append(shape.body_len)
            complexities.append(shape.complexity)
            docstring_lens.append(shape.docstring_len)
            if shape.docstring_len > 0:
                n_with_docstring += 1

    def agg(data):
        if not data:
            return None, None, None
        return (
            statistics.mean(data),
            statistics.median(data),
            percentile(data, 90),
        )

    c_mean, c_med, c_p90 = agg(comment_lens)
    x_mean, x_med, x_p90 = agg(complexities)
    fl_mean, fl_med, fl_p90 = agg(func_lens)
    bl_mean, bl_med, bl_p90 = agg(body_lens)
    dl_mean, dl_med, dl_p90 = agg(docstring_lens)

    return {
        "n_files": n_files,
        "parsed_files": parsed_files,
        "parse_rate": (parsed_files / n_files) if n_files else None,
        "total_lines": total_lines,
        "n_functions": len(func_lens),
        "mean_comment_len": c_mean, "median_comment_len": c_med, "p90_comment_len": c_p90,
        "mean_complexity": x_mean, "median_complexity": x_med, "p90_complexity": x_p90,
        "mean_func_len": fl_mean, "median_func_len": fl_med, "p90_func_len": fl_p90,
        "mean_body_len": bl_mean, "median_body_len": bl_med, "p90_body_len": bl_p90,
        "mean_docstring_len": dl_mean, "median_docstring_len": dl_med, "p90_docstring_len": dl_p90,
        "frac_functions_with_docstring": (n_with_docstring / len(func_lens)) if func_lens else None,
    }


def run_panel_b(repo_dir: str, repo_name: str, since_date, until_date, out_fh: IO[str], log=print) -> int:
    writer = csv.DictWriter(out_fh, fieldnames=FIELDNAMES)
    writer.writeheader()
    n_rows = 0

    for y, q, qend, is_partial, eff_date in iter_quarters_with_partial(since_date, until_date):
        sha = commit_at_or_before(repo_dir, eff_date.isoformat())
        if sha is None:
            continue  # repo did not exist yet at this quarter
        stats = process_snapshot(repo_dir, sha)
        row = {
            "repo": repo_name,
            "quarter": f"{y}Q{q}",
            "quarter_end_date": qend.isoformat(),
            "snapshot_sha": sha,
            "is_partial_quarter": int(is_partial),
            **stats,
        }
        writer.writerow(row)
        out_fh.flush()
        n_rows += 1
        pr = stats["parse_rate"]
        pr_s = f"{pr:.2f}" if pr is not None else "n/a"
        log(f"  [{repo_name}] {y}Q{q} sha={sha[:10]} n_files={stats['n_files']} "
            f"n_functions={stats['n_functions']} parse_rate={pr_s}"
            f"{'  (PARTIAL)' if is_partial else ''}")

    return n_rows


if __name__ == "__main__":
    import argparse
    from datetime import date

    ap = argparse.ArgumentParser(description="Standalone Panel B run (for validation).")
    ap.add_argument("repo_dir")
    ap.add_argument("repo_name")
    ap.add_argument("since", help="YYYY-MM-DD")
    ap.add_argument("until", help="YYYY-MM-DD")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    since_d = date.fromisoformat(args.since)
    until_d = date.fromisoformat(args.until)

    with open(args.out_csv, "w", newline="") as fh:
        n = run_panel_b(args.repo_dir, args.repo_name, since_d, until_d, fh)
    print(f"Wrote {n} rows to {args.out_csv}")
