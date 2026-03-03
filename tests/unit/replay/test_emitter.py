"""Tests for core.replay.emitter with per-call env-gated emission."""

import json
import logging

import pytest

from core.replay.canonical_json import canonical_json_dumps
from core.replay.emitter import (
    _build_envelope,
    _compute_event_hash,
    configure_envelope_emission,
    emit_decision_envelope,
    emit_envelope,
    emit_fill_envelope,
    emit_order_envelope,
    is_envelope_emission_enabled,
)
from core.utils.uuid_gen import compute_correlation_id, compute_event_pk
from core.replay.time import created_at_from_ts_ms


class CapturePublisher:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def publish(self, payload: str) -> None:
        self.messages.append(payload)


@pytest.fixture(autouse=True)
def reset_emitter(monkeypatch) -> None:
    monkeypatch.delenv("CDB_ENVELOPE_EMISSION", raising=False)
    monkeypatch.delenv("LR021_ENVELOPE_EMIT_ENABLED", raising=False)
    configure_envelope_emission(publisher=None)


def enable_emission(
    monkeypatch, publisher: CapturePublisher | None = None
) -> CapturePublisher:
    publisher = publisher or CapturePublisher()
    monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "1")
    configure_envelope_emission(publisher=publisher)
    return publisher


class TestEnvelopeConfiguration:
    def test_default_disabled(self):
        assert not is_envelope_emission_enabled()

    def test_enable_via_env_and_disable(self, monkeypatch):
        monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "1")
        assert is_envelope_emission_enabled()
        monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "0")
        assert not is_envelope_emission_enabled()

    def test_legacy_env_fallback(self, monkeypatch):
        """LR021_ENVELOPE_EMIT_ENABLED is used when CDB_ is not set."""
        monkeypatch.setenv("LR021_ENVELOPE_EMIT_ENABLED", "1")
        assert is_envelope_emission_enabled()
        monkeypatch.setenv("LR021_ENVELOPE_EMIT_ENABLED", "0")
        assert not is_envelope_emission_enabled()

    def test_primary_env_overrides_legacy(self, monkeypatch):
        """CDB_ENVELOPE_EMISSION takes precedence over legacy."""
        monkeypatch.setenv("LR021_ENVELOPE_EMIT_ENABLED", "1")
        monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "0")
        assert not is_envelope_emission_enabled()

    def test_emit_without_publisher_raises(self, monkeypatch):
        monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "1")
        configure_envelope_emission(publisher=None)
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-emit-1",
            ts_ms=1000,
            payload={"decision": "ALLOW"},
        )
        with pytest.raises(RuntimeError):
            emit_envelope(env)


class TestBuildEnvelope:
    def test_required_fields_only(self):
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
        )
        assert env["schema_version"] == "envelope.v1"
        assert env["event_type"] == "DECISION"
        assert env["event_id"] == "ev-001"
        assert env["ts_ms"] == 1700000000000
        assert env["created_at"] == created_at_from_ts_ms(1700000000000)
        assert env["payload"] == {"decision": "ALLOW"}
        assert "policy_id" not in env
        assert "policy_hash" not in env
        assert "input_hash" not in env
        assert "output_hash" not in env
        assert "correlation_id" not in env
        assert "trace_id" not in env
        assert "decision_context" not in env

    def test_optional_fields_included(self):
        env = _build_envelope(
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=1700000000000,
            payload={"symbol": "BTCUSDT"},
            policy_id="risk_v1",
            policy_hash="abc",
            input_hash="inp",
            output_hash="out",
        )
        assert env["policy_id"] == "risk_v1"
        assert env["policy_hash"] == "abc"
        assert env["input_hash"] == "inp"
        assert env["output_hash"] == "out"

    def test_deterministic_event_id_with_signal_context(self):
        env = _build_envelope(
            event_type="ORDER",
            event_id="legacy-order-id",
            ts_ms=1700000000000,
            payload={"symbol": "BTCUSDT"},
            signal_id="sig-001",
            order_id="ord-001",
            trace_id="trace-001",
            decision_context={"inputs": {"symbol": "BTCUSDT"}},
        )
        assert env["event_id"] == compute_event_pk(
            "sig-001", "ORDER", order_id="ord-001"
        )
        assert env["correlation_id"] == compute_correlation_id("sig-001")
        assert env["trace_id"] == "trace-001"
        assert env["decision_context"] == {"inputs": {"symbol": "BTCUSDT"}}

    def test_created_at_canonical_format(self):
        ts_ms = 1700000000123
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-002",
            ts_ms=ts_ms,
            payload={"decision": "ALLOW"},
        )
        assert env["created_at"] == created_at_from_ts_ms(ts_ms)


