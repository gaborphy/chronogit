import os
import subprocess
from urllib.parse import urlparse
from pathlib import Path

def clone_repo_full(git_url: str, target_dir: str="repos") -> str:
    """
    Clone a git repository to a specified directory.

    Args:
        git_url (str): The URL of the git repository to clone.
        target_dir (str): The directory where the repository will be cloned.

    Returns:
        str: The path to the cloned repository.
    """
    repo_name = Path(urlparse(git_url).path).stem
    clone_path = os.path.join(target_dir, repo_name)

    if os.path.exists(clone_path):
        print(f"✅ Repo already exists at {clone_path}, skipping clone.")
        return clone_path

    os.makedirs(target_dir, exist_ok=True)

    print(f"🔄 Cloning {git_url} into {clone_path} ...")
    subprocess.run(["git", "clone", git_url, clone_path], check=True)
    print("✅ Clone complete.")
    return clone_path