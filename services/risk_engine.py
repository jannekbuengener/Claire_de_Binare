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
    drawdown_threshold = -equity * float(
        risk_config.get("MAX_DRAWDOWN_PCT", 0.0)
    )
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


# ============================================================================
# Enhanced Risk Evaluation with MEXC Perpetuals Integration
# ============================================================================


@dataclass
class EnhancedRiskDecision(RiskDecision):
    """Enhanced risk decision with perpetuals metadata.

    Extends base RiskDecision with additional fields for perpetual futures:
        - liquidation_price: Calculated liquidation price
        - liquidation_distance: Distance to liquidation as decimal
        - leverage: Applied leverage multiplier
        - expected_slippage_bps: Expected slippage in basis points
        - execution_fees: Expected execution fees
        - sizing_method: Position sizing method used
        - funding_fee_estimate: Estimated funding fee per 8h
    """

    liquidation_price: Optional[float] = None
    liquidation_distance: Optional[float] = None
    leverage: Optional[int] = None
    expected_slippage_bps: Optional[float] = None
    execution_fees: Optional[float] = None
    sizing_method: Optional[str] = None
    funding_fee_estimate: Optional[float] = None


def evaluate_signal_v2(
    signal_event: Dict,
    risk_state: Dict,
    risk_config: Dict,
    market_conditions: Dict,
) -> EnhancedRiskDecision:
    """Enhanced signal evaluation with MEXC Perpetual Futures mechanics.

    Integrates:
    - Module 1: MEXC Perpetuals (margin, liquidation, funding)
    - Module 2: Advanced Position Sizing (vol-targeting, Kelly, etc.)
    - Module 3: Execution Simulation (slippage, fees, partial fills)

    Args:
        signal_event: Signal dict with keys: symbol, side, price.
        risk_state: Risk state dict with keys: equity, daily_pnl, total_exposure_pct,
            win_rate, avg_win, avg_loss.
        risk_config: Risk config dict (see load_risk_config()).
        market_conditions: Market data dict with keys:
            - volatility: Asset volatility (annualized)
            - atr: Average True Range
            - order_book_depth: Order book depth in quote currency
            - funding_rate: Current funding rate (optional)

    Returns:
        EnhancedRiskDecision with approval status and metadata.

    Example:
        >>> signal = {"symbol": "BTCUSDT", "side": "buy", "price": 50000}
        >>> risk_state = {"equity": 100000, "daily_pnl": 0, "total_exposure_pct": 0}
        >>> risk_config = load_risk_config()
        >>> market_conditions = {"volatility": 0.60, "atr": 2500, "order_book_depth": 1000000}
        >>> decision = evaluate_signal_v2(signal, risk_state, risk_config, market_conditions)
        >>> decision.approved
        True
    """
    # Import modules (lazy import to avoid circular dependencies)
    from services.mexc_perpetuals import (
        create_position_from_signal,
        validate_liquidation_distance,
    )
    from services.position_sizing import select_sizing_method
    from services.execution_simulator import ExecutionSimulator

    # 1. Basic Risk Checks (from original evaluate_signal)
    equity = _resolve_equity(risk_state, risk_config)
    daily_pnl = float(risk_state.get("daily_pnl") or 0.0)
    drawdown_threshold = -equity * float(risk_config.get("MAX_DRAWDOWN_PCT", 0.0))

    if daily_pnl <= drawdown_threshold:
        return EnhancedRiskDecision(
            approved=False,
            reason="max_daily_drawdown_exceeded",
            position_size=0.0,
            stop_price=None,
        )

    # 2. Advanced Position Sizing (Module 2)
    sizing_method = risk_config.get("SIZING_METHOD", "fixed_fractional")
    try:
        sizing_result = select_sizing_method(
            method=sizing_method,
            equity=equity,
            signal=signal_event,
            market_conditions=market_conditions,
            config=risk_config,
        )
        position_size_usd = sizing_result.size_usd
        position_size_contracts = position_size_usd / float(signal_event["price"])
    except (ValueError, KeyError) as e:
        # Sizing method error → fallback to basic sizing
        position_size_contracts = limit_position_size(signal_event, risk_config, equity)
        position_size_usd = position_size_contracts * float(signal_event["price"])
        sizing_result = None

    # Check if position size is zero
    if position_size_contracts <= 0:
        return EnhancedRiskDecision(
            approved=False,
            reason="position_size_zero_after_sizing",
            position_size=0.0,
            stop_price=None,
        )

    # 3. Exposure Check
    notional = position_size_usd
    exposure_pct = float(risk_state.get("total_exposure_pct") or 0.0)
    if equity > 0:
        exposure_pct += notional / equity

    if exposure_pct > float(risk_config.get("MAX_EXPOSURE_PCT", 1.0)):
        return EnhancedRiskDecision(
            approved=False,
            reason="max_exposure_reached",
            position_size=0.0,
            stop_price=None,
        )

    # 4. Perpetuals-Specific Checks (Module 1)
    try:
        position = create_position_from_signal(
            signal=signal_event,
            size=position_size_contracts,
            config=risk_config,
        )

        # Liquidation distance check
        min_liq_distance = float(risk_config.get("MIN_LIQUIDATION_DISTANCE", 0.15))
        liq_validation = validate_liquidation_distance(position, min_liq_distance)

        if not liq_validation["approved"]:
            return EnhancedRiskDecision(
                approved=False,
                reason=liq_validation["reason"],
                position_size=0.0,
                stop_price=None,
                liquidation_distance=liq_validation["distance"],
            )

        # Calculate liquidation price and distance
        liq_price = position.calculate_liquidation_price()
        liq_distance = position.calculate_liquidation_distance()

        # Estimate funding fee
        funding_rate = market_conditions.get("funding_rate", risk_config.get("FUNDING_RATE", 0.0001))
        funding_fee = position.calculate_funding_fee(funding_rate, hours=8.0)

    except Exception as e:
        # Perpetuals check failed → reject
        return EnhancedRiskDecision(
            approved=False,
            reason=f"perpetuals_validation_error: {str(e)}",
            position_size=0.0,
            stop_price=None,
        )

    # 5. Execution Simulation (Module 3)
    try:
        simulator = ExecutionSimulator(risk_config)
        execution = simulator.simulate_market_order(
            side=signal_event.get("side", "buy"),
            size=position_size_contracts,
            current_price=float(signal_event["price"]),
            order_book_depth=float(market_conditions.get("order_book_depth", 1000000.0)),
            volatility=float(market_conditions.get("volatility", 0.60)),
        )

        # Check for excessive slippage
        max_slippage_bps = float(risk_config.get("MAX_SLIPPAGE_BPS", 100.0))
        if execution.slippage_bps > max_slippage_bps:
            return EnhancedRiskDecision(
                approved=False,
                reason="excessive_slippage",
                position_size=0.0,
                stop_price=None,
                expected_slippage_bps=execution.slippage_bps,
            )

        # Use execution results
        final_size = execution.filled_size
        adjusted_entry_price = execution.avg_fill_price
        execution_fees = execution.fees

        # Update position with adjusted entry price (if partial fill)
        if execution.partial_fill:
            position = create_position_from_signal(
                signal=signal_event,
                size=final_size,
                config=risk_config,
            )
            liq_price = position.calculate_liquidation_price()
            liq_distance = position.calculate_liquidation_distance()

    except Exception as e:
        # Execution simulation failed → use original values
        final_size = position_size_contracts
        adjusted_entry_price = float(signal_event["price"])
        execution_fees = 0.0
        execution = None

    # 6. Generate stop-loss
    stop_loss = generate_stop_loss(signal_event, risk_config)

    # 7. Return approved decision with full metadata
    return EnhancedRiskDecision(
        approved=True,
        reason=None,
        position_size=final_size,
        stop_price=stop_loss["stop_price"],
        liquidation_price=liq_price,
        liquidation_distance=liq_distance,
        leverage=position.leverage,
        expected_slippage_bps=execution.slippage_bps if execution else 0.0,
        execution_fees=execution_fees,
        sizing_method=sizing_method,
        funding_fee_estimate=funding_fee,
    )


