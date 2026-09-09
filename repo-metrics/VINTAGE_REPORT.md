# Do newly-created packages look different depending on when they were born?

The [main study](REPORT.md) tracks the same 10 mature projects across 12
calendar years. This one asks a different question: pick 30 new Python
packages born in each quarter since 2014, measure each one's structure at
the same point in its own lifecycle (~180 days after its first commit),
and see whether the *starting* shape of a newly-created package has
changed across 51 birth-cohorts. Methodology, the discovery/validation
pipeline, and every caveat are in [README.md](README.md#vintage-cohort-study-separate-from-the-above);
this document is the findings.

**Sample:** 1,530 packages across 51 quarters (2014Q1–2026Q3), a clean 30
every quarter (no shortfalls at any point in this run — a wider discovery
net than the original 10/quarter pass), from 3,220 GitHub candidates
scanned (1,348 rejected for not actually being a package — no
`setup.py`/`pyproject.toml`/`setup.cfg` — and 211 more for having a
birth-quarter that didn't match their real git history; see README for
both).

**This is a fundamentally noisier, more confounded dataset than the main
study**, and the two shouldn't be read with equal confidence: even at 30
packages per point this is nowhere near a fixed panel of 10 tracked for 12
years each, selected by a popularity signal (GitHub stars) whose baseline
shifted enormously as GitHub itself grew across the same window. Every
finding below is stated with that caveat attached, not as a footnote at
the end. (An earlier pass at 10 packages/quarter found the same
directions on every metric below, generally at somewhat larger magnitudes
— the 3x-larger sample here moderates several of the more extreme ratios
toward more trustworthy values without changing any conclusion.)

---

## Headline: newly-created packages start out much bigger and more complex now than in 2014–2015

Comparing the median of the first 8 cohort-quarters (2014Q1–2015Q4) to the
median of the last 8 (2024Q4–2026Q2):

| metric | 2014–2015 cohorts | 2024–2026 cohorts | change |
|---|---:|---:|---:|
| mean function length (lines) | 12.2 | 24.9 | **+103%** |
| mean function body length (excl. docstring) | 9.9 | 21.8 | **+120%** |
| mean McCabe complexity | 2.59 | 4.37 | **+69%** |
| median McCabe complexity | 2.0 | 2.5 | +25% |
| fraction of functions with a docstring | 31% | 50% | **+60%** |
| mean comment length (chars) | 41.3 | 42.7 | +4% |

![Family 3: function length by vintage](output/vintage/charts/vintage_family3_function_length.png)

![Family 2: complexity by vintage](output/vintage/charts/vintage_family2_complexity.png)

The magnitude here still dwarfs the equivalent numbers from the
calendar-time study, where the *same 10 mature repos*, tracked over the
*same 12 years*, showed function length +25%, body length +17%,
complexity +4.7%. Put the
two side by side and a pattern emerges: **existing, mature projects have
drifted only modestly toward longer/more-complex functions, but the
population of newly-started packages has shifted much more sharply.**
Whatever is driving code to get bigger and more elaborate over the last
decade shows up far more in what a package looks like *when it's founded*
than in how an established codebase evolves.

## Docstring rate: flat for a decade, then a sharp acceleration in 2024–2025

![Docstrings and contributors by vintage](output/vintage/charts/vintage_docstring_and_contributors.png)

The fraction of functions carrying a docstring bounces noisily between
roughly 0.13 and 0.39 for every cohort from 2014Q1 through 2024Q3 — no
trend, just quarter-to-quarter sampling noise, now measured against a
30-package cohort rather than 10 and still showing no pattern. Then:
2024Q4 = 0.52, 2025Q1 = 0.50, 2025Q2 = 0.62, 2025Q4 = 0.64 (the single
highest point in the whole series), before settling back to 0.40–0.49 in
the first three quarters of 2026. That's a distinct
step, not a continuation of the prior noise band, and it lands squarely
in the window where AI coding assistants (GitHub Copilot, ChatGPT-based
tools) went from novelty to mainstream. **This is consistent with — but
does not prove — AI-assisted authorship of new packages**: these tools
are well known to default to generating docstrings liberally. Confirming
that would need the function-level AI-detector elsewhere in this project,
not a corpus-wide aggregate like this one. Two things temper the
enthusiasm for that reading: this is exactly the highest-star, most
recent, most confound-prone slice of the sample (see below), and the
2026 figures already show it pulling back rather than continuing to
climb.

## Comment length: the one thing that doesn't move, again

![Family 1: comment length by vintage](output/vintage/charts/vintage_family1_comment_length.png)

Both state comment length (42.8 vs 41.5) and flow-added comment length
(+4.5%) are essentially flat across the entire 12-year vintage span — the
same finding as Family 1 in the calendar-time study, now confirmed on an
entirely different, non-overlapping sample of packages. Whatever people
write in a `#` comment has stayed about the same length since 2014,
regardless of whether you look at a fixed set of mature projects over
time or a fresh sample of newly-founded ones by birth year. That
consistency across two independently-built datasets is itself the
strongest single piece of evidence in this whole exercise.

## Size of added parts: noisy, but a real late uptick

![Family 4: added part size by vintage](output/vintage/charts/vintage_family4_added_part_size.png)

Log-scaled because individual packages are wildly outlier-prone here — a
180-day-old package can easily have had only a dozen commits, so one bulk
scaffold/vendoring commit dominates its own median. Reading the median
line (not the scattered dots): added-lines-per-hunk sits in a tight
2.0–2.9 band from 2014 all the way through 2025Q2 — over a decade with no
real movement — then climbs sharply to 4.1–6.6 across 2025Q3–2026Q3, its
most recent five quarters. Added-lines-per-commit follows the same shape,
more noisily: roughly 6–14 for most of the series, then 16–28 in the same
2025Q3–2026Q3 window. With the larger sample this reads as a real,
recent, and specifically-timed shift rather than the vaguer "somewhere in
2024–2026" read from the smaller pass — whatever is behind it appears to
have kicked in around mid-2025. Unlike the
calendar-time study — where hunk size for *mature* repos was essentially
perfectly flat over 12 years — new packages' initial commits do appear to
be getting chunkier recently. Given the small-N noise here, treat this as
directional, not precise.

## What NOT to read into this data

**Contributor count and commit count in the first 180 days are the
weakest signals in this study and are presented for completeness, not as
a finding.** Median contributors-in-first-180-days went from 3.75
(2014–2015 cohorts) to 13.25 (2024–2026 cohorts), a +253% change — but this sample
selects the *most-starred* packages born each quarter, and GitHub's own
user base grew roughly 20-fold across this window. A "top-10-by-stars"
package born in 2025 is being drawn from an audience of ~100M+ developers;
one born in 2014 was drawn from ~4M. Faster star accumulation mechanically
implies faster visibility, which mechanically implies more contributors
showing up sooner — independent of anything about how the code itself is
written. Several 2025–2026 candidates in the raw discovery data show star
counts hard to justify for their age at all (see README), consistent with
the well-documented recent wave of star-inflation on speculative
AI-tooling repos. **The code-shape metrics above (function length,
complexity, docstring rate) are one step removed from this confound —
they're properties of the code, not of its audience — but they aren't
fully insulated from it either**: a more-visible package attracts more
total engineering effort per unit time, which could independently push
functions to grow faster regardless of *how* people are writing them.
Nothing in this dataset can fully separate "packages are written
differently now" from "popular new packages get more attention faster
now, and more attention means more code, faster." Both are probably true
to some degree; this study cannot apportion the split.

---

## Sample health

![Sample health](output/vintage/charts/vintage_sample_health.png)

Every one of the 51 quarters hit its full 30-package target — a wider
discovery net (up to 100 candidates per quarter instead of 25) gave
enough headroom that no quarter ran out of viable candidates this time.

`state_parse_rate`'s *median* is 1.0 in essentially every quarter,
including 2014 — at 30 packages per cohort, a clean majority are already
fully Python-3-parseable and the median saturates. The *mean* tells the
real story: it dips to 0.87–0.98 across 2014–2016 before settling at
~0.97–1.00 from 2017 onward, because roughly a third of 2014–2016 cohort
packages (118 of 360, checked directly against the raw per-package data)
carry at least one Python-2-only file even though most of their
codebase parses cleanly. Same Python-2-tail effect as the calendar-time
study, just measured on freshly-founded packages rather than on old files
still living inside a 2026 mature codebase — and only visible with the
mean, not the median, once the cohort is large enough for the median to
be dominated by the (parseable) majority.

## How this compares to the published literature

Complexity and size growth as software matures is one of the most heavily
studied phenomena in software engineering, going back to Lehman's laws of
software evolution. Empirical support is generally favorable for the
growth laws specifically: Alenezi's study of five open-source systems
found complexity growth conforms to Lehman's second law [1], while
Godfrey and Tenant's Linux kernel case study found growth so strong it
was super-linear, exceeding what Lehman's original model assumed [2].
This report's own headline finding — that newly-founded packages start
out bigger and more complex depending on *when* they were founded, not
just as they individually age — sits on a different axis from either of
these (they track a single system's growth across its own releases; this
report compares different systems at the same relative age across
different founding eras), but is consistent with the broader picture that
growth in open-source software is a robust, widely-replicated phenomenon
rather than an artifact of any one project.

The closest direct comparison is Yan et al.'s cross-community study of
cyclomatic complexity and lines-of-code-per-function trends across
Apache, Google, and Spring projects, explicitly framed as "relevant for
evaluating AI-generated code" [3]. They attribute rising complexity
mainly to feature growth and fault-tolerance logic in distributed
systems, and find that continuous refactoring by key contributors can
curb the rise — an important, testable alternative explanation this
report doesn't rule out: some of the vintage-cohort growth measured here
could reflect newer packages tackling more demanding problem domains from
the start (more distributed/infra-heavy software being founded now than
in 2014) rather than a shift in how *comparable* software gets written.
This report cannot distinguish "the same kind of software is now written
bigger" from "a different, more complex kind of software is now being
written" — a limitation worth stating plainly alongside the
AI-authorship one already in this report.

On the docstring-rate finding specifically: Ji et al.'s detector-based
study of LLM-generated code and comments across company- and
community-maintained repositories (2021–2025) found that code flagged as
likely LLM-generated *decreased* over their study window, while
LLM-generated comments remained comparatively stable [4] — a result that
sits in tension with this report's finding of a sharp docstring-rate
acceleration starting 2024Q4. The two studies use different detection
approaches (Ji et al. use content-based LLM-output detectors; this report
measures documentation *coverage*, not authorship) and different
repository populations (established repos vs. this report's
newly-founded ones), so they aren't measuring the same thing — but the
discrepancy is worth flagging rather than smoothing over. This report's
docstring finding should be read as "newly-founded packages are more
thoroughly documented in the AI era," not as direct evidence of AI
authorship, which Ji et al.'s more targeted methodology suggests may
itself be a more complicated, non-monotonic trend than a simple rise.

### References

[1] [Empirical Analysis of the Complexity Evolution in Open-Source Software Systems](https://consensus.app/papers/details/41c8f7d8b3c553519acc63405144ff2c/?utm_source=claude_desktop) (Alenezi et al., 2015, *International Journal of Hybrid Information Technology*)

[2] [Evolution in open source software: a case study](https://consensus.app/papers/details/ab652abf262259f4ac052d932af544a3/?utm_source=claude_desktop) (Godfrey & Tenant, 2000, ICSM)

[3] [Evolving Trends in Cleanliness of Open Source Projects](https://consensus.app/papers/details/0c06a6ea820453ea80d3b6847bc2105f/?utm_source=claude_desktop) (Yan et al., 2026, *ACM Transactions on Software Engineering and Methodology*)

[4] [An exploratory study on LLM-generated code and comments in code repositories](https://consensus.app/papers/details/30b1626094445398b1c1427382cd7606/?utm_source=claude_desktop) (Ji et al., 2026, *Journal of Systems and Software*)

## Data & reproducing this

- Discovered candidates (up to 100/quarter, before package validation):
  `output/vintage/candidates.json`
- One row per successfully-measured package: `output/vintage/packages.csv`
- Per-repo/candidate outcome log (why each of the 3,220 scanned candidates
  succeeded or was rejected): `output/vintage/progress.json`
- Cohort-quarter aggregates (median/mean/p25/p75 across each quarter's
  packages): `output/vintage/analysis/vintage_quarterly.csv`
- Headline early-vs-late trend table: `output/vintage/analysis/vintage_trend_summary.csv`
- Regenerate: `python3 src/vintage_discover.py && python3 src/vintage_extract.py
  && python3 src/vintage_analysis.py && python3 src/vintage_charts.py`
  (each stage is resumable; re-running a finished stage is a no-op)
