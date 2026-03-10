"""Deterministic Decision Contract 0/1 v1.

This module provides:
- canonical input normalization
- pure deterministic evaluation
- canonical JSON + SHA256 evidence hashing
- bundle verification for execution-time enforcement

The evaluator is IO-free and side-effect free.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Mapping

CONTRACT_NAME = "decision_contract_v1"
CONTRACT_VERSION = "v1"

ALLOWED_RUN_MODES = {"shadow", "paper", "replay", "live"}
ALLOWED_ORDER_SIDES = {"BUY", "SELL"}

_MONEY_Q = Decimal("0.00000001")
_RATIO_Q = Decimal("0.000001")
_QTY_Q = Decimal("0.00000001")


class DecisionContractError(ValueError):
    """Raised when a Decision Contract payload is invalid/unusable."""


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _to_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise DecisionContractError(
            f"{field} must be numeric, got {type(value).__name__}"
        )
    if isinstance(value, float):
        raise DecisionContractError(
            f"{field} must not be float (determinism rule). Use string/Decimal."
        )
    if isinstance(value, Decimal):
        raw = value
    elif isinstance(value, (int, str)):
        text = str(value).strip()
        if text == "":
            raise DecisionContractError(f"{field} must not be empty")
        try:
            raw = Decimal(text)
        except InvalidOperation as exc:
            raise DecisionContractError(
                f"{field} is not a valid decimal: {value!r}"
            ) from exc
    else:
        raise DecisionContractError(
            f"{field} has unsupported type {type(value).__name__}"
        )

    if not raw.is_finite():
        raise DecisionContractError(f"{field} must be finite")
    return raw


def _q_str(value: Decimal, *, quantum: Decimal) -> str:
    quantized = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if quantized == Decimal("-0").quantize(quantum):
        quantized = Decimal("0").quantize(quantum)
    return format(quantized, "f")


def _to_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise DecisionContractError(f"{field} must be int, got {type(value).__name__}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            raise DecisionContractError(f"{field} must not be empty")
        if text.startswith(("+", "-")):
            sign = text[0]
            digits = text[1:]
            if not digits.isdigit():
                raise DecisionContractError(f"{field} must be int-like, got {value!r}")
            return int(sign + digits)
        if text.isdigit():
            return int(text)
    raise DecisionContractError(f"{field} must be int-like, got {value!r}")


def _clean_string(value: Any, *, field: str, uppercase: bool = False) -> str:
    if value is None:
        raise DecisionContractError(f"{field} is required")
    text = str(value).strip()
    if text == "":
        raise DecisionContractError(f"{field} must not be empty")
    return text.upper() if uppercase else text


def _normalize_open_positions(raw_positions: Any) -> list[dict[str, str]]:
    if raw_positions is None:
        return []

    normalized: list[dict[str, str]] = []
    if isinstance(raw_positions, Mapping):
        for symbol, qty in raw_positions.items():
            symbol_text = _clean_string(symbol, field="open_positions.symbol")
            qty_dec = _to_decimal(qty, field=f"open_positions.{symbol_text}.quantity")
            normalized.append(
                {
                    "symbol": symbol_text,
                    "quantity": _q_str(qty_dec, quantum=_QTY_Q),
                }
            )
    elif isinstance(raw_positions, list):
        for idx, entry in enumerate(raw_positions):
            if not isinstance(entry, Mapping):
                raise DecisionContractError(
                    f"open_positions[{idx}] must be object, got {type(entry).__name__}"
                )
            symbol_text = _clean_string(
                entry.get("symbol"), field=f"open_positions[{idx}].symbol"
            )
            qty_dec = _to_decimal(
                entry.get("quantity"), field=f"open_positions[{idx}].quantity"
            )
            normalized.append(
                {
                    "symbol": symbol_text,
                    "quantity": _q_str(qty_dec, quantum=_QTY_Q),
                }
            )
    else:
        raise DecisionContractError(
            f"open_positions must be mapping or list, got {type(raw_positions).__name__}"
        )

    normalized.sort(key=lambda item: item["symbol"])
    return normalized


def _normalize_system_config(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise DecisionContractError(
            f"system_config must be object, got {type(raw).__name__}"
        )

    normalized: dict[str, Any] = {}
    for key in sorted(raw.keys()):
        value = raw[key]
        if isinstance(value, (str, bool, int)) or value is None:
            normalized[str(key)] = value
            continue
        if isinstance(value, Decimal):
            normalized[str(key)] = _q_str(value, quantum=_MONEY_Q)
            continue
        if isinstance(value, float):
            raise DecisionContractError(
                f"system_config.{key} must not be float (determinism rule)"
            )
        normalized[str(key)] = str(value)
    return normalized


def normalize_decision_contract_input(raw_input: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize raw input into canonical v1 structure.

    Fail-closed: raises DecisionContractError for malformed payloads.
    """
    if not isinstance(raw_input, Mapping):
        raise DecisionContractError(
            f"contract input must be object, got {type(raw_input).__name__}"
        )

    order = raw_input.get("order")
    account_state = raw_input.get("account_state")
    risk_policy = raw_input.get("risk_policy")
    context = raw_input.get("context") or {}

    if not isinstance(order, Mapping):
        raise DecisionContractError("order object is required")
    if not isinstance(account_state, Mapping):
        raise DecisionContractError("account_state object is required")
    if not isinstance(risk_policy, Mapping):
        raise DecisionContractError("risk_policy object is required")
    if not isinstance(context, Mapping):
        raise DecisionContractError("context must be object when provided")

    run_mode = _clean_string(raw_input.get("run_mode"), field="run_mode").lower()
    side = _clean_string(order.get("side"), field="order.side", uppercase=True)

    normalized_input = {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "run_mode": run_mode,
        "order": {
            "symbol": _clean_string(order.get("symbol"), field="order.symbol"),
            "side": side,
            "quantity": _q_str(
                _to_decimal(order.get("quantity"), field="order.quantity"),
                quantum=_QTY_Q,
            ),
            "price_ref": _q_str(
                _to_decimal(order.get("price_ref"), field="order.price_ref"),
                quantum=_MONEY_Q,
            ),
            "timestamp_input_ms": _to_int(
                order.get("timestamp_input_ms"), field="order.timestamp_input_ms"
            ),
            "reduce_only": bool(order.get("reduce_only", False)),
        },
        "account_state": {
            "balance_usdt": _q_str(
                _to_decimal(
                    account_state.get("balance_usdt"),
                    field="account_state.balance_usdt",
                ),
                quantum=_MONEY_Q,
            ),
            "total_exposure_usdt": _q_str(
                _to_decimal(
                    account_state.get("total_exposure_usdt"),
                    field="account_state.total_exposure_usdt",
                ),
                quantum=_MONEY_Q,
            ),
            "daily_drawdown_pct": _q_str(
                _to_decimal(
                    account_state.get("daily_drawdown_pct"),
                    field="account_state.daily_drawdown_pct",
                ),
                quantum=_RATIO_Q,
            ),
        },
        "open_positions": _normalize_open_positions(raw_input.get("open_positions")),
        "risk_policy": {
            "max_notional_usdt": _q_str(
                _to_decimal(
                    risk_policy.get("max_notional_usdt"),
                    field="risk_policy.max_notional_usdt",
                ),
                quantum=_MONEY_Q,
            ),
            "max_total_exposure_usdt": _q_str(
                _to_decimal(
                    risk_policy.get("max_total_exposure_usdt"),
                    field="risk_policy.max_total_exposure_usdt",
                ),
                quantum=_MONEY_Q,
            ),
            "max_daily_drawdown_pct": _q_str(
                _to_decimal(
                    risk_policy.get("max_daily_drawdown_pct"),
                    field="risk_policy.max_daily_drawdown_pct",
                ),
                quantum=_RATIO_Q,
            ),
        },
        "system_config": _normalize_system_config(raw_input.get("system_config")),
        "context": {
            "source": str(context.get("source", "unspecified")),
            "signal_id": str(context.get("signal_id", "")),
            "strategy_id": str(context.get("strategy_id", "")),
            "bot_id": str(context.get("bot_id", "")),
        },
    }

    return normalized_input


