"""
test_id: tc_pr_approval_context_v1_001
test_name: pr_approval_context_v1_builder_drift_cli
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/contracts/agent_approval/CDB_PR_APPROVAL_CONTEXT_V1.md
decision_ref: cdb.pr_approval_context.v1
issue_ref: 4257
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.agent_control.approval.codes import (
    AUTHORITY_LIMITS,
    REASON_STALE_HEAD,
    SCHEMA_ID,
)
from tools.agent_control.approval.context import (
    RepoPaths,
    build_approval_context,
    default_repo_paths,
)
from tools.agent_control.approval.digest import compute_context_digest
from tools.agent_control.approval.drift import audit_drift, load_baseline
from tools.agent_control.approval.policy import load_policy
from tools.agent_control.approval.prompt import load_prompt
from tools.agent_control.cli import main as cli_main
from tools.agent_control.paths import REPO_ROOT
from tools.agent_execution_contract.jcs import canonicalize

FIX = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "approval"
EXAMPLES = REPO_ROOT / "docs" / "contracts" / "examples" / "agent_approval"
SCHEMA = REPO_ROOT / "docs" / "contracts" / "cdb_pr_approval_context.v1.schema.json"


def _load(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def _paths(baseline: Path | None = None) -> RepoPaths:
    base = default_repo_paths(REPO_ROOT)
    return RepoPaths(
        repo_root=base.repo_root,
        policy_path=base.policy_path,
        prompt_path=base.prompt_path,
        baseline_path=baseline if baseline is not None else base.baseline_path,
        schema_path=base.schema_path,
    )


@pytest.mark.unit
def test_schema_file_declares_contract() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_id"]["const"] == SCHEMA_ID
    assert "STALE_HEAD" not in schema["properties"]["recommendation"]["enum"]
    assert set(AUTHORITY_LIMITS) <= set(
        schema["properties"]["authority_limits"]["required"]
    )


@pytest.mark.unit
def test_clean_path_approve_recommended_and_digest_stable() -> None:
    snap = _load("clean_app_check_run_success")
    env1 = build_approval_context(snap, _paths())
    assert env1["recommendation"] == "APPROVE_RECOMMENDED"
    assert env1["authority_limits"] == AUTHORITY_LIMITS
    assert env1["drift"]["status"] == "NONE"
    assert env1["policy"]["content_sha256"].startswith("sha256:")
    assert env1["prompt"]["content_sha256"].startswith("sha256:")

    # Key order must not affect digest.
    reordered = json.loads(canonicalize(snap))
    env2 = build_approval_context(reordered, _paths())
    assert env1["context_digest"] == env2["context_digest"]

    # Wall-clock metadata must not affect digest.
    snap_meta = deepcopy(snap)
    snap_meta["observed_at"] = "2099-01-01T00:00:00Z"
    env3 = build_approval_context(snap_meta, _paths())
    assert env3["context_digest"] == env1["context_digest"]

    # Different head → different digest.
    snap_head = deepcopy(snap)
    snap_head["pr"]["head_sha"] = "d" * 40
    snap_head["checks"][0]["source_sha"] = "d" * 40
    env4 = build_approval_context(snap_head, _paths())
    assert env4["context_digest"] != env1["context_digest"]
    assert env4["subject"]["head_sha"] == "d" * 40


@pytest.mark.unit
def test_missing_and_conflicting_head_blocked() -> None:
    missing = build_approval_context(_load("missing_head"), _paths())
    assert missing["recommendation"] == "BLOCKED"
    assert "MISSING_HEAD" in missing["reason_codes"]

    conflict = build_approval_context(_load("conflicting_head"), _paths())
    assert conflict["recommendation"] == "BLOCKED"
    assert "CONFLICTING_HEAD" in conflict["reason_codes"]


@pytest.mark.unit
def test_stale_head_is_reason_code_not_recommendation() -> None:
    env = build_approval_context(_load("stale_head"), _paths())
    assert env["recommendation"] in {"BLOCKED", "UNKNOWN", "HOLD"}
    assert env["recommendation"] != "APPROVE_RECOMMENDED"
    assert REASON_STALE_HEAD in env["reason_codes"]
    assert env["recommendation"] != "STALE_HEAD"


@pytest.mark.unit
def test_missing_source_sha_blocks_approve() -> None:
    snap = _load("clean_app_check_run_success")
    del snap["checks"][0]["source_sha"]
    env = build_approval_context(snap, _paths())
    assert env["recommendation"] != "APPROVE_RECOMMENDED"
    assert REASON_STALE_HEAD in env["reason_codes"]
    assert env["required_checks"][0]["matches_protection"] is False


@pytest.mark.unit
def test_incomplete_baseline_is_unknown_not_none(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("{}\n", encoding="utf-8")
    env = build_approval_context(_load("clean_app_check_run_success"), _paths(empty))
    assert env["drift"]["status"] == "UNKNOWN"
    assert env["recommendation"] != "APPROVE_RECOMMENDED"


@pytest.mark.unit
def test_missing_is_draft_blocks() -> None:
    snap = _load("clean_app_check_run_success")
    del snap["pr"]["is_draft"]
    env = build_approval_context(snap, _paths())
    assert env["recommendation"] == "BLOCKED"
    assert "MISSING_DRAFT_STATE" in env["reason_codes"]


@pytest.mark.unit
def test_content_hash_lf_normalized() -> None:
    from tools.agent_control.approval.policy import content_sha256_bytes

    assert content_sha256_bytes(b"a\r\nb\n") == content_sha256_bytes(b"a\nb\n")


@pytest.mark.unit
def test_required_check_semantics() -> None:
    wrong_mech = build_approval_context(
        _load("same_name_commit_status_wrong_mechanism"), _paths()
    )
    assert wrong_mech["recommendation"] != "APPROVE_RECOMMENDED"
    assert "MECHANISM_MISMATCH" in wrong_mech["reason_codes"]
    assert wrong_mech["required_checks"][0]["matches_protection"] is False

    wrong_app = build_approval_context(_load("wrong_app_id"), _paths())
    assert wrong_app["recommendation"] != "APPROVE_RECOMMENDED"
    assert "APP_ID_MISMATCH" in wrong_app["reason_codes"]

    pending = build_approval_context(_load("required_check_pending"), _paths())
    assert pending["recommendation"] != "APPROVE_RECOMMENDED"
    assert "REQUIRED_CHECK_PENDING" in pending["reason_codes"]

    failed = build_approval_context(_load("required_check_failed"), _paths())
    assert failed["recommendation"] != "APPROVE_RECOMMENDED"
    assert "REQUIRED_CHECK_FAILED" in failed["reason_codes"]


@pytest.mark.unit
def test_review_and_draft_block_approve() -> None:
    draft = build_approval_context(_load("draft_pr"), _paths())
    assert draft["recommendation"] != "APPROVE_RECOMMENDED"
    assert "DRAFT_PR" in draft["reason_codes"]

    blocking = build_approval_context(_load("blocking_review"), _paths())
    assert blocking["recommendation"] == "REQUEST_CHANGES"
    assert "CHANGES_REQUESTED" in blocking["reason_codes"]


@pytest.mark.unit
def test_policy_prompt_hashes_computed_not_embedded(tmp_path: Path) -> None:
    import yaml

    from tools.agent_control.approval.codes import ApprovalError

    policy_path = (
        REPO_ROOT / "config/agent-control/policies/approval/pr_approval.v1.yaml"
    )
    prompt_path = REPO_ROOT / "config/agent-control/prompts/approval/pr_approval.v1.md"
    policy_doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    assert "content_sha256" not in policy_doc
    prompt_fm = prompt_path.read_text(encoding="utf-8").split("---", 2)[1]
    assert "content_sha256" not in prompt_fm

    policy = load_policy(policy_path, repo_root=REPO_ROOT)
    prompt = load_prompt(prompt_path, repo_root=REPO_ROOT)
    assert policy["content_sha256"].startswith("sha256:")
    assert prompt["content_sha256"].startswith("sha256:")

    bad_prompt = tmp_path / "bad_prompt.md"
    bad_prompt.write_text(
        '---\nversion: "1.0.0"\ncontent_sha256: sha256:'
        + ("a" * 64)
        + "\n---\n\nbody\n",
        encoding="utf-8",
    )
    with pytest.raises(ApprovalError) as exc:
        load_prompt(bad_prompt, repo_root=REPO_ROOT)
    assert "content_sha256" in exc.value.message


@pytest.mark.unit
def test_drift_matrix() -> None:
    clean = _load("clean_app_check_run_success")
    env = build_approval_context(clean, _paths())
    assert env["drift"]["status"] == "NONE"

    policy_env = build_approval_context(
        _load("policy_drift"),
        _paths(FIX / "baseline_policy_drift.json"),
    )
    assert policy_env["drift"]["status"] == "POLICY"
    assert policy_env["recommendation"] != "APPROVE_RECOMMENDED"

    prompt_env = build_approval_context(
        _load("prompt_drift"),
        _paths(FIX / "baseline_prompt_drift.json"),
    )
    assert prompt_env["drift"]["status"] == "PROMPT"
    assert prompt_env["recommendation"] != "APPROVE_RECOMMENDED"

    adapter_env = build_approval_context(_load("adapter_drift"), _paths())
    assert adapter_env["drift"]["status"] == "ADAPTER"
    assert adapter_env["recommendation"] != "APPROVE_RECOMMENDED"

    prot_env = build_approval_context(_load("protection_view_drift"), _paths())
    assert prot_env["drift"]["status"] == "PROTECTION_VIEW"
    assert prot_env["recommendation"] != "APPROVE_RECOMMENDED"

    # Missing baseline → UNKNOWN (never NONE).
    missing_paths = RepoPaths(
        repo_root=REPO_ROOT,
        policy_path=REPO_ROOT
        / "config/agent-control/policies/approval/pr_approval.v1.yaml",
        prompt_path=REPO_ROOT
        / "config/agent-control/prompts/approval/pr_approval.v1.md",
        baseline_path=REPO_ROOT / "does-not-exist.json",
        schema_path=SCHEMA,
    )
    unknown = build_approval_context(clean, missing_paths)
    assert unknown["drift"]["status"] == "UNKNOWN"
    assert unknown["recommendation"] != "APPROVE_RECOMMENDED"


@pytest.mark.unit
def test_authority_limits_immutable() -> None:
    env = build_approval_context(_load("clean_app_check_run_success"), _paths())
    for key, value in AUTHORITY_LIMITS.items():
        assert env["authority_limits"][key] is value
        assert value is False


@pytest.mark.unit
def test_secret_like_input_redacted_from_envelope() -> None:
    env = build_approval_context(_load("secret_like_input"), _paths())
    dumped = json.dumps(env)
    assert "Bearer" not in dumped
    assert "SECRETTOKEN" not in dumped
    # Digest material also clean.
    material = compute_context_digest(env)
    assert "Bearer" not in material


@pytest.mark.unit
def test_cli_context_and_drift(tmp_path: Path) -> None:
    out = tmp_path / "ctx.json"
    rc = cli_main(
        [
            "approval",
            "context",
            "--pr",
            "1",
            "--snapshot",
            str(FIX / "clean_app_check_run_success.json"),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    envelope = json.loads(out.read_text(encoding="utf-8"))
    assert envelope["schema_id"] == SCHEMA_ID
    assert envelope["recommendation"] == "APPROVE_RECOMMENDED"
    # Committed examples must remain schema-valid (no test-time writes).
    assert (EXAMPLES / "positive_approve_recommended.json").is_file()
    assert (EXAMPLES / "negative_mechanism_mismatch.json").is_file()

    neg_out = tmp_path / "neg.json"
    rc_neg = cli_main(
        [
            "approval",
            "context",
            "--pr",
            "1",
            "--snapshot",
            str(FIX / "same_name_commit_status_wrong_mechanism.json"),
            "--output",
            str(neg_out),
        ]
    )
    assert rc_neg != 0
    neg = json.loads(neg_out.read_text(encoding="utf-8"))
    assert neg["recommendation"] != "APPROVE_RECOMMENDED"

    drift_rc = cli_main(
        [
            "approval",
            "drift",
            "--baseline",
            str(
                REPO_ROOT / "config/agent-control/capability-baselines/"
                "approval-dashboard-export.redacted.v1.json"
            ),
            "--snapshot",
            str(FIX / "clean_app_check_run_success.json"),
        ]
    )
    assert drift_rc == 0


@pytest.mark.unit
def test_audit_drift_helper_missing_baseline() -> None:
    policy = load_policy(
        REPO_ROOT / "config/agent-control/policies/approval/pr_approval.v1.yaml",
        repo_root=REPO_ROOT,
    )
    prompt = load_prompt(
        REPO_ROOT / "config/agent-control/prompts/approval/pr_approval.v1.md",
        repo_root=REPO_ROOT,
    )
    report = audit_drift(
        policy=policy, prompt=prompt, snapshot={}, baseline=load_baseline(None)
    )
    assert report["status"] == "UNKNOWN"
