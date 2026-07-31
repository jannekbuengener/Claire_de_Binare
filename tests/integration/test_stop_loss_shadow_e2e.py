"""Mock/shadow end-to-end proof: price trigger to exit intent (Issue #4186).

Protected rule: a full protection cycle must produce exactly one exit intent
from a realistic candle series, survive a mid-series consumer restart, and never
reach a productive adapter. No containers, no Redis, no exchange calls.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from core.safety.stop_loss import (
    DisabledProductiveExitAdapter,
    FileStopLossDedupStore,
    PositionSide,
    PositionSnapshot,
    RecordingExitIntentSink,
    StopLossConsumeDecision,
    StopLossContractError,
    StopLossReason,
    StopLossTriggerConfig,
    candle_observations,
    run_stop_loss_shadow,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "stop_loss_shadow_candles.json"


@pytest.fixture(scope="module")
def fixture_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def position(fixture_payload) -> PositionSnapshot:
    raw = fixture_payload["position"]
    return PositionSnapshot(
        symbol=raw["symbol"],
        side=PositionSide(raw["side"]),
        quantity=Decimal(raw["quantity"]),
        entry_price=Decimal(raw["entry_price"]),
        position_id=raw["position_id"],
        opened_at_ms=raw["opened_at_ms"],
    )


@pytest.fixture
def config(fixture_payload) -> StopLossTriggerConfig:
    return StopLossTriggerConfig(
        stop_loss_pct=Decimal(fixture_payload["stop_loss_pct"]),
        max_price_age_ms=fixture_payload["max_price_age_ms"],
    )


@pytest.fixture
def observations(fixture_payload, position):
    return candle_observations(fixture_payload["candles"], symbol=position.symbol)


@pytest.mark.integration
def test_shadow_run_emits_exactly_one_exit_intent(
    tmp_path, position, config, observations
):
    store = FileStopLossDedupStore(tmp_path / "dedup.json")
    store.initialize()
    sink = RecordingExitIntentSink()

    report = run_stop_loss_shadow(
        position=position,
        observations=observations,
        config=config,
        store=store,
        sink=sink,
    )

    assert report.emitted_count == 1
    assert len(set(report.emitted_intent_ids)) == 1
    assert len(sink.intents) == 1

    counts = report.decision_counts()
    assert counts[StopLossConsumeDecision.EXIT_INTENT_EMITTED.value] == 1
    assert counts[StopLossConsumeDecision.NO_TRIGGER.value] >= 1
    assert counts[StopLossConsumeDecision.DUPLICATE_SUPPRESSED.value] >= 1
    assert StopLossConsumeDecision.BLOCKED.value not in counts


@pytest.mark.integration
def test_shadow_run_survives_restart_after_the_trigger(
    tmp_path, position, config, observations
):
    """Restarting after the intent was finalized must not emit a second one."""
    store = FileStopLossDedupStore(tmp_path / "dedup.json")
    store.initialize()
    sink = RecordingExitIntentSink()

    trigger_index = next(
        index
        for index, obs in enumerate(observations)
        if Decimal(str(obs.price)) <= Decimal("98.00")
    )

    report = run_stop_loss_shadow(
        position=position,
        observations=observations,
        config=config,
        store=store,
        sink=sink,
        restart_before_indices=(trigger_index + 1, trigger_index + 2),
    )

    assert report.emitted_count == 1
    restarted_steps = [step for step in report.steps if step.restarted_before_step]
    assert restarted_steps
    assert all(
        step.decision == StopLossConsumeDecision.DUPLICATE_SUPPRESSED.value
        for step in restarted_steps
    )


@pytest.mark.integration
def test_shadow_run_is_deterministic_across_independent_runs(
    tmp_path, position, config, observations
):
    reports = []
    for run in ("a", "b"):
        store = FileStopLossDedupStore(tmp_path / f"dedup_{run}.json")
        store.initialize()
        reports.append(
            run_stop_loss_shadow(
                position=position,
                observations=observations,
                config=config,
                store=store,
                sink=RecordingExitIntentSink(),
            ).to_dict()
        )

    assert reports[0] == reports[1]


@pytest.mark.integration
def test_shadow_report_declares_no_productive_adapter(
    tmp_path, position, config, observations
):
    store = FileStopLossDedupStore(tmp_path / "dedup.json")
    store.initialize()

    report = run_stop_loss_shadow(
        position=position,
        observations=observations,
        config=config,
        store=store,
        sink=RecordingExitIntentSink(),
    )

    assert report.productive_adapter_enabled is False
    assert report.to_dict()["productive_adapter_enabled"] is False


@pytest.mark.integration
def test_productive_exit_adapter_blocks_the_shadow_intent(
    tmp_path, position, config, observations
):
    """Handing the intent to production fails closed instead of executing."""
    store = FileStopLossDedupStore(tmp_path / "dedup.json")
    store.initialize()

    report = run_stop_loss_shadow(
        position=position,
        observations=observations,
        config=config,
        store=store,
        sink=DisabledProductiveExitAdapter(),
    )

    assert report.emitted_count == 0
    blocked = [
        step
        for step in report.steps
        if step.decision == StopLossConsumeDecision.BLOCKED.value
    ]
    assert blocked
    assert blocked[0].reason_code == StopLossReason.EXIT_INTENT_SINK_FAILED.value


@pytest.mark.integration
def test_productive_adapter_refuses_any_intent_directly(
    tmp_path, position, config, observations
):
    store = FileStopLossDedupStore(tmp_path / "dedup.json")
    store.initialize()
    sink = RecordingExitIntentSink()
    run_stop_loss_shadow(
        position=position,
        observations=observations,
        config=config,
        store=store,
        sink=sink,
    )

    with pytest.raises(
        StopLossContractError, match=StopLossReason.PRODUCTIVE_ADAPTER_DISABLED.value
    ):
        DisabledProductiveExitAdapter().accept(sink.intents[0])


@pytest.mark.integration
def test_stale_candles_block_the_whole_run(tmp_path, position, config, observations):
    """A price series that is older than the freshness window must not trigger."""
    store = FileStopLossDedupStore(tmp_path / "dedup.json")
    store.initialize()
    sink = RecordingExitIntentSink()
    stale_now_ms = max(int(obs.observed_at_ms) for obs in observations) + 10_000_000

    report = run_stop_loss_shadow(
        position=position,
        observations=observations,
        config=config,
        store=store,
        sink=sink,
        now_ms_for=lambda obs: stale_now_ms,
    )

    assert report.emitted_count == 0
    assert sink.intents == []
    assert report.reason_codes() == [StopLossReason.PRICE_STALE.value]
