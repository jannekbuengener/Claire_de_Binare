"""
Prometheus Metrics Module for Claire de Binaire Services
Shared metrics definitions for all microservices

Based on: backoffice/docs/MONITORING_SPEC.md Section 3
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# Signal Engine Metrics
signals_generated = Counter(
    'cdb_signals_generated_total',
    'Total signals generated',
    ['symbol', 'direction', 'strategy']
)

signal_strength = Histogram(
    'cdb_signal_strength',
    'Signal strength distribution',
    ['symbol', 'strategy'],
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

market_data_events_received = Counter(
    'cdb_market_data_events_received_total',
    'Market data events received',
    ['symbol', 'source']
)

indicators_calculated = Counter(
    'cdb_indicators_calculated_total',
    'Technical indicators calculated',
    ['indicator_type', 'symbol']
)

# Risk Manager Metrics
signals_evaluated = Counter(
    'cdb_signals_evaluated_total',
    'Signals evaluated by risk engine',
    ['symbol']
)

orders_approved = Counter(
    'cdb_orders_approved_total',
    'Orders approved by risk',
    ['symbol']
)

orders_rejected = Counter(
    'cdb_orders_rejected_total',
    'Orders rejected by risk',
    ['symbol', 'reason_code']
)

approved_order_size = Histogram(
    'cdb_approved_order_size',
    'Size of approved orders',
    ['symbol'],
    buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
)

# Execution Service Metrics
orders_received = Counter(
    'cdb_orders_received_total',
    'Orders received by execution service',
    ['symbol']
)

trades_executed = Counter(
    'cdb_trades_executed_total',
    'Trades executed',
    ['symbol', 'side']
)

trade_pnl_usd = Histogram(
    'cdb_trade_pnl_usd',
    'Trade PnL in USD',
    ['symbol'],
    buckets=[-1000, -500, -100, -50, -10, 0, 10, 50, 100, 500, 1000]
)

cumulative_pnl_usd = Gauge(
    'cdb_cumulative_pnl_usd',
    'Cumulative PnL in USD'
)

open_positions = Gauge(
    'cdb_open_positions',
    'Number of open positions',
    ['symbol']
)

position_size = Gauge(
    'cdb_position_size',
    'Size of open positions',
    ['symbol']
)

# Market Data Screener Metrics
market_data_received = Counter(
    'cdb_market_data_received_total',
    'Market data events received',
    ['symbol', 'source']
)

websocket_connections_active = Gauge(
    'cdb_websocket_connections_active',
    'Active WebSocket connections'
)

rest_requests_total = Counter(
    'cdb_rest_requests_total',
    'REST API requests',
    ['endpoint', 'status_code']
)

# ============================================================================
# RISK METRICS
# ============================================================================

daily_drawdown_pct = Gauge(
    'cdb_daily_drawdown_pct',
    'Current daily drawdown percentage'
)

total_exposure_pct = Gauge(
    'cdb_total_exposure_pct',
    'Total portfolio exposure percentage'
)

position_exposure_pct = Gauge(
    'cdb_position_exposure_pct',
    'Position exposure percentage',
    ['symbol']
)

risk_violations = Counter(
    'cdb_risk_violations_total',
    'Risk limit violations',
    ['violation_type', 'layer']
)

circuit_breaker_active = Gauge(
    'cdb_circuit_breaker_active',
    'Circuit breaker status (1=active, 0=inactive)'
)

stop_loss_triggered = Counter(
    'cdb_stop_loss_triggered_total',
    'Stop-loss orders triggered',
    ['symbol']
)

data_staleness_seconds = Gauge(
    'cdb_data_staleness_seconds',
    'Age of last market data in seconds',
    ['source']
)

risk_layer_checks = Counter(
    'cdb_risk_layer_checks_total',
    'Risk layer checks performed',
    ['layer', 'result']
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

# Event Processing
event_processing_duration = Histogram(
    'cdb_event_processing_duration_seconds',
    'Event processing duration',
    ['service', 'event_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Signal Engine System Metrics
signal_processing_duration = Histogram(
    'cdb_signal_processing_duration_seconds',
    'Signal processing duration',
    ['strategy'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

signal_errors = Counter(
    'cdb_signal_errors_total',
    'Signal generation errors',
    ['error_type']
)

redis_publish_duration = Histogram(
    'cdb_redis_publish_duration_seconds',
    'Redis publish operation duration',
    ['topic'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Risk Engine System Metrics
risk_decision_duration = Histogram(
    'cdb_risk_decision_duration_seconds',
    'Risk decision duration',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

risk_state_update_duration = Histogram(
    'cdb_risk_state_update_duration_seconds',
    'Risk state update duration',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
)

# Execution Service System Metrics
order_execution_duration = Histogram(
    'cdb_order_execution_duration_seconds',
    'Order execution duration',
    ['exchange'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

execution_errors = Counter(
    'cdb_execution_errors_total',
    'Order execution errors',
    ['error_type']
)

slippage_bps = Histogram(
    'cdb_slippage_bps',
    'Slippage in basis points',
    ['symbol'],
    buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500]
)

# Market Data System Metrics
data_ingestion_latency = Histogram(
    'cdb_data_ingestion_latency_seconds',
    'Market data ingestion latency',
    ['source'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

websocket_reconnects = Counter(
    'cdb_websocket_reconnects_total',
    'WebSocket reconnection attempts'
)

# Health Status (per Service)
health_status = Gauge(
    'cdb_health_status',
    'Service health status (1=healthy, 0=unhealthy)',
    ['service']
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def record_signal(symbol: str, direction: str, strategy: str, strength: Optional[float] = None):
    """Record a generated signal"""
    signals_generated.labels(symbol=symbol, direction=direction, strategy=strategy).inc()
    if strength is not None:
        signal_strength.labels(symbol=symbol, strategy=strategy).observe(strength)
    logger.debug(f"Metric recorded: signal {symbol} {direction} strength={strength}")

def record_risk_decision(symbol: str, approved: bool, reason_code: Optional[str] = None, size: Optional[float] = None):
    """Record a risk decision"""
    signals_evaluated.labels(symbol=symbol).inc()
    if approved:
        orders_approved.labels(symbol=symbol).inc()
        if size is not None:
            approved_order_size.labels(symbol=symbol).observe(size)
    else:
        orders_rejected.labels(symbol=symbol, reason_code=reason_code or "UNKNOWN").inc()
    logger.debug(f"Metric recorded: risk_decision {symbol} approved={approved} reason={reason_code}")

def update_drawdown(drawdown_pct: float):
    """Update daily drawdown gauge"""
    daily_drawdown_pct.set(drawdown_pct)
    logger.debug(f"Metric updated: daily_drawdown_pct={drawdown_pct:.2f}%")

def update_exposure(total_pct: float, position_exposures: Optional[Dict[str, float]] = None):
    """Update exposure gauges"""
    total_exposure_pct.set(total_pct)
    if position_exposures:
        for symbol, pct in position_exposures.items():
            position_exposure_pct.labels(symbol=symbol).set(pct)
    logger.debug(f"Metric updated: total_exposure_pct={total_pct:.2f}%")

def record_violation(violation_type: str, layer: int):
    """Record a risk violation"""
    risk_violations.labels(violation_type=violation_type, layer=str(layer)).inc()
    logger.warning(f"Risk violation: {violation_type} at layer {layer}")

def record_trade(symbol: str, side: str, pnl: Optional[float] = None, slippage: Optional[float] = None):
    """Record an executed trade"""
    trades_executed.labels(symbol=symbol, side=side).inc()
    if pnl is not None:
        trade_pnl_usd.labels(symbol=symbol).observe(pnl)
    if slippage is not None:
        slippage_bps.labels(symbol=symbol).observe(slippage)
    logger.debug(f"Metric recorded: trade {symbol} {side} pnl={pnl} slippage={slippage}")

def update_pnl(total_pnl: float):
    """Update cumulative PnL"""
    cumulative_pnl_usd.set(total_pnl)
    logger.debug(f"Metric updated: cumulative_pnl_usd=${total_pnl:.2f}")

def update_positions(positions: Dict[str, float]):
    """Update open positions and sizes"""
    for symbol, size in positions.items():
        open_positions.labels(symbol=symbol).set(1 if size > 0 else 0)
        position_size.labels(symbol=symbol).set(size)
    logger.debug(f"Metric updated: {len(positions)} positions")

def set_circuit_breaker(active: bool):
    """Set circuit breaker status"""
    circuit_breaker_active.set(1 if active else 0)
    logger.info(f"Circuit breaker: {'ACTIVE' if active else 'INACTIVE'}")

def set_health_status(service: str, is_healthy: bool):
    """Set service health status"""
    health_status.labels(service=service).set(1 if is_healthy else 0)
    logger.info(f"Health status: {service} = {'healthy' if is_healthy else 'unhealthy'}")

def measure_event_processing(service: str, event_type: str):
    """Context manager for measuring event processing time"""
    return event_processing_duration.labels(service=service, event_type=event_type).time()

def get_metrics():
    """Return Prometheus metrics in text format"""
    return generate_latest(REGISTRY)

# ============================================================================
# SPECIALIZED CONTEXT MANAGERS
# ============================================================================

def measure_signal_processing(strategy: str):
    """Context manager for measuring signal processing time"""
    return signal_processing_duration.labels(strategy=strategy).time()

def measure_risk_decision():
    """Context manager for measuring risk decision time"""
    return risk_decision_duration.time()

def measure_order_execution(exchange: str = "MEXC"):
    """Context manager for measuring order execution time"""
    return order_execution_duration.labels(exchange=exchange).time()