def _evaluate_normalized_input(normalized_input: Mapping[str, Any]) -> dict[str, Any]:
    run_mode = str(normalized_input["run_mode"]).lower()

    order = normalized_input["order"]
    account_state = normalized_input["account_state"]
    risk_policy = normalized_input["risk_policy"]

    side = str(order["side"]).upper()
    reduce_only = bool(order["reduce_only"])

    quantity = Decimal(str(order["quantity"]))
    price_ref = Decimal(str(order["price_ref"]))
    balance = Decimal(str(account_state["balance_usdt"]))
    current_exposure = Decimal(str(account_state["total_exposure_usdt"]))
    daily_drawdown = Decimal(str(account_state["daily_drawdown_pct"]))

    max_notional = Decimal(str(risk_policy["max_notional_usdt"]))
    max_total_exposure = Decimal(str(risk_policy["max_total_exposure_usdt"]))
    max_daily_drawdown = Decimal(str(risk_policy["max_daily_drawdown_pct"]))

    reason_codes: set[str] = set()

    if run_mode not in ALLOWED_RUN_MODES:
        reason_codes.add("RC_INVALID_RUN_MODE")
    if side not in ALLOWED_ORDER_SIDES:
        reason_codes.add("RC_INVALID_ORDER_SIDE")

    if quantity <= Decimal("0"):
        reason_codes.add("RC_NON_POSITIVE_QTY")
    if price_ref <= Decimal("0"):
        reason_codes.add("RC_NON_POSITIVE_PRICE")
    if balance < Decimal("0"):
        reason_codes.add("RC_NEGATIVE_BALANCE")
    if current_exposure < Decimal("0"):
        reason_codes.add("RC_NEGATIVE_EXPOSURE")
    if daily_drawdown < Decimal("0"):
        reason_codes.add("RC_NEGATIVE_DRAWDOWN")

    if max_notional <= Decimal("0"):
        reason_codes.add("RC_INVALID_LIMIT_MAX_NOTIONAL")
    if max_total_exposure <= Decimal("0"):
        reason_codes.add("RC_INVALID_LIMIT_MAX_EXPOSURE")
    if max_daily_drawdown <= Decimal("0"):
        reason_codes.add("RC_INVALID_LIMIT_MAX_DRAWDOWN")

    order_notional = quantity * price_ref

    is_reduce_only_sell = side == "SELL" and reduce_only

    if side == "BUY" and not reduce_only:
        projected_exposure = current_exposure + order_notional
    else:
        projected_exposure = current_exposure - order_notional
        if projected_exposure < Decimal("0"):
            projected_exposure = Decimal("0")

    if (
        not is_reduce_only_sell
        and max_notional > Decimal("0")
        and order_notional > max_notional
    ):
        reason_codes.add("RC_LIMIT_NOTIONAL")
    if (
        not is_reduce_only_sell
        and max_total_exposure > Decimal("0")
        and projected_exposure > max_total_exposure
    ):
        reason_codes.add("RC_LIMIT_EXPOSURE")
    if max_daily_drawdown > Decimal("0") and daily_drawdown > max_daily_drawdown:
        reason_codes.add("RC_LIMIT_DRAWDOWN")

    reason_codes_sorted = sorted(reason_codes)
    decision = 0 if reason_codes_sorted else 1

    applied_limits = {
        "max_notional_usdt": _q_str(max_notional, quantum=_MONEY_Q),
        "max_total_exposure_usdt": _q_str(max_total_exposure, quantum=_MONEY_Q),
        "max_daily_drawdown_pct": _q_str(max_daily_drawdown, quantum=_RATIO_Q),
    }

    metrics = {
        "order_notional_usdt": _q_str(order_notional, quantum=_MONEY_Q),
        "projected_exposure_usdt": _q_str(projected_exposure, quantum=_MONEY_Q),
        "current_exposure_usdt": _q_str(current_exposure, quantum=_MONEY_Q),
        "daily_drawdown_pct": _q_str(daily_drawdown, quantum=_RATIO_Q),
        "balance_usdt": _q_str(balance, quantum=_MONEY_Q),
    }

    canonical_input = _canonical_json(normalized_input)
    input_hash = _sha256_hex(canonical_input)

    output_for_hash = {
        "contract_version": CONTRACT_VERSION,
        "decision": decision,
        "reason_codes": reason_codes_sorted,
        "applied_limits": applied_limits,
        "metrics": metrics,
        "input_hash": input_hash,
    }
    canonical_output = _canonical_json(output_for_hash)
    decision_hash = _sha256_hex(canonical_output)

    return {
        "contract_version": CONTRACT_VERSION,
        "decision": decision,
        "reason_codes": reason_codes_sorted,
        "applied_limits": applied_limits,
        "metrics": metrics,
        "evidence": {
            "canonical_input": canonical_input,
            "input_hash": input_hash,
            "canonical_output": canonical_output,
            "decision_hash": decision_hash,
        },
    }


