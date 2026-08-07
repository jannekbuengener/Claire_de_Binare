"""Governed local Windows worktree root contract (Y:\\Worktrees).

Public surface for resolve / policy / create / reconcile.
"""

from __future__ import annotations

from tools.worktrees.codes import (
    DEFAULT_WINDOWS_ROOT,
    ENV_WORKTREE_ROOT,
    LEGACY_CLASSES,
)
from tools.worktrees.create import (
    CreatePlan,
    CreateResult,
    create_worktree,
    plan_worktree_create,
)
from tools.worktrees.policy import (
    FsProbe,
    ValidationResult,
    validate_main_checkout_path,
    validate_new_worktree_path,
)
from tools.worktrees.reconcile import (
    LegacyWorktreeFacts,
    ReconcileResult,
    classify_legacy_worktree,
    inventory_from_porcelain,
)
from tools.worktrees.resolve import (
    ResolveResult,
    build_worktree_path,
    is_windows_drive_policy_applicable,
    resolve_worktree_root,
)

__all__ = [
    "DEFAULT_WINDOWS_ROOT",
    "ENV_WORKTREE_ROOT",
    "LEGACY_CLASSES",
    "CreatePlan",
    "CreateResult",
    "FsProbe",
    "LegacyWorktreeFacts",
    "ReconcileResult",
    "ResolveResult",
    "ValidationResult",
    "build_worktree_path",
    "classify_legacy_worktree",
    "create_worktree",
    "inventory_from_porcelain",
    "is_windows_drive_policy_applicable",
    "plan_worktree_create",
    "resolve_worktree_root",
    "validate_main_checkout_path",
    "validate_new_worktree_path",
]
