---
title: "npm's archived-package churn is large enough to change a published exponent"
date: 2026-09-24T09:21:01+02:00
abstract: >
  Extended cl_ecosystem_networks (the separate academic project this diary
  already tracks) by marking npm packages carrying the registry's own
  unpublished/removed/deprecated status and re-running that project's
  degree-distribution and tinkering-model fits with them excluded, to see
  whether that project's own published network statistics change once
  this churn is removed.
key_results:
  - "36% of the entire npm registry (1.9M of 5.3M packages) carries a non-null registry status, and by the most recent snapshot (2024-07-01) these packages account for 44% of nodes and 57% of edges in the raw dependency network -- diffuse throughout the graph, not a separate island (largest-WCC fraction barely moves, ~97% either way)."
  - "The fitted in-degree power-law exponent shifts from gamma=1.75 (archived packages excluded) to gamma=2.67 (included) at the same snapshot -- a qualitatively different tail shape, not a rounding difference. The excluded-only fit at 2020-01-01 (1.825) replicates that project's own previously-published gamma~1.82 figure almost exactly, since the 2020 network predates most of this churn's accumulation."
  - "The tinkering model's already-documented instability (unphysical negative p in cl_ecosystem_networks' own prior fits) reproduces in both the archived-excluded and unfiltered refits -- worth stating since it would be easy to mis-blame the new filtering for it. q (the one robust tinkering-model parameter here, from the degree-distribution MLE rather than the unstable OLS) does move: 0.137 vs. 0.084."
links:
  - label: Full report
    path: reports/CL_ECOSYSTEM_ARCHIVED_PACKAGES_REPORT.html
  - label: cl_ecosystem_networks session log
    path: file:///Users/molnar/Documents_alt/Research/cl_ecosystem_networks/quality_reports/session_logs/2026-09-24_mark-archived-npm-packages.md
  - label: cl_ecosystem_networks archived-impact figure
    path: file:///Users/molnar/Documents_alt/Research/cl_ecosystem_networks/results/figures/comparison/npm_archived_impact.png
---

Two open items, neither attempted this session: whether
`cl_ecosystem_networks`' own AI-era structural-break result (npm Chow
test at the ChatGPT release date) survives archived-package exclusion
was not rerun — the breakpoint script itself wasn't touched, only the
degree-distribution and tinkering-model fits were. And the sharp
regime shift visible in the last four months of parquet coverage
(March-July 2024, in both the archived-excluded and unfiltered series)
sits exactly at the data's collection boundary, so it's equally
consistent with a real acceleration or a late bulk-import artifact —
flagged in both projects' notes as unresolved, not chased down here.
`removed`/`unpublished` packages were excluded as both dependency
source and target (the more aggressive of two documented options);
`deprecated` packages (still technically installable, unlike the other
two statuses) were excluded on the same footing rather than kept as
valid targets, which is worth re-examining if this work continues.
