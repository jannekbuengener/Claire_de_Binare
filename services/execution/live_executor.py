"""
Live Executor for Real Trading
Claire de Binare Trading Bot

Uses MEXC Exchange API for actual order execution with real money.

CAUTION: This executor places REAL orders with REAL money.
Only use in production after thorough testing in paper trading mode.
"""

import logging
from typing import Optional
from datetime import datetime

try:
    from .mexc_client import MEXCClient
    from .models import Order, ExecutionResult, OrderStatus
except ImportError:
    from mexc_client import MEXCClient
    from models import Order, ExecutionResult, OrderStatus


class LiveExecutor:
    """
    Executes orders on live MEXC exchange

    WARNING: This uses real money. Ensure proper risk controls are in place.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize Live Executor

        Args:
            api_key: MEXC API key
            api_secret: MEXC API secret
            testnet: Use testnet environment (MEXC has no testnet, use with caution)
            dry_run: Log orders but don't execute (safety mode)
        """
        self.client = MEXCClient(api_key, api_secret, testnet)
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

        if dry_run:
            self.logger.warning("LiveExecutor in DRY RUN mode - orders will NOT be executed")
        else:
            self.logger.critical("LiveExecutor in LIVE mode - orders WILL be executed with REAL money")

        # Verify API connection
        if not self.client.health_check():
            raise ConnectionError("Failed to connect to MEXC API - check credentials and network")

        self.logger.info("LiveExecutor initialized successfully")

    def execute_order(self, order: Order) -> ExecutionResult:
        """
        Execute order on live exchange

        Args:
            order: Order to execute

        Returns:
            ExecutionResult with actual exchange response
        """
        # Validate order before execution
        validation_error = self._validate_order(order)
        if validation_error:
            self.logger.error(f"Order validation failed: {validation_error}")
            return ExecutionResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=order.client_id,
                error_message=f"Validation failed: {validation_error}",
                timestamp=datetime.utcnow().isoformat()
            )

        # Dry run mode - simulate success
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would execute {order.side} {order.quantity} {order.symbol}")
            return self._simulate_dry_run_success(order)

        # LIVE EXECUTION - REAL MONEY
        self.logger.critical(
            f"EXECUTING LIVE ORDER: {order.side} {order.quantity} {order.symbol} "
            f"(client_id: {order.client_id})"
        )

        try:
            result = self.client.place_order(order)

            self.logger.info(
                f"Order executed: {result.status} - "
                f"Order ID: {result.order_id}, "
                f"Filled: {result.filled_quantity}/{result.quantity} @ {result.price}"
            )

            return result

        except Exception as e:
            self.logger.exception(f"Order execution failed: {e}")
            return ExecutionResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=order.client_id,
                error_message=str(e),
                timestamp=datetime.utcnow().isoformat()
            )

    def _validate_order(self, order: Order) -> Optional[str]:
        """
        Validate order before execution

        Returns:
            Error message if invalid, None if valid
        """
        # Basic validation
        if not order.symbol:
            return "Symbol is required"

        if not order.side or order.side.upper() not in ["BUY", "SELL"]:
            return f"Invalid side: {order.side}"

        if order.quantity <= 0:
            return f"Invalid quantity: {order.quantity}"

        # Check if symbol format is correct (should end with USDT typically)
        if not order.symbol.endswith("USDT"):
            return f"Symbol must be a USDT pair: {order.symbol}"

        # For BUY orders, check if we have sufficient balance
        if order.side.upper() == "BUY":
            # Get current price
            current_price = self.client.get_ticker_price(order.symbol)
            if not current_price:
                return "Unable to get current price for validation"

            # Estimate cost
            estimated_cost = order.quantity * current_price

            # Get USDT balance
            usdt_balance = self.client.get_asset_balance("USDT")
            if usdt_balance is None:
                return "Unable to verify USDT balance"

            if usdt_balance < estimated_cost:
                return f"Insufficient balance: {usdt_balance} USDT < {estimated_cost} USDT required"

        # For SELL orders, check if we have sufficient asset
        elif order.side.upper() == "SELL":
            # Extract base asset (e.g., BTC from BTCUSDT)
            base_asset = order.symbol.replace("USDT", "")

            asset_balance = self.client.get_asset_balance(base_asset)
            if asset_balance is None:
                return f"Unable to verify {base_asset} balance"

            if asset_balance < order.quantity:
                return f"Insufficient {base_asset}: {asset_balance} < {order.quantity} required"

        return None

    def _simulate_dry_run_success(self, order: Order) -> ExecutionResult:
        """
        Simulate successful execution in dry run mode

        Returns:
            Simulated ExecutionResult
        """
        # Get real price for realistic simulation
        current_price = self.client.get_ticker_price(order.symbol)

        return ExecutionResult(
            order_id=f"DRY_RUN_{order.client_id}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            filled_quantity=order.quantity,
            status=OrderStatus.FILLED.value,
            price=current_price,
            client_id=order.client_id,
            error_message=None,
            timestamp=datetime.utcnow().isoformat()
        )

    def get_order_status(self, symbol: str, order_id: str) -> Optional[ExecutionResult]:
        """
        Query status of existing order

        Args:
            symbol: Trading pair
            order_id: Exchange order ID

        Returns:
            ExecutionResult with current status
        """
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would query status for order {order_id}")
            return None

        return self.client.get_order_status(symbol, order_id)

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel open order

        Args:
            symbol: Trading pair
            order_id: Exchange order ID

        Returns:
            True if cancelled successfully
        """
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would cancel order {order_id}")
            return True

        self.logger.warning(f"Cancelling order {order_id} on {symbol}")
        return self.client.cancel_order(symbol, order_id)

    def get_account_balance(self) -> Optional[dict]:
        """
        Get current account balances

        Returns:
            Account balance information
        """
        return self.client.get_account_balance()

    def health_check(self) -> bool:
        """
        Check if executor is healthy and can connect to exchange

        Returns:
            True if healthy
        """
        return self.client.health_check()
