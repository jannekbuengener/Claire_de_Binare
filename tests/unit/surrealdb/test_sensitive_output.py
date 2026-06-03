"""Unit tests for SurrealDB sensitive output redaction (#2918-#2920)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb import audit_trail_t3_common as t3_common
from tools.surrealdb.sensitive_output import (
    REDACT_PLACEHOLDER,
    redact_sensitive_json,
    redact_sensitive_mapping,
    redact_sensitive_text,
    write_restricted_secret_file,
)

pytestmark = pytest.mark.unit


def test_redact_sensitive_text_masks_env_and_urls() -> None:
    raw = (
        "SURREAL_PASS=super-secret-password "
        "token=abc123 https://user:pass@host/db"
    )
    redacted = redact_sensitive_text(raw)
    assert "super-secret-password" not in redacted
    assert "abc123" not in redacted
    assert "user:pass" not in redacted
    assert REDACT_PLACEHOLDER in redacted


def test_redact_sensitive_mapping_preserves_key_names() -> None:
    payload = {
        "auth_token": "leaked-token",
        "status": "ok",
        "nested": {"api_key": "secret-value"},
    }
    redacted = redact_sensitive_mapping(payload)
    assert redacted["auth_token"] == REDACT_PLACEHOLDER
    assert redacted["status"] == "ok"
    assert redacted["nested"]["api_key"] == REDACT_PLACEHOLDER


def test_redact_sensitive_json_is_parseable() -> None:
    rendered = redact_sensitive_json(
        {"message": "failure", "password": "must-not-appear"}
    )
    parsed = json.loads(rendered)
    assert parsed["password"] == REDACT_PLACEHOLDER
    assert "must-not-appear" not in rendered


def test_write_env_file_uses_sidecar_not_inline_password(tmp_path: Path) -> None:
    env_file = tmp_path / t3_common.ENV_FILENAME
    t3_common.write_env_file(
        env_file,
        surreal_url="https://10.0.0.5:8020",
        surreal_user="audit_user",
        surreal_pass="operator-pass-must-not-inline",
    )
    env_text = env_file.read_text(encoding="utf-8")
    assert "operator-pass-must-not-inline" not in env_text
    assert f"SURREAL_PASS_FILE={t3_common.PASS_SIDECAR_FILENAME}" in env_text
    sidecar = tmp_path / t3_common.PASS_SIDECAR_FILENAME
    assert sidecar.read_text(encoding="utf-8").strip() == "operator-pass-must-not-inline"


def test_load_env_file_reads_password_sidecar(tmp_path: Path) -> None:
    env_file = tmp_path / t3_common.ENV_FILENAME
    t3_common.write_env_file(
        env_file,
        surreal_url="https://10.0.0.5:8020",
        surreal_user="audit_user",
        surreal_pass="sidecar-only-pass",
    )
    loaded = t3_common.load_env_file(env_file)
    assert loaded.surreal_pass == "sidecar-only-pass"


def test_load_env_file_supports_legacy_inline_password(tmp_path: Path) -> None:
    env_file = tmp_path / t3_common.ENV_FILENAME
    env_file.write_text(
        "\n".join(
            [
                "SURREAL_URL=https://10.0.0.5:8020",
                "SURREAL_NS=cdb",
                "SURREAL_DB=audit_trail",
                "SURREAL_USER=audit_user",
                "SURREAL_PASS=legacy-inline-pass",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    loaded = t3_common.load_env_file(env_file)
    assert loaded.surreal_pass == "legacy-inline-pass"


def test_write_compose_env_file_omits_password(tmp_path: Path) -> None:
    compose_env = tmp_path / t3_common.COMPOSE_ENV_FILENAME
    t3_common.write_compose_env_file(compose_env, surreal_user="audit_user")
    text = compose_env.read_text(encoding="utf-8")
    assert text == "SURREAL_USER=audit_user\n"
    assert "SURREAL_PASS" not in text


def test_write_restricted_secret_file_roundtrip(tmp_path: Path) -> None:
    secret_path = tmp_path / "credential.pass"
    write_restricted_secret_file(secret_path, "stored-secret")
    assert secret_path.read_text(encoding="utf-8").strip() == "stored-secret"
