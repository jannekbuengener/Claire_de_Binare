"""
Claire de Binare - Execution Service (Live MEXC)
Handles real order placement via MEXC API
"""
import os
import logging
import time
import hmac
import hashlib
import requests
from typing import Dict, Optional
from flask import Flask, jsonify
import redis
import json
from decimal import Decimal

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = Flask(__name__)

class MEXCExecutor:
    """MEXC Order Executor with retry logic"""

    BASE_URL = os.getenv("MEXC_BASE_URL", "https://api.mexc.com")  # Oder testnet URL

    def __init__(self):
        self.api_key = os.getenv("MEXC_API_KEY")
        self.api_secret = os.getenv("MEXC_API_SECRET")
        self.trading_mode = os.getenv("TRADING_MODE", "paper")

        if self.trading_mode == "live" and not (self.api_key and self.api_secret):
            raise ValueError("MEXC_API_KEY and MEXC_API_SECRET required for live trading")

    def _sign(self, params: Dict) -> str:
        """Create HMAC SHA256 signature"""
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()

    def place_order(self, order: Dict) -> Dict:
        """Place order on MEXC (live or paper)"""
        if self.trading_mode == "paper":
            return self._simulate_order(order)

        try:
            params = {
                "symbol": order["symbol"],
                "side": order["side"].upper(),
                "type": "MARKET",
                "quantity": order["quantity"],
                "timestamp": int(time.time() * 1000)
            }

            params["signature"] = self._sign(params)

            headers = {"X-MEXC-APIKEY": self.api_key}

            response = requests.post(
                f"{self.BASE_URL}/api/v3/order",
                params=params,
                headers=headers,
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            return {
                "status": "filled",
                "order_id": result["orderId"],
                "executed_qty": float(result["executedQty"]),
                "avg_price": float(result.get("price", order["price"])),
                "commission": float(result.get("commission", 0)),
                "timestamp": time.time()
            }

        except requests.HTTPError as e:
            logger.error(f"MEXC API Error: {e.response.text}")
            return {"status": "rejected", "reason": str(e)}
        except requests.Timeout:
            logger.error("MEXC API Timeout")
            return {"status": "timeout", "reason": "API timeout"}
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return {"status": "error", "reason": str(e)}

    def _simulate_order(self, order: Dict) -> Dict:
        """Paper trading simulation"""
        logger.info(f"PAPER: Simulating order {order['symbol']} {order['side']}")

        commission = float(order["quantity"]) * float(order["price"]) * 0.0002

        return {
            "status": "filled",
            "order_id": f"PAPER_{int(time.time() * 1000)}",
            "executed_qty": float(order["quantity"]),
            "avg_price": float(order["price"]),
            "commission": commission,
            "timestamp": time.time()
        }

class ExecutionService:
    """Main Execution Service"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "cdb_redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )
        self.executor = MEXCExecutor()
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe("orders")

        logger.info(f"Execution Service started - Mode: {self.executor.trading_mode}")

    def process_orders(self):
        """Listen to orders channel and execute"""
        for message in self.pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                order = json.loads(message["data"])
                logger.info(f"Received order: {order['symbol']} {order['side']}")

                result = self.executor.place_order(order)

                result["symbol"] = order["symbol"]
                result["original_order"] = order

                self.redis_client.publish("order_results", json.dumps(result))
                logger.info(f"Order result: {result['status']}")

            except Exception as e:
                logger.error(f"Order processing failed: {e}")

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "cdb_execution"})

@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return """# HELP cdb_execution_status Service status (1=up, 0=down)
# TYPE cdb_execution_status gauge
cdb_execution_status{service="cdb_execution"} 1
""", 200, {"Content-Type": "text/plain; version=0.0.4"}

if __name__ == "__main__":
    service = ExecutionService()

    from threading import Thread
    listener = Thread(target=service.process_orders, daemon=True)
    listener.start()

    app.run(host="0.0.0.0", port=8003)