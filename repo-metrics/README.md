# repo-metrics

Two independent panels measuring how Python source code has changed over time
across a sample of mature open-source projects.

- **Panel A** (`output/<repo>_panel_a.csv`) — commit flow. One raw row per
  commit touching a `*.py` file, `--since` the observation window start.
  Never aggregated at extraction time; every rollup is done later so it can
  be redone without re-parsing history.
- **Panel B** (`output/<repo>_panel_b.csv`) — codebase state. One row per
  repo-quarter, read directly from git objects (`git ls-tree` +
  `git cat-file --batch`) for the last commit on the first-parent trunk at
  or before each quarter end. No `git checkout` is ever run.

Per-repo metadata (`output/<repo>_meta.json`) records the resolved `HEAD`
SHA, its committer date, the extraction date (UTC), the since/until window
used, and clone size/time — so a run is reproducible against a
moving target.

## Running it

```
python3 src/driver.py                    # full sample from src/config.py
python3 src/driver.py --only pandas      # single repo
```

The driver processes repos strictly one at a time: `git clone --no-checkout`
→ Panel A → Panel B → write CSVs + meta → `rm -rf` the clone. It is
resumable — a repo whose `_panel_a.csv`, `_panel_b.csv`, and `_meta.json`
all already exist in `output/` is skipped, so re-running after an
interruption is a no-op for finished repos.

Edit `src/config.py` to change `REPOS`, `SINCE`, or `UNTIL`.

## The file filter (fixed once, applies to both panels)

A `.py` path is **excluded** from "the codebase" if:

- any path component is one of: `tests`, `test`, `testing`, `doc`, `docs`,
  `examples`, `benchmarks`, `asv_bench`, `tools`, `ci`, `scripts`,
  `_vendor`, `vendored`, `third_party`
- its basename is `conftest.py`, `setup.py`, `_version.py`, or
  `versioneer.py`
- its basename matches `test_*.py` or `*_test.py`

This is the "strict" rule from the brief. It is implemented once in
`src/common.py::is_excluded_path` and imported by both panels — nothing
downstream re-derives it. **Series built under a different filter are not
comparable to these**; if you change the rule, re-run everything, don't
patch numbers.

Panel A additionally keeps *raw*, filter-independent counts on the same row
(`n_files`, `added_lines`, `deleted_lines` — every `*.py` file the commit's
diff touches, unfiltered) next to the *filtered* counts
(`n_hunks`, `hunk_added_sum`, `added_code_*`, `added_comment_*`,
`added_blank_lines` — only files that pass the rule above). That way "how
much does the filter matter" is answerable from the CSV itself, without
re-running git.

## Comment boilerplate filter

A comment is dropped (not counted, in either panel) if it is:

- a shebang (`#!...`)
- a coding declaration (`# -*- coding: ... -*-`)
- a tooling directive whose body starts with (case-insensitive) `type:`,
  `noqa`, `pylint`, `flake8`, or `fmt:`

These have stable, near-constant lengths and otherwise compress the
variance the comment-length metric is meant to capture.

## McCabe complexity

Per function (`FunctionDef` / `AsyncFunctionDef`), starting at 1:

- `+1` for each `If`, `For`, `AsyncFor`, `While`, `ExceptHandler`, `Assert`,
  `IfExp`, `With`, `AsyncWith`
- `+len(values) - 1` for each `BoolOp`
- `+1 + len(ifs)` per comprehension clause
- `+len(cases)` per `Match` (3.10+; skipped on older interpreters)

Nested function/class definitions do **not** contribute to their enclosing
function's score — each nested `def` is scored separately, as its own row.

## Function length vs. body length

`node.end_lineno - node.lineno + 1` includes the docstring. When
`func.body[0]` is a bare string-literal `Expr` (a docstring), its own line
span is subtracted out to get `body_len`; `docstring_len` is reported
separately. **Always read `mean_func_len` and `mean_body_len` together** —
they diverge, and a rise in the former without the latter is documentation
growth, not complexity growth.

## Parse rate

`ast.parse` fails on Python 2 syntax (`print x`, etc.), silently for
anything before roughly 2013–2014 depending on the project.
`parsed_files / n_files` is reported per repo-quarter as `parse_rate`;
AST-derived columns (complexity, function/body/docstring length) are
computed only from files that parsed. Comment metrics come from `tokenize`,
which is a lexer, not a parser, and survives Python 2 sources — so
`mean_comment_len` etc. do not carry the same caveat. Treat any
repo-quarter with `parse_rate < 1.0` as indicative only.

## Partial trailing quarter

The **current, still-open** quarter is written to `output/<repo>_panel_b.csv`
with `is_partial_quarter = 1` (its "quarter-end" snapshot is really just
"as of extraction date") rather than dropped, since it's still a real,
labeled data point. Any quarterly rollup built from **Panel A**'s raw rows
must exclude the partial trailing quarter outright — it is short *and*
dominated by whatever landed most recently.

## Text decoding

Blob content is decoded as UTF-8 with `errors="replace"`. This is a
simplification: it does not honor PEP 263 encoding declarations for the
rare non-UTF-8 source file. Good enough for length/complexity metrics; not
byte-exact.

## Author composition

Panel A carries `author` (git author name) on every row, so any commit-flow
series can be rebuilt pooled, excluding the top-volume contributor, or as a
per-quarter distinct-author count — this is a downstream rollup, not
something the extractor decides. Panel B measures the state of the code at
a point in time, not who wrote which line, so per-author decomposition
does not apply to it directly; the closest available signal there is the
Panel-A-derived contributor count for the same repo-quarter.

## Extraction record

See `output/<repo>_meta.json` per repo for: `head_sha`,
`head_committer_date`, `since`/`until`, `extraction_date_utc`,
`clone_size_bytes`, `clone_elapsed_s`, and row counts for both panels.
