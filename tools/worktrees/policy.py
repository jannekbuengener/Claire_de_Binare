"""Fail-closed Windows worktree path policy."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from tools.worktrees import codes
from tools.worktrees.resolve import (
    is_path_under_root,
    is_windows_drive_policy_applicable,
    resolve_worktree_root,
    windows_drive_letter,
)


@dataclass(frozen=True)
class FsProbe:
    """Injectable filesystem probes for unit tests."""

    exists: Callable[[Path], bool] = Path.exists
    is_dir: Callable[[Path], bool] = Path.is_dir

    def is_writable(self, path: Path) -> bool:
        if not self.exists(path) or not self.is_dir(path):
            return False
        probe = path / ".cdb_worktree_write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False


@dataclass(frozen=True)
class ValidationResult:
    status: str  # PASS | FAIL | SKIP
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    path: str = ""
    root: str = ""
    platform: str = ""
    purpose: str = ""


def default_fs_probe() -> FsProbe:
    return FsProbe()


def validate_main_checkout_path(
    path: Path | str,
    *,
    platform: str | None = None,
) -> ValidationResult:
    """Main checkout may remain on D:; it is not a new-worktree create path."""
    plat = platform or sys.platform
    return ValidationResult(
        status="PASS",
        reason_codes=(codes.MAIN_CHECKOUT_ALLOWED,),
        path=str(path),
        platform=plat,
        purpose="main_checkout",
    )


def validate_new_worktree_path(
    path: Path | str,
    *,
    root: Path | None = None,
    platform: str | None = None,
    fs: FsProbe | None = None,
    env: dict[str, str] | None = None,
    purpose: Literal["create"] = "create",
) -> ValidationResult:
    """Validate a candidate path for creating a new additional worktree."""
    plat = platform or sys.platform
    target = Path(path)
    probe = fs or default_fs_probe()

    if not is_windows_drive_policy_applicable(plat):
        return ValidationResult(
            status="SKIP",
            reason_codes=(codes.WORKTREE_POLICY_NOT_APPLICABLE,),
            path=str(target),
            platform=plat,
            purpose=purpose,
        )

    resolved = resolve_worktree_root(env=env, platform=plat)
    effective_root = root if root is not None else resolved.root
    if effective_root is None:
        return ValidationResult(
            status="FAIL",
            reason_codes=(
                codes.WORKTREE_ROOT_UNAVAILABLE,
                codes.HOLD_WORKTREE_ROOT_UNAVAILABLE,
            ),
            path=str(target),
            platform=plat,
            purpose=purpose,
        )

    root_path = Path(effective_root)
    if not probe.exists(root_path) or not probe.is_dir(root_path):
        return ValidationResult(
            status="FAIL",
            reason_codes=(
                codes.WORKTREE_ROOT_UNAVAILABLE,
                codes.HOLD_WORKTREE_ROOT_UNAVAILABLE,
            ),
            path=str(target),
            root=str(root_path),
            platform=plat,
            purpose=purpose,
        )

    if not probe.is_writable(root_path):
        return ValidationResult(
            status="FAIL",
            reason_codes=(
                codes.WORKTREE_ROOT_NOT_WRITABLE,
                codes.HOLD_WORKTREE_ROOT_NOT_WRITABLE,
            ),
            path=str(target),
            root=str(root_path),
            platform=plat,
            purpose=purpose,
        )

    drive = windows_drive_letter(target)
    if drive == "C":
        return ValidationResult(
            status="FAIL",
            reason_codes=(codes.WORKTREE_ON_C_DRIVE,),
            path=str(target),
            root=str(root_path),
            platform=plat,
            purpose=purpose,
        )
    if drive == "D":
        return ValidationResult(
            status="FAIL",
            reason_codes=(codes.WORKTREE_ON_D_DRIVE,),
            path=str(target),
            root=str(root_path),
            platform=plat,
            purpose=purpose,
        )

    if not is_path_under_root(target, root_path):
        return ValidationResult(
            status="FAIL",
            reason_codes=(
                codes.WORKTREE_OUTSIDE_CANONICAL_ROOT,
                codes.HOLD_WORKTREE_PATH_OUTSIDE_ALLOWED_ROOT,
            ),
            path=str(target),
            root=str(root_path),
            platform=plat,
            purpose=purpose,
        )

    return ValidationResult(
        status="PASS",
        reason_codes=(codes.WORKTREE_PATH_ALLOWED,),
        path=str(target),
        root=str(root_path),
        platform=plat,
        purpose=purpose,
    )


def path_exists(path: Path) -> bool:
    return os.path.exists(path)
