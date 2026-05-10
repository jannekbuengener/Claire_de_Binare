"""Unit tests for stale_context_cli.py — Stale Context CLI v1.

Issues:
    #2155 — [SURREALDB][CONTEXT][STALE-CLI] Add stale context CLI
    Parent: #2153 (Wave-16 anchor)
    Depends on: #2154 (stale_knowledge_scan service, merged via PR #2368)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/stale_context_cli.py.
    All fixtures are inline (tmp_path — no file loading overhead, no secrets).
    No DB access.  No SurrealDB SDK.  No MCP.  No networking.  No writes.
    No real datetime.now() — as_of from bundle meta; scan service uses cdb_utcnow.

Coverage:
    - scan-stale-context JSON and Markdown output
    - show-stale-context found and not-found (exit 3)
    - report-stale-context JSON and Markdown
    - --fail-on-blocking: exit 1 when blocking, exit 0 when no blocking
    - invalid bundle path → exit 2
    - invalid JSON → exit 2
    - not a JSON object → exit 2
    - guardrails appear in Markdown output
    - CLI does not write any file
    - deterministic output with same fixture
    - severity_summary and stale_type_summary present in report
    - blocking finding surfaced without --fail-on-blocking
    - as_of comes from bundle meta, not CLI wall-clock
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.surrealdb.stale_context_cli import (
    EXIT_BLOCKING,
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    main,
)
from tools.surrealdb.stale_knowledge_scan import StaleKnowledgeScanResult

# ── Fixed timestamps for determinism ─────────────────────────────────────────

_AS_OF = "2026-05-06T12:00:00+00:00"

# ── Inline fixtures ───────────────────────────────────────────────────────────

# source_deleted (exists=False) → severity=blocking → blocking=True
_BLOCKING_BUNDLE: dict = {
    "meta": {"as_of": _AS_OF},
    "sources": [
        {"source_id": "src-gone-cli", "exists": False}
    ],
}

# source_hash_changed → severity=warning → blocking=False
_WARNING_BUNDLE: dict = {
    "meta": {"as_of": _AS_OF},
    "sources": [
        {
            "source_id": "src-hash-cli",
            "path": "docs/test/api.md",
            "current_hash": "newnewhash",
            "last_verified_hash": "oldoldhash",
        }
    ],
}

# Empty bundle → 0 findings
_CLEAN_BUNDLE: dict = {}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_bundle(tmp_path: Path, bundle: dict, name: str = "bundle.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps(bundle), encoding="utf-8")
    return str(p)


def _read_json(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


# ── scan-stale-context: JSON ──────────────────────────────────────────────────


@pytest.mark.unit
def test_scan_stale_context_json(tmp_path: Path, capsys) -> None:
    """scan-stale-context JSON: required fields, status=ok, exit 0."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(["--format", "json", "scan-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "scan-stale-context"
    assert "findings" in payload
    assert "blocking_count" in payload
    assert "total_count" in payload
    assert "as_of" in payload
    assert "schema_version" in payload
    assert "severity_summary" in payload
    assert "recommended_refresh" in payload
    assert "guardrails" in payload
    assert isinstance(payload["findings"], list)
    assert isinstance(payload["guardrails"], list)
    assert len(payload["guardrails"]) >= 1


@pytest.mark.unit
def test_scan_stale_context_json_blocking_bundle(tmp_path: Path, capsys) -> None:
    """scan-stale-context JSON with blocking bundle: blocking_count > 0, exit 0 without flag."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["blocking_count"] >= 1
    assert payload["total_count"] >= 1


# ── scan-stale-context: Markdown ──────────────────────────────────────────────


@pytest.mark.unit
def test_scan_stale_context_markdown(tmp_path: Path, capsys) -> None:
    """scan-stale-context Markdown: title, severity summary, guardrails present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["--format", "markdown", "scan-stale-context", "--input", bundle_path])
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK  # no --fail-on-blocking
    assert "# Stale Context Scan" in out
    assert "scan-stale-context" in out
    assert "## Severity Summary" in out
    assert "Guardrail" in out


