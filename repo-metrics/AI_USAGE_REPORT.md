# Is AI actually writing these packages, not just being depended on?

[DEPENDENCY_REPORT.md](DEPENDENCY_REPORT.md) measured whether newborn
packages depend on AI/genAI SDKs (`openai`, `transformers`, ...) — a
*topic* signal, what a package is about. This report measures something
different: direct, retrospective evidence that a package's own code was
**written with an AI coding tool**, read straight out of its git history.
Same 1,530 vintage-cohort packages, a completely different signal.

**Headline: self-disclosed AI-tool usage went from ~0% of newborn
packages through 2021 to 73% of the (partial) 2026 cohort, and by
2025–2026 it has overtaken AI-topic SDK dependence as the dominant
"AI-relatedness" signal in this sample — recent packages are more likely
to be *written by* an AI tool than to merely *depend on* one.**

## Method

Two signal types, both read from git objects already reachable via each
package's `clone_url` + `snapshot_sha` in `output/vintage/packages.csv`
(same `--no-checkout` clone discipline as everywhere else in this
project):

1. **Commit trailers that self-identify a tool** — the same
   `Co-Authored-By: Claude` convention visible in this very project's own
   commit history. Scanned across a package's *entire* history up to its
   snapshot commit (not just a window), matched against explicit
   co-authorship/generation patterns for Claude, GitHub Copilot, Cursor,
   ChatGPT/OpenAI Codex, Devin, Gemini, Amazon Q, Windsurf, Replit, and
   Aider.
2. **Config/instruction files a repo carries for a tool to read** —
   `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`,
   `AGENTS.md`, `.windsurfrules`, and the `.claude/`, `.cursor/`,
   `.continue/`, `.windsurf/` directories — checked for presence at the
   snapshot commit.

