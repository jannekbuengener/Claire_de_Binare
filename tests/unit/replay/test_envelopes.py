"""Tests for core.replay.envelopes — envelope dataclasses.

Governance: LR-021 Slice 1 (Deterministic Replay Framework)
"""

from core.replay.canonical_json import canonical_hash
from core.replay.envelopes import (
    DecisionEnvelopeV1,
    FillEnvelopeV1,
    OrderEnvelopeV1,
)


SAMPLE_SNAPSHOT = {
    "policy_id": "risk_v2",
    "policy_version": "2.1.0",
    "git_commit": "abc1234",
    "checksum": "deadbeef",
    "effective_at": "2026-01-15T00:00:00Z",
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
        assert "policy_snapshot" not in d
        assert d["event_type"] == "DECISION"
        assert d["schema_version"] == "envelope.v1"

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
        assert "policy_snapshot" not in d
        assert d["event_type"] == "ORDER"

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
        assert "policy_snapshot" not in d
        assert d["event_type"] == "FILL"

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
