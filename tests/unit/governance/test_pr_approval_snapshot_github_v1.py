"""Tests for approval snapshot adapters and gh api helpers (#4505)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import yaml

from tools.agent_control.approval.context import build_approval_context, default_repo_paths
from tools.agent_control.approval.gh_api import merge_check_runs_payload, merge_comment_pages
from tools.agent_control.approval.snapshot_github import build_github_approval_snapshot
from tools.agent_control.paths import REPO_ROOT

FIX = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "approval"


@pytest.mark.unit
def test_merge_comment_pages_slurped_arrays() -> None:
    payload = [
        [{"id": 1, "body": "a", "user": {"login": "bot", "type": "Bot"}}],
        [{"id": 2, "body": "b", "user": {"login": "bot", "type": "Bot"}}],
    ]
    merged = merge_comment_pages(payload)
    assert len(merged) == 2
    assert merged[0]["id"] == 1


@pytest.mark.unit
def test_merge_check_runs_payload_slurped_pages() -> None:
    payload = [
        {"check_runs": [{"name": "ci", "status": "completed"}]},
        {"check_runs": [{"name": "policy-gate", "status": "completed"}]},
    ]
    merged = merge_check_runs_payload(payload)
    assert len(merged) == 2
    assert {item["name"] for item in merged} == {"ci", "policy-gate"}


@pytest.mark.unit
def test_live_snapshot_adapter_uses_baseline_fingerprint() -> None:
    pr_payload = {
        "head": {"sha": "a" * 40},
        "base": {"sha": "b" * 40},
        "body": "",
        "draft": False,
    }
    with patch(
        "tools.agent_control.approval.snapshot_github.gh_api_json",
        side_effect=[
            pr_payload,
            [],
            {"required_status_checks": {"contexts": ["cdb-local-ci"]}},
            {"check_runs": []},
            {"statuses": []},
        ],
    ), patch(
        "tools.agent_control.approval.snapshot_github._fetch_review_decision",
        return_value="APPROVED",
    ), patch(
        "tools.agent_control.approval.snapshot_github._fetch_blocking_thread_count",
        return_value=(0, True),
    ):
        snap = build_github_approval_snapshot(pr_number=1, repository="o/r", repo_root=REPO_ROOT)
    baseline = json.loads(
        (
            REPO_ROOT
            / "config/agent-control/capability-baselines/approval-dashboard-export.redacted.v1.json"
        ).read_text(encoding="utf-8")
    )
    assert snap["adapter"]["capability_fingerprint"] == baseline["capability_fingerprint"]
    env = build_approval_context(snap, default_repo_paths(REPO_ROOT))
    assert "ADAPTER" not in env["drift"].get("sources", [])


@pytest.mark.unit
def test_live_snapshot_review_decision_none_blocks() -> None:
    snap = json.loads((FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8"))
    snap["pr"]["review_decision"] = None
    env = build_approval_context(snap, default_repo_paths())
    assert env["recommendation"] != "APPROVE_RECOMMENDED"
    assert "UNKNOWN_REVIEW_DECISION" in env["reason_codes"]


@pytest.mark.unit
def test_live_snapshot_changes_requested_blocks() -> None:
    snap = json.loads((FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8"))
    snap["pr"]["review_decision"] = "CHANGES_REQUESTED"
    env = build_approval_context(snap, default_repo_paths())
    assert env["recommendation"] == "REQUEST_CHANGES"


@pytest.mark.unit
def test_live_snapshot_unknown_threads_blocks() -> None:
    snap = json.loads((FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8"))
    snap["pr"]["blocking_threads"] = None
    snap["review_thread_state"] = "unknown"
    env = build_approval_context(snap, default_repo_paths())
    assert env["recommendation"] == "UNKNOWN"
    assert "BLOCKING_THREAD_UNKNOWN" in env["reason_codes"]


@pytest.mark.unit
def test_trust_policy_fixture_is_fail_closed_by_default() -> None:
    data = yaml.safe_load(
        (FIX / "acceptance_producer_trust_test.v1.yaml").read_text(encoding="utf-8")
    )
    conductor = data["producers"]["cdb-batch-merge-conductor"]
    assert conductor["require_performed_via_github_app"] is True
    assert conductor["trusted_github_app_slugs"]


@pytest.mark.unit
def test_snapshot_pr_binding_rejects_mismatch() -> None:
    from tools.agent_control.approval.codes import ApprovalError
    from tools.agent_control.approval.context import validate_snapshot_pr_binding

    snap = json.loads((FIX / "clean_app_check_run_success.json").read_text(encoding="utf-8"))
    snap["pr"]["number"] = 99
    with pytest.raises(ApprovalError, match="APPROVAL_SNAPSHOT_PR_MISMATCH"):
        validate_snapshot_pr_binding(snap, 1)
    data = yaml.safe_load(
        (FIX / "acceptance_producer_trust_test.v1.yaml").read_text(encoding="utf-8")
    )
    conductor = data["producers"]["cdb-batch-merge-conductor"]
    assert conductor["require_performed_via_github_app"] is True
    assert conductor["trusted_github_app_slugs"]
