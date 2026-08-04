"""Budget + real executor adapter unit tests (#4153).

test_id: tc_sensitivity_campaign_executor_budget_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.arvp_vacation.sensitivity_campaign_budget import (
    SensitivityBudgetError,
    validate_resource_budget,
)
from tools.arvp_vacation.sensitivity_campaign_executor import (
    RunEnvelope,
    StrategyReplayCampaignExecutor,
)
from tools.arvp_vacation.sensitivity_campaign_grid import baseline_param_set
from tools.arvp_vacation.sensitivity_campaign_state import (
    SensitivityStateError,
    acquire_campaign_lock,
    release_campaign_lock,
)


def _budget(**overrides):
    body = {
        "max_parallelism": 2,
        "max_in_flight_runs": 2,
        "max_attempts_per_run": 2,
        "max_run_wall_time_seconds": 600,
        "max_campaign_wall_time_seconds": 86400,
        "max_artifact_bytes": 50 * 1024**3,
        "minimum_free_disk_bytes": 1,
        "max_consecutive_failures": 5,
        "max_total_failures": 50,
        "log_retention_days": 30,
    }
    body.update(overrides)
    return body


def test_budget_in_flight_must_not_exceed_parallelism() -> None:
    with pytest.raises(SensitivityBudgetError) as exc:
        validate_resource_budget(_budget(max_in_flight_runs=4, max_parallelism=2))
    assert "BUDGET_IN_FLIGHT_GT_PARALLELISM" in str(exc.value)


def test_budget_run_wall_vs_campaign_wall() -> None:
    with pytest.raises(SensitivityBudgetError) as exc:
        validate_resource_budget(
            _budget(
                max_run_wall_time_seconds=10_000,
                max_campaign_wall_time_seconds=100,
            )
        )
    assert "BUDGET_RUN_WALL_GT_CAMPAIGN_WALL" in str(exc.value)


def test_budget_consecutive_vs_total() -> None:
    with pytest.raises(SensitivityBudgetError) as exc:
        validate_resource_budget(
            _budget(max_consecutive_failures=20, max_total_failures=5)
        )
    assert "BUDGET_CONSECUTIVE_GT_TOTAL" in str(exc.value)


def test_budget_valid_equal_caps() -> None:
    out = validate_resource_budget(_budget())
    assert out["max_parallelism"] == 2


def _sample_envelope(tmp_path: Path) -> RunEnvelope:
    params = baseline_param_set()
    return RunEnvelope(
        run_key="rk1",
        campaign_id="arvp-sensitivity-4153-v1",
        manifest_fingerprint="a" * 64,
        execution_sha="b" * 40,
        window_id="binance_1m_month_2017_10",
        strategy_id="primary_breakout_v1",
        parameters=params,
        slot_id="baseline",
        phase="baseline",
        label="baseline",
        physical_parameter_set_fingerprint="c" * 64,
        effective_config_fingerprint="d" * 64,
        dataset_content_fingerprint="e" * 64,
        seed="f" * 64,
        output_dir=str(tmp_path / "run"),
        run_plan_fingerprint="1" * 64,
        authorization_fingerprint="2" * 64,
    )


def test_strategy_replay_adapter_builds_config_and_invokes(tmp_path: Path) -> None:
    seen = []

    def invoker(config):
        seen.append(config)
        return 0

    executor = StrategyReplayCampaignExecutor(
        replay_invoker=invoker,
        metrics_loader=lambda _p: {"gate_reason": "OK", "trade_count": 0},
    )
    result = executor.execute(_sample_envelope(tmp_path))
    assert result.exit_code == 0
    assert len(seen) == 1
    cfg = seen[0]
    assert cfg.dataset_source == "binance_window"
    assert cfg.binance_window_id == "binance_1m_month_2017_10"
    assert cfg.entry_lookback_minutes == 240
    assert cfg.strategy_id == "primary_breakout_v1"
    assert (tmp_path / "run" / "bound_run_envelope.json").exists()


def test_strategy_replay_adapter_rejects_missing_auth_fp(tmp_path: Path) -> None:
    env = _sample_envelope(tmp_path)
    env = RunEnvelope(**{**env.as_dict(), "authorization_fingerprint": ""})
    executor = StrategyReplayCampaignExecutor(replay_invoker=lambda _c: 0)
    result = executor.execute(env)
    assert result.exit_code == 2
    assert "EXECUTOR_AUTHORIZATION_FINGERPRINT_REQUIRED" in result.detail


def test_campaign_lock_exclusive(tmp_path: Path) -> None:
    root = tmp_path / "ns"
    acquire_campaign_lock(root, holder_token="token-a")
    with pytest.raises(SensitivityStateError) as exc:
        acquire_campaign_lock(root, holder_token="token-b")
    assert "STATE_CAMPAIGN_LOCK_HELD" in str(exc.value)
    release_campaign_lock(root, holder_token="token-a")
    acquire_campaign_lock(root, holder_token="token-b")
    release_campaign_lock(root, holder_token="token-b")
