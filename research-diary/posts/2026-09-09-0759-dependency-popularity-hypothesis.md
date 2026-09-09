---
title: "Are popular packages more likely to end up in a newborn package's dependency list?"
date: 2026-09-09T07:59:38+02:00
abstract: >
  Tested this as a case-control comparison, not just a description: parsed
  declared dependencies for the 1,530 vintage-cohort newborn packages
  (1,156 had at least one, 14,832 edges to 3,025 unique packages) and
  compared their popularity against a popularity-blind random sample of
  400 PyPI packages.
key_results:
  - "Decisive for stars and forks: dependency-set median is 813 stars vs 3 for a random package (271x, Mann-Whitney p=2.4e-84) -- a random used-dependency beats a random baseline package on stars 90% of the time."
  - "Real but much weaker for lifetime contributors (3.3x, p=3.4e-5, 67% effect size) -- plausibly because contributor count also reflects project age/size, not just visibility."
  - "Within the dependency set, being depended on by more of the 1,530 newborns correlates only moderately with popularity (Spearman ~0.34) -- popularity looks close to necessary for broad adoption but isn't sufficient (pyyaml, six rank top-10 by fan-in despite modest star counts). A later follow-up (see the time-dimension work in the full report) found no evidence this concentration effect is actually increasing over cohort years -- a naive signal that didn't survive a sample-size correction."
links:
  - label: Full report
    path: reports/DEPENDENCY_REPORT.html
  - label: Dependency edges & resolved popularity data
    path: ../repo-metrics/output/deps/
  - label: Charts
    path: ../repo-metrics/output/deps/charts/
---

Caveat carried over directly from the report: the 1,530-package sample is
itself star-ranked at the source (see the vintage-cohort post), so this
can't cleanly separate "popular packages get chosen because they're
popular" from "trendy new packages and trendy dependencies both move
together." The `setup.py` parser also had to handle the common
`install_requires = [...]` module-level-variable pattern (not just an
inline literal list passed straight to `setup()`) to avoid under-counting
dependencies -- same AST-literal-only discipline as the rest of this
project, no code execution involved.
