"""
Unit tests for Required Reads Resolver v1 (#2106).

Tests the resolve_required_reads function from tools.surrealdb.context_required_reads.
Pure unit tests: no DB, no network, no live repo access.
"""

import pytest
from pathlib import Path

from tools.surrealdb.context_required_reads import (
    resolve_required_reads,
    MINIMUM_READS,
)


pytestmark = pytest.mark.unit


class TestMinimumReads:
    """Verify minimum baseline reads are always included."""

    def test_minimum_reads_always_present(self) -> None:
        """Minimum reads (must_read) appear in output."""
        reads = resolve_required_reads(
            task_scope="test scope",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        min_paths = {entry["path"] for entry in MINIMUM_READS}
        result_paths = {r["path"] for r in reads}
        assert min_paths.issubset(result_paths), f"Missing minimum reads: {min_paths - result_paths}"

    def test_minimum_reads_have_priority_must_read(self) -> None:
        """Minimum reads have priority 'must_read'."""
        reads = resolve_required_reads(
            task_scope="test scope",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        for entry in MINIMUM_READS:
            matches = [r for r in reads if r["path"] == entry["path"]]
            assert matches, f"Minimum read missing: {entry['path']}"
            assert matches[0]["priority"] == "must_read", (
                f"Expected must_read for {entry['path']}, "
                f"got {matches[0]['priority']}"
            )


class TestDomainDetection:
    """Test domain detection from task_scope and target_paths."""

    def test_governance_domain_from_scope(self) -> None:
        """Governance keywords in task_scope add governance reads."""
        reads = resolve_required_reads(
            task_scope="update governance policy",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        paths = [r["path"] for r in reads]
        assert any("governance" in p.lower() for p in paths), (
            "Governance domain not detected"
        )

    def test_surrealdb_domain_from_scope(self) -> None:
        """SurrealDB keywords in task_scope add surrealdb reads."""
        reads = resolve_required_reads(
            task_scope="implement context briefing for surrealdb",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        paths = [r["path"] for r in reads]
        assert any("context" in p.lower() for p in paths), (
            "SurrealDB domain not detected"
        )

    def test_trading_domain_from_paths(self) -> None:
        """Trading-related paths add trading reads."""
        reads = resolve_required_reads(
            task_scope="update trading strategy",
            target_issue=None,
            target_paths=["services/execution/service.py"],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        paths = [r["path"] for r in reads]
        assert any("CONTROL_REGISTER" in p for p in paths), (
            "Trading domain not detected"
        )


class TestWriteMode:
    """Test that write operation_mode adds governance reads."""

    def test_write_mode_adds_governance_reads(self) -> None:
        """Write modes add extra must_read entries."""
        reads = resolve_required_reads(
            task_scope="update docs",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="write (code/docs)",
            repo_root=Path("/nonexistent"),
        )
        write_reads = [r for r in reads if r["priority"] == "must_read"]
        # At least one write-specific read (e.g., DELIVERY_APPROVED.yaml)
        write_paths = {r["path"] for r in write_reads}
        assert any("DELIVERY_APPROVED" in p for p in write_paths), (
            "Write-mode governance reads missing"
        )

    def test_non_write_mode_does_not_add_write_reads(self) -> None:
        """Read-only mode should not add write-specific reads."""
        reads_read = resolve_required_reads(
            task_scope="update docs",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        reads_write = resolve_required_reads(
            task_scope="update docs",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="write (code/docs)",
            repo_root=Path("/nonexistent"),
        )
        # Write mode should have more must_read entries
        must_read_read = [r for r in reads_read if r["priority"] == "must_read"]
        must_read_write = [r for r in reads_write if r["priority"] == "must_read"]
        assert len(must_read_write) > len(must_read_read), (
            "Write mode should add extra must_read entries"
        )


class TestTargetIssue:
    """Test that target_issue triggers domain reads."""

    def test_issue_with_governance_keyword(self) -> None:
        """Issue string containing governance keywords adds governance reads."""
        reads = resolve_required_reads(
            task_scope="fix issue",
            target_issue="#1234 governance policy update",
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        paths = [r["path"] for r in reads]
        assert any("governance" in p.lower() for p in paths), (
            "Issue-driven governance domain not detected"
        )


class TestDeduplication:
    """Test that duplicate reads are deduplicated."""

    def test_duplicate_paths_deduplicated(self) -> None:
        """Same path appearing multiple times is deduplicated."""
        reads = resolve_required_reads(
            task_scope="governance update",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        paths = [r["path"] for r in reads]
        assert len(paths) == len(set(paths)), "Duplicate paths found in output"


class TestOutputStructure:
    """Test that each returned dict has required keys."""

    def test_each_read_has_required_keys(self) -> None:
        """Each read dict contains path, priority, reason, source_ref, available, warning."""
        reads = resolve_required_reads(
            task_scope="test",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        required_keys = {"path", "priority", "reason", "source_ref", "available", "warning"}
        for r in reads:
            assert required_keys.issubset(r.keys()), (
                f"Missing keys in read dict: {required_keys - set(r.keys())}"
            )

    def test_available_is_bool(self) -> None:
        """Available field is boolean."""
        reads = resolve_required_reads(
            task_scope="test",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        for r in reads:
            assert isinstance(r["available"], bool), (
                f"available is not bool for {r['path']}"
            )


class TestEdgeCases:
    """Test edge cases and invalid inputs."""

    def test_empty_task_scope(self) -> None:
        """Empty task_scope still returns minimum reads."""
        reads = resolve_required_reads(
            task_scope="",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        assert len(reads) >= len(MINIMUM_READS), "Minimum reads missing for empty scope"

    def test_none_target_paths(self) -> None:
        """None target_paths treated as empty list."""
        reads = resolve_required_reads(
            task_scope="test",
            target_issue=None,
            target_paths=None,  # type: ignore
            target_symbols=[],
            operation_mode="read_only",
            repo_root=Path("/nonexistent"),
        )
        assert len(reads) >= len(MINIMUM_READS)

    def test_invalid_operation_mode(self) -> None:
        """Invalid operation_mode does not cause crash."""
        reads = resolve_required_reads(
            task_scope="test",
            target_issue=None,
            target_paths=[],
            target_symbols=[],
            operation_mode="invalid_mode",
            repo_root=Path("/nonexistent"),
        )
        # Should still return minimum reads
        assert len(reads) >= len(MINIMUM_READS)
