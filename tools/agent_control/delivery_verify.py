"""GitHub-backed delivery target verification for live Cursor pilots."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from tools.agent_control.errors import DispatchError

SHA40 = re.compile(r"^[a-f0-9]{40}$")
GhRunner = Callable[[list[str]], dict[str, Any]]


@dataclass(frozen=True)
class DeliveryVerification:
    ok: bool
    head_sha: str | None
    base_sha: str | None
    pr_number: int | None
    branch: str | None
    repo: str | None
    changed_files: list[str]
    code: str | None = None
    message: str | None = None


def _default_gh_runner(argv: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise DispatchError(
            "DELIVERY_GITHUB_QUERY_FAILED",
            (completed.stderr or completed.stdout or "gh failed")[:500],
        )
    return json.loads(completed.stdout)


def verify_github_delivery(
    *,
    expected_repo: str,
    pr_number: int | None = None,
    branch: str | None = None,
    expected_paths_prefix: list[str] | None = None,
    allow_empty: bool = False,
    runner: GhRunner | None = None,
) -> DeliveryVerification:
    """Verify PR/branch exists on expected repo and bind head/base SHAs.

    ``expected_repo`` is ``owner/name``. Never accepts a foreign repo.
    """
    run = runner or _default_gh_runner
    if not expected_repo or "/" not in expected_repo:
        return DeliveryVerification(
            ok=False,
            head_sha=None,
            base_sha=None,
            pr_number=pr_number,
            branch=branch,
            repo=expected_repo,
            changed_files=[],
            code="DELIVERY_REPO_INVALID",
            message="expected_repo must be owner/name",
        )

    if pr_number is None and not branch:
        return DeliveryVerification(
            ok=False,
            head_sha=None,
            base_sha=None,
            pr_number=None,
            branch=None,
            repo=expected_repo,
            changed_files=[],
            code="DELIVERY_TARGET_MISSING",
            message="pr_number or branch required",
        )

    if pr_number is not None:
        data = run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--repo",
                expected_repo,
                "--json",
                "number,state,headRefOid,baseRefOid,headRefName,files,url,headRepository",
            ]
        )
        head = data.get("headRefOid")
        base = data.get("baseRefOid")
        br = data.get("headRefName")
        files_raw = data.get("files") or []
        files = [
            f.get("path")
            for f in files_raw
            if isinstance(f, dict) and isinstance(f.get("path"), str)
        ]
        if not isinstance(head, str) or not SHA40.match(head):
            return DeliveryVerification(
                ok=False,
                head_sha=None,
                base_sha=base if isinstance(base, str) else None,
                pr_number=int(data.get("number") or pr_number),
                branch=br if isinstance(br, str) else branch,
                repo=expected_repo,
                changed_files=files,
                code="DELIVERY_HEAD_INVALID",
                message="PR head SHA missing or not 40-hex",
            )
        if not files and not allow_empty:
            return DeliveryVerification(
                ok=False,
                head_sha=head,
                base_sha=base if isinstance(base, str) else None,
                pr_number=int(data.get("number") or pr_number),
                branch=br if isinstance(br, str) else branch,
                repo=expected_repo,
                changed_files=[],
                code="DELIVERY_EMPTY",
                message="PR has no changed files",
            )
        if expected_paths_prefix:
            bad = [
                p
                for p in files
                if not any(
                    p == pref or p.startswith(pref.rstrip("*"))
                    for pref in expected_paths_prefix
                )
                and not any(_globish_match(p, pref) for pref in expected_paths_prefix)
            ]
            # Soft prefix: allow if every file starts with at least one allowlist root
            allow_roots = [p.rstrip("/*") for p in expected_paths_prefix]
            bad = [
                p
                for p in files
                if not any(p == r or p.startswith(r + "/") for r in allow_roots)
            ]
            if bad:
                return DeliveryVerification(
                    ok=False,
                    head_sha=head,
                    base_sha=base if isinstance(base, str) else None,
                    pr_number=int(data.get("number") or pr_number),
                    branch=br if isinstance(br, str) else branch,
                    repo=expected_repo,
                    changed_files=files,
                    code="DELIVERY_SCOPE_DRIFT",
                    message=f"files outside allowlist: {bad[:5]}",
                )
        return DeliveryVerification(
            ok=True,
            head_sha=head,
            base_sha=base if isinstance(base, str) else None,
            pr_number=int(data.get("number") or pr_number),
            branch=br if isinstance(br, str) else branch,
            repo=expected_repo,
            changed_files=files,
        )

    # Branch-only verification via gh api
    data = run(
        [
            "gh",
            "api",
            f"repos/{expected_repo}/branches/{branch}",
        ]
    )
    commit = (data.get("commit") or {}).get("sha")
    if not isinstance(commit, str) or not SHA40.match(commit):
        return DeliveryVerification(
            ok=False,
            head_sha=None,
            base_sha=None,
            pr_number=None,
            branch=branch,
            repo=expected_repo,
            changed_files=[],
            code="DELIVERY_HEAD_INVALID",
            message="branch tip SHA missing or not 40-hex",
        )
    return DeliveryVerification(
        ok=True,
        head_sha=commit,
        base_sha=None,
        pr_number=None,
        branch=branch,
        repo=expected_repo,
        changed_files=[],
    )


def _globish_match(path: str, pattern: str) -> bool:
    if pattern.endswith("/*"):
        root = pattern[:-2]
        return path == root or path.startswith(root + "/")
    return path == pattern


def normalize_cursor_git_branches(
    result_refs: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract branch/prUrl from Cursor result_refs without inventing commits."""
    refs = result_refs or {}
    claimed = refs.get("claimed_delivery")
    if isinstance(claimed, dict) and (
        claimed.get("branch") or claimed.get("pr_url") or claimed.get("repo_url")
    ):
        return {
            "branch": claimed.get("branch"),
            "pr_url": claimed.get("pr_url"),
            "repo_url": claimed.get("repo_url"),
        }
    git = refs.get("git") if isinstance(refs.get("git"), dict) else {}
    branches = git.get("branches") if isinstance(git.get("branches"), list) else []
    out: dict[str, Any] = {"branch": None, "pr_url": None, "repo_url": None}
    if not branches:
        return out
    first = branches[0]
    if not isinstance(first, dict):
        return out
    out["branch"] = first.get("branch")
    out["pr_url"] = first.get("prUrl") or first.get("pr_url")
    out["repo_url"] = first.get("repoUrl") or first.get("repo_url")
    return out


def claimed_delivery_from_git(git: dict[str, Any] | None) -> dict[str, Any]:
    """Cursor-claimed git snapshot only — never implies GitHub verification."""
    git = git if isinstance(git, dict) else {}
    branches = git.get("branches") if isinstance(git.get("branches"), list) else []
    out: dict[str, Any] = {
        "branch": None,
        "pr_url": None,
        "repo_url": None,
        "source": "run.git",
        "delivery_verified": False,
    }
    if not branches or not isinstance(branches[0], dict):
        return out
    first = branches[0]
    out["branch"] = first.get("branch")
    out["pr_url"] = first.get("prUrl") or first.get("pr_url")
    out["repo_url"] = first.get("repoUrl") or first.get("repo_url")
    return out


def truncate_run_result_text(value: Any, *, limit: int = 2000) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def pr_number_from_url(pr_url: str | None) -> int | None:
    if not pr_url or not isinstance(pr_url, str):
        return None
    m = re.search(r"/pull/(\d+)", pr_url)
    if not m:
        return None
    return int(m.group(1))
