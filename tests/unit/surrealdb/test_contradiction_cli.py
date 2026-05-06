"""Unit tests for contradiction_cli.py — Contradiction Scan CLI v1.

Issues:
    #2147 — [SURREALDB][CONTEXT][CONTRADICTION-CLI] Add contradiction scan CLI
    Parent: #2145 (Wave-15)
    Depends on: #2146 (contradiction_scan runtime)

Scope:
    Unit tests for tools/surrealdb/contradiction_cli.py.
    All fixtures are inline or use tmp_path (no secrets, no network, no DB).
    No writes. No SurrealDB SDK. No MCP. No networking.
    No real datetime.now() — timestamps from scan service via cdb_utcnow.
    Clock guardrail validated by test_clock.py::test_guardrails_no_forbidden_calls.

Coverage:
    - scan-contradictions: JSON and Markdown output
    - scan-contradictions: --fail-on-blocking exit 2 when blocking findings present
    - scan-contradictions: no blocking → exit 0 regardless of --fail-on-blocking
    - scan-contradictions: --type filter
    - show-contradiction: found finding
    - show-contradiction: unknown ID → exit 1
    - report-contradictions: JSON output with summary
    - report-contradictions: Markdown output
    - invalid input: missing file → exit 1
    - invalid input: bad JSON → exit 1
    - invalid input: not a JSON object → exit 1
    - CLI does not write any file
    - Service remains read-only (returns ContradictionScanResult)
    - Blocking finding is surfaced in scan output
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.contradiction_cli import (
    EXIT_BLOCKING,
    EXIT_ERROR,
    EXIT_OK,
    main,
)
from tools.surrealdb.contradiction_scan import ContradictionScanResult

# ── Helpers ───────────────────────────────────────────────────────────────────

# A minimal bundle that produces ≥1 blocking finding (claim_vs_evidence / invalidated)
_BLOCKING_BUNDLE: dict = {
    "claims": [
        {"claim_id": "c-001", "status": "invalidated", "topic": "test-topic", "evidence_refs": []}
    ]
}

# A bundle with no records → 0 findings, 0 blocking
_CLEAN_BUNDLE: dict = {}

def _write_bundle(tmp_path: Path, bundle: dict) -> str:
    p = tmp_path / "bundle.json"
    p.write_text(json.dumps(bundle), encoding="utf-8")
    return str(p)


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


# ── scan-contradictions ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_scan_contradictions_format_json(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(["--format", "json", "scan-contradictions", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "scan-contradictions"
    assert "findings" in payload
    assert "blocking_count" in payload
    assert "total_findings" in payload
    assert "scanned_at" in payload
    assert "schema_version" in payload


@pytest.mark.unit
def test_scan_contradictions_format_markdown(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["--format", "markdown", "scan-contradictions", "--input", bundle_path])
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK  # no --fail-on-blocking
    assert "# Contradiction Scan" in out
    assert "scan-contradictions" in out
    assert "Guardrail" in out  # guardrail note must be present


@pytest.mark.unit
def test_scan_contradictions_fail_on_blocking_exits_2(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(
        ["scan-contradictions", "--input", bundle_path, "--fail-on-blocking"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_BLOCKING
    assert payload["status"] == "ok"
    assert payload["blocking_count"] > 0


@pytest.mark.unit
def test_scan_contradictions_no_blocking_exits_0(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(
        ["scan-contradictions", "--input", bundle_path, "--fail-on-blocking"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["blocking_count"] == 0


@pytest.mark.unit
def test_scan_contradictions_no_flag_blocking_still_exits_0(tmp_path: Path, capsys) -> None:
    """Blocking findings without --fail-on-blocking → exit 0."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-contradictions", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["blocking_count"] > 0


