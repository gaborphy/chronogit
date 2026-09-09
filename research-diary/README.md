# ChronoGit Research Diary

A static blog of dated findings from the `repo-metrics/` studies. Open
`index.html` in a browser (or `python3 -m http.server` from this folder)
to read it.

## Structure

```
research-diary/
  posts/*.md   one file per diary entry (source of truth)
  build.py     regenerates index.html from posts/*.md
  style.css
  index.html   generated -- don't hand-edit, it'll be overwritten
```

## Adding a post by hand

Create `posts/YYYY-MM-DD-HHMM-<slug>.md`:

```markdown
---
title: "A descriptive title, phrased as a finding or a question"
date: 2026-09-08T19:30:18+02:00   # use the report/commit's real timestamp
summary: >
  3-6 sentences. Quantified claims, not vibes. State the honest caveats
  and what's robust vs. a single-sample artifact -- match the tone of the
  reports themselves, not marketing copy.
links:
  - label: Full report
    path: ../repo-metrics/WHATEVER_REPORT.md
  - label: Some other relevant file
    path: ../repo-metrics/output/whatever/
---

Optional longer body -- extra context, a caveat that didn't fit the
summary, or a pointer to a specific interesting number in the report.
```

Paths are relative to `research-diary/index.html` (i.e. one `../` gets you
to the project root), not to the post file itself. Then run:

```
python3 build.py
```

## Updating it via the diary-writer agent

`.claude/agents/diary-writer.md` defines a subagent that does the above
automatically: point it at the repo and ask it to "populate the diary with
current results" (or similar) and it will find report files that don't
have a post yet, write one for each in this same style, and rebuild the
site. It never edits or removes existing posts -- the diary is append-only.