class TestComputeEventHash:
    def test_deterministic(self):
        env = {
            "event_type": "DECISION",
            "event_id": "ev-001",
            "ts_ms": 1000,
            "payload": {},
        }
        h1 = _compute_event_hash(env)
        h2 = _compute_event_hash(env)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_data_different_hash(self):
        env1 = {
            "event_type": "DECISION",
            "event_id": "ev-001",
            "ts_ms": 1000,
            "payload": {},
        }
        env2 = {
            "event_type": "DECISION",
            "event_id": "ev-002",
            "ts_ms": 1000,
            "payload": {},
        }
        assert _compute_event_hash(env1) != _compute_event_hash(env2)

    def test_semantic_key_reordering_keeps_hash_stable(self):
        env1 = {
            "event_type": "DECISION",
            "event_id": "ev-001",
            "ts_ms": 1000,
            "payload": {"symbol": "BTCUSDT", "decision": "ALLOW"},
            "decision_context": {
                "inputs": {"slippage_pct": 0.001, "symbol": "BTCUSDT"},
                "thresholds": {"max_slippage_pct": 0.002},
            },
        }
        env2 = {
            "decision_context": {
                "thresholds": {"max_slippage_pct": 0.002},
                "inputs": {"symbol": "BTCUSDT", "slippage_pct": 0.001},
            },
            "payload": {"decision": "ALLOW", "symbol": "BTCUSDT"},
            "ts_ms": 1000,
            "event_id": "ev-001",
            "event_type": "DECISION",
        }
        assert _compute_event_hash(env1) == _compute_event_hash(env2)


class TestEmitEnvelope:
    def test_noop_when_off(self, caplog):
        publisher = CapturePublisher()
        configure_envelope_emission(publisher=publisher)
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1000,
            payload={},
        )
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        assert len(caplog.records) == 0
        assert not publisher.messages

    def test_emits_jsonl_when_on(self, monkeypatch, caplog):
        publisher = enable_emission(monkeypatch)
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1000,
            payload={"k": "v"},
        )
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        assert len(caplog.records) == 1
        line = caplog.records[0].message
        parsed = json.loads(line)
        assert parsed["event_type"] == "DECISION"
        assert parsed["event_id"] == "ev-001"
        assert "event_hash" in parsed
        assert len(parsed["event_hash"]) == 64
        assert publisher.messages == [line]

    def test_event_hash_is_correct(self, monkeypatch, caplog):
        publisher = enable_emission(monkeypatch)
        env = _build_envelope(
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=2000,
            payload={"x": 1},
        )
        expected_hash = _compute_event_hash(env)
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        parsed = json.loads(caplog.records[0].message)
        assert parsed["event_hash"] == expected_hash
        assert publisher.messages[0] == caplog.records[0].message

    def test_no_cache_per_call_env_read(self, monkeypatch, caplog):
        """Prove _should_emit() reads env on every call — no module-level cache."""
        publisher = CapturePublisher()
        configure_envelope_emission(publisher=publisher)
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-cache-1",
            ts_ms=1000,
            payload={"k": "v"},
        )

        # Phase 1: OFF (default, no env set) => no-op
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        assert not publisher.messages

        # Phase 2: ON => publishes
        monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "1")
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        assert len(publisher.messages) == 1

        # Phase 3: OFF again => no-op
        monkeypatch.setenv("CDB_ENVELOPE_EMISSION", "0")
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        assert len(publisher.messages) == 1  # still 1, not 2


