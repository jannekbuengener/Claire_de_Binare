"""GitHub App JWT + installation-token minting for Check Run publisher (#4170 Phase C).

Credentials stay in memory only. Never log PEM, JWT, or installation tokens.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes

from ci.publisher.exceptions import AuthenticationError, GitHubApiError, PublisherError
from ci.publisher.github_client import (
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_API,
    GitHubResponse,
    Transport,
    _default_transport,
)
from ci.publisher.redaction import redact_mapping, redact_text

# Canonical env names
APP_ID_ENV = "CDB_GH_APP_ID"
INSTALLATION_ID_ENV = "CDB_GH_APP_INSTALLATION_ID"
PRIVATE_KEY_ENV = "CDB_GH_APP_PRIVATE_KEY"
PRIVATE_KEY_PATH_ENV = "CDB_GH_APP_PRIVATE_KEY_PATH"

# Documented read aliases (operator User-env convenience)
APP_ID_ALIAS_ENV = "CDB_GITHUB_APP_ID"
INSTALLATION_ID_ALIAS_ENV = "CDB_GITHUB_APP_INSTALLATION_ID"
PRIVATE_KEY_PATH_ALIAS_ENV = "CDB_GITHUB_APP_PRIVATE_KEY_PATH"

# GitHub App JWT TTL: max 10 minutes; use ~9 minutes with 60s past iat skew.
JWT_IAT_SKEW_SECONDS = 60
JWT_TTL_SECONDS = 540


def _env_first(*names: str) -> str:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def _parse_positive_int(value: object, *, field_name: str) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise PublisherError(
            f"{field_name} must be a positive integer, got {value!r}"
        ) from exc
    if parsed <= 0:
        raise PublisherError(f"{field_name} must be a positive integer, got {parsed}")
    return parsed


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def resolve_app_id_from_env() -> int:
    """Resolve App ID from canonical env, then documented alias."""
    raw = _env_first(APP_ID_ENV, APP_ID_ALIAS_ENV)
    if not raw:
        raise AuthenticationError(
            f"Missing {APP_ID_ENV} (alias {APP_ID_ALIAS_ENV} also unset)"
        )
    return _parse_positive_int(raw, field_name=APP_ID_ENV)


def resolve_installation_id_from_env() -> int:
    """Resolve Installation ID from canonical env, then documented alias."""
    raw = _env_first(INSTALLATION_ID_ENV, INSTALLATION_ID_ALIAS_ENV)
    if not raw:
        raise AuthenticationError(
            f"Missing {INSTALLATION_ID_ENV} "
            f"(alias {INSTALLATION_ID_ALIAS_ENV} also unset)"
        )
    return _parse_positive_int(raw, field_name=INSTALLATION_ID_ENV)


def _normalize_pem_text(raw: str) -> bytes:
    text = raw.strip()
    if not text:
        raise AuthenticationError("GitHub App private key is empty")
    # Support env values that escaped newlines as literal \n
    if "\\n" in text and "-----BEGIN" in text:
        text = text.replace("\\n", "\n")
    if "-----BEGIN" not in text:
        raise AuthenticationError("GitHub App private key is not a PEM block")
    return text.encode("utf-8")


def load_private_key_pem() -> bytes:
    """Load PEM bytes: inline env wins over path env (canonical before alias path)."""
    inline = (os.environ.get(PRIVATE_KEY_ENV) or "").strip()
    if inline:
        return _normalize_pem_text(inline)
    path_raw = _env_first(PRIVATE_KEY_PATH_ENV, PRIVATE_KEY_PATH_ALIAS_ENV)
    if not path_raw:
        raise AuthenticationError(
            f"Missing {PRIVATE_KEY_ENV} and {PRIVATE_KEY_PATH_ENV} "
            f"(alias {PRIVATE_KEY_PATH_ALIAS_ENV} also unset)"
        )
    path = Path(path_raw).expanduser()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise AuthenticationError(
            f"Unable to read GitHub App private key path "
            f"({PRIVATE_KEY_PATH_ENV}): {redact_text(type(exc).__name__)}"
        ) from exc
    if not data.strip():
        raise AuthenticationError("GitHub App private key file is empty")
    try:
        return _normalize_pem_text(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise AuthenticationError(
            "GitHub App private key file is not valid UTF-8 PEM text"
        ) from exc


def _load_rsa_private_key(pem: bytes) -> PrivateKeyTypes:
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError(
            "GitHub App private key PEM is invalid or unreadable"
        ) from exc
    if not hasattr(key, "sign"):
        raise AuthenticationError("GitHub App private key is not an RSA signing key")
    return key


def mint_app_jwt(
    *,
    app_id: int,
    private_key_pem: bytes,
    now: int | None = None,
) -> str:
    """Create a short-lived RS256 App JWT (in memory only)."""
    issued_at = int(now if now is not None else time.time())
    payload = {
        "iat": issued_at - JWT_IAT_SKEW_SECONDS,
        "exp": issued_at - JWT_IAT_SKEW_SECONDS + JWT_TTL_SECONDS,
        "iss": str(app_id),
    }
    header = {"alg": "RS256", "typ": "JWT"}
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    ).encode("ascii")
    key = _load_rsa_private_key(private_key_pem)
    try:
        signature = key.sign(  # type: ignore[union-attr]
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed; never surface key material
        raise AuthenticationError(
            f"Failed to sign GitHub App JWT: {type(exc).__name__}"
        ) from exc
    return f"{signing_input.decode('ascii')}.{_b64url(signature)}"


def request_installation_token(
    *,
    app_jwt: str,
    installation_id: int,
    transport: Transport | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """POST /app/installations/{id}/access_tokens; return token (memory only)."""
    if not app_jwt.strip():
        raise AuthenticationError("Empty GitHub App JWT")
    installation_id = _parse_positive_int(
        installation_id, field_name=INSTALLATION_ID_ENV
    )
    path = f"/app/installations/{installation_id}/access_tokens"
    url = f"{GITHUB_API}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {app_jwt}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cdb-local-ci-app-auth",
        "Content-Type": "application/json",
    }
    runner = transport or _default_transport
    try:
        response: GitHubResponse = runner("POST", url, headers, b"{}", timeout_seconds)
    except TimeoutError as exc:
        raise GitHubApiError("GitHub App installation token request timed out") from exc
    except GitHubApiError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GitHubApiError(
            f"GitHub App installation token request failed: {type(exc).__name__}"
        ) from exc

    if response.status_code in {401, 403}:
        raise AuthenticationError(
            "GitHub App JWT rejected or insufficient permission to mint "
            f"installation token (HTTP {response.status_code})"
        )
    if response.status_code == 404:
        raise AuthenticationError(
            f"GitHub App installation {installation_id} not found (HTTP 404)"
        )
    if response.status_code >= 400:
        raise GitHubApiError(
            f"Installation token mint failed HTTP {response.status_code}: "
            f"{redact_mapping(response.body)}"
        )
    body = response.body
    if not isinstance(body, dict):
        raise GitHubApiError("Ambiguous installation token response")
    token = str(body.get("token") or "").strip()
    if not token:
        raise AuthenticationError("Installation token response missing token field")
    return token


def mint_installation_token(
    *,
    transport: Transport | None = None,
    now: int | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Resolve App credentials from env, mint JWT, exchange for installation token."""
    app_id = resolve_app_id_from_env()
    installation_id = resolve_installation_id_from_env()
    pem = load_private_key_pem()
    jwt = mint_app_jwt(app_id=app_id, private_key_pem=pem, now=now)
    return request_installation_token(
        app_jwt=jwt,
        installation_id=installation_id,
        transport=transport,
        timeout_seconds=timeout_seconds,
    )


def app_credentials_configured() -> bool:
    """True when App ID, Installation ID, and a private-key source are present."""
    try:
        resolve_app_id_from_env()
        resolve_installation_id_from_env()
        load_private_key_pem()
    except (AuthenticationError, PublisherError):
        return False
    return True


def credential_summary() -> dict[str, Any]:
    """Non-secret diagnostic for probe/logs (never includes PEM/JWT/token)."""
    return {
        "app_id_env_present": bool(_env_first(APP_ID_ENV, APP_ID_ALIAS_ENV)),
        "installation_id_env_present": bool(
            _env_first(INSTALLATION_ID_ENV, INSTALLATION_ID_ALIAS_ENV)
        ),
        "private_key_inline_present": bool(
            (os.environ.get(PRIVATE_KEY_ENV) or "").strip()
        ),
        "private_key_path_present": bool(
            _env_first(PRIVATE_KEY_PATH_ENV, PRIVATE_KEY_PATH_ALIAS_ENV)
        ),
    }
