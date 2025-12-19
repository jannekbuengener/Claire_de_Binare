"""
MEXC Exchange API Client
Claire de Binare Trading Bot

Features:
- REST API for order execution
- WebSocket for real-time price feeds
- Account balance queries
- Order status tracking

Documentation: https://mexcdevelop.github.io/apidocs/spot_v3_en/
"""

import hmac
import hashlib
import time
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlencode

try:
    from .models import Order, ExecutionResult, OrderStatus
except ImportError:
    from models import Order, ExecutionResult, OrderStatus


class MEXCClient:
    """MEXC Exchange API Client"""

    BASE_URL = "https://api.mexc.com"
    WS_URL = "wss://wbs.mexc.com/ws"

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize MEXC API Client

        Args:
            api_key: MEXC API key
            api_secret: MEXC API secret
            testnet: Use testnet environment (if available)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.logger = logging.getLogger(__name__)

        if testnet:
            # MEXC doesn't have a dedicated testnet, use caution with small amounts
            self.logger.warning("MEXC testnet not available - use with extreme caution")

        self.session = requests.Session()
        self.session.headers.update({
            "X-MEXC-APIKEY": self.api_key,
            "Content-Type": "application/json"
        })

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC SHA256 signature for request

        Args:
            params: Request parameters

        Returns:
            Signature string
        """
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        endpoint: str,
        signed: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API request

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            signed: Whether request requires signature
            **kwargs: Additional request parameters

        Returns:
            API response as dictionary
        """
        url = f"{self.BASE_URL}{endpoint}"

        if signed:
            params = kwargs.get('params', {})
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            params['signature'] = self._generate_signature(params)
            kwargs['params'] = params

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for symbol

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')

        Returns:
            Current price or None if error
        """
        try:
            response = self._request(
                "GET",
                "/api/v3/ticker/price",
                params={"symbol": symbol}
            )
            return float(response.get("price", 0))
        except Exception as e:
            self.logger.error(f"Failed to get ticker price: {e}")
            return None

    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """
        Get account balances

        Returns:
            Account balance information
        """
        try:
            response = self._request(
                "GET",
                "/api/v3/account",
                signed=True
            )
            return response
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return None

    def get_asset_balance(self, asset: str) -> Optional[float]:
        """
        Get balance for specific asset

        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')

        Returns:
            Available balance for asset
        """
        account = self.get_account_balance()
        if not account:
            return None

        balances = account.get("balances", [])
        for balance in balances:
            if balance.get("asset") == asset:
                return float(balance.get("free", 0))

        return 0.0

    def place_order(self, order: Order) -> ExecutionResult:
        """
        Place order on MEXC exchange

        Args:
            order: Order object with details

        Returns:
            ExecutionResult with exchange response
        """
        try:
            # Prepare order parameters
            params = {
                "symbol": order.symbol,
                "side": order.side.upper(),
                "type": order.order_type.upper() if hasattr(order, 'order_type') else "LIMIT",
                "quantity": str(order.quantity),
            }

            # Add client order ID if provided
            if order.client_id:
                params["newClientOrderId"] = order.client_id

            # Add price for limit orders
            if hasattr(order, 'price') and order.price:
                params["price"] = str(order.price)
                params["timeInForce"] = "GTC"  # Good Till Cancel
            else:
                # Market order
                params["type"] = "MARKET"

            # Execute order
            response = self._request(
                "POST",
                "/api/v3/order",
                signed=True,
                params=params
            )

            # Parse response
            return self._parse_order_response(response, order)

        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
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

    def _parse_order_response(
        self,
        response: Dict[str, Any],
        original_order: Order
    ) -> ExecutionResult:
        """
        Parse MEXC order response into ExecutionResult

        Args:
            response: MEXC API response
            original_order: Original order request

        Returns:
            ExecutionResult object
        """
        status_map = {
            "NEW": OrderStatus.PENDING.value,
            "PARTIALLY_FILLED": OrderStatus.PARTIAL.value,
            "FILLED": OrderStatus.FILLED.value,
            "CANCELED": OrderStatus.CANCELLED.value,
            "REJECTED": OrderStatus.REJECTED.value,
            "EXPIRED": OrderStatus.REJECTED.value,
        }

        mexc_status = response.get("status", "REJECTED")
        our_status = status_map.get(mexc_status, OrderStatus.REJECTED.value)

        # Calculate average price if available
        executed_qty = float(response.get("executedQty", 0))
        cumulative_quote_qty = float(response.get("cummulativeQuoteQty", 0))

        avg_price = None
        if executed_qty > 0 and cumulative_quote_qty > 0:
            avg_price = cumulative_quote_qty / executed_qty

        return ExecutionResult(
            order_id=str(response.get("orderId", "")),
            symbol=response.get("symbol", original_order.symbol),
            side=response.get("side", original_order.side),
            quantity=float(response.get("origQty", original_order.quantity)),
            filled_quantity=executed_qty,
            status=our_status,
            price=avg_price,
            client_id=response.get("clientOrderId"),
            error_message=None,
            timestamp=datetime.utcnow().isoformat()
        )

    def get_order_status(self, symbol: str, order_id: str) -> Optional[ExecutionResult]:
        """
        Query order status

        Args:
            symbol: Trading pair
            order_id: Order ID from exchange

        Returns:
            ExecutionResult with current status
        """
        try:
            response = self._request(
                "GET",
                "/api/v3/order",
                signed=True,
                params={
                    "symbol": symbol,
                    "orderId": order_id
                }
            )

            # Create minimal Order object for parsing
            dummy_order = Order(
                symbol=symbol,
                side=response.get("side", "BUY"),
                quantity=float(response.get("origQty", 0))
            )

            return self._parse_order_response(response, dummy_order)

        except Exception as e:
            self.logger.error(f"Failed to query order status: {e}")
            return None

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel open order

        Args:
            symbol: Trading pair
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            self._request(
                "DELETE",
                "/api/v3/order",
                signed=True,
                params={
                    "symbol": symbol,
                    "orderId": order_id
                }
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if API connection is healthy

        Returns:
            True if API is accessible
        """
        try:
            self._request("GET", "/api/v3/ping")
            return True
        except Exception:
            return False
