"""Contract tests for audit_trail_t4_proof CLI — no network (#2759)."""

from __future__ import annotations

import json

import pytest

from tools.surrealdb.audit_trail_t4_common import (
    T4_ENDPOINT_CLASS,
    T4_WRITE_PROOF_BLOCKED_CODE,
    T4_WRITE_PROOF_BLOCKED_MESSAGE,
)
from tools.surrealdb.audit_trail_t4_proof import _write_proof_row_status, run_proof


@pytest.mark.unit
def test_write_proof_row_skipped_by_default() -> None:
    status = _write_proof_row_status(write_proof_row=False)
    assert status["write_proof_row_requested"] == "no"
    assert status["write_proof_row_status"] == "skipped"
    assert status["proof_row_written"] == "no"


@pytest.mark.unit
def test_write_proof_row_refused_until_hgw_authorized() -> None:
    status = _write_proof_row_status(write_proof_row=True)
    assert status["write_proof_row_requested"] == "yes"
    assert status["write_proof_row_status"] == "refused"
    assert status["write_proof_row_blocked_code"] == T4_WRITE_PROOF_BLOCKED_CODE
    assert status["write_proof_row_blocked_message"] == T4_WRITE_PROOF_BLOCKED_MESSAGE
    assert status["proof_row_written"] == "no"
    assert status["agent_memory_written"] == "no"


@pytest.mark.unit
def test_check_env_only_matrix_passes(tmp_path, monkeypatch) -> None:
    secrets = tmp_path / ".secrets" / ".cdb"
    secrets.mkdir(parents=True)
    env_file = secrets / "SURREALDB_AUDIT_TRAIL_ENV"
    env_file.write_text(
        "\n".join(
            [
                "SURREAL_URL=https://audit-trail.example:8011",
                "SURREAL_NS=cdb",
                "SURREAL_DB=audit_trail",
                "SURREAL_USER=audit_writer",
                "SURREAL_PASS=redacted",
            ]
        ),
        encoding="utf-8",
    )
    tls_dir = secrets / "audit_trail_tls"
    tls_dir.mkdir()
    (tls_dir / "cert.pem").write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("SECRETS_PATH", str(secrets))
    matrix = run_proof(
        secrets_path=str(secrets),
        write_proof_row=False,
        check_env_only=True,
    )
    assert matrix["endpoint_class"] == T4_ENDPOINT_CLASS
    assert matrix["pass"] is True
    assert matrix["env_structure"] == "ok"


@pytest.mark.unit
def test_check_env_only_write_proof_row_still_fails_without_hgw_env(
    tmp_path, monkeypatch
) -> None:
    secrets = tmp_path / ".secrets" / ".cdb"
    secrets.mkdir(parents=True)
    env_file = secrets / "SURREALDB_AUDIT_TRAIL_ENV"
    env_file.write_text(
        "\n".join(
            [
                "SURREAL_URL=https://audit-trail.example:8011",
                "SURREAL_NS=cdb",
                "SURREAL_DB=audit_trail",
                "SURREAL_USER=audit_writer",
                "SURREAL_PASS=redacted",
            ]
        ),
        encoding="utf-8",
    )
    tls_dir = secrets / "audit_trail_tls"
    tls_dir.mkdir()
    (tls_dir / "cert.pem").write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("SECRETS_PATH", str(secrets))
    matrix = run_proof(
        secrets_path=str(secrets),
        write_proof_row=True,
        check_env_only=True,
    )
    assert matrix["write_proof_row_status"] == "refused"
    assert matrix["pass"] is False
    assert "write_proof_row_blocked" in matrix["failures"]


@pytest.mark.unit
def test_t4_endpoint_fingerprint_differs_from_t3() -> None:
    from tools.surrealdb.audit_trail_t4_common import (
        endpoint_fingerprint as t4_fingerprint,
    )
    from tools.surrealdb.audit_trail_t3_common import (
        endpoint_fingerprint as t3_fingerprint,
    )

    assert t4_fingerprint(ns="cdb", db="audit_trail") != t3_fingerprint(
        ns="cdb", db="audit_trail"
    )


