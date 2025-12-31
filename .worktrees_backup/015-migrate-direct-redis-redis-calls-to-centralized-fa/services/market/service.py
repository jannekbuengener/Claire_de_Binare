"""
Market Data Service - STUB/TEMPLATE
⚠️ NOT IMPLEMENTED - Placeholder for future development

Purpose: Market data ingestion and processing
Port: 8004
Dependencies: Redis, Postgres

TODO:
1. Implement market data fetching from exchange APIs
2. Implement data validation and normalization
3. Implement Redis pub/sub for real-time data distribution
4. Implement Postgres persistence for historical data
5. Integrate email_alerter for critical market events
6. Add proper error handling and logging
7. Configure environment variables (see config.py pattern)
"""

import logging
import os
import sys
import time
from flask import Flask, jsonify

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] market_service: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Flask app for health endpoint
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint required by Docker HEALTHCHECK"""
    return jsonify({"status": "healthy", "service": "market_data"}), 200


def main():
    """
    Main service loop (NOT IMPLEMENTED)

    TODO: Implement market data service logic:
    - Connect to Redis (use REDIS_HOST, REDIS_PASSWORD from env)
    - Connect to Postgres (use POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD)
    - Initialize exchange API clients
    - Start data ingestion loop
    - Publish to Redis pub/sub
    - Persist to Postgres
    """
    logger.warning("=" * 60)
    logger.warning("MARKET DATA SERVICE - STUB ONLY")
    logger.warning("This service is NOT IMPLEMENTED")
    logger.warning("Running health endpoint only on port 8004")
    logger.warning("=" * 60)

    # TODO: Add actual service initialization here
    # Example pattern (DO NOT IMPLEMENT WITHOUT SECRETS):
    # redis_client = redis.Redis(
    #     host=os.getenv("REDIS_HOST", "localhost"),
    #     password=os.getenv("REDIS_PASSWORD"),
    #     decode_responses=True
    # )

    # For now, just run the health endpoint
    logger.info("Starting health endpoint on port 8004...")
    app.run(host="0.0.0.0", port=8004, debug=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Service crashed: {e}")
        sys.exit(1)
