"""
Profile Manager - Verwaltet automatische Risk-Profile-Anpassungen

Überwacht Performance und wechselt automatisch zwischen:
- SAFE (konservativ)
- BASELINE (moderat)
- AGGRESSIVE (aggressiv)
"""

import logging
from datetime import datetime
from typing import Optional, List

from .models import (
    RiskProfile,
    ProfileConfig,
    PROFILE_CONFIGS,
    PerformanceMetrics,
    ProfileTransition,
)
from .performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Verwaltet Risk-Profile und automatische Anpassungen

    Workflow:
    1. Analysiert Performance über letzte 300 Trades
    2. Prüft Upgrade/Downgrade-Kriterien
    3. Wechselt Profile automatisch
    4. Loggt Transitions für Audit-Trail
    """

    def __init__(
        self,
        performance_analyzer: PerformanceAnalyzer,
        initial_profile: RiskProfile = RiskProfile.NEUTRAL,
        auto_adjust: bool = True,
    ):
        """
        Args:
            performance_analyzer: Performance Analyzer Instance
            initial_profile: Start-Profil (default: NEUTRAL)
            auto_adjust: Automatische Anpassungen aktiviert (default: True)
        """
        self.analyzer = performance_analyzer
        self.current_profile = initial_profile
        self.auto_adjust = auto_adjust
        self.transition_history: List[ProfileTransition] = []

        logger.info(
            f"ProfileManager initialized - Profile: {initial_profile.value}, "
            f"Auto-adjust: {auto_adjust}"
        )

    def get_current_config(self) -> ProfileConfig:
        """Gibt aktuelle Profile-Config zurück"""
        return PROFILE_CONFIGS[self.current_profile]

    def check_and_adjust(self) -> Optional[ProfileTransition]:
        """
        Prüft Performance und passt Profil automatisch an

        Returns:
            ProfileTransition wenn Wechsel stattfand, sonst None
        """
        if not self.auto_adjust:
            logger.debug("Auto-adjust disabled - skipping profile check")
            return None

        # Performance analysieren
        metrics = self.analyzer.analyze_recent_performance()

        if not metrics:
            logger.warning("Cannot adjust profile - no performance metrics available")
            return None

        # Entscheidung: Upgrade, Downgrade oder bleiben
        new_profile = self._decide_profile(metrics)

        if new_profile == self.current_profile:
            logger.debug(f"Profile unchanged: {self.current_profile.value}")
            return None

        # Profile wechseln
        return self._transition_to(new_profile, metrics)

    def _decide_profile(self, metrics: PerformanceMetrics) -> RiskProfile:
        """
        Entscheidet neues Profil basierend auf Performance

        Logik:
        - Bei Upgrade-Kriterien → Nächsthöheres Profil
        - Bei Downgrade-Kriterien → Nächstniedrigeres Profil
        - Bei Circuit Breaker → Direkt zu SAFE
        - Sonst → Aktuelles Profil beibehalten

        Args:
            metrics: Performance-Metriken

        Returns:
            Empfohlenes Risk-Profil
        """
        current = self.current_profile

        # Circuit Breaker → sofort zu DRY
        if metrics.circuit_breaker_events > 0:
            logger.warning(
                f"Circuit Breaker detected ({metrics.circuit_breaker_events} events) "
                f"→ Downgrade to DRY"
            )
            return RiskProfile.DRY

        # Upgrade möglich? (DRY → NEUTRAL → WET)
        if metrics.meets_upgrade_criteria():
            if current == RiskProfile.DRY:
                logger.info(
                    f"🌧️ Upgrade criteria met - DRY → NEUTRAL "
                    f"(Winrate: {metrics.winrate*100:.1f}%, "
                    f"PF: {metrics.profit_factor:.2f})"
                )
                return RiskProfile.NEUTRAL
            elif current == RiskProfile.NEUTRAL:
                logger.info(
                    f"💧 Upgrade criteria met - NEUTRAL → WET "
                    f"(Winrate: {metrics.winrate*100:.1f}%, "
                    f"PF: {metrics.profit_factor:.2f})"
                )
                return RiskProfile.WET
            else:
                # Bereits WET - bleibe
                return RiskProfile.WET

        # Downgrade nötig? (WET → NEUTRAL → DRY)
        elif metrics.meets_downgrade_criteria():
            if current == RiskProfile.WET:
                logger.warning(
                    f"☀️ Downgrade criteria met - WET → NEUTRAL "
                    f"(Winrate: {metrics.winrate*100:.1f}%, "
                    f"PF: {metrics.profit_factor:.2f})"
                )
                return RiskProfile.NEUTRAL
            elif current == RiskProfile.NEUTRAL:
                logger.warning(
                    f"🏜️ Downgrade criteria met - NEUTRAL → DRY "
                    f"(Winrate: {metrics.winrate*100:.1f}%, "
                    f"PF: {metrics.profit_factor:.2f})"
                )
                return RiskProfile.DRY
            else:
                # Bereits DRY - bleibe
                return RiskProfile.DRY

        # Keine Änderung
        else:
            logger.debug(
                f"Performance stable - keeping {current.value} "
                f"(Winrate: {metrics.winrate*100:.1f}%, "
                f"PF: {metrics.profit_factor:.2f})"
            )
            return current

    def _transition_to(
        self, new_profile: RiskProfile, metrics: PerformanceMetrics
    ) -> ProfileTransition:
        """
        Führt Profile-Wechsel durch

        Args:
            new_profile: Neues Profil
            metrics: Aktuelle Performance-Metriken

        Returns:
            ProfileTransition Event
        """
        old_profile = self.current_profile

        # Bestimme Grund
        if metrics.circuit_breaker_events > 0:
            reason = "CIRCUIT_BREAKER"
        elif new_profile.value > old_profile.value:
            reason = "UPGRADE"
        else:
            reason = "DOWNGRADE"

        # Erstelle Transition-Event
        transition = ProfileTransition(
            timestamp=datetime.now(datetime.UTC),
            from_profile=old_profile,
            to_profile=new_profile,
            reason=reason,
            metrics=metrics,
        )

        # Profile wechseln
        self.current_profile = new_profile
        self.transition_history.append(transition)

        logger.info(
            f"🔄 PROFILE TRANSITION: {old_profile.value} → {new_profile.value} "
            f"({reason}) - "
            f"Trades: {metrics.trade_count}, "
            f"Winrate: {metrics.winrate*100:.1f}%, "
            f"PF: {metrics.profit_factor:.2f}, "
            f"Drawdown: {metrics.max_drawdown_pct*100:.1f}%"
        )

        return transition

    def force_profile(self, profile: RiskProfile, reason: str = "MANUAL") -> ProfileTransition:
        """
        Erzwingt manuellen Profile-Wechsel

        Args:
            profile: Ziel-Profil
            reason: Grund für manuellen Wechsel

        Returns:
            ProfileTransition Event
        """
        if profile == self.current_profile:
            logger.info(f"Profile already {profile.value} - no change")
            return None

        # Erstelle Dummy-Metrics für manuelle Transition
        metrics = PerformanceMetrics(
            timestamp=datetime.now(datetime.UTC),
            trade_count=0,
            lookback_trades=self.analyzer.lookback_trades,
            winrate=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            total_pnl=0.0,
            avg_win=0.0,
            avg_loss=0.0,
        )

        transition = ProfileTransition(
            timestamp=datetime.now(datetime.UTC),
            from_profile=self.current_profile,
            to_profile=profile,
            reason=reason,
            metrics=metrics,
        )

        self.current_profile = profile
        self.transition_history.append(transition)

        logger.info(
            f"🔧 MANUAL PROFILE CHANGE: {transition.from_profile.value} → "
            f"{profile.value} ({reason})"
        )

        return transition

    def get_transition_history(self, limit: int = 10) -> List[ProfileTransition]:
        """
        Gibt letzte N Profile-Transitions zurück

        Args:
            limit: Max Anzahl Transitions

        Returns:
            Liste der letzten Transitions
        """
        return self.transition_history[-limit:]

    def get_status_summary(self) -> dict:
        """
        Erstellt Status-Summary für Monitoring

        Returns:
            Dict mit aktuellem Status
        """
        config = self.get_current_config()
        metrics = self.analyzer.analyze_recent_performance()

        summary = {
            "current_profile": self.current_profile.value,
            "auto_adjust": self.auto_adjust,
            "config": {
                "signal_threshold_pct": config.signal_threshold_pct,
                "rsi_threshold": config.rsi_threshold,
                "max_exposure_pct": config.max_exposure_pct,
            },
            "transitions_count": len(self.transition_history),
        }

        if metrics:
            summary["performance"] = {
                "trade_count": metrics.trade_count,
                "winrate": f"{metrics.winrate * 100:.1f}%",
                "profit_factor": f"{metrics.profit_factor:.2f}",
                "max_drawdown": f"{metrics.max_drawdown_pct * 100:.1f}%",
                "can_upgrade": metrics.meets_upgrade_criteria(),
                "needs_downgrade": metrics.meets_downgrade_criteria(),
            }

        return summary
