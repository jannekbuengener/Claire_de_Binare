"""
Configuration for Execution Service
Claire de Binare Trading Bot
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from core.secrets import read_secret

load_dotenv()

# Service Info
SERVICE_NAME = "execution_service"
SERVICE_VERSION = "0.1.0"
SERVICE_PORT = 8003

# MEXC API Configuration (Docker secrets with .env fallback)
MEXC_API_KEY = read_secret("mexc_api_key", "MEXC_API_KEY")
MEXC_API_SECRET = read_secret("mexc_api_secret", "MEXC_API_SECRET")
# Spot REST base. Default is the mainnet spot host https://api.mexc.com.
# MEXC has no spot testnet; the former https://contract.mexc.com futures host was
# discontinued 2026-01-19 and must not be a spot default.
# See docs/live-readiness/LR-050-VENUE-ENDPOINT-SEMANTICS-2026-07-03.md §4.
MEXC_BASE_URL = os.getenv("MEXC_BASE_URL", "https://api.mexc.com")
# Nominal flag only: MEXC_TESTNET is NOT a no-send proof and selects no real sandbox
# (no MEXC spot testnet exists). No-send depends on DRY_RUN + MOCK_TRADING
# (mock_builtin). See LR-050-VENUE-ENDPOINT-SEMANTICS-2026-07-03.md §5.
MEXC_TESTNET = os.getenv("MEXC_TESTNET", "true").lower() == "true"

# Trading Mode
MOCK_TRADING = os.getenv("MOCK_TRADING", "true").lower() == "true"
DRY_RUN = (
    os.getenv("DRY_RUN", "true").lower() == "true"
)  # Safety: log orders without executing

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# PostgreSQL Configuration (Docker secrets with env fallback)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "cdb_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "cdb_user")
POSTGRES_PASSWORD = read_secret(
    "postgres_password", "POSTGRES_PASSWORD"
)  # No hardcoded default!
POSTGRES_DB = os.getenv("POSTGRES_DB", "claire_de_binare")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{quote_plus(POSTGRES_PASSWORD)}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

# Topics
TOPIC_ORDERS = "orders"  # Subscribe: Orders from Risk Manager
TOPIC_ORDER_RESULTS = "order_results"  # Publish: Execution results
STREAM_ORDER_RESULTS = os.getenv("STREAM_ORDER_RESULTS", "stream.fills")
STREAM_BOT_SHUTDOWN = os.getenv("STREAM_BOT_SHUTDOWN", "stream.bot_shutdown")

# Order Configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
ORDER_TIMEOUT_SECONDS = 10

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
