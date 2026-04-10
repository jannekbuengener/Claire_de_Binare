"""Phase 9: Trace Contract v1 Schema Validation Tests

Validates required IDs/hashes per trace_contract_v1.md (PR-1 scope).

Focus:
- Hash determinism (policy_hash + output_hash)
- _phase9_enrich_evidence() helper behavior with toggle ON/OFF
"""

import pytest

from core.utils.uuid_gen import (
    POLICY_ID,
    compute_output_hash,
    compute_policy_hash,
)


class TestPolicyHashDeterminism:
    def test_policy_hash_same_input_same_output(self):
        thresholds = {"max_exposure": 0.30, "stop_loss": 0.02, "nested": {"a": 1}}
        hash1 = compute_policy_hash(thresholds)
        hash2 = compute_policy_hash(thresholds)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_policy_hash_order_independent(self):
        thresholds_a = {"z": 1, "a": 2}
        thresholds_b = {"a": 2, "z": 1}
        assert compute_policy_hash(thresholds_a) == compute_policy_hash(thresholds_b)

    def test_policy_hash_different_input_different_output(self):
        assert compute_policy_hash({"max_exposure": 0.30}) != compute_policy_hash(
            {"max_exposure": 0.50}
        )


class TestOutputHashDeterminism:
    def test_output_hash_deterministic(self):
        hash1 = compute_output_hash(
            decision="BLOCK",
            reason_code="RC_001",
            decision_pk="pk-123",
            decision_id="dec-456",
            contract_version="v1",
            input_hash="abc",
            policy_hash="def",
        )
        hash2 = compute_output_hash(
            decision="BLOCK",
            reason_code="RC_001",
            decision_pk="pk-123",
            decision_id="dec-456",
            contract_version="v1",
            input_hash="abc",
            policy_hash="def",
        )
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_output_hash_varies_with_decision(self):
        base_args = {
            "decision_pk": "pk-123",
            "decision_id": "dec-456",
            "contract_version": "v1",
            "input_hash": "abc",
            "policy_hash": "def",
        }
        hash_block = compute_output_hash(
            decision="BLOCK", reason_code="RC_001", **base_args
        )
        hash_allow = compute_output_hash(
            decision="ALLOW", reason_code=None, **base_args
        )
        assert hash_block != hash_allow

    def test_output_hash_varies_with_reason_code(self):
        base_args = {
            "decision": "BLOCK",
            "decision_pk": "pk-123",
            "decision_id": "dec-456",
            "contract_version": "v1",
            "input_hash": "abc",
            "policy_hash": "def",
        }
        hash_rc001 = compute_output_hash(reason_code="RC_001", **base_args)
        hash_rc002 = compute_output_hash(reason_code="RC_002", **base_args)
        assert hash_rc001 != hash_rc002


class TestPolicyIdFormat:
    def test_policy_id_versioned_format(self):
        assert POLICY_ID == "risk_policy_v1"
        assert POLICY_ID.startswith("risk_policy_")


