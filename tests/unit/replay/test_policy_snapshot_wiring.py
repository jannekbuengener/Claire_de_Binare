"""Tests for #748 Slice 2 policy_snapshot wiring.

Verifies toggle OFF/ON behavior, zero-payload-change invariant,
and propagation through the Decision→Order→Fill chain.
"""

import json

import pytest

from core.replay.policy_snapshot import (
    build_policy_snapshot,
    policy_snapshot_binding_enabled,
)
from core.replay.envelopes import (
    DecisionEnvelopeV1,
    FillEnvelopeV1,
    OrderEnvelopeV1,
)
from core.replay.canonical_json import canonical_hash
from core.utils.redis_payload import sanitize_payload
from services.execution.models import Order as ExecutionOrder
from services.execution.models import _parse_json_field
from services.risk.models import Order as RiskOrder


SAMPLE_THRESHOLDS = {
    "return_1m_min": -2.0,
    "return_5m_min": -5.0,
    "staleness_s_max": 5.0,
    "allowed_regimes": [0, 1],
}

SAMPLE_TS_MS = 1706000000000

SAMPLE_SNAPSHOT = {
    "policy_id": "risk_policy_v1",
    "version": "1.0.0",
    "git_commit": "abc1234",
    "checksum": "deadbeef" * 8,
    "effective_at": "2024-01-23T13:46:40+00:00",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure no toggle/env leaks between tests."""
    monkeypatch.delenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", raising=False)
    monkeypatch.delenv("CDB_GIT_COMMIT", raising=False)
    monkeypatch.delenv("CDB_POLICY_VERSION", raising=False)


# ---------------------------------------------------------------------------
# Toggle OFF: zero payload change
# ---------------------------------------------------------------------------

class TestToggleOff:
    """Toggle OFF (default) must produce ZERO payload changes."""

    def test_risk_order_to_dict_no_snapshot_key(self):
        """Toggle OFF -> Order.to_dict() must NOT contain 'policy_snapshot' key."""
        order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            stop_loss_pct=2.0,
            signal_id="sig-1",
            reason="test",
            timestamp=1706000000,
            strategy_id="strat-1",
        )
        d = order.to_dict()
        assert "policy_snapshot" not in d

    def test_risk_order_snapshot_is_none(self):
        """Toggle OFF -> Order.policy_snapshot is None."""
        order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            stop_loss_pct=2.0,
            signal_id="sig-1",
            reason="test",
            timestamp=1706000000,
            strategy_id="strat-1",
        )
        assert order.policy_snapshot is None

    def test_execution_order_to_dict_no_snapshot_key(self):
        """Toggle OFF -> Execution Order.to_dict() must NOT contain 'policy_snapshot' key."""
        order = ExecutionOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
        )
        d = order.to_dict()
        assert "policy_snapshot" not in d

    def test_decision_envelope_no_snapshot_key(self):
        """Toggle OFF -> DecisionEnvelopeV1.to_dict() omits policy_snapshot."""
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="test-1",
            ts_ms=1000,
            payload={"decision": "ALLOW", "symbol": "BTCUSDT"},
        )
        d = env.to_dict()
        assert "policy_snapshot" not in d

    def test_order_envelope_no_snapshot_key(self):
        """Toggle OFF -> OrderEnvelopeV1.to_dict() omits policy_snapshot."""
        env = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="test-2",
            ts_ms=2000,
            payload={"symbol": "BTCUSDT", "side": "BUY"},
        )
        d = env.to_dict()
        assert "policy_snapshot" not in d

    def test_fill_envelope_no_snapshot_key(self):
        """Toggle OFF -> FillEnvelopeV1.to_dict() omits policy_snapshot."""
        env = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="test-3",
            ts_ms=3000,
            payload={"order_id": "o-1", "fill_id": "f-1"},
        )
        d = env.to_dict()
        assert "policy_snapshot" not in d

    def test_golden_hash_unchanged(self):
        """Toggle OFF -> envelope hash identical to known baseline."""
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="test-1",
            ts_ms=1000,
            payload={"decision": "ALLOW", "symbol": "BTCUSDT"},
        )
        # Compute hash without snapshot
        hash_without = canonical_hash(env.to_dict())
        # Explicitly set None (same as default)
        env.policy_snapshot = None
        hash_with_none = canonical_hash(env.to_dict())
        assert hash_without == hash_with_none


# ---------------------------------------------------------------------------
# Toggle ON: snapshot present
# ---------------------------------------------------------------------------

class TestToggleOn:
    """Toggle ON must produce valid policy_snapshot in all envelopes."""

    def test_build_snapshot_via_toggle(self, monkeypatch):
        """Toggle ON -> build_policy_snapshot produces valid snapshot."""
        monkeypatch.setenv("CDB_POLICY_SNAPSHOT_BINDING_ENABLED", "1")
        monkeypatch.setenv("CDB_GIT_COMMIT", "abc1234")
        monkeypatch.setenv("CDB_POLICY_VERSION", "1.0.0")
        assert policy_snapshot_binding_enabled() is True
        snap = build_policy_snapshot(SAMPLE_THRESHOLDS, SAMPLE_TS_MS)
        assert set(snap.keys()) == {
            "policy_id", "version", "git_commit", "checksum", "effective_at",
        }

    def test_risk_order_carries_snapshot(self):
        """Toggle ON -> Risk Order.policy_snapshot is set."""
        order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            stop_loss_pct=2.0,
            signal_id="sig-1",
            reason="test",
            timestamp=1706000000,
            strategy_id="strat-1",
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        assert order.policy_snapshot == SAMPLE_SNAPSHOT

    def test_risk_order_to_dict_has_snapshot(self):
        """Toggle ON -> Order.to_dict() contains 'policy_snapshot' key."""
        order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            stop_loss_pct=2.0,
            signal_id="sig-1",
            reason="test",
            timestamp=1706000000,
            strategy_id="strat-1",
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = order.to_dict()
        assert "policy_snapshot" in d
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_decision_envelope_has_snapshot(self):
        """Toggle ON -> DecisionEnvelopeV1.to_dict() includes policy_snapshot."""
        env = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="test-1",
            ts_ms=1000,
            payload={"decision": "ALLOW", "symbol": "BTCUSDT"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = env.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_order_envelope_has_snapshot(self):
        """Toggle ON -> OrderEnvelopeV1.to_dict() includes policy_snapshot."""
        env = OrderEnvelopeV1(
            schema_version="envelope.v1",
            event_type="ORDER",
            event_id="test-2",
            ts_ms=2000,
            payload={"symbol": "BTCUSDT", "side": "BUY"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = env.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_fill_envelope_has_snapshot(self):
        """Toggle ON -> FillEnvelopeV1.to_dict() includes policy_snapshot."""
        env = FillEnvelopeV1(
            schema_version="envelope.v1",
            event_type="FILL",
            event_id="test-3",
            ts_ms=3000,
            payload={"order_id": "o-1", "fill_id": "f-1"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = env.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT

    def test_snapshot_changes_envelope_hash(self):
        """Envelope with snapshot produces different hash than without."""
        base = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="test-1",
            ts_ms=1000,
            payload={"decision": "ALLOW", "symbol": "BTCUSDT"},
        )
        with_snap = DecisionEnvelopeV1(
            schema_version="envelope.v1",
            event_type="DECISION",
            event_id="test-1",
            ts_ms=1000,
            payload={"decision": "ALLOW", "symbol": "BTCUSDT"},
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        assert canonical_hash(base.to_dict()) != canonical_hash(with_snap.to_dict())


# ---------------------------------------------------------------------------
# Propagation: Redis roundtrip
# ---------------------------------------------------------------------------

class TestPropagation:
    """Verify policy_snapshot survives Decision→Order→Fill chain."""

    def test_redis_roundtrip_risk_to_execution(self):
        """to_dict() -> sanitize_payload() -> from_event() preserves snapshot."""
        risk_order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            stop_loss_pct=2.0,
            signal_id="sig-1",
            reason="test",
            timestamp=1706000000,
            strategy_id="strat-1",
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        # Simulate Redis path: to_dict -> sanitize_payload -> JSON -> parse -> from_event
        raw_dict = risk_order.to_dict()
        sanitized = sanitize_payload(raw_dict)
        # sanitize_payload converts dicts to JSON strings
        assert isinstance(sanitized["policy_snapshot"], str)
        # Simulate JSON roundtrip (Redis PUBLISH path)
        json_str = json.dumps(sanitized)
        received = json.loads(json_str)
        exec_order = ExecutionOrder.from_event(received)
        assert exec_order.policy_snapshot == SAMPLE_SNAPSHOT

    def test_redis_roundtrip_no_snapshot(self):
        """Toggle OFF: no policy_snapshot key survives to execution."""
        risk_order = RiskOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            stop_loss_pct=2.0,
            signal_id="sig-1",
            reason="test",
            timestamp=1706000000,
            strategy_id="strat-1",
        )
        raw_dict = risk_order.to_dict()
        assert "policy_snapshot" not in raw_dict
        sanitized = sanitize_payload(raw_dict)
        assert "policy_snapshot" not in sanitized
        json_str = json.dumps(sanitized)
        received = json.loads(json_str)
        exec_order = ExecutionOrder.from_event(received)
        assert exec_order.policy_snapshot is None

    def test_execution_order_to_dict_no_snapshot_when_none(self):
        """Execution Order.to_dict() omits policy_snapshot when None."""
        exec_order = ExecutionOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
        )
        d = exec_order.to_dict()
        assert "policy_snapshot" not in d

    def test_execution_order_to_dict_has_snapshot_when_set(self):
        """Execution Order.to_dict() includes policy_snapshot when set."""
        exec_order = ExecutionOrder(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            policy_snapshot=SAMPLE_SNAPSHOT,
        )
        d = exec_order.to_dict()
        assert d["policy_snapshot"] == SAMPLE_SNAPSHOT


# ---------------------------------------------------------------------------
# _parse_json_field edge cases
# ---------------------------------------------------------------------------

class TestParseJsonField:
    """Edge cases for _parse_json_field (only used for policy_snapshot)."""

    def test_none_returns_none(self):
        assert _parse_json_field(None) is None

    def test_dict_passthrough(self):
        assert _parse_json_field({"a": 1}) == {"a": 1}

    def test_json_string_parsed(self):
        assert _parse_json_field('{"a": 1}') == {"a": 1}

    def test_invalid_json_returns_none(self):
        assert _parse_json_field("not-json") is None

    def test_json_non_dict_returns_none(self):
        assert _parse_json_field("[1, 2, 3]") is None

    def test_int_returns_none(self):
        assert _parse_json_field(42) is None

    def test_nested_snapshot_roundtrip(self):
        """Full snapshot dict survives JSON string roundtrip."""
        as_str = json.dumps(SAMPLE_SNAPSHOT)
        result = _parse_json_field(as_str)
        assert result == SAMPLE_SNAPSHOT