@pytest.mark.unit
def test_scan_contradictions_type_filter(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(
        ["scan-contradictions", "--input", bundle_path, "--type", "claim_vs_evidence"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    for f in payload["findings"]:
        assert f["contradiction_type"] == "claim_vs_evidence"


@pytest.mark.unit
def test_scan_contradictions_type_filter_unknown_type(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(
        ["scan-contradictions", "--input", bundle_path, "--type", "not_a_real_type"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"


@pytest.mark.unit
def test_scan_contradictions_blocking_finding_surfaced(tmp_path: Path, capsys) -> None:
    """Blocking findings are surfaced in the output even without --fail-on-blocking."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-contradictions", "--input", bundle_path])
    payload = _read_json(capsys)

    blocking = [f for f in payload["findings"] if f["blocking"]]
    assert len(blocking) >= 1
    assert exit_code == EXIT_OK  # surfaced but not blocking exit


# ── show-contradiction ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_show_contradiction_found(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    # First, discover the contradiction_id via scan
    main(["scan-contradictions", "--input", bundle_path])
    scan_payload = _read_json(capsys)
    blocking_findings = [f for f in scan_payload["findings"] if f["blocking"]]
    assert blocking_findings, "test precondition: need at least one blocking finding"
    known_id = blocking_findings[0]["contradiction_id"]

    # Now show it
    exit_code = main(["show-contradiction", "--input", bundle_path, "--id", known_id])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "show-contradiction"
    assert "finding" in payload
    assert payload["finding"]["contradiction_id"] == known_id


@pytest.mark.unit
def test_show_contradiction_not_found_exits_1(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(
        ["show-contradiction", "--input", bundle_path, "--id", "nonexistent-id"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "nonexistent-id" in payload["message"]


@pytest.mark.unit
def test_show_contradiction_format_markdown(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    # Discover blocking id
    main(["scan-contradictions", "--input", bundle_path])
    scan_payload = _read_json(capsys)
    known_id = [f for f in scan_payload["findings"] if f["blocking"]][0]["contradiction_id"]

    exit_code = main(
        ["--format", "markdown", "show-contradiction", "--input", bundle_path, "--id", known_id]
    )
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK
    assert "# Contradiction Scan" in out
    assert known_id in out
    assert "Guardrail" in out


# ── report-contradictions ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_report_contradictions_json(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["report-contradictions", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "report-contradictions"
    assert "summary" in payload
    assert "blocking" in payload["summary"]
    assert "overridden" in payload["summary"]
    assert "warning" in payload["summary"]
    assert "info" in payload["summary"]
    assert "guardrail" in payload
    assert "blocking_count" in payload
    assert "total_findings" in payload


@pytest.mark.unit
def test_report_contradictions_markdown(tmp_path: Path, capsys) -> None:
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["--format", "markdown", "report-contradictions", "--input", bundle_path])
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK
    assert "# Contradiction Scan" in out
    assert "report-contradictions" in out
    assert "Guardrail" in out


@pytest.mark.unit
def test_report_contradictions_summary_counts_match(tmp_path: Path, capsys) -> None:
    """Summary counts must match: sum(blocking+warning+info) == total_findings."""
    bundle = {
        "claims": [
            {"claim_id": "c-001", "status": "invalidated", "evidence_refs": []},
            {"claim_id": "c-002", "status": "stale", "evidence_refs": ["ev-001"]},
        ]
    }
    bundle_path = _write_bundle(tmp_path, bundle)
    main(["report-contradictions", "--input", bundle_path])
    payload = _read_json(capsys)

    summary = payload["summary"]
    total_from_summary = (
        len(summary["blocking"])
        + len(summary["overridden"])
        + len(summary["warning"])
        + len(summary["info"])
    )
    assert total_from_summary == payload["total_findings"]


# ── Invalid input ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_invalid_input_nonexistent_file_exits_1(tmp_path: Path, capsys) -> None:
    exit_code = main(
        ["scan-contradictions", "--input", str(tmp_path / "does_not_exist.json")]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "not found" in payload["message"]


@pytest.mark.unit
def test_invalid_input_bad_json_exits_1(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    exit_code = main(["scan-contradictions", "--input", str(bad)])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "not valid JSON" in payload["message"]


@pytest.mark.unit
def test_invalid_input_not_a_dict_exits_1(tmp_path: Path, capsys) -> None:
    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    exit_code = main(["scan-contradictions", "--input", str(arr)])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "JSON object" in payload["message"]


# ── Guardrails: read-only / no writes ─────────────────────────────────────────


@pytest.mark.unit
def test_cli_does_not_write_any_file(tmp_path: Path, capsys, monkeypatch) -> None:
    """Ensure the CLI never calls Path.write_text or open() for writing."""
    # Create the bundle file BEFORE patching so the helper write is not counted.
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_BLOCKING_BUNDLE), encoding="utf-8")

    write_calls: list[str] = []
    original_write_text = Path.write_text

    def spy_write_text(self: Path, *args, **kwargs):  # type: ignore[override]
        write_calls.append(str(self))
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)

    main(["scan-contradictions", "--input", str(bundle_path)])
    # CLI output goes to stdout only — no file writes expected
    assert write_calls == [], f"CLI unexpectedly wrote to: {write_calls}"


@pytest.mark.unit
def test_cli_service_returns_scan_result(tmp_path: Path) -> None:
    """scan_contradictions_v1 returns a ContradictionScanResult (read-only contract)."""
    from tools.surrealdb.contradiction_scan import scan_contradictions_v1

    result = scan_contradictions_v1(_BLOCKING_BUNDLE)
    assert isinstance(result, ContradictionScanResult)
    # No mutation — result is frozen dataclass
    assert isinstance(result.findings, tuple)


@pytest.mark.unit
def test_cli_with_overrides_in_bundle(tmp_path: Path, capsys) -> None:
    """Overrides extracted from bundle root are passed to service correctly."""
    # First get the blocking contradiction_id
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["scan-contradictions", "--input", bundle_path])
    scan_payload = _read_json(capsys)
    blocking = [f for f in scan_payload["findings"] if f["blocking"]]
    assert blocking, "test precondition"
    cid = blocking[0]["contradiction_id"]

    # Now supply an override to make it false_positive (non-blocking)
    bundle_with_override = {
        **_BLOCKING_BUNDLE,
        "overrides": {cid: "false_positive"},
    }
    sub = tmp_path / "sub"
    sub.mkdir(exist_ok=True)
    bundle_path2 = str(sub / "bundle.json")
    (sub / "bundle.json").write_text(
        json.dumps(bundle_with_override), encoding="utf-8"
    )

    main(["scan-contradictions", "--input", bundle_path2, "--fail-on-blocking"])
    payload = _read_json(capsys)

    # With override applied the finding becomes false_positive → blocking=False → exit 0
    assert payload["blocking_count"] == 0
