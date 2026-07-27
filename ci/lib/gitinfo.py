"""Git metadata for commit-bound local CI evidence."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitInfo:
    commit_sha: str
    branch: str
    dirty_worktree: bool
    remote_url: str
    repo_name: str


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout.strip()


def collect_git_info(repo_root: Path) -> GitInfo:
    commit_sha = _run_git(repo_root, "rev-parse", "HEAD")
    branch = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    # Tracked dirty only (-uno): untracked local noise must not invalidate
    # commit-SHA-bound evidence of an otherwise clean HEAD tree.
    porcelain = _run_git(repo_root, "status", "--porcelain", "-uno")
    dirty = bool(porcelain.strip())
    remote_url = ""
    try:
        remote_url = _run_git(repo_root, "remote", "get-url", "origin")
    except RuntimeError:
        remote_url = ""
    repo_name = "Claire_de_Binare"
    if remote_url:
        cleaned = remote_url.rstrip("/").removesuffix(".git")
        repo_name = cleaned.split("/")[-1].split(":")[-1]
    return GitInfo(
        commit_sha=commit_sha,
        branch=branch,
        dirty_worktree=dirty,
        remote_url=remote_url,
        repo_name=repo_name,
    )
