#!/usr/bin/env python3
"""Render the repo-metrics/*.md reports into themed HTML pages under
research-diary/reports/, so the diary's "Full report" links point at a
page that actually renders in a browser instead of raw markdown source.

Source of truth stays the .md files in repo-metrics/ -- this is a pure
read-only render step, never edits them. Re-run any time those change;
called automatically from build.py so the two can't drift out of sync.
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

DIARY_DIR = Path(__file__).resolve().parent
ROOT = DIARY_DIR.parent
REPO_METRICS = ROOT / "repo-metrics"
REPORTS_OUT_DIR = DIARY_DIR / "reports"

# source .md (in repo-metrics/) -> rendered filename (in research-diary/reports/)
REPORTS = {
    "REPORT.md": "REPORT.html",
    "VINTAGE_REPORT.md": "VINTAGE_REPORT.html",
    "DEPENDENCY_REPORT.md": "DEPENDENCY_REPORT.html",
    "README.md": "README.html",
}

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc", "codehilite"]
MD_EXTENSION_CONFIGS = {"codehilite": {"guess_lang": False}}

TAG_ATTR_RE = re.compile(r'(<(?:a|img) [^>]*(?:href|src)=")([^"]+)(")')
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)


def _rewrite_url(url: str) -> str:
    if url.startswith(("http://", "https://", "#", "mailto:")):
        return url
    path, _, frag = url.partition("#")
    if path in REPORTS:
        # internal cross-link to another rendered report, same directory
        return REPORTS[path] + (f"#{frag}" if frag else "")
    # otherwise a repo-metrics-relative asset (chart image, data dir, ...)
    return f"../../repo-metrics/{path}" + (f"#{frag}" if frag else "")


def _rewrite_links(body_html: str) -> str:
    return TAG_ATTR_RE.sub(lambda m: m.group(1) + _rewrite_url(m.group(2)) + m.group(3), body_html)


def _style_bootstrap(body_html: str) -> str:
    body_html = body_html.replace("<table>", '<table class="table table-striped table-bordered table-sm">')
    body_html = re.sub(r'<img ([^>]*)>', r'<img class="img-fluid rounded border my-3" \1>', body_html)
    return body_html


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - ChronoGit Research Diary</title>
<link rel="stylesheet" href="../vendor/bootstrap-yeti.min.css">
<link rel="stylesheet" href="report.css">
</head>
<body>
  <nav class="navbar navbar-expand navbar-dark bg-primary mb-4">
    <div class="container">
      <a class="navbar-brand mb-0 h1" href="../index.html">&larr; ChronoGit Research Diary</a>
    </div>
  </nav>
  <div class="container report-container">
{body}
  </div>
</body>
</html>
"""


def render_one(src_name: str, out_name: str) -> None:
    src_path = REPO_METRICS / src_name
    text = src_path.read_text()
    body_html = markdown.markdown(text, extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS)
    body_html = _rewrite_links(body_html)
    body_html = _style_bootstrap(body_html)

    m = H1_RE.search(body_html)
    title = re.sub(r"<[^>]+>", "", m.group(1)) if m else src_name

    page = PAGE_TEMPLATE.format(title=title, body=body_html)
    REPORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_OUT_DIR / out_name).write_text(page)


def render_pygments_css() -> None:
    css = HtmlFormatter(style="default").get_style_defs(".codehilite")
    (REPORTS_OUT_DIR / "pygments.css").write_text(css)


def render_report_css() -> None:
    css = """.report-container {
  max-width: 900px;
  background: #fff;
  padding: 2.5rem 3rem;
  margin-top: 1rem;
  margin-bottom: 3rem;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.report-container img { max-width: 100%; }
.report-container table { font-size: 0.92rem; }
.report-container pre { background: #f6f8fa; padding: 0.75rem; border-radius: 4px; overflow-x: auto; }
@import url("pygments.css");
"""
    (REPORTS_OUT_DIR / "report.css").write_text(css)


def render_all() -> None:
    REPORTS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_pygments_css()
    render_report_css()
    for src, out in REPORTS.items():
        render_one(src, out)
        print(f"  rendered {src} -> reports/{out}")


if __name__ == "__main__":
    render_all()
    print(f"Done. Wrote {len(REPORTS)} report pages to {REPORTS_OUT_DIR}")
