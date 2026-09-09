---
title: "Do newly-created packages look different depending on when they were born?"
date: 2026-09-08T23:15:01+02:00
abstract: >
  Sampled 30 new Python packages per birth quarter from GitHub search,
  2014Q1-2026Q3 (1,530 packages -- rescaled up from an original 10/quarter,
  490-package pass, every quarter now hitting its full target with no
  shortfalls), and measured each one once at ~180 days old so different
  eras are compared at the same point in a package's life, not the same
  calendar date.
key_results:
  - "Function length and complexity grew far more for newly-founded packages (+103% / +69%, 2014-15 vs 2024-26 cohorts) than for the mature, tracked-over-time repos in the calendar-time study (+25% / +4.7%) -- most of the \"code got bigger\" signal is in what gets founded now, not in how existing projects evolved. (Same direction as the original 10/quarter pass, at more trustworthy, less extreme magnitudes.)"
  - "Comment length stayed flat here too, independently confirming the calendar-time study's strongest result."
  - "Docstring rate shows a sharp, untrended jump starting 2024Q4 -- timing consistent with mainstream AI-coding-assistant adoption, flagged as suggestive rather than proven. Added-lines-per-hunk tells a similarly precise story at this larger scale: flat for over a decade (2014-2025Q2), then a sharp climb starting specifically 2025Q3."
links:
  - label: Full report
    path: reports/VINTAGE_REPORT.html
  - label: Methodology & pipeline caveats
    path: reports/README.html
  - label: Per-package data
    path: ../repo-metrics/output/vintage/packages.csv
  - label: Cohort-quarter aggregates
    path: ../repo-metrics/output/vintage/analysis/
  - label: Charts
    path: ../repo-metrics/output/vintage/charts/
---

Two real bugs were caught and fixed during single-quarter validation before
committing to the full 51-quarter run, both documented in the report:
`git log --reverse ... -1` silently returns HEAD's date instead of the
oldest commit's (confirmed live on wagtail/wagtail), and a repo's
"is this a package" check has to run at the measurement snapshot, not just
at HEAD (a curated markdown list with 319k stars slipped through a
HEAD-only check with 1 real Python file 180 days after its first commit).
Also added a filter this study needed but the calendar-time one didn't:
rejecting candidates where GitHub's `created_at` diverges more than 180
days from the git history's true first commit, catching cases like
`google-api-python-client` (GitHub says "created 2014," real first commit
is from 2010).
