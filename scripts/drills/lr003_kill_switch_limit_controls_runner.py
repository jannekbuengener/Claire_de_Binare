"""Deterministic LR-003 drill for kill-switch and limit controls.

This runner is intentionally repo-local and non-live. It exercises existing
fail-closed control paths and writes a compact evidence summary without
touching external services or live execution paths.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.contracts.decision_contract_v1 import evaluate_decision_contract_v1  # noqa: E402
from core.safety.kill_switch import (  # noqa: E402
    KILL_SWITCH_STATE_FILE_ENV,
    KillSwitch,
    KillSwitchReason,
)
from services.execution import service as execution_service  # noqa: E402
from services.risk import service as risk_service  # noqa: E402
from services.risk.config import RiskConfig  # noqa: E402

DRILL_ID = "lr003_kill_switch_limit_controls"
DEFAULT_OUTPUT_DIR = Path("reports/drills/lr003")
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "decision_contract_v1" / "golden_vectors.json"
)


class DummyRedisClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []
        self.streams: list[tuple[str, dict, int]] = []

    def publish(self, channel: str, payload: str) -> None:
        self.published.append((channel, payload))

    def xadd(self, stream: str, payload: dict, maxlen: int) -> None:
        self.streams.append((stream, payload, maxlen))


class DummyDatabase:
    def __init__(self) -> None:
        self.saved_orders: list[str] = []
        self.saved_trades: list[str] = []

    def save_order(self, result: object) -> None:
        self.saved_orders.append(result.order_id)

    def save_trade(self, result: object) -> None:
        self.saved_trades.append(result.order_id)


def _load_vectors() -> dict[str, dict]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        vectors = json.load(handle)
    return {case["name"]: case for case in vectors}


def _make_risk_manager() -> risk_service.RiskManager:
    test_config = RiskConfig(
        max_position_pct=0.10,
        max_total_exposure_pct=0.30,
        max_daily_drawdown_pct=0.05,
        stop_loss_pct=0.02,
    )
    with patch.object(risk_service, "config", test_config):
        return risk_service.RiskManager()


def _make_execution_payload() -> dict:
    return {
        "type": "order",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01,
        "strategy_id": "lr003-drill",
        "bot_id": "lr003-bot",
        "client_id": "lr003-client",
        "run_mode": "paper",
        "timestamp": 1700000000,
    }


def _scenario(
    name: str,
    *,
    passed: bool,
    expected: str,
    actual: str,
    details: dict | None = None,
) -> dict:
    return {
        "name": name,
        "passed": passed,
        "expected": expected,
        "actual": actual,
        "details": details or {},
    }


def _run_risk_kill_switch_active() -> dict:
    with TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / "kill_switch.state"
        kill_switch = KillSwitch(state_file=str(state_file))
        kill_switch.activate(
            KillSwitchReason.MANUAL,
            "LR-003 drill active gate",
            operator="lr003-drill",
        )
        with patch.dict(
            os.environ,
            {KILL_SWITCH_STATE_FILE_ENV: str(state_file)},
            clear=False,
        ):
            manager = _make_risk_manager()
            active, code, context = manager._kill_switch_gate()

    passed = (
        active is True
        and code == risk_service.KILL_SWITCH_BLOCK_REASON_CODE
        and context.get("reason") == KillSwitchReason.MANUAL.value
    )
    return _scenario(
        "risk_kill_switch_active_blocks",
        passed=passed,
        expected="active=True, code=KILL_SWITCH_ACTIVE, reason=manual",
        actual=f"active={active}, code={code}, reason={context.get('reason')}",
        details=context,
    )


def _run_risk_kill_switch_eval_error() -> dict:
    manager = _make_risk_manager()
    with patch.object(
        risk_service,
        "get_kill_switch_details",
        side_effect=RuntimeError("state file corrupt"),
    ):
        active, code, context = manager._kill_switch_gate()

    passed = (
        active is True
        and code == risk_service.KILL_SWITCH_UNEVALUABLE_REASON_CODE
        and "evaluation error" in context.get("message", "")
    )
    return _scenario(
        "risk_kill_switch_eval_error_fails_closed",
        passed=passed,
        expected="active=True, code=KILL_SWITCH_UNEVALUABLE, fail-closed message",
        actual=f"active={active}, code={code}, message={context.get('message')}",
        details=context,
    )


def _run_execution_kill_switch_active() -> dict:
    original_state = {
        "executor": execution_service.executor,
        "redis_client": execution_service.redis_client,
        "db": execution_service.db,
        "stats": execution_service.stats.copy(),
    }
    redis_stub = DummyRedisClient()
    db_stub = DummyDatabase()
    executor_mock = MagicMock()
    executor_mock.execute_order.side_effect = AssertionError(
        "kill-switch should block before executor"
    )
    publish_result = MagicMock()

    try:
        with TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "kill_switch.state"
            kill_switch = KillSwitch(state_file=str(state_file))
            kill_switch.activate(
                KillSwitchReason.MANUAL,
                "LR-003 drill execution block",
                operator="lr003-drill",
            )
            with patch.dict(
                os.environ,
                {KILL_SWITCH_STATE_FILE_ENV: str(state_file)},
                clear=False,
            ):
                execution_service.executor = executor_mock
                execution_service.redis_client = redis_stub
                execution_service.db = db_stub
                with patch.object(execution_service, "_publish_result", publish_result):
                    result = execution_service.process_order(_make_execution_payload())
    finally:
        execution_service.executor = original_state["executor"]
        execution_service.redis_client = original_state["redis_client"]
        execution_service.db = original_state["db"]
        execution_service.stats.clear()
        execution_service.stats.update(original_state["stats"])

    passed = (
        result is not None
        and result.status == execution_service.OrderStatus.REJECTED.value
        and "kill-switch active" in (result.error_message or "").lower()
        and executor_mock.execute_order.call_count == 0
        and publish_result.call_count == 1
    )
    return _scenario(
        "execution_kill_switch_active_blocks",
        passed=passed,
        expected="REJECTED before executor with persisted order_result",
        actual=(
            f"status={getattr(result, 'status', None)}, "
            f"published={publish_result.call_count}, "
            f"executor_calls={executor_mock.execute_order.call_count}"
        ),
        details={
            "order_id": getattr(result, "order_id", None),
            "error_message": getattr(result, "error_message", None),
            "saved_orders": db_stub.saved_orders,
        },
    )


def _run_limit_case(case_name: str) -> dict:
    case = _load_vectors()[case_name]
    output = evaluate_decision_contract_v1(case["input"])
    passed = output == case["expected_output"]
    return _scenario(
        case_name,
        passed=passed,
        expected=json.dumps(
            {
                "decision": case["expected_output"]["decision"],
                "reason_codes": case["expected_output"]["reason_codes"],
            },
            sort_keys=True,
        ),
        actual=json.dumps(
            {
                "decision": output["decision"],
                "reason_codes": output["reason_codes"],
            },
            sort_keys=True,
        ),
        details={
            "input_hash": output["evidence"]["input_hash"],
            "decision_hash": output["evidence"]["decision_hash"],
        },
    )


def build_summary(scenarios: list[dict]) -> dict:
    passed_count = sum(1 for scenario in scenarios if scenario["passed"])
    failed_count = len(scenarios) - passed_count
    return {
        "drill_id": DRILL_ID,
        "verdict": "PASS" if failed_count == 0 else "FAIL",
        "scenario_count": len(scenarios),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "scenarios": scenarios,
    }


def render_markdown(summary: dict) -> str:
    lines = [
        "# LR-003 Kill-Switch + Limit Controls Drill",
        "",
        f"- drill_id: `{summary['drill_id']}`",
        f"- verdict: `{summary['verdict']}`",
        f"- passed: `{summary['passed_count']}/{summary['scenario_count']}`",
        "",
        "| Scenario | Verdict | Expected | Actual |",
        "| --- | --- | --- | --- |",
    ]
    for scenario in summary["scenarios"]:
        lines.append(
            f"| `{scenario['name']}` | "
            f"`{'PASS' if scenario['passed'] else 'FAIL'}` | "
            f"{scenario['expected']} | {scenario['actual']} |"
        )
    lines.extend(
        [
            "",
            "Scope notes:",
            "- Uses existing risk/execution kill-switch gates and the existing decision contract vectors.",
            "- Read-only drill: no live endpoints, no exchange access, no state outside temporary kill-switch files.",
            "- Fail-closed expectation: kill-switch evaluation error must block; limit vectors must keep exact deterministic outputs.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_lr003_drill(output_dir: Path) -> dict:
    scenarios = [
        _run_risk_kill_switch_active(),
        _run_risk_kill_switch_eval_error(),
        _run_execution_kill_switch_active(),
        _run_limit_case("deny_max_notional"),
        _run_limit_case("deny_max_exposure"),
        _run_limit_case("deny_max_drawdown"),
        _run_limit_case("allow_reduce_only_sell"),
    ]
    summary = build_summary(scenarios)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "lr003_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_path / "lr003_report.md").write_text(
        render_markdown(summary),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic LR-003 kill-switch + limit controls drill."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for summary/report artifacts",
    )
    args = parser.parse_args()

    summary = run_lr003_drill(args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
