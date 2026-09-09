# ChronoGit Research Diary

A static blog of dated findings from the `repo-metrics/` studies. Open
`index.html` directly in a browser, or serve it -- **from the project
root**, not from inside this folder, since report pages link out to
`repo-metrics/` as a sibling directory:

```
cd .. && python3 -m http.server 8000
# then open http://localhost:8000/research-diary/
```

Styled with [Bootstrap Yeti](https://bootswatch.com/yeti/) (vendored
locally in `vendor/`, no CDN dependency, no JS required -- the one
collapsible bit per post uses native `<details>`).

## Structure

```
research-diary/
  posts/*.md         one file per diary entry (source of truth)
  build.py           regenerates index.html AND reports/*.html
  render_reports.py  converts repo-metrics/*.md -> reports/*.html (called by build.py)
  vendor/bootstrap-yeti.min.css   theme, vendored (see below to update it)
  style.css          small overrides layered on top of the theme, for index.html
  index.html         generated -- don't hand-edit, it'll be overwritten
  reports/           generated -- rendered copies of the repo-metrics/*.md
                     reports, so "Full report" links open a real page
                     instead of raw markdown. Don't hand-edit; the .md
                     files in repo-metrics/ are the source of truth.
```

## Adding a post by hand

Each post is a **short abstract + 2-3 headline results**, not the report
itself -- that's what the report is for. Create
`posts/YYYY-MM-DD-HHMM-<slug>.md`:

```markdown
---
title: "A descriptive title, phrased as a finding or a question"
date: 2026-09-08T19:30:18+02:00   # use the report/commit's real timestamp
abstract: >
  One or two sentences: what was measured, on what sample. Framing only --
  the findings go in key_results, not here.
key_results:
  - "Headline finding 1, quantified. Match the report's own hedging -- if it says 'suggestive, not proven,' say that here too."
  - "Headline finding 2, quantified."
  - "Headline finding 3 (optional), quantified."
links:
  - label: Full report
    path: reports/WHATEVER_REPORT.html   # NOT the .md -- see below
  - label: Some other relevant file
    path: ../repo-metrics/output/whatever/
---

Optional longer body -- extra context, a caveat that didn't fit the
abstract, a bug caught during validation. Rendered collapsed under
"More notes" so it doesn't bulk out the post itself.
```

**"Full report" links point at `reports/<NAME>.html`, never at the
`repo-metrics/*.md` source directly** -- raw markdown doesn't render as a
page in a browser. If the report you're linking isn't yet in
`render_reports.py`'s `REPORTS` dict, add it there (source `.md` filename
-> output `.html` filename); `build.py` calls it automatically so the
rendered page and the source can't drift out of sync. Every other link
(data files, chart directories) is relative to `research-diary/index.html`
(i.e. one `../` gets you to the project root), not to the post file
itself. Then run:

```
python3 build.py
```

## Updating the theme

`vendor/bootstrap-yeti.min.css` is a plain download, not a package
dependency:

```
curl -sL "https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/yeti/bootstrap.min.css" \
  -o vendor/bootstrap-yeti.min.css
```

Bump the version in that URL to update. Switching to a different
Bootswatch theme is the same command with a different theme name.

## Updating it via the diary-writer agent

`.claude/agents/diary-writer.md` defines a subagent that does the above
automatically: point it at the repo and ask it to "populate the diary with
current results" (or similar) and it will find report files that don't
have a post yet, write one for each in this same style, and rebuild the
site. It never edits or removes existing posts -- the diary is append-only.
