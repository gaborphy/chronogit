---
title: "Does removing the GitHub-star sampling bias change any conclusion?"
date: 2026-09-10T06:57:12+02:00
abstract: >
  Built a second, equal-sized vintage cohort (1,470 packages, 2014Q1-2026Q1)
  sampled uniformly at random from the full PyPI population -- via an
  external project's bulk PyPI data dump, stratified by first release
  quarter, no popularity signal involved -- and reran the same extraction
  and AI-signal pipeline used on the original GitHub-star-ranked cohort, to
  see which of that cohort's findings hold up once the known star-sampling
  bias is removed.
key_results:
  - "The AI-usage report's headline adoption numbers were substantially inflated by star-sampling: the unbiased 2025 rate is 10.8%, not 51.7% (4.8x gap), and 2026 is 43.3% vs. 73.3% -- though the same near-zero-then-rising-after-ChatGPT shape holds in both cohorts, so the mechanism looks real even though the star-sampled magnitude was not."
  - "The vintage-cohort report's +253% contributor-count growth trend turns out to be a pure sampling artifact: it vanishes in the unbiased data (~flat, ρ=-0.11, not significant), whose median sits at exactly 1 contributor in nearly every quarter across the full 2014-2026 span -- star-ranked discovery was measuring its own increasing bias toward multi-contributor projects, not a population-wide shift."
  - "The core code-shape findings do replicate: functions, function bodies, cyclomatic complexity, docstring length/rate, and hunk/commit size all move in the same direction in the unbiased cohort as in the star-sampled one, with five of seven metrics showing significant quarter-by-quarter correlation between the two cohorts -- just at roughly half the magnitude (e.g. function length +49% vs. +103%)."
links:
  - label: Full report
    path: reports/UNBIASED_COHORT_REPORT.html
  - label: Cohort-comparison data & charts
    path: ../repo-metrics/output/cohort_comparison/
  - label: Unbiased vintage cohort data
    path: ../repo-metrics/output/vintage_unbiased/
  - label: Unbiased AI-signal data
    path: ../repo-metrics/output/ai_signal_unbiased/
---

Two methodology caveats carried over directly from the report: the new
cohort is anchored to first PyPI release rather than first git commit
(arguably the cleaner "birth" event for a published package, but a genuine
design difference from the original cohort, not a pure isolation of
sampling bias -- some of the magnitude gap could reflect that instead),
and 2026 is asymmetric between cohorts (unbiased has only 2026Q1, since
the source parquet snapshot has no PyPI releases recorded for 2026Q2/Q3).
Not attempted here: rerunning the dependency-popularity or
AI-dependency-network comparisons on this cohort -- both need a separate,
separately-expensive dependency-extraction pass. A discovery-source-specific
confound was caught before the full run: sampling by "first PyPI release
in quarter X" can surface sub-packages of already-mature monorepos as if
newborn (`open-telemetry/opentelemetry-python`, `autoresearch/autora`),
fixed with a first-commit-vs-release gap check that rejected 208
candidates in the full run.
