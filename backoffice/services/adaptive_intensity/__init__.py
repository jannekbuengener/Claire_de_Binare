"""
Adaptive Intensity System - Claire de Binare "Dry/Wet" Engine

Automatische Anpassung der Trading-Aggressivität basierend auf Performance der letzten 300 Trades.

Performance-Gates:
- Winrate über letzte 300 Trades
- Max Drawdown
- Profit Factor
- Circuit Breaker Events

Risk Profiles - "Dry/Wet" System:
- DRY: threshold=3.0%, rsi>60, conservative (weniger Trades, sicherer)
- NEUTRAL: threshold=2.0%, rsi>50, moderate (balanciert)
- WET: threshold=1.5%, rsi>40, aggressive (mehr Trades, höhere Frequenz)

DRY = Mehr Bodenhaftung (controlled, grip, safer)
WET = Fließen lassen (flowing, liquid, higher frequency)
"""

from .models import RiskProfile, PerformanceMetrics
from .performance_analyzer import PerformanceAnalyzer
from .profile_manager import ProfileManager

__all__ = [
    "RiskProfile",
    "PerformanceMetrics",
    "PerformanceAnalyzer",
    "ProfileManager",
]
