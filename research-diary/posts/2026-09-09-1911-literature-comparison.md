---
title: "How do these findings hold up against the published literature?"
date: 2026-09-09T19:11:18+02:00
abstract: >
  Searched peer-reviewed literature via Consensus for research relevant to
  each of the four reports' core findings, and added a "How this compares
  to the published literature" section plus numbered references to all
  four (18 references total). Deliberately included points of tension,
  not just agreement.
key_results:
  - "Two very recent (2026) studies use near-identical methodology to the AI-usage report's own -- commit co-authoring traces and config-file scanning at far larger scale (128,018 and 180M repositories) -- and independently corroborate its two headline findings: agent-assisted commits are larger than human-only ones (matching the sharp added-lines-per-hunk uptick starting 2025Q3), and Claude Code specifically dominates silent, config-file-only self-disclosure. One of the two also puts a hard number on this project's own \"floor, not an estimate\" caveat: bot-account lookup alone recovers only 3.3% of what full multi-signal detection finds."
  - "The dependency-popularity report's case-control result replicates a direct prior finding from a different ecosystem (npm highly-selected packages correlating with stars/downloads), and its no-rising-concentration finding lines up with network-growth models showing dependency networks settle into a self-limiting \"sustainable regime\" as they mature -- rather than concentrating further under naive preferential attachment."
  - "Real tension surfaced too, not smoothed over: a detector-based study found LLM-generated code *decreasing* over 2021-2025 even as this project's own docstring-rate finding rises sharply from 2024Q4 (different things being measured -- authorship detection vs. documentation coverage); a commit-classification study on an overlapping repo (pandas) found a documentation-commit *decrease* post-2022, where this project's own trend-corrected event study found no discrete break at all."
links:
  - label: Calendar-time study references
    path: reports/REPORT.html#how-this-compares-to-the-published-literature
  - label: Vintage-cohort study references
    path: reports/VINTAGE_REPORT.html#how-this-compares-to-the-published-literature
  - label: Dependency-popularity references
    path: reports/DEPENDENCY_REPORT.html#how-this-compares-to-the-published-literature
  - label: AI-usage references
    path: reports/AI_USAGE_REPORT.html#how-this-compares-to-the-published-literature
---

Deliberate choice worth stating plainly: every report's literature section
includes at least one point of disagreement or unresolved tension with
this project's own findings, not only corroborating citations. Two
examples beyond the docstring/documentation ones above: Godfrey and
Tenant's Linux kernel case study found *super-linear* (accelerating)
growth, more dramatic than any pattern in the calendar-time study's ten
repos, suggesting this project's panel sits toward the calmer end of
what's been observed elsewhere, not an extreme outlier. And Yan et al.'s
cross-community complexity study attributes rising complexity partly to
projects tackling more demanding problem domains (distributed systems,
fault tolerance) as they mature -- a plausible alternative explanation
for the vintage-cohort report's growth findings that this project cannot
rule out with the data it has: it cannot distinguish "the same kind of
software is now written bigger" from "a different, more complex kind of
software is now being founded."
