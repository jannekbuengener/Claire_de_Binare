"""Short-lived GitHub App installation token broker for Hermes (#4289).

Reuses JWT minting helpers from ``ci.publisher.app_auth`` (lineage #4170 / #4195)
as library code only. Hermes credentials use ``HERMES_GH_APP_*`` env vars —
never the ``cdb-local-ci`` App ``4410232`` via ``CDB_GH_APP_*``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ci.publisher.app_auth import (
    AuthenticationError,
    GitHubApiError,
    _extract_installation_token,
    _mint_transport,
    mint_app_jwt,
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
from tools.hermes_ops.profile_users import (
    PEM_HOST_PATH,
    TOKEN_RUNTIME_DIR,
    assert_token_consumer_allowed,
    linux_user_for_profile,
    token_file_path,
)

Transport = Callable[[str, str, dict[str, str], bytes | None, float], GitHubResponse]

# Hermes-only credential env (must not collide with cdb-local-ci publisher).
HERMES_APP_ID_ENV = "HERMES_GH_APP_ID"
HERMES_INSTALLATION_ID_ENV = "HERMES_GH_APP_INSTALLATION_ID"
HERMES_PRIVATE_KEY_PATH_ENV = "HERMES_GH_APP_PRIVATE_KEY_PATH"

CDB_LOCAL_CI_APP_ID = 4410232
REQUIRED_HERMES_WRITE_PERMS = ("contents", "pull_requests", "issues")
FORBIDDEN_HERMES_PERMS = ("checks", "statuses", "administration", "secrets", "actions")

ALLOWED_TOKEN_FILE_PREFIXES = (
    TOKEN_RUNTIME_DIR,
    "/run/hermes/cdb-engineer/",
)


@dataclass(frozen=True)
class MintResult:
    """Non-secret mint metadata. The token itself stays out of logs."""

    profile: str
    repositories: tuple[str, ...]
    permissions: dict[str, str]
    expires_hint: str = "installation_token_short_lived"


def _env_first(*names: str) -> str:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def resolve_hermes_app_id() -> int:
    raw = _env_first(HERMES_APP_ID_ENV)
    if not raw:
        raise AuthenticationError(f"Missing {HERMES_APP_ID_ENV}")
    try:
        app_id = int(raw)
    except ValueError as exc:
        raise AuthenticationError(f"{HERMES_APP_ID_ENV} must be an integer") from exc
    if app_id == CDB_LOCAL_CI_APP_ID:
        raise AuthenticationError(
            "App 4410232 (cdb-local-ci) is forbidden for Hermes token mint"
        )
    return app_id


def resolve_hermes_installation_id() -> int:
    raw = _env_first(HERMES_INSTALLATION_ID_ENV)
    if not raw:
        raise AuthenticationError(f"Missing {HERMES_INSTALLATION_ID_ENV}")
    try:
        value = int(raw)
    except ValueError as exc:
        raise AuthenticationError(
            f"{HERMES_INSTALLATION_ID_ENV} must be an integer"
        ) from exc
    if value <= 0:
        raise AuthenticationError(f"{HERMES_INSTALLATION_ID_ENV} must be positive")
    return value


def load_hermes_private_key_pem() -> bytes:
    path = _env_first(HERMES_PRIVATE_KEY_PATH_ENV) or PEM_HOST_PATH
    normalized = path.replace("\\", "/")
    for root in (
        "/var/lib/hermes/profiles",
        r"D:\Dev\HermesWorkspace",
        "D:/Dev/HermesWorkspace",
    ):
        if normalized.lower().startswith(root.replace("\\", "/").lower()):
            raise AuthenticationError(
                f"{HERMES_PRIVATE_KEY_PATH_ENV} must not live under agent workspace"
            )
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise AuthenticationError(
            f"Cannot read Hermes App PEM ({HERMES_PRIVATE_KEY_PATH_ENV}): "
            f"{type(exc).__name__}"
        ) from exc
    if b"BEGIN" not in data:
        raise AuthenticationError("Hermes App private key is not a PEM block")
    return data


def assert_token_file_path_allowed(path: str) -> None:
    """Live tokens may only land under the isolated /run/hermes/cdb-engineer tree."""
    text = str(path).strip().replace("\\", "/")
    if not text:
        raise AuthenticationError("token file path is empty")
    if ".." in text.split("/"):
        raise AuthenticationError("token file path must not contain ..")
    allowed = False
    for prefix in ALLOWED_TOKEN_FILE_PREFIXES:
        p = prefix.rstrip("/")
        if text == p or text.startswith(p + "/"):
            allowed = True
            break
    if not allowed:
        raise AuthenticationError(
            "token file must be under /run/hermes/cdb-engineer "
            "(HOLD_TOKEN_DELIVERY_ISOLATION)"
        )
    if "/var/lib/hermes/profiles" in text:
        raise AuthenticationError(
            "token file under profile home is forbidden "
            "(HOLD_TOKEN_DELIVERY_ISOLATION)"
        )


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
    # OS delivery identity must be the engineer user only.
    assert_token_consumer_allowed(linux_user_for_profile(profile))
    permissions = dict(policy.get("token_permissions") or {})
    if not permissions:
        raise AuthenticationError(f"profile {profile} has empty token_permissions")
    for key in FORBIDDEN_HERMES_PERMS:
        if permissions.get(key) == "write":
            raise AuthenticationError(f"{key}:write is forbidden for Hermes profiles")
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
    """Mint a scoped installation token for a Hermes profile."""
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
    assert_app_compatible_for_hermes_write()
    app_id = resolve_hermes_app_id()
    installation_id = resolve_hermes_installation_id()
    pem = load_hermes_private_key_pem()
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
    """Return errors if Hermes PEM path points inside agent-readable workspaces."""
    roots = workspace_roots or [
        "/var/lib/hermes/profiles",
        r"D:\Dev\HermesWorkspace",
        "D:/Dev/HermesWorkspace",
    ]
    # If caller passed a single path list used as roots incorrectly, detect env.
    path = (os.environ.get(HERMES_PRIVATE_KEY_PATH_ENV) or "").strip()
    if not path:
        path = (os.environ.get("CDB_GH_APP_PRIVATE_KEY_PATH") or "").strip()
    errors: list[str] = []
    if not path:
        return errors
    # If the "roots" argument is actually a list of candidate paths (len==1 file),
    # treat as explicit path check when it looks like a file path.
    check_paths = [path]
    if (
        workspace_roots
        and len(workspace_roots) == 1
        and workspace_roots[0].endswith((".pem", ".key"))
    ):
        check_paths = list(workspace_roots)
        roots = [
            "/var/lib/hermes/profiles",
            r"D:\Dev\HermesWorkspace",
            "D:/Dev/HermesWorkspace",
        ]
    for candidate in check_paths:
        normalized = candidate.replace("\\", "/").lower()
        for root in roots:
            root_n = root.replace("\\", "/").lower()
            if normalized.startswith(root_n):
                errors.append(
                    "private key path must not live under agent workspace: "
                    f"{redact_text(candidate)}"
                )
    return errors


def assert_app_compatible_for_hermes_write(
    *,
    app_id: int | None = None,
    installation_permissions: dict[str, str] | None = None,
) -> None:
    """Fail closed when the resolved App cannot mint Hermes write tokens."""
    resolved = app_id
    if resolved is None:
        raw = _env_first(HERMES_APP_ID_ENV)
        if not raw:
            # Also reject accidental use of publisher env pointing at 4410232.
            legacy = (
                os.environ.get("CDB_GH_APP_ID") or os.environ.get("APP_ID") or ""
            ).strip()
            if legacy.isdigit() and int(legacy) == CDB_LOCAL_CI_APP_ID:
                raise AuthenticationError(
                    "App 4410232 (cdb-local-ci) is not reusable for Hermes GitHub "
                    "write; set HERMES_GH_APP_ID to a dedicated engineering App. "
                    "HOLD_SCOPE_BLOCKER."
                )
            if legacy.isdigit():
                resolved = int(legacy)
        elif raw.isdigit():
            resolved = int(raw)
    if resolved == CDB_LOCAL_CI_APP_ID:
        raise AuthenticationError(
            "App 4410232 (cdb-local-ci) is not reusable for Hermes GitHub write; "
            "live perms are checks:write+metadata:read only. "
            "Provide a dedicated engineering App. HOLD_SCOPE_BLOCKER."
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
                "(separation from cdb-local-ci / admin surfaces)"
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
        "linux_user": linux_user_for_profile(profile),
        "token_file": token_file_path(),
        "required_app_permissions": {
            "contents": "write",
            "pull_requests": "write",
            "issues": "write",
            "metadata": "read",
        },
        "forbidden_app_permissions": {
            "checks": "write",
            "statuses": "write",
            "administration": "write",
            "secrets": "write",
            "actions": "write",
        },
        "credential_env": [
            HERMES_APP_ID_ENV,
            HERMES_INSTALLATION_ID_ENV,
            HERMES_PRIVATE_KEY_PATH_ENV,
        ],
    }
