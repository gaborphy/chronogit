---
title: "How has Python source code changed since 2014?"
date: 2026-09-08T19:30:18+02:00
summary: >
  Tracked pandas, numpy, scipy, scikit-learn, matplotlib, django, sqlalchemy,
  sympy, ipython, and pytest across 12 years (2014-2026) on two independent
  panels: raw commit flow and quarterly codebase-state snapshots. Function
  length grew faster than function-body length everywhere (docstrings, not
  logic, drove a third of the apparent growth) -- confirmed panel-wide, not
  just in pandas. Median added-lines-per-hunk stayed completely flat across
  all 10 repos and 12 years while lines-per-commit rose 44% -- growth came
  from bundling more hunks per commit, not bigger edits. An event-study scan
  for a discrete break at four candidate dates (including the Nov 2022
  ChatGPT release) found none that survives correcting for each repo's own
  pre-existing trend -- sympy's dramatic-looking complexity swings turned
  out to be a module-addition/removal artifact in its function count, not a
  code-complexity story.
links:
  - label: Full report
    path: ../repo-metrics/REPORT.md
  - label: Methodology & file-filter rules
    path: ../repo-metrics/README.md
  - label: Raw panel data (per repo)
    path: ../repo-metrics/output/
  - label: Aggregated quarterly series
    path: ../repo-metrics/output/analysis/
  - label: Charts
    path: ../repo-metrics/output/charts/
---

Full writeup, charts, and the robust-vs-single-repo-artifact breakdown are
in the linked report. Headline numbers only here; see the report for the
event-study methodology and the author-controlled decomposition
(sqlalchemy's top contributor made 71% of all commits in-window; pandas
reproduces the "one dominant contributor skews a single quarter" pitfall
almost exactly in 2026Q2).
