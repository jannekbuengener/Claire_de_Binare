"""Git metadata for commit-bound local CI evidence."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

EXPECTED_REPOSITORY = "jannekbuengener/Claire_de_Binare"
_SSH_GITHUB_RE = re.compile(
    r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)
_HTTPS_GITHUB_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


@dataclass(frozen=True)
class GitInfo:
    commit_sha: str
    branch: str
    dirty_worktree: bool
    remote_url: str
    repo_name: str


def normalize_repository_slug(remote_or_name: str) -> str:
    """Normalize a remote URL or owner/name string to ``owner/repo``.

    Accepts HTTPS/SSH GitHub remotes and bare ``owner/repo`` or repo-name-only
    values (repo-name-only maps to the expected CDB owner).
    """
    value = (remote_or_name or "").strip()
    if not value:
        raise ValueError("Empty repository identifier")
    for pattern in (_SSH_GITHUB_RE, _HTTPS_GITHUB_RE):
        match = pattern.match(value)
        if match:
            repo = match.group("repo")
            return f"{match.group('owner')}/{repo}"
    cleaned = value.rstrip("/").removesuffix(".git")
    if "/" in cleaned:
        owner, repo = cleaned.rsplit("/", 1)
        if owner and repo:
            return f"{owner}/{repo}"
    # Bare repo name — bind to expected CDB owner for local evidence.
    if "/" not in cleaned and cleaned:
        return f"jannekbuengener/{cleaned}"
    raise ValueError(f"Cannot normalize repository identifier: {remote_or_name!r}")


def assert_expected_repository(remote_or_name: str) -> str:
    """Fail closed unless the repository slug is the CDB canonical repo."""
    slug = normalize_repository_slug(remote_or_name)
    # Case-insensitive repo name, exact owner.
    owner, repo = slug.split("/", 1)
    expected_owner, expected_repo = EXPECTED_REPOSITORY.split("/", 1)
    if owner != expected_owner or repo.lower() != expected_repo.lower():
        raise ValueError(
            f"Foreign repository rejected: {slug!r} (expected {EXPECTED_REPOSITORY})"
        )
    return f"{expected_owner}/{expected_repo}"


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
