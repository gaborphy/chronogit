"""Shared constants and helpers used by both panels.

File-filter rule, comment-boilerplate rule, and the McCabe formula all live
here so both extractors (and any later re-analysis) use exactly one
definition. See ../README.md for the rationale.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import List, Optional

# ---------------------------------------------------------------------------
# File filter (the "strict" rule from the brief)
# ---------------------------------------------------------------------------

EXCLUDED_DIR_PARTS = {
    "tests", "test", "testing",
    "doc", "docs",
    "examples", "benchmarks", "asv_bench",
    "tools", "ci", "scripts",
    "_vendor", "vendored", "third_party",
}

EXCLUDED_BASENAMES = {
    "conftest.py", "setup.py", "_version.py", "versioneer.py",
}

_TEST_BASENAME_RE = re.compile(r"^(test_.*\.py|.*_test\.py)$")


def is_excluded_path(path: str) -> bool:
    """True if *path* (posix-style, relative to repo root) should be dropped.

    Applies to both panels identically. Only paths that return False here
    are ever parsed or counted as part of "the codebase".
    """
    if not path.endswith(".py"):
        return True
    parts = path.split("/")
    basename = parts[-1]
    if basename in EXCLUDED_BASENAMES:
        return True
    if _TEST_BASENAME_RE.match(basename):
        return True
    for part in parts[:-1]:
        if part in EXCLUDED_DIR_PARTS:
            return True
    return False


# ---------------------------------------------------------------------------
# Comment classification / boilerplate filter
# ---------------------------------------------------------------------------

_BOILERPLATE_LOWER_PREFIXES = ("type:", "noqa", "pylint", "flake8", "fmt:")


def is_comment_line(line: str) -> bool:
    return line.lstrip().startswith("#")


def comment_body_and_length(line: str) -> Optional[int]:
    """Return the character length of the comment (from '#' to end of line,
    trailing newline/whitespace stripped), or None if it's boilerplate /
    not a comment at all.
    """
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return None
    if stripped.startswith("#!"):
        return None  # shebang
    body = stripped.lstrip("#").strip()
    if body.startswith("-*-"):
        return None  # coding declarations
    lower = body.lower()
    if lower.startswith(_BOILERPLATE_LOWER_PREFIXES):
        return None
    comment_text = stripped.rstrip("\n").rstrip("\r")
    return len(comment_text)


def is_boilerplate_comment_text(comment_text: str) -> bool:
    """Same filter, applied to a full raw comment token/line (used by the
    tokenize-based Panel B path, where we already have the '#...' text).
    """
    return comment_body_and_length(comment_text) is None


# ---------------------------------------------------------------------------
# McCabe complexity (exact formula specified in the brief)
# ---------------------------------------------------------------------------

_HAS_MATCH = hasattr(ast, "Match")

_SIMPLE_INCREMENT_NODES = (
    ast.If, ast.For, ast.AsyncFor, ast.While,
    ast.ExceptHandler, ast.Assert, ast.IfExp,
    ast.With, ast.AsyncWith,
)


def _iter_own_scope(node: ast.AST):
    """Walk descendants of *node*, but do not descend into nested function
    or class definitions -- each of those gets scored separately as its own
    function/method, and should not inflate the complexity of its enclosing
    function.
    """
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        yield child
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(child))


def mccabe_complexity(func_node: ast.AST) -> int:
    complexity = 1
    for child in _iter_own_scope(func_node):
        if isinstance(child, _SIMPLE_INCREMENT_NODES):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            complexity += 1 + len(child.ifs)
        elif _HAS_MATCH and isinstance(child, ast.Match):
            complexity += len(child.cases)
    return complexity


# ---------------------------------------------------------------------------
# Function length / docstring split
# ---------------------------------------------------------------------------

@dataclass
class FuncShape:
    name: str
    lineno: int
    end_lineno: int
    total_len: int
    body_len: int
    docstring_len: int
    complexity: int


def _is_docstring_stmt(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def function_shape(func_node) -> FuncShape:
    total_len = func_node.end_lineno - func_node.lineno + 1
    docstring_len = 0
    if func_node.body and _is_docstring_stmt(func_node.body[0]):
        doc = func_node.body[0]
        docstring_len = doc.end_lineno - doc.lineno + 1
    body_len = total_len - docstring_len
    return FuncShape(
        name=func_node.name,
        lineno=func_node.lineno,
        end_lineno=func_node.end_lineno,
        total_len=total_len,
        body_len=body_len,
        docstring_len=docstring_len,
        complexity=mccabe_complexity(func_node),
    )


def iter_functions(tree: ast.AST):
    """Yield every FunctionDef/AsyncFunctionDef in *tree* (top-level and
    nested/methods alike -- each is its own row).
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


# ---------------------------------------------------------------------------
# Quarter helpers
# ---------------------------------------------------------------------------

def quarter_label(year: int, month: int) -> str:
    q = (month - 1) // 3 + 1
    return f"{year}Q{q}"


def quarter_end_date(year: int, quarter: int):
    from datetime import date
    end_month = quarter * 3
    if end_month == 12:
        return date(year, 12, 31)
    # last day of end_month: first day of next month minus one day
    import calendar
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, end_month, last_day)


def iter_quarters_with_partial(since_date, until_date):
    """Yield (year, quarter, quarter_end_date, is_partial, effective_date)
    for every quarter that has *started* by until_date.

    The final quarter is included with is_partial=True and effective_date
    clamped to until_date (its real end hasn't happened yet) -- callers
    decide whether to flag or drop it.
    """
    from datetime import date

    y = since_date.year
    q = (since_date.month - 1) // 3 + 1
    while True:
        qstart = date(y, (q - 1) * 3 + 1, 1)
        if qstart > until_date:
            break
        qend = quarter_end_date(y, q)
        is_partial = qend > until_date
        effective_date = min(qend, until_date)
        yield y, q, qend, is_partial, effective_date
        q += 1
        if q > 4:
            q = 1
            y += 1


def percentile(data: List[float], p: float) -> Optional[float]:
    """Nearest-rank percentile; None for empty input."""
    if not data:
        return None
    s = sorted(data)
    import math
    k = max(0, min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1))
    return s[k]
