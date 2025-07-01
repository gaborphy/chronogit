import ast
import duckdb
import pandas as pd
import json
import re
from chronogit.db import get_connection

def extract_diff_rows(conn, ext=".py") -> pd.DataFrame:
    return conn.execute(f"""
        SELECT repo_name, commit_hash, filename, diff_added_lines, diff_deleted_lines
        FROM file_code_changes
        WHERE filename LIKE '%{ext}'
    """).fetchdf()

def parse_diff_list(text: str) -> list[tuple[int, str]]:
    try:
        return eval(text) if text else []
    except Exception:
        return []

def extract_library_usage(lines: list[tuple[int, str]], edit_type: str, commit_info: dict) -> list[dict]:
    usage = []

    for lineno, line in lines:
        line = line.strip()

        # match "import numpy as np"
        if match := re.match(r"import\s+([\w\.]+)", line):
            usage.append({
                **commit_info,
                "lineno": lineno,
                "edit_type": edit_type,
                "library": match.group(1),
                "function": None
            })

        # match "from sklearn.model_selection import train_test_split"
        elif match := re.match(r"from\s+([\w\.]+)\s+import\s+([\w\*\, ]+)", line):
            funcs = [f.strip() for f in match.group(2).split(",")]
            for func in funcs:
                usage.append({
                    **commit_info,
                    "lineno": lineno,
                    "edit_type": edit_type,
                    "library": match.group(1),
                    "function": func
                })

        # match "pd.read_csv(", "np.dot(", etc.
        elif match := re.match(r"(\w+)\.(\w+)\(", line):
            usage.append({
                **commit_info,
                "lineno": lineno,
                "edit_type": edit_type,
                "library": match.group(1),
                "function": match.group(2)
            })

    return usage

def analyze_and_store_usage_changes():
    with get_connection() as conn:
        df = extract_diff_rows(conn)

        all_usage = []

        for _, row in df.iterrows():
            commit_info = {
                "repo_name": row.repo_name,
                "commit_hash": row.commit_hash,
                "filename": row.filename
            }

            added_lines = parse_diff_list(row.diff_added_lines)
            deleted_lines = parse_diff_list(row.diff_deleted_lines)

            all_usage += extract_library_usage(added_lines, "added", commit_info)
            all_usage += extract_library_usage(deleted_lines, "deleted", commit_info)

        if not all_usage:
            print("⚠️ No library usage found.")
            return

        usage_df = pd.DataFrame(all_usage)

        # create table if not exists
        conn.execute("""
        CREATE TABLE IF NOT EXISTS code_usage_changes (
            repo_name TEXT,
            commit_hash TEXT,
            filename TEXT,
            lineno INTEGER,
            edit_type TEXT,  -- 'added' or 'deleted'
            library TEXT,
            function TEXT
        )
        """)

        conn.execute("INSERT INTO code_usage_changes SELECT * FROM usage_df")

        print(f"✅ Inserted {len(usage_df)} library/function changes.")
