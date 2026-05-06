"""Unit tests for scope_drift_cli.py — Scope Drift Check CLI v1.

Issues:
    #2164 — [SURREALDB][CONTEXT][SCOPE-CLI] Add scope drift check CLI
    Parent: #2162 (Wave-17 anchor)
    Depends on: #2163 (scope_drift_firewall service, merged via PR #2376)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/scope_drift_cli.py.
    All fixtures are inline (tmp_path — no file loading overhead, no secrets).
    No DB access.  No SurrealDB SDK.  No MCP.  No networking.  No writes.
    No real datetime.now() — as_of from bundle meta; scan service uses cdb_utcnow.

Coverage:
    - scan-scope-drift JSON output (clean bundle, exit 0)
    - scan-scope-drift JSON output (blocking bundle, exit 0 without --fail-on-blocking)
    - scan-scope-drift JSON output (blocking bundle + --fail-on-blocking, exit 1)
    - scan-scope-drift Markdown output (blocking bundle)
    - scan-scope-drift Markdown: blocking findings section present
    - show-scope-drift: found (exit 0)
    - show-scope-drift: not found (exit 3)
    - report-scope-drift: JSON (drift_type_summary + blocking_findings)
    - report-scope-drift: Markdown
    - missing bundle path → exit 2
    - invalid JSON content → exit 2
    - not a JSON object (array) → exit 2
    - CLI does not write any file (no writes guardrail)
    - deterministic output with same bundle (stable service result)
    - guardrails appear in JSON and Markdown output
    - operator action (stop_conditions/blocking metadata) present for blocking scan
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.scope_drift_cli import (
    EXIT_BLOCKING,
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    main,
)

# ── Fixed timestamp for determinism ──────────────────────────────────────────

_AS_OF = "2026-05-06T12:00:00+00:00"

# ── Inline fixtures ───────────────────────────────────────────────────────────

# Triggers path_out_of_scope (blocking) + missing_human_go (blocking):
#   - declared target_paths set; touched artifact is outside declared paths
#   - operation_mode=write with no human_go_token
_BLOCKING_BUNDLE: dict = {
    "meta": {
        "as_of": _AS_OF,
        "session_id": "cli-test-blocking-001",
        "operation_mode": "write",
        "human_go_token": None,
    },
    "declared_scope": {
        "task_scope": "CLI test scope",
        "target_issue": "2164",
        "target_paths": [
            "tools/surrealdb/",
            "tests/unit/surrealdb/",
        ],
    },
    "touched_artifacts": [
        {
            "path": "services/cdb_market/service.py",
            "surface_type": "runtime",
        },
    ],
    "issue_refs": [
        {"issue_id": "2164", "state": "OPEN", "label": "Wave-17"},
    ],
    "generated_findings": [],
    "forbidden_surfaces": [],
}

# Triggers domain_out_of_scope (warning only) — non-blocking:
#   - allowed_domains declared; touched artifact surface_type not in allowed list
_WARNING_BUNDLE: dict = {
    "meta": {"as_of": _AS_OF},
    "declared_scope": {
        "target_issue": "2164",
        "allowed_domains": ["tools"],
    },
    "touched_artifacts": [
        {
            "path": "docs/some/file.md",
            "surface_type": "docs",
        },
    ],
    "issue_refs": [],
    "generated_findings": [],
    "forbidden_surfaces": [],
}

# Zero findings bundle
_CLEAN_BUNDLE: dict = {}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_bundle(tmp_path: Path, bundle: dict, name: str = "bundle.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps(bundle), encoding="utf-8")
    return str(p)


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


# ── scan-scope-drift: JSON ────────────────────────────────────────────────────


@pytest.mark.unit
def test_scan_json_clean(tmp_path: Path, capsys) -> None:
    """scan-scope-drift JSON: clean bundle → status=ok, all required fields, exit 0."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(["--format", "json", "scan-scope-drift", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "scan-scope-drift"
    assert "findings" in payload
    assert "blocking_count" in payload
    assert "total_count" in payload
    assert "scanned_at" in payload
    assert "schema_version" in payload
    assert "severity_summary" in payload
    assert "guardrails" in payload
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["guardrails"], list)
    assert len(payload["guardrails"]) >= 1
    assert payload["blocking_count"] == 0
    assert payload["total_count"] == 0


