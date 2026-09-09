---
title: "Is AI actually writing these packages, not just being depended on?"
date: 2026-09-09T09:55:43+02:00
abstract: >
  A genuinely different signal from the earlier AI/genAI-SDK-dependency
  proxy: read the same 490 vintage-cohort packages' own git history for
  direct, self-disclosed evidence of AI-tool authorship -- commit trailers
  like "Co-Authored-By: Claude" and AI-tool config files (CLAUDE.md,
  .cursorrules, AGENTS.md, ...) present at each package's snapshot.
  Strong-signal, low-recall by design: a positive is solid evidence, a
  negative proves nothing, so every number here is a floor on true usage.
key_results:
  - "Self-disclosed AI-tool usage went from ~0% of newborn packages through 2021 to 89% of the (partial) 2026 cohort -- 7.9% (2022), 5.0% (2023), 15.0% (2024), 50.0% (2025), 88.9% (2026 Q1-Q3) -- a strong, significant trend (Spearman p=0.003)."
  - "This overtook AI-SDK topic dependence as the dominant \"AI-relatedness\" signal by 2025: the two moved together through 2022-2024 (~5-15%), then AI-SDK share plateaued around 8-10% while self-disclosed usage kept climbing to 50% then 89%."
  - "Confirmed broad-based, not a self-referential niche: 78% of AI-signal-positive packages have no \"claude/copilot/cursor/skill/agent\" in their own name, and the same rising pattern holds within just that non-meta subset."
links:
  - label: Full report
    path: reports/AI_USAGE_REPORT.html
  - label: Per-package signals
    path: ../repo-metrics/output/ai_signal/ai_signals.csv
  - label: Charts
    path: ../repo-metrics/output/ai_signal/charts/
---

Important limitation carried over directly from the report, not to be
missed: the tool-breakdown chart shows Claude dominating from 2024
onward, but that's at least as much a read of which tools self-disclose
by default (Claude Code adds a co-author trailer to every commit unless
disabled -- the same convention visible in this very project's own
history) as of which tool is actually used most. GitHub Copilot's
inline-autocomplete mode leaves no trace by default and is almost
certainly undercounted relative to Claude and Cursor here. Also worth a
look: `Graphify-Labs/graphify` (51.3% AI-attributed commits) is the same
repo flagged in the vintage-cohort study for star counts implausible for
its age -- a heavily-AI-agent-driven project, a bot-inflated one, or both.
