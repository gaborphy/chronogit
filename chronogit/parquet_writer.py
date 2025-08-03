# chronogit/parquet_writer.py
import pandas as pd
import os
from datetime import datetime
from chronogit.git_parser import CommitRecord

def write_to_parquet(commits: list[CommitRecord], repo_name: str, outdir="tmp_parquet"):
    timestamp = datetime.now().isoformat()
    base_path = os.path.join(outdir, repo_name)
    os.makedirs(base_path, exist_ok=True)

    # Flatten commits
    commit_rows = []
    edit_rows = []
    code_change_rows = []

    for c in commits:
        commit_rows.append({
            "commit_hash": c.hash,
            "repo_name": c.repo_name,
            "author": c.author,
            "author_email": c.author_email,
            "date": c.date,
            "message": c.msg,
            "query_time": timestamp,
        })
        for f in c.files:
            edit_rows.append({
                "commit_hash": c.hash,
                "repo_name": c.repo_name,
                "filename": f.filename,
                "added_lines": f.added_lines,
                "deleted_lines": f.deleted_lines,
                "change_type": f.change_type,
            })
            code_change_rows.append({
                "commit_hash": c.hash,
                "repo_name": c.repo_name,
                "filename": f.filename,
                "diff": f.diff,
                "diff_added_lines": str(f.diff_added),
                "diff_deleted_lines": str(f.diff_deleted),
                "source_code_before": f.source_before,
                "source_code_after": f.source_after,
            })

    # Save to parquet
    pd.DataFrame(commit_rows).to_parquet(f"{base_path}/commits.parquet", index=False)
    pd.DataFrame(edit_rows).to_parquet(f"{base_path}/file_edits.parquet", index=False)
    pd.DataFrame(code_change_rows).to_parquet(f"{base_path}/file_code_changes.parquet", index=False)
