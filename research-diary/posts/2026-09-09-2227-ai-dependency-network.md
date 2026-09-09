---
title: "Do AI-authored packages build dependency networks differently?"
date: 2026-09-09T22:27:09+02:00
abstract: >
  Joined the dependency-edge data from the earlier dependency-popularity
  report against the self-disclosed AI-usage signal from the AI-usage
  report, restricted to the 296 packages born 2024 or later (139
  AI-flagged, 191 non-flagged, 6,064 edges), to test whether AI-flagged
  packages depend on more-popular or differently-structured dependency
  sets than comparable non-flagged ones.
key_results:
  - "The naive pooled comparison looks like a real effect (AI-flagged dependencies have 1.38x the median star count, p=0.029) but doesn't survive a confound check: within 2024-2026, AI-flagged-ness is nearly collinear with calendar quarter (2024Q1 is 0/30 flagged, 2026Q1 is 25/30), so a quarter-stratified Wilcoxon test on the same comparison gives p=0.69 for stars and forks, with the direction actually flipping (AI-flagged lower in 5 of 7 quarters) -- no evidence AI-flagged packages depend on more, less, or differently-positioned popularity once time is controlled for."
  - "Dependency breadth shows the same pattern -- a naive 10-vs-13 median-dependency-count gap nearly vanishes (10 vs 9.5) once stratified -- except one difference that stays stable across both naive and stratified views: AI-flagged packages have a higher rate of zero extractable dependencies (12.5-13.0% vs 8.4-9.8%), though this could be a real self-contained-scaffolding effect or a parser artifact and isn't resolved here."
  - "What is real: a compositional difference in which specific packages get used, not a structural one -- top-20 dependency overlap between the two groups is moderate (Jaccard 0.38), with AI-flagged-only picks forming an LLM-agent/API-tooling cluster (anthropic, mcp, tiktoken, typer, httpx) against a non-flagged-only classic ML/CV cluster (accelerate, huggingface-hub, opencv-python, torchvision) -- read as \"AI-flagged and non-flagged projects tend to be different kinds of software,\" not as AI authorship changing how a comparable project picks dependencies."
links:
  - label: Full report
    path: reports/AI_DEPENDENCY_NETWORK_REPORT.html
  - label: Naive & stratified comparison tables
    path: ../repo-metrics/output/deps/analysis_ai_comparison/
  - label: Charts
    path: ../repo-metrics/output/deps/charts_ai_comparison/
---

Triggered by a session spent understanding an external academic project,
`cl_ecosystem_networks` (npm/PyPI/CRAN dependency-network growth at
multi-million-node scale), whose own authors flag "decompose the
post-2022 densification effect by actual AI involvement" as unfinished
future work they have no package-level ground truth to attempt -- this
project's AI-usage signal is exactly that ground truth, at a much smaller
scale. The report is explicit that its 139 AI-flagged packages are two to
three orders of magnitude smaller than what that project's formal
break-search machinery was built for, and that a genuine next step would
be running this project's AI-signal scan over their full, star-sampling-free
newborn-package population instead. A specific confound the report names
as unresolved: being AI-flagged and being agent/LLM-topic software may be
the same underlying thing wearing two hats (someone building an agent
framework today is more likely to use Claude Code *and* import
`anthropic`/`mcp`), and this data can't separate the two.
