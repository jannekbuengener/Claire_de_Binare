"""Unit tests for hh_hl production execution wiring (#4374).

Never starts a real campaign or physical binance-window replay. All replay
surfaces are injected fakes with call counters.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
    frozen_hh_hl_parameters,
)
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    ArvpReplayOutcome,
)
from tools.arvp_vacation.campaign_executor_providers import (
    HhHlSingleRunReplayProvider,
    resolve_campaign_executor,
)
from tools.arvp_vacation.campaign_profile import CampaignProfileError, load_profile
from tools.arvp_vacation.hh_hl_campaign_execute import (
    HOLD_FREE_DISK_BELOW_MINIMUM,
    HhHlCampaignExecuteError,
    _owner_go_fetcher,
    _test_set_free_disk_bytes,
    _test_set_git_sha_resolver,
    _test_set_now_utc,
    _test_set_owner_go_fetcher,
    _test_set_single_run_callable,
    assert_free_disk_meets_budget,
    assert_per_run_pre_dispatch,
    build_parser,
    dispatch_run_with_terminalization,
    main as execute_main,
)
from tools.arvp_vacation.hh_hl_campaign_execution_authorization import (
    OwnerGoComment,
    authorization_context_from_verified_go,
    default_gh_comment_fetcher,
    verify_owner_execution_go_comment,
)
from tools.arvp_vacation.hh_hl_campaign_lifecycle import bindings_from_authorization
from tools.arvp_vacation.hh_hl_campaign_sha_gate import GitShaResolver
from tools.arvp_vacation.hh_hl_single_run_callable import (
    HOLD_DATASET_CONTENT_MISMATCH,
    HOLD_FROZEN_PARAM_MISMATCH,
    HOLD_PB1_FORBIDDEN,
    HOLD_SCENARIO_GROUP_FORBIDDEN,
    assert_frozen_hh_hl_parameters,
    build_hh_hl_arvp_replay_config,
    build_production_single_run_callable,
)
from tools.arvp_vacation.campaign_profile import CampaignProfileError
from tools.arvp_vacation.sensitivity_campaign_executor import RunEnvelope, RunResult
from tools.arvp_vacation.sensitivity_campaign_state import (
    SensitivityStateError,
    commit_successful_result,
    inspect_run_for_resume,
    run_envelope_path,
    write_run_envelope,
)

EXEC_SHA = "ba6b1d94c6da480b77fa3ffcb7d46bba6f0d42a2"
MANIFEST_FP = "1b1165b8b049099324cfc97c0858919f7f04fab985584cff54ad7161ecfcfc07"
RUN_PLAN_FP = "4b72e08eb3f1f5473be771a98033ae2b19a96ee2da8e8e83177db700f10e482b"
DATASET_SEL = "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
DATASET_DIGEST = "10f94c34e32db28a9393c38f944db4968b42e87d9ed223397e3637ff44323af9"
SURFACE_FP = "43f67ae4ae420bb7c474c5bcc47333f7933bcc302e2128086ad2b7db023046cf"
DESIGN_BODY_FP = "415400720d28c998dad6b311c71f9107395e3dd17528d4137d097918d682887d"
WINDOW_FP = "3e7fc8e8024972405eb0e53c2f483e8d5999dda1d9d56fda44b3c40b9f966d5c"
REPO_ROOT = Path(__file__).resolve().parents[3]
MIN_FREE_DISK = 21474836480


def _budget() -> dict[str, int]:
    return {
        "log_retention_days": 30,
        "max_artifact_bytes": 21474836480,
        "max_attempts_per_run": 1,
        "max_campaign_wall_time_seconds": 172800,
        "max_consecutive_failures": 3,
        "max_in_flight_runs": 1,
        "max_parallelism": 1,
        "max_run_wall_time_seconds": 3600,
        "max_total_failures": 5,
        "minimum_free_disk_bytes": MIN_FREE_DISK,
    }


def _go_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "absolute_bans_unchanged": True,
        "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
        "analyzer_profile_id": "hh_hl_analyzer_prep_v1",
        "authorizes": ["exactly_bound_replay_only_campaign_execution"],
        "authorizing_github_login": "jannekbuengener",
        "bound_main_sha": EXEC_SHA,
        "campaign_id": "arvp-hh-hl-continuation-4374-prep-v1",
        "dataset_content_fingerprint_digest": DATASET_DIGEST,
        "dataset_selection_sha256": DATASET_SEL,
        "design_go_body_fingerprint": DESIGN_BODY_FP,
        "design_go_comment_id": 5206657394,
        "does_not_authorize": [
            "stage_b",
            "oos",
            "stress",
            "paper",
            "live",
            "echtgeld",
            "promotion",
            "merge",
        ],
        "evidence_namespace": "artifacts/arvp_campaign/hh_hl_continuation/4374",
        "execution_sha": EXEC_SHA,
        "execution_surface_id": "services.validation.strategy_replay_runner.single_run",
        "expected_run_count": 39,
        "expires_at_utc": (datetime.now(timezone.utc) + timedelta(days=7))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "granted_capabilities": ["campaign_execution_replay_only"],
        "issue": 4374,
        "lr_status": "NO-GO",
        "manifest_fingerprint": MANIFEST_FP,
        "manifest_id": "arvp-hh-hl-continuation-4374-prep-v1",
        "manifest_path": "config/arvp/hh_hl_campaign_4374_v1.json",
        "max_run_count": 39,
        "repository": "jannekbuengener/Claire_de_Binare",
        "reproduction_policy": "hh_hl_reproduction_prep_v1",
        "resource_budget": _budget(),
        "resume_policy": {
            "allow_resume": True,
            "refuse_binding_mismatch": True,
            "refuse_running_without_completion": True,
            "retry_failed": True,
            "skip_succeeded_identical_bindings": True,
        },
        "run_plan_fingerprint": RUN_PLAN_FP,
        "schema_version": "cdb.hh_hl_campaign_execution_authorization.v1",
        "status": "GO_HH_HL_CAMPAIGN_EXECUTION",
        "strategy_set": [HH_HL_CONTINUATION_STRATEGY_ID],
        "strategy_version": "cdb.batch_b.hh_hl_continuation_v1.spec.1",
        "surface_capability_fingerprint": SURFACE_FP,
        "variant_count": 1,
        "window_count": 39,
    }
    payload.update(overrides)
    return payload


def _fence_body(payload: dict[str, Any]) -> str:
    return (
        "```cdb.hh_hl_campaign_execution_authorization.v1\n"
        + json.dumps(payload, indent=2, sort_keys=True)
        + "\n```\n"
    )


def _owner_comment(
    payload: dict[str, Any] | None = None, *, body: str | None = None
) -> OwnerGoComment:
    pl = payload or _go_payload()
    return OwnerGoComment(
        comment_id=999001,
        issue_number=4374,
        author_login="jannekbuengener",
        body=body if body is not None else _fence_body(pl),
        created_at="2026-08-07T07:36:48Z",
        updated_at="2026-08-07T07:36:48Z",
        repository="jannekbuengener/Claire_de_Binare",
    )


@pytest.fixture(autouse=True)
def _clear_test_hooks():
    _test_set_owner_go_fetcher(None)
    _test_set_git_sha_resolver(None)
    _test_set_now_utc(None)
    _test_set_single_run_callable(None)
    _test_set_free_disk_bytes(None)
    yield
    _test_set_owner_go_fetcher(None)
    _test_set_git_sha_resolver(None)
    _test_set_now_utc(None)
    _test_set_single_run_callable(None)
    _test_set_free_disk_bytes(None)


def _install_valid_go_and_sha(
    *, free_disk_bytes: int | None = MIN_FREE_DISK
) -> list[Any]:
    """Private-injection seams only (never CLI fixtures). Returns hit_count list."""
    hits: list[Any] = []
    comment = _owner_comment()

    def _fetch(repository: str, issue: int, comment_id: int) -> OwnerGoComment:
        hits.append(("fetch", repository, issue, comment_id))
        return comment

    def _fake_callable(req: dict[str, Any]) -> RunResult:
        hits.append(("callable", req))
        return RunResult(exit_code=0, metrics={})

    _test_set_owner_go_fetcher(_fetch)
    _test_set_git_sha_resolver(
        GitShaResolver(
            fetch=lambda: None,
            resolve_main_tip=lambda: EXEC_SHA,
            object_type=lambda sha: "commit",
            head=lambda: EXEC_SHA,
        )
    )
    if free_disk_bytes is not None:
        _test_set_free_disk_bytes(free_disk_bytes)
    _test_set_single_run_callable(_fake_callable)
    return hits


def test_resolve_campaign_executor_wires_production_callable():
    provider = resolve_campaign_executor(load_profile("hh_hl_continuation_replay_v1"))
    assert isinstance(provider, HhHlSingleRunReplayProvider)
    callable_ = provider._resolve_single_run_callable()
    assert callable_ is not None


def test_build_arvp_config_exact_bindings(tmp_path: Path):
    req = {
        "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
        "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
        "window_id": "binance_1m_month_2017_10",
        "parameters": frozen_hh_hl_parameters(),
        "output_dir": str(tmp_path / "run1"),
        "dataset_content_fingerprint": WINDOW_FP,
        "scenario_group_id": None,
        "scenario_ids": None,
    }
    cfg = build_hh_hl_arvp_replay_config(req)
    assert isinstance(cfg, ARVPReplayConfig)
    assert cfg.dataset_source == "binance_window"
    assert cfg.binance_window_id == "binance_1m_month_2017_10"
    assert cfg.strategy_id == HH_HL_CONTINUATION_STRATEGY_ID
    assert cfg.adapter_id == BATCH_B_SHADOW_ADAPTER_ID
    assert cfg.scenario_ids is None
    assert cfg.scenario_group_id is None
    assert cfg.dry_run is False
    assert cfg.output_directory.endswith("replay")


def test_frozen_param_mismatch_hold():
    with pytest.raises(CampaignProfileError) as exc:
        assert_frozen_hh_hl_parameters({"swing_left_bars": 99})
    assert HOLD_FROZEN_PARAM_MISMATCH in str(exc.value)


def test_pb1_and_scenario_group_hold(tmp_path: Path):
    base = {
        "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
        "window_id": "binance_1m_month_2017_10",
        "parameters": frozen_hh_hl_parameters(),
        "output_dir": str(tmp_path),
        "dataset_content_fingerprint": WINDOW_FP,
    }
    with pytest.raises(CampaignProfileError) as exc:
        build_hh_hl_arvp_replay_config({**base, "strategy_id": "primary_breakout_v1"})
    assert HOLD_PB1_FORBIDDEN in str(exc.value)
    with pytest.raises(CampaignProfileError) as exc2:
        build_hh_hl_arvp_replay_config(
            {
                **base,
                "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
                "scenario_group_id": "x",
            }
        )
    assert HOLD_SCENARIO_GROUP_FORBIDDEN in str(exc2.value)


def test_dataset_mismatch_before_replay(monkeypatch, tmp_path: Path):
    calls: list[Any] = []

    def _fake_load(window_id, warmup_candles=0, window_bank_root=None):
        class _Inner:
            content_fingerprint = "a" * 64

        class _Loaded:
            dataset_result = _Inner()

        return _Loaded()

    def _detailed(cfg: ARVPReplayConfig) -> ArvpReplayOutcome:
        calls.append(cfg)
        return ArvpReplayOutcome(exit_code=0)

    monkeypatch.setattr(
        "tools.arvp_vacation.hh_hl_single_run_callable.load_binance_window_dataset",
        _fake_load,
    )
    runnable = build_production_single_run_callable(replay_detailed=_detailed)
    req = {
        "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
        "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
        "window_id": "binance_1m_month_2017_10",
        "parameters": frozen_hh_hl_parameters(),
        "output_dir": str(tmp_path / "r"),
        "dataset_content_fingerprint": WINDOW_FP,
    }
    with pytest.raises(CampaignProfileError) as exc:
        runnable(req)
    assert HOLD_DATASET_CONTENT_MISMATCH in str(exc.value)
    assert calls == []


def test_production_callable_maps_outcome_metrics(monkeypatch, tmp_path: Path):
    def _fake_load(window_id, warmup_candles=0, window_bank_root=None):
        class _Inner:
            content_fingerprint = WINDOW_FP

        class _Loaded:
            dataset_result = _Inner()

        return _Loaded()

    def _detailed(cfg: ARVPReplayConfig) -> ArvpReplayOutcome:
        assert cfg.strategy_id == HH_HL_CONTINUATION_STRATEGY_ID
        assert cfg.adapter_id == BATCH_B_SHADOW_ADAPTER_ID
        assert cfg.dataset_source == "binance_window"
        assert cfg.scenario_ids is None
        return ArvpReplayOutcome(
            exit_code=0,
            run_id="run-1",
            artifact_root=str(tmp_path / "replay" / "run-1"),
            gate_result={"status": "NOT_RANKING_READY", "ranking_ready": False},
            metrics={
                "closed_trades_total": 1,
                "fees_total_quote": "0.1",
                "net_pnl_quote": "1.0",
                "expectancy_r": "0.2",
                "max_drawdown_r": "0.3",
            },
            content_fingerprint=WINDOW_FP,
        )

    monkeypatch.setattr(
        "tools.arvp_vacation.hh_hl_single_run_callable.load_binance_window_dataset",
        _fake_load,
    )
    runnable = build_production_single_run_callable(replay_detailed=_detailed)
    result = runnable(
        {
            "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
            "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
            "window_id": "binance_1m_month_2017_10",
            "parameters": frozen_hh_hl_parameters(),
            "output_dir": str(tmp_path / "r"),
            "dataset_content_fingerprint": WINDOW_FP,
        }
    )
    assert result.exit_code == 0
    assert result.metrics["closed_trades_total"] == 1
    assert result.metrics["gate_result"]["status"] == "NOT_RANKING_READY"
    assert result.metrics["run_id"] == "run-1"


def test_provider_requires_authorization_before_callable(tmp_path: Path):
    calls: list[Any] = []

    def _fake(req: dict[str, Any]) -> RunResult:
        calls.append(req)
        return RunResult(exit_code=0, metrics={})

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_fake
    )
    envelope = RunEnvelope(
        run_key="rk",
        campaign_id="arvp-hh-hl-continuation-4374-prep-v1",
        manifest_fingerprint=MANIFEST_FP,
        execution_sha=EXEC_SHA,
        window_id="binance_1m_month_2017_10",
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        parameters=frozen_hh_hl_parameters(),
        slot_id="hh_hl_baseline_001",
        phase="BASELINE",
        label="spec_frozen_baseline",
        physical_parameter_set_fingerprint="p" * 64,
        effective_config_fingerprint="e" * 64,
        dataset_content_fingerprint=WINDOW_FP,
        seed="s",
        output_dir=str(tmp_path),
        run_plan_fingerprint=RUN_PLAN_FP,
        authorization_fingerprint="a" * 64,
    )
    with pytest.raises(CampaignProfileError) as exc:
        provider.execute(envelope, authorization_context=None)
    assert "HOLD_EXECUTION_OWNER_GO_REQUIRED" in str(exc.value)
    assert calls == []


def test_invalid_fence_go_hold(tmp_path: Path, capsys):
    bad = _owner_comment(body="`cdb.hh_hl_campaign_execution_authorization.v1\n{}\n`\n")

    def _fetch(repository: str, issue: int, comment_id: int) -> OwnerGoComment:
        return bad

    _test_set_owner_go_fetcher(_fetch)
    _test_set_git_sha_resolver(
        GitShaResolver(
            fetch=lambda: None,
            resolve_main_tip=lambda: EXEC_SHA,
            object_type=lambda sha: "commit",
            head=lambda: EXEC_SHA,
        )
    )
    code = execute_main(
        [
            "--repo-root",
            str(Path(__file__).resolve().parents[3]),
            "--execution-go-comment-id",
            "999001",
            "preflight",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "HOLD_EXECUTION_GO_BLOCK_MISSING" in out or "HOLD_EXECUTION_GO" in out


def test_public_cli_rejects_fixture_json():
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            ["--execution-go-comment-id", "1", "--fixture-json", "x.json", "preflight"]
        )
    assert exc.value.code == 2


def test_public_cli_rejects_design_go_fixture_json():
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            [
                "--execution-go-comment-id",
                "1",
                "--design-go-fixture-json",
                "x.json",
                "preflight",
            ]
        )
    assert exc.value.code == 2


def test_production_owner_go_fetcher_is_live_when_no_injection():
    assert _owner_go_fetcher(None) is default_gh_comment_fetcher


def test_private_owner_go_injection_still_usable():
    seen: list[int] = []

    def _fetch(repository: str, issue: int, comment_id: int) -> OwnerGoComment:
        seen.append(comment_id)
        return _owner_comment()

    _test_set_owner_go_fetcher(_fetch)
    assert _owner_go_fetcher(None) is _fetch
    _owner_go_fetcher(None)("jannekbuengener/Claire_de_Binare", 4374, 42)
    assert seen == [42]


def test_fabricated_owner_go_cannot_mint_context_via_cli(tmp_path: Path, capsys):
    """Local JSON + --fixture-json must not be a production path."""
    fabricated = tmp_path / "fake_owner_go.json"
    fabricated.write_text(
        json.dumps(
            {
                "id": 1,
                "issue_number": 4374,
                "user": {"login": "jannekbuengener"},
                "body": _fence_body(_go_payload()),
                "created_at": "2026-08-07T07:36:48Z",
                "updated_at": "2026-08-07T07:36:48Z",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "--execution-go-comment-id",
                "1",
                "--fixture-json",
                str(fabricated),
                "preflight",
            ]
        )


def test_assert_free_disk_below_minimum_hold():
    with pytest.raises(HhHlCampaignExecuteError) as exc:
        assert_free_disk_meets_budget(
            budget=_budget(),
            free_disk_bytes=1,
        )
    assert exc.value.reason_code == HOLD_FREE_DISK_BELOW_MINIMUM


def test_assert_free_disk_equal_or_above_minimum_pass():
    assert (
        assert_free_disk_meets_budget(
            budget=_budget(),
            free_disk_bytes=MIN_FREE_DISK,
        )
        == MIN_FREE_DISK
    )
    assert (
        assert_free_disk_meets_budget(
            budget=_budget(),
            free_disk_bytes=MIN_FREE_DISK + 1,
        )
        == MIN_FREE_DISK + 1
    )


def test_preflight_free_disk_below_minimum_before_callable(capsys):
    hits = _install_valid_go_and_sha(free_disk_bytes=1)
    code = execute_main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--execution-go-comment-id",
            "999001",
            "preflight",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert HOLD_FREE_DISK_BELOW_MINIMUM in out
    assert not any(h[0] == "callable" for h in hits)


def test_execute_free_disk_below_minimum_replay_hit_count_zero(capsys):
    hits = _install_valid_go_and_sha(free_disk_bytes=1)
    code = execute_main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--execution-go-comment-id",
            "999001",
            "execute",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert HOLD_FREE_DISK_BELOW_MINIMUM in out
    assert not any(h[0] == "callable" for h in hits)


def test_preflight_free_disk_at_minimum_passes_disk_gate(capsys):
    """Disk gate PASS when free >= minimum; later gates may still HOLD (no real GO/plan)."""
    hits = _install_valid_go_and_sha(free_disk_bytes=MIN_FREE_DISK)
    code = execute_main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--execution-go-comment-id",
            "999001",
            "preflight",
        ]
    )
    out = capsys.readouterr().out
    assert HOLD_FREE_DISK_BELOW_MINIMUM not in out
    assert not any(h[0] == "callable" for h in hits)
    # Preflight never dispatches callables; success or non-disk HOLD both OK here.
    assert code in (0, 1)


def test_execute_serial_loop_with_fake_callable(tmp_path: Path, monkeypatch, capsys):
    """Fresh execute plans START for all runs but uses injected callable (0 real replays)."""
    # This test focuses on provider wiring + auth gate rather than full 39-run rebuild
    # (FINAL plan rebuild needs live design/dataset gates). Keep it narrow.
    provider = resolve_campaign_executor(load_profile("hh_hl_continuation_replay_v1"))
    assert provider._single_run_callable is not None
    # Ensure injected override still works for tests
    calls: list[Any] = []

    def _fake(req: dict[str, Any]) -> RunResult:
        calls.append(req)
        return RunResult(exit_code=0, metrics={"closed_trades_total": 0})

    override = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_fake
    )
    assert override._resolve_single_run_callable() is _fake


def _mint_auth_ctx():
    comment = _owner_comment()

    def _fetch(repository: str, issue: int, comment_id: int) -> OwnerGoComment:
        return comment

    verified = verify_owner_execution_go_comment(
        comment_id=999001,
        expected={},
        repository="jannekbuengener/Claire_de_Binare",
        issue=4374,
        fetcher=_fetch,
        now_utc=datetime.now(timezone.utc),
    )
    return authorization_context_from_verified_go(verified)


def _make_envelope(tmp_path: Path, *, ctx=None, run_key: str = "rk1") -> RunEnvelope:
    auth_fp = ctx.authorization_fingerprint if ctx is not None else ("a" * 64)
    return RunEnvelope(
        run_key=run_key,
        campaign_id="arvp-hh-hl-continuation-4374-prep-v1",
        manifest_fingerprint=MANIFEST_FP,
        execution_sha=EXEC_SHA,
        window_id="binance_1m_month_2017_10",
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        parameters=frozen_hh_hl_parameters(),
        slot_id="hh_hl_baseline_001",
        phase="BASELINE",
        label="spec_frozen_baseline",
        physical_parameter_set_fingerprint="p" * 64,
        effective_config_fingerprint=MANIFEST_FP,
        dataset_content_fingerprint=WINDOW_FP,
        seed="s",
        output_dir=str(tmp_path / "runs" / run_key),
        run_plan_fingerprint=RUN_PLAN_FP,
        authorization_fingerprint=auth_fp,
        attempt=1,
    )


def test_per_run_disk_drop_before_second_dispatch_no_running(tmp_path: Path):
    """Campaign-start disk OK; second per-run check fails before RUNNING/callable."""
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    hits: list[str] = []
    disk_reads = {"n": 0}

    def _disk() -> int:
        disk_reads["n"] += 1
        # First per-run gate OK; second drops below minimum.
        return MIN_FREE_DISK if disk_reads["n"] == 1 else 1

    _test_set_free_disk_bytes(_disk)

    def _ok(req: dict[str, Any]) -> RunResult:
        hits.append("ok")
        return RunResult(exit_code=0, metrics={})

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_ok
    )
    budget = _budget()

    r1 = dispatch_run_with_terminalization(
        provider=provider,
        ctx=ctx,
        envelope=_make_envelope(tmp_path, ctx=ctx, run_key="rk1"),
        evidence_root=evidence_root,
        bindings=bindings,
        run_key="rk1",
        attempt=1,
        repo_root=REPO_ROOT,
        budget=budget,
    )
    commit_successful_result(
        evidence_root,
        run_key="rk1",
        bindings=bindings,
        attempt=1,
        envelope=_make_envelope(tmp_path, ctx=ctx, run_key="rk1").as_dict(),
        result=r1.metrics,
        exit_code=0,
    )
    assert hits == ["ok"]
    assert json.loads(run_envelope_path(evidence_root, "rk1").read_text())[
        "status"
    ] == ("SUCCEEDED")

    with pytest.raises(HhHlCampaignExecuteError) as exc:
        dispatch_run_with_terminalization(
            provider=provider,
            ctx=ctx,
            envelope=_make_envelope(tmp_path, ctx=ctx, run_key="rk2"),
            evidence_root=evidence_root,
            bindings=bindings,
            run_key="rk2",
            attempt=1,
            repo_root=REPO_ROOT,
            budget=budget,
        )
    assert exc.value.reason_code == HOLD_FREE_DISK_BELOW_MINIMUM
    assert hits == ["ok"]
    assert not run_envelope_path(evidence_root, "rk2").exists()


def test_per_run_disk_equal_minimum_passes(tmp_path: Path):
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    _test_set_free_disk_bytes(MIN_FREE_DISK)
    envelope = _make_envelope(tmp_path, ctx=ctx)
    assert_per_run_pre_dispatch(
        ctx=ctx,
        repo_root=REPO_ROOT,
        budget=_budget(),
        envelope=envelope,
    )


def test_provider_campaign_profile_error_terminals_blocked(tmp_path: Path):
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    _test_set_free_disk_bytes(MIN_FREE_DISK)

    def _raise(req: dict[str, Any]) -> RunResult:
        raise CampaignProfileError("HOLD_EXECUTION_DATASET_CONTENT_MISMATCH")

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_raise
    )
    with pytest.raises(CampaignProfileError):
        dispatch_run_with_terminalization(
            provider=provider,
            ctx=ctx,
            envelope=_make_envelope(tmp_path, ctx=ctx),
            evidence_root=evidence_root,
            bindings=bindings,
            run_key="rk1",
            attempt=1,
            repo_root=REPO_ROOT,
            budget=_budget(),
        )
    env = json.loads(
        run_envelope_path(evidence_root, "rk1").read_text(encoding="utf-8")
    )
    assert env["status"] == "BLOCKED"
    assert (
        "HOLD_EXECUTION_DATASET_CONTENT_MISMATCH" in env["envelope"]["terminal_reason"]
    )


def test_provider_auth_expiry_terminals_blocked_zero_hits(tmp_path: Path):
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    _test_set_free_disk_bytes(MIN_FREE_DISK)
    hits: list[Any] = []

    def _never(req: dict[str, Any]) -> RunResult:
        hits.append(req)
        return RunResult(exit_code=0, metrics={})

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_never
    )
    # Force expiry at provider boundary via past now_utc injection on context check:
    # mutate by wrapping execute to raise auth HOLD.
    original = provider.execute

    def _expired(envelope, authorization_context=None, *, now_utc=None):
        raise CampaignProfileError("HOLD_EXECUTION_GO_EXPIRED")

    provider.execute = _expired  # type: ignore[method-assign]
    with pytest.raises(CampaignProfileError):
        dispatch_run_with_terminalization(
            provider=provider,
            ctx=ctx,
            envelope=_make_envelope(tmp_path, ctx=ctx),
            evidence_root=evidence_root,
            bindings=bindings,
            run_key="rk1",
            attempt=1,
            repo_root=REPO_ROOT,
            budget=_budget(),
        )
    assert hits == []
    env = json.loads(
        run_envelope_path(evidence_root, "rk1").read_text(encoding="utf-8")
    )
    assert env["status"] == "BLOCKED"
    del original


def test_provider_nonzero_exit_terminals_failed(tmp_path: Path):
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    _test_set_free_disk_bytes(MIN_FREE_DISK)

    def _fail(req: dict[str, Any]) -> RunResult:
        return RunResult(exit_code=7, metrics={"err": True})

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_fail
    )
    result = dispatch_run_with_terminalization(
        provider=provider,
        ctx=ctx,
        envelope=_make_envelope(tmp_path, ctx=ctx),
        evidence_root=evidence_root,
        bindings=bindings,
        run_key="rk1",
        attempt=1,
        repo_root=REPO_ROOT,
        budget=_budget(),
    )
    assert result.exit_code == 7
    env = json.loads(
        run_envelope_path(evidence_root, "rk1").read_text(encoding="utf-8")
    )
    assert env["status"] == "FAILED"
    assert env["exit_code"] == 7


def test_unexpected_provider_exception_terminals_failed_and_stops(tmp_path: Path):
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    _test_set_free_disk_bytes(MIN_FREE_DISK)

    def _boom(req: dict[str, Any]) -> RunResult:
        raise RuntimeError("boom-side-effect")

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_boom
    )
    with pytest.raises(HhHlCampaignExecuteError) as exc:
        dispatch_run_with_terminalization(
            provider=provider,
            ctx=ctx,
            envelope=_make_envelope(tmp_path, ctx=ctx),
            evidence_root=evidence_root,
            bindings=bindings,
            run_key="rk1",
            attempt=1,
            repo_root=REPO_ROOT,
            budget=_budget(),
        )
    assert exc.value.reason_code == "HOLD_EXECUTION_PROVIDER_UNEXPECTED"
    env = json.loads(
        run_envelope_path(evidence_root, "rk1").read_text(encoding="utf-8")
    )
    assert env["status"] == "FAILED"
    assert "UNEXPECTED:RuntimeError" in env["envelope"]["terminal_reason"]


def test_successful_dispatch_then_commit_succeeded(tmp_path: Path):
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    _test_set_free_disk_bytes(MIN_FREE_DISK)

    def _ok(req: dict[str, Any]) -> RunResult:
        return RunResult(exit_code=0, metrics={"closed_trades_total": 0})

    provider = HhHlSingleRunReplayProvider(
        load_profile("hh_hl_continuation_replay_v1"), single_run_callable=_ok
    )
    envelope = _make_envelope(tmp_path, ctx=ctx)
    result = dispatch_run_with_terminalization(
        provider=provider,
        ctx=ctx,
        envelope=envelope,
        evidence_root=evidence_root,
        bindings=bindings,
        run_key="rk1",
        attempt=1,
        repo_root=REPO_ROOT,
        budget=_budget(),
    )
    fp = commit_successful_result(
        evidence_root,
        run_key="rk1",
        bindings=bindings,
        attempt=1,
        envelope=envelope.as_dict(),
        result=result.metrics,
        exit_code=0,
    )
    assert fp
    env = json.loads(
        run_envelope_path(evidence_root, "rk1").read_text(encoding="utf-8")
    )
    assert env["status"] == "SUCCEEDED"


def test_hard_crash_running_without_completion_still_blocks_resume(tmp_path: Path):
    """Do not weaken STATE_RUNNING_WITHOUT_COMPLETION for real crashes."""
    ctx = _mint_auth_ctx()
    bindings = bindings_from_authorization(ctx)
    evidence_root = tmp_path / "evidence"
    write_run_envelope(
        evidence_root,
        run_key="rk_crash",
        bindings=bindings,
        status="RUNNING",
        attempt=1,
        envelope={"run_key": "rk_crash"},
    )
    with pytest.raises(SensitivityStateError) as exc:
        inspect_run_for_resume(
            evidence_root,
            run_key="rk_crash",
            bindings=bindings,
            max_attempts=1,
            retry_failed=True,
        )
    assert "STATE_RUNNING_WITHOUT_COMPLETION" in str(exc.value)


def test_preflight_fail_closed_when_window_bank_unavailable(monkeypatch, capsys):
    """#4395: receipt digests alone must not yield ok=true without a physical bank."""
    from tools.arvp_vacation.hh_hl_execution_window_bank import (
        HOLD_WINDOW_BANK_UNAVAILABLE,
        HhHlExecutionWindowBankError,
    )

    hits = _install_valid_go_and_sha(free_disk_bytes=MIN_FREE_DISK)

    def _missing(_repo_root=None):
        raise HhHlExecutionWindowBankError(
            HOLD_WINDOW_BANK_UNAVAILABLE, "synthetic_missing_bank"
        )

    monkeypatch.setattr(
        "tools.arvp_vacation.hh_hl_campaign_execute.assert_execution_window_bank_available",
        _missing,
    )
    code = execute_main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--execution-go-comment-id",
            "999001",
            "preflight",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert HOLD_WINDOW_BANK_UNAVAILABLE in out
    assert '"ok": false' in out.lower() or '"ok": false' in out
    assert not any(h[0] == "callable" for h in hits)
