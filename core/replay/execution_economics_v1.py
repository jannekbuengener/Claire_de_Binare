"""Canonical Execution Economics Gross-to-Net contract v1 (#4150).

SSOT for:
  - scenario field names, units, ranges, and simulator mapping
  - research assumptions snapshot (order size, synthetic depth, fees, models)
  - gross-to-net reconciliation without double-counting embedded slippage

Physics remain in services.execution.simulator.ExecutionSimulator (read-only
from this module's perspective). This contract does not soften costs or
authorize live/paper runtime changes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping, Optional, Sequence

from core.replay.canonical_json import canonical_hash

CONTRACT_VERSION = "execution_economics_gross_to_net.v1"
CONTRACT_FORMULA = (
    "net_pnl = gross_pnl - total_fee_cost - spread_cost - slippage_cost"
    " - partial_fill_impact - reject_impact - latency_or_delay_impact"
    " - funding_cost_when_active"
)

# Money quantization (quote currency)
_MONEY_Q = Decimal("0.00000001")
_BPS_Q = Decimal("0.0001")

# Defaults mirror ExecutionSimulator / ARVP research hardcodes (synthetic).
DEFAULT_MAKER_FEE_RATE = Decimal("0.0002")
DEFAULT_TAKER_FEE_RATE = Decimal("0.0006")
DEFAULT_BASE_SLIPPAGE_BPS = Decimal("5")
DEFAULT_DEPTH_IMPACT_FACTOR = Decimal("0.10")
DEFAULT_VOL_SLIPPAGE_MULTIPLIER = Decimal("2.0")
DEFAULT_USABLE_DEPTH_FRACTION = Decimal("0.80")
DEFAULT_ORDER_SIZE = Decimal("1.0")
DEFAULT_ORDER_BOOK_DEPTH_MULTIPLIER = Decimal("10000")
DEFAULT_FUNDING_RATE = Decimal("0.0001")

MAX_SLIPPAGE_BPS = Decimal("10000")  # 100%
MAX_FEE_RATE = Decimal("0.05")
MAX_USABLE_DEPTH_FRACTION = Decimal("1.0")
MAX_DEPTH_IMPACT_FACTOR = Decimal("10.0")

COMPONENT_STATUS_ACTIVE = "active"
COMPONENT_STATUS_ZERO = "zero"
COMPONENT_STATUS_NOT_APPLICABLE = "not_applicable"
COMPONENT_STATUS_INACTIVE = "inactive_not_wired"
COMPONENT_STATUS_UNAVAILABLE = "unavailable"
COMPONENT_STATUS_EMBEDDED = "embedded_in_fill_price"

VALID_COMPONENT_STATUSES: frozenset[str] = frozenset(
    {
        COMPONENT_STATUS_ACTIVE,
        COMPONENT_STATUS_ZERO,
        COMPONENT_STATUS_NOT_APPLICABLE,
        COMPONENT_STATUS_INACTIVE,
        COMPONENT_STATUS_UNAVAILABLE,
        COMPONENT_STATUS_EMBEDDED,
    }
)

# Statuses whose amount MUST be null: the component carries no billable number.
NULL_AMOUNT_COMPONENT_STATUSES: frozenset[str] = frozenset(
    {
        COMPONENT_STATUS_NOT_APPLICABLE,
        COMPONENT_STATUS_INACTIVE,
        COMPONENT_STATUS_UNAVAILABLE,
    }
)

# Statuses that are never subtracted from gross (null amounts plus amounts that
# are already embedded in the fill price and would otherwise double-count).
NON_SUBTRACTED_COMPONENT_STATUSES: frozenset[str] = NULL_AMOUNT_COMPONENT_STATUSES | {
    COMPONENT_STATUS_EMBEDDED
}

ORDER_TYPE_MARKET = "market"
ORDER_TYPE_LIMIT = "limit"
VALID_ORDER_TYPES: frozenset[str] = frozenset({ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT})

FILL_STATUS_FILLED = "filled"
FILL_STATUS_PARTIALLY_FILLED = "partially_filled"
FILL_STATUS_NOT_FILLED = "not_filled"
VALID_FILL_STATUSES: frozenset[str] = frozenset(
    {FILL_STATUS_FILLED, FILL_STATUS_PARTIALLY_FILLED, FILL_STATUS_NOT_FILLED}
)

DEFAULT_FUNDING_SETTLEMENT_HOURS = Decimal("8")

# Funding rate provenance that is NOT admissible as an active, billable input.
# Activating funding on any of these would invent a venue cost (#4190).
UNPROVEN_FUNDING_RATE_SOURCES: frozenset[str] = frozenset(
    {
        "",
        "unknown",
        "assumed",
        "placeholder",
        "synthetic_default",
        "simulator_default",
    }
)
FUNDING_RATE_SOURCE_SYNTHETIC_DEFAULT = "synthetic_default"

# #4190 wire-or-retire verdict for the two surfaces inventoried by #4150.
# Replay datasets are OHLCV only; no funding-rate series and no per-position
# holding duration reach the active runner path, so funding stays unbillable.
FUNDING_INPUT_AVAILABILITY = "unavailable_no_funding_rate_series"
# services.execution.simulator.simulate_limit_order is parked: no runner calls
# it and its fill trigger bills a marketable (taker) limit as a maker fill.
LIMIT_ORDER_MODEL_STATUS = "parked_not_economics_billable"
REQUIRED_FUNDING_BASIS_KEYS: frozenset[str] = frozenset(
    {"position_value", "funding_rate", "funding_rate_source", "hours_held"}
)

# Scenario override key -> ExecutionSimulator config field
SCENARIO_OVERRIDE_KEY_TO_SIMULATOR: dict[str, str] = {
    "execution_slippage_bps": "BASE_SLIPPAGE_BPS",
    "usable_depth_fraction": "FILL_THRESHOLD",
    "depth_impact_factor": "DEPTH_IMPACT_FACTOR",
    "execution_delay_bars": "EXECUTION_DELAY_BARS",
}

LEGACY_SCENARIO_OVERRIDE_KEYS: dict[str, str] = {
    "fill_rate": "usable_depth_fraction",
    "fill_depth_factor": "depth_impact_factor",
}

ALLOWED_SCENARIO_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "pack_id",
        "pack_version",
        "execution_slippage_bps",
        "usable_depth_fraction",
        "depth_impact_factor",
        "execution_delay_bars",
        "feed_gap_bars",
        "execution_posture",
    }
)

UNSUPPORTED_SCENARIO_OVERRIDES: frozenset[str] = frozenset(
    {
        "feed_gap_seconds",
        "drop_ticks_on_gap",
    }
)

# Documented mock/paper comparison surface (read-only inventory of mock_executor).
MOCK_PAPER_ECONOMICS_ASSUMPTIONS: dict[str, Any] = {
    "producer": "services.execution.mock_executor.MockExecutor",
    "synthetic": True,
    "success_rate": 0.95,
    "latency_ms": {"min": 50, "max": 200, "distribution": "uniform_int"},
    "base_slippage_pct": 0.02,
    "slippage_cap_pct": 0.1,
    "fee_model": "none",
    "spread_model": "none",
    "price_model": "synthetic_symbol_base",
    "seed_source": "core.utils.seed.SeedManager",
    "reproducible_when": "identical SeedManager seed and identical call sequence",
    "venue_claim": "none",
}


class ExecutionEconomicsError(ValueError):
    """Raised when economics inputs violate the v1 contract."""


@dataclass(frozen=True, slots=True)
class ScenarioFieldSpec:
    """Machine-readable scenario field contract entry."""

    name: str
    unit: str
    default: Any
    value_range: tuple[Any, Any] | None
    simulator_field: str | None
    effect: str
    synthetic: bool = False


SCENARIO_FIELD_CATALOG: dict[str, ScenarioFieldSpec] = {
    "execution_slippage_bps": ScenarioFieldSpec(
        name="execution_slippage_bps",
        unit="bps",
        default=float(DEFAULT_BASE_SLIPPAGE_BPS),
        value_range=(0.0, float(MAX_SLIPPAGE_BPS)),
        simulator_field="BASE_SLIPPAGE_BPS",
        effect="Replaces BASE_SLIPPAGE_BPS; contributes to fill-price slippage.",
        synthetic=True,
    ),
    "usable_depth_fraction": ScenarioFieldSpec(
        name="usable_depth_fraction",
        unit="fraction",
        default=float(DEFAULT_USABLE_DEPTH_FRACTION),
        value_range=(0.0, float(MAX_USABLE_DEPTH_FRACTION)),
        simulator_field="FILL_THRESHOLD",
        effect=(
            "Fraction of order_book_depth usable for a single market fill "
            "(usable_depth = depth * fraction). Not a probabilistic fill rate."
        ),
        synthetic=True,
    ),
    "depth_impact_factor": ScenarioFieldSpec(
        name="depth_impact_factor",
        unit="coefficient",
        default=float(DEFAULT_DEPTH_IMPACT_FACTOR),
        value_range=(0.0, float(MAX_DEPTH_IMPACT_FACTOR)),
        simulator_field="DEPTH_IMPACT_FACTOR",
        effect=(
            "Depth-impact coefficient in slippage_bps = "
            "(notional/depth) * factor * 10000 (+ base + vol terms). "
            "Does not shrink book depth."
        ),
        synthetic=True,
    ),
    "execution_delay_bars": ScenarioFieldSpec(
        name="execution_delay_bars",
        unit="bars",
        default=0,
        value_range=(0, 10_000),
        simulator_field="EXECUTION_DELAY_BARS",
        effect=(
            "Bar-level delay: signal at index i executes at i+K when the runner "
            "implements EXECUTION_DELAY_BARS (primary_breakout path)."
        ),
        synthetic=False,
    ),
    "feed_gap_bars": ScenarioFieldSpec(
        name="feed_gap_bars",
        unit="bars",
        default=0,
        value_range=(0, 10_000),
        simulator_field=None,
        effect="Replay-data override: inject stale midpoint bars (volume=0).",
        synthetic=False,
    ),
    "execution_posture": ScenarioFieldSpec(
        name="execution_posture",
        unit="tag",
        default="baseline",
        value_range=None,
        simulator_field="_execution_posture",
        effect="Metadata tag only; no numeric simulator effect.",
        synthetic=False,
    ),
}


def _to_decimal(value: Any, *, field_name: str) -> Decimal:
    if value is None:
        raise ExecutionEconomicsError(f"{field_name} must not be None")
    if isinstance(value, bool):
        raise ExecutionEconomicsError(f"{field_name} must be numeric, not bool")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ExecutionEconomicsError(f"{field_name} must be finite (got {value!r})")
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ExecutionEconomicsError(
            f"{field_name} is not a valid decimal: {value!r}"
        ) from exc
    if not dec.is_finite():
        raise ExecutionEconomicsError(f"{field_name} must be finite (got {value!r})")
    return dec


def _q_money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP)


def _q_bps(value: Decimal) -> Decimal:
    return value.quantize(_BPS_Q, rounding=ROUND_HALF_UP)


def rate_to_bps(rate: Any) -> Decimal:
    """Convert a fractional rate (0.0001 = 1 bps) to basis points."""
    dec = _to_decimal(rate, field_name="rate")
    if dec < 0:
        raise ExecutionEconomicsError(
            "negative rates are not supported (rebates not enabled in v1)"
        )
    if dec > MAX_FEE_RATE:
        raise ExecutionEconomicsError(f"rate exceeds MAX_FEE_RATE={MAX_FEE_RATE}")
    return _q_bps(dec * Decimal("10000"))


def bps_to_rate(bps: Any) -> Decimal:
    """Convert basis points to a fractional rate."""
    dec = _to_decimal(bps, field_name="bps")
    if dec < 0:
        raise ExecutionEconomicsError(
            "negative bps are not supported (rebates not enabled in v1)"
        )
    if dec > MAX_SLIPPAGE_BPS:
        raise ExecutionEconomicsError(
            f"bps exceeds MAX_SLIPPAGE_BPS={MAX_SLIPPAGE_BPS}"
        )
    return (dec / Decimal("10000")).quantize(
        Decimal("0.0000000001"), rounding=ROUND_HALF_UP
    )


def validate_bps(bps: Any, *, field_name: str = "bps") -> Decimal:
    dec = _to_decimal(bps, field_name=field_name)
    if dec < 0:
        raise ExecutionEconomicsError(f"{field_name} must be >= 0 (got {dec})")
    if dec > MAX_SLIPPAGE_BPS:
        raise ExecutionEconomicsError(
            f"{field_name} must be <= {MAX_SLIPPAGE_BPS} (got {dec})"
        )
    return _q_bps(dec)


def validate_fraction(value: Any, *, field_name: str, maximum: Decimal) -> Decimal:
    dec = _to_decimal(value, field_name=field_name)
    if dec < 0:
        raise ExecutionEconomicsError(f"{field_name} must be >= 0 (got {dec})")
    if dec > maximum:
        raise ExecutionEconomicsError(f"{field_name} must be <= {maximum} (got {dec})")
    return dec


def resolve_scenario_overrides(overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve scenario overrides into simulator + replay-data surfaces.

    Fail-closed on unknown keys and legacy misleading names.
    """
    if not isinstance(overrides, Mapping):
        raise ExecutionEconomicsError("overrides must be a mapping")

    keys = set(overrides.keys())
    legacy_hits = keys & set(LEGACY_SCENARIO_OVERRIDE_KEYS)
    if legacy_hits:
        details = ", ".join(
            f"{old!r} -> use {LEGACY_SCENARIO_OVERRIDE_KEYS[old]!r}"
            for old in sorted(legacy_hits)
        )
        raise ExecutionEconomicsError(
            f"Legacy scenario override keys are rejected fail-closed: {details}"
        )

    unsupported = keys & UNSUPPORTED_SCENARIO_OVERRIDES
    if unsupported:
        raise ExecutionEconomicsError(
            f"Scenario override not currently supported: {sorted(unsupported)}. "
            f"Supported overrides: {sorted(ALLOWED_SCENARIO_OVERRIDE_KEYS)}. "
            f"`feed_gap_seconds` is not representable on the strict 1m replay canvas; "
            f"use explicit bar-level semantics instead."
        )

    unknown = keys - ALLOWED_SCENARIO_OVERRIDE_KEYS
    if unknown:
        raise ExecutionEconomicsError(
            f"Scenario overrides contain unknown keys: {sorted(unknown)}. "
            f"Supported overrides: {sorted(ALLOWED_SCENARIO_OVERRIDE_KEYS)}"
        )

    simulator_config: dict[str, Any] = {}
    replay_data_overrides: dict[str, Any] = {}

    for override_key, sim_field in SCENARIO_OVERRIDE_KEY_TO_SIMULATOR.items():
        if override_key not in overrides:
            continue
        value = overrides[override_key]
        if override_key == "execution_slippage_bps":
            value = float(validate_bps(value, field_name=override_key))
        elif override_key == "usable_depth_fraction":
            value = float(
                validate_fraction(
                    value,
                    field_name=override_key,
                    maximum=MAX_USABLE_DEPTH_FRACTION,
                )
            )
        elif override_key == "depth_impact_factor":
            value = float(
                validate_fraction(
                    value,
                    field_name=override_key,
                    maximum=MAX_DEPTH_IMPACT_FACTOR,
                )
            )
        elif override_key == "execution_delay_bars":
            delay = _to_decimal(value, field_name=override_key)
            if delay != delay.to_integral_value() or delay < 0:
                raise ExecutionEconomicsError(
                    f"{override_key} must be a non-negative integer"
                )
            value = int(delay)
        simulator_config[sim_field] = value

    if "feed_gap_bars" in overrides:
        gap = _to_decimal(overrides["feed_gap_bars"], field_name="feed_gap_bars")
        if gap != gap.to_integral_value() or gap < 0:
            raise ExecutionEconomicsError(
                "feed_gap_bars must be a non-negative integer"
            )
        replay_data_overrides["feed_gap_bars"] = int(gap)

    posture = overrides.get("execution_posture")
    if posture:
        if not isinstance(posture, str) or not posture.strip():
            raise ExecutionEconomicsError(
                "execution_posture must be a non-empty string"
            )
        simulator_config["_execution_posture"] = posture.strip()

    return {
        "simulator_config": simulator_config,
        "replay_data_overrides": replay_data_overrides,
    }


