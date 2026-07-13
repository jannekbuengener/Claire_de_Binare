"""Shared helpers for Batch-A Stage-A/B gate scorers (#4032)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.metric_contract import is_rankable_job_metrics, metric_is_missing
from tools.arvp_vacation.strategy_metric_extraction import PROFIT_FACTOR_INFINITY_TOKEN

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"

STAGE_A_GATE_CONTRACT_PATH = (
    CONTRACTS_DIR / "batch_a_stage_a_gate_contract.v1.json"
)
STAGE_B_CONFIRMATION_CONTRACT_PATH = (
    CONTRACTS_DIR / "batch_a_stage_b_confirmation_contract.v1.json"
)

PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN = "-infinity"


class BatchAGateError(ValueError):
    """Fail-closed Batch-A gate evaluation error."""


def load_json_contract(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BatchAGateError(f"Gate contract missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BatchAGateError(f"Gate contract root must be object: {path}")
    return payload


def compute_gate_contract_sha256(contract: Mapping[str, Any]) -> str:
    return canonical_hash(dict(contract))


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def record_is_rankable(record: Mapping[str, Any]) -> bool:
    if record.get("rankable") is False:
        return False
    metrics = {
        "closed_trades_total": record.get("closed_trades_total"),
    }
    return is_rankable_job_metrics(metrics)


def profit_factor_passes_gate(
    value: object,
    *,
    threshold: float,
    net_pnl_positive: bool,
    closed_trades_gte: int,
) -> bool | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, str):
        token = value.strip().lower()
        if token == PROFIT_FACTOR_INFINITY_TOKEN:
            return net_pnl_positive and closed_trades_gte >= 10
        if token == PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN:
            return False
    numeric = _as_float(value)
    if numeric is None:
        return None
    if numeric == 0.0:
        return False
    return numeric >= threshold


def median_of_field(records: Sequence[Mapping[str, Any]], field: str) -> float | None:
    values: list[float] = []
    for record in records:
        if metric_is_missing(record, field):
            continue
        parsed = _as_float(record.get(field))
        if parsed is not None:
            values.append(parsed)
    if not values:
        return None
    return float(median(values))


def profit_factor_gate_value(
    records: Sequence[Mapping[str, Any]],
    *,
    field: str = "profit_factor",
) -> float | str | None:
    """Median numeric profit factor, preserving canonical infinity tokens."""
    infinity_seen = False
    values: list[float] = []
    for record in records:
        if metric_is_missing(record, field):
            continue
        raw = record.get(field)
        if isinstance(raw, str) and raw.strip().lower() == PROFIT_FACTOR_INFINITY_TOKEN:
            infinity_seen = True
            continue
        if isinstance(raw, str) and raw.strip().lower() == PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN:
            return PROFIT_FACTOR_NEGATIVE_INFINITY_TOKEN
        parsed = _as_float(raw)
        if parsed is not None:
            values.append(parsed)
    if infinity_seen:
        return PROFIT_FACTOR_INFINITY_TOKEN
    if not values:
        return None
    return float(median(values))


def positive_share(records: Sequence[Mapping[str, Any]], field: str) -> float | None:
    if not records:
        return None
    positives = 0
    observed = 0
    for record in records:
        if metric_is_missing(record, field):
            continue
        parsed = _as_float(record.get(field))
        if parsed is None:
            continue
        observed += 1
        if parsed > 0:
            positives += 1
    if observed == 0:
        return None
    return positives / observed


def max_of_field(records: Sequence[Mapping[str, Any]], field: str) -> float | None:
    values: list[float] = []
    for record in records:
        if metric_is_missing(record, field):
            continue
        parsed = _as_float(record.get(field))
        if parsed is not None:
            values.append(parsed)
    if not values:
        return None
    return max(values)


def sum_of_field(records: Sequence[Mapping[str, Any]], field: str) -> int | None:
    total = 0
    seen = False
    for record in records:
        parsed = _as_int(record.get(field))
        if parsed is None:
            continue
        seen = True
        total += parsed
    return total if seen else None


def gate_result(
    gate_id: str,
    *,
    passed: bool | None,
    observed: object,
    threshold: object = None,
    detail: str | None = None,
    skipped: bool = False,
    skip_flag: str | None = None,
) -> dict[str, Any]:
    status = "SKIP" if skipped else ("PASS" if passed else "FAIL")
    if passed is None and not skipped:
        status = "FAIL"
    payload: dict[str, Any] = {
        "gate_id": gate_id,
        "status": status,
        "passed": passed if not skipped else None,
        "observed": observed,
    }
    if threshold is not None:
        payload["threshold"] = threshold
    if detail:
        payload["detail"] = detail
    if skip_flag:
        payload["skip_flag"] = skip_flag
    return payload
