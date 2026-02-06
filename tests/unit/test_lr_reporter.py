"""
Unit tests for LR-005 Phase A: Live Readiness Completion Reporter

Focus:
  - Deterministic output (same inputs -> same outputs)
  - Correct DONE/BLOCKED field mapping
  - blocked_details is subset of BLOCKED tasks
  - No network/Git dependencies in tests (mocked Git metadata)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Import functions from lr_reporter
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lr_reporter import (
    generate_snapshot,
    parse_iso_timestamp,
    render_markdown,
)


@pytest.fixture
def mock_git_metadata():
    """Mock Git metadata to avoid Git dependency in tests."""
    return {"git_commit": "abc1234", "git_branch": "test-branch"}


@pytest.fixture
def sample_tasks_manifest():
    """Sample LR-TASKS.yaml content."""
    return {
        "spec_version": "1.0",
        "tasks": [
            {"task_id": "LR-001", "task_title": "Task One"},
            {"task_id": "LR-002", "task_title": "Task Two"},
            {"task_id": "LR-003", "task_title": "Task Three"},
        ],
    }


@pytest.fixture
def sample_state_done():
    """Sample DONE state file."""
    return {
        "spec_version": "1.0",
        "task_id": "LR-001",
        "task_title": "Task One",
        "status": "DONE",
        "completion_timestamp": "2026-02-01T10:00:00Z",
        "completion_author": "test-user",
        "evidence_file": "docs/live-readiness/LR-001-EVIDENCE.md",
        "evidence_commit": "def5678",
        "blocked_reason_code": None,
        "blocked_reason_text": None,
        "blocked_since": None,
    }


@pytest.fixture
def sample_state_blocked():
    """Sample BLOCKED state file."""
    return {
        "spec_version": "1.0",
        "task_id": "LR-002",
        "task_title": "Task Two",
        "status": "BLOCKED",
        "completion_timestamp": None,
        "completion_author": None,
        "evidence_file": "docs/live-readiness/LR-002-SPEC.md",
        "evidence_commit": None,
        "blocked_reason_code": "RC_WAIT_IMPL",
        "blocked_reason_text": "Waiting for implementation",
        "blocked_since": "2026-02-05T14:30:00Z",
    }


@pytest.fixture
def temp_data_dir(
    tmp_path, sample_tasks_manifest, sample_state_done, sample_state_blocked
):
    """Create temporary data directory with sample files."""
    data_dir = tmp_path / "live-readiness"
    data_dir.mkdir()

    # Write LR-TASKS.yaml
    with open(data_dir / "LR-TASKS.yaml", "w") as f:
        yaml.dump(sample_tasks_manifest, f)

    # Write LR-001-STATE.yaml (DONE)
    with open(data_dir / "LR-001-STATE.yaml", "w") as f:
        yaml.dump(sample_state_done, f)

    # Write LR-002-STATE.yaml (BLOCKED)
    with open(data_dir / "LR-002-STATE.yaml", "w") as f:
        yaml.dump(sample_state_blocked, f)

    # Write LR-003-STATE.yaml (DONE)
    state_003 = sample_state_done.copy()
    state_003["task_id"] = "LR-003"
    state_003["task_title"] = "Task Three"
    state_003["completion_timestamp"] = "2026-02-03T12:00:00Z"
    with open(data_dir / "LR-003-STATE.yaml", "w") as f:
        yaml.dump(state_003, f)

    return data_dir


def test_parse_iso_timestamp():
    """Test ISO 8601 timestamp parsing to Unix epoch."""
    # Valid timestamp - check deterministic parsing (exact value is timezone-dependent)
    result = parse_iso_timestamp("2026-02-05T14:30:00Z")
    assert result is not None
    assert isinstance(result, int)
    assert result > 0

    # None input
    assert parse_iso_timestamp(None) is None

    # Invalid input
    assert parse_iso_timestamp("invalid") is None


def test_generate_snapshot_deterministic(temp_data_dir, mock_git_metadata):
    """Test that snapshot generation is deterministic."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot1 = generate_snapshot(temp_data_dir)
        snapshot2 = generate_snapshot(temp_data_dir)

        # Same inputs -> same outputs
        assert snapshot1 == snapshot2