@dataclass(frozen=True, slots=True)
class CostComponent:
    """One gross-to-net cost line with explicit applicability status."""

    name: str
    amount: Optional[Decimal]
    status: str
    unit: str = "quote_currency"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "unit": self.unit,
        }
        if self.amount is not None:
            payload["amount"] = str(_q_money(self.amount))
        else:
            payload["amount"] = None
        if self.notes:
            payload["notes"] = self.notes
        return payload


@dataclass(frozen=True, slots=True)
class GrossToNetResult:
    """Reconciled gross-to-net economics evidence."""

    contract_version: str
    formula: str
    gross_pnl: Decimal
    fill_price_embedded_gross: Optional[Decimal]
    maker_fee_cost: CostComponent
    taker_fee_cost: CostComponent
    total_fee_cost: CostComponent
    spread_cost: CostComponent
    slippage_cost: CostComponent
    partial_fill_impact: CostComponent
    reject_impact: CostComponent
    latency_or_delay_impact: CostComponent
    funding_cost_when_active: CostComponent
    net_pnl: Decimal
    reconciled: bool
    residual: Decimal
    order_type: str = ORDER_TYPE_MARKET
    fill_status: str = FILL_STATUS_FILLED
    maker_fill_evidence: bool = False
    funding_basis: Optional[dict[str, Any]] = None
    reported_net_pnl: Optional[Decimal] = None
    assumptions_snapshot: dict[str, Any] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "formula": self.formula,
            "execution_semantics": {
                "order_type": self.order_type,
                "fill_status": self.fill_status,
                "maker_fill_evidence": self.maker_fill_evidence,
                "funding_basis": self.funding_basis,
            },
            "gross_pnl": str(_q_money(self.gross_pnl)),
            "fill_price_embedded_gross": (
                str(_q_money(self.fill_price_embedded_gross))
                if self.fill_price_embedded_gross is not None
                else None
            ),
            "components": {
                "maker_fee_cost": self.maker_fee_cost.to_dict(),
                "taker_fee_cost": self.taker_fee_cost.to_dict(),
                "total_fee_cost": self.total_fee_cost.to_dict(),
                "spread_cost": self.spread_cost.to_dict(),
                "slippage_cost": self.slippage_cost.to_dict(),
                "partial_fill_impact": self.partial_fill_impact.to_dict(),
                "reject_impact": self.reject_impact.to_dict(),
                "latency_or_delay_impact": self.latency_or_delay_impact.to_dict(),
                "funding_cost_when_active": self.funding_cost_when_active.to_dict(),
            },
            "net_pnl": str(_q_money(self.net_pnl)),
            "reported_net_pnl": (
                None
                if self.reported_net_pnl is None
                else str(_q_money(self.reported_net_pnl))
            ),
            "reconciled": self.reconciled,
            "residual": str(_q_money(self.residual)),
            "assumptions_snapshot": self.assumptions_snapshot,
            "limitations": list(self.limitations),
        }


