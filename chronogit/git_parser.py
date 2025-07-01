# chronogit/git_parser.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class FileEdit:
    filename: str
    added_lines: int
    deleted_lines: int
    change_type: str  # 'add', 'delete', 'modify'
    diff: Optional[str] = None
    diff_added: Optional[list[tuple[int, str]]] = None
    diff_deleted: Optional[list[tuple[int, str]]] = None
    source_before: Optional[str] = None
    source_after: Optional[str] = None

@dataclass
class CommitRecord:
    hash: str
    repo_name: str
    author: str
    author_email: str
    date: datetime
    msg: str
    files: List[FileEdit]

from pydriller import Repository
from .git_parser import CommitRecord, FileEdit

def parse_repo(repo_path: str, repo_name: str) -> List[CommitRecord]:
    parsed_commits = []
    for commit in Repository(repo_path).traverse_commits():
        files = []
        for mod in commit.modified_files:
            files.append(FileEdit(
                filename=mod.new_path or mod.old_path or "UNKNOWN",
                added_lines=mod.added_lines,
                deleted_lines=mod.deleted_lines,
                change_type=mod.change_type.name,
                diff = mod.diff,
                diff_added= mod.diff_parsed.get("added", []),
                diff_deleted = mod.diff_parsed.get("deleted", []),
                source_before=safe_get_source_before(mod),
                source_after= safe_get_source(mod)
            ))

        parsed_commits.append(CommitRecord(
            hash=commit.hash,
            repo_name=repo_name,
            author=commit.author.name,
            author_email=commit.author.email,
            date=commit.committer_date,
            msg=commit.msg,
            files=files
        ))

    return parsed_commits

def safe_get_source(mod):
    try:
        return mod.source_code
    except Exception as e:
        print(f"[⚠️] Failed to get source for {mod.new_path or mod.old_path}: {e}")
        return None

def safe_get_source_before(mod):
    try:
        return mod.source_code_before
    except Exception:
        return None
