"""Governed worktree creation entry point (dry-run default)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.worktrees import codes
from tools.worktrees.policy import FsProbe, default_fs_probe, validate_new_worktree_path
from tools.worktrees.resolve import build_worktree_path, resolve_worktree_root


@dataclass(frozen=True)
class CreatePlan:
    status: str
    path: str
    repository: str
    worktree_name: str
    ref: str
    branch: str | None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    root: str = ""
    dry_run: bool = True


@dataclass(frozen=True)
class CreateResult:
    status: str
    path: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    dry_run: bool = True
    git_stdout: str = ""
    git_stderr: str = ""


def plan_worktree_create(
    *,
    repository: str,
    worktree_name: str,
    ref: str = "origin/main",
    branch: str | None = None,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
    fs: FsProbe | None = None,
    path_exists: Callable[[Path], bool] | None = None,
) -> CreatePlan:
    """Resolve root, build path, and fail-closed validate (no git mutation)."""
    plat = platform or sys.platform
    probe = fs or default_fs_probe()
    exists_fn = path_exists or (lambda p: p.exists())

    resolved = resolve_worktree_root(env=env, platform=plat)
    if resolved.root is None:
        return CreatePlan(
            status="FAIL",
            path="",
            repository=repository,
            worktree_name=worktree_name,
            ref=ref,
            branch=branch,
            reason_codes=resolved.reason_codes
            or (
                codes.WORKTREE_ROOT_UNAVAILABLE,
                codes.HOLD_WORKTREE_ROOT_UNAVAILABLE,
            ),
            root="",
        )

    try:
        target = build_worktree_path(resolved.root, repository, worktree_name)
    except ValueError:
        return CreatePlan(
            status="FAIL",
            path="",
            repository=repository,
            worktree_name=worktree_name,
            ref=ref,
            branch=branch,
            reason_codes=(codes.WORKTREE_NAME_INVALID,),
            root=str(resolved.root),
        )

    validation = validate_new_worktree_path(
        target,
        root=resolved.root,
        platform=plat,
        fs=probe,
        env=dict(env) if env is not None else None,
    )
    if validation.status == "FAIL":
        return CreatePlan(
            status="FAIL",
            path=str(target),
            repository=repository,
            worktree_name=worktree_name,
            ref=ref,
            branch=branch,
            reason_codes=validation.reason_codes,
            root=str(resolved.root),
        )
    if validation.status == "SKIP":
        # Non-Windows: still allow planning a path under an explicit root,
        # but do not enforce Y: drive letters.
        pass

    if exists_fn(Path(target)):
        return CreatePlan(
            status="FAIL",
            path=str(target),
            repository=repository,
            worktree_name=worktree_name,
            ref=ref,
            branch=branch,
            reason_codes=(codes.WORKTREE_PATH_COLLISION,),
            root=str(resolved.root),
        )

    return CreatePlan(
        status="PASS",
        path=str(target),
        repository=repository,
        worktree_name=worktree_name,
        ref=ref,
        branch=branch,
        reason_codes=(codes.WORKTREE_CREATE_PLANNED,),
        root=str(resolved.root),
    )


def create_worktree(
    plan: CreatePlan,
    *,
    dry_run: bool = True,
    git_runner: Callable[..., Any] | None = None,
    repo_dir: Path | str | None = None,
) -> CreateResult:
    """Execute or dry-run ``git worktree add`` for a validated plan."""
    if plan.status != "PASS":
        return CreateResult(
            status="FAIL",
            path=plan.path,
            reason_codes=plan.reason_codes,
            dry_run=dry_run,
        )

    if dry_run:
        return CreateResult(
            status="PASS",
            path=plan.path,
            reason_codes=(codes.WORKTREE_CREATE_PLANNED,),
            dry_run=True,
        )

    runner = git_runner or subprocess.run
    args = ["git", "worktree", "add"]
    if plan.branch:
        args.extend(["-b", plan.branch])
    args.extend([plan.path, plan.ref])
    kwargs: dict[str, Any] = {"capture_output": True, "text": True, "check": False}
    if repo_dir is not None:
        kwargs["cwd"] = str(repo_dir)
    completed = runner(args, **kwargs)
    stdout = getattr(completed, "stdout", "") or ""
    stderr = getattr(completed, "stderr", "") or ""
    rc = getattr(completed, "returncode", 1)
    if rc != 0:
        return CreateResult(
            status="FAIL",
            path=plan.path,
            reason_codes=plan.reason_codes + ("GIT_WORKTREE_ADD_FAILED",),
            dry_run=False,
            git_stdout=stdout,
            git_stderr=stderr,
        )
    return CreateResult(
        status="PASS",
        path=plan.path,
        reason_codes=(codes.WORKTREE_CREATE_OK,),
        dry_run=False,
        git_stdout=stdout,
        git_stderr=stderr,
    )
