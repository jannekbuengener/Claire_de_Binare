"""
Configuration for Execution Service
Claire de Binare Trading Bot
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _read_secret(secret_name: str, fallback_env: str = None) -> str:
    """
    Read secret from Docker secrets or fallback to environment variable.

    Supports both production (Docker secrets) and development (.env) workflows.

    Args:
        secret_name: Name of the Docker secret file
        fallback_env: Environment variable name for development fallback

    Returns:
        Secret value as string, empty string if not found
    """
    # Try Docker secret first
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        return secret_path.read_text().strip()

    # Fallback to environment variable
    if fallback_env:
        return os.getenv(fallback_env, "")

    return ""

# Service Info
SERVICE_NAME = "execution_service"
SERVICE_VERSION = "0.1.0"
SERVICE_PORT = 8003

# MEXC API Configuration (Docker secrets with .env fallback)
MEXC_API_KEY = _read_secret("mexc_api_key", "MEXC_API_KEY")
MEXC_API_SECRET = _read_secret("mexc_api_secret", "MEXC_API_SECRET")
MEXC_BASE_URL = os.getenv("MEXC_BASE_URL", "https://contract.mexc.com")
MEXC_TESTNET = os.getenv("MEXC_TESTNET", "true").lower() == "true"

# Trading Mode
MOCK_TRADING = os.getenv("MOCK_TRADING", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"  # Safety: log orders without executing

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# PostgreSQL Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "cdb_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "cdb_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "cdb_secure_password_2025")
POSTGRES_DB = os.getenv("POSTGRES_DB", "claire_de_binare")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# Topics
TOPIC_ORDERS = "orders"  # Subscribe: Orders from Risk Manager
TOPIC_ORDER_RESULTS = "order_results"  # Publish: Execution results
TOPIC_ALERTS = "alerts"  # Publish: Execution alerts
STREAM_ORDER_RESULTS = os.getenv("STREAM_ORDER_RESULTS", "order_results")
STREAM_BOT_SHUTDOWN = os.getenv("STREAM_BOT_SHUTDOWN", "stream.bot_shutdown")

# Order Configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
ORDER_TIMEOUT_SECONDS = 10

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