@pytest.mark.unit
def test_scan_json_blocking_no_flag(tmp_path: Path, capsys) -> None:
    """scan-scope-drift JSON: blocking bundle without --fail-on-blocking → exit 0."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-scope-drift", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["blocking_count"] >= 1
    assert payload["total_count"] >= 1
    assert any(f["human_go_required"] for f in payload["findings"])


@pytest.mark.unit
def test_scan_json_blocking_with_flag(tmp_path: Path, capsys) -> None:
    """scan-scope-drift --fail-on-blocking: blocking bundle → exit EXIT_BLOCKING (1)."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-scope-drift", "--input", bundle_path, "--fail-on-blocking"])
    _read_json(capsys)  # consume stdout

    assert exit_code == EXIT_BLOCKING


@pytest.mark.unit
def test_scan_json_no_flag_non_blocking_exit0(tmp_path: Path, capsys) -> None:
    """scan-scope-drift: warning-only bundle without --fail-on-blocking → exit 0."""
    bundle_path = _write_bundle(tmp_path, _WARNING_BUNDLE)
    exit_code = main(["scan-scope-drift", "--input", bundle_path, "--fail-on-blocking"])
    payload = _read_json(capsys)

    # warning findings present but none blocking → exit 0 even with --fail-on-blocking
    assert exit_code == EXIT_OK
    assert payload["blocking_count"] == 0


# ── scan-scope-drift: Markdown ────────────────────────────────────────────────


@pytest.mark.unit
def test_scan_markdown(tmp_path: Path, capsys) -> None:
    """scan-scope-drift Markdown: title, severity summary, guardrails present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["--format", "markdown", "scan-scope-drift", "--input", bundle_path])
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK  # no --fail-on-blocking
    assert "# Scope Drift Scan" in out
    assert "scan-scope-drift" in out
    assert "## Severity Summary" in out
    assert "Guardrail" in out


@pytest.mark.unit
def test_scan_markdown_blocking_section(tmp_path: Path, capsys) -> None:
    """scan-scope-drift Markdown: blocking findings section appears when blocking exists."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["--format", "markdown", "scan-scope-drift", "--input", bundle_path])
    out = capsys.readouterr().out

    assert "## Blocking Findings" in out


@pytest.mark.unit
def test_scan_markdown_operator_action(tmp_path: Path, capsys) -> None:
    """scan-scope-drift Markdown: operator action (stop/required_action) present for blocking."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["--format", "markdown", "scan-scope-drift", "--input", bundle_path])
    out = capsys.readouterr().out

    # stop_conditions or required_action must appear in Markdown blocking section
    assert "stop" in out.lower() or "request_go" in out.lower()


# ── show-scope-drift ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_show_found(tmp_path: Path, capsys) -> None:
    """show-scope-drift: valid drift_id from scan → exit 0, finding dict present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    # First get a drift_id from scan
    main(["scan-scope-drift", "--input", bundle_path])
    scan_payload = _read_json(capsys)
    assert scan_payload["findings"], "Expected at least one finding for show test"
    drift_id = scan_payload["findings"][0]["drift_id"]

    # Now show it
    exit_code = main(["show-scope-drift", "--input", bundle_path, "--drift-id", drift_id])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "show-scope-drift"
    assert "finding" in payload
    assert payload["finding"]["drift_id"] == drift_id


