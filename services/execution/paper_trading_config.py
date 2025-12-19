"""
Paper Trading Configuration
Realistic market simulation parameters
"""

import os
from dataclasses import dataclass
from typing import Dict


@dataclass
class PaperTradingConfig:
    """Configuration for paper trading simulation"""

    # Execution simulation
    success_rate: float = float(os.getenv("PAPER_SUCCESS_RATE", "0.95"))
    min_latency_ms: int = int(os.getenv("PAPER_MIN_LATENCY_MS", "50"))
    max_latency_ms: int = int(os.getenv("PAPER_MAX_LATENCY_MS", "200"))

    # Slippage (percentage as decimal)
    min_slippage_pct: float = float(os.getenv("PAPER_MIN_SLIPPAGE_PCT", "0.05"))  # 0.05%
    max_slippage_pct: float = float(os.getenv("PAPER_MAX_SLIPPAGE_PCT", "0.3"))   # 0.3%

    # Trading fees (percentage as decimal)
    taker_fee_pct: float = float(os.getenv("PAPER_TAKER_FEE_PCT", "0.1"))  # 0.1%
    maker_fee_pct: float = float(os.getenv("PAPER_MAKER_FEE_PCT", "0.05")) # 0.05%

    # Partial fills
    partial_fill_probability: float = float(os.getenv("PAPER_PARTIAL_FILL_PROB", "0.10"))  # 10%
    min_fill_ratio: float = float(os.getenv("PAPER_MIN_FILL_RATIO", "0.3"))  # 30% min
    max_fill_ratio: float = float(os.getenv("PAPER_MAX_FILL_RATIO", "0.9"))  # 90% max

    # Asset base prices (for simulation)
    asset_prices: Dict[str, float] = None

    def __post_init__(self):
        """Initialize asset prices"""
        if self.asset_prices is None:
            self.asset_prices = {
                "BTCUSDT": 95000.0,   # Current BTC price
                "ETHUSDT": 3500.0,    # Current ETH price
                "SOLUSDT": 180.0,     # Current SOL price
                "BNBUSDT": 620.0,     # BNB
                "ADAUSDT": 1.05,      # Cardano
                "DOGEUSDT": 0.38,     # Dogecoin
                "XRPUSDT": 2.45,      # Ripple
                "DOTUSDT": 9.2,       # Polkadot
                "MATICUSDT": 1.15,    # Polygon
                "LINKUSDT": 23.5,     # Chainlink
            }

    def get_base_price(self, symbol: str) -> float:
        """
        Get base price for symbol

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')

        Returns:
            Base price for simulation
        """
        return self.asset_prices.get(symbol, 100.0)  # Default fallback

    def validate(self) -> bool:
        """Validate configuration"""
        if not (0.0 <= self.success_rate <= 1.0):
            raise ValueError("success_rate must be between 0 and 1")

        if self.min_latency_ms < 0 or self.max_latency_ms < self.min_latency_ms:
            raise ValueError("Invalid latency configuration")

        if self.min_slippage_pct < 0 or self.max_slippage_pct < self.min_slippage_pct:
            raise ValueError("Invalid slippage configuration")

        if not (0.0 <= self.partial_fill_probability <= 1.0):
            raise ValueError("partial_fill_probability must be between 0 and 1")

        if not (0.0 < self.min_fill_ratio < self.max_fill_ratio <= 1.0):
            raise ValueError("Invalid fill ratio configuration")

        return True


# Global config instance
paper_config = PaperTradingConfig()
