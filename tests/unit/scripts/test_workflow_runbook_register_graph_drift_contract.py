"""Workflow runbook/register/graph drift regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]
FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "workflow_contract"


def _fixture_dir(name: str) -> Path:
    return FIXTURES_ROOT / name


def _scan() -> helpers.WorkflowDocsDriftScan:
    return helpers.scan_workflow_docs_drift(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        runbook_md_path=helpers.RUNBOOK_MD,
        graph_md_path=helpers.GRAPH_MD,
        control_plane_entrypoint_path=helpers.CONTROL_PLANE_ENTRYPOINT,
    )


def test_docs_scan_declares_only_structural_limitations() -> None:
    scan = _scan()
    assert scan.limitations
    assert any("relationship-focused" in item for item in scan.limitations)
    assert not any("not auto-fixed" in item.lower() for item in scan.limitations)


def test_operational_docs_have_no_inventory_drift() -> None:
    scan = _scan()
    assert scan.register_header_count == scan.disk_count == 57
    assert scan.register_table_count == scan.disk_count
    assert scan.control_plane_entrypoint_count_claim == scan.disk_count
    assert scan.graph_missing_on_disk == ()
    assert scan.findings == ()


def test_graph_references_active_workflows() -> None:
    scan = _scan()
    assert scan.graph_referenced_workflows
    assert {"ci.yml", "policy-gate.yml", "project_reconcile_daily.yml"} <= set(
        scan.graph_referenced_workflows
    )


def test_fixture_detects_runbook_and_graph_drift() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=_fixture_dir("docs_drift"),
        register_md_path=_fixture_dir("docs_drift") / "GITHUB_WORKFLOW_REGISTER.md",
        runbook_md_path=_fixture_dir("docs_drift") / "GITHUB_CONTROL_PLANE_RUNBOOK.md",
        graph_md_path=_fixture_dir("docs_drift") / "GITHUB_CONTROL_PLANE_GRAPH.md",
        control_plane_entrypoint_path=_fixture_dir("docs_drift") / "CONTROL_PLANE.md",
    )
    assert scan.disk_count == 2
    assert any(f.kind == "runbook_count_drift" for f in scan.findings)
    assert any(f.kind == "graph_missing_on_disk" for f in scan.findings)
    assert any(f.kind == "graph_stale_register_count_reference" for f in scan.findings)
