"""Unit tests for SurrealDBLocalContextApplyAdapter (#2458).

All tests use mocked urllib; no real SurrealDB container is needed.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
import urllib.error

import pytest

from tools.surrealdb.context_importer import (
    ADAPTER_KIND_SURREALDB_LOCAL,
    ALLOWED_CONTEXT_IMPORT_TABLES,
    ApplyAdapterError,
    ApplyGateError,
    REAL_SURREALDB_ADAPTER_AVAILABLE,
    SurrealDBLocalContextApplyAdapter,
    TOMBSTONE_FIELD_AT,
    TOMBSTONE_FIELD_FLAG,
    TOMBSTONE_FIELD_LAST_SEEN_RUN_ID,
    TOMBSTONE_FIELD_REASON,
    TOMBSTONE_FIELD_SUPERSEDED_BY,
    _payload_to_surql_content,
    main,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOCAL_URL = "http://127.0.0.1:8010"
_NS = "cdb_context_local"
_DB = "cdb_context_intel"


def _ok_body(result: Any = None) -> bytes:
    return json.dumps([{"status": "OK", "result": result}]).encode()


def _make_adapter(
    url: str = _LOCAL_URL,
    user: str | None = None,
    password: str | None = None,
    timeout: int = 5,
) -> SurrealDBLocalContextApplyAdapter:
    return SurrealDBLocalContextApplyAdapter(
        surreal_url=url,
        namespace=_NS,
        database=_DB,
        user=user,
        password=password,
        timeout=timeout,
    )


def _tombstone_payload() -> dict[str, Any]:
    return {
        # Tombstone meta-fields (required by adapter validation before write)
        TOMBSTONE_FIELD_FLAG: True,
        TOMBSTONE_FIELD_AT: "2026-05-13T12:00:00Z",
        TOMBSTONE_FIELD_REASON: "record_removed_from_snapshot",
        TOMBSTONE_FIELD_LAST_SEEN_RUN_ID: "run-1",
        TOMBSTONE_FIELD_SUPERSEDED_BY: None,
        # Domain fields preserved from the prior record's existing_payload
        "chunk_id": "chunk-test-1",
        "content": "the prior content of this chunk",
    }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_real_surrealdb_adapter_available_is_true() -> None:
    """#2458: REAL_SURREALDB_ADAPTER_AVAILABLE must be True after implementation."""
    assert REAL_SURREALDB_ADAPTER_AVAILABLE is True


@pytest.mark.unit
def test_adapter_kind_constant() -> None:
    assert ADAPTER_KIND_SURREALDB_LOCAL == "surrealdb-local"


@pytest.mark.unit
def test_adapter_kind_attribute() -> None:
    adapter = _make_adapter()
    assert adapter.kind == ADAPTER_KIND_SURREALDB_LOCAL


# ---------------------------------------------------------------------------
# URL guard (fail-closed for non-local targets)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_adapter_rejects_remote_ip() -> None:
    with pytest.raises(ApplyGateError):
        _make_adapter(url="http://10.0.0.1:8010")


@pytest.mark.unit
def test_adapter_rejects_production_url() -> None:
    with pytest.raises(ApplyGateError):
        _make_adapter(url="https://surrealdb.prod.example.com/")


@pytest.mark.unit
def test_adapter_accepts_127_0_0_1() -> None:
    _make_adapter(url="http://127.0.0.1:8010")  # must not raise


@pytest.mark.unit
def test_adapter_accepts_localhost() -> None:
    _make_adapter(url="http://localhost:8010")  # must not raise


# ---------------------------------------------------------------------------
# apply_create — SQL sent to /sql
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_create_sends_upsert_content_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _make_adapter()
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter.apply_create("repo_artifact", "abc-123", {"path": "README.md"})

    assert len(sent) == 1
    sql = sent[0]
    assert "UPSERT repo_artifact:" in sql
    assert "CONTENT" in sql
    assert "README.md" in sql


@pytest.mark.unit
def test_apply_create_no_auth_header_when_no_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _make_adapter(user=None, password=None)
    captured_req: list[Any] = []

    def fake_urlopen(req, timeout=None):
        captured_req.append(req)
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter.apply_create("repo_artifact", "abc", {"k": "v"})

    req = captured_req[0]
    assert req.get_header("Authorization") is None


