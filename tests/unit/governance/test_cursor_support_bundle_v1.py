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
        # freeze observed_at via rebuilding from same states — digests of
        # comparison signature should match even if timestamps differ.
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
    assert FAKE_KEY not in dumped
    assert "Authorization" not in dumped
    assert "Bearer " not in dumped
    assert "crsr_" not in dumped


@pytest.mark.unit
def test_claimed_branch_unverified_and_github_404_preserved(tmp_path: Path) -> None:
    result = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=tmp_path / "out",
        repo_root=REPO_ROOT,
    )
    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
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


@pytest.mark.unit
def test_workspace_mismatch_unknown_without_identity_evidence() -> None:
    assert classify_workspace_binding({"apiKeyName": "api.CDB", "userId": 1}) == (
        "CURSOR_WORKSPACE_IDENTITY_UNKNOWN"
    )
    assert classify_workspace_binding({}) == "CURSOR_WORKSPACE_IDENTITY_UNKNOWN"


@pytest.mark.unit
def test_reference_pr_does_not_prove_same_api_workspace(tmp_path: Path) -> None:
    result = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=tmp_path / "out",
        repo_root=REPO_ROOT,
    )
    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    ref = bundle["direct_evidence"]["successful_reference"]
    assert ref["proves_same_api_workspace"] is False
    assert ref["proves_github_app_can_write_at_some_path"] is True


@pytest.mark.unit
def test_missing_error_maps_to_observability_gap_and_usage_not_pass(
    tmp_path: Path,
) -> None:
    result = run_support_bundle_from_states(
        state_run1_path=RUN1,
        state_run2_path=RUN2,
        shared_path=SHARED,
        output_dir=tmp_path / "out",
        repo_root=REPO_ROOT,
    )
    bundle = json.loads(Path(result["bundle_path"]).read_text(encoding="utf-8"))
    rc = bundle["inferences"]["root_cause"]
    assert rc["primary_classification"] == "UNKNOWN_OBSERVABILITY_GAP"
    assert bundle["direct_evidence"]["run1"]["usage_total_tokens"] > 0
    assert bundle["direct_evidence"]["run2"]["usage_total_tokens"] > 0
    # usage without delivery never maps to PASS
    assert bundle["inferences"]["delivery_verified"] is False
    assert (
        bundle["comparison"]["repeated_failure_signature"]["no_structured_error_object"]
        is True
    )


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
    assert tracked.is_file()
    text = tracked.read_text(encoding="utf-8")
    assert "UNKNOWN_OBSERVABILITY_GAP" in text
    assert "run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b" in text
    assert "run-c2c3898b-af9e-4f73-ad91-830f600561b9" in text
