"""
Live Executor for Real Trading
Claire de Binare Trading Bot

Features:
- Real MEXC API execution
- Real market prices
- Real order placement
- Error handling and retries
"""

import logging
from typing import Optional, Dict, Any

from core.utils.clock import utcnow

try:
    from .models import Order, ExecutionResult, OrderStatus
    from .mexc_client import MexcClient
except ImportError:
    from models import Order, ExecutionResult, OrderStatus
    from mexc_client import MexcClient

logger = logging.getLogger(__name__)


class LiveExecutor:
    """Executes real orders via MEXC API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        dry_run: bool = False,
    ):
        """
        Initialize Live Executor

        Args:
            api_key: MEXC API Key (default: from env)
            api_secret: MEXC API Secret (default: from env)
            testnet: Use testnet API (default: False)
            dry_run: Log orders without executing (default: False)
        """
        self.dry_run = dry_run
        self.testnet = testnet

        if dry_run:
            logger.warning("🔶 DRY RUN MODE - Orders will be logged but NOT executed!")
            self.client = None
        else:
            try:
                self.client = MexcClient(
                    api_key=api_key, api_secret=api_secret, testnet=testnet
                )
                logger.info("✅ Live Executor initialized")
            except ValueError as e:
                logger.error(f"❌ Failed to initialize MEXC client: {e}")
                raise

    def execute_order(self, order: Order) -> ExecutionResult:
        """
        Execute real order via MEXC API

        Args:
            order: Order to execute

        Returns:
            ExecutionResult with real execution data
        """
        logger.info(
            f"🚀 Executing order: {order.symbol} {order.side} {order.quantity} {order.order_type}"
        )

        # DRY RUN: Log and return mock result
        if self.dry_run:
            logger.warning(
                f"🔶 DRY RUN: Would execute {order.symbol} {order.side} {order.quantity}"
            )
            return self._create_dry_run_result(order)

        try:
            # Execute based on order type
            if order.order_type.upper() == "MARKET":
                response = self.client.place_market_order(
                    symbol=order.symbol, side=order.side, quantity=float(order.quantity)
                )
            elif order.order_type.upper() == "LIMIT":
                if not order.price:
                    raise ValueError("Limit order requires price")
                response = self.client.place_limit_order(
                    symbol=order.symbol,
                    side=order.side,
                    quantity=float(order.quantity),
                    price=float(order.price),
                )
            else:
                raise ValueError(f"Unsupported order type: {order.order_type}")

            # Parse MEXC response
            return self._parse_mexc_response(order, response)

        except Exception as e:
            logger.error(f"❌ Order execution failed: {e}")
            return self._create_error_result(order, str(e))

    def _parse_mexc_response(
        self, order: Order, response: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Parse MEXC API response into ExecutionResult

        MEXC Response Format:
        {
            "symbol": "BTCUSDT",
            "orderId": "123456",
            "clientOrderId": "CDB_xxx",
            "transactTime": 1234567890,
            "price": "50000.00",
            "origQty": "0.01",
            "executedQty": "0.01",
            "status": "FILLED",
            "type": "MARKET",
            "side": "BUY"
        }
        """
        status_map = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PARTIAL,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.REJECTED,
        }

        mexc_status = response.get("status", "UNKNOWN")
        status = status_map.get(mexc_status, OrderStatus.PENDING)

        # Get execution price
        if status == OrderStatus.FILLED or status == OrderStatus.PARTIAL:
            # For filled orders, use executed price or average price
            execution_price = float(response.get("price", 0))
            if execution_price == 0:
                # Fallback: get current market price
                execution_price = self.client.get_ticker_price(order.symbol)
        else:
            execution_price = 0.0

        filled_qty = float(response.get("executedQty", 0))

        result = ExecutionResult(
            order_id=str(response.get("orderId")),
            client_id=order.client_id or response.get("clientOrderId", ""),
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            filled_quantity=filled_qty,
            price=order.price,
            execution_price=execution_price,
            status=status,
            timestamp=utcnow(),
            exchange="MEXC",
            exchange_order_id=str(response.get("orderId")),
            error_message=None,
            metadata={
                "mexc_response": response,
                "testnet": self.testnet,
                "transact_time": response.get("transactTime"),
            },
        )

        logger.info(
            f"✅ Order executed: {result.symbol} {result.status} - "
            f"Filled: {result.filled_quantity}/{result.quantity} @ {result.execution_price}"
        )

        return result

    def _create_dry_run_result(self, order: Order) -> ExecutionResult:
        """Create mock result for dry-run mode"""
        return ExecutionResult(
            order_id=f"DRY_RUN_{order.client_id or 'UNKNOWN'}",
            client_id=order.client_id or "",
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            filled_quantity=order.quantity,
            price=order.price,
            execution_price=order.price or 0.0,
            status=OrderStatus.FILLED,
            timestamp=utcnow(),
            exchange="DRY_RUN",
            exchange_order_id="DRY_RUN",
            error_message=None,
            metadata={"dry_run": True},
        )

    def _create_error_result(self, order: Order, error: str) -> ExecutionResult:
        """Create error result"""
        return ExecutionResult(
            order_id=f"ERROR_{order.client_id or 'UNKNOWN'}",
            client_id=order.client_id or "",
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            filled_quantity=0.0,
            price=order.price,
            execution_price=0.0,
            status=OrderStatus.REJECTED,
            timestamp=utcnow(),
            exchange="MEXC",
            exchange_order_id="",
            error_message=error,
            metadata={"error": error},
        )

    def get_balance(self, asset: str = "USDT") -> float:
        """
        Get real account balance from MEXC

        Args:
            asset: Asset symbol (default: "USDT")

        Returns:
            Available balance
        """
        if self.dry_run:
            logger.warning(f"🔶 DRY RUN: Would fetch {asset} balance")
            return 10000.0  # Mock balance for dry-run

        try:
            balance = self.client.get_balance(asset)
            logger.info(f"💰 Real balance fetched: {balance} {asset}")
            return balance
        except Exception as e:
            logger.error(f"❌ Failed to fetch balance: {e}")
            return 0.0