@pytest.mark.unit
def test_apply_create_includes_basic_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _make_adapter(user="root", password="s3cr3t")
    captured_req: list[Any] = []

    def fake_urlopen(req, timeout=None):
        captured_req.append(req)
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter.apply_create("repo_artifact", "abc", {"k": "v"})

    req = captured_req[0]
    expected_token = base64.b64encode(b"root:s3cr3t").decode()
    assert req.get_header("Authorization") == f"Basic {expected_token}"


# ---------------------------------------------------------------------------
# apply_update — same SQL pattern as create (UPSERT CONTENT)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_update_sends_upsert_content_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _make_adapter()
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter.apply_update("doc_page", "page-1", {"title": "updated"})

    assert len(sent) == 1
    sql = sent[0]
    assert "UPSERT doc_page:" in sql
    assert "CONTENT" in sql
    assert "updated" in sql


# ---------------------------------------------------------------------------
# apply_tombstone
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_tombstone_sends_upsert_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _make_adapter()
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    payload = _tombstone_payload()
    adapter.apply_tombstone("doc_chunk", "chunk-1", payload)

    assert len(sent) == 1
    sql = sent[0]
    assert "UPSERT doc_chunk:" in sql
    assert "CONTENT" in sql
    # Domain fields from the prior record are preserved in the DB write
    assert "chunk-test-1" in sql
    # Tombstone meta-fields are stripped — not declared in context_intelligence_v0.surql
    assert "record_removed_from_snapshot" not in sql
    assert "tombstoned" not in sql


@pytest.mark.unit
def test_apply_tombstone_missing_fields_raises() -> None:
    adapter = _make_adapter()
    with pytest.raises(ApplyAdapterError, match="missing required fields"):
        adapter.apply_tombstone("doc_chunk", "chunk-1", {})


@pytest.mark.unit
def test_apply_tombstone_flag_must_be_true_raises() -> None:
    adapter = _make_adapter()
    payload = _tombstone_payload()
    payload[TOMBSTONE_FIELD_FLAG] = False
    with pytest.raises(ApplyAdapterError, match=TOMBSTONE_FIELD_FLAG):
        adapter.apply_tombstone("doc_chunk", "chunk-1", payload)


# ---------------------------------------------------------------------------
# HTTP error handling (fail-closed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_http_500_raises_apply_adapter_error(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _make_adapter()

    class FakeHTTPError(urllib.error.HTTPError):
        def read(self) -> bytes:
            return b""

    http_err = FakeHTTPError(
        url=f"{_LOCAL_URL}/sql",
        code=500,
        msg="Internal Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(http_err),
    )

    with pytest.raises(ApplyAdapterError):
        adapter.apply_create("repo_artifact", "abc", {"k": "v"})


@pytest.mark.unit
def test_connection_refused_raises_apply_adapter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _make_adapter()
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(
            urllib.error.URLError("Connection refused")
        ),
    )

    with pytest.raises(ApplyAdapterError, match="connection failed"):
        adapter.apply_create("repo_artifact", "abc", {"k": "v"})


@pytest.mark.unit
def test_surrealdb_err_response_raises_apply_adapter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _make_adapter()
    err_body = json.dumps([{"status": "ERR", "result": "Parse error"}]).encode()

    def fake_urlopen(req, timeout=None):
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = err_body
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ApplyAdapterError, match="statement error"):
        adapter.apply_create("repo_artifact", "abc", {"k": "v"})


# ---------------------------------------------------------------------------
# Credential security — secrets must never appear in error messages or logs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_password_not_in_adapter_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _make_adapter(user="myuser", password="supersecret123")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(
            urllib.error.URLError("Connection refused")
        ),
    )

    with pytest.raises(ApplyAdapterError) as exc_info:
        adapter.apply_create("repo_artifact", "abc", {"k": "v"})

    assert "supersecret123" not in str(exc_info.value)
    assert "myuser" not in str(exc_info.value)


@pytest.mark.unit
def test_password_not_in_log_output(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    adapter = _make_adapter(user="root", password="hunter2")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **kw: (_ for _ in ()).throw(
            urllib.error.URLError("Connection refused")
        ),
    )

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ApplyAdapterError):
            adapter.apply_create("repo_artifact", "abc", {"k": "v"})

    for record in caplog.records:
        assert "hunter2" not in record.getMessage()
        assert "hunter2" not in (record.exc_text or "")


