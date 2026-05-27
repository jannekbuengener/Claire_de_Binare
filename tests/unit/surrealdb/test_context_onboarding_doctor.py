"""Unit tests for context onboarding doctor (#2642)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.surrealdb import context_onboarding_doctor as doctor

pytestmark = pytest.mark.unit


def test_evaluate_env_var_unset() -> None:
    assert doctor.evaluate_env_var("SECRETS_PATH", {}) == "unset"


def test_evaluate_env_var_set_invalid(tmp_path: Path) -> None:
    missing = tmp_path / "missing-dir"
    assert (
        doctor.evaluate_env_var("SECRETS_PATH", {"SECRETS_PATH": str(missing)})
        == "set_invalid"
    )


def test_evaluate_env_var_set_valid(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    assert (
        doctor.evaluate_env_var("SECRETS_PATH", {"SECRETS_PATH": str(secrets)})
        == "set_valid"
    )


def test_resolve_secrets_prefers_cdb_context_override(tmp_path: Path) -> None:
    canon = tmp_path / "canon"
    override = tmp_path / "override"
    canon.mkdir()
    override.mkdir()
    (override / "SURREALDB_ENV").write_text(
        "SURREAL_USER=root\nSURREAL_PASS=super-secret-password\n",
        encoding="utf-8",
    )
    env = {
        "SECRETS_PATH": str(canon),
        "CDB_CONTEXT_SECRETS_PATH": str(override),
    }
    resolved = doctor.resolve_secrets_dir(env)
    assert resolved.resolved_source == "CDB_CONTEXT_SECRETS_PATH"
    assert resolved.canon_store == "exists"
    assert resolved.surrealdb_env == "exists"
    assert resolved.resolved_dir == override


def test_resolve_secrets_falls_back_to_secrets_path(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=root\nSURREAL_PASS=super-secret-password\n",
        encoding="utf-8",
    )
    resolved = doctor.resolve_secrets_dir({"SECRETS_PATH": str(secrets)})
    assert resolved.resolved_source == "SECRETS_PATH"
    assert resolved.canon_store == "exists"


def test_resolve_secrets_missing_returns_none(tmp_path: Path) -> None:
    with patch.object(
        doctor, "_canon_default_secrets_dir", return_value=tmp_path / "nope"
    ):
        resolved = doctor.resolve_secrets_dir({})
    assert resolved.resolved_source == "none"
    assert resolved.canon_store == "missing"


def test_config_exists_missing(tmp_path: Path) -> None:
    report = doctor.build_report(
        tmp_path,
        skip_mcp=True,
        skip_schema=True,
        tcp_checker=lambda _h, _p, _t: False,
        environ={},
    )
    assert report.config_context_query_local == "missing"


def test_config_exists_when_present(tmp_path: Path) -> None:
    config_dir = tmp_path / "infrastructure/config/surrealdb"
    config_dir.mkdir(parents=True)
    (config_dir / "context_query.local.yaml").write_text(
        "auth_mode: none\n", encoding="utf-8"
    )
    report = doctor.build_report(
        tmp_path,
        skip_mcp=True,
        skip_schema=True,
        tcp_checker=lambda _h, _p, _t: False,
        environ={},
    )
    assert report.config_context_query_local == "exists"


def test_mcp_reachable_and_not_reachable() -> None:
    report_up = doctor.build_report(
        Path("."),
        skip_mcp=False,
        skip_schema=True,
        tcp_checker=lambda host, port, _t: host == "127.0.0.1" and port == 8811,
        http_checker=lambda _u, _t: False,
        environ={"SECRETS_PATH": "/nope"},
    )
    assert report_up.mcp_server_status == "reachable"

    report_down = doctor.build_report(
        Path("."),
        skip_mcp=False,
        skip_schema=True,
        tcp_checker=lambda _h, _p, _t: False,
        http_checker=lambda _u, _t: False,
        environ={"SECRETS_PATH": "/nope"},
    )
    assert report_down.mcp_server_status == "not_reachable"


def test_surrealdb_health_and_version_ok() -> None:
    def http_ok(url: str, _timeout: float) -> int | None:
        if url.endswith("/health") or url.endswith("/version"):
            return 200
        return None

    report = doctor.build_report(
        Path("."),
        skip_mcp=True,
        skip_schema=True,
        tcp_checker=lambda _h, port, _t: port == 8010,
        http_checker=http_ok,
        environ={"SECRETS_PATH": "/nope"},
    )
    assert report.surrealdb_status == "reachable"
    assert report.surrealdb_health == "ok"
    assert report.surrealdb_version == "ok"


def test_surrealdb_health_fail() -> None:
    report = doctor.build_report(
        Path("."),
        skip_mcp=True,
        skip_schema=True,
        tcp_checker=lambda _h, port, _t: port == 8010,
        http_checker=lambda _u, _t: None,
        environ={"SECRETS_PATH": "/nope"},
    )
    assert report.surrealdb_health == "fail"
    assert report.surrealdb_version == "fail"


def test_schema_ok_and_fail(tmp_path: Path) -> None:
    config_dir = tmp_path / "infrastructure/config/surrealdb"
    config_dir.mkdir(parents=True)
    (config_dir / "context_query.local.yaml").write_text(
        "auth_mode: root\n", encoding="utf-8"
    )

    def schema_ok(_url: str, _user: str, _password: str) -> doctor.CheckStatus:
        return "ok"

    def schema_fail(_url: str, _user: str, _password: str) -> doctor.CheckStatus:
        return "fail"

    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=root\nSURREAL_PASS=super-secret-password\n",
        encoding="utf-8",
    )
    env = {"SECRETS_PATH": str(secrets)}

    report_ok = doctor.build_report(
        tmp_path,
        skip_mcp=True,
        skip_schema=False,
        tcp_checker=lambda _h, port, _t: port == 8010,
        http_checker=lambda url, _t: (
            200 if "/health" in url or "/version" in url else None
        ),
        schema_checker=schema_ok,
        environ=env,
    )
    report_fail = doctor.build_report(
        tmp_path,
        skip_mcp=True,
        skip_schema=False,
        tcp_checker=lambda _h, port, _t: port == 8010,
        http_checker=lambda url, _t: (
            200 if "/health" in url or "/version" in url else None
        ),
        schema_checker=schema_fail,
        environ=env,
    )
    assert report_ok.surrealdb_schema == "ok"
    assert report_fail.surrealdb_schema == "fail"


@pytest.mark.parametrize(
    ("report_kwargs", "expected_action"),
    [
        (
            {"secrets_canon_store": "missing"},
            "set SECRETS_PATH or CDB_CONTEXT_SECRETS_PATH",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "missing",
            },
            "create SURREALDB_ENV from infrastructure/config/surrealdb/SURREALDB_ENV.example",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "exists",
                "config_context_query_local": "missing",
            },
            "create context_query.local.yaml from context_query.local.example.yaml",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "exists",
                "config_context_query_local": "exists",
                "surrealdb_status": "not_reachable",
            },
            "start local SurrealDB with make context-up",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "exists",
                "config_context_query_local": "exists",
                "surrealdb_status": "reachable",
                "surrealdb_health": "fail",
            },
            "start local SurrealDB with make context-up",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "exists",
                "config_context_query_local": "exists",
                "surrealdb_status": "reachable",
                "surrealdb_health": "ok",
                "surrealdb_version": "ok",
                "surrealdb_schema": "fail",
            },
            "run make context-schema-apply",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "exists",
                "config_context_query_local": "exists",
                "surrealdb_status": "reachable",
                "surrealdb_health": "ok",
                "surrealdb_version": "ok",
                "surrealdb_schema": "ok",
                "mcp_server_status": "not_reachable",
            },
            "configure MCP host for 127.0.0.1:8811 or use stdio cdb_context via claire-de-binare.mcp.json",
        ),
        (
            {
                "secrets_canon_store": "exists",
                "secrets_surrealdb_env": "exists",
                "config_context_query_local": "exists",
                "surrealdb_status": "reachable",
                "surrealdb_health": "ok",
                "surrealdb_version": "ok",
                "surrealdb_schema": "ok",
                "mcp_server_status": "reachable",
            },
            "no action required",
        ),
    ],
)
def test_prioritize_next_action(report_kwargs: dict, expected_action: str) -> None:
    report = doctor.DoctorReport(**report_kwargs)
    assert doctor.prioritize_next_action(report) == expected_action


def test_json_output_contains_no_secret_values(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=root\nSURREAL_PASS=super-secret-password\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "infrastructure/config/surrealdb"
    config_dir.mkdir(parents=True)
    (config_dir / "context_query.local.yaml").write_text(
        "auth_mode: root\n", encoding="utf-8"
    )

    report = doctor.build_report(
        tmp_path,
        skip_mcp=True,
        skip_schema=True,
        tcp_checker=lambda _h, _p, _t: False,
        environ={"SECRETS_PATH": str(secrets)},
    )
    payload = doctor.format_report(report, "json")
    assert "super-secret-password" not in payload
    assert "SURREAL_PASS" not in payload
    assert "SURREAL_USER=root" not in payload
    parsed = json.loads(payload)
    assert parsed["lr_note"] == "NO-GO"
    assert parsed["secrets"]["canon_store"] == "exists"


def test_text_output_contains_no_secret_values(tmp_path: Path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "SURREALDB_ENV").write_text(
        "SURREAL_USER=root\nSURREAL_PASS=super-secret-password\n",
        encoding="utf-8",
    )
    report = doctor.build_report(
        tmp_path,
        skip_mcp=True,
        skip_schema=True,
        tcp_checker=lambda _h, _p, _t: False,
        environ={"SECRETS_PATH": str(secrets)},
    )
    text = doctor.format_report(report, "text")
    assert "super-secret-password" not in text
    assert "SURREAL_PASS" not in text


def test_compute_exit_code_blocking_and_ok() -> None:
    blocked = doctor.DoctorReport(
        secrets_canon_store="missing",
        config_context_query_local="missing",
        surrealdb_status="not_reachable",
    )
    assert doctor.compute_exit_code(blocked) == 1

    ok = doctor.DoctorReport(
        secrets_canon_store="exists",
        secrets_surrealdb_env="exists",
        config_context_query_local="exists",
        surrealdb_status="reachable",
        surrealdb_health="ok",
        surrealdb_version="ok",
        surrealdb_schema="ok",
        mcp_server_status="not_reachable",
    )
    assert doctor.compute_exit_code(ok) == 0


def test_main_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor,
        "build_report",
        lambda *_args, **_kwargs: doctor.DoctorReport(secrets_canon_store="missing"),
    )
    assert doctor.main(["--format", "json"]) == 1

    monkeypatch.setattr(
        doctor,
        "build_report",
        lambda *_args, **_kwargs: doctor.DoctorReport(
            secrets_canon_store="exists",
            secrets_surrealdb_env="exists",
            config_context_query_local="exists",
            surrealdb_status="reachable",
            surrealdb_health="ok",
            surrealdb_version="ok",
            surrealdb_schema="ok",
        ),
    )
    assert doctor.main(["--format", "text"]) == 0

    with pytest.raises(SystemExit) as exc_info:
        doctor.main(["--format", "xml"])
    assert exc_info.value.code == 2
