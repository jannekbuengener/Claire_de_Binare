"""Workflow inventory and register drift contract tests (#3844)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "workflow_contract"


def _fixture_dir(name: str) -> Path:
    return FIXTURES_ROOT / name


def test_disk_workflow_count_matches_register_header_claim() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        control_plane_json_path=helpers.CONTROL_PLANE_REGISTER_JSON,
    )
    register_text = helpers.WORKFLOW_REGISTER_MD.read_text(encoding="utf-8")
    match = __import__("re").search(
        r"\*\*Total workflow definitions:\*\* (\d+) YAML files",
        register_text,
    )
    assert match is not None, "register header must declare total YAML workflow count"
    declared = int(match.group(1))
    assert len(scan.disk_workflows) == declared


def test_unregistered_workflows_are_explicit_findings_not_silent_pass() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        control_plane_json_path=helpers.CONTROL_PLANE_REGISTER_JSON,
    )
    assert scan.unregistered_on_disk, "expected explicit unregistered findings on current repo"
    kinds = {finding.kind for finding in scan.findings}
    assert "unregistered_workflow" in kinds
    assert set(scan.unregistered_on_disk) == helpers.KNOWN_UNREGISTERED_WORKFLOWS


def test_register_has_no_missing_on_disk_workflows() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        control_plane_json_path=helpers.CONTROL_PLANE_REGISTER_JSON,
    )
    assert scan.missing_on_disk == ()


def test_control_plane_register_paths_exist_on_disk() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=helpers.WORKFLOWS_DIR,
        register_md_path=helpers.WORKFLOW_REGISTER_MD,
        control_plane_json_path=helpers.CONTROL_PLANE_REGISTER_JSON,
    )
    assert scan.control_plane_missing_on_disk == ()
    assert scan.control_plane_workflows


def test_control_plane_register_is_partial_coverage_by_design() -> None:
    payload = json.loads(helpers.CONTROL_PLANE_REGISTER_JSON.read_text(encoding="utf-8"))
    assert payload.get("coverage") == "partial"
    assert payload.get("catalog_scope") == "control-plane-sprint1"
    disk_count = len(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))
    assert payload.get("unit_count", 0) < disk_count


@pytest.mark.parametrize(
    "filename,expected_status_keyword",
    [
        ("ci.yml", "aktiv"),
        ("ci.yaml", "historisch"),
        ("control_board_auto_routing.yml", "parked"),
        ("control-board-routing-label-dispatch.yml", "parked"),
        ("gemini-scheduled-triage.yml", "parked"),
        ("gemini-invoke.yml", "aktiv"),
    ],
)
def test_register_classifies_known_workflow_status(
    filename: str,
    expected_status_keyword: str,
) -> None:
    status_map = helpers.parse_register_status_map(helpers.WORKFLOW_REGISTER_MD)
    assert filename in status_map
    assert expected_status_keyword in status_map[filename]


def test_register_marks_reusable_gemini_workflows_as_wcall() -> None:
    text = helpers.WORKFLOW_REGISTER_MD.read_text(encoding="utf-8")
    assert "| `gemini-invoke.yml` | aktiv | wcall |" in text


def test_ci_yaml_is_frozen_legacy_dispatch_only() -> None:
    workflow_path = helpers.WORKFLOWS_DIR / "ci.yaml"
    content = workflow_path.read_text(encoding="utf-8")
    assert "LEGACY-FREEZE" in content
    assert "NOISE-FREEZE" in content
    assert helpers.workflow_has_only_dispatch_trigger(workflow_path)


def test_ci_yml_is_active_canonical_pr_gate() -> None:
    workflow_path = helpers.WORKFLOWS_DIR / helpers.ACTIVE_CANONICAL_CI_WORKFLOW
    workflow = helpers.load_workflow_yaml(workflow_path)
    triggers = helpers.extract_on_triggers(workflow)
    assert "pull_request" in triggers
    assert "push" in triggers
    assert workflow_path.name != "ci.yaml"


def test_fixture_detects_unregistered_workflow_drift() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=_fixture_dir("inventory_drift"),
        register_md_path=_fixture_dir("inventory_drift") / "GITHUB_WORKFLOW_REGISTER.md",
        control_plane_json_path=_fixture_dir("inventory_drift") / "workflow-register.json",
    )
    assert scan.unregistered_on_disk == ("orphan.yml",)
    assert any(f.kind == "unregistered_workflow" for f in scan.findings)


def test_fixture_detects_register_missing_file_drift() -> None:
    scan = helpers.scan_workflow_inventory(
        workflows_dir=_fixture_dir("register_missing_file"),
        register_md_path=_fixture_dir("register_missing_file") / "GITHUB_WORKFLOW_REGISTER.md",
        control_plane_json_path=_fixture_dir("register_missing_file") / "workflow-register.json",
    )
    assert scan.missing_on_disk == ("ghost.yml",)
    assert any(f.kind == "register_missing_file" for f in scan.findings)
