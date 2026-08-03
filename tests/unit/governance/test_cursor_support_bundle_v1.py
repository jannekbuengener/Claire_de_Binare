"""
test_id: tc_cursor_support_bundle_v1_001
test_name: dual_run_cursor_support_bundle
test_type: Bauteil-Test
cdb_area: governance
issue_ref: 4258
security_relevant: true
live_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.agent_control.cli import main as cli_main
from tools.agent_control.cursor_support_bundle import (
    SupportBundleError,
    build_support_bundle,
    classify_workspace_binding,
    run_support_bundle_from_states,
)
from tools.agent_control.paths import REPO_ROOT

FIX = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "cursor"
RUN1 = FIX / "dual_run_error_run1.json"
RUN2 = FIX / "dual_run_error_run2.json"
SHARED = FIX / "dual_run_shared_meta.json"
FAKE_KEY = "crsr_test_support_bundle_secret_DO_NOT_LEAK"


def _bundle(tmp_path: Path) -> dict:
    result = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=tmp_path / "out",
        repo_root=REPO_ROOT,
    )
    return json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))


@pytest.mark.unit
def test_dual_error_runs_produce_deterministic_comparison(tmp_path: Path) -> None:
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    r1 = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=out1,
        repo_root=REPO_ROOT,
    )
    r2 = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=out2,
        repo_root=REPO_ROOT,
    )
    b1 = json.loads((out1 / "support_bundle_redacted.json").read_text(encoding="utf-8"))
    b2 = json.loads((out2 / "support_bundle_redacted.json").read_text(encoding="utf-8"))
    assert (
        b1["comparison"]["repeated_failure_signature"]
        == b2["comparison"]["repeated_failure_signature"]
    )
    assert r1["run_ids"] == r2["run_ids"]
    assert set(r1["run_ids"]) == {
        "run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b",
        "run-c2c3898b-af9e-4f73-ad91-830f600561b9",
    }
    assert set(r1["evidence_ids"]) == {
        "are-5ae1839fa8b0c71ad7e8b902",
        "are-48dbdce0fbaf7ff5654b23f4",
    }


@pytest.mark.unit
def test_support_bundle_zero_posts_and_no_secrets(tmp_path: Path) -> None:
    result = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=tmp_path / "out",
        repo_root=REPO_ROOT,
    )
    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    dumped = json.dumps(bundle)
    assert bundle["safety"]["cursor_http_posts"] == 0
    assert result["cursor_http_posts"] == 0
    assert result["new_agents"] == 0
    assert result["new_runs"] == 0
    assert result["third_run_started"] is False
    assert bundle["external_send_allowed"] is False
    assert FAKE_KEY not in dumped
    assert "Authorization" not in dumped
    assert "Bearer " not in dumped
    assert "crsr_" not in dumped


@pytest.mark.unit
def test_privacy_minimization_omits_account_and_cost_metadata(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    dumped = json.dumps(bundle)
    draft = (tmp_path / "out" / "cursor_support_request_draft.md").read_text(
        encoding="utf-8"
    )
    combined = dumped + "\n" + draft
    # JSON/API field names must not appear as keys or raw values.
    assert '"userId"' not in combined
    assert "363812814" not in combined
    assert '"apiKeyName"' not in combined
    assert "api.CDB" not in combined
    assert '"usageUuid"' not in combined
    assert "156f951d-a147-534f-9137-7fbe9d14edc1" not in combined
    assert "chargedCents" not in combined
    assert "rawCostCents" not in combined
    assert "sample-brain" not in combined
    assert "gpt-mcp-server" not in combined
    assert "redacted_states" not in dumped
    assert "credential_present" not in dumped
    assert "token_length" not in combined
    assert "token_prefix" not in combined
    assert "token_suffix" not in combined
    assert "token_hash" not in combined
    assert ".secrets/" not in combined
    assert "C:\\Users\\" not in combined
    assert "prompt_text" not in combined
    # Required evidence retained
    assert bundle["inferences"]["root_cause"]["primary_classification"] == (
        "UNKNOWN_OBSERVABILITY_GAP"
    )
    assert bundle["direct_evidence"]["run1"]["created_at"] == (
        "2026-08-03T01:29:56.853Z"
    )
    assert bundle["direct_evidence"]["run2"]["terminal_at"] == (
        "2026-08-03T02:29:52.402Z"
    )
    assert (
        bundle["direct_evidence"]["repo_config"]["named_environment_present"] is False
    )
    assert bundle["direct_evidence"]["repo_config"]["branchName_present"] is False
    assert (
        bundle["direct_evidence"]["successful_reference"]["proves_same_api_workspace"]
        is False
    )
    shared = bundle["direct_evidence"]["shared"]
    assert shared["numeric_account_id_omitted"] is True
    assert shared["api_key_display_name_omitted"] is True
    assert shared["unrelated_repositories_omitted"] is True


@pytest.mark.unit
def test_claimed_branch_unverified_and_github_404_preserved(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    d = bundle["direct_evidence"]
    assert (
        d["run1"]["github_branch_status"][
            "cloud-cursor/cursor-cloud-pilot-marker-3c10"
        ]["status"]
        == 404
    )
    assert (
        d["run2"]["github_branch_status"]["cloud-cursor/probe-4258-documentation-69b3"][
            "status"
        ]
        == 404
    )
    assert bundle["inferences"]["delivery_verified"] is False
    assert bundle["inferences"]["approval_context"].startswith("SKIP")
    assert bundle["inferences"]["failure_phases"]["git_push_attempt_proven"] is False
    assert bundle["inferences"]["failure_phases"]["commit_attempt_proven"] is False
    assert bundle["inferences"]["failure_phases"]["pr_create_attempt_proven"] is False


@pytest.mark.unit
def test_workspace_mismatch_unknown_without_identity_evidence() -> None:
    assert classify_workspace_binding({"apiKeyName": "api.CDB", "userId": 1}) == (
        "CURSOR_WORKSPACE_IDENTITY_UNKNOWN"
    )
    assert classify_workspace_binding({}) == "CURSOR_WORKSPACE_IDENTITY_UNKNOWN"


@pytest.mark.unit
def test_reference_pr_does_not_prove_same_api_workspace(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    ref = bundle["direct_evidence"]["successful_reference"]
    assert ref["proves_same_api_workspace"] is False
    assert ref["proves_github_app_can_write_at_some_path"] is True


@pytest.mark.unit
def test_missing_error_maps_to_observability_gap_and_usage_not_pass(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    rc = bundle["inferences"]["root_cause"]
    assert rc["primary_classification"] == "UNKNOWN_OBSERVABILITY_GAP"
    assert bundle["direct_evidence"]["run1"]["usage_total_tokens"] > 0
    assert bundle["direct_evidence"]["run2"]["usage_total_tokens"] > 0
    assert bundle["inferences"]["delivery_verified"] is False
    assert (
        bundle["comparison"]["repeated_failure_signature"]["no_structured_error_object"]
        is True
    )


@pytest.mark.unit
def test_support_draft_contains_backend_questions_and_required_sections(
    tmp_path: Path,
) -> None:
    result = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=tmp_path / "out",
        repo_root=REPO_ROOT,
    )
    draft = Path(result["draft_path"]).read_text(encoding="utf-8")
    for section in (
        "## Summary",
        "## Expected behavior",
        "## Actual behavior",
        "## Run 1 identifiers and timestamps",
        "## Run 2 identifiers and timestamps",
        "## Repeated failure signature",
        "## Create and configuration details",
        "## Repository visibility",
        "## Successful reference PR #4295",
        "## Ruled-out causes and evidence limits",
        "## Requested backend investigation",
        "## Security and privacy statement",
        "## Attachment list",
    ):
        assert section in draft
    assert "Internal backend error for both run IDs" in draft
    assert "Workspace associated with the API key" in draft
    assert "Workspace associated with the GitHub App installation" in draft
    assert "Repository authorization and effective permissions" in draft
    assert "Environment selection, repo-config resolution" in draft
    assert "Selected model and model/runtime startup result" in draft
    assert "Whether file changes, commits or Git pushes were attempted" in draft
    assert "Whether PR creation was attempted" in draft
    assert "run.git.branches" in draft
    assert "known defect in the public Cloud Agents v1 API" in draft
    assert (tmp_path / "out" / "ATTACHMENT_MANIFEST.md").is_file()


@pytest.mark.unit
def test_post_nonzero_raises() -> None:
    s1 = json.loads(RUN1.read_text(encoding="utf-8"))
    s2 = json.loads(RUN2.read_text(encoding="utf-8"))
    with pytest.raises(SupportBundleError) as exc:
        build_support_bundle(state_run1=s1, state_run2=s2, cursor_posts=1)
    assert exc.value.code == "BUNDLE_POST_FORBIDDEN"


@pytest.mark.unit
def test_cli_cursor_support_bundle(tmp_path: Path) -> None:
    out = tmp_path / "bundle_out"
    tracked = tmp_path / "CURSOR_CLOUD_DUAL_RUN_FAILURE_4258.md"
    code = cli_main(
        [
            "pilot",
            "cursor-support-bundle",
            "--state-run1",
            str(RUN1),
            "--state-run2",
            str(RUN2),
            "--shared",
            str(SHARED),
            "--output",
            str(out),
            "--tracked-summary",
            str(tracked),
        ]
    )
    assert code == 0
    assert (out / "support_bundle_redacted.json").is_file()
    assert (out / "cursor_support_request_draft.md").is_file()
    assert (out / "ATTACHMENT_MANIFEST.md").is_file()
    assert tracked.is_file()
    text = tracked.read_text(encoding="utf-8")
    assert "UNKNOWN_OBSERVABILITY_GAP" in text
    assert "run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b" in text
    assert "run-c2c3898b-af9e-4f73-ad91-830f600561b9" in text
    assert '"userId"' not in text
    assert '"apiKeyName"' not in text
    assert "363812814" not in text
    assert "api.CDB" not in text
