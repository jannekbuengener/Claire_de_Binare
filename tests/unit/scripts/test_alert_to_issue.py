"""Unit tests for scripts.alert_to_issue"""

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.alert_to_issue import (
    build_comment_body,
    build_issue_body,
    find_existing_issue,
    fingerprint,
    process_alert,
    severity_at_or_above,
    FINGERPRINT_MARKER,
)


class TestFingerprint:
    def test_deterministic(self):
        fp1 = fingerprint("cdb_risk", "Circuit breaker triggered")
        fp2 = fingerprint("cdb_risk", "Circuit breaker triggered")
        assert fp1 == fp2

    def test_case_insensitive(self):
        fp1 = fingerprint("CDB_RISK", "Circuit Breaker Triggered")
        fp2 = fingerprint("cdb_risk", "circuit breaker triggered")
        assert fp1 == fp2

    def test_different_inputs_differ(self):
        fp1 = fingerprint("cdb_risk", "Circuit breaker triggered")
        fp2 = fingerprint("cdb_execution", "Order timeout")
        assert fp1 != fp2

    def test_length(self):
        fp = fingerprint("x", "y")
        assert len(fp) == 16


class TestSeverity:
    def test_critical_meets_critical(self):
        assert severity_at_or_above("CRITICAL", "CRITICAL") is True

    def test_error_below_critical(self):
        assert severity_at_or_above("ERROR", "CRITICAL") is False

    def test_critical_meets_error(self):
        assert severity_at_or_above("CRITICAL", "ERROR") is True

    def test_info_below_warning(self):
        assert severity_at_or_above("INFO", "WARNING") is False

    def test_invalid_returns_false(self):
        assert severity_at_or_above("BOGUS", "CRITICAL") is False


class TestBuildIssueBody:
    def test_contains_fingerprint_marker(self):
        fp = fingerprint("cdb_risk", "test")
        body = build_issue_body("cdb_risk", "CRITICAL", "details", fp)
        marker = FINGERPRINT_MARKER.format(fp=fp)
        assert marker in body

    def test_contains_component(self):
        body = build_issue_body("cdb_ws", "ERROR", "msg", "abc123")
        assert "cdb_ws" in body

    def test_contains_severity(self):
        body = build_issue_body("cdb_ws", "CRITICAL", "msg", "abc123")
        assert "CRITICAL" in body


class TestBuildCommentBody:
    def test_contains_severity(self):
        body = build_comment_body("CRITICAL", "repeated failure")
        assert "CRITICAL" in body
        assert "repeated failure" in body


class TestFindExistingIssue:
    @patch("scripts.alert_to_issue._run_gh")
    def test_finds_matching_issue(self, mock_gh):
        fp = "abc123deadbeef00"
        marker = FINGERPRINT_MARKER.format(fp=fp)
        mock_gh.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"number": 42, "body": f"some text\n{marker}\n"}]),
        )
        assert find_existing_issue(fp) == 42

    @patch("scripts.alert_to_issue._run_gh")
    def test_returns_none_when_no_match(self, mock_gh):
        mock_gh.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"number": 99, "body": "unrelated issue body"}]),
        )
        assert find_existing_issue("nomatch00000000") is None

    @patch("scripts.alert_to_issue._run_gh")
    def test_returns_none_on_gh_failure(self, mock_gh):
        mock_gh.return_value = MagicMock(returncode=1, stderr="auth error")
        assert find_existing_issue("x") is None


class TestProcessAlert:
    def test_below_threshold_skipped(self):
        result = process_alert(
            component="cdb_ws",
            severity="WARNING",
            title="Minor issue",
            body="details",
            threshold="CRITICAL",
        )
        assert result["action"] == "skipped"

    @patch("scripts.alert_to_issue.find_existing_issue", return_value=None)
    def test_dry_run_no_existing_issue(self, mock_find):
        result = process_alert(
            component="cdb_risk",
            severity="CRITICAL",
            title="Circuit breaker triggered",
            body="details",
        )
        assert result["action"] == "dry_run"
        assert result["execute"] is False
        assert result["would_create"] is True
        assert result["would_comment"] is False
        assert result["existing_issue"] is None
        assert "fingerprint" in result
        mock_find.assert_called_once()

    @patch("scripts.alert_to_issue.find_existing_issue", return_value=77)
    def test_dry_run_with_existing_issue(self, mock_find):
        result = process_alert(
            component="cdb_risk",
            severity="CRITICAL",
            title="Circuit breaker triggered",
            body="details",
        )
        assert result["action"] == "dry_run"
        assert result["would_create"] is False
        assert result["would_comment"] is True
        assert result["existing_issue"] == 77
        mock_find.assert_called_once()

    @patch("scripts.alert_to_issue.find_existing_issue", return_value=None)
    @patch("scripts.alert_to_issue.create_issue", return_value=123)
    def test_execute_creates_issue(self, mock_create, mock_find):
        result = process_alert(
            component="cdb_risk",
            severity="CRITICAL",
            title="Test alert",
            body="body",
            execute=True,
        )
        assert result["action"] == "created"
        assert result["issue_number"] == 123
        mock_create.assert_called_once()

    @patch("scripts.alert_to_issue.find_existing_issue", return_value=42)
    @patch("scripts.alert_to_issue.comment_on_issue", return_value=True)
    def test_execute_comments_on_existing(self, mock_comment, mock_find):
        result = process_alert(
            component="cdb_risk",
            severity="CRITICAL",
            title="Test alert",
            body="body",
            execute=True,
        )
        assert result["action"] == "commented"
        assert result["issue_number"] == 42
        mock_comment.assert_called_once()

    @patch("scripts.alert_to_issue.find_existing_issue", return_value=None)
    @patch("scripts.alert_to_issue.create_issue", return_value=None)
    def test_execute_create_failed(self, mock_create, mock_find):
        result = process_alert(
            component="cdb_risk",
            severity="CRITICAL",
            title="Test alert",
            body="body",
            execute=True,
        )
        assert result["action"] == "create_failed"
