import duckdb
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from pip._internal.utils.misc import ensure_dir

load_dotenv()
DB_PATH = os.getenv("CHRONOGIT_DB", "data/chronogit.duckdb")

def get_connection():
    """
    Get a connection to the DuckDB database.
    """
    conn = duckdb.connect(DB_PATH)
    return conn

def initialise_db():
    with get_connection() as conn:
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS commits
                     (
                         commit_hash TEXT,
                         repo_name TEXT,
                         author TEXT,
                         author_email TEXT,
                         date TIMESTAMP,
                         message TEXT,
                         query_time TIMESTAMP,
                         content_hash TEXT,
                         PRIMARY KEY (commit_hash, repo_name)
                     );
                     """)

        conn.execute("""
                     CREATE TABLE IF NOT EXISTS file_edits(
                         commit_hash TEXT,
                         repo_name TEXT,
                         filename TEXT,
                         added_lines INTEGER,
                         deleted_lines INTEGER,
                         change_type TEXT,
                         PRIMARY KEY (commit_hash, repo_name, filename),
                         FOREIGN KEY (commit_hash, repo_name) REFERENCES commits(commit_hash, repo_name)
                     );
                        """)

        conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_code_changes (
                        commit_hash TEXT,
                        repo_name TEXT,
                        filename TEXT,
                        diff TEXT,
                        diff_added_lines TEXT,
                        diff_deleted_lines TEXT,
                        source_code_before TEXT,
                        source_code_after TEXT,
                        PRIMARY KEY (commit_hash, repo_name, filename),
                        FOREIGN KEY (commit_hash, repo_name, filename) REFERENCES file_edits(commit_hash, repo_name, filename)
                    );
        """)

        conn.execute("""
                     CREATE TABLE IF NOT EXISTS repo_status (
                        repo_name TEXT PRIMARY KEY,
                        repo_url TEXT,
                        last_commit TIMESTAMP,
                        last_commit_hash TEXT,
                        first_commit TIMESTAMP,
                        first_commit_hash TEXT,
                        commit_count INTEGER,
                        query_ts TIMESTAMP
                    );
        """)

        conn.execute("""
                    CREATE TABLE IF NOT EXISTS library_usage (
                        commit_hash TEXT,
                        repo_name TEXT,
                        filename TEXT,
                        library TEXT,
                        function TEXT,
                        edit_type TEXT,
                        query_time TIMESTAMP,
                        PRIMARY KEY (commit_hash, repo_name, filename, library, function, edit_type),
                        FOREIGN KEY (commit_hash, repo_name, filename) REFERENCES file_edits(commit_hash, repo_name, filename)
                    );
        """)

from chronogit.git_parser import CommitRecord, FileEdit

def store_commits(commits: list[CommitRecord]):
    with get_connection() as conn:
        for commit in commits:
            conn.execute("""
                         INSERT OR IGNORE INTO commits VALUES (?, ?, ?, ?, ?, ?)
                         """, [commit.hash, commit.repo_name, commit.author, commit.author_email,
                               commit.date, commit.msg])

            for file in commit.files:
                res = conn.execute("""
                             INSERT or ignore INTO file_edits (
                        commit_hash, repo_name, filename, added_lines, deleted_lines, change_type
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, [commit.hash, commit.repo_name, file.filename, file.added_lines, file.deleted_lines, file.change_type])

                conn.execute("""
                             INSERT INTO file_code_changes 
                             (commit_hash, repo_name, filename, diff, diff_added_lines,
                             diff_deleted_lines, source_code_before, source_code_after)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                             """, [commit.hash, commit.repo_name, file.filename, file.diff, str(file.diff_added),
                                   str(file.diff_deleted), file.source_before, file.source_after])


def get_existing_hashes(repo_name: str) -> set[str]:
    with get_connection() as conn:
        result = conn.execute(
            "SELECT commit_hash FROM commits WHERE repo_name = ?", [repo_name]
        ).fetchall()
        return set(r[0] for r in result)

def write_parquet_files(commits: list[CommitRecord], base_dir: str = "tmp_parquet"):
    if not commits:
        return

    repo_name = commits[0].repo_name
    out_dir = os.path.join(base_dir, repo_name)
    ensure_dir(out_dir)

    df_commits = pd.DataFrame([
        {
            "commit_hash": c.hash,
            "repo_name": c.repo_name,
            "author": c.author,
            "author_email": c.author_email,
            "date": c.date,
            "message": c.msg,
            "query_time": datetime.now(),
            "content_hash": c.hash,
        }
        for c in commits
    ])

    df_files = pd.DataFrame([
        {
            "commit_hash": c.hash,
            "repo_name": c.repo_name,
            "filename": f.filename,
            "added_lines": f.added_lines,
            "deleted_lines": f.deleted_lines,
            "change_type": f.change_type,
        }
        for c in commits for f in c.files
    ])

    df_code = pd.DataFrame([
        {
            "commit_hash": c.hash,
            "repo_name": c.repo_name,
            "filename": f.filename,
            "diff": f.diff,
            "diff_added_lines": str(f.diff_added),
            "diff_deleted_lines": str(f.diff_deleted),
            "source_code_before": f.source_before,
            "source_code_after": f.source_after,
        }
        for c in commits for f in c.files
    ])

    df_commits.to_parquet(os.path.join(out_dir, "commits.parquet"), index=False)
    df_files.to_parquet(os.path.join(out_dir, "file_edits.parquet"), index=False)
    df_code.to_parquet(os.path.join(out_dir, "file_code_changes.parquet"), index=False)

    print(f"✅ Written {len(df_commits)} commits to {out_dir}/")


# Implement a function to get repo status
def store_repo_status(repo_name: str, repo_url: str, commits: list[CommitRecord]):
    """
    Save a summary of a repository's commit stats.
    """
    if not commits:
        return

    # Sort by date
    sorted_commits = sorted(commits, key=lambda c: c.date)
    first_commit = sorted_commits[0]
    last_commit = sorted_commits[-1]

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO repo_status (
                repo_name, repo_url,
                first_commit, first_commit_hash,
                last_commit, last_commit_hash,
                commit_count, query_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_name) DO UPDATE SET
                repo_url = EXCLUDED.repo_url,
                first_commit = EXCLUDED.first_commit,
                first_commit_hash = EXCLUDED.first_commit_hash,
                last_commit = EXCLUDED.last_commit,
                last_commit_hash = EXCLUDED.last_commit_hash,
                commit_count = EXCLUDED.commit_count,
                query_ts = EXCLUDED.query_ts
        """, [
            repo_name,
            repo_url,
            first_commit.date,
            first_commit.hash,
            last_commit.date,
            last_commit.hash,
            len(commits),
            datetime.now().isoformat()
        ])