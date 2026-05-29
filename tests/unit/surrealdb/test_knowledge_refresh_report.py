"""Unit tests for knowledge_refresh_report.py — Knowledge Refresh Loop v1 (#2717)."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

from tools.surrealdb.knowledge_refresh_cli import EXIT_ERROR, EXIT_OK, main
from tools.surrealdb.knowledge_refresh_report import (
    CLASSIFICATIONS,
    GUARDRAILS,
    SCHEMA_VERSION,
    classify_finding,
    generate_knowledge_refresh_report_v1,
    is_canon_protected,
)

pytestmark = pytest.mark.unit

_AS_OF = "2026-05-06T12:00:00+00:00"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "surrealdb"
    / "knowledge_refresh"
    / "sample_bundle.json"
)


def _load_fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _minimal_bundle(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "meta": {"scope_id": "test-scope", "level": "domain", "as_of": _AS_OF},
        "sources": [],
        "decisions": [],
        "evidence_records": [],
        "memory_records": [],
        "dependency_edges": [],
        "context_packages": [],
        "briefings": [],
    }
    base.update(overrides)
    return base


@pytest.mark.unit
def test_is_canon_protected_paths() -> None:
    assert is_canon_protected("AGENTS.md")
    assert is_canon_protected("agents/AGENTS.md")
    assert is_canon_protected("knowledge/governance/CDB_CONSTITUTION.md")
    assert is_canon_protected("docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md")
    assert not is_canon_protected("docs/scratch/unowned-notes.md")


@pytest.mark.unit
def test_canon_protected_stale_never_archive() -> None:
    bundle = _minimal_bundle(
        sources=[
            {
                "source_id": "s1",
                "path": "AGENTS.md",
                "current_hash": "a",
                "last_verified_hash": "b",
                "exists": True,
            }
        ]
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    agent_item = next(i for i in report.items if i.target_ref == "AGENTS.md")
    assert agent_item.classification == "refresh_required"
    assert agent_item.canon_protected is True
    assert agent_item.write_authorized is False
    assert agent_item.classification != "archive_candidate"


@pytest.mark.unit
def test_deleted_non_canon_source_archive_or_issue() -> None:
    bundle = _minimal_bundle(
        sources=[
            {
                "source_id": "s1",
                "path": "docs/deprecated/old-runbook.md",
                "exists": False,
            }
        ]
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    item = next(i for i in report.items if "old-runbook" in i.target_ref)
    assert item.classification in {"archive_candidate", "needs_issue_proposal"}
    assert item.canon_protected is False
    assert item.write_authorized is False


@pytest.mark.unit
def test_expired_evidence_refresh_required() -> None:
    bundle = _minimal_bundle(
        evidence_records=[
            {"evidence_id": "E-1", "expires_at": "2026-01-01T00:00:00+00:00"}
        ]
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    item = next(i for i in report.items if i.stale_type == "evidence_expired")
    assert item.classification == "refresh_required"


@pytest.mark.unit
def test_stale_memory_refresh_required() -> None:
    bundle = _minimal_bundle(
        memory_records=[
            {"memory_id": "M-1", "expires_at": "2026-01-01T00:00:00+00:00"}
        ]
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    item = next(i for i in report.items if i.stale_type == "memory_ttl_expired")
    assert item.classification == "refresh_required"


@pytest.mark.unit
def test_stale_context_package_and_briefing() -> None:
    bundle = _minimal_bundle(
        context_packages=[
            {
                "package_id": "P-1",
                "source_snapshot_id": "old",
                "current_snapshot_id": "new",
            }
        ],
        briefings=[
            {
                "briefing_id": "B-1",
                "source_snapshot_id": "old",
                "current_snapshot_id": "new",
            }
        ],
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    types = {i.stale_type for i in report.items}
    assert "stale_context_package" in types
    assert "stale_briefing" in types


@pytest.mark.unit
def test_accepted_stale_classification() -> None:
    from tools.surrealdb.stale_knowledge_scan import scan_stale_knowledge_v1

    bundle = _minimal_bundle(
        sources=[
            {
                "source_id": "s1",
                "path": "docs/architecture/legacy-note.md",
                "current_hash": "a",
                "last_verified_hash": "b",
                "exists": True,
            }
        ]
    )
    scan = scan_stale_knowledge_v1(bundle, as_of=_AS_OF)
    finding = next(f for f in scan.findings if f.stale_type == "source_hash_changed")
    finding = finding.__class__(
        **{**finding.__dict__, "status": "accepted_stale", "blocking": False}
    )
    assert classify_finding(finding, None, []) == "stale_but_accepted"


@pytest.mark.unit
def test_mixed_stale_quality_architect_fixture() -> None:
    report = generate_knowledge_refresh_report_v1(_load_fixture(), as_of=_AS_OF)
    assert report.status == "ok"
    assert report.classification_summary["refresh_required"] >= 1
    mixed = next(
        (i for i in report.items if "stale_knowledge_scan.py" in i.target_ref),
        None,
    )
    assert mixed is not None
    assert mixed.classification == "refresh_required"
    assert report.quality.get("overall_grade")
    assert report.architect_signals.get("total_signals", 0) >= 0


@pytest.mark.unit
def test_orphan_candidate_detection() -> None:
    bundle = _minimal_bundle(
        sources=[{"source_id": "o1", "path": "docs/scratch/unowned-notes.md", "exists": True}]
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    orphan = next(
        (i for i in report.items if i.classification == "orphan_candidate"),
        None,
    )
    assert orphan is not None
    assert orphan.target_ref == "docs/scratch/unowned-notes.md"


@pytest.mark.unit
def test_all_plan_items_write_authorized_false() -> None:
    report = generate_knowledge_refresh_report_v1(_load_fixture(), as_of=_AS_OF)
    assert all(item.write_authorized is False for item in report.items)
    assert report.refresh_plan["write_authorized"] is False


@pytest.mark.unit
def test_issue_proposal_text_only() -> None:
    bundle = _minimal_bundle(
        sources=[{"source_id": "s1", "path": "docs/deprecated/gone.md", "exists": False}]
    )
    report = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF)
    proposals = [i for i in report.items if i.issue_proposal]
    assert proposals
    assert "NOT auto-created" in proposals[0].issue_proposal


@pytest.mark.unit
def test_deterministic_json_output() -> None:
    bundle = _load_fixture()
    first = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF).to_json()
    second = generate_knowledge_refresh_report_v1(bundle, as_of=_AS_OF).to_json()
    assert first == second


@pytest.mark.unit
def test_markdown_output_operator_friendly() -> None:
    report = generate_knowledge_refresh_report_v1(_load_fixture(), as_of=_AS_OF)
    md = report.to_markdown()
    assert "# Knowledge Refresh Loop Report" in md
    assert "## Guardrails" in md
    for guardrail in GUARDRAILS[:2]:
        assert guardrail in md


@pytest.mark.unit
def test_schema_and_classifications_present() -> None:
    report = generate_knowledge_refresh_report_v1(_load_fixture(), as_of=_AS_OF)
    data = report.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    assert set(data["classification_summary"].keys()).issubset(CLASSIFICATIONS)


@pytest.mark.unit
def test_no_forbidden_imports_in_report_module() -> None:
    import tools.surrealdb.knowledge_refresh_report as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("surrealdb", "requests", "httpx", "subprocess"):
        assert f"import {forbidden}" not in source


@pytest.mark.unit
def test_cli_report_json(tmp_path: Path, capsys) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_load_fixture()), encoding="utf-8")
    exit_code = main(
        [
            "--format",
            "json",
            "report-knowledge-refresh",
            "--input",
            str(bundle_path),
            "--as-of",
            _AS_OF,
        ]
    )
    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["status"] == "ok"


@pytest.mark.unit
def test_cli_report_markdown(tmp_path: Path, capsys) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_minimal_bundle()), encoding="utf-8")
    exit_code = main(
        [
            "--format",
            "markdown",
            "report-knowledge-refresh",
            "--input",
            str(bundle_path),
            "--as-of",
            _AS_OF,
        ]
    )
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "Knowledge Refresh Loop Report" in out


@pytest.mark.unit
def test_cli_missing_input_exit_2(capsys) -> None:
    exit_code = main(
        [
            "report-knowledge-refresh",
            "--input",
            "does-not-exist-bundle.json",
        ]
    )
    assert exit_code == EXIT_ERROR


@pytest.mark.unit
def test_pure_report_path_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("network call attempted")

    monkeypatch.setattr(socket, "socket", _fail)
    report = generate_knowledge_refresh_report_v1(_load_fixture(), as_of=_AS_OF)
    assert report.report_id
