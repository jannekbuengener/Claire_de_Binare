"""Risk engine helpers for signal evaluation.

The functions in this module are intentionally stateless and dependency-free so
they can be exercised in unit tests without external services. They provide a
minimal scaffold for sizing, stop-loss placement, and basic exposure guards.
Extend or replace them with production-grade logic once portfolio connectivity
is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RiskDecision:
    """Result of evaluating a trading signal.

    Attributes:
        approved: Whether the signal is allowed to proceed.
        reason: Optional rejection code for downstream logging.
        position_size: Final approved size (in units of the symbol).
        stop_price: Optional stop-loss price accompanying the decision.
    """

    approved: bool
    reason: Optional[str]
    position_size: float
    stop_price: Optional[float]


def _resolve_equity(state: Dict[str, float], config: Dict[str, float]) -> float:
    """Return the equity baseline used for percentage-based checks.

    Falls back to ``ACCOUNT_EQUITY`` from the risk configuration if no explicit
    value is stored on the state. The default prevents divide-by-zero errors in
    early scaffolding phases.
    """

    return float(state.get("equity") or config.get("ACCOUNT_EQUITY", 1.0))


def limit_position_size(
    signal_event: Dict[str, float],
    risk_config: Dict[str, float],
    equity: Optional[float] = None,
) -> float:
    """Return the maximum position size allowed for a signal.

    Args:
        signal_event: Event dict containing ``price`` and requested ``size``.
        risk_config: Risk configuration containing ``MAX_POSITION_PCT`` and
            ``ACCOUNT_EQUITY``.
        equity: Optional override for account equity; falls back to config.

    The allowed size is capped by ``MAX_POSITION_PCT`` of account equity. When
    no size or price is provided, a zero size is returned to avoid accidental
    over-allocation.
    """

    price = float(signal_event.get("price") or 0.0)
    requested_size = float(signal_event.get("size") or 0.0)
    base_equity = equity or risk_config.get("ACCOUNT_EQUITY", 1.0)

    if price <= 0.0:
        return 0.0

    max_notional = base_equity * float(risk_config.get("MAX_POSITION_PCT", 0.0))
    if max_notional <= 0.0:
        return 0.0

    allowed_size = max_notional / price
    return min(requested_size, allowed_size)


def _calculate_signal_notional(signal_event: Dict[str, float], size: float) -> float:
    """Calculate notional value for exposure checks."""

    price = float(signal_event.get("price") or 0.0)
    notional = float(signal_event.get("notional") or 0.0)
    if notional > 0:
        return notional
    return price * size


def generate_stop_loss(
    signal_event: Dict[str, float], risk_config: Dict[str, float]
) -> Dict[str, float]:
    """Generate a basic stop-loss level for a signal.

    Args:
        signal_event: Event dict containing ``price`` and ``side``.
        risk_config: Risk configuration containing ``STOP_LOSS_PCT``.

    Long signals place the stop below the entry, short signals above. The
    percentage is controlled via ``STOP_LOSS_PCT`` in the risk configuration.
    """

    price = float(signal_event.get("price") or 0.0)
    stop_pct = float(risk_config.get("STOP_LOSS_PCT", 0.0))
    side = str(signal_event.get("side") or "buy").lower()

    if price <= 0.0:
        return {"stop_price": 0.0, "side": side}

    if side == "sell":
        stop_price = price * (1 + stop_pct)
    else:
        stop_price = price * (1 - stop_pct)
    return {"stop_price": stop_price, "side": side}


def evaluate_signal(
    signal_event: Dict[str, float],
    risk_state: Dict[str, float],
    risk_config: Dict[str, float],
) -> RiskDecision:
    """Evaluate whether a signal should be accepted under current risk limits.

    The evaluation is purely arithmetic: drawdown guard, position sizing cap,
    exposure guard, and stop-loss suggestion. No external I/O occurs here.
    """

    equity = _resolve_equity(risk_state, risk_config)
    daily_pnl = float(risk_state.get("daily_pnl") or 0.0)
    drawdown_threshold = -equity * float(risk_config.get("MAX_DRAWDOWN_PCT", 0.0))
    if daily_pnl <= drawdown_threshold:
        return RiskDecision(
            approved=False,
            reason="max_daily_drawdown_exceeded",
            position_size=0.0,
            stop_price=None,
        )

    position_size = limit_position_size(signal_event, risk_config, equity)
    notional = _calculate_signal_notional(signal_event, position_size)
    exposure_pct = float(risk_state.get("total_exposure_pct") or 0.0)
    if equity > 0:
        exposure_pct += notional / equity

    if exposure_pct > float(risk_config.get("MAX_EXPOSURE_PCT", 1.0)):
        return RiskDecision(
            approved=False,
            reason="max_exposure_reached",
            position_size=0.0,
            stop_price=None,
        )

    stop_loss = generate_stop_loss(signal_event, risk_config)
    return RiskDecision(
        approved=True,
        reason=None,
        position_size=position_size,
        stop_price=stop_loss["stop_price"],
    )


# TODO: Replace placeholder risk logic with production-grade rules and
# connectivity to portfolio and order management services.
