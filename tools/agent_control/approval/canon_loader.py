"""Load governance canon from git refs (fail-closed bootstrap for #4505)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.paths import REPO_ROOT

BOOTSTRAP_RELPATH = (
    "config/agent-control/policies/approval/acceptance_publisher_bootstrap.v1.yaml"
)
DEFAULT_SCHEMA_GIT_REF = "origin/main"
DEFAULT_BOOTSTRAP_GIT_REF = "origin/main"


def git_show_text(repo_root: Path, git_ref: str, relpath: str) -> str:
    """Read file content at ``git_ref:relpath``; fail closed when missing."""
    result = subprocess.run(
        ["git", "show", f"{git_ref}:{relpath}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ApprovalError(
            "APPROVAL_CANON_REF_MISSING",
            f"cannot read {git_ref}:{relpath}: {detail}",
        )
    return result.stdout


def load_yaml_from_git(repo_root: Path, git_ref: str, relpath: str) -> dict[str, Any]:
    data = yaml.safe_load(git_show_text(repo_root, git_ref, relpath))
    if not isinstance(data, dict):
        raise ApprovalError(
            "APPROVAL_CANON_INVALID",
            f"{git_ref}:{relpath} must be a mapping",
        )
    return data


def load_json_from_git(repo_root: Path, git_ref: str, relpath: str) -> dict[str, Any]:
    data = json.loads(git_show_text(repo_root, git_ref, relpath))
    if not isinstance(data, dict):
        raise ApprovalError(
            "APPROVAL_CANON_INVALID",
            f"{git_ref}:{relpath} must be a JSON object",
        )
    return data


def load_bootstrap_policy(
    repo_root: Path | None = None,
    *,
    git_ref: str | None = None,
) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    ref = git_ref or DEFAULT_BOOTSTRAP_GIT_REF

    def _from_worktree() -> dict[str, Any]:
        path = root / BOOTSTRAP_RELPATH
        if not path.is_file():
            raise ApprovalError(
                "APPROVAL_CANON_REF_MISSING",
                f"bootstrap missing at {BOOTSTRAP_RELPATH}",
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ApprovalError("APPROVAL_CANON_INVALID", "bootstrap must be a mapping")
        return data

    if git_ref is None:
        try:
            return load_yaml_from_git(root, ref, BOOTSTRAP_RELPATH)
        except ApprovalError:
            try:
                return load_yaml_from_git(root, "HEAD", BOOTSTRAP_RELPATH)
            except ApprovalError:
                return _from_worktree()
    try:
        return load_yaml_from_git(root, ref, BOOTSTRAP_RELPATH)
    except ApprovalError:
        if ref in {DEFAULT_BOOTSTRAP_GIT_REF, "HEAD"}:
            return _from_worktree()
        raise


def load_acceptance_schema_from_canon(
    bootstrap: dict[str, Any],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    canon = bootstrap.get("canon") if isinstance(bootstrap.get("canon"), dict) else {}
    git_ref = str(canon.get("schema_git_ref") or DEFAULT_SCHEMA_GIT_REF)
    relpath = str(canon.get("schema_relpath") or "")
    if not relpath:
        raise ApprovalError(
            "APPROVAL_CANON_INVALID", "bootstrap canon.schema_relpath missing"
        )
    return load_json_from_git(root, git_ref, relpath)
