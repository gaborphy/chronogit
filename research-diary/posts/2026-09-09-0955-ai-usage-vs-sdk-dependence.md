---
title: "Is AI actually writing these packages, not just being depended on?"
date: 2026-09-09T09:55:43+02:00
abstract: >
  A genuinely different signal from the earlier AI/genAI-SDK-dependency
  proxy: read the same 1,530 vintage-cohort packages' own git history for
  direct, self-disclosed evidence of AI-tool authorship -- commit trailers
  like "Co-Authored-By: Claude" and AI-tool config files (CLAUDE.md,
  .cursorrules, AGENTS.md, ...) present at each package's snapshot.
  Strong-signal, low-recall by design: a positive is solid evidence, a
  negative proves nothing, so every number here is a floor on true usage.
key_results:
  - "Self-disclosed AI-tool usage went from ~0% of newborn packages through 2021 to 73% of the (partial) 2026 cohort -- 2.5% (2022), 2.5% (2023), 9.2% (2024), 51.7% (2025), 73.3% (2026 Q1-Q3) -- a strong, significant trend (Spearman p=0.002)."
  - "This overtook AI-SDK topic dependence as the dominant \"AI-relatedness\" signal by 2025: the two moved together through 2022-2024 (~2-10%), then AI-SDK share plateaued around 8-9% while self-disclosed usage kept climbing to 52% then 73%."
  - "Confirmed broad-based, not a self-referential niche: 83% of AI-signal-positive packages have no \"claude/copilot/cursor/skill/agent\" in their own name, and the same rising pattern holds within just that non-meta subset -- an even cleaner result than the original 10/quarter pass."
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
At 3x the sample, even more extreme cases turned up: `2akouwu/reverify`
(85.5%) and `ShenSeanChen/waku-agent` (84.3%), plus
`anthropics/claude-agent-sdk-python` (40.6%) -- Anthropic's own
Claude-agent SDK, itself substantially built with Claude.
