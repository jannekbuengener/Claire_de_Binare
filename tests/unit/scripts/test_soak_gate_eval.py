"""Tests for soak_gate_eval.py shadow evidence hard gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from soak_gate_eval import evaluate_shadow_soak_evidence


def _write_evidence(
    tmp_path: Path,
    *,
    shadow_blocked_total: int = 1,
    orders_filled: int = 0,
    order_result_found: bool = True,
    order_result_status: str = "REJECTED",
    filled_quantity: float = 0.0,
    probe_error: str | None = None,
    skip_probe: bool = False,
    has_live_data: bool = True,
    orders_approved: int = 0,
    risk_blocked_all: bool = True,
    trading_mode: str | None = "mock",
    kill_switch_active: bool | None = False,
    skip_exec_status: bool = False,
    skip_risk_status: bool = False,
) -> Path:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "evidence_index.json").write_text(
        json.dumps(
            {
                "shadow_blocked_total": shadow_blocked_total,
                "orders_filled": orders_filled,
                "has_live_data": has_live_data,
                "orders_approved": orders_approved,
                "risk_blocked_all": risk_blocked_all,
            }
        ),
        encoding="utf-8",
    )
    if not skip_probe:
        (evidence_dir / "shadow_block_probe.json").write_text(
            json.dumps(
                {
                    "probe_order_id": "ci-shadow-probe-123",
                    "publish_subscribers": 1,
                    "order_result_found": order_result_found,
                    "order_result_source": "pubsub",
                    "stream_order_result_found": True,
                    "order_result": {
                        "status": order_result_status,
                        "filled_quantity": filled_quantity,
                    },
                    "error": probe_error,
                }
            ),
            encoding="utf-8",
        )
    endpoints_dir = evidence_dir / "endpoints"
    endpoints_dir.mkdir()
    if not skip_exec_status:
        (endpoints_dir / "execution_status.json").write_text(
            json.dumps({"mode": trading_mode, "service": "execution_service"}),
            encoding="utf-8",
        )
    if not skip_risk_status:
        risk_state: dict = {"total_exposure": 0.0}
        if kill_switch_active is not None:
            risk_state["circuit_breaker"] = kill_switch_active
        (endpoints_dir / "risk_status.json").write_text(
            json.dumps({"risk_state": risk_state, "status": "running"}),
            encoding="utf-8",
        )
    return evidence_dir


def test_evaluate_shadow_soak_evidence_passes(tmp_path: Path) -> None:
    result = evaluate_shadow_soak_evidence(_write_evidence(tmp_path))

    assert result["verdict"] == "PASS"
    assert result["failures"] == []
    assert result["schema_version"] == "1.1"
    assert result["runtime"]["trading_mode"] == "mock"
    assert result["runtime"]["kill_switch_active"] is False


@pytest.mark.parametrize(
    ("kwargs", "expected_failure"),
    [
        ({"shadow_blocked_total": 0}, "shadow_blocked_total_gte_1"),
        ({"orders_filled": 1}, "execution_orders_filled_total_eq_0"),
        (
            {"order_result_found": False, "probe_error": "timeout"},
            "auditable_reject_present",
        ),
        ({"filled_quantity": 1.0}, "reject_filled_quantity_eq_0"),
        ({"has_live_data": False}, "has_live_data_true"),
        ({"orders_approved": 1}, "orders_approved_eq_0"),
        ({"risk_blocked_all": False}, "risk_blocked_all_true"),
        ({"trading_mode": "live"}, "runtime_mode_verified"),
        ({"trading_mode": ""}, "runtime_mode_verified"),
        ({"kill_switch_active": True}, "kill_switch_precheck_inactive"),
    ],
)
def test_evaluate_shadow_soak_evidence_fails_closed(
    tmp_path: Path,
    kwargs: dict,
    expected_failure: str,
) -> None:
    result = evaluate_shadow_soak_evidence(_write_evidence(tmp_path, **kwargs))

    assert result["verdict"] == "FAIL"
    assert expected_failure in result["failures"]


def test_evaluate_shadow_soak_evidence_requires_probe_artifact(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        evaluate_shadow_soak_evidence(_write_evidence(tmp_path, skip_probe=True))
    assert exc_info.value.code == 1


def test_evaluate_fails_on_missing_execution_status(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        evaluate_shadow_soak_evidence(_write_evidence(tmp_path, skip_exec_status=True))
    assert exc_info.value.code == 1


def test_evaluate_fails_on_missing_risk_status(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        evaluate_shadow_soak_evidence(_write_evidence(tmp_path, skip_risk_status=True))
    assert exc_info.value.code == 1


def test_evaluate_fails_on_unevaluable_kill_switch(tmp_path: Path) -> None:
    """circuit_breaker key absent from risk_status → kill_switch not evaluable → FAIL."""
    result = evaluate_shadow_soak_evidence(
        _write_evidence(tmp_path, kill_switch_active=None)
    )
    assert result["verdict"] == "FAIL"
    assert "kill_switch_precheck_inactive" in result["failures"]


def test_evaluate_fails_on_ambiguous_runtime_mode(tmp_path: Path) -> None:
    """trading_mode absent (None) from execution_status → FAIL."""
    result = evaluate_shadow_soak_evidence(_write_evidence(tmp_path, trading_mode=None))
    assert result["verdict"] == "FAIL"
    assert "runtime_mode_verified" in result["failures"]