@pytest.mark.unit
def test_wrong_namespace_fails_matrix(tmp_path, monkeypatch) -> None:
    secrets = tmp_path / ".secrets" / ".cdb"
    secrets.mkdir(parents=True)
    env_file = secrets / "SURREALDB_AUDIT_TRAIL_ENV"
    env_file.write_text(
        "\n".join(
            [
                "SURREAL_URL=https://audit-trail.example:8011",
                "SURREAL_NS=wrong_ns",
                "SURREAL_DB=audit_trail",
                "SURREAL_USER=audit_writer",
                "SURREAL_PASS=redacted",
            ]
        ),
        encoding="utf-8",
    )
    tls_dir = secrets / "audit_trail_tls"
    tls_dir.mkdir()
    (tls_dir / "cert.pem").write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("SECRETS_PATH", str(secrets))

    def fake_health(*args, **kwargs):
        return True

    def fake_guard(url):
        return "audit-trail.example"

    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.build_ssl_context",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.health_check",
        fake_health,
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.guard_non_localhost",
        fake_guard,
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof._table_exists",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.container_network_names",
        lambda *_args, **_kwargs: (True, {"audit_trail_net"}),
    )

    matrix = run_proof(
        secrets_path=str(secrets),
        write_proof_row=False,
        check_env_only=False,
    )
    assert matrix["ns_present"] is False
    assert matrix["pass"] is False
    assert "ns_present" in matrix["failures"]


@pytest.mark.unit
def test_table_exists_rejects_statement_error(monkeypatch) -> None:
    from tools.surrealdb import audit_trail_t4_proof as proof_module

    def fake_sql(*args, **kwargs):
        body = json.dumps([{"status": "ERR", "result": "table missing"}]).encode(
            "utf-8"
        )
        return 200, body

    monkeypatch.setattr(proof_module, "sql_request", fake_sql)
    assert proof_module._table_exists(None, None, "audit_observation") is False


@pytest.mark.unit
def test_write_proof_row_fails_matrix_when_hgw_env_missing(
    tmp_path, monkeypatch
) -> None:
    secrets = tmp_path / ".secrets" / ".cdb"
    secrets.mkdir(parents=True)
    env_file = secrets / "SURREALDB_AUDIT_TRAIL_ENV"
    env_file.write_text(
        "\n".join(
            [
                "SURREAL_URL=https://audit-trail.example:8011",
                "SURREAL_NS=cdb",
                "SURREAL_DB=audit_trail",
                "SURREAL_USER=audit_writer",
                "SURREAL_PASS=redacted",
            ]
        ),
        encoding="utf-8",
    )
    tls_dir = secrets / "audit_trail_tls"
    tls_dir.mkdir()
    (tls_dir / "cert.pem").write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("SECRETS_PATH", str(secrets))

    def fake_health(*args, **kwargs):
        return True

    def fake_guard(url):
        return "audit-trail.example"

    def fake_table_exists(*args, **kwargs):
        return True

    def fake_container_names(*args, **kwargs):
        return True, {"audit_trail_net"}

    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.build_ssl_context",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.health_check",
        fake_health,
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.guard_non_localhost",
        fake_guard,
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof._table_exists",
        lambda _env, _ssl, table: table == "audit_observation",
    )
    monkeypatch.setattr(
        "tools.surrealdb.audit_trail_t4_proof.container_network_names",
        fake_container_names,
    )

    matrix = run_proof(
        secrets_path=str(secrets),
        write_proof_row=True,
        check_env_only=False,
    )
    assert matrix["write_proof_row_status"] == "refused"
    assert matrix["pass"] is False
    assert "write_proof_row_blocked" in matrix["failures"]