# ---------------------------------------------------------------------------
# CLI adapter selection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cli_help_advertises_adapter_flag(capsys: pytest.CaptureFixture) -> None:
    """CLI --help shows --adapter flag with both choices."""
    with pytest.raises(SystemExit) as exc_info:
        main(["apply", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "--adapter" in out
    assert "in-memory" in out
    assert "surrealdb-local" in out


@pytest.mark.unit
def test_cli_default_adapter_choice_is_in_memory(capsys: pytest.CaptureFixture) -> None:
    """Without --adapter flag, help shows in-memory as the default."""
    with pytest.raises(SystemExit) as exc_info:
        main(["apply", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "in-memory" in out


# ---------------------------------------------------------------------------
# Makefile / config integration checks
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_import_local_uses_surrealdb_local_adapter() -> None:
    """Makefile context-import-local must pass --adapter surrealdb-local (#2458)."""
    makefile = Path(__file__).parents[3] / "Makefile"
    assert makefile.exists(), "Makefile not found"
    content = makefile.read_text(encoding="utf-8")
    in_target = False
    for line in content.splitlines():
        if line.startswith("context-import-local:"):
            in_target = True
        elif in_target and line.startswith("\t"):
            if "--adapter surrealdb-local" in line:
                return
        elif in_target and not line.startswith("\t") and line.strip():
            break
    pytest.fail(
        "context-import-local target in Makefile does not contain '--adapter surrealdb-local'"
    )


@pytest.mark.unit
def test_config_example_allowed_tables_match_allowed_context_import_tables() -> None:
    """Config example allowed_tables must exactly match ALLOWED_CONTEXT_IMPORT_TABLES."""
    import yaml as _yaml

    config_path = (
        Path(__file__).parents[3]
        / "infrastructure"
        / "config"
        / "surrealdb"
        / "context_import.local.example.yaml"
    )
    assert config_path.exists(), f"Config example not found at {config_path}"
    data = _yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_tables = frozenset(data.get("allowed_tables", []))
    assert config_tables == ALLOWED_CONTEXT_IMPORT_TABLES, (
        f"Config allowed_tables {sorted(config_tables)} != "
        f"ALLOWED_CONTEXT_IMPORT_TABLES {sorted(ALLOWED_CONTEXT_IMPORT_TABLES)}"
    )


# ---------------------------------------------------------------------------
# Domain payload threading — adapter receives real JSONL fields, not metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_writes_domain_payload_not_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_create must serialize actual domain fields, not import metadata."""
    adapter = _make_adapter()
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    # Domain payload from a repo_artifact JSONL record
    domain_payload = {
        "artifact_id": "art-readme-1",
        "source_path": "README.md",
        "source_hash": "a" * 64,
        "integrity_algo": "sha256",
        "size_bytes": 128,
    }
    adapter.apply_create("repo_artifact", "repo_artifact:art-readme-1", domain_payload)

    assert len(sent) == 1
    sql = sent[0]
    content_part = sql.split("CONTENT", 1)[1]
    # Domain fields present
    assert "artifact_id" in content_part
    assert "art-readme-1" in content_part
    assert "README.md" in content_part
    # Import meta-fields must NOT be written to the SCHEMAFULL table
    assert "payload_hash" not in content_part
    assert '"table"' not in content_part
    assert '"record_id"' not in content_part
    assert '"run_id"' not in content_part


@pytest.mark.unit
def test_update_writes_domain_payload_not_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_update must serialize actual domain fields, not import metadata."""
    adapter = _make_adapter()
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    # Domain payload from a doc_page JSONL record
    domain_payload = {
        "page_id": "page-onboarding",
        "source_path": "docs/onboarding.md",
        "title": "Developer Onboarding",
        "source_hash": "b" * 64,
    }
    adapter.apply_update("doc_page", "doc_page:page-onboarding", domain_payload)

    assert len(sent) == 1
    sql = sent[0]
    content_part = sql.split("CONTENT", 1)[1]
    assert "page_id" in content_part
    assert "page-onboarding" in content_part
    assert "Developer Onboarding" in content_part
    assert "payload_hash" not in content_part
    assert '"table"' not in content_part


@pytest.mark.unit
def test_tombstone_domain_fields_preserved_meta_stripped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_tombstone must write domain fields and strip tombstone/meta-fields."""
    adapter = _make_adapter()
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    # doc_chunk domain fields + tombstone meta (as _build_payload_for_op produces)
    payload = {
        # domain fields from existing_payload
        "chunk_id": "chunk-api-1",
        "content": "API description text",
        "content_hash": "c" * 64,
        # tombstone meta-fields (not in context_intelligence_v0.surql)
        TOMBSTONE_FIELD_FLAG: True,
        TOMBSTONE_FIELD_AT: "2026-05-13T12:00:00Z",
        TOMBSTONE_FIELD_REASON: "record_removed_from_snapshot",
        TOMBSTONE_FIELD_LAST_SEEN_RUN_ID: "run-2",
        TOMBSTONE_FIELD_SUPERSEDED_BY: None,
        # pipeline meta-fields (not in schema)
        "table": "doc_chunk",
        "record_id": "doc_chunk:chunk-api-1",
        "run_id": "run-2",
        "payload_hash": "d" * 64,
    }
    adapter.apply_tombstone("doc_chunk", "doc_chunk:chunk-api-1", payload)

    assert len(sent) == 1
    sql = sent[0]
    content_part = sql.split("CONTENT", 1)[1]
    # Domain fields from prior record are written
    assert "chunk-api-1" in content_part
    assert "API description text" in content_part
    # Tombstone meta-fields are stripped — not in context_intelligence_v0.surql
    assert "tombstoned" not in content_part
    assert "tombstone_reason" not in content_part
    assert "record_removed_from_snapshot" not in content_part
    assert "last_seen_run_id" not in content_part
    # Pipeline meta-fields also stripped
    assert "payload_hash" not in content_part
    assert '"run_id"' not in content_part


# ---------------------------------------------------------------------------
# Auth / Makefile checks (Thread B)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_context_import_local_passes_secrets_path() -> None:
    """context-import-local target must pass --secrets-path for auth_mode: root."""
    makefile = Path(__file__).parents[3] / "Makefile"
    assert makefile.exists(), "Makefile not found"
    content = makefile.read_text(encoding="utf-8")
    in_target = False
    for line in content.splitlines():
        if line.startswith("context-import-local:"):
            in_target = True
        elif in_target and line.startswith("\t"):
            if "--secrets-path" in line:
                return
        elif in_target and not line.startswith("\t") and line.strip():
            break
    pytest.fail(
        "context-import-local target in Makefile does not pass --secrets-path"
    )


@pytest.mark.unit
def test_example_config_auth_mode_is_root() -> None:
    """Example config must use auth_mode: root to match the local sidecar auth setup."""
    import yaml as _yaml

    config_path = (
        Path(__file__).parents[3]
        / "infrastructure"
        / "config"
        / "surrealdb"
        / "context_import.local.example.yaml"
    )
    assert config_path.exists(), f"Config example not found at {config_path}"
    data = _yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data.get("auth_mode") == "root", (
        f"Expected auth_mode: root, got: {data.get('auth_mode')!r}. "
        "The local sidecar (cdb_surrealdb) requires SURREAL_USER/SURREAL_PASS; "
        "auth_mode must be 'root', not 'none'."
    )


# ---------------------------------------------------------------------------
# SurrealQL datetime literal serialization (#2573 / datetime coercion fix)
# ---------------------------------------------------------------------------


def _capture_sql(monkeypatch: pytest.MonkeyPatch) -> "list[str]":
    """Return a list that will be populated with each SQL body sent via urlopen."""
    sent: list[str] = []

    def fake_urlopen(req, timeout=None):
        sent.append(req.data.decode("utf-8"))
        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.status = 200
        resp.read.return_value = _ok_body()
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return sent


@pytest.mark.unit
def test_apply_create_observed_at_becomes_surql_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_create must write observed_at as a SurrealQL datetime literal.

    SurrealDB v2 SCHEMAFULL TYPE datetime rejects plain JSON strings; the
    importer must emit d"..." syntax for allowlisted datetime fields.
    """
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_create(
        "repo_artifact",
        "art-ts-1",
        {
            "artifact_id": "art-ts-1",
            "source_path": "docs/DESIGN.md",
            "observed_at": "2026-05-18T19:50:12Z",
            "confidence": 1.0,
        },
    )

    assert len(sent) == 1
    content_part = sent[0].split("CONTENT", 1)[1]
    # observed_at must be a SurrealQL datetime literal, not a JSON string
    assert 'd"2026-05-18T19:50:12Z"' in content_part
    assert '"observed_at": "2026-05-18T19:50:12Z"' not in content_part
    # Non-datetime fields must remain untouched
    assert "DESIGN.md" in content_part
    assert '"confidence": 1.0' in content_part


@pytest.mark.unit
def test_apply_create_non_allowlisted_iso_string_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-allowlisted fields with ISO-like string values must stay as JSON strings.

    Only the explicit _SURQL_DATETIME_FIELDS allowlist is converted; arbitrary
    text fields (e.g. description, notes) that happen to contain ISO timestamps
    must not be rewritten.
    """
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_create(
        "repo_artifact",
        "art-ts-2",
        {
            "artifact_id": "art-ts-2",
            "description": "2026-05-18T19:50:12Z",  # non-allowlisted field
            "source_path": "README.md",
        },
    )

    content_part = sent[0].split("CONTENT", 1)[1]
    # The non-allowlisted field must remain a plain JSON string
    assert '"description": "2026-05-18T19:50:12Z"' in content_part
    assert 'description: d"' not in content_part


@pytest.mark.unit
def test_apply_update_collected_at_becomes_surql_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_update must also convert allowlisted datetime fields (e.g. collected_at)."""
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_update(
        "evidence_ref",
        "ev-1",
        {
            "evidence_id": "ev-1",
            "collected_at": "2026-04-01T10:00:00Z",
        },
    )

    content_part = sent[0].split("CONTENT", 1)[1]
    assert 'd"2026-04-01T10:00:00Z"' in content_part
    assert '"collected_at": "2026-04-01T10:00:00Z"' not in content_part


@pytest.mark.unit
def test_apply_tombstone_datetime_field_surql_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_tombstone must use the same datetime literal serialization.

    Tombstone meta-fields are stripped before writing; remaining domain fields
    that contain allowlisted datetime values must be emitted as d"..." literals.
    """
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    payload = _tombstone_payload()
    # Add an allowlisted datetime field to the domain portion
    payload["observed_at"] = "2026-03-15T08:30:00Z"

    adapter.apply_tombstone("doc_chunk", "chunk-ts-1", payload)

    assert len(sent) == 1
    content_part = sent[0].split("CONTENT", 1)[1]
    # Domain datetime field converted to literal
    assert 'd"2026-03-15T08:30:00Z"' in content_part
    # Tombstone meta-fields stripped as before
    assert "record_removed_from_snapshot" not in content_part


@pytest.mark.unit
def test_payload_to_surql_content_roundtrip() -> None:
    """_payload_to_surql_content unit tests: allowlist, non-allowlist, null, number."""
    # Allowlisted field with Z-suffix ISO string → converted
    result = _payload_to_surql_content({"observed_at": "2026-05-18T19:50:12Z", "x": "y"})
    assert '"observed_at": d"2026-05-18T19:50:12Z"' in result
    assert '"x": "y"' in result

    # Non-allowlisted ISO-like field → not converted
    result2 = _payload_to_surql_content({"timestamp_text": "2026-05-18T19:50:12Z"})
    assert '"timestamp_text": "2026-05-18T19:50:12Z"' in result2
    assert "d\"" not in result2

    # Allowlisted field without Z suffix → not converted (no partial matches)
    result3 = _payload_to_surql_content({"observed_at": "2026-05-18T19:50:12"})
    assert '"observed_at": "2026-05-18T19:50:12"' in result3
    assert "d\"" not in result3

    # Null value for allowlisted field → not converted (null is not a string)
    result4 = _payload_to_surql_content({"observed_at": None})
    assert '"observed_at": null' in result4
    assert "d\"" not in result4


@pytest.mark.unit
def test_payload_to_surql_content_record_ref_unquoted() -> None:
    """page_ref / section_ref record-ref strings are unquoted in CONTENT (#2577)."""
    result = _payload_to_surql_content({
        "page_ref": "doc_page:\u27e8page-example\u27e9",
        "title": "Example",
    })
    assert '"page_ref": doc_page:\u27e8page-example\u27e9' in result
    assert '"title": "Example"' in result
    # Must not appear quoted
    assert '"page_ref": "doc_page:' not in result


@pytest.mark.unit
def test_payload_to_surql_content_section_ref_unquoted() -> None:
    """section_ref record-ref strings are unquoted in CONTENT (#2577)."""
    result = _payload_to_surql_content({
        "section_ref": "doc_section:\u27e8section-example\u27e9",
    })
    assert '"section_ref": doc_section:\u27e8section-example\u27e9' in result
    assert '"section_ref": "doc_section:' not in result


@pytest.mark.unit
def test_payload_to_surql_content_datetime_regression_after_ascii_change() -> None:
    """ensure_ascii=False must not break the existing datetime literal conversion."""
    result = _payload_to_surql_content({
        "observed_at": "2026-05-18T19:50:12Z",
        "title": "still works",
    })
    assert '"observed_at": d"2026-05-18T19:50:12Z"' in result
    assert '"title": "still works"' in result


@pytest.mark.unit
def test_apply_create_doc_section_page_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_create for doc_section: page_id is remapped to page_ref record ref (#2577).

    Input payload uses page_id (JSONL contract); the SQL CONTENT must contain
    an unquoted page_ref record ref and must NOT contain page_id.
    """
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_create(
        "doc_section",
        "section-example",
        {
            "section_id": "section-example",
            "page_id": "page-example",
            "heading": "Example",
            "source_path": "docs/example.md",
        },
    )

    assert len(sent) == 1
    content_part = sent[0].split("CONTENT", 1)[1]
    # page_ref must be an unquoted SurrealDB record ref
    assert '"page_ref": doc_page:\u27e8page-example\u27e9' in content_part
    # page_id must not appear in DB payload
    assert '"page_id"' not in content_part
    # page_ref value must NOT be a quoted JSON string
    assert '"page_ref": "' not in content_part


@pytest.mark.unit
def test_apply_create_doc_chunk_page_ref_and_section_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_create for doc_chunk: page_id + section_id remapped to record refs (#2577).

    Input payload uses page_id and section_id (JSONL contract); the SQL CONTENT
    must contain unquoted page_ref and section_ref record refs.
    """
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_create(
        "doc_chunk",
        "chunk-example",
        {
            "chunk_id": "chunk-example",
            "page_id": "page-example",
            "section_id": "section-example",
            "content": "safe context",
            "source_path": "docs/example.md",
        },
    )

    assert len(sent) == 1
    content_part = sent[0].split("CONTENT", 1)[1]
    assert '"page_ref": doc_page:\u27e8page-example\u27e9' in content_part
    assert '"section_ref": doc_section:\u27e8section-example\u27e9' in content_part
    assert '"page_id"' not in content_part
    assert '"section_id"' not in content_part
    assert '"page_ref": "' not in content_part
    assert '"section_ref": "' not in content_part


@pytest.mark.unit
def test_apply_update_doc_section_page_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """apply_update for doc_section also remaps page_id to page_ref (#2577)."""
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_update(
        "doc_section",
        "section-upd",
        {
            "section_id": "section-upd",
            "page_id": "page-upd",
            "heading": "Updated",
            "source_path": "docs/updated.md",
        },
    )

    content_part = sent[0].split("CONTENT", 1)[1]
    assert '"page_ref": doc_page:\u27e8page-upd\u27e9' in content_part
    assert '"page_id"' not in content_part


@pytest.mark.unit
def test_apply_create_non_ref_table_payload_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tables without record-ref mappings must pass payload through unchanged (#2577 regression)."""
    sent = _capture_sql(monkeypatch)
    adapter = _make_adapter()

    adapter.apply_create(
        "repo_artifact",
        "art-1",
        {"artifact_id": "art-1", "source_path": "src/main.py"},
    )

    content_part = sent[0].split("CONTENT", 1)[1]
    assert '"artifact_id": "art-1"' in content_part
    assert '"source_path": "src/main.py"' in content_part