def build_assumptions_snapshot(
    *,
    order_size: Any = DEFAULT_ORDER_SIZE,
    order_book_depth_multiplier: Any = DEFAULT_ORDER_BOOK_DEPTH_MULTIPLIER,
    maker_fee_rate: Any = DEFAULT_MAKER_FEE_RATE,
    taker_fee_rate: Any = DEFAULT_TAKER_FEE_RATE,
    base_slippage_bps: Any = DEFAULT_BASE_SLIPPAGE_BPS,
    depth_impact_factor: Any = DEFAULT_DEPTH_IMPACT_FACTOR,
    vol_slippage_multiplier: Any = DEFAULT_VOL_SLIPPAGE_MULTIPLIER,
    usable_depth_fraction: Any = DEFAULT_USABLE_DEPTH_FRACTION,
    funding_rate: Any = DEFAULT_FUNDING_RATE,
    funding_active: bool = False,
    funding_rate_source: str = FUNDING_RATE_SOURCE_SYNTHETIC_DEFAULT,
    limit_orders_active: bool = False,
    limit_order_fill_model: str | None = None,
    spread_model: str = "not_modeled",
    reject_model: str = "not_modeled_in_replay_market_path",
    latency_model: str = "bar_delay_when_runner_implements",
    extras: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Versioned research assumptions (synthetic where marked). No secrets.

    Activating funding or limit orders is fail-closed: the caller must name a
    non-synthetic funding rate source, respectively a limit-order fill model,
    otherwise the snapshot would advertise an active model that no proven input
    backs (#4190).
    """
    if funding_active and funding_rate_source.strip() in UNPROVEN_FUNDING_RATE_SOURCES:
        raise ExecutionEconomicsError(
            "funding_active=True requires a non-synthetic funding_rate_source; "
            f"got {funding_rate_source!r}. Replay datasets carry no funding-rate "
            "series, so funding must stay inactive_not_wired."
        )
    if limit_orders_active and not (limit_order_fill_model or "").strip():
        raise ExecutionEconomicsError(
            "limit_orders_active=True requires an explicit limit_order_fill_model; "
            "maker fills must never be assumed guaranteed."
        )
    snapshot: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "order_size": {
            "value": str(_to_decimal(order_size, field_name="order_size")),
            "unit": "base_quantity",
            "synthetic": True,
            "notes": "ARVP/Pack-A research default historically 1.0 BTC",
        },
        "book_depth": {
            "depth_multiplier": str(
                _to_decimal(
                    order_book_depth_multiplier,
                    field_name="order_book_depth_multiplier",
                )
            ),
            "formula": "max(volume * price * depth_multiplier, price)",
            "unit": "quote_depth",
            "synthetic": True,
            "notes": "Synthetic depth; not venue L2 evidence",
        },
        "fee_schedule": {
            "maker_fee_rate": str(
                _to_decimal(maker_fee_rate, field_name="maker_fee_rate")
            ),
            "taker_fee_rate": str(
                _to_decimal(taker_fee_rate, field_name="taker_fee_rate")
            ),
            "unit": "rate",
            "synthetic": True,
            "notes": "Defaults mirror ExecutionSimulator comments (MEXC 2024); unverified venue claim",
        },
        "spread_model": {
            "status": (
                COMPONENT_STATUS_INACTIVE
                if spread_model == "not_modeled"
                else COMPONENT_STATUS_ACTIVE
            ),
            "model": spread_model,
            "synthetic": True,
        },
        "slippage_model": {
            "base_slippage_bps": str(
                validate_bps(base_slippage_bps, field_name="base_slippage_bps")
            ),
            "depth_impact_factor": str(
                validate_fraction(
                    depth_impact_factor,
                    field_name="depth_impact_factor",
                    maximum=MAX_DEPTH_IMPACT_FACTOR,
                )
            ),
            "vol_slippage_multiplier": str(
                _to_decimal(
                    vol_slippage_multiplier, field_name="vol_slippage_multiplier"
                )
            ),
            "embedding": "slippage applied inside avg_fill_price; attributed separately for gross-to-net",
            "synthetic": True,
        },
        "fill_model": {
            "usable_depth_fraction": str(
                validate_fraction(
                    usable_depth_fraction,
                    field_name="usable_depth_fraction",
                    maximum=MAX_USABLE_DEPTH_FRACTION,
                )
            ),
            "order_type": "market",
            "synthetic": True,
        },
        "reject_model": {
            "status": COMPONENT_STATUS_INACTIVE,
            "model": reject_model,
            "notes": "Deterministic replay market path has no reject model",
        },
        "latency_model": {
            "model": latency_model,
            "unit": "bars_or_milliseconds",
            "notes": "Replay uses bar delay when implemented; mock uses seeded 50-200ms sleep",
        },
        "funding_model": {
            "status": (
                COMPONENT_STATUS_ACTIVE if funding_active else COMPONENT_STATUS_INACTIVE
            ),
            "funding_rate": str(_to_decimal(funding_rate, field_name="funding_rate")),
            "funding_rate_source": funding_rate_source,
            "period": "8h",
            "wired_into_replay_pnl": bool(funding_active),
            "input_availability": (
                "available" if funding_active else FUNDING_INPUT_AVAILABILITY
            ),
            "synthetic": not funding_active,
        },
        "limit_order_model": {
            "status": (
                COMPONENT_STATUS_ACTIVE
                if limit_orders_active
                else LIMIT_ORDER_MODEL_STATUS
            ),
            "fill_model": limit_order_fill_model,
            "wired_into_arvp_runners": bool(limit_orders_active),
            "notes": (
                "Limit-order fill model declared by caller"
                if limit_orders_active
                else (
                    "simulate_limit_order is parked: no ARVP/replay runner calls it "
                    "and its fill trigger bills a marketable (taker) limit as maker"
                )
            ),
        },
        "mock_paper_comparison": dict(MOCK_PAPER_ECONOMICS_ASSUMPTIONS),
    }
    if extras:
        for key, value in extras.items():
            if key in snapshot:
                raise ExecutionEconomicsError(
                    f"assumptions extras collide with {key!r}"
                )
            snapshot[key] = value
    snapshot["fingerprint"] = canonical_hash(snapshot)
    return snapshot


def _validate_component_status(name: str, status: str) -> str:
    if status not in VALID_COMPONENT_STATUSES:
        raise ExecutionEconomicsError(
            f"{name} status {status!r} is not a valid component status; "
            f"allowed: {sorted(VALID_COMPONENT_STATUSES)}"
        )
    return status


def _component(
    name: str,
    value: Any,
    status: str,
    *,
    notes: str = "",
) -> CostComponent:
    """Resolve one cost line, fail-closed on status/value contradictions.

    ``value is None`` means "not supplied". A supplied value under a
    null-amount status is rejected instead of being silently dropped.
    """
    _validate_component_status(name, status)
    if status in NULL_AMOUNT_COMPONENT_STATUSES:
        if value is not None:
            raise ExecutionEconomicsError(
                f"{name} must not carry a value when status={status!r} "
                f"(got {value!r}); a supplied cost would be silently dropped"
            )
        return CostComponent(name=name, amount=None, status=status, notes=notes)
    amount = Decimal("0") if value is None else _to_decimal(value, field_name=name)
    if amount < 0:
        raise ExecutionEconomicsError(
            f"{name} cost amount must be >= 0 (got {amount}); "
            "costs are unsigned; subtract from gross"
        )
    resolved_status = (
        COMPONENT_STATUS_ZERO
        if amount == 0 and status == COMPONENT_STATUS_ACTIVE
        else status
    )
    return CostComponent(
        name=name, amount=_q_money(amount), status=resolved_status, notes=notes
    )


def _billable_amount(component: CostComponent) -> Decimal:
    if component.status in NON_SUBTRACTED_COMPONENT_STATUSES:
        return Decimal("0")
    if component.amount is None:
        return Decimal("0")
    return component.amount


def funding_cost_from_rate(
    *,
    position_value: Any,
    funding_rate: Any,
    hours_held: Any,
    settlement_hours: Any = DEFAULT_FUNDING_SETTLEMENT_HOURS,
) -> Decimal:
    """Deterministic funding cost = position_value * rate * settlement periods.

    Decimal mirror of ``ExecutionSimulator.calculate_funding_fees`` for evidence
    use. Requires real inputs; it does not supply a default rate.
    """
    value = _to_decimal(position_value, field_name="position_value")
    if value < 0:
        raise ExecutionEconomicsError("position_value must be >= 0")
    rate = _to_decimal(funding_rate, field_name="funding_rate")
    if rate < 0:
        raise ExecutionEconomicsError(
            "negative funding rates (funding received) are not supported in v1; "
            "costs are unsigned"
        )
    hours = _to_decimal(hours_held, field_name="hours_held")
    if hours < 0:
        raise ExecutionEconomicsError("hours_held must be >= 0")
    settlement = _to_decimal(settlement_hours, field_name="settlement_hours")
    if settlement <= 0:
        raise ExecutionEconomicsError("settlement_hours must be > 0")
    return _q_money(value * rate * (hours / settlement))


def resolve_funding_basis(basis: Mapping[str, Any]) -> tuple[Decimal, dict[str, Any]]:
    """Validate a funding basis and derive its deterministic cost.

    Fail-closed: an active funding component needs notional, rate, holding
    duration and a named non-synthetic rate provenance (#4190).
    """
    if not isinstance(basis, Mapping):
        raise ExecutionEconomicsError("funding_basis must be a mapping")
    missing = sorted(REQUIRED_FUNDING_BASIS_KEYS - set(basis))
    if missing:
        raise ExecutionEconomicsError(
            f"funding_basis is missing required keys: {missing}"
        )
    source = str(basis["funding_rate_source"]).strip()
    if source in UNPROVEN_FUNDING_RATE_SOURCES:
        raise ExecutionEconomicsError(
            f"funding_rate_source {source!r} is not admissible as an active cost; "
            "funding must stay inactive_not_wired until a sourced rate series exists"
        )
    settlement = basis.get("settlement_hours", DEFAULT_FUNDING_SETTLEMENT_HOURS)
    cost = funding_cost_from_rate(
        position_value=basis["position_value"],
        funding_rate=basis["funding_rate"],
        hours_held=basis["hours_held"],
        settlement_hours=settlement,
    )
    resolved = {
        "position_value": str(
            _to_decimal(basis["position_value"], field_name="position_value")
        ),
        "funding_rate": str(
            _to_decimal(basis["funding_rate"], field_name="funding_rate")
        ),
        "funding_rate_source": source,
        "hours_held": str(_to_decimal(basis["hours_held"], field_name="hours_held")),
        "settlement_hours": str(_to_decimal(settlement, field_name="settlement_hours")),
        "derived_cost": str(cost),
    }
    return cost, resolved


def _validate_fill_semantics(
    *,
    fill_status: str,
    gross: Decimal,
    total_fee: CostComponent,
    slip: CostComponent,
    partial: CostComponent,
) -> None:
    """Keep fill, no-fill and partial-fill cases mutually unambiguous."""
    if fill_status == FILL_STATUS_NOT_FILLED:
        if gross != 0:
            raise ExecutionEconomicsError(
                f"fill_status='not_filled' requires gross_pnl == 0 (got {gross})"
            )
        for component in (total_fee, slip):
            if _billable_amount(component) != 0:
                raise ExecutionEconomicsError(
                    f"fill_status='not_filled' forbids a non-zero "
                    f"{component.name} (got {component.amount})"
                )
        return
    if fill_status == FILL_STATUS_PARTIALLY_FILLED:
        if partial.status in NULL_AMOUNT_COMPONENT_STATUSES:
            raise ExecutionEconomicsError(
                "fill_status='partially_filled' requires a billable "
                f"partial_fill_impact (got status={partial.status!r})"
            )
        return
    if _billable_amount(partial) != 0:
        raise ExecutionEconomicsError(
            "fill_status='filled' forbids a non-zero partial_fill_impact "
            f"(got {partial.amount}); use 'partially_filled' or 'not_filled'"
        )


def reconcile_gross_to_net(
    *,
    gross_pnl: Any,
    maker_fee_cost: Any | None = None,
    taker_fee_cost: Any | None = None,
    spread_cost: Any | None = None,
    spread_status: str = COMPONENT_STATUS_NOT_APPLICABLE,
    slippage_cost: Any | None = None,
    slippage_status: str = COMPONENT_STATUS_ACTIVE,
    partial_fill_impact: Any | None = None,
    partial_fill_status: str = COMPONENT_STATUS_ACTIVE,
    reject_impact: Any | None = None,
    reject_status: str = COMPONENT_STATUS_NOT_APPLICABLE,
    latency_or_delay_impact: Any | None = None,
    latency_status: str = COMPONENT_STATUS_NOT_APPLICABLE,
    funding_cost: Any | None = None,
    funding_status: str = COMPONENT_STATUS_INACTIVE,
    funding_basis: Mapping[str, Any] | None = None,
    order_type: str = ORDER_TYPE_MARKET,
    maker_fill_evidence: bool = False,
    fill_status: str = FILL_STATUS_FILLED,
    fill_price_embedded_gross: Any | None = None,
    reported_net_pnl: Any | None = None,
    assumptions_snapshot: Mapping[str, Any] | None = None,
    limitations: Sequence[str] | None = None,
    residual_tolerance: Any = "0.00000001",
) -> GrossToNetResult:
    """Reconcile gross -> costs -> net with fail-closed invariants.

    ``gross_pnl`` must be reference/mid PnL that does **not** already embed
    slippage that is also passed as ``slippage_cost``.

    Cost arguments use ``None`` for "not supplied". Supplying a value under a
    non-billable status raises instead of dropping the cost silently, and an
    active status without a proven input raises instead of inventing a value.
    """
    if order_type not in VALID_ORDER_TYPES:
        raise ExecutionEconomicsError(
            f"order_type {order_type!r} invalid; allowed: {sorted(VALID_ORDER_TYPES)}"
        )
    if fill_status not in VALID_FILL_STATUSES:
        raise ExecutionEconomicsError(
            f"fill_status {fill_status!r} invalid; allowed: {sorted(VALID_FILL_STATUSES)}"
        )
    if maker_fill_evidence and order_type != ORDER_TYPE_LIMIT:
        raise ExecutionEconomicsError(
            "maker_fill_evidence requires order_type='limit'; a market order is "
            "always a taker fill"
        )

    gross = _q_money(_to_decimal(gross_pnl, field_name="gross_pnl"))
    maker = _component(
        "maker_fee_cost",
        maker_fee_cost,
        COMPONENT_STATUS_ACTIVE,
        notes="Maker fees require a proven limit-order maker fill",
    )
    if _billable_amount(maker) > 0 and not (
        order_type == ORDER_TYPE_LIMIT and maker_fill_evidence
    ):
        raise ExecutionEconomicsError(
            "maker_fee_cost > 0 requires order_type='limit' and "
            "maker_fill_evidence=True; maker fills must not be assumed on the "
            "market-only replay path"
        )
    taker = _component(
        "taker_fee_cost",
        taker_fee_cost,
        COMPONENT_STATUS_ACTIVE,
    )
    total_fee_amount = _billable_amount(maker) + _billable_amount(taker)
    total_fee = _component(
        "total_fee_cost",
        total_fee_amount,
        COMPONENT_STATUS_ACTIVE,
        notes="maker_fee_cost + taker_fee_cost",
    )

    spread = _component(
        "spread_cost",
        spread_cost,
        spread_status,
        notes=(
            "Spread not modeled in ExecutionSimulator; not silently zeroed as measured"
        ),
    )
    slip = _component(
        "slippage_cost",
        slippage_cost,
        slippage_status,
        notes=(
            "Attributed from fill vs reference; do not subtract again from "
            "fill_price_embedded_gross"
        ),
    )
    partial = _component(
        "partial_fill_impact",
        partial_fill_impact,
        partial_fill_status,
        notes="Impact of unfilled quantity; filled quantity carries PnL",
    )
    reject = _component(
        "reject_impact",
        reject_impact,
        reject_status,
        notes="Replay market path has no reject model",
    )
    latency = _component(
        "latency_or_delay_impact",
        latency_or_delay_impact,
        latency_status,
        notes="Set active when delay-vs-baseline money impact is measured",
    )

    _validate_component_status("funding_cost_when_active", funding_status)
    resolved_funding_basis: dict[str, Any] | None = None
    if funding_status in NULL_AMOUNT_COMPONENT_STATUSES:
        if funding_basis is not None:
            raise ExecutionEconomicsError(
                f"funding_basis must not be supplied when funding_status="
                f"{funding_status!r}"
            )
        funding = _component(
            "funding_cost_when_active",
            funding_cost,
            funding_status,
            notes=(
                "Funding API exists on the simulator but no funding-rate series "
                "reaches the active replay/paper path (#4190)"
            ),
        )
    else:
        if funding_basis is None:
            raise ExecutionEconomicsError(
                "an active funding_status requires funding_basis "
                f"({sorted(REQUIRED_FUNDING_BASIS_KEYS)}); a bare funding_cost "
                "would be an invented venue cost"
            )
        derived, resolved_funding_basis = resolve_funding_basis(funding_basis)
        if funding_cost is not None:
            supplied = _q_money(_to_decimal(funding_cost, field_name="funding_cost"))
            if supplied != derived:
                raise ExecutionEconomicsError(
                    f"funding_cost {supplied} does not reconcile with the funding "
                    f"basis ({derived}); funding must be derived deterministically"
                )
        funding = _component(
            "funding_cost_when_active",
            derived,
            funding_status,
            notes="Derived from funding_basis: position_value * rate * periods",
        )

    _validate_fill_semantics(
        fill_status=fill_status,
        gross=gross,
        total_fee=total_fee,
        slip=slip,
        partial=partial,
    )

    total_costs = (
        _billable_amount(total_fee)
        + _billable_amount(spread)
        + _billable_amount(slip)
        + _billable_amount(partial)
        + _billable_amount(reject)
        + _billable_amount(latency)
        + _billable_amount(funding)
    )
    net = _q_money(gross - total_costs)
    tolerance = _to_decimal(residual_tolerance, field_name="residual_tolerance")
    if tolerance < 0:
        raise ExecutionEconomicsError("residual_tolerance must be >= 0")
    if reported_net_pnl is None:
        residual = _q_money(Decimal("0"))
    else:
        residual = _q_money(
            _to_decimal(reported_net_pnl, field_name="reported_net_pnl") - net
        )
    reconciled = abs(residual) <= tolerance

    embedded: Optional[Decimal] = None
    if fill_price_embedded_gross is not None:
        embedded = _q_money(
            _to_decimal(
                fill_price_embedded_gross, field_name="fill_price_embedded_gross"
            )
        )

    snap = (
        dict(assumptions_snapshot)
        if assumptions_snapshot
        else build_assumptions_snapshot()
    )
    lims = tuple(
        limitations
        or (
            "Synthetic research assumptions; not venue-verified.",
            "Spread model inactive; component marked not_applicable.",
            "Funding and limit-order models inactive_not_wired.",
            "Does not prove profitability, live readiness, or venue realism.",
        )
    )

    return GrossToNetResult(
        contract_version=CONTRACT_VERSION,
        formula=CONTRACT_FORMULA,
        gross_pnl=gross,
        fill_price_embedded_gross=embedded,
        maker_fee_cost=maker,
        taker_fee_cost=taker,
        total_fee_cost=total_fee,
        spread_cost=spread,
        slippage_cost=slip,
        partial_fill_impact=partial,
        reject_impact=reject,
        latency_or_delay_impact=latency,
        funding_cost_when_active=funding,
        net_pnl=net,
        reconciled=reconciled,
        residual=residual,
        order_type=order_type,
        fill_status=fill_status,
        maker_fill_evidence=maker_fill_evidence,
        funding_basis=resolved_funding_basis,
        reported_net_pnl=(
            None
            if reported_net_pnl is None
            else _q_money(_to_decimal(reported_net_pnl, field_name="reported_net_pnl"))
        ),
        assumptions_snapshot=snap,
        limitations=lims,
    )


def slippage_cost_from_bps(*, notional: Any, slippage_bps: Any) -> Decimal:
    """Convert slippage bps on notional into quote cost (>= 0)."""
    notion = _to_decimal(notional, field_name="notional")
    if notion < 0:
        raise ExecutionEconomicsError("notional must be >= 0")
    bps = validate_bps(slippage_bps, field_name="slippage_bps")
    return _q_money(notion * bps / Decimal("10000"))


def reference_gross_pnl(
    *,
    side: str,
    filled_size: Any,
    entry_reference_price: Any,
    exit_reference_price: Any,
) -> Decimal:
    """Gross PnL on filled size using reference/mid prices (no slippage)."""
    size = _to_decimal(filled_size, field_name="filled_size")
    if size < 0:
        raise ExecutionEconomicsError("filled_size must be >= 0")
    entry = _to_decimal(entry_reference_price, field_name="entry_reference_price")
    exit_ = _to_decimal(exit_reference_price, field_name="exit_reference_price")
    side_l = side.lower().strip()
    if side_l in {"buy", "long"}:
        return _q_money((exit_ - entry) * size)
    if side_l in {"sell", "short"}:
        return _q_money((entry - exit_) * size)
    raise ExecutionEconomicsError(f"unsupported side: {side!r}")


def fill_price_embedded_gross_pnl(
    *,
    side: str,
    filled_size: Any,
    entry_fill_price: Any,
    exit_fill_price: Any,
) -> Decimal:
    """Legacy fill-price PnL that already embeds slippage in prices."""
    return reference_gross_pnl(
        side=side,
        filled_size=filled_size,
        entry_reference_price=entry_fill_price,
        exit_reference_price=exit_fill_price,
    )


def partial_fill_impact_quote(
    *,
    requested_size: Any,
    filled_size: Any,
    reference_pnl_per_unit: Any,
) -> Decimal:
    """Forgone absolute PnL on unfilled size using reference per-unit PnL."""
    requested = _to_decimal(requested_size, field_name="requested_size")
    filled = _to_decimal(filled_size, field_name="filled_size")
    if requested < 0 or filled < 0:
        raise ExecutionEconomicsError("sizes must be >= 0")
    if filled > requested:
        raise ExecutionEconomicsError("filled_size cannot exceed requested_size")
    per_unit = _to_decimal(reference_pnl_per_unit, field_name="reference_pnl_per_unit")
    unfilled = requested - filled
    # Cost impact is the forgone positive PnL; negative forgone PnL is zero cost
    # (avoid inventing beneficial rejects).
    forgone = per_unit * unfilled
    if forgone <= 0:
        return _q_money(Decimal("0"))
    return _q_money(forgone)


def compare_economics_components(
    replay: Mapping[str, Any],
    paper: Mapping[str, Any],
) -> dict[str, Any]:
    """Component-wise replay-vs-paper economics diff (research comparison).

    Inputs are GrossToNetResult.to_dict()-like mappings or flat component maps
    with numeric/string amounts under components.*.amount.
    """
    if not isinstance(replay, Mapping) or not isinstance(paper, Mapping):
        raise ExecutionEconomicsError("replay and paper must be mappings")

    def _amounts(payload: Mapping[str, Any]) -> dict[str, Optional[Decimal]]:
        components = payload.get("components")
        if isinstance(components, Mapping):
            out: dict[str, Optional[Decimal]] = {}
            for name, body in components.items():
                if not isinstance(body, Mapping):
                    continue
                status = str(body.get("status") or "")
                if status in NON_SUBTRACTED_COMPONENT_STATUSES:
                    out[str(name)] = None
                    continue
                amount = body.get("amount")
                out[str(name)] = (
                    None
                    if amount is None
                    else _to_decimal(amount, field_name=f"{name}.amount")
                )
            return out
        # Flat fallback: {component: amount}
        return {
            str(k): (None if v is None else _to_decimal(v, field_name=str(k)))
            for k, v in payload.items()
            if k
            in {
                "maker_fee_cost",
                "taker_fee_cost",
                "total_fee_cost",
                "spread_cost",
                "slippage_cost",
                "partial_fill_impact",
                "reject_impact",
                "latency_or_delay_impact",
                "funding_cost_when_active",
                "gross_pnl",
                "net_pnl",
            }
        }

    replay_amt = _amounts(replay)
    paper_amt = _amounts(paper)
    names = sorted(set(replay_amt) | set(paper_amt))
    diffs: dict[str, Any] = {}
    for name in names:
        r = replay_amt.get(name)
        p = paper_amt.get(name)
        if r is None and p is None:
            diffs[name] = {
                "replay": None,
                "paper": None,
                "delta": None,
                "status": "both_not_applicable_or_missing",
            }
            continue
        if r is None or p is None:
            diffs[name] = {
                "replay": None if r is None else str(_q_money(r)),
                "paper": None if p is None else str(_q_money(p)),
                "delta": None,
                "status": "incomparable",
            }
            continue
        delta = _q_money(r - p)
        diffs[name] = {
            "replay": str(_q_money(r)),
            "paper": str(_q_money(p)),
            "delta": str(delta),
            "status": "compared",
        }

    payload = {
        "contract_version": CONTRACT_VERSION,
        "component_diffs": diffs,
        "mock_paper_assumptions": dict(MOCK_PAPER_ECONOMICS_ASSUMPTIONS),
        "notes": [
            "Deltas are replay - paper in quote currency where both sides active.",
            "Synthetic mock prices/fees/latency must not be read as venue proof.",
        ],
    }
    payload["fingerprint"] = canonical_hash(payload)
    return payload


def economics_evidence_fingerprint(payload: Mapping[str, Any]) -> str:
    """Deterministic fingerprint for economics evidence payloads."""
    return canonical_hash(dict(payload))


def scenario_field_catalog_dict() -> dict[str, Any]:
    """Serialize field catalog for docs/evidence."""
    out: dict[str, Any] = {}
    for name, spec in SCENARIO_FIELD_CATALOG.items():
        out[name] = {
            "name": spec.name,
            "unit": spec.unit,
            "default": spec.default,
            "value_range": (
                list(spec.value_range) if spec.value_range is not None else None
            ),
            "simulator_field": spec.simulator_field,
            "effect": spec.effect,
            "synthetic": spec.synthetic,
        }
    return out
