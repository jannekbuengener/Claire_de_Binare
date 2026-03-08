"""Golden and determinism tests for Decision Contract v1 (LR-762)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.contracts.decision_contract_v1 import (
    DecisionContractError,
    build_decision_contract_audit_record,
    build_decision_contract_v1_bundle,
    evaluate_decision_contract_v1,
    verify_decision_contract_v1_bundle,
    write_decision_contract_audit_record,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "decision_contract_v1"
    / "golden_vectors.json"
)


def _load_vectors() -> list[dict]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.contract
def test_decision_contract_v1_golden_vectors_exact_match():
    vectors = _load_vectors()
    assert vectors, "expected non-empty golden vector set"

    for case in vectors:
        output = evaluate_decision_contract_v1(case["input"])
        assert output == case["expected_output"], f"golden mismatch for {case['name']}"
        assert output["reason_codes"] == sorted(output["reason_codes"])


@pytest.mark.contract
def test_decision_contract_v1_deterministic_50x():
    vectors = _load_vectors()
    assert vectors, "expected non-empty golden vector set"

    for case in vectors:
        first = evaluate_decision_contract_v1(case["input"])
        first_input_json = first["evidence"]["canonical_input"]
        first_output_json = first["evidence"]["canonical_output"]
        first_input_hash = first["evidence"]["input_hash"]
        first_decision_hash = first["evidence"]["decision_hash"]

        for _ in range(50):
            current = evaluate_decision_contract_v1(case["input"])
            assert current["evidence"]["canonical_input"] == first_input_json
            assert current["evidence"]["canonical_output"] == first_output_json
            assert current["evidence"]["input_hash"] == first_input_hash
            assert current["evidence"]["decision_hash"] == first_decision_hash


@pytest.mark.contract
def test_decision_contract_v1_bundle_verification_roundtrip():
    vectors = _load_vectors()
    for case in vectors:
        bundle = build_decision_contract_v1_bundle(case["input"])
        ok, reason = verify_decision_contract_v1_bundle(bundle, require_allow=False)
        assert ok, f"bundle verification failed for {case['name']}: {reason}"


@pytest.mark.contract
def test_decision_contract_v1_fail_closed_on_float_inputs():
    with pytest.raises(DecisionContractError, match="must not be float"):
        evaluate_decision_contract_v1(
            {
                "run_mode": "paper",
                "order": {
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "quantity": 0.01,  # float -> fail-closed
                    "price_ref": "50000",
                    "timestamp_input_ms": 1700000000000,
                    "reduce_only": False,
                },
                "account_state": {
                    "balance_usdt": "10000",
                    "total_exposure_usdt": "100",
                    "daily_drawdown_pct": "1.0",
                },
                "open_positions": {},
                "risk_policy": {
                    "max_notional_usdt": "2000",
                    "max_total_exposure_usdt": "5000",
                    "max_daily_drawdown_pct": "5.0",
                },
                "system_config": {"service": "tests"},
                "context": {
                    "source": "tests",
                    "signal_id": "sig-float",
                    "strategy_id": "paper",
                    "bot_id": "",
                },
            }
        )


@pytest.mark.contract
def test_decision_contract_v1_audit_record_writer(tmp_path):
    case = _load_vectors()[0]
    bundle = build_decision_contract_v1_bundle(case["input"])

    record = build_decision_contract_audit_record(bundle)
    assert record["decision_hash"] == bundle["output"]["evidence"]["decision_hash"]

    out_path = write_decision_contract_audit_record(bundle, output_dir=tmp_path)
    assert out_path.exists()

    persisted = json.loads(out_path.read_text(encoding="utf-8"))
    assert persisted["decision_hash"] == bundle["output"]["evidence"]["decision_hash"]
    assert persisted["input_hash"] == bundle["output"]["evidence"]["input_hash"]