Deliberately **strong-signal, low-recall**: matching only explicit
co-authorship trailers (not bare mentions of a tool's name) means a
positive here is solid evidence — nobody accidentally writes
`Co-Authored-By: Claude` — but a negative proves nothing. Most
AI-assisted commits (autocomplete completions, chat-suggested code pasted
in by hand, anything committed under a human's own identity) leave no
trace at all. **This measures self-disclosed usage, not true usage, and
it is a floor, not an estimate of the real rate.**

## Adoption: near-zero through 2021, then a sharp, sustained rise

![Adoption rate over time](output/ai_signal/charts/adoption_rate.png)

| cohort year | packages | % with any AI-tool signal | mean commit-share attributed to AI (all packages) |
|---|---:|---:|---:|
| 2014–2021 | 958 | 0–0.8% (noise) | ~0% |
| 2022 | 120 | 2.5% | 0.07% |
| 2023 | 120 | 2.5% | 0.03% |
| 2024 | 120 | 9.2% | 0.07% |
| 2025 | 120 | **51.7%** | 3.6% |
| 2026 (Q1–Q3, partial) | 90 | **73.3%** | 13.9% |

Trend is strong and significant: Spearman ρ=0.77, p=0.0022 for adoption
rate; ρ=0.77, p=0.0023 for mean AI-attributed commit share. 2026 is a
partial year (through the extraction date) on a smaller sample (90
packages, vs. 120 for a full year) — the rate should be read as "the most
recent few months look even more extreme than 2025," not taken as a
precise annual figure. (An earlier pass at ~10 packages/quarter found
88.9% for the partial 2026 cohort on just 27 packages — the more reliable
73.3% here, on more than 3x that sample, is the number to trust; the
overall shape and every other year are essentially unchanged.)

## This overtook AI-SDK topic dependence around 2024–2025

![Usage vs. topic](output/ai_signal/charts/adoption_vs_sdk_timeline.png)

Through 2022–2024, self-disclosed AI-tool usage and AI-SDK dependency
share moved roughly together (both in the 2–10% range) — consistent with
"AI-relatedness" mostly meaning packages *about* AI. From 2025 onward
they diverge sharply: AI-SDK dependency share plateaus around 8–9%,
while self-disclosed tool usage keeps climbing to 52% then 73%. **By
2025–2026, most of the AI signal in this sample is about *how* a package
was written, not *what* it does.** A package no longer needs to be an AI
application for AI to plausibly have written parts of it.

## Not just a self-referential niche

Repos with "claude," "copilot," "cursor," "skill," or "agent" in their
own name (Claude-skill libraries, agent-tooling meta-packages) are 26 of
the 149 packages showing any AI signal (17%, an even *smaller* share than
the 22% seen at 10/quarter) — a real presence, but a minority. Restricting
to the other 123 (packages with no such self-referential name — a
stock-analysis tool, a video-editing toolkit, a browser-automation
harness, several of Andrej Karpathy's ML research repos, and others with
no obvious connection to AI *tooling* as a topic) the same rising pattern
holds: 1 in 2014, 1 in 2017, 1 in 2018, 1 in 2020, 3 in 2022, 3 in 2023,
11 in 2024, **46 in 2025, 56 in 2026** (partial year). This is
broad-based, not an artifact of a self-referential AI-tooling category
inflating the numbers, and it's an even cleaner result at 3x the sample.

## Which tool shows up — read this one with real caution

![Tool breakdown](output/ai_signal/charts/tool_breakdown.png)

Claude dominates the trailer counts from 2024 onward (1 in 2024, 45 in
2025, 58 in 2026), ahead of Copilot (8, 24, 24) and Cursor (0, 7, 27).
**This is not a reliable read of which tool is used most — it's at least
as much a read of which tool discloses itself most consistently by
default.** Claude Code (this very project's own tool) adds a
`Co-Authored-By: Claude` trailer to every commit unless a user
disables it; GitHub Copilot's inline autocomplete, by contrast, is
attributed to nothing by default — a developer accepting Copilot
suggestions inside their own commits is invisible to this method
entirely. **Copilot in particular is almost certainly undercounted here
far more than Claude or Cursor are**, simply because its most common mode
of use leaves no marker to find. Read the adoption-rate trend (a tool was
used) as the reliable finding; read the tool-breakdown chart (which tool)
as biased toward whichever tools happen to self-disclose by convention,
not as a market-share estimate.

## The extreme cases

Some 2025–2026 packages are majority AI-attributed by commit count:
`2akouwu/reverify` (85.5%, 71/83 commits), `ShenSeanChen/waku-agent`
(84.3%), `teng-lin/notebooklm-py` (73.2%, 1,286/1,756 commits),
`Imbad0202/academic-research-skills` (70.6%), `yusufkaraaslan/Skill_Seekers`
(61.4%), `Graphify-Labs/graphify` (51.3%, 861/1,678 commits). The last is
worth flagging on its own: it's the same repo noted in the vintage-cohort
study as showing star counts implausible for a repo only months old
(115,989 stars) — a heavily-AI-agent-driven project, a bot-inflated one,
or both; either reading is consistent with an unusually high
self-disclosed AI-commit share. Also worth noting:
`anthropics/claude-agent-sdk-python` (40.6%) — Anthropic's own SDK for
building Claude-based agents, itself substantially built with Claude.
Full table: `output/ai_signal/analysis/top15_ai_attributed.csv`.

## Caveats

- **Floor, not an estimate.** Every number in this report is a lower
  bound on true AI-tool usage. The true rate is unknowable from git
  history alone for tools that don't self-disclose.
- **Disclosure convention, not usage frequency, drives the tool
  ranking** — see above. Don't read "Claude appears most" as "Claude is
  used most."
- **This still can't attribute *why*.** It shows a rising, broad-based,
  statistically strong trend in self-disclosed AI-tool usage among
  newborn packages — consistent with the "recency" component of the
  broader popularity-effect hypothesis in DEPENDENCY_REPORT.md's
  time-dimension section, but that report's *concentration* finding
  (packages converging on the same popular dependencies) did **not**
  hold up once corrected for sample size. Rising AI-tool usage and flat
  dependency concentration can both be true at once — this report
  doesn't reconcile them further; a real answer would need to check
  whether AI-tool-flagged packages specifically show different
  dependency-concentration behavior than non-flagged ones in the same
  cohort, which isn't done here.
- **2026 is a partial year** on a smaller sample (90 vs. 120 packages) —
  treat the 73.3% figure as directional, not a stable annual rate.

## Data & reproducing this

- Per-package signals: `output/ai_signal/ai_signals.csv`
- Cohort adoption rates, tool breakdown, trend tests, top-attributed
  packages: `output/ai_signal/analysis/*.csv`
- Regenerate: `python3 src/ai_signal_extract.py && python3
  src/ai_signal_analysis.py && python3 src/ai_signal_charts.py`
  (requires `output/vintage/packages.csv` from the vintage-cohort study
  and `output/deps/analysis_time/` from the dependency time-analysis)