# ============================================================================
# Configuration Loaders
# ============================================================================


def load_risk_config() -> Dict:
    """Load comprehensive risk configuration from environment variables.

    Combines:
    - Base risk limits (from original risk_engine)
    - Perpetuals config (from mexc_perpetuals)
    - Position sizing config (from position_sizing)
    - Execution config (from execution_simulator)

    Returns:
        Dict with all risk configuration parameters.
    """
    import os
    from services.mexc_perpetuals import load_perpetuals_config
    from services.position_sizing import load_sizing_config
    from services.execution_simulator import load_execution_config

    base_config = {
        "ACCOUNT_EQUITY": float(os.getenv("ACCOUNT_EQUITY", "100000.0")),
        "MAX_POSITION_PCT": float(os.getenv("MAX_POSITION_PCT", "0.10")),
        "MAX_DRAWDOWN_PCT": float(os.getenv("MAX_DRAWDOWN_PCT", "0.05")),
        "MAX_EXPOSURE_PCT": float(os.getenv("MAX_EXPOSURE_PCT", "0.50")),
        "STOP_LOSS_PCT": float(os.getenv("STOP_LOSS_PCT", "0.02")),
        "MAX_SLIPPAGE_BPS": float(os.getenv("MAX_SLIPPAGE_BPS", "100.0")),
    }

    # Merge all configs
    config = {
        **base_config,
        **load_perpetuals_config(),
        **load_sizing_config(),
        **load_execution_config(),
    }

    return config


# TODO: Replace placeholder risk logic with production-grade rules and
# connectivity to portfolio and order management services.
