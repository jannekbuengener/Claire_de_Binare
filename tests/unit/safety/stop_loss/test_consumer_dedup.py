"""Restart-safe stop-loss consumer tests (Issue #4186).

Protected rule: exactly one exit intent per unique protection event, across
double delivery, replay, and consumer restart. Every state anomaly blocks.
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal

import pytest

from core.safety.stop_loss import (
    DedupRecordState,
    FileStopLossDedupStore,
    InMemoryStopLossDedupStore,
    PositionSide,
    RecordingExitIntentSink,
    StopLossConsumeDecision,
    StopLossConsumer,
    StopLossDedupRecord,
    StopLossReason,
    StopLossTriggerConfig,
)
from core.safety.stop_loss.dedup_state import (
    DEDUP_STATE_SCHEMA_VERSION,
    StopLossDedupStateError,
)

from tests.unit.safety.stop_loss.conftest import NOW_MS, observation


def _consumer(store, sink, *, config=None, now_ms=NOW_MS) -> StopLossConsumer:
    return StopLossConsumer(
        store=store,
        sink=sink,
        config=config or StopLossTriggerConfig(stop_loss_pct=Decimal("0.02")),
        clock_ms=lambda: now_ms,
    )


@pytest.fixture
def state_file(tmp_path):
    path = tmp_path / "stop_loss_dedup.json"
    FileStopLossDedupStore(path).initialize()
    return path


@pytest.mark.unit
def test_single_breach_emits_exactly_one_exit_intent(
    state_file, long_position, breach_observation
):
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(state_file), sink)

    outcome = consumer.consume(long_position, breach_observation)

    assert outcome.decision is StopLossConsumeDecision.EXIT_INTENT_EMITTED
    assert outcome.reason_code == StopLossReason.EXIT_INTENT_EMITTED.value
    assert len(sink.intents) == 1
    intent = sink.intents[0]
    assert intent.side == "SELL"
    assert intent.reduce_only is True
    assert intent.quantity == Decimal("0.50000000")
    assert intent.productive_adapter_enabled is False
    assert intent.dispatch_state == "NOT_DISPATCHED"


@pytest.mark.unit
def test_double_delivery_of_the_same_event_emits_one_intent(
    state_file, long_position, breach_observation
):
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(state_file), sink)

    first = consumer.consume(long_position, breach_observation)
    second = consumer.consume(long_position, breach_observation)

    assert first.emitted is True
    assert second.decision is StopLossConsumeDecision.DUPLICATE_SUPPRESSED
    assert second.reason_code == StopLossReason.DUPLICATE_SUPPRESSED.value
    assert len(sink.intents) == 1


@pytest.mark.unit
def test_repeated_deeper_ticks_do_not_multiply_intents(state_file, long_position):
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(state_file), sink)

    decisions = [
        consumer.consume(long_position, observation(price)).decision
        for price in ("97.50", "97.00", "90.00", "50.00")
    ]

    assert decisions[0] is StopLossConsumeDecision.EXIT_INTENT_EMITTED
    assert all(d is StopLossConsumeDecision.DUPLICATE_SUPPRESSED for d in decisions[1:])
    assert len(sink.intents) == 1


@pytest.mark.unit
def test_replay_after_restart_is_idempotent(
    state_file, long_position, breach_observation
):
    first_sink = RecordingExitIntentSink()
    _consumer(FileStopLossDedupStore(state_file), first_sink).consume(
        long_position, breach_observation
    )

    # Fresh consumer, fresh sink, same persistent state: process restart.
    restarted_sink = RecordingExitIntentSink()
    restarted = _consumer(FileStopLossDedupStore(state_file), restarted_sink)
    outcome = restarted.consume(long_position, breach_observation)

    assert outcome.decision is StopLossConsumeDecision.DUPLICATE_SUPPRESSED
    assert restarted_sink.intents == []
    assert len(first_sink.intents) == 1


@pytest.mark.unit
def test_restart_between_prepare_and_finalize_blocks(
    state_file, long_position, breach_observation
):
    """A PREPARED record means delivery is unproven: never emit a second intent."""

    class FinalizeCrashStore(FileStopLossDedupStore):
        def finalize(self, record):
            raise RuntimeError("process died before finalize")

    crashing_sink = RecordingExitIntentSink()
    crashed = _consumer(FinalizeCrashStore(state_file), crashing_sink).consume(
        long_position, breach_observation
    )

    assert crashed.decision is StopLossConsumeDecision.BLOCKED
    assert crashed.reason_code == StopLossReason.DEDUP_FINALIZE_FAILED.value
    assert crashed.intent is not None  # partial success is reported, not hidden
    assert len(crashing_sink.intents) == 1

    stored = FileStopLossDedupStore(state_file).load(crashed.event_id)
    assert stored.state is DedupRecordState.PREPARED

    restarted_sink = RecordingExitIntentSink()
    outcome = _consumer(FileStopLossDedupStore(state_file), restarted_sink).consume(
        long_position, breach_observation
    )

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.PREPARE_INCOMPLETE.value
    assert restarted_sink.intents == []


@pytest.mark.unit
def test_sink_failure_blocks_and_leaves_record_prepared(
    state_file, long_position, breach_observation
):
    class FailingSink:
        def accept(self, intent):
            raise RuntimeError("queue unavailable")

    store = FileStopLossDedupStore(state_file)
    outcome = _consumer(store, FailingSink()).consume(long_position, breach_observation)

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.EXIT_INTENT_SINK_FAILED.value
    assert store.load(outcome.event_id).state is DedupRecordState.PREPARED


@pytest.mark.unit
def test_prepare_failure_blocks_without_emitting(
    state_file, long_position, breach_observation
):
    class PrepareFailStore(FileStopLossDedupStore):
        def prepare(self, record):
            raise RuntimeError("disk full")

    sink = RecordingExitIntentSink()
    outcome = _consumer(PrepareFailStore(state_file), sink).consume(
        long_position, breach_observation
    )

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.DEDUP_PREPARE_FAILED.value
    assert sink.intents == []


@pytest.mark.unit
def test_missing_state_blocks_before_any_intent(
    tmp_path, long_position, breach_observation
):
    sink = RecordingExitIntentSink()
    store = FileStopLossDedupStore(tmp_path / "never_initialized.json")

    outcome = _consumer(store, sink).consume(long_position, breach_observation)

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.DEDUP_STATE_MISSING.value
    assert sink.intents == []


@pytest.mark.unit
def test_corrupt_state_blocks_before_any_intent(
    state_file, long_position, breach_observation
):
    state_file.write_text("{broken", encoding="utf-8")
    sink = RecordingExitIntentSink()

    outcome = _consumer(FileStopLossDedupStore(state_file), sink).consume(
        long_position, breach_observation
    )

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.DEDUP_STATE_CORRUPT.value
    assert sink.intents == []


@pytest.mark.unit
def test_contradictory_stored_fingerprint_blocks(
    state_file, long_position, breach_observation
):
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(state_file), sink)
    emitted = consumer.consume(long_position, breach_observation)

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    payload["records"][emitted.event_id]["fingerprint"] = "0" * 64
    state_file.write_text(json.dumps(payload), encoding="utf-8")

    outcome = consumer.consume(long_position, breach_observation)

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.DEDUP_STATE_CONTRADICTORY.value
    assert len(sink.intents) == 1


@pytest.mark.unit
def test_newer_protection_event_is_not_swallowed_by_an_older_dedup_entry(
    state_file, long_position, breach_observation
):
    """A new position on the same symbol must still get its own exit intent."""
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(state_file), sink)

    first = consumer.consume(long_position, breach_observation)
    reopened = replace(
        long_position,
        position_id="pos-long-2",
        opened_at_ms=NOW_MS - 10,
        entry_price=Decimal("99.00"),
    )
    second = consumer.consume(reopened, observation("96.00"))

    assert first.emitted is True
    assert second.emitted is True
    assert first.event_id != second.event_id
    assert len(sink.intents) == 2


@pytest.mark.unit
def test_position_id_reuse_with_new_epoch_is_a_new_event(
    state_file, long_position, breach_observation
):
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(state_file), sink)

    consumer.consume(long_position, breach_observation)
    reused = replace(long_position, opened_at_ms=NOW_MS - 5)
    second = consumer.consume(reused, breach_observation)

    assert second.emitted is True
    assert len(sink.intents) == 2


@pytest.mark.unit
def test_unknown_position_state_blocks_before_state_access(
    state_file, long_position, breach_observation
):
    class ExplodingStore(FileStopLossDedupStore):
        def load(self, event_id):
            raise AssertionError("state must not be consulted for an unknown position")

    sink = RecordingExitIntentSink()
    unknown = replace(long_position, side=PositionSide.UNKNOWN)

    outcome = _consumer(ExplodingStore(state_file), sink).consume(
        unknown, breach_observation
    )

    assert outcome.decision is StopLossConsumeDecision.BLOCKED
    assert outcome.reason_code == StopLossReason.POSITION_STATE_UNKNOWN.value
    assert sink.intents == []


@pytest.mark.unit
def test_no_trigger_does_not_touch_the_dedup_state(
    state_file, long_position, safe_observation
):
    sink = RecordingExitIntentSink()
    outcome = _consumer(FileStopLossDedupStore(state_file), sink).consume(
        long_position, safe_observation
    )

    assert outcome.decision is StopLossConsumeDecision.NO_TRIGGER
    assert sink.intents == []
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload == {"schema_version": DEDUP_STATE_SCHEMA_VERSION, "records": {}}


@pytest.mark.unit
def test_short_position_exit_intent_buys_back(state_file, short_position):
    sink = RecordingExitIntentSink()
    outcome = _consumer(FileStopLossDedupStore(state_file), sink).consume(
        short_position, observation("102.50")
    )

    assert outcome.emitted is True
    assert sink.intents[0].side == "BUY"
    assert sink.intents[0].reduce_only is True


@pytest.mark.unit
def test_in_memory_store_restart_handoff_suppresses_duplicate(
    long_position, breach_observation
):
    store = InMemoryStopLossDedupStore()
    store.initialize()
    first_sink = RecordingExitIntentSink()
    _consumer(store, first_sink).consume(long_position, breach_observation)

    restarted_sink = RecordingExitIntentSink()
    outcome = _consumer(
        InMemoryStopLossDedupStore(store.records), restarted_sink
    ).consume(long_position, breach_observation)

    assert outcome.decision is StopLossConsumeDecision.DUPLICATE_SUPPRESSED
    assert restarted_sink.intents == []


@pytest.mark.unit
def test_finalized_record_without_intent_id_is_rejected_by_state_layer(state_file):
    payload = {
        "schema_version": DEDUP_STATE_SCHEMA_VERSION,
        "records": {
            "slp-x": StopLossDedupRecord(
                event_id="slp-x",
                fingerprint="f" * 64,
                state=DedupRecordState.FINALIZED,
                symbol="BTCUSDT",
                position_id="pos-1",
                prepared_at_ms=1,
            ).to_dict()
        },
    }
    state_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(StopLossDedupStateError):
        FileStopLossDedupStore(state_file).load("slp-x")