def evaluate_decision_contract_v1(raw_input: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate Decision Contract v1 for a raw input payload."""
    normalized_input = normalize_decision_contract_input(raw_input)
    return _evaluate_normalized_input(normalized_input)


def build_decision_contract_v1_bundle(raw_input: Mapping[str, Any]) -> dict[str, Any]:
    """Build canonical bundle with normalized input and evaluated output."""
    normalized_input = normalize_decision_contract_input(raw_input)
    output = _evaluate_normalized_input(normalized_input)
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "input": normalized_input,
        "output": output,
    }


def verify_decision_contract_v1_bundle(
    bundle: Mapping[str, Any], *, require_allow: bool = False
) -> tuple[bool, str]:
    """Verify a Decision Contract v1 bundle.

    Returns:
        (True, "OK") when bundle is valid and deterministic.
        (False, "<reason>") otherwise.
    """
    try:
        if not isinstance(bundle, Mapping):
            return False, "bundle must be object"
        if bundle.get("contract_name") != CONTRACT_NAME:
            return False, "unsupported contract_name"
        if bundle.get("contract_version") != CONTRACT_VERSION:
            return False, "unsupported contract_version"

        input_payload = bundle.get("input")
        provided_output = bundle.get("output")
        if not isinstance(input_payload, Mapping):
            return False, "missing input payload"
        if not isinstance(provided_output, Mapping):
            return False, "missing output payload"

        normalized_input = normalize_decision_contract_input(input_payload)
        expected_output = _evaluate_normalized_input(normalized_input)

        if _canonical_json(provided_output) != _canonical_json(expected_output):
            return False, "output does not match deterministic evaluation"

        if require_allow and int(expected_output["decision"]) != 1:
            return False, "decision contract denied execution"

        return True, "OK"
    except DecisionContractError as exc:
        return False, f"invalid decision contract input: {exc}"
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return False, f"verification error: {exc}"


def build_decision_contract_audit_record(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Build canonical audit record from a verified decision contract bundle."""
    ok, reason = verify_decision_contract_v1_bundle(bundle, require_allow=False)
    if not ok:
        raise DecisionContractError(f"audit record build failed: {reason}")

    output = bundle["output"]
    evidence = output["evidence"]

    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "input": bundle["input"],
        "output": output,
        "input_hash": evidence["input_hash"],
        "decision_hash": evidence["decision_hash"],
    }


