"""
LR-005 Schema Compliance Integration Tests

Tests that validate JSON snapshots against the LR-005-SCHEMA.json schema.

Constraints:
- No network/GitHub API calls
- No state mutations
- Deterministic validation only
"""

import json
from pathlib import Path

import jsonschema
import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_schema() -> dict:
    """Load LR-005-SCHEMA.json from docs/live-readiness."""
    schema_path = PROJECT_ROOT / "docs" / "live-readiness" / "LR-005-SCHEMA.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_example(filename: str) -> dict:
    """Load example JSON from examples/ directory."""
    example_path = PROJECT_ROOT / "examples" / filename
    with open(example_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_schema_itself_is_valid():
    """Test that LR-005-SCHEMA.json is a valid JSON Schema (Draft 7)."""
    schema = load_schema()

    # Validate against JSON Schema Draft 7 meta-schema
    jsonschema.Draft7Validator.check_schema(schema)

    # Basic structural assertions
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["title"] == "LR-005 Completion Snapshot Schema"
    assert schema["type"] == "object"
    assert "spec_version" in schema["required"]
    assert "snapshot_metadata" in schema["required"]
    assert "summary" in schema["required"]
    assert "tasks" in schema["required"]
    assert "blocked_details" in schema["required"]


def test_example_done_validates_against_schema():
    """Test that lr-snapshot-done.json validates against LR-005-SCHEMA.json."""
    schema = load_schema()
    snapshot = load_example("lr-snapshot-done.json")

    # Validate (raises ValidationError if invalid)
    jsonschema.validate(instance=snapshot, schema=schema)

    # Structural assertions
    assert snapshot["spec_version"] == "1.0"
    assert snapshot["summary"]["blocked_count"] == 0
    assert len(snapshot["blocked_details"]) == 0
    assert all(task["status"] == "DONE" for task in snapshot["tasks"])


def test_example_blocked_validates_against_schema():
    """Test that lr-snapshot-blocked.json validates against LR-005-SCHEMA.json."""
    schema = load_schema()
    snapshot = load_example("lr-snapshot-blocked.json")

    # Validate (raises ValidationError if invalid)
    jsonschema.validate(instance=snapshot, schema=schema)

    # Structural assertions
    assert snapshot["spec_version"] == "1.0"
    assert snapshot["summary"]["blocked_count"] >= 1
    assert len(snapshot["blocked_details"]) >= 1

    # Verify blocked_details is a subset of BLOCKED tasks
    blocked_task_ids = {
        task["task_id"] for task in snapshot["tasks"] if task["status"] == "BLOCKED"
    }
    blocked_detail_ids = {detail["task_id"] for detail in snapshot["blocked_details"]}
    assert blocked_detail_ids.issubset(blocked_task_ids)


def test_schema_rejects_invalid_spec_version():
    """Test that schema rejects invalid spec_version format."""
    schema = load_schema()
    invalid_snapshot = load_example("lr-snapshot-done.json")
    invalid_snapshot["spec_version"] = "v1.0"  # Invalid format (no 'v' prefix allowed)

    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(instance=invalid_snapshot, schema=schema)

    assert "spec_version" in str(excinfo.value)


def test_schema_rejects_missing_required_fields():
    """Test that schema rejects snapshots missing required top-level fields."""
    schema = load_schema()
    invalid_snapshot = load_example("lr-snapshot-done.json")
    del invalid_snapshot["summary"]  # Remove required field

    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(instance=invalid_snapshot, schema=schema)

    assert "summary" in str(excinfo.value)


def test_schema_rejects_invalid_task_id_format():
    """Test that schema rejects invalid task_id format (not LR-XXX)."""
    schema = load_schema()
    invalid_snapshot = load_example("lr-snapshot-done.json")
    invalid_snapshot["tasks"][0]["task_id"] = "LR-1"  # Invalid (missing leading zeros)

    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(instance=invalid_snapshot, schema=schema)

    assert "task_id" in str(excinfo.value) or "pattern" in str(excinfo.value)


def test_schema_rejects_invalid_git_commit_format():
    """Test that schema rejects invalid git_commit SHA format."""
    schema = load_schema()
    invalid_snapshot = load_example("lr-snapshot-done.json")
    invalid_snapshot["snapshot_metadata"]["git_commit"] = "INVALID"  # Invalid (not hex)

    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(instance=invalid_snapshot, schema=schema)

    assert "git_commit" in str(excinfo.value) or "pattern" in str(excinfo.value)


def test_schema_rejects_completion_percentage_out_of_range():
    """Test that schema rejects completion_percentage outside [0, 100]."""
    schema = load_schema()
    invalid_snapshot = load_example("lr-snapshot-done.json")
    invalid_snapshot["summary"]["completion_percentage"] = 150.0  # Invalid (> 100)

    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(instance=invalid_snapshot, schema=schema)

    assert "completion_percentage" in str(excinfo.value) or "maximum" in str(
        excinfo.value
    )


def test_schema_allows_null_evidence_commit():
    """Test that schema allows null evidence_commit (optional field)."""
    schema = load_schema()
    snapshot = load_example("lr-snapshot-done.json")
    snapshot["tasks"][0]["evidence_commit"] = None  # Should be valid

    # Should not raise
    jsonschema.validate(instance=snapshot, schema=schema)


def test_blocked_details_subset_structure():
    """Test that blocked_details has the correct subset structure."""
    snapshot = load_example("lr-snapshot-blocked.json")

    # Blocked details should have exactly these fields
    required_fields = {
        "task_id",
        "task_title",
        "reason_code",
        "reason_text",
        "blocked_since",
        "blocked_since_epoch",
    }

    for detail in snapshot["blocked_details"]:
        assert set(detail.keys()) == required_fields


def test_done_task_has_null_blocked_fields():
    """Test that DONE tasks have null blocked_* fields."""
    snapshot = load_example("lr-snapshot-done.json")

    for task in snapshot["tasks"]:
        if task["status"] == "DONE":
            assert task["blocked_reason_code"] is None
            assert task["blocked_reason_text"] is None
            assert task["blocked_since"] is None
            assert task["blocked_since_epoch"] is None


def test_blocked_task_has_null_completion_fields():
    """Test that BLOCKED tasks have null completion_* fields."""
    snapshot = load_example("lr-snapshot-blocked.json")

    for task in snapshot["tasks"]:
        if task["status"] == "BLOCKED":
            assert task["completion_timestamp"] is None
            assert task["completion_author"] is None