@pytest.mark.unit
def test_scan_stale_context_markdown_guardrail_text(tmp_path: Path, capsys) -> None:
    """scan-stale-context Markdown: at least one guardrail string appears."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["--format", "markdown", "scan-stale-context", "--input", bundle_path])
    out = capsys.readouterr().out

    # The footer guardrail note must be present
    assert "LR status remains NO-GO" in out or "Guardrail" in out
    # The ## Guardrails section must be present
    assert "## Guardrails" in out


# ── scan-stale-context: blocking finding surfaced ─────────────────────────────


@pytest.mark.unit
def test_scan_stale_context_blocking_finding_surfaced(tmp_path: Path, capsys) -> None:
    """Blocking finding appears in output even without --fail-on-blocking."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    blocking = [f for f in payload["findings"] if f["blocking"]]
    assert len(blocking) >= 1
    assert exit_code == EXIT_OK  # surfaced but not forced exit


# ── fail-on-blocking ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_fail_on_blocking_exits_1(tmp_path: Path, capsys) -> None:
    """--fail-on-blocking with blocking findings → exit 1."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["scan-stale-context", "--input", bundle_path, "--fail-on-blocking"])
    payload = _read_json(capsys)

    assert exit_code == EXIT_BLOCKING
    assert payload["status"] == "ok"
    assert payload["blocking_count"] > 0


@pytest.mark.unit
def test_fail_on_blocking_no_findings_exits_0(tmp_path: Path, capsys) -> None:
    """--fail-on-blocking with clean bundle → exit 0."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(["scan-stale-context", "--input", bundle_path, "--fail-on-blocking"])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["blocking_count"] == 0


@pytest.mark.unit
def test_fail_on_blocking_warning_only_exits_0(tmp_path: Path, capsys) -> None:
    """--fail-on-blocking with warning (non-blocking) findings only → exit 0."""
    bundle_path = _write_bundle(tmp_path, _WARNING_BUNDLE)
    exit_code = main(["scan-stale-context", "--input", bundle_path, "--fail-on-blocking"])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["blocking_count"] == 0
    assert payload["total_count"] >= 1


# ── show-stale-context ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_show_stale_context_found(tmp_path: Path, capsys) -> None:
    """show-stale-context: found by stale_id → status=ok, finding present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    # Discover stale_id via scan
    main(["scan-stale-context", "--input", bundle_path])
    scan_payload = _read_json(capsys)
    blocking_findings = [f for f in scan_payload["findings"] if f["blocking"]]
    assert blocking_findings, "test precondition: need at least one blocking finding"
    known_id = blocking_findings[0]["stale_id"]

    # Show by stale_id
    exit_code = main(["show-stale-context", "--input", bundle_path, "--stale-id", known_id])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "show-stale-context"
    assert "finding" in payload
    assert payload["finding"]["stale_id"] == known_id
    assert "as_of" in payload
    assert "schema_version" in payload


@pytest.mark.unit
def test_show_stale_context_not_found_exits_3(tmp_path: Path, capsys) -> None:
    """show-stale-context: unknown stale_id → exit 3, status=error."""
    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    exit_code = main(
        ["show-stale-context", "--input", bundle_path, "--stale-id", "nonexistent-id"]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_NOT_FOUND
    assert payload["status"] == "error"
    assert "nonexistent-id" in payload["message"]


@pytest.mark.unit
def test_show_stale_context_format_markdown(tmp_path: Path, capsys) -> None:
    """show-stale-context Markdown: title, Finding section, guardrail present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    # Discover stale_id
    main(["scan-stale-context", "--input", bundle_path])
    scan_payload = _read_json(capsys)
    known_id = [f for f in scan_payload["findings"] if f["blocking"]][0]["stale_id"]

    exit_code = main(
        ["--format", "markdown", "show-stale-context", "--input", bundle_path, "--stale-id", known_id]
    )
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK
    assert "# Stale Context Scan" in out
    assert known_id in out
    assert "## Finding" in out
    assert "Guardrail" in out


# ── report-stale-context: JSON ────────────────────────────────────────────────