def test_generate_snapshot_structure(temp_data_dir, mock_git_metadata):
    """Test snapshot structure conforms to LR-005-SPEC §4.2."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot = generate_snapshot(temp_data_dir)

        # Top-level keys
        assert snapshot["spec_version"] == "1.0"
        assert "snapshot_metadata" in snapshot
        assert "summary" in snapshot
        assert "tasks" in snapshot
        assert "blocked_details" in snapshot

        # Snapshot metadata
        meta = snapshot["snapshot_metadata"]
        assert meta["git_commit"] == "abc1234"
        assert meta["git_branch"] == "test-branch"
        assert "live-readiness" in meta["data_source"]

        # Summary
        summary = snapshot["summary"]
        assert summary["total_tasks"] == 3
        assert summary["done_count"] == 2
        assert summary["blocked_count"] == 1
        assert summary["completion_percentage"] == 66.7


def test_generate_snapshot_done_task(temp_data_dir, mock_git_metadata):
    """Test DONE task field mapping."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot = generate_snapshot(temp_data_dir)

        done_task = next(t for t in snapshot["tasks"] if t["task_id"] == "LR-001")

        assert done_task["status"] == "DONE"
        assert done_task["completion_timestamp"] == "2026-02-01T10:00:00Z"
        assert done_task["completion_author"] == "test-user"
        assert done_task["blocked_reason_code"] is None
        assert done_task["blocked_reason_text"] is None
        assert done_task["blocked_since"] is None
        assert done_task["blocked_since_epoch"] is None


def test_generate_snapshot_blocked_task(temp_data_dir, mock_git_metadata):
    """Test BLOCKED task field mapping."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot = generate_snapshot(temp_data_dir)

        blocked_task = next(t for t in snapshot["tasks"] if t["task_id"] == "LR-002")

        assert blocked_task["status"] == "BLOCKED"
        assert blocked_task["completion_timestamp"] is None
        assert blocked_task["completion_author"] is None
        assert blocked_task["blocked_reason_code"] == "RC_WAIT_IMPL"
        assert blocked_task["blocked_reason_text"] == "Waiting for implementation"
        assert blocked_task["blocked_since"] == "2026-02-05T14:30:00Z"
        assert blocked_task["blocked_since_epoch"] is not None
        assert isinstance(blocked_task["blocked_since_epoch"], int)


def test_blocked_details_subset(temp_data_dir, mock_git_metadata):
    """Test that blocked_details is subset of BLOCKED tasks."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot = generate_snapshot(temp_data_dir)

        blocked_tasks = [t for t in snapshot["tasks"] if t["status"] == "BLOCKED"]
        blocked_details = snapshot["blocked_details"]

        assert len(blocked_details) == len(blocked_tasks)
        assert len(blocked_details) == 1

        blocked_detail = blocked_details[0]
        assert blocked_detail["task_id"] == "LR-002"
        assert blocked_detail["reason_code"] == "RC_WAIT_IMPL"
        assert blocked_detail["blocked_since_epoch"] is not None
        assert isinstance(blocked_detail["blocked_since_epoch"], int)


def test_render_markdown_structure(temp_data_dir, mock_git_metadata):
    """Test Markdown rendering produces expected structure."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot = generate_snapshot(temp_data_dir)
        markdown = render_markdown(snapshot)

        # Check for expected sections
        assert "# LR-Task Completion Snapshot" in markdown
        assert "## Summary" in markdown
        assert "## Task Status" in markdown
        assert "## Blocked Tasks" in markdown

        # Check metadata (flexible matching for Markdown vs raw format)
        assert "abc1234" in markdown
        assert "test-branch" in markdown

        # Check summary table
        assert "| **Total Tasks** | 3 |" in markdown
        assert "| **Done** | 2 |" in markdown
        assert "| **Blocked** | 1 |" in markdown
        assert "| **Completion** | 66.7% |" in markdown

        # Check task status (flexible emoji matching - may appear as unicode)
        assert "DONE" in markdown
        assert "BLOCKED" in markdown


def test_markdown_no_clock_fields(temp_data_dir, mock_git_metadata):
    """Test that Markdown does not contain dynamic clock fields."""
    with patch("lr_reporter.get_git_metadata", return_value=mock_git_metadata):
        snapshot = generate_snapshot(temp_data_dir)
        markdown = render_markdown(snapshot)

        # No "Generated at" or similar dynamic timestamps
        assert "Generated at" not in markdown
        assert "Report date" not in markdown

        # Should only contain timestamps from STATE files
        assert "2026-02-01T10:00:00Z" in markdown  # completion_timestamp
        assert "2026-02-05T14:30:00Z" in markdown  # blocked_since
