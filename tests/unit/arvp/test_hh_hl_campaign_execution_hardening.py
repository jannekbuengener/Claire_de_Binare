"""Fail-closed hardening tests for the hh_hl Execution-GO authorization path.

test_id: tc_hh_hl_campaign_exec_hardening_001
test_type: Schutz-Test (negative / boundary)
cdb_area: arvp_campaign
issue_ref: #4374
live_relevant: false

Every negative executor path asserts the injected single-run callable was
invoked *exactly zero times* — a blocked authorization must never reach the
replay surface. No live network (git resolvers and GO fetchers are injected
fakes) and no physical replays. Covers:

* surface-receipt tamper / fixture / wrong-surface-id / bare-hash rejects,
* the post-merge live-main SHA gate (arbitrary non-main + nonexistent SHA),
* execution-sha existence + checked-out HEAD drift,
* exact envelope bindings (each empty/mismatch binding blocks individually),
* expiry re-check between GO verification and execute,
* Owner-GO re-verify on resume/start (mutation blocks),
* Execution-GO contract sync (generator payload == live schema == template) and
  the pre-post package validator (authorizes / does_not_authorize discipline).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.arvp_vacation import hh_hl_campaign_execution_prep as prep
from tools.arvp_vacation.campaign_executor_providers import (
    HhHlSingleRunReplayProvider,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_REPLAY_PROFILE_ID,
    CampaignProfileError,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import load_pass_receipt
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    VERIFIED_DESIGN_GO_BOUND_MAIN_SHA,
    build_reference_design_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_execution_authorization import (
    ADAPTER_ID,
    AUTH_SCHEMA_VERSION,
    AUTHORIZES_EXACT,
    CAMPAIGN_ID,
    EVIDENCE_NAMESPACE,
    GO_STATUS,
    GRANTED_CAPABILITY,
    MANIFEST_ID,
    MAX_RUN_COUNT,
    REQUIRED_DOES_NOT_AUTHORIZE,
    STRATEGY_ID,
    AuthorizationContext,
    HhHlExecutionAuthorizationError,
    OwnerGoComment,
    authorization_context_from_verified_go,
    fingerprint_execution_authorization_payload,
    validate_execution_go_package,
    validate_execution_go_payload,
    verify_owner_execution_go_comment,
)
from tools.arvp_vacation.hh_hl_campaign_final_manifest import (
    DEFAULT_RESOURCE_BUDGET,
    DEFAULT_RESUME_POLICY,
)
from tools.arvp_vacation.hh_hl_campaign_lifecycle import (
    reverify_owner_go_for_resume_or_start,
)
from tools.arvp_vacation.hh_hl_campaign_run_plan import build_hh_hl_final_run_plan
from tools.arvp_vacation.hh_hl_campaign_sha_gate import (
    GitShaResolver,
    HhHlShaGateError,
    assert_checked_out_matches_execution_sha,
    assert_execution_sha_exists,
)
from tools.arvp_vacation.hh_hl_campaign_surface import (
    ALLOWED_EXECUTION_SURFACE_ID,
    SURFACE_RECEIPT_SCHEMA_VERSION,
    HhHlSurfaceReceiptError,
    load_and_validate_surface_receipt,
    probe_hh_hl_surface,
)
from tools.arvp_vacation.sensitivity_campaign_executor import RunEnvelope, RunResult

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = PROJECT_ROOT / "docs" / "contracts"
MANIFEST_PATH = PROJECT_ROOT / "config" / "arvp" / "hh_hl_campaign_4374_v1.json"
DATASET_RECEIPT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "evidence"
    / "arvp_hh_hl_dataset_local_proof_receipt_4374.json"
)
LIVE_SCHEMA_PATH = (
    CONTRACTS / "cdb_hh_hl_campaign_execution_authorization.v1.schema.json"
)
TEMPLATE_PATH = CONTRACTS / "examples" / "go_hh_hl_campaign_execution.v1.template.json"

REPO = "jannekbuengener/Claire_de_Binare"
BASE_SHA = VERIFIED_DESIGN_GO_BOUND_MAIN_SHA
POST_MERGE_SHA = "a" * 40  # valid post-merge sha, distinct from BASE_SHA
EXECUTION_SHA = "b" * 40
SURFACE_FP = "c" * 64
FIXED_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=UTC)
AFTER_FAR_FUTURE = datetime(2027, 7, 1, 0, 0, 0, tzinfo=UTC)
FAR_FUTURE = "2027-06-01T00:00:00Z"


# --------------------------------------------------------------------------- #
# Shared fixtures / helpers
# --------------------------------------------------------------------------- #
def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _design_receipt():
    return build_reference_design_receipt(repo_root=PROJECT_ROOT)


def _dataset_receipt():
    return load_pass_receipt(DATASET_RECEIPT_PATH)


def _build_final(
    planning_sha: str,
    *,
    resolver: GitShaResolver | None = None,
    pre_final: bool = False,
):
    return build_hh_hl_final_run_plan(
        final_manifest=_manifest(),
        design_receipt=_design_receipt(),
        dataset_receipt=_dataset_receipt(),
        planning_sha=planning_sha,
        pre_final=pre_final,
        live_main_resolver=resolver,
    )


def _fake_resolver(
    *,
    main_tip: str,
    obj_types: dict[str, str] | None = None,
    head: str | None = None,
) -> GitShaResolver:
    types = dict(obj_types or {})
    return GitShaResolver(
        fetch=lambda: None,
        resolve_main_tip=lambda: main_tip,
        object_type=lambda sha: types.get(sha),
        head=lambda: head if head is not None else main_tip,
    )


def _full_receipt(**over) -> dict:
    """Complete, fingerprint-bound, owner-GO-eligible receipt (as a mapping).

    ``over`` mutates fields *after* the fingerprint is computed so negative
    tests can force a tamper / wrong id without recomputing the fingerprint.
    """
    receipt = probe_hh_hl_surface(
        fixture=False,
        manifest_fingerprint="a" * 64,
        run_plan_fingerprint="b" * 64,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256="c" * 64,
        dataset_content_fingerprint_digest="d" * 64,
        run_plan_loadable=True,
        resource_budget=dict(DEFAULT_RESOURCE_BUDGET),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
        physical_dataset_proof_passed=True,
    )
    receipt.update(over)
    return receipt


def _live_payload(*, run_plan_fp: str, comment_id: int = 987654321, **over) -> dict:
    """A complete, schema-valid *live* Execution-GO payload (no host comment id)."""
    _ = comment_id  # host metadata only; bound via OwnerGoComment
    manifest = _manifest()
    binding = manifest["dataset_binding"]
    design = manifest["design_ratification"]
    payload = {
        "schema_version": AUTH_SCHEMA_VERSION,
        "status": GO_STATUS,
        "repository": REPO,
        "issue": 4374,
        "authorizing_github_login": "jannekbuengener",
        "bound_main_sha": POST_MERGE_SHA,
        "execution_sha": EXECUTION_SHA,
        "manifest_path": manifest["manifest_path"],
        "manifest_id": MANIFEST_ID,
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "design_go_comment_id": int(design["comment_id"]),
        "design_go_body_fingerprint": design["body_fingerprint"],
        "campaign_id": CAMPAIGN_ID,
        "strategy_set": [STRATEGY_ID],
        "strategy_version": manifest["strategy_version"],
        "adapter_id": ADAPTER_ID,
        "dataset_selection_sha256": binding["selection_sha256"],
        "dataset_content_fingerprint_digest": binding["content_fingerprint_digest"],
        "window_count": 39,
        "variant_count": 1,
        "run_plan_fingerprint": run_plan_fp,
        "expected_run_count": 39,
        "max_run_count": MAX_RUN_COUNT,
        "execution_surface_id": HhHlSingleRunReplayProvider.SURFACE_ID,
        "surface_capability_fingerprint": SURFACE_FP,
        "resource_budget": dict(DEFAULT_RESOURCE_BUDGET),
        "evidence_namespace": EVIDENCE_NAMESPACE,
        "resume_policy": dict(DEFAULT_RESUME_POLICY),
        "reproduction_policy": manifest["reproduction_policy"][
            "reproduction_policy_id"
        ],
        "analyzer_profile_id": manifest["analyzer_profile_id"],
        "granted_capabilities": [GRANTED_CAPABILITY],
        "absolute_bans_unchanged": True,
        "expires_at_utc": FAR_FUTURE,
        "lr_status": "NO-GO",
        "authorizes": list(AUTHORIZES_EXACT),
        "does_not_authorize": list(REQUIRED_DOES_NOT_AUTHORIZE),
    }
    payload.update(over)
    return payload


def _exec_comment(
    payload: dict,
    *,
    comment_id: int = 987654321,
    created: str = "2026-08-06T16:00:00Z",
    updated: str | None = None,
) -> OwnerGoComment:
    body = (
        "```cdb.hh_hl_campaign_execution_authorization.v1\n"
        + json.dumps(payload)
        + "\n```"
    )
    return OwnerGoComment(
        comment_id=int(comment_id),
        issue_number=4374,
        author_login="jannekbuengener",
        body=body,
        created_at=created,
        updated_at=updated if updated is not None else created,
        repository=REPO,
    )


def _expected(payload: dict) -> dict:
    keys = (
        "bound_main_sha",
        "execution_sha",
        "manifest_path",
        "manifest_id",
        "manifest_fingerprint",
        "campaign_id",
        "run_plan_fingerprint",
        "expected_run_count",
        "execution_surface_id",
        "surface_capability_fingerprint",
        "evidence_namespace",
        "dataset_selection_sha256",
        "dataset_content_fingerprint_digest",
    )
    return {k: payload[k] for k in keys}


def _fetcher(comment: OwnerGoComment):
    def _fetch(repository, issue, comment_id):
        return comment

    return _fetch


def _verified_context(run_plan_fp: str) -> AuthorizationContext:
    payload = _live_payload(run_plan_fp=run_plan_fp)
    verified = verify_owner_execution_go_comment(
        comment_id=987654321,
        expected=_expected(payload),
        fetcher=_fetcher(_exec_comment(payload)),
        now_utc=FIXED_NOW,
    )
    return authorization_context_from_verified_go(verified)


def _provider_with_counter() -> tuple[HhHlSingleRunReplayProvider, list]:
    profile = load_profile(HH_HL_REPLAY_PROFILE_ID)
    calls: list = []

    def _run(request):
        calls.append(request)
        return RunResult(exit_code=0, metrics={"gate_reason": "OK"})

    provider = HhHlSingleRunReplayProvider(profile, single_run_callable=_run)
    return provider, calls


def _envelope(ctx: AuthorizationContext, **over) -> RunEnvelope:
    base = {
        "run_key": "rk-0",
        "campaign_id": CAMPAIGN_ID,
        "manifest_fingerprint": ctx.manifest_fingerprint,
        "execution_sha": ctx.execution_sha,
        "window_id": "binance_1m_month_2017_10",
        "strategy_id": STRATEGY_ID,
        "parameters": {"swing_left_bars": 2},
        "slot_id": "hh_hl_baseline_001",
        "phase": "BASELINE",
        "label": "spec_frozen_baseline",
        "physical_parameter_set_fingerprint": "p" * 64,
        "effective_config_fingerprint": "e" * 64,
        "dataset_content_fingerprint": "d" * 64,
        "seed": "s",
        "output_dir": "artifacts/out",
        "run_plan_fingerprint": ctx.run_plan_fingerprint,
        "authorization_fingerprint": ctx.authorization_fingerprint,
    }
    base.update(over)
    return RunEnvelope(**base)


# --------------------------------------------------------------------------- #
# 1) Surface receipt — tamper / fixture / wrong id / bare hash
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_surface_bare_hash_stub_blocks():
    stub = {
        "schema_version": SURFACE_RECEIPT_SCHEMA_VERSION,
        "execution_surface_id": ALLOWED_EXECUTION_SURFACE_ID,
        "surface_capability_fingerprint": "a" * 64,
    }
    with pytest.raises(HhHlSurfaceReceiptError) as exc:
        load_and_validate_surface_receipt(stub)
    assert exc.value.reason_code == "HOLD_SURFACE_RECEIPT_INCOMPLETE"


@pytest.mark.unit
def test_surface_wrong_schema_version_blocks():
    receipt = _full_receipt(schema_version="cdb.something_else.v1")
    with pytest.raises(HhHlSurfaceReceiptError) as exc:
        load_and_validate_surface_receipt(receipt)
    assert exc.value.reason_code == "HOLD_SURFACE_RECEIPT_SCHEMA_INVALID"


@pytest.mark.unit
def test_surface_wrong_surface_id_blocks():
    receipt = _full_receipt(execution_surface_id="services.validation.evil")
    with pytest.raises(HhHlSurfaceReceiptError) as exc:
        load_and_validate_surface_receipt(receipt)
    assert exc.value.reason_code == "HOLD_SURFACE_RECEIPT_SURFACE_ID_INVALID"


@pytest.mark.unit
def test_surface_manipulated_fingerprint_blocks():
    receipt = _full_receipt()
    # Tamper a body field after the fingerprint was computed → recompute differs.
    receipt["free_disk_bytes"] = int(receipt["free_disk_bytes"]) + 1
    with pytest.raises(HhHlSurfaceReceiptError) as exc:
        load_and_validate_surface_receipt(receipt)
    assert exc.value.reason_code == "HOLD_SURFACE_RECEIPT_FINGERPRINT_MISMATCH"


@pytest.mark.unit
def test_surface_fixture_blocks_owner_package_but_ok_when_explicitly_allowed():
    fixture_receipt = probe_hh_hl_surface(
        fixture=True,
        manifest_fingerprint="a" * 64,
        run_plan_fingerprint="b" * 64,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256="c" * 64,
        dataset_content_fingerprint_digest="d" * 64,
        run_plan_loadable=True,
        resource_budget=dict(DEFAULT_RESOURCE_BUDGET),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
    )
    assert fixture_receipt["fixture"] is True
    assert fixture_receipt["owner_go_package_eligible"] is False
    with pytest.raises(HhHlSurfaceReceiptError) as exc:
        load_and_validate_surface_receipt(fixture_receipt)
    assert (
        exc.value.reason_code
        == "HOLD_SURFACE_RECEIPT_FIXTURE_NOT_ELIGIBLE_FOR_OWNER_GO"
    )
    # A fixture receipt is only loadable when the caller *explicitly* opts in.
    ok = load_and_validate_surface_receipt(
        fixture_receipt, allow_fixture_for_owner_go=True
    )
    assert ok["fixture"] is True


@pytest.mark.unit
def test_surface_non_eligible_non_fixture_blocks_owner_package():
    receipt = probe_hh_hl_surface(
        fixture=False,
        manifest_fingerprint="a" * 64,
        run_plan_fingerprint="b" * 64,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256="c" * 64,
        dataset_content_fingerprint_digest="d" * 64,
        run_plan_loadable=False,  # 39 keys did not load → not eligible
        resource_budget=dict(DEFAULT_RESOURCE_BUDGET),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
    )
    assert receipt["owner_go_package_eligible"] is False
    with pytest.raises(HhHlSurfaceReceiptError) as exc:
        load_and_validate_surface_receipt(receipt)
    assert exc.value.reason_code == "HOLD_SURFACE_RECEIPT_NOT_OWNER_GO_ELIGIBLE"


@pytest.mark.unit
def test_surface_full_receipt_loads_and_binds_surface_id():
    receipt = _full_receipt()
    loaded = load_and_validate_surface_receipt(receipt)
    assert loaded["execution_surface_id"] == ALLOWED_EXECUTION_SURFACE_ID
    assert loaded["owner_go_package_eligible"] is True
    assert loaded["replays"] is False
    assert loaded["campaign_artifacts_written"] is False


@pytest.mark.unit
def test_surface_forced_eligible_without_physical_proof_is_false():
    """Caller-supplied eligible=True cannot bypass a missing physical proof."""
    receipt = probe_hh_hl_surface(
        fixture=False,
        manifest_fingerprint="a" * 64,
        run_plan_fingerprint="b" * 64,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256="c" * 64,
        dataset_content_fingerprint_digest="d" * 64,
        run_plan_loadable=True,
        resource_budget=dict(DEFAULT_RESOURCE_BUDGET),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
        physical_dataset_proof_passed=None,
    )
    # Build path defaults eligible=None; force True via build_surface_receipt.
    from tools.arvp_vacation.hh_hl_campaign_surface import build_surface_receipt

    forced = build_surface_receipt(
        execution_surface_id=ALLOWED_EXECUTION_SURFACE_ID,
        planning_sha=POST_MERGE_SHA,
        manifest_fingerprint="a" * 64,
        run_plan_fingerprint="b" * 64,
        dataset_selection_sha256="c" * 64,
        dataset_content_fingerprint_digest="d" * 64,
        run_plan_loadable=True,
        single_run_provider_reachable=True,
        reproduction_provider_reachable=True,
        analyzer_provider_reachable=True,
        resource_budget=dict(DEFAULT_RESOURCE_BUDGET),
        free_disk_bytes=21474836480,
        fixture=False,
        owner_go_package_eligible=True,
        physical_dataset_proof_passed=None,
    )
    assert receipt["owner_go_package_eligible"] is False
    assert forced["owner_go_package_eligible"] is False


# --------------------------------------------------------------------------- #
# 2) Post-merge live-main SHA gate
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_final_live_gate_arbitrary_existing_non_main_sha_blocks():
    # An existing commit that is NOT the current origin/main tip is refused —
    # this is the same gate prepare-execution-go runs before assembling a
    # package, so an old-main / branch-head SHA cannot back a FINAL plan.
    resolver = _fake_resolver(
        main_tip="f" * 40,
        obj_types={POST_MERGE_SHA: "commit", "f" * 40: "commit"},
    )
    with pytest.raises(CampaignProfileError, match="HOLD_POST_MERGE_SHA_NOT_LIVE_MAIN"):
        _build_final(POST_MERGE_SHA, resolver=resolver)


@pytest.mark.unit
def test_final_live_gate_nonexistent_40hex_blocks():
    resolver = _fake_resolver(main_tip=POST_MERGE_SHA, obj_types={})
    with pytest.raises(CampaignProfileError, match="HOLD_POST_MERGE_SHA_NOT_LIVE_MAIN"):
        _build_final("d" * 40, resolver=resolver)


@pytest.mark.unit
def test_final_live_gate_equal_main_tip_builds_final():
    resolver = _fake_resolver(
        main_tip=POST_MERGE_SHA, obj_types={POST_MERGE_SHA: "commit"}
    )
    plan = _build_final(POST_MERGE_SHA, resolver=resolver)
    assert plan.status == "FINAL"
    assert plan.post_merge_final is True
    assert plan.executable is False


@pytest.mark.unit
def test_final_live_gate_reused_design_base_blocks():
    resolver = _fake_resolver(main_tip=BASE_SHA, obj_types={BASE_SHA: "commit"})
    with pytest.raises(CampaignProfileError, match="HOLD_POST_MERGE_MAIN_SHA_REQUIRED"):
        _build_final(BASE_SHA, resolver=resolver)


@pytest.mark.unit
def test_execution_sha_existence_and_format():
    resolver = _fake_resolver(
        main_tip=POST_MERGE_SHA, obj_types={EXECUTION_SHA: "commit"}
    )
    assert assert_execution_sha_exists(EXECUTION_SHA, resolver=resolver) == (
        EXECUTION_SHA
    )
    with pytest.raises(HhHlShaGateError, match="HOLD_EXECUTION_SHA_INVALID"):
        assert_execution_sha_exists("not-hex", resolver=resolver)
    with pytest.raises(HhHlShaGateError, match="HOLD_EXECUTION_SHA_NOT_A_COMMIT"):
        assert_execution_sha_exists(
            "e" * 40,
            resolver=_fake_resolver(main_tip=POST_MERGE_SHA, obj_types={}),
        )


@pytest.mark.unit
def test_checked_out_head_drift_blocks_execute_entry():
    ok = _fake_resolver(main_tip=POST_MERGE_SHA, head=EXECUTION_SHA)
    assert (
        assert_checked_out_matches_execution_sha(EXECUTION_SHA, resolver=ok)
        == EXECUTION_SHA
    )
    drift = _fake_resolver(main_tip=POST_MERGE_SHA, head="9" * 40)
    with pytest.raises(HhHlShaGateError, match="HOLD_EXECUTION_SHA_CHECKOUT_DRIFT"):
        assert_checked_out_matches_execution_sha(EXECUTION_SHA, resolver=drift)


# --------------------------------------------------------------------------- #
# 3) Envelope bindings — every empty/mismatch binding blocks (0 callable calls)
# --------------------------------------------------------------------------- #
_BINDING_CASES = [
    ("campaign_id", "", "HOLD_EXECUTION_CAMPAIGN_MISMATCH"),
    ("campaign_id", "arvp-other", "HOLD_EXECUTION_CAMPAIGN_MISMATCH"),
    ("manifest_fingerprint", "", "HOLD_EXECUTION_MANIFEST_MISMATCH"),
    ("manifest_fingerprint", "0" * 64, "HOLD_EXECUTION_MANIFEST_MISMATCH"),
    ("run_plan_fingerprint", "", "HOLD_EXECUTION_RUN_PLAN_MISMATCH"),
    ("run_plan_fingerprint", "0" * 64, "HOLD_EXECUTION_RUN_PLAN_MISMATCH"),
    (
        "authorization_fingerprint",
        "",
        "HOLD_EXECUTION_AUTHORIZATION_FINGERPRINT_MISMATCH",
    ),
    (
        "authorization_fingerprint",
        "0" * 64,
        "HOLD_EXECUTION_AUTHORIZATION_FINGERPRINT_MISMATCH",
    ),
    ("execution_sha", "", "HOLD_EXECUTION_EXECUTION_SHA_MISMATCH"),
    ("execution_sha", "c" * 40, "HOLD_EXECUTION_EXECUTION_SHA_MISMATCH"),
    ("run_key", "", "HOLD_EXECUTION_RUN_KEY_REQUIRED"),
    ("window_id", "", "HOLD_EXECUTION_WINDOW_ID_REQUIRED"),
]


@pytest.mark.unit
@pytest.mark.parametrize("field,value,reason", _BINDING_CASES)
def test_envelope_binding_blocks_before_callable(field, value, reason):
    provider, calls = _provider_with_counter()
    plan = _build_final(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    envelope = _envelope(ctx, **{field: value})
    with pytest.raises(CampaignProfileError, match=reason):
        provider.execute(envelope, authorization_context=ctx)
    assert calls == []  # callable invoked exactly 0 times


@pytest.mark.unit
def test_envelope_scenario_group_and_pb1_block_before_callable():
    provider, calls = _provider_with_counter()
    plan = _build_final(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    with pytest.raises(CampaignProfileError, match="HH_HL_SCENARIO_GROUP_FORBIDDEN"):
        provider.execute(
            _envelope(ctx, parameters={"scenario_group_id": "x"}),
            authorization_context=ctx,
        )
    with pytest.raises(CampaignProfileError, match="HH_HL_ENVELOPE_STRATEGY_MISMATCH"):
        provider.execute(
            _envelope(ctx, strategy_id="primary_breakout_v1"),
            authorization_context=ctx,
        )
    assert calls == []


@pytest.mark.unit
def test_missing_owner_go_blocks_before_callable():
    provider, calls = _provider_with_counter()
    plan = _build_final(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    with pytest.raises(CampaignProfileError, match="HOLD_EXECUTION_OWNER_GO_REQUIRED"):
        provider.execute(_envelope(ctx), authorization_context=None)
    assert calls == []


# --------------------------------------------------------------------------- #
# 4) Expiry between verify and execute → callable never called
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_context_expiring_between_verify_and_execute_never_calls_callable():
    provider, calls = _provider_with_counter()
    plan = _build_final(POST_MERGE_SHA)
    # Verified while still valid (FIXED_NOW << FAR_FUTURE), then dispatched after
    # the bound expiry lapsed (AFTER_FAR_FUTURE > FAR_FUTURE).
    ctx = _verified_context(plan.run_plan_fingerprint)
    with pytest.raises(CampaignProfileError, match="HOLD_EXECUTION_GO_EXPIRED"):
        provider.execute(
            _envelope(ctx),
            authorization_context=ctx,
            now_utc=AFTER_FAR_FUTURE,
        )
    assert calls == []


@pytest.mark.unit
def test_valid_context_calls_callable_exactly_once():
    provider, calls = _provider_with_counter()
    plan = _build_final(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    result = provider.execute(
        _envelope(ctx), authorization_context=ctx, now_utc=FIXED_NOW
    )
    assert result.exit_code == 0
    assert len(calls) == 1


# --------------------------------------------------------------------------- #
# 5) Owner-GO re-verify on resume/start
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_resume_reverify_ok_returns_context():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    comment = _exec_comment(payload)
    ctx = reverify_owner_go_for_resume_or_start(
        comment_id=987654321,
        expected=_expected(payload),
        fetcher=_fetcher(comment),
        bound_comment_updated_at=comment.updated_at,
        now_utc=FIXED_NOW,
    )
    assert isinstance(ctx, AuthorizationContext)
    assert ctx.run_plan_fingerprint == plan.run_plan_fingerprint


@pytest.mark.unit
def test_resume_reverify_blocks_on_updated_at_drift_vs_bound():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    # Live comment is internally consistent (created == updated) but its
    # updated_at drifted from the timestamp bound at first verification.
    mutated = _exec_comment(
        payload, created="2026-08-06T16:05:00Z", updated="2026-08-06T16:05:00Z"
    )
    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_COMMENT_MUTATED"
    ):
        reverify_owner_go_for_resume_or_start(
            comment_id=987654321,
            expected=_expected(payload),
            fetcher=_fetcher(mutated),
            bound_comment_updated_at="2026-08-06T16:00:00Z",
            now_utc=FIXED_NOW,
        )


@pytest.mark.unit
def test_resume_reverify_blocks_on_edited_comment():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    edited = _exec_comment(payload, updated="2026-08-06T16:05:00Z")
    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_COMMENT_MUTATED"
    ):
        reverify_owner_go_for_resume_or_start(
            comment_id=987654321,
            expected=_expected(payload),
            fetcher=_fetcher(edited),
            bound_comment_updated_at="2026-08-06T16:00:00Z",
            now_utc=FIXED_NOW,
        )


# --------------------------------------------------------------------------- #
# 6) Execution-GO contract sync + package validator
# --------------------------------------------------------------------------- #
def _assembled_package() -> dict:
    plan = _build_final(POST_MERGE_SHA, pre_final=True)
    surface = _full_receipt()
    return prep._assemble_execution_go_payload(
        manifest=_manifest(),
        plan=plan,
        planning_sha=POST_MERGE_SHA,
        execution_sha=EXECUTION_SHA,
        surface=surface,
        expires_at_utc=FAR_FUTURE,
    )


@pytest.mark.unit
def test_generator_payload_matches_live_schema_and_template_keys():
    payload = _assembled_package()
    schema = json.loads(LIVE_SCHEMA_PATH.read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert schema.get("additionalProperties") is False
    # The generator emits exactly the live schema's required key set (no more,
    # no less) so a hardened additionalProperties:false schema stays in sync.
    assert set(payload.keys()) == required

    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    tpl_keys = set(template.keys())
    assert required.issubset(tpl_keys)
    # Template may only add the human-facing ``notes`` beyond the contract keys.
    assert tpl_keys - required <= {"notes"}
    assert template["authorizes"] == list(AUTHORIZES_EXACT)
    assert set(REQUIRED_DOES_NOT_AUTHORIZE).issubset(template["does_not_authorize"])


@pytest.mark.unit
def test_complete_pre_post_package_validates_without_comment_id():
    payload = _assembled_package()
    assert "github_comment_id" not in payload
    # Must not raise: signed Owner payload is postable without a self-ID.
    validate_execution_go_package(payload)
    # Live schema accepts the same body (no host comment id).
    validate_execution_go_payload(payload, now_utc=FIXED_NOW)


@pytest.mark.unit
def test_fresh_unedited_owner_comment_without_payload_comment_id_accepted():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    assert "github_comment_id" not in payload
    verified = verify_owner_execution_go_comment(
        comment_id=987654321,
        expected=_expected(payload),
        fetcher=_fetcher(_exec_comment(payload, comment_id=987654321)),
        now_utc=FIXED_NOW,
    )
    assert verified["valid"] is True
    assert verified["github_comment_id"] == 987654321
    assert "github_comment_id" not in verified["payload"]
    ctx = authorization_context_from_verified_go(verified)
    assert ctx.github_comment_id == 987654321
    assert ctx.comment_updated_at == "2026-08-06T16:00:00Z"
    assert ctx.authorization_fingerprint == verified["authorization_fingerprint"]


@pytest.mark.unit
def test_smuggled_github_comment_id_in_payload_blocked():
    payload = _live_payload(run_plan_fp="f" * 64, github_comment_id=987654321)
    assert "github_comment_id" in payload
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_HOST_METADATA_IN_PAYLOAD|HOLD_EXECUTION_GO_SCHEMA_VALIDATION_FAILED|HOLD_EXECUTION_GO_PACKAGE_SCHEMA_VALIDATION_FAILED",
    ):
        validate_execution_go_payload(payload, now_utc=FIXED_NOW)
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_HOST_METADATA_IN_PAYLOAD|HOLD_EXECUTION_GO_PACKAGE_SCHEMA_VALIDATION_FAILED",
    ):
        validate_execution_go_package(payload)


@pytest.mark.unit
def test_wrong_requested_comment_id_blocks():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    comment = _exec_comment(payload, comment_id=111111111)

    def _fetch(repository, issue, comment_id):
        # Fetcher returns a different id than requested → identity HOLD.
        return comment

    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_COMMENT_ID_MISMATCH"
    ):
        verify_owner_execution_go_comment(
            comment_id=999999999,
            expected=_expected(payload),
            fetcher=_fetch,
            now_utc=FIXED_NOW,
        )


@pytest.mark.unit
def test_wrong_author_blocks_without_reaching_replay():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    provider, calls = _provider_with_counter()
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_AUTHOR_NOT_ALLOWLISTED|HOLD_EXECUTION_GO_AUTHOR_LOGIN_INVALID",
    ):
        verify_owner_execution_go_comment(
            comment_id=987654321,
            expected=_expected(payload),
            fetcher=_fetcher(
                OwnerGoComment(
                    comment_id=987654321,
                    issue_number=4374,
                    author_login="not-the-owner",
                    body=(
                        "```cdb.hh_hl_campaign_execution_authorization.v1\n"
                        + json.dumps(payload)
                        + "\n```"
                    ),
                    created_at="2026-08-06T16:00:00Z",
                    updated_at="2026-08-06T16:00:00Z",
                    repository=REPO,
                )
            ),
            now_utc=FIXED_NOW,
        )
    assert calls == []


@pytest.mark.unit
def test_authorization_fingerprint_deterministic_without_comment_id():
    plan = _build_final(POST_MERGE_SHA)
    payload = _live_payload(run_plan_fp=plan.run_plan_fingerprint)
    fp1 = fingerprint_execution_authorization_payload(payload)
    fp2 = fingerprint_execution_authorization_payload(dict(payload))
    assert fp1 == fp2
    assert len(fp1) == 64
    # Injecting host metadata must not be silently ignored by the fingerprint
    # path used after validation — validation rejects first.
    smuggled = dict(payload)
    smuggled["github_comment_id"] = 1
    with pytest.raises(HhHlExecutionAuthorizationError):
        validate_execution_go_payload(smuggled, now_utc=FIXED_NOW)


@pytest.mark.unit
def test_missing_does_not_authorize_blocks_live_payload():
    payload = _live_payload(run_plan_fp="f" * 64)
    del payload["does_not_authorize"]
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_DOES_NOT_AUTHORIZE_MISSING",
    ):
        validate_execution_go_payload(payload, now_utc=FIXED_NOW)


@pytest.mark.unit
def test_incomplete_does_not_authorize_blocks_live_payload():
    payload = _live_payload(run_plan_fp="f" * 64)
    payload["does_not_authorize"] = ["stage_b", "oos"]  # truncated disclaimer
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_DOES_NOT_AUTHORIZE_INCOMPLETE",
    ):
        validate_execution_go_payload(payload, now_utc=FIXED_NOW)


@pytest.mark.unit
def test_wrong_authorizes_blocks_live_payload():
    payload = _live_payload(run_plan_fp="f" * 64)
    payload["authorizes"] = ["something_broader"]
    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_AUTHORIZES_INVALID"
    ):
        validate_execution_go_payload(payload, now_utc=FIXED_NOW)


@pytest.mark.unit
def test_package_missing_does_not_authorize_blocks():
    payload = _assembled_package()
    del payload["does_not_authorize"]
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_DOES_NOT_AUTHORIZE_MISSING",
    ):
        validate_execution_go_package(payload)
