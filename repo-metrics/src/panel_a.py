"""Panel A -- commit flow: one raw row per commit, streamed from a single
`git log -p` process (never one git invocation per commit).

Row scope, deliberately kept in two layers so the file-filter decision is
revisitable later without re-parsing history:

  RAW layer   (n_files, added_lines, deleted_lines):
      every *.py file the commit's diff touches, no directory/basename
      filtering -- this is "whatever git says changed".

  FILTERED layer (n_hunks, hunk_added_sum, added_code_*, added_comment_*,
  added_blank_lines):
      only files that pass common.is_excluded_path() -- this is "the
      codebase" as defined for the rest of the study.

Both layers are on the same row so you can always tell how much the filter
mattered without re-running git.
"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import IO, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import comment_body_and_length, is_excluded_path  # noqa: E402

FIELDNAMES = [
    "repo", "sha", "unix_ts", "author",
    "n_files", "n_hunks", "added_lines", "deleted_lines",
    "hunk_added_sum",
    "added_code_lines", "added_code_chars",
    "added_comment_lines", "added_comment_chars",
    "added_blank_lines",
]

_MARK = "\x01CG\x01"


def _log_p_command(since: str, until: Optional[str] = None) -> list[str]:
    fmt = f"{_MARK}%H\x01%at\x01%an"
    cmd = [
        "git", "log",
        "--reverse", "--no-merges", "--no-renames",
        "-U0",
        f"--since={since}",
    ]
    if until:
        cmd.append(f"--until={until}")
    cmd += [f"--format={fmt}", "--", "*.py"]
    return cmd


class _CommitAcc:
    __slots__ = (
        "sha", "unix_ts", "author",
        "raw_files", "raw_added", "raw_deleted",
        "n_hunks", "added_code_lines", "added_code_chars",
        "added_comment_lines", "added_comment_chars", "added_blank_lines",
    )

    def __init__(self, sha: str, unix_ts: str, author: str):
        self.sha = sha
        self.unix_ts = unix_ts
        self.author = author
        self.raw_files: set[str] = set()
        self.raw_added = 0
        self.raw_deleted = 0
        self.n_hunks = 0
        self.added_code_lines = 0
        self.added_code_chars = 0
        self.added_comment_lines = 0
        self.added_comment_chars = 0
        self.added_blank_lines = 0

    def hunk_added_sum(self) -> int:
        return self.added_code_lines + self.added_comment_lines + self.added_blank_lines

    def row(self, repo: str) -> dict:
        return {
            "repo": repo,
            "sha": self.sha,
            "unix_ts": self.unix_ts,
            "author": self.author,
            "n_files": len(self.raw_files),
            "n_hunks": self.n_hunks,
            "added_lines": self.raw_added,
            "deleted_lines": self.raw_deleted,
            "hunk_added_sum": self.hunk_added_sum(),
            "added_code_lines": self.added_code_lines,
            "added_code_chars": self.added_code_chars,
            "added_comment_lines": self.added_comment_lines,
            "added_comment_chars": self.added_comment_chars,
            "added_blank_lines": self.added_blank_lines,
        }


def _classify_added_line(content: str, acc: _CommitAcc) -> None:
    clen = comment_body_and_length(content)
    if clen is not None:
        acc.added_comment_lines += 1
        acc.added_comment_chars += clen
        return
    if content.strip() == "":
        acc.added_blank_lines += 1
        return
    acc.added_code_lines += 1
    acc.added_code_chars += len(content.rstrip("\n").rstrip("\r"))


def stream_panel_a(repo_dir: str, repo_name: str, since: str, out_fh: IO[str],
                    until: Optional[str] = None) -> int:
    """Run `git log -p` in *repo_dir*, write Panel A rows to *out_fh* as we
    go, return the number of commit rows written.
    """
    writer = csv.DictWriter(out_fh, fieldnames=FIELDNAMES)
    writer.writeheader()

    cmd = _log_p_command(since, until)
    stderr_tmp = tempfile.TemporaryFile(mode="w+")
    proc = subprocess.Popen(
        cmd, cwd=repo_dir, stdout=subprocess.PIPE, stderr=stderr_tmp,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )

    acc: Optional[_CommitAcc] = None
    current_excluded = True
    in_header = False  # between "diff --git" and the file's "+++" line
    n_rows = 0

    assert proc.stdout is not None
    for line in proc.stdout:
        if line.startswith(_MARK):
            if acc is not None:
                writer.writerow(acc.row(repo_name))
                n_rows += 1
            rest = line[len(_MARK):].rstrip("\n")
            sha, unix_ts, author = rest.split("\x01", 2)
            acc = _CommitAcc(sha, unix_ts, author)
            current_excluded = True
            in_header = False
            continue

        if acc is None:
            continue  # stray output before first commit marker

        if line.startswith("diff --git "):
            in_header = True
            current_excluded = True
            continue

        if in_header:
            if line.startswith("+++ "):
                b_path = line[4:].rstrip("\n")
                if b_path.startswith("b/"):
                    b_path = b_path[2:]
                if b_path == "/dev/null":
                    # deleted file; path came from the preceding "--- a/..." line,
                    # already unused here -- deleted files contribute no added lines.
                    current_excluded = True
                else:
                    acc.raw_files.add(b_path)
                    current_excluded = is_excluded_path(b_path)
                in_header = False
            # "--- ...", "index ...", "old/new mode", "deleted/new file mode":
            # nothing else to extract from the header block.
            continue

        if line.startswith("Binary files "):
            continue

        if line.startswith("@@"):
            if not current_excluded:
                acc.n_hunks += 1
            continue

        if line.startswith("\\ No newline"):
            continue

        if line.startswith("+"):
            content = line[1:]
            acc.raw_added += 1
            if not current_excluded:
                _classify_added_line(content, acc)
            continue

        if line.startswith("-"):
            acc.raw_deleted += 1
            continue

        # blank separator lines between commits, etc. -- ignore

    if acc is not None:
        writer.writerow(acc.row(repo_name))
        n_rows += 1

    ret = proc.wait()
    stderr_tmp.seek(0)
    stderr_text = stderr_tmp.read()
    stderr_tmp.close()
    if ret != 0:
        raise RuntimeError(f"git log failed (exit {ret}) for {repo_name}:\n{stderr_text}")
    if stderr_text.strip():
        print(f"[panel_a] git stderr for {repo_name}:\n{stderr_text}", file=sys.stderr)

    return n_rows


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Standalone Panel A run (for validation).")
    ap.add_argument("repo_dir")
    ap.add_argument("repo_name")
    ap.add_argument("since")
    ap.add_argument("out_csv")
    args = ap.parse_args()

    with open(args.out_csv, "w", newline="") as fh:
        n = stream_panel_a(args.repo_dir, args.repo_name, args.since, fh)
    print(f"Wrote {n} rows to {args.out_csv}")
