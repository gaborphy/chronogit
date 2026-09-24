# npm's archived-package churn is large enough to change a published exponent

**Question:** in `cl_ecosystem_networks` (the separate academic project this
diary already tracks — see
[`AI_DEPENDENCY_NETWORK_REPORT.md`'s connection section](AI_DEPENDENCY_NETWORK_REPORT.md#connection-to-cl_ecosystem_networks)),
npm's registry carries a large population of packages flagged
`unpublished`/`removed`/`deprecated`. Does leaving them in the dependency
graph meaningfully change that project's own published network statistics
and model fits? **Yes.** Excluding them shifts the fitted in-degree
power-law exponent from 2.67 to 1.75 at the same snapshot — not a small
correction, a qualitatively different distribution shape — and the
project's own previously-published γ≈1.82 figure only replicates once
archived packages are removed.

This report summarizes a session spent inside `cl_ecosystem_networks`
(`~/Documents_alt/Research/cl_ecosystem_networks/`, explored and extended
directly, not read-only this time — new scripts were added there) marking
and excluding npm's archived-status packages, then re-running that
project's own degree-distribution and tinkering-model fitting methodology
on the resulting "active-only" network. Full detail lives in that
project's own session log,
`quality_reports/session_logs/2026-09-24_mark-archived-npm-packages.md`.

## What "archived" means here

`cl_ecosystem_networks` ingests the ecosyste.ms bulk data release, whose
`packages` table carries the npm registry's own `status` field. Of
5,325,740 total npm packages in that data:

| status | count | % |
|---|---|---|
| active (`NULL`) | 3,423,886 | 64.3% |
| unpublished | 1,420,645 | 26.7% |
| removed | 383,290 | 7.2% |
| deprecated | 97,919 | 1.8% |

36% of the entire npm registry carries a non-null status. This was
confirmed as the intended definition of "archived" with the project's
owner before building on it (a GitHub-repo-archived-flag interpretation
was considered and rejected — ecosyste.ms doesn't carry that signal, and
it wasn't what was meant).

## Method

Two new scripts were added to `cl_ecosystem_networks/src/`:

- `analysis/mark_archived_packages.py` — classifies every npm package by
  status, writes small committed summary CSVs plus an external Parquet
  lookup (too large for that project's `data/exports/` 1MB convention).
- `analysis/network_stats_active.py`, `models/tinkering_model_active.py`,
  `plotting/plot_degree_snapshots_active.py` — re-run that project's own
  existing active-version-semantics DuckDB/Parquet methodology
  (`densification_curves.py`'s pattern; `tinkering_model.py`'s degree-fit
  and ODE-regression methodology, ported not imported, to avoid coupling
  to a script flagged as legacy) with archived packages excluded as both
  dependency source **and** target — the more aggressive of two
  documented options, on the reasoning that a `removed`/`unpublished`
  package is genuinely uninstallable, so counting it as a valid node
  overstates the graph a developer can actually resolve today.

npm-only (the only ecosystem with this marking); two structural snapshots
(2021-01-01, 2024-07-01 — the parquet data's actual coverage boundary,
not 2026 as that project's own older exports assume) and a monthly
2020–2024 time series for the tinkering-model fit.

## Finding 1: archived packages are co-mingled through the network, not off to the side

| | 2021-01-01 | 2024-07-01 |
|---|---|---|
| unfiltered nodes / edges | 1,009,983 / 4,716,202 | 3,442,564 / 27,120,742 |
| active-only nodes / edges | 908,263 / 4,050,364 | 1,941,028 / 11,553,864 |
| archived share | 10% / 14% | **44% / 57%** |

By the most recent snapshot, archived packages are **most of the raw
graph's edges**, and the share has grown sharply since 2021 — consistent
with registry churn accumulating over time rather than a one-off event.
Largest-weakly-connected-component fraction barely moves either way
(~97%), so this isn't a separate archived island distorting connectivity
counts; it's diffuse, present throughout the graph.

## Finding 2: this changes a fitted exponent, not just a size count

Degree-distribution MLE fits (Clauset et al. power-law for in-degree,
geometric MLE for out-degree) at 2024-07-01:

| | active only | unfiltered |
|---|---|---|
| γ_in (in-degree power-law) | **1.7495 ± 0.0015** | 2.6721 ± 0.0012 |
| λ_out (out-degree exponential) | 0.1469 | 0.0872 |
| q = 1 − e^(−λ_out) | 0.1367 | 0.0835 |

`cl_ecosystem_networks`' own `docs/synthesis_brief.md` previously reported
"γ ≈ 1.82 (npm, 2020-01-01)." This session's active-only fit at
2020-01-01 gives 1.825 — a near-exact replication, and a useful
cross-check that the new methodology is consistent with the project's
existing work. What it also means, read the other way: **that earlier
figure only holds because the network it was computed from was
already, incidentally, mostly free of the archived-package churn that
had by 2024 grown to 44–57% of the raw graph** — a 2020 snapshot predates
most of the accumulation this report measures. A 2024 fit computed
without this exclusion would have reported γ≈2.67 instead, a materially
different tail shape.

## Finding 3: the tinkering model's instability is not caused by this filtering

`cl_ecosystem_networks`' tinkering-model fit (Valverde & Solé; `p`, `q`
via `dL/dN = mp + mq·L/N`) already carries a documented limitation —
their own brief calls it a "7–10× amplitude mismatch... initial condition
dependence... unresolved." Refitting on the active-only network reproduces
the same instability: `p` comes out unphysically negative in *both*
variants at 2024-07-01 (active-only −0.43, unfiltered −0.31), and the
expanding-window OLS swings wildly across the entire 2020–2024 series in
both, not just at the archived-heavy tail. Worth stating plainly since
it would be easy to mis-blame the archived-package filtering for this:
**it doesn't cause the instability, it was already there.** `q` (from the
degree-distribution MLE, not the OLS) is the only tinkering-model
parameter reliable enough here to draw a comparison from, and it moves
the same direction as γ_in and λ_out: 0.137 (active-only) vs. 0.084
(unfiltered) at 2024-07-01.

## Caveat carried over, unresolved

Both variants show a sharp jump in the last four months of parquet
coverage (March→July 2024: active-only N rises 1.49M→1.83M, 23% in four
months against a ~1–2%/month baseline; γ_in drops 1.818→1.750 over the
same window). It shows up whether or not archived packages are excluded,
so it isn't an artifact of this report's filtering — but it sits exactly
at the data's coverage boundary, so it's equally consistent with a real
late-2024 acceleration or a late bulk-import batch in how the source data
was collected. `cl_ecosystem_networks`' own session log flags this
explicitly as unresolved, not investigated further here.

## Connection back to the AI-breakpoint question

This project's [`AI_DEPENDENCY_NETWORK_REPORT.md`](AI_DEPENDENCY_NETWORK_REPORT.md#connection-to-cl_ecosystem_networks)
already names `cl_ecosystem_networks`' `ai_breakpoint_analysis.py`
Chow-test result (npm: F=11.47, p=0.0001 at the ChatGPT release date, but
not independently found by an unconstrained break search) as an open
question this project's small AI-flagged sample couldn't help resolve at
that project's scale. This report doesn't resolve it either, but adds a
relevant methodological fact: **that breakpoint analysis, like the
γ≈1.82 figure above, was run on the unfiltered network** — the same
network now shown to be 44–57% archived-package edges at recent
snapshots. Whether the post-2022 densification break survives
archived-package exclusion is an open question this report does not
attempt (the breakpoint script wasn't rerun on the active-only edge set),
flagged here as the natural next step for whichever project picks it up.
