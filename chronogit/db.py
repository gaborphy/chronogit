import duckdb
import os

DB_PATH = os.getenv("CHRONOGIT_DB", "data/chronogit.duckdb")

def get_connection():
    """
    Get a connection to the DuckDB database.
    """
    conn = duckdb.connect(DB_PATH)
    return conn