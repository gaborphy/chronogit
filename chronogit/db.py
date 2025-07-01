import duckdb
import os
from dotenv import load_dotenv

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