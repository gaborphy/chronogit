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

def extract_repo_name(git_url: str) -> str:
    """
    Extract the repository name from a git URL.

    Args:
        git_url (str): The URL of the git repository.

    Returns:
        str: The name of the repository.
    """
    return Path(urlparse(git_url).path).stem

def clone_repo_if_needed(url: str, base_dir: str = "repos") -> str:
    """
    Clone a repo if it doesn't exist locally. Return the local path.
    """
    repo_name = extract_repo_name(url)
    repo_path = os.path.join(base_dir, repo_name)

    if os.path.exists(repo_path):
        print(f"✅ Repo already exists at {repo_path}, skipping clone.")
    else:
        print(f"🔁 Cloning {url} into {repo_path}...")
        os.makedirs(base_dir, exist_ok=True)
        subprocess.run(["git", "clone", url, repo_path], check=True)

    return repo_path