def write_decision_contract_audit_record(
    bundle: Mapping[str, Any], *, output_dir: str | Path = "reports/decision_contract"
) -> Path:
    """Write canonical audit JSON for one decision bundle.

    The filename is deterministic and derived from decision_hash.
    """
    record = build_decision_contract_audit_record(bundle)
    decision_hash = str(record["decision_hash"])
    if len(decision_hash) < 12:
        raise DecisionContractError("decision_hash too short for audit filename")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{decision_hash}.json"
    out_path.write_text(_canonical_json(record) + "\n", encoding="utf-8")
    return out_path


def decision_contract_v1_schema() -> dict[str, Any]:
    """Return JSON Schema for Decision Contract v1 bundle."""
    decimal_pattern = r"^-?\d+(\.\d+)?$"
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Decision Contract v1 Bundle",
        "type": "object",
        "additionalProperties": False,
        "required": ["contract_name", "contract_version", "input", "output"],
        "properties": {
            "contract_name": {"const": CONTRACT_NAME},
            "contract_version": {"const": CONTRACT_VERSION},
            "input": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "contract_name",
                    "contract_version",
                    "run_mode",
                    "order",
                    "account_state",
                    "open_positions",
                    "risk_policy",
                    "system_config",
                    "context",
                ],
                "properties": {
                    "contract_name": {"const": CONTRACT_NAME},
                    "contract_version": {"const": CONTRACT_VERSION},
                    "run_mode": {"enum": sorted(ALLOWED_RUN_MODES)},
                    "order": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "symbol",
                            "side",
                            "quantity",
                            "price_ref",
                            "timestamp_input_ms",
                            "reduce_only",
                        ],
                        "properties": {
                            "symbol": {"type": "string", "minLength": 1},
                            "side": {"enum": sorted(ALLOWED_ORDER_SIDES)},
                            "quantity": {"type": "string", "pattern": decimal_pattern},
                            "price_ref": {"type": "string", "pattern": decimal_pattern},
                            "timestamp_input_ms": {"type": "integer"},
                            "reduce_only": {"type": "boolean"},
                        },
                    },
                    "account_state": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "balance_usdt",
                            "total_exposure_usdt",
                            "daily_drawdown_pct",
                        ],
                        "properties": {
                            "balance_usdt": {
                                "type": "string",
                                "pattern": decimal_pattern,
                            },
                            "total_exposure_usdt": {
                                "type": "string",
                                "pattern": decimal_pattern,
                            },
                            "daily_drawdown_pct": {
                                "type": "string",
                                "pattern": decimal_pattern,
                            },
                        },
                    },
                    "open_positions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["symbol", "quantity"],
                            "properties": {
                                "symbol": {"type": "string", "minLength": 1},
                                "quantity": {
                                    "type": "string",
                                    "pattern": decimal_pattern,
                                },
                            },
                        },
                    },
                    "risk_policy": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "max_notional_usdt",
                            "max_total_exposure_usdt",
                            "max_daily_drawdown_pct",
                        ],
                        "properties": {
                            "max_notional_usdt": {
                                "type": "string",
                                "pattern": decimal_pattern,
                            },
                            "max_total_exposure_usdt": {
                                "type": "string",
                                "pattern": decimal_pattern,
                            },
                            "max_daily_drawdown_pct": {
                                "type": "string",
                                "pattern": decimal_pattern,
                            },
                        },
                    },
                    "system_config": {"type": "object"},
                    "context": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["source", "signal_id", "strategy_id", "bot_id"],
                        "properties": {
                            "source": {"type": "string"},
                            "signal_id": {"type": "string"},
                            "strategy_id": {"type": "string"},
                            "bot_id": {"type": "string"},
                        },
                    },
                },
            },
            "output": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "contract_version",
                    "decision",
                    "reason_codes",
                    "applied_limits",
                    "metrics",
                    "evidence",
                ],
                "properties": {
                    "contract_version": {"const": CONTRACT_VERSION},
                    "decision": {"enum": [0, 1]},
                    "reason_codes": {"type": "array", "items": {"type": "string"}},
                    "applied_limits": {"type": "object"},
                    "metrics": {"type": "object"},
                    "evidence": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "canonical_input",
                            "input_hash",
                            "canonical_output",
                            "decision_hash",
                        ],
                        "properties": {
                            "canonical_input": {"type": "string"},
                            "input_hash": {
                                "type": "string",
                                "pattern": "^[a-f0-9]{64}$",
                            },
                            "canonical_output": {"type": "string"},
                            "decision_hash": {
                                "type": "string",
                                "pattern": "^[a-f0-9]{64}$",
                            },
                        },
                    },
                },
            },
        },
    }
