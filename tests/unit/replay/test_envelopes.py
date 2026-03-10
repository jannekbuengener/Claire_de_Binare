"""Tests for core.replay.envelopes — envelope dataclasses.

Governance: LR-021 Slice 1 (Deterministic Replay Framework)
"""

from core.replay.canonical_json import canonical_hash
from core.replay.envelopes import (
    DecisionEnvelopeV1,
    FillEnvelopeV1,
    OrderEnvelopeV1,
)
from core.replay.time import created_at_from_ts_ms

SAMPLE_SNAPSHOT = {
    "policy_id": "risk_v2",
    "policy_version": "2.1.0",
    "git_commit": "abc1234",
    "checksum": "deadbeef",
    "effective_at": "2026-01-15T00:00:00Z",
}

SAMPLE_DECISION_CONTEXT = {
    "contract_version": "decision_contract_v1",
    "inputs": {"symbol": "BTCUSDT", "slippage_pct": 0.001},
    "thresholds": {"blocked_regimes": [3, 4], "max_slippage_pct": 0.002},
}


class TestDecisionEnvelopeV1:
    def test_to_dict_omits_none(self):
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
        )
        d = env.to_dict()
        assert "policy_id" not in d
        assert "policy_hash" not in d
        assert "input_hash" not in d
        assert "output_hash" not in d
        assert "correlation_id" not in d
        assert "trace_id" not in d
        assert "decision_context" not in d
        assert "policy_snapshot" not in d
        assert d["event_type"] == "DECISION"
        assert d["schema_version"] == "envelope.v1"
        assert d["created_at"] == created_at_from_ts_ms(1700000000000)

    def test_to_dict_includes_present_optionals(self):
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
            policy_id="risk_policy_v1",
            policy_hash="abc123",
        )
        d = env.to_dict()
        assert d["policy_id"] == "risk_policy_v1"
        assert d["policy_hash"] == "abc123"
        assert "input_hash" not in d
        assert "output_hash" not in d

    def test_policy_snapshot_included_when_set(self):
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = env.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_trace_and_decision_context_included_when_set(self):
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
            correlation_id="corr-123",
            trace_id="trace-123",
            decision_context=SAMPLE_DECISION_CONTEXT,
        )
        d = env.to_dict()
        assert d["correlation_id"] == "corr-123"
        assert d["trace_id"] == "trace-123"
        assert d["decision_context"] == SAMPLE_DECISION_CONTEXT

    def test_created_at_is_canonical_milliseconds(self):
        ts_ms = 1700000000123
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-002",
            ts_ms=ts_ms,
            payload={"decision": "ALLOW"},
        )
        d = env.to_dict()
        assert d["created_at"] == created_at_from_ts_ms(ts_ms)
        assert d["created_at"].endswith("Z")
        assert "." in d["created_at"]

    def test_created_at_preserves_explicit_value(self):
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-003",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
            created_at="",
        )
        d = env.to_dict()
        assert d["created_at"] == ""

    def test_roundtrip_determinism(self):
        kwargs = dict(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "BLOCK", "symbol": "ETHUSDT"},
            policy_id="risk_policy_v1",
        )
        env1 = DecisionEnvelopeV1(**kwargs)
        env2 = DecisionEnvelopeV1(**kwargs)
        assert canonical_hash(env1.to_dict()) == canonical_hash(env2.to_dict())

    def test_roundtrip_determinism_with_snapshot(self):
        kwargs = dict(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="ev-001",
            ts_ms=1700000000000,
            payload={"decision": "ALLOW"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        env1 = DecisionEnvelopeV1(**kwargs)
        env2 = DecisionEnvelopeV1(**kwargs)
        assert canonical_hash(env1.to_dict()) == canonical_hash(env2.to_dict())


class TestOrderEnvelopeV1:
    def test_to_dict_omits_none(self):
        env = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=1700000000000,
            payload={"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.01},
        )
        d = env.to_dict()
        assert "policy_id" not in d
        assert "correlation_id" not in d
        assert "trace_id" not in d
        assert "decision_context" not in d
        assert "policy_snapshot" not in d
        assert d["event_type"] == "ORDER"
        assert d["created_at"] == created_at_from_ts_ms(1700000000000)

    def test_to_dict_includes_present_optionals(self):
        env = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=1700000000000,
            payload={"symbol": "BTCUSDT"},
            input_hash="inp-hash",
            output_hash="out-hash",
        )
        d = env.to_dict()
        assert d["input_hash"] == "inp-hash"
        assert d["output_hash"] == "out-hash"

    def test_policy_snapshot_included_when_set(self):
        env = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=1700000000000,
            payload={"symbol": "BTCUSDT"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = env.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_order_context_fields_included_when_set(self):
        env = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="ord-001",
            ts_ms=1700000000000,
            payload={"symbol": "BTCUSDT"},
            correlation_id="corr-456",
            trace_id="trace-456",
            decision_context=SAMPLE_DECISION_CONTEXT,
        )
        d = env.to_dict()
        assert d["correlation_id"] == "corr-456"
        assert d["trace_id"] == "trace-456"
        assert d["decision_context"] == SAMPLE_DECISION_CONTEXT


class TestFillEnvelopeV1:
    def test_to_dict_omits_none(self):
        env = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="fill-001",
            ts_ms=1700000000000,
            payload={"order_id": "ord-001", "status": "FILLED"},
        )
        d = env.to_dict()
        assert "policy_id" not in d
        assert "correlation_id" not in d
        assert "trace_id" not in d
        assert "decision_context" not in d
        assert "policy_snapshot" not in d
        assert d["event_type"] == "FILL"
        assert d["created_at"] == created_at_from_ts_ms(1700000000000)

    def test_to_dict_includes_present_optionals(self):
        env = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="fill-001",
            ts_ms=1700000000000,
            payload={"order_id": "ord-001"},
            policy_id="risk_policy_v1",
            policy_hash="ph",
            input_hash="ih",
            output_hash="oh",
        )
        d = env.to_dict()
        assert d["policy_id"] == "risk_policy_v1"
        assert d["policy_hash"] == "ph"
        assert d["input_hash"] == "ih"
        assert d["output_hash"] == "oh"

    def test_policy_snapshot_included_when_set(self):
        env = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="fill-001",
            ts_ms=1700000000000,
            payload={"order_id": "ord-001"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = env.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_fill_context_fields_included_when_set(self):
        env = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="fill-001",
            ts_ms=1700000000000,
            payload={"order_id": "ord-001"},
            correlation_id="corr-789",
            trace_id="trace-789",
            decision_context=SAMPLE_DECISION_CONTEXT,
        )
        d = env.to_dict()
        assert d["correlation_id"] == "corr-789"
        assert d["trace_id"] == "trace-789"
        assert d["decision_context"] == SAMPLE_DECISION_CONTEXT