class TestCanonicalOutput:
    def test_none_in_payload_omitted_from_output(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-canon-1",
            ts_ms=1000,
            payload={"decision": "ALLOW", "reason_code": None},
        )
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        line = caplog.records[0].message
        assert '"reason_code"' not in line
        parsed = json.loads(line)
        assert "reason_code" not in parsed["payload"]

    def test_negative_zero_normalized_in_output(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        env = _build_envelope(
            event_type="ORDER",
            event_id="ev-canon-2",
            ts_ms=2000,
            payload={"price": -0.0},
        )
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        line = caplog.records[0].message
        assert '"-0.0"' not in line
        assert "-0.0" not in line
        parsed = json.loads(line)
        assert parsed["payload"]["price"] == 0.0

    def test_key_order_canonical_in_output(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        env = _build_envelope(
            event_type="DECISION",
            event_id="ev-canon-3",
            ts_ms=3000,
            payload={"z_key": 1, "a_key": 2},
        )
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_envelope(env)
        line = caplog.records[0].message
        parsed = json.loads(line)
        event_hash = parsed.pop("event_hash")
        expected_line = canonical_json_dumps({**parsed, "event_hash": event_hash})
        assert line == expected_line


class TestEmitDecisionEnvelope:
    def test_noop_when_off(self, caplog):
        configure_envelope_emission(publisher=CapturePublisher())
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_decision_envelope(
                event_id="dec-001",
                ts_ms=1000,
                decision="ALLOW",
                reason_code=None,
                symbol="BTCUSDT",
                evidence={"key1": "val1"},
            )
        assert len(caplog.records) == 0

    def test_emits_with_evidence_keys(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_decision_envelope(
                event_id="dec-001",
                ts_ms=1000,
                decision="BLOCK",
                reason_code="MAX_EXPOSURE",
                symbol="ETHUSDT",
                evidence={"z_key": 1, "a_key": 2},
                signal_id="sig-001",
                trace_id="trace-001",
                decision_context={"inputs": {"symbol": "ETHUSDT"}},
            )
        assert len(caplog.records) == 1
        parsed = json.loads(caplog.records[0].message)
        assert parsed["event_type"] == "DECISION"
        assert parsed["event_id"] == compute_event_pk("sig-001", "DECISION")
        assert parsed["correlation_id"] == compute_correlation_id("sig-001")
        assert parsed["trace_id"] == "trace-001"
        assert parsed["decision_context"] == {"inputs": {"symbol": "ETHUSDT"}}
        payload = parsed["payload"]
        assert payload["decision"] == "BLOCK"
        assert payload["decision_id"] == "dec-001"
        assert payload["reason_code"] == "MAX_EXPOSURE"
        assert payload["symbol"] == "ETHUSDT"
        assert payload["evidence_keys"] == ["a_key", "z_key"]

    def test_reason_code_none_omitted(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_decision_envelope(
                event_id="dec-002",
                ts_ms=1000,
                decision="ALLOW",
                reason_code=None,
                symbol="BTCUSDT",
                evidence={},
            )
        parsed = json.loads(caplog.records[0].message)
        assert "reason_code" not in parsed["payload"]
        assert "evidence_keys" not in parsed["payload"]

    def test_empty_evidence_no_keys(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_decision_envelope(
                event_id="dec-003",
                ts_ms=1000,
                decision="ALLOW",
                reason_code=None,
                symbol="BTCUSDT",
                evidence={},
            )
        parsed = json.loads(caplog.records[0].message)
        assert "evidence_keys" not in parsed["payload"]


class TestEmitOrderEnvelope:
    def test_noop_when_off(self, caplog):
        configure_envelope_emission(publisher=CapturePublisher())
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_order_envelope(
                event_id="ord-001",
                ts_ms=1000,
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.01,
                price=50000.0,
            )
        assert len(caplog.records) == 0

    def test_emits_order(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_order_envelope(
                event_id="legacy-order-id",
                ts_ms=1000,
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.01,
                price=50000.0,
                signal_id="sig-001",
                decision_id="dec-001",
                order_id="ord-001",
                trace_id="trace-001",
                decision_context={"thresholds": {"max_slippage_pct": 0.002}},
            )
        parsed = json.loads(caplog.records[0].message)
        assert parsed["event_type"] == "ORDER"
        assert parsed["event_id"] == compute_event_pk(
            "sig-001", "ORDER", order_id="ord-001"
        )
        assert parsed["correlation_id"] == compute_correlation_id("sig-001")
        assert parsed["trace_id"] == "trace-001"
        assert parsed["decision_context"] == {"thresholds": {"max_slippage_pct": 0.002}}


class TestEmitFillEnvelope:
    def test_noop_when_off(self, caplog):
        configure_envelope_emission(publisher=CapturePublisher())
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_fill_envelope(
                event_id="fill-001",
                ts_ms=1000,
                order_id="ord-001",
                fill_id="fill-001",
                symbol="BTCUSDT",
                side="BUY",
                filled_quantity=0.005,
                price=50000.0,
            )
        assert len(caplog.records) == 0

    def test_emits_fill(self, monkeypatch, caplog):
        enable_emission(monkeypatch)
        with caplog.at_level(logging.INFO, logger="lr021.emitter"):
            emit_fill_envelope(
                event_id="fill-001",
                ts_ms=1000,
                order_id="ord-001",
                fill_id="fill-001",
                symbol="BTCUSDT",
                side="BUY",
                filled_quantity=0.005,
                price=None,
                status="FILLED",
                policy_id="policy-1",
                policy_hash="hash-1",
            )
        parsed = json.loads(caplog.records[0].message)
        assert parsed["event_type"] == "FILL"
        payload = parsed["payload"]
        assert "filled_quantity" in payload
        assert payload["status"] == "FILLED"
        assert "price" not in payload
        assert parsed["policy_id"] == "policy-1"
        assert parsed["policy_hash"] == "hash-1"