class TestPhase9EnrichEvidence:
    @pytest.fixture
    def mock_evidence(self):
        return {
            "contract_version": "decision_contract_v1",
            "signal_id": "sig-test-001",
            "decision_id": "dec-test-001",
            "trace_id": "trace-test-001",
            "timestamp_ms": 1700000000001,
            "symbol": "BTCUSDT",
            "regime_id": 0,
            "return_1m": 0.0,
            "return_5m": 0.0,
            "price_change_5m": 0.0,
            "pct_change_15m": 5.0,
            "volume_15m": 0.20,
            "daily_drawdown_pct": 0.0,
            "total_exposure_pct": 0.0,
            "slippage_pct": 0.0,
            "staleness_s": 0.001,
            "data_silence_s": 0.001,
            "thresholds": {
                "return_1m_min": -2.0,
                "return_5m_min": -5.0,
                "signal_pct_change_15m_min": 3.0,
                "signal_volume_15m_min": 0.165,
            },
        }

    def test_toggle_off_zero_impact(self, mock_evidence, monkeypatch):
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")
        import services.risk.service as risk_svc

        evidence_before = mock_evidence.copy()
        evidence = mock_evidence.copy()

        enriched, input_hash, decision_pk = risk_svc._phase9_enrich_evidence(
            evidence=evidence,
            decision="ALLOW",
            reason_code=None,
            symbol="BTCUSDT",
            ts_ms=1700000000001,
        )

        assert input_hash is None
        assert decision_pk is None
        assert enriched == evidence_before

        assert "policy_id" not in enriched
        assert "policy_hash" not in enriched
        assert "output_hash" not in enriched
        assert "decision_context" not in enriched
        assert "input_hash" not in enriched

    def test_toggle_on_includes_phase9_fields(self, mock_evidence, monkeypatch):
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
        import services.risk.service as risk_svc

        evidence = mock_evidence.copy()
        enriched, input_hash, decision_pk = risk_svc._phase9_enrich_evidence(
            evidence=evidence,
            decision="ALLOW",
            reason_code=None,
            symbol="BTCUSDT",
            ts_ms=1700000000001,
        )

        assert input_hash is not None
        assert decision_pk is not None
        assert len(input_hash) == 64

        assert enriched["policy_id"] == "risk_policy_v1"
        assert len(enriched["policy_hash"]) == 64
        assert len(enriched["output_hash"]) == 64
        assert len(enriched["input_hash"]) == 64
        assert enriched["input_hash"] == input_hash

        assert "decision_context" in enriched
        assert "thresholds" in enriched["decision_context"]
        assert "inputs" in enriched["decision_context"]
        assert "contract_version" in enriched["decision_context"]
        assert (
            enriched["decision_context"]["contract_version"]
            == "decision_contract_v1"
        )

    def test_hashes_are_deterministic(self, mock_evidence, monkeypatch):
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
        import services.risk.service as risk_svc

        ev1 = mock_evidence.copy()
        ev2 = mock_evidence.copy()

        enriched1, input_hash1, decision_pk1 = risk_svc._phase9_enrich_evidence(
            evidence=ev1,
            decision="BLOCK",
            reason_code="RC_001",
            symbol="BTCUSDT",
            ts_ms=1700000000001,
        )
        enriched2, input_hash2, decision_pk2 = risk_svc._phase9_enrich_evidence(
            evidence=ev2,
            decision="BLOCK",
            reason_code="RC_001",
            symbol="BTCUSDT",
            ts_ms=1700000000001,
        )

        assert input_hash1 == input_hash2
        assert decision_pk1 == decision_pk2
        assert enriched1["policy_hash"] == enriched2["policy_hash"]
        assert enriched1["output_hash"] == enriched2["output_hash"]

    def test_output_hash_changes_with_decision(self, mock_evidence, monkeypatch):
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
        import services.risk.service as risk_svc

        ev_allow = mock_evidence.copy()
        ev_block = mock_evidence.copy()

        enriched_allow, _, _ = risk_svc._phase9_enrich_evidence(
            evidence=ev_allow,
            decision="ALLOW",
            reason_code=None,
            symbol="BTCUSDT",
            ts_ms=1700000000001,
        )
        enriched_block, _, _ = risk_svc._phase9_enrich_evidence(
            evidence=ev_block,
            decision="BLOCK",
            reason_code="RC_001",
            symbol="BTCUSDT",
            ts_ms=1700000000001,
        )

        assert enriched_allow["output_hash"] != enriched_block["output_hash"]
        assert enriched_allow["policy_hash"] == enriched_block["policy_hash"]


class TestToggleAccessor:
    """B1: Verifiziert trace_contract_v1_enabled() Verhalten."""

    def test_toggle_off_default(self, monkeypatch):
        """Default (kein Env-Var gesetzt) = OFF."""
        monkeypatch.delenv("TRACE_CONTRACT_V1_ENABLED", raising=False)
        from core.utils.trace_toggle import trace_contract_v1_enabled

        assert trace_contract_v1_enabled() is False

    def test_toggle_off_explicit(self, monkeypatch):
        """Explizit '0' = OFF."""
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")
        from core.utils.trace_toggle import trace_contract_v1_enabled

        assert trace_contract_v1_enabled() is False

    def test_toggle_on(self, monkeypatch):
        """'1' = ON."""
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
        from core.utils.trace_toggle import trace_contract_v1_enabled

        assert trace_contract_v1_enabled() is True

    def test_toggle_invalid_value_is_off(self, monkeypatch):
        """Ungültiger Wert = OFF (fail-safe)."""
        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "true")
        from core.utils.trace_toggle import trace_contract_v1_enabled

        assert trace_contract_v1_enabled() is False

    def test_toggle_respects_monkeypatch(self, monkeypatch):
        """Wechsel zwischen ON/OFF in Tests möglich (kein Modul-Cache)."""
        from core.utils.trace_toggle import trace_contract_v1_enabled

        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "1")
        assert trace_contract_v1_enabled() is True

        monkeypatch.setenv("TRACE_CONTRACT_V1_ENABLED", "0")
        assert trace_contract_v1_enabled() is False


