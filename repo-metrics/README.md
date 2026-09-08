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

---

## Vintage-cohort study (separate from the above)

A second, independent study (`src/vintage_discover.py` /
`vintage_extract.py` / `vintage_analysis.py` / `vintage_charts.py`,
findings in `VINTAGE_REPORT.md`) asks a different question: not "how has
this fixed set of mature projects changed over time" but "how does the
*starting* structure of newly-created packages differ depending on when
they were born." Sample: ~10 packages per birth quarter, 2014Q1–2026Q3
(51 quarters, 490 packages total).

**Discovery.** GitHub's search API, `language:Python fork:false
created:<quarter-range>`, sorted by stars, one request per quarter
(unauthenticated search is rate-limited to 10/min; the much stingier
60/hour unauthenticated *core* API is deliberately never called during
discovery). Candidates are over-fetched (25/quarter) because most
star-ranked "Python" repos are not packages at all.

**"Is this actually a package" check.** Deferred to right after a
`--no-checkout` clone (a local `git ls-tree`, not a GitHub API call — see
above): requires `setup.py`, `pyproject.toml`, or `setup.cfg` at repo
root, and at least 2 in-scope `.py` files at the measurement snapshot
specifically (checking only at HEAD isn't enough — a snapshot from
shortly after birth can be far sparser than the repo is today; caught
live when `vinta/awesome-python`, a curated markdown list with 319k
stars, passed a HEAD-only check but had exactly 1 in-scope file 180 days
after its first commit). Of 978 candidates scanned, 358 were rejected
purely for lacking a manifest — a majority of "language:Python, sorted by
stars" results are not installable packages.

**Vintage vs. actual coding start.** GitHub's `created_at` is when the
*repository object* was created, which can diverge sharply from when the
code was actually first written — an existing project rehosted with
preserved history (`googleapis/google-api-python-client`: GitHub says
"created 2014Q1," git says first commit 2010, 1360 days earlier), or a
repo slot that sat empty/was transferred before real development started
(`seleniumbase/SeleniumBase`: "created" 2014Q1, real first commit late
2015, 640 days later). Both directions are rejected when
`|created_at − true_first_commit| > 180 days` (78 of 490 rejections were
this filter) — the vintage label is a package's actual git history, not
GitHub repo metadata.

**Snapshot timing.** Each package is measured once, at its first commit
date + 180 days (or "now" if younger — 18 of 490 packages, all from the
most recent couple of quarters, are flagged `is_young_partial=1`), using
the same Panel-B state extraction and a Panel-A-style flow rollup over
just that package's pre-snapshot history. This holds *age* constant
across cohorts rather than calendar date, so a 2014-born and a
2025-born package are compared at the same point in their own lifecycle.

*Known git gotcha, worth restating because it's easy to reintroduce:*
`git log --reverse --format=... -1` does **not** give the oldest commit —
`-1` limits the (newest-first) traversal before `--reverse` reorders
whatever survived that limit, so it silently returns HEAD's date instead.
Confirmed live on `wagtail/wagtail` during validation (buggy command
returned today's date; the fix — fetch the full reversed list, take the
first line — returned the real 2014-01-22 first commit). `vintage_extract.py`
uses the fix; `commit_at_or_before()` in `panel_b.py` is unaffected (no
`--reverse`, different semantics).

**Aggregation is median-based, not mean-based**, unlike the calendar-time
study: with only 7–10 packages per quarter and a handful of commits per
young package, one outlier package dominates a mean in a way it can't
dominate a median. `vintage_quarterly.csv` carries both, plus p25/p75.

**Selection-bias caveat that does not apply to the calendar-time study
above:** ranking by accumulated stars is a weaker, noisier signal for
recent quarters (less time to accumulate) than for old ones, and several
2025–2026 candidates showed star counts implausible for their age,
consistent with known GitHub star-inflation in the current AI-tooling
gold rush. Metrics tied directly to popularity/reach (contributor count,
commit count) should be read as *upper bounds on the most-quickly-visible
packages of each era*, not as population averages — and are additionally
confounded by GitHub's own userbase growth across 2014–2026. Code-shape
metrics (function length, complexity, docstring rate) are one step
removed from that confound but not immune to it either — see
`VINTAGE_REPORT.md` for the full discussion.
