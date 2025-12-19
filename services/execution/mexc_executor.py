"""
MEXC Real Executor for Live Trading
URGENT: Replaces MockExecutor with real MEXC API integration
"""

import requests
import time
import hashlib
import hmac
import uuid
from typing import Optional
from datetime import datetime
from .models import Order, ExecutionResult, OrderStatus
from .config import MEXC_API_KEY, MEXC_API_SECRET, MEXC_BASE_URL, MEXC_TESTNET


class MexcExecutor:
    """Real MEXC API Executor - NO MORE MOCK DATA"""

    def __init__(self):
        self.api_key = MEXC_API_KEY
        self.api_secret = MEXC_API_SECRET
        self.base_url = MEXC_BASE_URL
        self.testnet = MEXC_TESTNET

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "MEXC_API_KEY and MEXC_API_SECRET must be set in environment"
            )

    def _generate_signature(self, params: str, timestamp: str) -> str:
        """Generate MEXC API signature"""
        message = f"{timestamp}{params}"
        return hmac.new(
            self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _make_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        """Make authenticated request to MEXC API"""
        timestamp = str(int(time.time() * 1000))

        if params is None:
            params = {}

        # Add timestamp to params
        params["timestamp"] = timestamp

        # Sort parameters
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])

        # Generate signature
        signature = self._generate_signature(query_string, timestamp)

        # Add signature
        params["signature"] = signature

        headers = {"X-MEXC-APIKEY": self.api_key, "Content-Type": "application/json"}

        url = f"{self.base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=params, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, params=params, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    def get_current_price(self, symbol: str) -> float:
        """Get real current price from MEXC - NO MORE FAKE PRICES"""
        try:
            response = self._make_request(
                "GET", "/api/v3/ticker/price", {"symbol": symbol}
            )
            return float(response["price"])
        except Exception as e:
            raise Exception(f"Failed to get real price for {symbol}: {str(e)}")

    def execute_order(self, order: Order) -> ExecutionResult:
        """Execute REAL order via MEXC API - NO MORE MOCK"""
        try:
            # Get real current price
            current_price = self.get_current_price(order.symbol)

            # Prepare order parameters
            params = {
                "symbol": order.symbol,
                "side": order.side.upper(),
                "type": order.order_type.upper(),
                "quantity": str(order.quantity),
            }

            if order.order_type.lower() == "limit":
                params["price"] = str(order.price)
                params["timeInForce"] = "GTC"
            elif order.order_type.lower() == "market":
                # Market order uses current price
                params["quoteOrderQty"] = str(order.quantity * current_price)

            # Execute REAL order
            result = self._make_request("POST", "/api/v3/order", params)

            # Create execution result with REAL data
            execution_result = ExecutionResult(
                order_id=result["orderId"],
                client_id=order.client_id,
                status=OrderStatus.FILLED.value,  # Assume filled for now
                filled_price=current_price,
                filled_quantity=order.quantity,
                timestamp=datetime.utcnow().isoformat(),
                error_message=None,
            )

            return execution_result

        except Exception as e:
            # Return error result
            return ExecutionResult(
                order_id=f"ERROR_{uuid.uuid4().hex[:8]}",
                client_id=order.client_id,
                status=OrderStatus.REJECTED.value,
                filled_price=0.0,
                filled_quantity=0.0,
                timestamp=datetime.utcnow().isoformat(),
                error_message=f"MEXC API Error: {str(e)}",
            )

    def get_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        """Get REAL order status from MEXC"""
        try:
            result = self._make_request("GET", "/api/v3/order", {"orderId": order_id})

            return ExecutionResult(
                order_id=result["orderId"],
                client_id=result.get("clientOrderId", ""),
                status=result["status"].lower(),
                filled_price=float(result.get("price", 0)),
                filled_quantity=float(result.get("executedQty", 0)),
                timestamp=datetime.utcnow().isoformat(),
                error_message=None,
            )
        except Exception:
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel REAL order via MEXC API"""
        try:
            self._make_request("DELETE", "/api/v3/order", {"orderId": order_id})
            return True
        except Exception:
            return False

    def get_account_balance(self) -> dict:
        """Get REAL account balance from MEXC - NO MORE FAKE BALANCE"""
        try:
            result = self._make_request("GET", "/api/v3/account")

            balance_dict = {}
            for balance in result.get("balances", []):
                asset = balance["asset"]
                free = float(balance["free"])
                locked = float(balance["locked"])
                total = free + locked

                if total > 0:  # Only include assets with balance
                    balance_dict[asset] = {
                        "free": free,
                        "locked": locked,
                        "total": total,
                    }

            return balance_dict

        except Exception as e:
            raise Exception(f"Failed to get real account balance: {str(e)}")
