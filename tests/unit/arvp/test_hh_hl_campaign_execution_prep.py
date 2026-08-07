"""Unit/contract tests for hh_hl campaign execution *preparation* (#4374).

test_id: tc_hh_hl_campaign_exec_prep_001
test_type: Bauteil-Test / Schutz-Test
cdb_area: arvp_campaign
issue_ref: #4374
live_relevant: false

Covers Design-GO ratification, execution-capable-not-authorized final manifest,
FINAL/PRE_FINALIZATION run plan, Owner Execution-GO verification +
AuthorizationContext minting, executor fail-closed wiring, the thin lifecycle
adapter, and the write-free CLI. No live network and no physical replays.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.arvp_vacation import hh_hl_campaign_execution_prep as cli
from tools.arvp_vacation.campaign_executor_providers import (
    HhHlSingleRunReplayProvider,
    PlanningOnlyExecutor,
    resolve_campaign_executor,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    HH_HL_REPLAY_PROFILE_ID,
    CampaignProfileError,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    VERIFIED_DESIGN_GO_BOUND_MAIN_SHA,
    VERIFIED_DESIGN_GO_COMMENT_ID,
    DesignGoComment,
    HhHlDesignAuthorizationError,
    build_reference_design_receipt,
    canonical_design_go_payload,
    verify_design_go_comment,
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
    verify_owner_execution_go_comment,
)
from tools.arvp_vacation.hh_hl_campaign_final_manifest import (
    DEFAULT_RESOURCE_BUDGET,
    DEFAULT_RESUME_POLICY,
    build_hh_hl_final_manifest,
    load_source_manifest,
)
from tools.arvp_vacation.hh_hl_campaign_lifecycle import (
    HH_HL_EVIDENCE_NAMESPACE,
    HhHlLifecycleError,
    bindings_from_authorization,
    hh_hl_evidence_root_for,
    plan_resume_actions,
    validate_primary_run_keys,
)
from tools.arvp_vacation import hh_hl_campaign_sha_gate as sha_gate
from tools.arvp_vacation.hh_hl_campaign_run_plan import build_hh_hl_final_run_plan
from tools.arvp_vacation.hh_hl_campaign_sha_gate import GitShaResolver
from tools.arvp_vacation.hh_hl_campaign_surface import probe_hh_hl_surface
from tools.arvp_vacation.sensitivity_campaign_executor import RunEnvelope, RunResult
from tools.arvp_vacation.sensitivity_campaign_state import (
    CampaignBindings,
    SensitivityStateError,
    commit_successful_result,
    write_campaign_envelope,
    write_run_envelope,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = PROJECT_ROOT / "config" / "arvp" / "hh_hl_campaign_4374_v1.json"
DATASET_RECEIPT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "evidence"
    / "arvp_hh_hl_dataset_local_proof_receipt_4374.json"
)
REPO = "jannekbuengener/Claire_de_Binare"
BASE_SHA = VERIFIED_DESIGN_GO_BOUND_MAIN_SHA
POST_MERGE_SHA = "a" * 40  # valid post-merge sha, distinct from BASE_SHA
EXECUTION_SHA = "b" * 40
SURFACE_FP = "c" * 64
FIXED_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=UTC)
FAR_FUTURE = "2027-06-01T00:00:00Z"


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #
def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _dataset_receipt():
    from tools.arvp_vacation.hh_hl_campaign_dataset import load_pass_receipt

    return load_pass_receipt(DATASET_RECEIPT_PATH)


def _design_receipt():
    return build_reference_design_receipt(repo_root=PROJECT_ROOT)


def _final_plan(planning_sha: str = POST_MERGE_SHA, *, pre_final: bool = False):
    return build_hh_hl_final_run_plan(
        final_manifest=_load_manifest(),
        design_receipt=_design_receipt(),
        dataset_receipt=_dataset_receipt(),
        planning_sha=planning_sha,
        pre_final=pre_final,
    )


def _design_comment(
    *,
    created="2026-08-06T15:08:54Z",
    updated=None,
    author="jannekbuengener",
    mutate=None,
) -> DesignGoComment:
    payload = canonical_design_go_payload(
        bound_main_sha=BASE_SHA,
        comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
        repo_root=PROJECT_ROOT,
    )
    if mutate is not None:
        mutate(payload)
    body = "```json\n" + json.dumps(payload) + "\n```"
    return DesignGoComment(
        comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
        issue_number=4374,
        author_login=author,
        body=body,
        created_at=created,
        updated_at=updated if updated is not None else created,
        repository=REPO,
    )


def _design_fetcher(comment: DesignGoComment):
    def _fetch(repository, issue, comment_id):
        return comment

    return _fetch


def _exec_payload(
    *,
    run_plan_fp: str,
    comment_id: int = 987654321,
    bound: str = POST_MERGE_SHA,
    exec_sha: str = EXECUTION_SHA,
    expires: str = FAR_FUTURE,
    surface_fp: str = SURFACE_FP,
    **over,
) -> dict:
    manifest = _load_manifest()
    binding = manifest["dataset_binding"]
    design = manifest["design_ratification"]
    payload = {
        "schema_version": AUTH_SCHEMA_VERSION,
        "status": GO_STATUS,
        "repository": REPO,
        "issue": 4374,
        "authorizing_github_login": "jannekbuengener",
        "bound_main_sha": bound,
        "execution_sha": exec_sha,
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
        "surface_capability_fingerprint": surface_fp,
        "resource_budget": dict(DEFAULT_RESOURCE_BUDGET),
        "evidence_namespace": EVIDENCE_NAMESPACE,
        "resume_policy": dict(DEFAULT_RESUME_POLICY),
        "reproduction_policy": manifest["reproduction_policy"][
            "reproduction_policy_id"
        ],
        "analyzer_profile_id": manifest["analyzer_profile_id"],
        "granted_capabilities": [GRANTED_CAPABILITY],
        "absolute_bans_unchanged": True,
        "expires_at_utc": expires,
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
    created="2026-08-06T16:00:00Z",
    updated=None,
    author="jannekbuengener",
) -> OwnerGoComment:
    body = (
        "```cdb.hh_hl_campaign_execution_authorization.v1\n"
        + json.dumps(payload)
        + "\n```"
    )
    return OwnerGoComment(
        comment_id=int(comment_id),
        issue_number=4374,
        author_login=author,
        body=body,
        created_at=created,
        updated_at=updated if updated is not None else created,
        repository=REPO,
    )


def _exec_fetcher(comment: OwnerGoComment):
    def _fetch(repository, issue, comment_id):
        return comment

    return _fetch


def _expected_from_payload(payload: dict) -> dict:
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


def _verified_context(run_plan_fp: str) -> AuthorizationContext:
    payload = _exec_payload(run_plan_fp=run_plan_fp)
    verified = verify_owner_execution_go_comment(
        comment_id=987654321,
        expected=_expected_from_payload(payload),
        fetcher=_exec_fetcher(_exec_comment(payload)),
        now_utc=FIXED_NOW,
    )
    return authorization_context_from_verified_go(verified)


def _run_envelope(ctx: AuthorizationContext, **over) -> RunEnvelope:
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


def _capture(capsys) -> dict:
    out = capsys.readouterr().out.strip()
    return json.loads(out)


def _fake_live_main_resolver(
    *,
    main_tip: str = POST_MERGE_SHA,
    extra_commits: tuple[str, ...] = (EXECUTION_SHA,),
) -> GitShaResolver:
    """Offline FINAL live-main resolver (no public CLI skip path)."""
    known = {main_tip: "commit", **{sha: "commit" for sha in extra_commits}}
    return GitShaResolver(
        fetch=lambda: None,
        resolve_main_tip=lambda: main_tip,
        object_type=lambda sha: known.get(sha),
        head=lambda: main_tip,
    )


@pytest.fixture(autouse=True)
def _clear_test_gate_overrides():
    """Ensure private FINAL/physical test hooks never leak across tests."""
    sha_gate._test_set_sha_resolver_override(None)
    cli._test_set_physical_proof_override(None)
    cli._test_set_free_disk_override(None)
    yield
    sha_gate._test_set_sha_resolver_override(None)
    cli._test_set_physical_proof_override(None)
    cli._test_set_free_disk_override(None)


def _full_surface_receipt(**over) -> dict:
    """A complete, fingerprint-bound, owner-GO-eligible surface receipt.

    Bound exactly to the FINAL plan + final manifest for ``POST_MERGE_SHA`` so
    ``prepare-execution-go`` binding checks pass. ``over`` mutates fields
    *after* the fingerprint is computed (negative fingerprint-tamper cases).
    """
    plan = _final_plan(POST_MERGE_SHA)
    manifest = _load_manifest()
    binding = manifest["dataset_binding"]
    receipt = probe_hh_hl_surface(
        fixture=False,
        manifest_fingerprint=str(manifest["manifest_fingerprint"]),
        run_plan_fingerprint=plan.run_plan_fingerprint,
        planning_sha=POST_MERGE_SHA,
        dataset_selection_sha256=str(binding["selection_sha256"]),
        dataset_content_fingerprint_digest=str(binding["content_fingerprint_digest"]),
        run_plan_loadable=True,
        resource_budget=dict(manifest["resource_budget_contract"]),
        reachability={"single_run": True, "reproduction": True, "analyzer": True},
        free_disk_bytes=21474836480,
        physical_dataset_proof_passed=True,
    )
    receipt.update(over)
    return receipt


def _write_surface_receipt(path: Path, **over) -> Path:
    path.write_text(
        json.dumps(_full_surface_receipt(**over), sort_keys=True), encoding="utf-8"
    )
    return path


# --------------------------------------------------------------------------- #
# A) Design-GO
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_design_go_valid_and_body_fingerprint_matches_manifest():
    result = verify_design_go_comment(
        comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
        fetcher=_design_fetcher(_design_comment()),
        repo_root=PROJECT_ROOT,
    )
    assert result["valid"] is True
    manifest = _load_manifest()
    assert (
        result["body_fingerprint"]
        == manifest["design_ratification"]["body_fingerprint"]
    )
    ref = build_reference_design_receipt(repo_root=PROJECT_ROOT)
    assert result["body_fingerprint"] == ref.body_fingerprint


@pytest.mark.unit
def test_design_go_live_shaped_body_fingerprint_matches_reference_binding_view():
    """Owner-comment extras (.draft, notes, rationale) must not drift the FP."""
    # Shape mirrors live comment 5206657394 (bindings identical; extras present).
    live_shaped = {
        "schema_version": "cdb.hh_hl_campaign_design_go.v1.draft",
        "status": "GO_HH_HL_CAMPAIGN_DESIGN",
        "repository": REPO,
        "issue": 4374,
        "authorizing_github_login": "jannekbuengener",
        "bound_main_sha": BASE_SHA,
        "profile_id": "hh_hl_continuation_prep_v1",
        "campaign_id": "arvp-hh-hl-continuation-4374-prep-v1",
        "manifest_path": "config/arvp/hh_hl_campaign_4374_draft_v1.json",
        "manifest_fingerprint": (
            "ab095923a795445ff41d319b1b3941412c9429d38128a5edd2256f4a777afa80"
        ),
        "strategy_set": ["hh_hl_continuation_v1"],
        "grid": {
            "grid_provider_id": "hh_hl_baseline_only_grid_v1",
            "variant_count": 1,
            "slots": ["hh_hl_baseline_001"],
            "rationale": "Spec-frozen parameters; baseline-only pilot",
        },
        "dataset": {
            "dataset_root_kind": "binance_window_bank:locked_batch_a_development_39",
            "window_count": 39,
            "selection_sha256": (
                "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
            ),
            "content_fingerprint_digest": (
                "10f94c34e32db28a9393c38f944db4968b42e87d9ed223397e3637ff44323af9"
            ),
        },
        "authorizes": [
            "exact_grid_definition",
            "dataset_selection",
            "manifest_and_run_plan_freeze",
        ],
        "does_not_authorize": [
            "campaign_execute",
            "paper",
            "live",
            "echtgeld",
            "promotion",
            "stage_b",
            "oos",
            "stress",
        ],
        "notes": (
            "Design ratified after Preparation PR #4375 merged. Campaign "
            "execution requires a separate, fully bound Owner Execution-GO."
        ),
        "lr_status": "NO-GO",
    }
    comment = DesignGoComment(
        comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
        issue_number=4374,
        author_login="jannekbuengener",
        body="```json\n" + json.dumps(live_shaped) + "\n```",
        created_at="2026-08-06T15:08:54Z",
        updated_at="2026-08-06T15:08:54Z",
        repository=REPO,
    )
    live = verify_design_go_comment(
        comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
        fetcher=_design_fetcher(comment),
        repo_root=PROJECT_ROOT,
    )
    ref = build_reference_design_receipt(repo_root=PROJECT_ROOT)
    assert live["body_fingerprint"] == ref.body_fingerprint
    assert (
        live["body_fingerprint"]
        == _load_manifest()["design_ratification"]["body_fingerprint"]
    )


@pytest.mark.unit
def test_design_go_rejects_mutated_comment():
    with pytest.raises(
        HhHlDesignAuthorizationError, match="HOLD_DESIGN_GO_COMMENT_MUTATED"
    ):
        verify_design_go_comment(
            comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
            fetcher=_design_fetcher(_design_comment(updated="2026-08-06T15:09:00Z")),
            repo_root=PROJECT_ROOT,
        )


@pytest.mark.unit
def test_design_go_rejects_foreign_author_and_wrong_status():
    with pytest.raises(
        HhHlDesignAuthorizationError, match="HOLD_DESIGN_GO_AUTHOR_NOT_ALLOWLISTED"
    ):
        verify_design_go_comment(
            comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
            fetcher=_design_fetcher(_design_comment(author="mallory")),
            repo_root=PROJECT_ROOT,
        )

    def _wrong_status(payload):
        payload["status"] = "GO_SOMETHING_ELSE"

    with pytest.raises(
        HhHlDesignAuthorizationError, match="HOLD_DESIGN_GO_STATUS_INVALID"
    ):
        verify_design_go_comment(
            comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
            fetcher=_design_fetcher(_design_comment(mutate=_wrong_status)),
            repo_root=PROJECT_ROOT,
        )


# --------------------------------------------------------------------------- #
# C) Final manifest
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_final_manifest_deterministic_capable_not_authorized():
    source = load_source_manifest(PROJECT_ROOT)
    body = build_hh_hl_final_manifest(
        design_receipt=_design_receipt(),
        dataset_receipt=_dataset_receipt(),
        source_manifest=source,
    )
    on_disk = _load_manifest()
    assert body["manifest_fingerprint"] == on_disk["manifest_fingerprint"]
    # Distinct from immutable source draft fingerprint.
    assert body["source_manifest_fingerprint"] != body["manifest_fingerprint"]
    assert body["source_manifest_fingerprint"] == (
        "ab095923a795445ff41d319b1b3941412c9429d38128a5edd2256f4a777afa80"
    )
    assert body["execution_enabled"] is True
    assert body["campaign_execution_authorized"] is False
    assert body["requires_external_owner_go"] is True
    assert body["lr_status"] == "NO-GO"
    assert body["expected_run_count"] == 39


@pytest.mark.unit
def test_final_manifest_has_no_absolute_paths_and_no_execution_go_data():
    body = _load_manifest()
    blob = json.dumps(body)
    for marker in (":\\", "/home/", "/Users/", "C:/", "D:/"):
        assert marker not in blob
    assert "execution_sha" not in body
    assert "surface_capability_fingerprint" not in body
    assert "expires_at_utc" not in body


# --------------------------------------------------------------------------- #
# D) Run plan final / pre-final
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_final_run_plan_final_and_pre_final():
    final = _final_plan(POST_MERGE_SHA)
    assert final.status == "FINAL"
    assert final.post_merge_final is True
    assert final.expected_run_count == 39
    assert final.campaign_execution_authorized is False
    assert final.executable is False
    assert final.execution_sha is None

    pre = _final_plan(BASE_SHA, pre_final=True)
    assert pre.status == "PRE_FINALIZATION"
    assert pre.post_merge_final is False
    assert pre.executable is False
    # Different fingerprints for pre-final vs final (status + sha bound in body).
    assert pre.run_plan_fingerprint != final.run_plan_fingerprint


@pytest.mark.unit
def test_final_run_plan_requires_real_post_merge_sha():
    # Missing / non-sha planning_sha without pre_final → HOLD.
    with pytest.raises(CampaignProfileError, match="HOLD_POST_MERGE_MAIN_SHA_REQUIRED"):
        _final_plan("not-a-sha")
    # Re-using the pre-merge base as "final" is refused.
    with pytest.raises(CampaignProfileError, match="HOLD_POST_MERGE_MAIN_SHA_REQUIRED"):
        _final_plan(BASE_SHA)


# --------------------------------------------------------------------------- #
# E) Execution-GO verification + AuthorizationContext
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_execution_go_valid_mints_authorization_context():
    plan = _final_plan(POST_MERGE_SHA)
    payload = _exec_payload(run_plan_fp=plan.run_plan_fingerprint)
    verified = verify_owner_execution_go_comment(
        comment_id=987654321,
        expected=_expected_from_payload(payload),
        fetcher=_exec_fetcher(_exec_comment(payload)),
        now_utc=FIXED_NOW,
    )
    assert verified["valid"] is True
    ctx = authorization_context_from_verified_go(verified)
    assert isinstance(ctx, AuthorizationContext)
    assert ctx.run_plan_fingerprint == plan.run_plan_fingerprint
    assert ctx.granted_capabilities == (GRANTED_CAPABILITY,)


@pytest.mark.unit
def test_execution_go_rejects_wrong_go_type_mutation_and_expiry():
    plan = _final_plan(POST_MERGE_SHA)
    # Implementation-GO status must never satisfy the Execution-GO.
    impl = _exec_payload(
        run_plan_fp=plan.run_plan_fingerprint,
        status="GO_HH_HL_CONTINUATION_IMPLEMENTATION",
    )
    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_WRONG_GO_TYPE"
    ):
        verify_owner_execution_go_comment(
            comment_id=987654321,
            expected=_expected_from_payload(impl),
            fetcher=_exec_fetcher(_exec_comment(impl)),
            now_utc=FIXED_NOW,
        )

    ok = _exec_payload(run_plan_fp=plan.run_plan_fingerprint)
    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_COMMENT_MUTATED"
    ):
        verify_owner_execution_go_comment(
            comment_id=987654321,
            expected=_expected_from_payload(ok),
            fetcher=_exec_fetcher(_exec_comment(ok, updated="2026-08-06T16:05:00Z")),
            now_utc=FIXED_NOW,
        )

    expired = _exec_payload(
        run_plan_fp=plan.run_plan_fingerprint, expires="2026-08-06T00:00:00Z"
    )
    with pytest.raises(
        HhHlExecutionAuthorizationError, match="HOLD_EXECUTION_GO_EXPIRED"
    ):
        verify_owner_execution_go_comment(
            comment_id=987654321,
            expected=_expected_from_payload(expired),
            fetcher=_exec_fetcher(_exec_comment(expired)),
            now_utc=FIXED_NOW,
        )


@pytest.mark.unit
def test_authorization_context_factory_only():
    with pytest.raises(
        HhHlExecutionAuthorizationError,
        match="HOLD_EXECUTION_GO_CONTEXT_REQUIRES_VERIFIED_GO",
    ):
        authorization_context_from_verified_go({"valid": False})


# --------------------------------------------------------------------------- #
# F) Executor AuthorizationContext wiring
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_executor_holds_without_owner_go_even_with_replay_profile():
    profile = load_profile(HH_HL_REPLAY_PROFILE_ID)
    provider = HhHlSingleRunReplayProvider(
        profile, single_run_callable=lambda req: RunResult(exit_code=0)
    )
    plan = _final_plan(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    envelope = _run_envelope(ctx)
    with pytest.raises(CampaignProfileError, match="HOLD_EXECUTION_OWNER_GO_REQUIRED"):
        provider.execute(envelope, authorization_context=None)


@pytest.mark.unit
def test_executor_runs_injected_callable_with_valid_context():
    profile = load_profile(HH_HL_REPLAY_PROFILE_ID)
    calls: list = []

    def _fake_single_run(request):
        calls.append(request)
        return RunResult(exit_code=0, metrics={"gate_reason": "OK"})

    provider = HhHlSingleRunReplayProvider(
        profile, single_run_callable=_fake_single_run
    )
    plan = _final_plan(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    result = provider.execute(_run_envelope(ctx), authorization_context=ctx)
    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0]["scenario_group_id"] is None
    bindings = result.metrics["campaign_bindings"]
    assert bindings["authorization_fingerprint"] == ctx.authorization_fingerprint
    assert bindings["campaign_id"] == CAMPAIGN_ID


@pytest.mark.unit
def test_executor_refuses_pb1_and_scenario_group():
    profile = load_profile(HH_HL_REPLAY_PROFILE_ID)
    provider = HhHlSingleRunReplayProvider(
        profile, single_run_callable=lambda req: RunResult(exit_code=0)
    )
    plan = _final_plan(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    with pytest.raises(CampaignProfileError, match="HH_HL_ENVELOPE_STRATEGY_MISMATCH"):
        provider.execute(
            _run_envelope(ctx, strategy_id="primary_breakout_v1"),
            authorization_context=ctx,
        )
    with pytest.raises(CampaignProfileError, match="HH_HL_SCENARIO_GROUP_FORBIDDEN"):
        provider.execute(
            _run_envelope(ctx, parameters={"scenario_group_id": "x"}),
            authorization_context=ctx,
        )


@pytest.mark.unit
def test_prep_profile_resolves_planning_only_executor():
    prep = load_profile(HH_HL_PREP_PROFILE_ID)
    assert isinstance(resolve_campaign_executor(prep), PlanningOnlyExecutor)


# --------------------------------------------------------------------------- #
# G) Lifecycle adapter
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_validate_primary_run_keys_requires_exactly_39():
    plan = _final_plan(POST_MERGE_SHA)
    assert len(validate_primary_run_keys(plan.run_keys)) == 39
    with pytest.raises(
        HhHlLifecycleError, match="HH_HL_LIFECYCLE_RUN_KEY_COUNT_MISMATCH"
    ):
        validate_primary_run_keys(plan.run_keys[:-1])


@pytest.mark.unit
def test_bindings_from_authorization_and_evidence_namespace():
    plan = _final_plan(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    bindings = bindings_from_authorization(ctx)
    assert isinstance(bindings, CampaignBindings)
    assert bindings.campaign_id == CAMPAIGN_ID
    assert bindings.run_plan_fingerprint == plan.run_plan_fingerprint
    assert bindings.main_sha == POST_MERGE_SHA
    with pytest.raises(
        HhHlLifecycleError, match="HH_HL_LIFECYCLE_RUN_PLAN_FINGERPRINT_MISMATCH"
    ):
        bindings_from_authorization(ctx, run_plan_fingerprint="deadbeef")
    root = hh_hl_evidence_root_for(
        base=Path("/tmp"),
        campaign_id=CAMPAIGN_ID,
        manifest_fingerprint=ctx.manifest_fingerprint,
        authorization_id=ctx.authorization_fingerprint,
    )
    assert HH_HL_EVIDENCE_NAMESPACE in root.as_posix()
    assert "arvp_sensitivity/4153" not in root.as_posix()


# Filesystem-safe synthetic keys for state-writing sub-tests. Real run keys use
# a ``|`` separator which is legal on the Linux runner but not a valid Windows
# directory name; the lifecycle composition under test is independent of the key
# format (keys are opaque directory tokens to the state layer).
_SAFE_KEYS = tuple(f"rk-{i:02d}" for i in range(39))


@pytest.mark.unit
def test_plan_resume_actions_skip_and_running_without_marker(tmp_path: Path):
    plan = _final_plan(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    bindings = bindings_from_authorization(ctx)
    write_campaign_envelope(tmp_path, bindings=bindings, run_count=39)

    keys = list(_SAFE_KEYS)
    # Fresh namespace → every run planned to start.
    actions = plan_resume_actions(tmp_path, bindings=bindings, run_keys=keys)
    assert set(actions.values()) == {"start"}

    # A committed successful run resumes as skip.
    commit_successful_result(
        tmp_path,
        run_key=keys[0],
        bindings=bindings,
        attempt=1,
        envelope={"run_key": keys[0]},
        result={"gate_reason": "OK"},
    )
    actions = plan_resume_actions(tmp_path, bindings=bindings, run_keys=keys)
    assert actions[keys[0]] == "skip"

    # RUNNING without a completion marker fails closed.
    write_run_envelope(
        tmp_path,
        run_key=keys[1],
        bindings=bindings,
        status="RUNNING",
        attempt=1,
        envelope={"run_key": keys[1]},
    )
    with pytest.raises(SensitivityStateError, match="STATE_RUNNING_WITHOUT_COMPLETION"):
        plan_resume_actions(tmp_path, bindings=bindings, run_keys=keys)


@pytest.mark.unit
def test_plan_resume_actions_refuses_binding_mismatch(tmp_path: Path):
    plan = _final_plan(POST_MERGE_SHA)
    ctx = _verified_context(plan.run_plan_fingerprint)
    bindings = bindings_from_authorization(ctx)
    keys = list(_SAFE_KEYS)
    write_campaign_envelope(tmp_path, bindings=bindings, run_count=39)
    write_run_envelope(
        tmp_path,
        run_key=keys[0],
        bindings=bindings,
        status="PLANNED",
        attempt=1,
        envelope={"run_key": keys[0]},
    )
    drift = CampaignBindings(
        campaign_id=bindings.campaign_id,
        manifest_fingerprint="f" * 64,
        run_plan_fingerprint=bindings.run_plan_fingerprint,
        authorization_fingerprint=bindings.authorization_fingerprint,
        execution_sha=bindings.execution_sha,
        main_sha=bindings.main_sha,
    )
    with pytest.raises(SensitivityStateError, match="STATE_BINDING_MISMATCH"):
        plan_resume_actions(tmp_path, bindings=drift, run_keys=keys)


# --------------------------------------------------------------------------- #
# D/CLI) Write-free CLI + fail-closed probes
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_cli_verify_design_go_fixture(tmp_path: Path, capsys):
    payload = canonical_design_go_payload(
        bound_main_sha=BASE_SHA,
        comment_id=VERIFIED_DESIGN_GO_COMMENT_ID,
        repo_root=PROJECT_ROOT,
    )
    fixture = {
        "id": VERIFIED_DESIGN_GO_COMMENT_ID,
        "issue_number": 4374,
        "user": {"login": "jannekbuengener"},
        "body": "```json\n" + json.dumps(payload) + "\n```",
        "created_at": "2026-08-06T15:08:54Z",
        "updated_at": "2026-08-06T15:08:54Z",
    }
    path = tmp_path / "design_go.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "verify-design-go",
            "--comment-id",
            str(VERIFIED_DESIGN_GO_COMMENT_ID),
            "--fixture-json",
            str(path),
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["valid"] is True
    assert out["writes"] is False
    assert out["replays"] is False


@pytest.mark.unit
def test_cli_build_final_manifest_matches_on_disk(tmp_path: Path, capsys):
    rc = cli.main(["--repo-root", str(PROJECT_ROOT), "build-final-manifest"])
    out = _capture(capsys)
    assert rc == 0
    assert out["ok"] is True
    assert out["manifest_fingerprint"] == _load_manifest()["manifest_fingerprint"]
    assert out["campaign_execution_authorized"] is False
    assert out["writes"] is False

    target = tmp_path / "final.json"
    rc = cli.main(
        ["--repo-root", str(PROJECT_ROOT), "build-final-manifest", "--out", str(target)]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["writes"] is True
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["manifest_fingerprint"] == (
        out["manifest_fingerprint"]
    )


@pytest.mark.unit
def test_cli_finalize_plan_pre_final_and_final(capsys):
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "finalize-plan",
            "--pre-final",
            "--planning-sha",
            BASE_SHA,
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["status"] == "PRE_FINALIZATION"
    assert out["campaign_execution_authorized"] is False
    assert out["execution_sha"] is None
    assert out["writes"] is False

    # FINAL always runs the live-main gate. Offline tests inject a private
    # resolver (no public CLI skip flag) so planning_sha == origin/main tip.
    sha_gate._test_set_sha_resolver_override(_fake_live_main_resolver())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "finalize-plan",
            "--planning-sha",
            POST_MERGE_SHA,
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["status"] == "FINAL"

    # Re-using the design-bound pre-merge base as "final" is refused by the
    # always-on live-main gate (format/distinct + tip mismatch).
    sha_gate._test_set_sha_resolver_override(
        _fake_live_main_resolver(main_tip=POST_MERGE_SHA)
    )
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "finalize-plan",
            "--planning-sha",
            BASE_SHA,
        ]
    )
    out = _capture(capsys)
    assert rc == 1
    assert out["reason_code"] == "HOLD_POST_MERGE_MAIN_SHA_REQUIRED"


@pytest.mark.unit
def test_cli_prepare_execution_go_surface_required_then_ok(tmp_path: Path, capsys):
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "prepare-execution-go",
            "--planning-sha",
            POST_MERGE_SHA,
            "--execution-sha",
            EXECUTION_SHA,
            "--expires-at-utc",
            FAR_FUTURE,
        ]
    )
    out = _capture(capsys)
    assert rc == 1
    assert out["reason_code"] == "HOLD_EXECUTION_SURFACE_PROOF_REQUIRED"

    # A complete, fingerprint-bound, owner-GO-eligible surface receipt (a bare
    # {surface_id, fingerprint} stub is rejected — see the hardening suite).
    surface = _write_surface_receipt(tmp_path / "surface.json")
    sha_gate._test_set_sha_resolver_override(_fake_live_main_resolver())
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "prepare-execution-go",
            "--planning-sha",
            POST_MERGE_SHA,
            "--execution-sha",
            EXECUTION_SHA,
            "--surface-receipt",
            str(surface),
            "--expires-at-utc",
            FAR_FUTURE,
        ]
    )
    out = _capture(capsys)
    assert rc == 0
    assert out["ready_for_owner_execution_go"] is True
    assert out["campaign_execution_authorized"] is False
    assert out["github_comment_id"] is None
    assert out["execution_go_payload"]["expected_run_count"] == 39
    # The assembled pre-post package carries the full hardened contract.
    payload = out["execution_go_payload"]
    assert payload["authorizes"] == list(AUTHORIZES_EXACT)
    assert set(REQUIRED_DOES_NOT_AUTHORIZE).issubset(payload["does_not_authorize"])
    assert payload["max_run_count"] == MAX_RUN_COUNT
    assert "github_comment_id" not in payload


@pytest.mark.unit
def test_cli_prepare_execution_go_holds_without_post_merge_sha(tmp_path: Path, capsys):
    # A full, valid, owner-GO-eligible surface receipt so the surface gate
    # passes and the *post-merge SHA* gate is the reached failure: re-using the
    # design-bound pre-merge base SHA as "final" is refused.
    surface = _write_surface_receipt(tmp_path / "surface.json")
    sha_gate._test_set_sha_resolver_override(
        _fake_live_main_resolver(main_tip=POST_MERGE_SHA)
    )
    rc = cli.main(
        [
            "--repo-root",
            str(PROJECT_ROOT),
            "prepare-execution-go",
            "--planning-sha",
            BASE_SHA,
            "--execution-sha",
            EXECUTION_SHA,
            "--surface-receipt",
            str(surface),
            "--expires-at-utc",
            FAR_FUTURE,
        ]
    )
    out = _capture(capsys)
    assert rc == 1
    assert out["reason_code"] == "HOLD_POST_MERGE_MAIN_SHA_REQUIRED"


@pytest.mark.unit
def test_cli_probe_surface_fixture_and_negative_execute_probe(capsys):
    rc = cli.main(["probe-surface", "--fixture"])
    out = _capture(capsys)
    assert rc == 0
    assert out["replays"] is False
    assert out["probed"] is True

    rc = cli.main(["negative-execute-probe"])
    out = _capture(capsys)
    assert rc == 0
    assert out["ok"] is True
    assert out["replays"] is False
    assert all(p["pass"] for p in out["probes"])
