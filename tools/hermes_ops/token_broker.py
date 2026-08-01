"""Short-lived GitHub App installation token broker for Hermes (#4289).

Reuses the App credential resolution / JWT minting from ``ci.publisher.app_auth``
(lineage #4170 / #4195). Does **not** publish ``cdb-local-ci`` and never logs tokens.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from ci.publisher.app_auth import (
    AuthenticationError,
    GitHubApiError,
    _extract_installation_token,
    _mint_transport,
    load_private_key_pem,
    mint_app_jwt,
    resolve_app_id_from_env,
    resolve_installation_id_from_env,
)
from ci.publisher.github_client import (
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_API,
    GitHubResponse,
)
from ci.publisher.redaction import redact_mapping, redact_text
from tools.hermes_ops.policy import (
    FORBIDDEN_GITHUB_ACTIONS,
    assert_action_allowed,
    get_profile_policy,
)

Transport = Callable[[str, str, dict[str, str], bytes | None, float], GitHubResponse]


@dataclass(frozen=True)
class MintResult:
    """Non-secret mint metadata. The token itself is returned separately and must
    stay in memory / caller-controlled FD only."""

    profile: str
    repositories: tuple[str, ...]
    permissions: dict[str, str]
    expires_hint: str = "installation_token_short_lived"


def _repo_names_only(repositories: list[str]) -> list[str]:
    names: list[str] = []
    for item in repositories:
        text = str(item).strip()
        if not text:
            continue
        if "/" in text:
            text = text.split("/", 1)[1]
        names.append(text)
    return names


def build_mint_body(profile: str) -> dict[str, Any]:
    policy = get_profile_policy(profile)
    if not policy.get("github_write"):
        raise AuthenticationError(
            f"profile {profile} is not allowed to mint GitHub write tokens"
        )
    permissions = dict(policy.get("token_permissions") or {})
    if not permissions:
        raise AuthenticationError(f"profile {profile} has empty token_permissions")
    # Hard deny: Hermes must never receive checks:write (cdb-local-ci publish).
    if permissions.get("checks") == "write":
        raise AuthenticationError("checks:write is forbidden for Hermes profiles")
    repositories = list(policy.get("allowed_repositories") or [])
    if not repositories:
        raise AuthenticationError(f"profile {profile} has no allowed_repositories")
    return {
        "repositories": _repo_names_only(repositories),
        "permissions": permissions,
    }


def request_scoped_installation_token(
    *,
    app_jwt: str,
    installation_id: int,
    body: dict[str, Any],
    transport: Transport | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    if not app_jwt.strip():
        raise AuthenticationError("Empty GitHub App JWT")
    url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {app_jwt}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cdb-hermes-token-broker",
        "Content-Type": "application/json",
    }
    payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
    runner = transport or _mint_transport
    try:
        response = runner("POST", url, headers, payload, timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        raise GitHubApiError(
            f"Scoped installation token request failed: {type(exc).__name__}"
        ) from exc
    if response.status_code in {401, 403}:
        raise AuthenticationError(
            f"GitHub App JWT rejected for scoped mint (HTTP {response.status_code})"
        )
    if response.status_code >= 400:
        raise GitHubApiError(
            f"Scoped installation token mint failed HTTP {response.status_code}: "
            f"{redact_mapping(response.body)}"
        )
    return _extract_installation_token(response.body)


def mint_profile_token(
    profile: str,
    *,
    transport: Transport | None = None,
    now: int | None = None,
    dry_run: bool = False,
) -> tuple[str | None, MintResult]:
    """Mint a scoped installation token for a Hermes profile.

    Returns ``(token_or_none, metadata)``. In ``dry_run`` mode, validates policy
    and returns ``(None, metadata)`` without contacting GitHub or reading PEM
    unless credentials are already configured and caller opts into live mint.
    """
    verdict = assert_action_allowed(profile, "github_write_branch_pr")
    if not verdict.ok:
        raise AuthenticationError(verdict.reason)
    for action in FORBIDDEN_GITHUB_ACTIONS:
        denied = assert_action_allowed(profile, action)
        if denied.ok:
            raise AuthenticationError(
                f"policy misconfigured: forbidden action {action} marked allowed"
            )
    body = build_mint_body(profile)
    meta = MintResult(
        profile=profile,
        repositories=tuple(body["repositories"]),
        permissions=dict(body["permissions"]),
    )
    if dry_run:
        return None, meta
    app_id = resolve_app_id_from_env()
    installation_id = resolve_installation_id_from_env()
    pem = load_private_key_pem()
    jwt = mint_app_jwt(app_id=app_id, private_key_pem=pem, now=now)
    token = request_scoped_installation_token(
        app_jwt=jwt,
        installation_id=installation_id,
        body=body,
        transport=transport,
    )
    return token, meta


def credential_paths_outside_workspace(
    workspace_roots: list[str] | None = None,
) -> list[str]:
    """Return errors if PEM path env points inside agent-readable workspaces."""
    roots = workspace_roots or [
        "/var/lib/hermes/profiles",
        r"D:\Dev\HermesWorkspace",
        "D:/Dev/HermesWorkspace",
    ]
    path = (os.environ.get("CDB_GH_APP_PRIVATE_KEY_PATH") or "").strip()
    errors: list[str] = []
    if not path:
        return errors
    normalized = path.replace("\\", "/").lower()
    for root in roots:
        root_n = root.replace("\\", "/").lower()
        if normalized.startswith(root_n):
            errors.append(
                "CDB_GH_APP_PRIVATE_KEY_PATH must not live under agent workspace: "
                f"{redact_text(path)}"
            )
    return errors


# cdb-local-ci App (app_id=4410232) is specialized for Check Runs only.
# Hermes engineering write must NOT silently reuse it without compatible perms.
CDB_LOCAL_CI_APP_ID = 4410232
REQUIRED_HERMES_WRITE_PERMS = ("contents", "pull_requests", "issues")
FORBIDDEN_HERMES_PERMS = ("checks",)


def assert_app_compatible_for_hermes_write(
    *,
    app_id: int | None = None,
    installation_permissions: dict[str, str] | None = None,
) -> None:
    """Fail closed when the resolved App cannot mint Hermes write tokens.

    Callers that have live installation permission JSON should pass it.
    Without a permission map, App 4410232 is rejected by known specialization.
    """
    resolved = app_id
    if resolved is None:
        raw = (os.environ.get("CDB_GH_APP_ID") or os.environ.get("APP_ID") or "").strip()
        if raw.isdigit():
            resolved = int(raw)
    if resolved == CDB_LOCAL_CI_APP_ID and installation_permissions is None:
        raise AuthenticationError(
            "App 4410232 (cdb-local-ci) is not reusable for Hermes GitHub write; "
            "live perms are checks:write+metadata:read only. "
            "Provide a dedicated engineering App or pass verified "
            "installation_permissions proving contents/pull_requests/issues write "
            "without checks:write. HOLD_SCOPE_BLOCKER."
        )
    if installation_permissions is None:
        return
    for key in REQUIRED_HERMES_WRITE_PERMS:
        if installation_permissions.get(key) != "write":
            raise AuthenticationError(
                f"Hermes write App missing required permission {key}:write "
                "(HOLD_SCOPE_BLOCKER — do not expand cdb-local-ci App)"
            )
    for key in FORBIDDEN_HERMES_PERMS:
        if installation_permissions.get(key) == "write":
            raise AuthenticationError(
                f"Hermes write App must not have {key}:write "
                "(separation from cdb-local-ci publish)"
            )


def metadata_only(profile: str) -> dict[str, Any]:
    """Safe JSON-able mint preview (no token)."""
    _, meta = mint_profile_token(profile, dry_run=True)
    return {
        "profile": meta.profile,
        "repositories": list(meta.repositories),
        "permissions": meta.permissions,
        "expires_hint": meta.expires_hint,
        "forbidden_actions": sorted(FORBIDDEN_GITHUB_ACTIONS),
        "auth_lineage_reference_only": ["4170", "4195"],
        "reuse_cdb_local_ci_app": False,
        "required_app_permissions": {
            "contents": "write",
            "pull_requests": "write",
            "issues": "write",
            "metadata": "read",
        },
        "forbidden_app_permissions": {"checks": "write"},
    }
