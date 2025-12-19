"""
Paper Trading Prometheus Metrics
Monitoring and performance tracking
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# Order metrics
paper_orders_total = Counter(
    'paper_orders_total',
    'Total paper trading orders',
    ['status', 'symbol', 'side']
)

paper_orders_filled = Counter(
    'paper_orders_filled',
    'Successfully filled orders',
    ['symbol', 'side']
)

paper_orders_rejected = Counter(
    'paper_orders_rejected',
    'Rejected orders',
    ['symbol', 'reason']
)

paper_orders_partial = Counter(
    'paper_orders_partial',
    'Partially filled orders',
    ['symbol']
)

# Fill metrics
paper_order_fill_rate = Gauge(
    'paper_order_fill_rate',
    'Order fill rate percentage',
    ['symbol']
)

paper_average_fill_ratio = Gauge(
    'paper_average_fill_ratio',
    'Average fill ratio for partial fills',
    ['symbol']
)

# P&L metrics
paper_trading_pnl = Gauge(
    'paper_trading_pnl',
    'Cumulative P&L by symbol',
    ['symbol']
)

paper_total_pnl = Gauge(
    'paper_total_pnl',
    'Total cumulative P&L across all symbols'
)

paper_fees_paid = Counter(
    'paper_fees_paid_total',
    'Total trading fees paid',
    ['symbol', 'fee_type']
)

# Execution metrics
paper_execution_latency_seconds = Histogram(
    'paper_execution_latency_seconds',
    'Order execution latency',
    ['symbol'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

paper_slippage_pct = Histogram(
    'paper_slippage_pct',
    'Slippage percentage',
    ['symbol', 'side'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0]
)

# Volume metrics
paper_volume_traded = Counter(
    'paper_volume_traded_usdt',
    'Total volume traded in USDT',
    ['symbol', 'side']
)

paper_average_order_size = Gauge(
    'paper_average_order_size_usdt',
    'Average order size in USDT',
    ['symbol']
)

# System info
paper_trading_info = Info(
    'paper_trading_system',
    'Paper trading system information'
)

# Set initial system info
paper_trading_info.info({
    'version': '2.0.0',
    'mode': 'enhanced_simulation',
    'features': 'slippage,fees,partial_fills,multi_asset'
})


class MetricsCollector:
    """Helper class for collecting and updating metrics"""

    @staticmethod
    def record_order_execution(
        symbol: str,
        side: str,
        status: str,
        filled_quantity: float,
        total_quantity: float,
        execution_price: float,
        latency_seconds: float,
        slippage_pct: float,
        fee_amount: float,
        fee_type: str
    ):
        """
        Record complete order execution metrics

        Args:
            symbol: Trading pair
            side: BUY or SELL
            status: Order status (FILLED, PARTIAL, REJECTED, etc.)
            filled_quantity: Amount filled
            total_quantity: Total order size
            execution_price: Execution price
            latency_seconds: Execution time
            slippage_pct: Slippage percentage
            fee_amount: Fee amount
            fee_type: TAKER or MAKER
        """
        # Order counts
        paper_orders_total.labels(
            status=status,
            symbol=symbol,
            side=side
        ).inc()

        if status == "FILLED":
            paper_orders_filled.labels(symbol=symbol, side=side).inc()
        elif status == "PARTIAL":
            paper_orders_partial.labels(symbol=symbol).inc()
        elif status == "REJECTED":
            # Extract rejection reason from status if available
            reason = "unknown"
            paper_orders_rejected.labels(symbol=symbol, reason=reason).inc()

        # Execution metrics
        if latency_seconds > 0:
            paper_execution_latency_seconds.labels(symbol=symbol).observe(latency_seconds)

        if slippage_pct > 0:
            paper_slippage_pct.labels(symbol=symbol, side=side).observe(slippage_pct)

        # Volume
        if filled_quantity > 0 and execution_price > 0:
            volume_usdt = filled_quantity * execution_price
            paper_volume_traded.labels(symbol=symbol, side=side).inc(volume_usdt)

        # Fees
        if fee_amount > 0:
            paper_fees_paid.labels(symbol=symbol, fee_type=fee_type).inc(fee_amount)

    @staticmethod
    def update_pnl(symbol: str, pnl_change: float):
        """
        Update P&L metrics

        Args:
            symbol: Trading pair
            pnl_change: P&L change amount
        """
        # Symbol-specific P&L
        current_pnl = paper_trading_pnl.labels(symbol=symbol)._value._value
        paper_trading_pnl.labels(symbol=symbol).set(current_pnl + pnl_change)

        # Total P&L
        current_total = paper_total_pnl._value._value
        paper_total_pnl.set(current_total + pnl_change)

    @staticmethod
    def update_fill_rate(symbol: str, fill_rate: float):
        """Update fill rate gauge"""
        paper_order_fill_rate.labels(symbol=symbol).set(fill_rate)

    @staticmethod
    def update_average_fill_ratio(symbol: str, avg_ratio: float):
        """Update average fill ratio for partial fills"""
        paper_average_fill_ratio.labels(symbol=symbol).set(avg_ratio)

    @staticmethod
    def update_average_order_size(symbol: str, avg_size_usdt: float):
        """Update average order size"""
        paper_average_order_size.labels(symbol=symbol).set(avg_size_usdt)
