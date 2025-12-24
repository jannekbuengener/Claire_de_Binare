"""
WebSocket Service - STUB/TEMPLATE
⚠️ NOT IMPLEMENTED - Placeholder for future development

Purpose: Real-time WebSocket connections to exchange APIs
Port: 8000
Dependencies: Redis (for pub/sub)

TODO:
1. Implement WebSocket client for exchange API (MEXC, Binance, etc.)
2. Implement connection management (reconnection, heartbeat)
3. Implement data stream handling (order book, trades, klines)
4. Implement Redis pub/sub for data distribution
5. Add proper error handling and logging
6. Configure environment variables (WS_EXCHANGE, WS_SYMBOLS, etc.)
7. Implement graceful shutdown
"""

import logging
import os
import sys
from flask import Flask, jsonify

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] ws_service: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Flask app for health endpoint
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint required by Docker HEALTHCHECK"""
    return jsonify({"status": "healthy", "service": "websocket"}), 200


def main():
    """
    Main service loop (NOT IMPLEMENTED)

    TODO: Implement WebSocket service logic:
    - Connect to Redis (use REDIS_HOST, REDIS_PASSWORD from env)
    - Initialize WebSocket client for exchange API
    - Subscribe to market data streams (order book, trades, klines)
    - Publish received data to Redis pub/sub channels
    - Handle connection errors and reconnection
    """
    logger.warning("=" * 60)
    logger.warning("WEBSOCKET SERVICE - STUB ONLY")
    logger.warning("This service is NOT IMPLEMENTED")
    logger.warning("Running health endpoint only on port 8000")
    logger.warning("=" * 60)

    # TODO: Add actual WebSocket service initialization here
    # Example pattern (DO NOT IMPLEMENT WITHOUT SECRETS):
    # redis_client = redis.Redis(
    #     host=os.getenv("REDIS_HOST", "localhost"),
    #     password=os.getenv("REDIS_PASSWORD"),
    #     decode_responses=True
    # )
    #
    # async def ws_handler():
    #     uri = os.getenv("WS_URI")
    #     async with websockets.connect(uri) as websocket:
    #         # Subscribe to streams
    #         # Publish to Redis
    #         pass

    # For now, just run the health endpoint
    logger.info("Starting health endpoint on port 8000...")
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Service crashed: {e}")
        sys.exit(1)