@pytest.mark.unit
def test_report_stale_context_json(tmp_path: Path, capsys) -> None:
    """report-stale-context JSON: all required fields, status=ok."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["report-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    assert exit_code == EXIT_OK
    assert payload["status"] == "ok"
    assert payload["command"] == "report-stale-context"
    assert "total_count" in payload
    assert "blocking_count" in payload
    assert "severity_summary" in payload
    assert "stale_type_summary" in payload
    assert "blocking_findings" in payload
    assert "recommended_refresh" in payload
    assert "guardrails" in payload
    assert "as_of" in payload
    assert "schema_version" in payload


@pytest.mark.unit
def test_report_stale_context_severity_summary(tmp_path: Path, capsys) -> None:
    """report-stale-context: severity_summary has all three levels, counts match."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["report-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    sev = payload["severity_summary"]
    assert "info" in sev
    assert "warning" in sev
    assert "blocking" in sev
    assert sev["blocking"] == payload["blocking_count"]
    assert sum(sev.values()) == payload["total_count"]


@pytest.mark.unit
def test_report_stale_context_stale_type_summary(tmp_path: Path, capsys) -> None:
    """report-stale-context: stale_type_summary has all 8 stale types."""
    from tools.surrealdb.stale_knowledge_scan import STALE_TYPES

    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["report-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    st = payload["stale_type_summary"]
    for t in STALE_TYPES:
        assert t in st, f"missing stale_type key: {t}"
        assert isinstance(st[t], int)
        assert st[t] >= 0


@pytest.mark.unit
def test_report_stale_context_blocking_findings_list(tmp_path: Path, capsys) -> None:
    """report-stale-context: blocking_findings lists all blocking findings."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["report-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    assert len(payload["blocking_findings"]) == payload["blocking_count"]
    for f in payload["blocking_findings"]:
        assert f["blocking"] is True


@pytest.mark.unit
def test_report_stale_context_guardrails_list(tmp_path: Path, capsys) -> None:
    """report-stale-context: guardrails is a non-empty list of strings."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["report-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    gs = payload["guardrails"]
    assert isinstance(gs, list)
    assert len(gs) >= 1
    for g in gs:
        assert isinstance(g, str)
        assert g.strip() != ""


# ── report-stale-context: Markdown ───────────────────────────────────────────


@pytest.mark.unit
def test_report_stale_context_markdown(tmp_path: Path, capsys) -> None:
    """report-stale-context Markdown: required sections present."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    exit_code = main(["--format", "markdown", "report-stale-context", "--input", bundle_path])
    out = capsys.readouterr().out

    assert exit_code == EXIT_OK
    assert "# Stale Context Scan" in out
    assert "report-stale-context" in out
    assert "## Severity Summary" in out
    assert "## Stale Type Summary" in out
    assert "## Guardrails" in out
    assert "Guardrail" in out


@pytest.mark.unit
def test_report_stale_context_markdown_blocking_section(tmp_path: Path, capsys) -> None:
    """report-stale-context Markdown: ## Blocking Findings appears for blocking bundle."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)
    main(["--format", "markdown", "report-stale-context", "--input", bundle_path])
    out = capsys.readouterr().out

    assert "## Blocking Findings" in out


# ── Invalid input ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_invalid_bundle_path_exits_2(tmp_path: Path, capsys) -> None:
    """Missing input file → exit 2, status=error, 'not found' in message."""
    exit_code = main(
        ["scan-stale-context", "--input", str(tmp_path / "does_not_exist.json")]
    )
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "not found" in payload["message"]


@pytest.mark.unit
def test_invalid_json_exits_2(tmp_path: Path, capsys) -> None:
    """Malformed JSON file → exit 2, status=error, 'not valid JSON' in message."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    exit_code = main(["scan-stale-context", "--input", str(bad)])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "not valid JSON" in payload["message"]


@pytest.mark.unit
def test_invalid_not_dict_exits_2(tmp_path: Path, capsys) -> None:
    """JSON array input → exit 2, status=error, 'JSON object' in message."""
    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    exit_code = main(["scan-stale-context", "--input", str(arr)])
    payload = _read_json(capsys)

    assert exit_code == EXIT_ERROR
    assert payload["status"] == "error"
    assert "JSON object" in payload["message"]


# ── Guardrails in Markdown ────────────────────────────────────────────────────


@pytest.mark.unit
def test_guardrails_appear_in_markdown(tmp_path: Path, capsys) -> None:
    """scan-stale-context Markdown: all guardrail strings from service appear."""
    from tools.surrealdb.stale_knowledge_scan import GUARDRAILS

    bundle_path = _write_bundle(tmp_path, _CLEAN_BUNDLE)
    main(["--format", "markdown", "scan-stale-context", "--input", bundle_path])
    out = capsys.readouterr().out

    # At minimum, the ## Guardrails section exists
    assert "## Guardrails" in out
    # Each guardrail string should appear in the output
    for g in GUARDRAILS:
        assert g in out, f"guardrail string missing from markdown: {g!r}"


# ── No output file writes ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_output_file_writes(tmp_path: Path, capsys, monkeypatch) -> None:
    """CLI must never call Path.write_text (stdout only — no file writes)."""
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_BLOCKING_BUNDLE), encoding="utf-8")

    write_calls: list[str] = []
    original_write_text = Path.write_text

    def spy_write_text(self: Path, *args, **kwargs):  # type: ignore[override]
        write_calls.append(str(self))
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)

    main(["scan-stale-context", "--input", str(bundle_path)])
    assert write_calls == [], f"CLI unexpectedly wrote to: {write_calls}"


# ── Deterministic output ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_deterministic_output_same_fixture(tmp_path: Path, capsys) -> None:
    """Same input bundle produces identical JSON output across two independent runs."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    main(["scan-stale-context", "--input", bundle_path])
    out_a = capsys.readouterr().out.strip()

    main(["scan-stale-context", "--input", bundle_path])
    out_b = capsys.readouterr().out.strip()

    assert out_a == out_b, "CLI output is not deterministic for the same input"


@pytest.mark.unit
def test_deterministic_stale_ids_across_runs(tmp_path: Path, capsys) -> None:
    """stale_id values are identical across two independent scan runs."""
    bundle_path = _write_bundle(tmp_path, _BLOCKING_BUNDLE)

    main(["scan-stale-context", "--input", bundle_path])
    ids_a = {f["stale_id"] for f in _read_json(capsys)["findings"]}

    main(["scan-stale-context", "--input", bundle_path])
    ids_b = {f["stale_id"] for f in _read_json(capsys)["findings"]}

    assert ids_a == ids_b


# ── as_of from bundle meta ────────────────────────────────────────────────────


@pytest.mark.unit
def test_as_of_comes_from_bundle_meta(tmp_path: Path, capsys) -> None:
    """as_of in JSON output matches the bundle meta.as_of field."""
    bundle = {
        "meta": {"as_of": _AS_OF},
        "sources": [],
    }
    bundle_path = _write_bundle(tmp_path, bundle)
    main(["scan-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    assert payload["as_of"] == _AS_OF


@pytest.mark.unit
def test_meta_not_passed_to_service_as_key(tmp_path: Path, capsys) -> None:
    """meta key is stripped from bundle before passing to service (no spurious findings)."""
    bundle = {
        "meta": {"as_of": _AS_OF, "description": "test"},
    }
    bundle_path = _write_bundle(tmp_path, bundle)
    exit_code = main(["scan-stale-context", "--input", bundle_path])
    payload = _read_json(capsys)

    # meta contains no stale-triggering records; should produce 0 findings
    assert exit_code == EXIT_OK
    assert payload["total_count"] == 0


# ── Service contract ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_service_returns_scan_result(tmp_path: Path) -> None:
    """scan_stale_knowledge_v1 returns a StaleKnowledgeScanResult (read-only contract)."""
    from tools.surrealdb.stale_knowledge_scan import scan_stale_knowledge_v1

    result = scan_stale_knowledge_v1(_BLOCKING_BUNDLE, as_of=_AS_OF)
    assert isinstance(result, StaleKnowledgeScanResult)
    assert isinstance(result.findings, tuple)
    # Frozen dataclass — no mutation
    assert result.total_count == len(result.findings)
