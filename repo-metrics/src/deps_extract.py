"""Extract declared dependencies for each of the 490 vintage-cohort
newborn packages, read directly from their manifest at the SAME snapshot
commit already used to measure their code structure (output/vintage/packages.csv)
-- no re-measurement, just a second read of the same git object.

Sources tried, in order, unioned (a repo can declare deps in more than one):
  - pyproject.toml: PEP 621 `[project.dependencies]`, or Poetry's
    `[tool.poetry.dependencies]`
  - setup.py: `install_requires=[...]` when it's a literal list (best
    effort -- AST, not execution; dynamic install_requires is skipped and
    logged, not guessed at)
  - requirements.txt (root only)

Output: one row per (newborn_repo, dependency_name) edge.
"""
from __future__ import annotations

import ast
import csv
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import List, Optional, Set

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
VINTAGE_DIR = ROOT / "output" / "vintage"
DEPS_DIR = ROOT / "output" / "deps"
CLONES_DIR = ROOT / "clones-deps"

_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_REQ_SKIP_PREFIXES = ("-", "#", "git+", "http://", "https://")


def normalize_name(name: str) -> str:
    """PEP 503 normalization: lowercase, runs of -_. collapse to a single -."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_to_name(req: str) -> Optional[str]:
    req = req.strip()
    if not req or req.startswith(_REQ_SKIP_PREFIXES) or "://" in req:
        return None
    m = _NAME_RE.match(req)
    if not m:
        return None
    return normalize_name(m.group(1))


def parse_requirements_txt(text: str) -> Set[str]:
    names = set()
    for line in text.splitlines():
        n = _requirement_to_name(line)
        if n:
            names.add(n)
    return names


def parse_pyproject_toml(text: str) -> Set[str]:
    names = set()
    try:
        data = tomllib.loads(text)
    except Exception:
        return names

    for req in data.get("project", {}).get("dependencies", []) or []:
        n = _requirement_to_name(req)
        if n:
            names.add(n)

    poetry_deps = (
        data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}
    )
    for pkg in poetry_deps:
        if pkg.lower() == "python":
            continue
        names.add(normalize_name(pkg))

    return names


def _string_list_literal(node: ast.AST) -> Optional[List[str]]:
    if isinstance(node, (ast.List, ast.Tuple)):
        out = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.append(elt.value)
            else:
                return None  # non-literal element -- don't guess
        return out
    return None


def parse_setup_py(text: str) -> Set[str]:
    """AST-based, not execution. Handles both
    `setup(install_requires=[...])` (inline literal) and the equally common
    `install_requires = [...]` / `setup(install_requires=install_requires)`
    pattern (module-level variable referenced by name) -- confirmed live on
    wagtail/wagtail, whose real 13 dependencies were silently missed until
    this second form was handled.
    """
    names = set()
    try:
        tree = ast.parse(text)
    except Exception:
        return names

    # Module-level `NAME = [literal strings]` assignments, for resolving
    # `install_requires=some_variable` references.
    top_level_lists: dict[str, List[str]] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            lit = _string_list_literal(node.value)
            if lit is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    top_level_lists[target.id] = lit

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setup"):
            continue
        for kw in node.keywords:
            if kw.arg != "install_requires":
                continue
            reqs: Optional[List[str]] = None
            if isinstance(kw.value, (ast.List, ast.Tuple)):
                reqs = _string_list_literal(kw.value)
            elif isinstance(kw.value, ast.Name):
                reqs = top_level_lists.get(kw.value.id)
            for req in (reqs or []):
                n = _requirement_to_name(req)
                if n:
                    names.add(n)
    return names


def get_manifest_texts(repo_dir: str, sha: str) -> dict:
    """Fetch pyproject.toml / setup.py / requirements.txt content at *sha*,
    root only. Returns {filename: text} for whichever exist.
    """
    paths = subprocess.check_output(
        ["git", "-C", repo_dir, "ls-tree", "--name-only", sha], text=True
    ).splitlines()
    wanted = [p for p in paths if p in ("pyproject.toml", "setup.py", "requirements.txt")]
    if not wanted:
        return {}

    specs = [f"{sha}:{p}" for p in wanted]
    proc = subprocess.Popen(
        ["git", "-C", repo_dir, "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out, _ = proc.communicate(("\n".join(specs) + "\n").encode())

    texts = {}
    pos = 0
    for path in wanted:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode(errors="replace")
        pos = nl + 1
        parts = header.split()
        if len(parts) >= 2 and parts[-1] == "missing":
            continue
        size = int(parts[2])
        content = out[pos:pos + size]
        pos += size
        if pos < len(out) and out[pos:pos + 1] == b"\n":
            pos += 1
        texts[path] = content.decode("utf-8", errors="replace")
    return texts


def extract_deps_for_package(clone_url: str, sha: str, repo_full_name: str) -> tuple[Set[str], List[str]]:
    """Returns (dependency_names, sources_used). Clones --no-checkout,
    reads manifests at *sha*, cleans up.
    """
    import shutil

    safe_name = repo_full_name.replace("/", "__")
    clone_dir = CLONES_DIR / safe_name
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    try:
        subprocess.run(
            ["git", "clone", "--no-checkout", "--quiet", clone_url, str(clone_dir)],
            check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        texts = get_manifest_texts(str(clone_dir), sha)
        names: Set[str] = set()
        sources = []
        if "pyproject.toml" in texts:
            got = parse_pyproject_toml(texts["pyproject.toml"])
            if got:
                sources.append("pyproject.toml")
            names |= got
        if "setup.py" in texts:
            got = parse_setup_py(texts["setup.py"])
            if got:
                sources.append("setup.py")
            names |= got
        if "requirements.txt" in texts:
            got = parse_requirements_txt(texts["requirements.txt"])
            if got:
                sources.append("requirements.txt")
            names |= got
        return names, sources
    except Exception as e:
        print(f"  [warn] {repo_full_name}: {e}")
        return set(), []
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir)


def main() -> None:
    DEPS_DIR.mkdir(parents=True, exist_ok=True)
    CLONES_DIR.mkdir(parents=True, exist_ok=True)

    pkgs = pd.read_csv(VINTAGE_DIR / "packages.csv")
    print(f"Extracting dependencies for {len(pkgs)} newborn packages ...")

    edges_path = DEPS_DIR / "edges.csv"
    summary_path = DEPS_DIR / "newborn_manifest_summary.csv"

    with open(edges_path, "w", newline="") as ef, open(summary_path, "w", newline="") as sf:
        ew = csv.writer(ef)
        ew.writerow(["newborn_repo", "vintage_quarter", "dependency_name"])
        sw = csv.writer(sf)
        sw.writerow(["newborn_repo", "vintage_quarter", "n_dependencies", "sources"])

        for i, row in pkgs.iterrows():
            names, sources = extract_deps_for_package(
                row["clone_url"], row["snapshot_sha"], row["repo_full_name"]
            )
            for n in sorted(names):
                ew.writerow([row["repo_full_name"], row["vintage_quarter"], n])
            sw.writerow([row["repo_full_name"], row["vintage_quarter"], len(names), ";".join(sources)])
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(pkgs)} processed ...")

    print(f"Done. Wrote {edges_path} and {summary_path}")


if __name__ == "__main__":
    main()
