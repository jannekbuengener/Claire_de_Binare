"""Production single-run callable for hh_hl campaign execution (#4374).

Binds ``HhHlSingleRunReplayProvider`` to the existing
``services.validation.strategy_replay_runner`` single-run path. Never calls
``run_hh_hl_continuation_backtest`` directly and never opens PB1 / scenario-group
surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from core.replay.binance_window_bank_adapter import (
    BinanceWindowBankAdapterError,
    load_binance_window_dataset,
)
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
    frozen_hh_hl_parameters,
    hh_hl_warmup_candles,
)
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    ArvpReplayOutcome,
    run_arvp_replay_detailed,
)
from tools.arvp_vacation.campaign_profile import CampaignProfileError
from tools.arvp_vacation.sensitivity_campaign_executor import RunResult

DetailedReplayInvoker = Callable[[ARVPReplayConfig], ArvpReplayOutcome]

HOLD_FROZEN_PARAM_MISMATCH = "HOLD_EXECUTION_FROZEN_PARAM_MISMATCH"
HOLD_DATASET_CONTENT_MISMATCH = "HOLD_EXECUTION_DATASET_CONTENT_MISMATCH"
HOLD_WINDOW_ID_REQUIRED = "HOLD_EXECUTION_WINDOW_ID_REQUIRED"
HOLD_OUTPUT_DIR_REQUIRED = "HOLD_EXECUTION_OUTPUT_DIR_REQUIRED"
HOLD_DATASET_FP_REQUIRED = "HOLD_EXECUTION_DATASET_CONTENT_FINGERPRINT_REQUIRED"
HOLD_STRATEGY_MISMATCH = "HOLD_EXECUTION_STRATEGY_MISMATCH"
HOLD_ADAPTER_MISMATCH = "HOLD_EXECUTION_ADAPTER_MISMATCH"
HOLD_PB1_FORBIDDEN = "HOLD_EXECUTION_PB1_FORBIDDEN"
HOLD_SCENARIO_GROUP_FORBIDDEN = "HOLD_EXECUTION_SCENARIO_GROUP_FORBIDDEN"
HOLD_REPLAY_CONFIG_INVALID = "HOLD_EXECUTION_REPLAY_CONFIG_INVALID"
HOLD_DATASET_LOAD_FAILED = "HOLD_EXECUTION_DATASET_LOAD_FAILED"


def assert_frozen_hh_hl_parameters(
    parameters: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed unless request parameters exactly match the frozen spec."""
    frozen = frozen_hh_hl_parameters()
    actual = dict(parameters or {})
    if actual != frozen:
        raise CampaignProfileError(
            f"{HOLD_FROZEN_PARAM_MISMATCH}: expected={frozen!r} actual={actual!r}"
        )
    return frozen


def build_hh_hl_arvp_replay_config(
    request: Mapping[str, Any],
    *,
    window_bank_root: Path | None = None,
) -> ARVPReplayConfig:
    """Map a bound single-run request to ``ARVPReplayConfig`` (no loose overrides)."""
    strategy_id = str(request.get("strategy_id") or "")
    adapter_id = str(request.get("adapter_id") or "")
    if strategy_id == "primary_breakout_v1":
        raise CampaignProfileError(HOLD_PB1_FORBIDDEN)
    if strategy_id != HH_HL_CONTINUATION_STRATEGY_ID:
        raise CampaignProfileError(f"{HOLD_STRATEGY_MISMATCH}:{strategy_id}")
    if adapter_id != BATCH_B_SHADOW_ADAPTER_ID:
        raise CampaignProfileError(f"{HOLD_ADAPTER_MISMATCH}:{adapter_id}")
    if (
        request.get("scenario_group_id") is not None
        or request.get("scenario_ids") is not None
    ):
        raise CampaignProfileError(HOLD_SCENARIO_GROUP_FORBIDDEN)

    window_id = str(request.get("window_id") or "").strip()
    if not window_id or ".." in window_id:
        raise CampaignProfileError(HOLD_WINDOW_ID_REQUIRED)

    output_dir = str(request.get("output_dir") or "").strip()
    if not output_dir:
        raise CampaignProfileError(HOLD_OUTPUT_DIR_REQUIRED)

    assert_frozen_hh_hl_parameters(request.get("parameters"))

    bank_root = window_bank_root
    if bank_root is None and request.get("window_bank_root"):
        bank_root = Path(str(request["window_bank_root"]))

    config = ARVPReplayConfig(
        dataset_source="binance_window",
        binance_window_id=window_id,
        window_bank_root=str(bank_root.resolve()) if bank_root is not None else None,
        strategy_id=HH_HL_CONTINUATION_STRATEGY_ID,
        adapter_id=BATCH_B_SHADOW_ADAPTER_ID,
        symbol="BTCUSDT",
        speedup_profile="instant",
        output_directory=str(Path(output_dir) / "replay"),
        dry_run=False,
        scenario_ids=None,
        scenario_group_id=None,
        # PB1 lookbacks unused by hh_hl runner; keep valid defaults for validate().
        entry_lookback_minutes=240,
        exit_lookback_minutes=120,
        breakout_buffer=0.0005,
        min_minutes_between_entries=int(
            frozen_hh_hl_parameters()["min_minutes_between_entries"]
        ),
    )
    try:
        config.validate()
    except ValueError as exc:
        raise CampaignProfileError(f"{HOLD_REPLAY_CONFIG_INVALID}:{exc}") from exc
    return config


