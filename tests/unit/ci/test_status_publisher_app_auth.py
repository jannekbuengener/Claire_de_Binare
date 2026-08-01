"""Unit tests for GitHub App JWT / installation-token auto-mint (#4170 Phase C)."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ci.publisher.app_auth import (
    APP_ID_ALIAS_ENV,
    APP_ID_ENV,
    INSTALLATION_ID_ALIAS_ENV,
    INSTALLATION_ID_ENV,
    PRIVATE_KEY_ENV,
    PRIVATE_KEY_PATH_ALIAS_ENV,
    PRIVATE_KEY_PATH_ENV,
    load_private_key_pem,
    mint_app_jwt,
    mint_installation_token,
    request_installation_token,
    resolve_app_id_from_env,
    resolve_installation_id_from_env,
)
from ci.publisher.backends import (
    APP_INSTALLATION_TOKEN_ENV,
    resolve_app_installation_token,
)
from ci.publisher.cli import main as publisher_main
from ci.publisher.exceptions import AuthenticationError, GitHubApiError
from ci.publisher.github_client import GitHubResponse
from ci.publisher.models import CHECK_RUN_NAME, SHADOW_CHECK_RUN_NAME
from ci.publisher.redaction import redact_text

pytestmark = pytest.mark.unit

APP_ID = 2247101
INSTALLATION_ID = 987654321
SHA = "dddddddddddddddddddddddddddddddddddddddd"


def _make_pem() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: list[GitHubResponse] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> GitHubResponse:
        safe_headers = {
            k: ("[REDACTED]" if k.lower() == "authorization" else v)
            for k, v in headers.items()
        }
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": safe_headers,
                "body": body.decode("utf-8") if body else None,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("No fake response queued")
        return self.responses.pop(0)


@pytest.fixture()
def pem_bytes() -> bytes:
    return _make_pem()


@pytest.fixture()
def clear_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        APP_ID_ENV,
        APP_ID_ALIAS_ENV,
        INSTALLATION_ID_ENV,
        INSTALLATION_ID_ALIAS_ENV,
        PRIVATE_KEY_ENV,
        PRIVATE_KEY_PATH_ENV,
        PRIVATE_KEY_PATH_ALIAS_ENV,
        APP_INSTALLATION_TOKEN_ENV,
        "GITHUB_TOKEN",
        "GH_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)


def test_resolve_app_id_canonical(clear_app_env: None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(APP_ID_ENV, str(APP_ID))
    assert resolve_app_id_from_env() == APP_ID


def test_resolve_app_id_alias(clear_app_env: None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(APP_ID_ALIAS_ENV, str(APP_ID))
    assert resolve_app_id_from_env() == APP_ID


def test_resolve_installation_id_alias(
    clear_app_env: None, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(INSTALLATION_ID_ALIAS_ENV, str(INSTALLATION_ID))
    assert resolve_installation_id_from_env() == INSTALLATION_ID


def test_missing_app_id_fail_closed(clear_app_env: None):
    with pytest.raises(AuthenticationError, match=APP_ID_ENV):
        resolve_app_id_from_env()


def test_missing_installation_id_fail_closed(clear_app_env: None):
    with pytest.raises(AuthenticationError, match=INSTALLATION_ID_ENV):
        resolve_installation_id_from_env()


def test_private_key_inline_beats_path(
    clear_app_env: None,
    monkeypatch: pytest.MonkeyPatch,
    pem_bytes: bytes,
    tmp_path: Path,
):
    other = _make_pem()
    path = tmp_path / "other.pem"
    path.write_bytes(other)
    monkeypatch.setenv(PRIVATE_KEY_ENV, pem_bytes.decode("utf-8"))
    monkeypatch.setenv(PRIVATE_KEY_PATH_ENV, str(path))
    loaded = load_private_key_pem()
    assert loaded.strip() == pem_bytes.strip()
    assert b"BEGIN" in loaded


def test_private_key_path_canonical(
    clear_app_env: None,
    monkeypatch: pytest.MonkeyPatch,
    pem_bytes: bytes,
    tmp_path: Path,
):
    path = tmp_path / "app.pem"
    path.write_bytes(pem_bytes)
    monkeypatch.setenv(PRIVATE_KEY_PATH_ENV, str(path))
    assert load_private_key_pem().strip() == pem_bytes.strip()


def test_private_key_path_alias(
    clear_app_env: None,
    monkeypatch: pytest.MonkeyPatch,
    pem_bytes: bytes,
    tmp_path: Path,
):
    path = tmp_path / "alias.pem"
    path.write_bytes(pem_bytes)
    monkeypatch.setenv(PRIVATE_KEY_PATH_ALIAS_ENV, str(path))
    assert load_private_key_pem().strip() == pem_bytes.strip()


def test_unreadable_pem_path_fail_closed(
    clear_app_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    missing = tmp_path / "missing.pem"
    monkeypatch.setenv(PRIVATE_KEY_PATH_ENV, str(missing))
    with pytest.raises(AuthenticationError, match="Unable to read"):
        load_private_key_pem()


def test_invalid_pem_fail_closed(clear_app_env: None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(PRIVATE_KEY_ENV, "not-a-pem")
    with pytest.raises(AuthenticationError, match="not a PEM"):
        load_private_key_pem()


def test_mint_app_jwt_rs256_no_secret_leak(pem_bytes: bytes):
    jwt = mint_app_jwt(app_id=APP_ID, private_key_pem=pem_bytes, now=1_700_000_000)
    parts = jwt.split(".")
    assert len(parts) == 3
    header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    assert header["alg"] == "RS256"
    assert payload["iss"] == str(APP_ID)
    assert "BEGIN" not in jwt
    assert pem_bytes.decode("utf-8") not in jwt
    redacted = redact_text(f"Authorization: Bearer {jwt}")
    assert "[REDACTED]" in redacted
    assert jwt not in redacted


def test_request_installation_token_success(pem_bytes: bytes):
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(201, {"token": "ghs_installation_token_testvalue"}, {})
    )
    jwt = mint_app_jwt(app_id=APP_ID, private_key_pem=pem_bytes, now=1_700_000_000)
    token = request_installation_token(
        app_jwt=jwt, installation_id=INSTALLATION_ID, transport=transport
    )
    assert token.startswith("ghs_")
    assert transport.calls[0]["method"] == "POST"
    assert (
        f"/app/installations/{INSTALLATION_ID}/access_tokens"
        in transport.calls[0]["url"]
    )
    assert transport.calls[0]["headers"]["Authorization"] == "[REDACTED]"


@pytest.mark.parametrize("status", [401, 403, 404])
def test_request_installation_token_auth_errors(status: int, pem_bytes: bytes):
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(status, {"message": "nope ghs_should_redact_abcdefgh"}, {})
    )
    jwt = mint_app_jwt(app_id=APP_ID, private_key_pem=pem_bytes, now=1_700_000_000)
    with pytest.raises(AuthenticationError):
        request_installation_token(
            app_jwt=jwt, installation_id=INSTALLATION_ID, transport=transport
        )


def test_request_installation_token_missing_token_field(pem_bytes: bytes):
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(201, {"expires_at": "soon"}, {}))
    jwt = mint_app_jwt(app_id=APP_ID, private_key_pem=pem_bytes, now=1_700_000_000)
    with pytest.raises(AuthenticationError, match="missing token"):
        request_installation_token(
            app_jwt=jwt, installation_id=INSTALLATION_ID, transport=transport
        )


def test_request_installation_token_rejects_redacted_sentinel(pem_bytes: bytes):
    """Regression: _default_transport redact_mapping replaced token with [REDACTED]."""
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(201, {"token": "[REDACTED]"}, {}))
    jwt = mint_app_jwt(app_id=APP_ID, private_key_pem=pem_bytes, now=1_700_000_000)
    with pytest.raises(AuthenticationError, match="redacted before extraction"):
        request_installation_token(
            app_jwt=jwt, installation_id=INSTALLATION_ID, transport=transport
        )


def test_default_style_redacting_transport_would_break_without_mint_transport(
    pem_bytes: bytes,
):
    """Simulate _default_transport success path (redact_mapping on body)."""
    from ci.publisher.redaction import redact_mapping

    real_token = "ghs_live_style_installation_token_xx"

    def redacting_transport(method, url, headers, body, timeout):
        return GitHubResponse(
            201,
            redact_mapping({"token": real_token, "permissions": {"checks": "write"}}),
            {},
        )

    jwt = mint_app_jwt(app_id=APP_ID, private_key_pem=pem_bytes, now=1_700_000_000)
    with pytest.raises(AuthenticationError, match="redacted before extraction"):
        request_installation_token(
            app_jwt=jwt,
            installation_id=INSTALLATION_ID,
            transport=redacting_transport,
        )


def test_mint_installation_token_end_to_end(
    clear_app_env: None,
    monkeypatch: pytest.MonkeyPatch,
    pem_bytes: bytes,
    tmp_path: Path,
):
    path = tmp_path / "key.pem"
    path.write_bytes(pem_bytes)
    monkeypatch.setenv(APP_ID_ENV, str(APP_ID))
    monkeypatch.setenv(INSTALLATION_ID_ENV, str(INSTALLATION_ID))
    monkeypatch.setenv(PRIVATE_KEY_PATH_ENV, str(path))
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(201, {"token": "ghs_minted_installation_abcdefgh"}, {})
    )
    token = mint_installation_token(transport=transport, now=1_700_000_000)
    assert token.startswith("ghs_minted_")


def test_resolve_priority_explicit_token_env_beats_mint(
    clear_app_env: None, monkeypatch: pytest.MonkeyPatch, pem_bytes: bytes
):
    monkeypatch.setenv(APP_INSTALLATION_TOKEN_ENV, "ghs_explicit_env_token_value")
    monkeypatch.setenv(APP_ID_ENV, str(APP_ID))
    monkeypatch.setenv(INSTALLATION_ID_ENV, str(INSTALLATION_ID))
    monkeypatch.setenv(PRIVATE_KEY_ENV, pem_bytes.decode("utf-8"))
    transport = FakeTransport()
    token = resolve_app_installation_token(transport=transport)
    assert token == "ghs_explicit_env_token_value"
    assert transport.calls == []


def test_resolve_auto_mint_when_token_env_missing(
    clear_app_env: None,
    monkeypatch: pytest.MonkeyPatch,
    pem_bytes: bytes,
    tmp_path: Path,
):
    path = tmp_path / "key.pem"
    path.write_bytes(pem_bytes)
    monkeypatch.setenv(APP_ID_ALIAS_ENV, str(APP_ID))
    monkeypatch.setenv(INSTALLATION_ID_ALIAS_ENV, str(INSTALLATION_ID))
    monkeypatch.setenv(PRIVATE_KEY_PATH_ALIAS_ENV, str(path))
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(201, {"token": "ghs_auto_minted_token_valuexx"}, {})
    )
    token = resolve_app_installation_token(transport=transport)
    assert token.startswith("ghs_auto_minted_")


def test_resolve_no_pat_fallback_when_mint_fails(
    clear_app_env: None, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_should_not_be_used_abcdefgh")
    monkeypatch.setenv("GH_TOKEN", "ghs_also_not_used_abcdefghijkl")
    with pytest.raises(AuthenticationError, match="refuses"):
        resolve_app_installation_token()


def test_resolve_explicit_inject(clear_app_env: None):
    assert (
        resolve_app_installation_token(explicit="ghs_explicit_inject_token_xx")
        == "ghs_explicit_inject_token_xx"
    )


def test_app_auth_probe_refuses_required_name(capsys: pytest.CaptureFixture[str]):
    code = publisher_main(
        [
            "app-auth-probe",
            "--commit-sha",
            SHA,
            "--check-run-name",
            CHECK_RUN_NAME,
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "refused" in err.lower() or "rejects" in err.lower() or "REJECT" in err
    assert CHECK_RUN_NAME in err or "non-shadow" in err.lower() or "only allows" in err


def test_app_auth_probe_requires_sha():
    code = publisher_main(["app-auth-probe", "--commit-sha", "short"])
    assert code == 2


def test_app_auth_probe_dry_run_with_mint(
    clear_app_env: None,
    monkeypatch: pytest.MonkeyPatch,
    pem_bytes: bytes,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    path = tmp_path / "key.pem"
    path.write_bytes(pem_bytes)
    monkeypatch.setenv(APP_ID_ENV, str(APP_ID))
    monkeypatch.setenv(INSTALLATION_ID_ENV, str(INSTALLATION_ID))
    monkeypatch.setenv(PRIVATE_KEY_PATH_ENV, str(path))
    monkeypatch.setenv(APP_INSTALLATION_TOKEN_ENV, "ghs_probe_dry_run_token_value")

    code = publisher_main(
        [
            "app-auth-probe",
            "--commit-sha",
            SHA,
            "--dry-run",
            "--check-run-name",
            SHADOW_CHECK_RUN_NAME,
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["check_run_name"] == SHADOW_CHECK_RUN_NAME
    assert payload["sha"] == SHA
    assert "ghs_" not in out
    assert "BEGIN" not in out
