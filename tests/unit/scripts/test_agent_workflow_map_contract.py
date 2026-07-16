"""Agent-facing workflow map contract tests."""

from __future__ import annotations

import json

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REQUIRED_ENTRY_FIELDS = frozenset(
    {
        "file", "name", "purpose", "triggers", "permissions",
        "writes_github", "has_schedule", "status",
        "required_check_producer", "registered_in_markdown_register", "risk",
    }
)


def test_agent_workflow_map_is_complete() -> None:
    payload = json.loads(helpers.AGENT_WORKFLOW_MAP_JSON.read_text(encoding="utf-8"))
    assert payload["coverage"] == "complete"
    assert payload["catalog_scope"] == "workflow-inventory"
    assert payload["entry_count"] == 57
    assert payload["disk_workflow_count"] == 57
    assert payload["register_table_count"] == 57
    assert payload["unregistered_on_disk"] == []


def test_committed_agent_map_matches_builder_output() -> None:
    committed = json.loads(helpers.AGENT_WORKFLOW_MAP_JSON.read_text(encoding="utf-8"))
    assert committed == helpers.build_agent_workflow_map()


def test_agent_map_matches_disk_and_register() -> None:
    payload = helpers.build_agent_workflow_map()
    disk = set(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))
    mapped = {entry["file"] for entry in payload["entries"]}
    assert mapped == disk
    assert all(entry["registered_in_markdown_register"] for entry in payload["entries"])


def test_entry_schema_and_statuses() -> None:
    payload = helpers.build_agent_workflow_map()
    assert {entry["status"] for entry in payload["entries"]} == {"active", "manual_only"}
    for entry in payload["entries"]:
        assert REQUIRED_ENTRY_FIELDS <= set(entry)


def test_required_check_producers_are_exact() -> None:
    payload = helpers.build_agent_workflow_map()
    producers = {entry["file"] for entry in payload["entries"] if entry["required_check_producer"]}
    assert producers == helpers.REQUIRED_CHECK_PRODUCER_FILES
    assert set(payload["required_check_contexts"]) == helpers.REQUIRED_CHECK_CONTEXTS


@pytest.mark.parametrize(
    "filename,expected_status",
    [
        ("ci.yml", "active"),
        ("policy-gate.yml", "active"),
        ("cdb-control-followup-classifier.yml", "manual_only"),
        ("required-checks-audit.yml", "manual_only"),
    ],
)
def test_known_statuses(filename: str, expected_status: str) -> None:
    assert helpers.classify_workflow_operational_status(filename) == expected_status


def test_risky_cascades_do_not_contain_removed_gemini_chain() -> None:
    payload = helpers.build_agent_workflow_map()
    assert "gemini_workflow_call_chain" not in payload["risky_cascade_families"]
    assert "label_event_cascade" in payload["risky_cascade_families"]


def test_map_builder_is_deterministic() -> None:
    assert helpers.build_agent_workflow_map() == helpers.build_agent_workflow_map()
