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
            "pct_change_15m": 0.05,
            "volume_15m": 0.20,
            "daily_drawdown_pct": 0.0,
            "total_exposure_pct": 0.0,
            "slippage_pct": 0.0,
            "staleness_s": 0.001,
            "data_silence_s": 0.001,
            "thresholds": {
                "return_1m_min": -2.0,
                "return_5m_min": -5.0,
                "signal_pct_change_15m_min": 0.03,
                "signal_volume_15m_min": 0.165,
            },
        }

    def test_toggle_off_zero_impact(self, mock_evidence):
        import services.risk.service as risk_svc

        original_value = risk_svc.TRACE_CONTRACT_V1_ENABLED
        risk_svc.TRACE_CONTRACT_V1_ENABLED = False
        try:
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
        finally:
            risk_svc.TRACE_CONTRACT_V1_ENABLED = original_value

    def test_toggle_on_includes_phase9_fields(self, mock_evidence):
        import services.risk.service as risk_svc

        original_value = risk_svc.TRACE_CONTRACT_V1_ENABLED
        risk_svc.TRACE_CONTRACT_V1_ENABLED = True
        try:
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
        finally:
            risk_svc.TRACE_CONTRACT_V1_ENABLED = original_value

    def test_hashes_are_deterministic(self, mock_evidence):
        import services.risk.service as risk_svc

        original_value = risk_svc.TRACE_CONTRACT_V1_ENABLED
        risk_svc.TRACE_CONTRACT_V1_ENABLED = True
        try:
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
        finally:
            risk_svc.TRACE_CONTRACT_V1_ENABLED = original_value

    def test_output_hash_changes_with_decision(self, mock_evidence):
        import services.risk.service as risk_svc

        original_value = risk_svc.TRACE_CONTRACT_V1_ENABLED
        risk_svc.TRACE_CONTRACT_V1_ENABLED = True
        try:
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
        finally:
            risk_svc.TRACE_CONTRACT_V1_ENABLED = original_value
