"""Fail-closed producer trust from GitHub comment provenance (#4505)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.paths import REPO_ROOT

DEFAULT_TRUST_POLICY_RELPATH = (
    "config/agent-control/policies/approval/acceptance_producer_trust.v1.yaml"
)

_DEBUG_LOG = Path("debug-6088fb.log")


def _debug_log(*, hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # #region agent log
    try:
        import time

        payload = {
            "sessionId": "6088fb",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass
    # #endregion


def load_producer_trust_policy(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    path = root / DEFAULT_TRUST_POLICY_RELPATH
    if not path.is_file():
        raise ApprovalError("APPROVAL_TRUST_POLICY_MISSING", f"missing trust policy: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ApprovalError("APPROVAL_TRUST_POLICY_INVALID", "trust policy must be mapping")
    return data


def producer_actor_trusted(
    *,
    producer: str,
    comment: CommentRecord,
    trust_policy: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> tuple[bool, str]:
    """Return (trusted, detail). Never infer trust from envelope producer field."""
    policy = trust_policy or load_producer_trust_policy(repo_root)
    producers = policy.get("producers") if isinstance(policy.get("producers"), dict) else {}
    rules = producers.get(producer) if isinstance(producers.get(producer), dict) else None
    if rules is None:
        _debug_log(
            hypothesis_id="H1",
            location="producer_trust.py:producer_actor_trusted",
            message="unknown producer in trust policy",
            data={"producer": producer, "comment_id": comment.comment_id},
        )
        return False, f"producer {producer!r} not in trust policy"

    app_slug = comment.performed_via_github_app_slug
    app_slugs = rules.get("trusted_github_app_slugs") or []
    if isinstance(app_slugs, list) and app_slug and app_slug in app_slugs:
        _debug_log(
            hypothesis_id="H1",
            location="producer_trust.py:producer_actor_trusted",
            message="trusted via github app slug",
            data={"producer": producer, "app_slug": app_slug},
        )
        return True, f"github_app_slug={app_slug}"

    login = comment.author_login
    logins = rules.get("trusted_author_logins") or []
    allowed_types = rules.get("allowed_author_types") or []
    if (
        isinstance(logins, list)
        and login
        and login in logins
        and (
            not allowed_types
            or comment.author_type in allowed_types
        )
    ):
        _debug_log(
            hypothesis_id="H1",
            location="producer_trust.py:producer_actor_trusted",
            message="trusted via author login",
            data={"producer": producer, "login": login},
        )
        return True, f"author_login={login}"

    require_app = bool(rules.get("require_performed_via_github_app"))
    if require_app and not app_slug:
        detail = "require_performed_via_github_app but comment has no app identity"
        _debug_log(
            hypothesis_id="H1",
            location="producer_trust.py:producer_actor_trusted",
            message="fail closed: no app identity",
            data={"producer": producer, "login": login, "author_type": comment.author_type},
        )
        return False, detail

    detail = (
        f"untrusted actor login={login!r} type={comment.author_type!r} "
        f"app_slug={app_slug!r}"
    )
    _debug_log(
        hypothesis_id="H1",
        location="producer_trust.py:producer_actor_trusted",
        message="fail closed: actor not allowlisted",
        data={"producer": producer, "login": login, "app_slug": app_slug},
    )
    return False, detail
