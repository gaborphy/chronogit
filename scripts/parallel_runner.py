# scripts/parallel_runner.py

import os
import argparse
import concurrent.futures
from urllib.parse import urlparse
from chronogit.utils import clone_repo_if_needed, extract_repo_name
from chronogit.git_parser import parse_repo
from chronogit.db import get_existing_hashes, write_parquet_files, store_repo_status

MAX_WORKERS = min(8, os.cpu_count() or 4)

REPOS = [
    "https://github.com/bieniu/accuweather",
    "https://github.com/dotnet/machinelearning",
    # add more repos here
]

def process_repo(url: str, output_dir: str = "tmp_parquet"):
    try:
        repo_name = extract_repo_name(url)
        repo_path = clone_repo_if_needed(url, "repos")

        print(f"📥 Loading known hashes from DB for: {repo_name}")
        known_hashes = get_existing_hashes(repo_name)

        print(f"🔎 Parsing repo {repo_name} (skipping {len(known_hashes)} known hashes)...")
        commits = parse_repo(repo_path, repo_name, skip_hashes=known_hashes)

        print(f"💾 Writing {len(commits)} commits to {output_dir}/{repo_name}")
        write_parquet_files(commits, output_dir)

        print(f"📊 Storing repo status for {repo_name} in DB...")
        store_repo_status(repo_name, url, commits)

        print(f"✅ Done with {repo_name}")
    except Exception as e:
        print(f"[❌] Failed on {url}: {e}")


def run_parallel(urls: list[str], output_dir: str = "tmp_parquet"):
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_repo, url, output_dir) for url in urls]
        for f in concurrent.futures.as_completed(futures):
            f.result()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", help="GitHub repo URLs to parse")
    args = parser.parse_args()

    run_parallel(args.urls)