@pytest.mark.unit
def test_show_not_found(tmp_path: Path, capsys) -> None:
    """show-scope-drift: unknown drift_id → exit EXIT_NOT_FOUND (3)."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(
        ["show-scope-drift", "--input", bundle_path, "--drift-id", "nonexistent0000"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_NOT_FOUND
    assert payload["status"] == "error"


# ── report-scope-drift ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_report_json(tmp_path: Path, capsys) -> None:
    """report-scope-drift JSON: drift_type_summary + blocking_findings present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["report-scope-drift", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["command"] == "report-scope-drift"
    assert "drift_type_summary" in payload
    assert "blocking_findings" in payload
    assert "blocking_count" in payload
    assert "severity_summary" in payload
    assert isinstance(payload["blocking_findings"], list)
    assert isinstance(payload["drift_type_summary"], dict)
    # Blocking bundle must have at least one blocking finding in report
    assert payload["blocking_count"] >= 1
    assert len(payload["blocking_findings"]) >= 1


@pytest.mark.unit
def test_report_markdown(tmp_path: Path, capsys) -> None:
    """report-scope-drift Markdown: header and drift type summary present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["--format", "markdown", "report-scope-drift", "--input", bundle_path])
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK
    assert "# Scope Drift Scan" in out
    assert "report-scope-drift" in out
    assert "## Drift Type Summary" in out
    assert "## Blocking Findings" in out
    assert "Guardrail" in out


# ── Error cases ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_missing_bundle_exit2(tmp_path: Path, capsys) -> None:
    """Missing bundle file → exit EXIT_ERROR (2)."""
    nonexistent = str(tmp_path / "does_not_exist.json")
    exit_code = main(["scan-scope-drift", "--input", nonexistent])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "CLI_ERROR" in payload.get("error", "")


@pytest.mark.unit
def test_invalid_json_exit2(tmp_path: Path, capsys) -> None:
    """Invalid JSON content → exit EXIT_ERROR (2)."""
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{not valid json!!!", encoding="utf-8")
    exit_code = main(["scan-scope-drift", "--input", str(bad_path)])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"


@pytest.mark.unit
def test_not_a_dict_exit2(tmp_path: Path, capsys) -> None:
    """JSON array (not a dict) → exit EXIT_ERROR (2)."""
    array_path = tmp_path / "array.json"
    array_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    exit_code = main(["scan-scope-drift", "--input", str(array_path)])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"


# ── Safety / guardrails ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_file_writes(tmp_path: Path, capsys) -> None:
    """CLI scan must not create any extra files in tmp_path."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    files_before = set(tmp_path.iterdir())

    main(["scan-scope-drift", "--input", bundle_path])
    capsys.readouterr()  # discard stdout

    files_after = set(tmp_path.iterdir())
    assert files_after == files_before, (
        f"CLI created unexpected files: {files_after - files_before}"
    )


@pytest.mark.unit
def test_service_result_stable(tmp_path: Path, capsys) -> None:
    """Same bundle must produce identical JSON output on successive calls (determinism)."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    main(["scan-scope-drift", "--input", bundle_path])
    first = capsys.readouterr().out.strip()

    main(["scan-scope-drift", "--input", bundle_path])
    second = capsys.readouterr().out.strip()

    assert first == second, "CLI output must be deterministic for the same input"


@pytest.mark.unit
def test_guardrails_in_json(tmp_path: Path, capsys) -> None:
    """Guardrails list must appear in JSON output."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    main(["scan-scope-drift", "--input", bundle_path])
    payload = _read_json(capsys)

    assert "guardrails" in payload
    assert len(payload["guardrails"]) >= 1
    guardrail_text = " ".join(payload["guardrails"])
    assert "signal" in guardrail_text.lower() or "no auto-fix" in guardrail_text.lower()


@pytest.mark.unit
def test_guardrails_in_markdown(tmp_path: Path, capsys) -> None:
    """Guardrails section must appear in Markdown output."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    main(["--format", "markdown", "scan-scope-drift", "--input", bundle_path])
    out = capsys.readouterr().out

    assert "## Guardrails" in out
    assert "⚠" in out  # guardrail note always appended


@pytest.mark.unit
def test_as_of_from_bundle_meta(tmp_path: Path, capsys) -> None:
    """scanned_at in output must reflect the as_of from bundle meta."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["scan-scope-drift", "--input", bundle_path])
    payload = _read_json(capsys)

    # The service uses as_of from bundle.meta.as_of when provided
    assert payload["scanned_at"] == _AS_OF


@pytest.mark.unit
def test_report_drift_type_summary_has_all_types(tmp_path: Path, capsys) -> None:
    """report-scope-drift drift_type_summary must include all known drift types."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    main(["report-scope-drift", "--input", bundle_path])
    payload = _read_json(capsys)

    from tools.surrealdb.scope_drift_firewall import DRIFT_TYPES

    dt_summary = payload["drift_type_summary"]
    for dt in DRIFT_TYPES:
        assert dt in dt_summary, f"Missing drift_type '{dt}' in drift_type_summary"
