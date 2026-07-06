"""Test Pack manifest and scenario catalog contract tests (#3873).

Parent #3872. Fixture/repo reads only — no Docker, no live defaults.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.unit.test_pack._test_pack_contract_helpers import (
    PACK_MANIFEST_JSON,
    PACK_MANIFEST_YAML,
    SCENARIO_CATALOG,
    TEST_PACK_ROOT,
    assert_no_live_defaults_in_text,
    collect_missing_scenario_artifacts,
    load_pack_manifest_json,
    load_pack_manifest_yaml,
    load_scenario_catalog,
    resolve_pack_relative,
    scenario_artifact_paths,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_pack_manifest_json_is_parseable() -> None:
    manifest = load_pack_manifest_json()
    assert manifest["pack_name"]
    assert "inputs" in manifest
    assert isinstance(manifest["inputs"], dict)


def test_pack_manifest_yaml_is_parseable() -> None:
    manifest = load_pack_manifest_yaml()
    assert manifest["name"] == "cdb_test_pack"
    assert manifest["version"]
    assert "operator_drills" in manifest.get("focus", [])
    assert "kill_switch_verified" in manifest.get("principles", [])


def test_scenario_catalog_is_parseable_with_unique_ids() -> None:
    catalog = load_scenario_catalog()
    scenarios = catalog.get("scenarios", [])
    assert scenarios, "catalog must list at least one scenario"
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids)), f"duplicate scenario ids: {ids}"


@pytest.mark.parametrize(
    "scenario_id",
    ["S-CHAOS-001", "S-CHAOS-002", "S-OPS-001", "S-MOCK-001"],
)
def test_catalog_scenario_ids_present(scenario_id: str) -> None:
    catalog = load_scenario_catalog()
    ids = {s["id"] for s in catalog.get("scenarios", [])}
    assert scenario_id in ids


def test_scenario_required_artifact_links_resolve_or_are_reported() -> None:
    catalog = load_scenario_catalog()
    missing = collect_missing_scenario_artifacts(catalog)
    assert missing == {}, (
        "missing scenario artifacts must be visible in contract output: "
        f"{json.dumps(missing, indent=2)}"
    )


def test_each_scenario_declares_evidence_link() -> None:
    catalog = load_scenario_catalog()
    for scenario in catalog.get("scenarios", []):
        assert scenario.get("evidence"), f"{scenario.get('id')} missing evidence link"
        assert scenario.get("intent"), f"{scenario.get('id')} missing intent"


def test_scenario_tool_and_runbook_paths_are_pack_relative() -> None:
    catalog = load_scenario_catalog()
    for scenario in catalog.get("scenarios", []):
        for rel in scenario_artifact_paths(scenario):
            assert not rel.startswith("/"), f"{scenario['id']}: absolute path {rel}"
            assert ".." not in rel, f"{scenario['id']}: parent traversal {rel}"


def test_pack_manifest_files_exist_on_disk() -> None:
    assert PACK_MANIFEST_JSON.is_file()
    assert PACK_MANIFEST_YAML.is_file()
    assert SCENARIO_CATALOG.is_file()
    assert TEST_PACK_ROOT.is_dir()


def test_scenarios_have_no_live_default_phrases() -> None:
    catalog_text = SCENARIO_CATALOG.read_text(encoding="utf-8")
    manifest_text = PACK_MANIFEST_YAML.read_text(encoding="utf-8")
    readme = (TEST_PACK_ROOT / "README.md").read_text(encoding="utf-8")
    violations: list[str] = []
    violations.extend(assert_no_live_defaults_in_text(catalog_text, label="catalog"))
    violations.extend(assert_no_live_defaults_in_text(manifest_text, label="manifest"))
    violations.extend(assert_no_live_defaults_in_text(readme, label="readme"))
    assert not violations, violations


def test_ops_scenario_points_to_operator_drill_trigger() -> None:
    catalog = load_scenario_catalog()
    ops = next(s for s in catalog["scenarios"] if s["id"] == "S-OPS-001")
    trigger_path = resolve_pack_relative(ops["trigger"])
    assert trigger_path.name == "trigger-operator-drill.ps1"
    assert trigger_path.is_file()


def test_mock_scenario_exercises_simulation_not_live_exchange() -> None:
    catalog = load_scenario_catalog()
    mock = next(s for s in catalog["scenarios"] if s["id"] == "S-MOCK-001")
    intent = mock.get("intent", "").lower()
    assert "mock" in intent or "without" in intent
    assert "real market" not in intent or "without touching real market" in intent