def assert_request_dataset_content_fingerprint(
    request: Mapping[str, Any],
    *,
    window_bank_root: Path | None = None,
) -> str:
    """Physically load the bound window and compare content fingerprint before replay."""
    expected = str(request.get("dataset_content_fingerprint") or "").strip()
    if not expected or len(expected) != 64:
        raise CampaignProfileError(HOLD_DATASET_FP_REQUIRED)

    window_id = str(request.get("window_id") or "").strip()
    if not window_id:
        raise CampaignProfileError(HOLD_WINDOW_ID_REQUIRED)

    bank_root = window_bank_root
    if bank_root is None and request.get("window_bank_root"):
        bank_root = Path(str(request["window_bank_root"]))

    try:
        loaded = load_binance_window_dataset(
            window_id,
            warmup_candles=hh_hl_warmup_candles(),
            window_bank_root=bank_root,
        )
    except BinanceWindowBankAdapterError as exc:
        raise CampaignProfileError(f"{HOLD_DATASET_LOAD_FAILED}:{exc}") from exc

    actual = str(loaded.dataset_result.content_fingerprint or "")
    if actual != expected:
        raise CampaignProfileError(
            f"{HOLD_DATASET_CONTENT_MISMATCH}: expected={expected} actual={actual}"
        )
    return actual


def outcome_to_run_result(outcome: ArvpReplayOutcome) -> RunResult:
    """Map typed replay outcome into campaign ``RunResult`` metrics."""
    metrics: dict[str, Any] = {}
    if outcome.metrics:
        metrics.update(dict(outcome.metrics))
    if outcome.gate_result is not None:
        metrics["gate_result"] = dict(outcome.gate_result)
    if outcome.run_id:
        metrics["run_id"] = outcome.run_id
    if outcome.artifact_root:
        metrics["artifact_root"] = outcome.artifact_root
    if outcome.content_fingerprint:
        metrics["content_fingerprint"] = outcome.content_fingerprint
    return RunResult(
        exit_code=int(outcome.exit_code),
        metrics=metrics,
        detail=str(outcome.detail or ""),
    )


def build_production_single_run_callable(
    *,
    window_bank_root: Path | None = None,
    replay_detailed: DetailedReplayInvoker | None = None,
) -> Callable[[Mapping[str, Any]], RunResult]:
    """Return the production SingleRunCallable used by the hh_hl provider."""

    invoker = replay_detailed or run_arvp_replay_detailed

    def _run(request: Mapping[str, Any]) -> RunResult:
        config = build_hh_hl_arvp_replay_config(
            request, window_bank_root=window_bank_root
        )
        # Dataset binding must pass before any backtest / replay orchestration.
        assert_request_dataset_content_fingerprint(
            request, window_bank_root=window_bank_root
        )
        Path(config.output_directory).mkdir(parents=True, exist_ok=True)
        outcome = invoker(config)
        if not isinstance(outcome, ArvpReplayOutcome):
            raise CampaignProfileError("HOLD_EXECUTION_REPLAY_OUTCOME_INVALID")
        return outcome_to_run_result(outcome)

    return _run


__all__ = [
    "HOLD_ADAPTER_MISMATCH",
    "HOLD_DATASET_CONTENT_MISMATCH",
    "HOLD_DATASET_FP_REQUIRED",
    "HOLD_DATASET_LOAD_FAILED",
    "HOLD_FROZEN_PARAM_MISMATCH",
    "HOLD_OUTPUT_DIR_REQUIRED",
    "HOLD_PB1_FORBIDDEN",
    "HOLD_REPLAY_CONFIG_INVALID",
    "HOLD_SCENARIO_GROUP_FORBIDDEN",
    "HOLD_STRATEGY_MISMATCH",
    "HOLD_WINDOW_ID_REQUIRED",
    "assert_frozen_hh_hl_parameters",
    "assert_request_dataset_content_fingerprint",
    "build_hh_hl_arvp_replay_config",
    "build_production_single_run_callable",
    "outcome_to_run_result",
]
