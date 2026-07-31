"""Persistent dedup state tests (Issue #4186).

Protected rule: the dedup state is the restart-safety anchor. A missing or
corrupt state must block; it must never be silently reinterpreted as "nothing
has been protected yet".
"""

from __future__ import annotations

import json

import pytest

from core.safety.stop_loss import (
    DEDUP_STATE_SCHEMA_VERSION,
    DedupRecordState,
    FileStopLossDedupStore,
    InMemoryStopLossDedupStore,
    StopLossDedupRecord,
    StopLossDedupStateError,
    StopLossDedupStore,
)
from core.safety.stop_loss.contracts import StopLossReason


def _record(**overrides) -> StopLossDedupRecord:
    payload = {
        "event_id": "slp-abc",
        "fingerprint": "f" * 64,
        "state": DedupRecordState.PREPARED,
        "symbol": "BTCUSDT",
        "position_id": "pos-1",
        "prepared_at_ms": 1_800_000_000_000,
        "intent_id": "slx-abc",
    }
    payload.update(overrides)
    return StopLossDedupRecord(**payload)


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "stop_loss_dedup.json"


@pytest.mark.unit
def test_file_and_memory_stores_satisfy_the_protocol(state_file):
    assert isinstance(FileStopLossDedupStore(state_file), StopLossDedupStore)
    assert isinstance(InMemoryStopLossDedupStore(), StopLossDedupStore)


@pytest.mark.unit
def test_missing_state_file_blocks_instead_of_returning_empty(state_file):
    store = FileStopLossDedupStore(state_file)

    with pytest.raises(StopLossDedupStateError) as excinfo:
        store.load("slp-abc")

    assert excinfo.value.reason is StopLossReason.DEDUP_STATE_MISSING


@pytest.mark.unit
def test_initialize_creates_valid_empty_state(state_file):
    store = FileStopLossDedupStore(state_file)
    store.initialize()

    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == DEDUP_STATE_SCHEMA_VERSION
    assert payload["records"] == {}
    assert store.load("slp-abc") is None


@pytest.mark.unit
def test_initialize_does_not_overwrite_existing_records(state_file):
    store = FileStopLossDedupStore(state_file)
    store.initialize()
    store.finalize(_record())

    store_again = FileStopLossDedupStore(state_file)
    store_again.initialize()

    assert store_again.load("slp-abc") is not None


@pytest.mark.unit
def test_initialize_on_corrupt_state_still_blocks(state_file):
    state_file.write_text("{not json", encoding="utf-8")
    store = FileStopLossDedupStore(state_file)

    with pytest.raises(StopLossDedupStateError) as excinfo:
        store.initialize()

    assert excinfo.value.reason is StopLossReason.DEDUP_STATE_CORRUPT


@pytest.mark.unit
@pytest.mark.parametrize(
    "content",
    [
        "",
        "   ",
        "{not json",
        "[]",
        json.dumps({"records": {}}),
        json.dumps({"schema_version": "other/v9", "records": {}}),
        json.dumps({"schema_version": DEDUP_STATE_SCHEMA_VERSION, "records": []}),
    ],
)
def test_corrupt_state_blocks(state_file, content):
    state_file.write_text(content, encoding="utf-8")
    store = FileStopLossDedupStore(state_file)

    with pytest.raises(StopLossDedupStateError) as excinfo:
        store.load("slp-abc")

    assert excinfo.value.reason is StopLossReason.DEDUP_STATE_CORRUPT


@pytest.mark.unit
@pytest.mark.parametrize(
    "record_payload",
    [
        "not-an-object",
        {"event_id": "slp-abc"},
        {
            "event_id": "slp-abc",
            "fingerprint": "f" * 64,
            "state": "WHATEVER",
            "symbol": "BTCUSDT",
            "position_id": "pos-1",
            "prepared_at_ms": 1,
        },
        {
            "event_id": "slp-abc",
            "fingerprint": "f" * 64,
            "state": "PREPARED",
            "symbol": "BTCUSDT",
            "position_id": "pos-1",
            "prepared_at_ms": "1",
        },
        {
            "event_id": "slp-abc",
            "fingerprint": "f" * 64,
            "state": "FINALIZED",
            "symbol": "BTCUSDT",
            "position_id": "pos-1",
            "prepared_at_ms": 1,
            "intent_id": None,
        },
        {
            "event_id": "slp-abc",
            "fingerprint": "f" * 64,
            "state": "FINALIZED",
            "symbol": "BTCUSDT",
            "position_id": "pos-1",
            "prepared_at_ms": 1,
            "intent_id": "slx-abc",
            "finalized_at_ms": "later",
        },
    ],
)
def test_corrupt_record_blocks(state_file, record_payload):
    state_file.write_text(
        json.dumps(
            {
                "schema_version": DEDUP_STATE_SCHEMA_VERSION,
                "records": {"slp-abc": record_payload},
            }
        ),
        encoding="utf-8",
    )
    store = FileStopLossDedupStore(state_file)

    with pytest.raises(StopLossDedupStateError) as excinfo:
        store.load("slp-abc")

    assert excinfo.value.reason is StopLossReason.DEDUP_STATE_CORRUPT


@pytest.mark.unit
def test_record_key_mismatch_blocks(state_file):
    state_file.write_text(
        json.dumps(
            {
                "schema_version": DEDUP_STATE_SCHEMA_VERSION,
                "records": {"slp-key": _record(event_id="slp-other").to_dict()},
            }
        ),
        encoding="utf-8",
    )
    store = FileStopLossDedupStore(state_file)

    with pytest.raises(StopLossDedupStateError) as excinfo:
        store.load("slp-key")

    assert excinfo.value.reason is StopLossReason.DEDUP_STATE_CORRUPT


@pytest.mark.unit
def test_prepare_then_finalize_roundtrip_survives_new_store_instance(state_file):
    store = FileStopLossDedupStore(state_file)
    store.initialize()
    store.prepare(_record())

    reloaded = FileStopLossDedupStore(state_file).load("slp-abc")
    assert reloaded.state is DedupRecordState.PREPARED

    store.finalize(_record(finalized_at_ms=1_800_000_000_500))
    reloaded = FileStopLossDedupStore(state_file).load("slp-abc")
    assert reloaded.state is DedupRecordState.FINALIZED
    assert reloaded.intent_id == "slx-abc"
    assert reloaded.finalized_at_ms == 1_800_000_000_500


@pytest.mark.unit
def test_write_leaves_no_temp_file_behind(state_file):
    store = FileStopLossDedupStore(state_file)
    store.initialize()
    store.prepare(_record())

    siblings = [path.name for path in state_file.parent.iterdir()]
    assert siblings == [state_file.name]


@pytest.mark.unit
def test_in_memory_store_requires_initialization():
    store = InMemoryStopLossDedupStore()

    with pytest.raises(StopLossDedupStateError) as excinfo:
        store.load("slp-abc")

    assert excinfo.value.reason is StopLossReason.DEDUP_STATE_MISSING


@pytest.mark.unit
def test_in_memory_store_preserves_records_across_handoff():
    store = InMemoryStopLossDedupStore()
    store.initialize()
    store.finalize(_record())

    restarted = InMemoryStopLossDedupStore(store.records)
    assert restarted.load("slp-abc").state is DedupRecordState.FINALIZED
