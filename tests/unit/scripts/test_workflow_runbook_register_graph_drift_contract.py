"""Workflow runbook/register/graph drift regression tests (#3853)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "workflow_contract"


def _fixture_dir(name: str) -> Path:
    return FIXTURES_ROOT / name


def test_docs_drift_scan_surfaces_limitations() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        runbook_md_path=helpers.RUNBOOK_MD,
        graph_md_path=helpers.GRAPH_MD,
        control_plane_entrypoint_path=helpers.CONTROL_PLANE_ENTRYPOINT,
    )
    assert scan.limitations
    assert any("partial" in item.lower() for item in scan.limitations)
    assert any("not auto-fixed" in item.lower() for item in scan.limitations)


def test_register_header_matches_disk_count() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        runbook_md_path=helpers.RUNBOOK_MD,
        graph_md_path=helpers.GRAPH_MD,
        control_plane_entrypoint_path=helpers.CONTROL_PLANE_ENTRYPOINT,
    )
    assert scan.register_header_count == scan.disk_count
    assert not any(f.kind == "register_header_count_drift" for f in scan.findings)


def test_known_runbook_and_entrypoint_count_drifts_are_explicit_findings() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        runbook_md_path=helpers.RUNBOOK_MD,
        graph_md_path=helpers.GRAPH_MD,
        control_plane_entrypoint_path=helpers.CONTROL_PLANE_ENTRYPOINT,
    )
    kinds = {finding.kind for finding in scan.findings}
    assert "runbook_count_drift" in kinds
    assert "control_plane_entrypoint_count_drift" in kinds
    assert "graph_stale_register_count_reference" in kinds
    assert scan.runbook_count_claim == helpers.KNOWN_DOCS_COUNT_DRIFTS[
        "runbook_workflow_count"
    ][0]
    assert scan.control_plane_entrypoint_count_claim == helpers.KNOWN_DOCS_COUNT_DRIFTS[
        "control_plane_entrypoint_count"
    ][0]


def test_graph_references_do_not_point_at_missing_workflows() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        runbook_md_path=helpers.RUNBOOK_MD,
        graph_md_path=helpers.GRAPH_MD,
        control_plane_entrypoint_path=helpers.CONTROL_PLANE_ENTRYPOINT,
    )
    assert scan.graph_missing_on_disk == ()
    assert scan.graph_referenced_workflows


def test_register_table_is_partial_vs_disk_by_design() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        runbook_md_path=helpers.RUNBOOK_MD,
        graph_md_path=helpers.GRAPH_MD,
        control_plane_entrypoint_path=helpers.CONTROL_PLANE_ENTRYPOINT,
    )
    assert scan.register_table_count < scan.disk_count
    inventory = helpers.scan_workflow_inventory(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        control_plane_json_path=helpers.CONTROL_PLANE_REGISTER_JSON,
    )
    assert set(inventory.unregistered_on_disk) == helpers.KNOWN_UNREGISTERED_WORKFLOWS


def test_fixture_detects_runbook_count_drift() -> None:
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


def test_fixture_detects_graph_stale_register_reference() -> None:
    scan = helpers.scan_workflow_docs_drift(
        workflows_dir=_fixture_dir("docs_drift"),
        register_md_path=_fixture_dir("docs_drift") / "GITHUB_WORKFLOW_REGISTER.md",
        runbook_md_path=_fixture_dir("docs_drift") / "GITHUB_CONTROL_PLANE_RUNBOOK.md",
        graph_md_path=_fixture_dir("docs_drift") / "GITHUB_CONTROL_PLANE_GRAPH.md",
        control_plane_entrypoint_path=_fixture_dir("docs_drift") / "CONTROL_PLANE.md",
    )
    assert any(f.kind == "graph_stale_register_count_reference" for f in scan.findings)