class TestDecisionPkDeterminism:
    """B2: decision_pk darf nicht von wall-clock abhängen."""

    def test_input_hash_excludes_wall_clock_fields(self):
        """timestamp_ms, staleness_s, data_silence_s sind NICHT im Hash."""
        from core.utils.uuid_gen import compute_input_snapshot_hash

        base = {
            "symbol": "BTCUSDT",
            "regime_id": 0,
            "return_1m": 1.0,
            "return_5m": 2.0,
            "price_change_5m": 3.0,
            "pct_change_15m": 5.0,
            "volume_15m": 0.20,
            "daily_drawdown_pct": 1.0,
            "total_exposure_pct": 10.0,
            "slippage_pct": 0.1,
            "thresholds": {"a": 1},
        }

        # Gleiche deterministische Felder, unterschiedliche wall-clock-Felder
        ev1 = {**base, "timestamp_ms": 1000, "staleness_s": 0.5, "data_silence_s": 1.0}
        ev2 = {**base, "timestamp_ms": 9999, "staleness_s": 99.0, "data_silence_s": 50.0}

        assert compute_input_snapshot_hash(ev1) == compute_input_snapshot_hash(ev2)

    def test_decision_pk_stable_across_wall_clocks(self):
        """Gleicher signal_ts_ms + gleiche Inputs → gleicher decision_pk."""
        from core.utils.uuid_gen import generate_decision_pk

        signal_ts_ms = 1700000000000
        evidence = {
            "symbol": "BTCUSDT",
            "regime_id": 0,
            "return_1m": 1.0,
            "return_5m": 2.0,
            "price_change_5m": 3.0,
            "pct_change_15m": 5.0,
            "volume_15m": 0.20,
            "daily_drawdown_pct": 1.0,
            "total_exposure_pct": 10.0,
            "slippage_pct": 0.1,
            "thresholds": {"a": 1},
            "timestamp_ms": 1700000001000,  # wall-clock 1
            "staleness_s": 0.5,
            "data_silence_s": 1.0,
        }

        pk1 = generate_decision_pk("BTCUSDT", signal_ts_ms, evidence)

        # Anderer wall-clock-Zeitpunkt
        evidence["timestamp_ms"] = 1700000099000
        evidence["staleness_s"] = 99.0
        evidence["data_silence_s"] = 50.0

        pk2 = generate_decision_pk("BTCUSDT", signal_ts_ms, evidence)

        assert pk1 == pk2, "decision_pk muss wall-clock-unabhängig sein"

    def test_decision_pk_varies_with_signal_ts(self):
        """Unterschiedlicher signal_ts_ms → unterschiedlicher decision_pk."""
        from core.utils.uuid_gen import generate_decision_pk

        evidence = {
            "symbol": "BTCUSDT",
            "regime_id": 0,
            "return_1m": 1.0,
            "return_5m": 2.0,
            "price_change_5m": 3.0,
            "pct_change_15m": 5.0,
            "volume_15m": 0.20,
            "daily_drawdown_pct": 1.0,
            "total_exposure_pct": 10.0,
            "slippage_pct": 0.1,
            "thresholds": {"a": 1},
        }

        pk1 = generate_decision_pk("BTCUSDT", 1700000000000, evidence)
        pk2 = generate_decision_pk("BTCUSDT", 1700000099000, evidence)

        assert pk1 != pk2, "Unterschiedlicher signal_ts_ms muss unterschiedlichen pk erzeugen"
