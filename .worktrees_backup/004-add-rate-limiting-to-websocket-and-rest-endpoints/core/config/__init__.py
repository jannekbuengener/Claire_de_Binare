"""
Core configuration module for Claire de Binare.
"""

from .trading_mode import TradingMode, get_trading_mode, validate_trading_mode
from .rate_limits import (
    RateLimitConfig,
    RESTRateLimitConfig,
    WebSocketRateLimitConfig,
    get_rate_limit_config,
    get_rest_rate_limit_config,
    get_websocket_rate_limit_config,
    get_cached_rate_limit_config,
    is_rate_limiting_enabled,
    reset_cached_config,
)

__all__ = [
    # Trading mode
    "TradingMode",
    "get_trading_mode",
    "validate_trading_mode",
    # Rate limiting
    "RateLimitConfig",
    "RESTRateLimitConfig",
    "WebSocketRateLimitConfig",
    "get_rate_limit_config",
    "get_rest_rate_limit_config",
    "get_websocket_rate_limit_config",
    "get_cached_rate_limit_config",
    "is_rate_limiting_enabled",
    "reset_cached_config",
]
