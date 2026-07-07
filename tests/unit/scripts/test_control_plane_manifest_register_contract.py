"""Control-plane manifest and generated register contract tests (#3852)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

COLLECTION_DIR = helpers.CONTROL_PLANE_COLLECTION_DIR
GENERATED_REGISTER = helpers.CONTROL_PLANE_REGISTER_JSON
VALIDATOR = helpers.CONTROL_PLANE_VALIDATOR


def _run_validator(*extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root", str(helpers.REPO_ROOT)]
        + list(extra_args),
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("unit_dir", helpers.list_manifest_unit_dirs(), ids=lambda p: p.name)
def test_manifest_status_uses_canonical_enum(unit_dir: Path) -> None:
    manifest = helpers.load_manifest_yaml(unit_dir / "manifest.yaml")
    assert manifest.get("status") in helpers.MANIFEST_STATUS_VALUES


@pytest.mark.parametrize("unit_dir", helpers.list_manifest_unit_dirs(), ids=lambda p: p.name)
def test_manifest_required_top_level_fields(unit_dir: Path) -> None:
    manifest = helpers.load_manifest_yaml(unit_dir / "manifest.yaml")
    required = {
        "id",
        "kind",
        "status",
        "owner_surface",
        "workflow",
        "purpose",
        "control",
        "discovery",
        "tests",
    }
    missing = required - set(manifest)
    assert not missing, f"{unit_dir.name} missing fields: {sorted(missing)}"


@pytest.mark.parametrize("unit_dir", helpers.list_manifest_unit_dirs(), ids=lambda p: p.name)
def test_manifest_triggers_match_real_workflow_yaml(unit_dir: Path) -> None:
    manifest = helpers.load_manifest_yaml(unit_dir / "manifest.yaml")
    workflow_rel = (manifest.get("workflow") or {}).get("path")
    assert isinstance(workflow_rel, str)
    workflow_path = helpers.REPO_ROOT / workflow_rel
    assert workflow_path.is_file()
    assert helpers.manifest_triggers_match_yaml(manifest, workflow_path)


@pytest.mark.parametrize("unit_dir", helpers.list_manifest_unit_dirs(), ids=lambda p: p.name)
def test_manifest_permissions_match_real_workflow_yaml(unit_dir: Path) -> None:
    manifest = helpers.load_manifest_yaml(unit_dir / "manifest.yaml")
    workflow_rel = (manifest.get("workflow") or {}).get("path")
    assert isinstance(workflow_rel, str)
    workflow_path = helpers.REPO_ROOT / workflow_rel
    assert helpers.manifest_permissions_match_yaml(manifest, workflow_path)


def test_generated_register_has_no_duplicate_ids() -> None:
    payload = json.loads(GENERATED_REGISTER.read_text(encoding="utf-8"))
    ids = [unit["id"] for unit in payload.get("units") or []]
    assert len(ids) == len(set(ids))


def test_generated_register_matches_validator_output(tmp_path: Path) -> None:
    output = tmp_path / "workflow-register.json"
    result = _run_validator("--generate", "--output", str(output))
    assert result.returncode == 0, result.stderr
    generated = json.loads(output.read_text(encoding="utf-8"))
    committed = json.loads(GENERATED_REGISTER.read_text(encoding="utf-8"))
    assert generated == committed


def test_generated_register_units_sorted_by_id() -> None:
    payload = json.loads(GENERATED_REGISTER.read_text(encoding="utf-8"))
    ids = [unit["id"] for unit in payload.get("units") or []]
    assert ids == sorted(ids)


def test_control_plane_partial_coverage_surfaces_missing_units() -> None:
    disk_count = len(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))
    manifest_count = len(helpers.list_manifest_unit_dirs())
    assert manifest_count < disk_count
    assert helpers.control_plane_missing_unit_findings() == ()


def test_all_manifest_units_pass_validator() -> None:
    result = _run_validator()
    assert result.returncode == 0, (
        f"control_plane_validate failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_manifest_schema_documents_status_enum_values() -> None:
    schema_path = helpers.REPO_ROOT / ".github" / "control-plane" / "schema" / "manifest.schema.yaml"
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    status_values = set(schema["fields"]["status"]["values"])
    assert status_values == helpers.MANIFEST_STATUS_VALUES
