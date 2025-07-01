import sys
from chronogit.utils import clone_repo_full
from chronogit.git_parser import parse_repo
from chronogit.db import store_commits, initialise_db
from urllib.parse import urlparse
from pathlib import Path

def get_repo_name_from_url(git_url: str) -> str:
    """
    Extract the repository name from a git URL.

    Args:
        git_url (str): The URL of the git repository.

    Returns:
        str: The name of the repository.
    """
    return Path(urlparse(git_url).path).stem


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python scripts/test_parse.py <GIT_REPO_URL>")
        sys.exit(1)

    url = sys.argv[1]
    repo_path = clone_repo_full(url)
    repo_name = get_repo_name_from_url(repo_path)

    # ✅ Initialize the database tables
    initialise_db()

    print(f"📁 Parsing commits in {repo_path}...")
    commits = parse_repo(repo_path, repo_name)

    print(f"💾 Parsed {len(commits)} commits. Storing in DB...")
    store_commits(commits)

    print("✅ Done.")