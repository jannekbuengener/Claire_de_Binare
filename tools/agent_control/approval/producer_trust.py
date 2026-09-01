"""Fail-closed producer trust from GitHub comment provenance (#4505)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tools.agent_control.approval.canon_loader import (
    DEFAULT_BOOTSTRAP_GIT_REF,
    load_yaml_from_git,
)
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.paths import REPO_ROOT

DEFAULT_TRUST_POLICY_RELPATH = (
    "config/agent-control/policies/approval/acceptance_producer_trust.v1.yaml"
)
DEFAULT_TRUST_POLICY_GIT_REF = DEFAULT_BOOTSTRAP_GIT_REF


def load_producer_trust_policy(
    repo_root: Path | None = None,
    *,
    git_ref: str | None = None,
) -> dict[str, Any]:
    """Load trust policy from protected canon; never trust candidate-checkout edits."""
    root = repo_root or REPO_ROOT
    ref = git_ref or DEFAULT_TRUST_POLICY_GIT_REF
    path = root / DEFAULT_TRUST_POLICY_RELPATH

    def _from_worktree() -> dict[str, Any]:
        if not path.is_file():
            raise ApprovalError(
                "APPROVAL_TRUST_POLICY_MISSING", f"missing trust policy: {path}"
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ApprovalError(
                "APPROVAL_TRUST_POLICY_INVALID", "trust policy must be mapping"
            )
        return data

    if git_ref is None:
        try:
            return load_yaml_from_git(root, ref, DEFAULT_TRUST_POLICY_RELPATH)
        except ApprovalError:
            try:
                return load_yaml_from_git(root, "HEAD", DEFAULT_TRUST_POLICY_RELPATH)
            except ApprovalError:
                return _from_worktree()
    try:
        return load_yaml_from_git(root, ref, DEFAULT_TRUST_POLICY_RELPATH)
    except ApprovalError:
        if ref in {DEFAULT_TRUST_POLICY_GIT_REF, "HEAD"}:
            return _from_worktree()
        raise


def producer_actor_trusted(
    *,
    producer: str,
    comment: CommentRecord,
    trust_policy: dict[str, Any] | None = None,
    repo_root: Path | None = None,
    git_ref: str | None = None,
) -> tuple[bool, str]:
    """Return (trusted, detail). Never infer trust from envelope producer field."""
    policy = trust_policy or load_producer_trust_policy(repo_root, git_ref=git_ref)
    producers = (
        policy.get("producers") if isinstance(policy.get("producers"), dict) else {}
    )
    rules = (
        producers.get(producer) if isinstance(producers.get(producer), dict) else None
    )
    if rules is None:
        return False, f"producer {producer!r} not in trust policy"

    app_slug = comment.performed_via_github_app_slug
    app_slugs = rules.get("trusted_github_app_slugs") or []
    if isinstance(app_slugs, list) and app_slug and app_slug in app_slugs:
        return True, f"github_app_slug={app_slug}"

    login = comment.author_login
    logins = rules.get("trusted_author_logins") or []
    allowed_types = rules.get("allowed_author_types") or []
    if (
        isinstance(logins, list)
        and login
        and login in logins
        and (not allowed_types or comment.author_type in allowed_types)
    ):
        return True, f"author_login={login}"

    require_app = bool(rules.get("require_performed_via_github_app"))
    if require_app and not app_slug:
        return False, "require_performed_via_github_app but comment has no app identity"

    detail = (
        f"untrusted actor login={login!r} type={comment.author_type!r} "
        f"app_slug={app_slug!r}"
    )
    return False, detail
