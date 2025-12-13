"""
Configuration for Execution Service
Claire de Binare Trading Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Service Info
SERVICE_NAME = "execution_service"
SERVICE_VERSION = "0.1.0"
SERVICE_PORT = 8003

# MEXC API Configuration
MEXC_API_KEY = os.getenv("MEXC_API_KEY", "")
MEXC_API_SECRET = os.getenv("MEXC_API_SECRET", "")
MEXC_BASE_URL = os.getenv("MEXC_BASE_URL", "https://contract.mexc.com")
MEXC_TESTNET = os.getenv("MEXC_TESTNET", "true").lower() == "true"

# Trading Mode
MOCK_TRADING = os.getenv("MOCK_TRADING", "true").lower() == "true"

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

# Order Configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
ORDER_TIMEOUT_SECONDS = 10

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
