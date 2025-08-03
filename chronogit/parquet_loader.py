# chronogit/parquet_loader.py

import os
import duckdb
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("CHRONOGIT_DB", "data/chronogit.duckdb")

def load_parquet_to_duckdb(repo_name: str, base_dir="tmp_parquet"):
    conn = duckdb.connect(DB_PATH)

    repo_dir = os.path.join(base_dir, repo_name)
    if not os.path.exists(repo_dir):
        print(f"[⛔] Repo path not found: {repo_dir}")
        return

    for table in ["commits", "file_edits", "file_code_changes"]:
        parquet_file = os.path.join(repo_dir, f"{table}.parquet")
        if os.path.exists(parquet_file):
            print(f"[⬆️] Inserting {table} from {parquet_file}...")
            try:
                conn.execute(f"""
                    INSERT INTO {table}
                    SELECT * FROM read_parquet('{parquet_file}')
                """)
            except Exception as e:
                print(f"[❌] Failed to insert {table}: {e}")
        else:
            print(f"[⚠️] Missing {table}.parquet for {repo_name}")

    conn.close()

def load_all_parquet_to_duckdb(base_dir="tmp_parquet"):
    """
    Load all repos' .parquet files from base_dir into the DuckDB database.
    """
    print(f"[🔍] Scanning {base_dir} for .parquet files...")
    conn = duckdb.connect(DB_PATH)
    for repo_name in os.listdir(base_dir):
        repo_path = os.path.join(base_dir, repo_name)
        if os.path.isdir(repo_path):
            print(f"\n📦 Loading repo: {repo_name}")
            load_parquet_to_duckdb(repo_name, base_dir=base_dir)
    conn.close()
    print("\n✅ All parquet files loaded.")