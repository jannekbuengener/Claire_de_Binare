"""
Adaptive Intensity Service - "Dry/Wet" Engine
Background Service für automatische Risk-Profile-Anpassung

Flask HTTP API + Background Loop:
- Überwacht Performance kontinuierlich (alle 5min)
- Passt Risk-Profile automatisch an (DRY ↔ NEUTRAL ↔ WET)
- Exposes Prometheus Metriken
- Provides REST API für Status/Control
"""

import logging
import os
import threading
import time
from typing import Optional

from flask import Flask, jsonify
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

from .models import RiskProfile, PROFILE_CONFIGS
from .performance_analyzer import PerformanceAnalyzer
from .profile_manager import ProfileManager

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Prometheus Metriken
PROFILE_GAUGE = Gauge(
    "adaptive_intensity_profile",
    "Current Risk Profile - Dry/Wet System (0=DRY, 1=NEUTRAL, 2=WET)",
)

PERFORMANCE_WINRATE = Gauge(
    "adaptive_intensity_winrate", "Current winrate over lookback window"
)

PERFORMANCE_PROFIT_FACTOR = Gauge(
    "adaptive_intensity_profit_factor", "Current profit factor"
)

PERFORMANCE_MAX_DRAWDOWN = Gauge(
    "adaptive_intensity_max_drawdown_pct", "Current max drawdown percentage"
)

PERFORMANCE_TRADE_COUNT = Gauge(
    "adaptive_intensity_analyzed_trades", "Number of trades in current analysis window"
)

PROFILE_TRANSITIONS = Counter(
    "adaptive_intensity_profile_transitions_total",
    "Total number of profile transitions",
    ["from_profile", "to_profile", "reason"],
)

CHECK_DURATION = Histogram(
    "adaptive_intensity_check_duration_seconds",
    "Time spent checking and adjusting profile",
)

# Global Profile Manager
profile_manager: Optional[ProfileManager] = None


def init_profile_manager():
    """Initialisiert ProfileManager mit PostgreSQL-Connection"""
    global profile_manager

    # PostgreSQL Config (aus ENV)
    db_config = {
        "db_host": os.getenv("POSTGRES_HOST", "localhost"),
        "db_port": int(os.getenv("POSTGRES_PORT", "5432")),
        "db_name": os.getenv("POSTGRES_DB", "claire_de_binare"),
        "db_user": os.getenv("POSTGRES_USER", "claire_user"),
        "db_password": os.getenv("POSTGRES_PASSWORD", "claire_db_secret_2024"),
        "lookback_trades": int(os.getenv("ADAPTIVE_LOOKBACK_TRADES", "300")),
    }

    # Performance Analyzer
    analyzer = PerformanceAnalyzer(**db_config)

    # Initial Profile (aus ENV oder default NEUTRAL)
    initial_profile_str = os.getenv("ADAPTIVE_INITIAL_PROFILE", "NEUTRAL")
    initial_profile = RiskProfile[initial_profile_str]

    # Auto-Adjust aktiviert? (aus ENV)
    auto_adjust = os.getenv("ADAPTIVE_AUTO_ADJUST", "true").lower() == "true"

    # ProfileManager initialisieren
    profile_manager = ProfileManager(
        performance_analyzer=analyzer,
        initial_profile=initial_profile,
        auto_adjust=auto_adjust,
    )

    logger.info(f"ProfileManager initialized - Profile: {initial_profile.value}")

    # Initial Metric setzen
    _update_metrics()


def _update_metrics():
    """Updated Prometheus Metriken basierend auf aktuellem Status"""
    if not profile_manager:
        return

    # Profile als Numeric (für Grafana Alerts) - Dry/Wet System
    profile_map = {
        RiskProfile.DRY: 0,  # Trocken/konservativ
        RiskProfile.NEUTRAL: 1,  # Neutral/balanciert
        RiskProfile.WET: 2,  # Nass/aggressiv
    }
    PROFILE_GAUGE.set(profile_map[profile_manager.current_profile])

    # Performance Metriken
    metrics = profile_manager.analyzer.analyze_recent_performance()
    if metrics:
        PERFORMANCE_WINRATE.set(metrics.winrate)
        PERFORMANCE_PROFIT_FACTOR.set(metrics.profit_factor)
        PERFORMANCE_MAX_DRAWDOWN.set(metrics.max_drawdown_pct)
        PERFORMANCE_TRADE_COUNT.set(metrics.trade_count)


def background_check_loop():
    """
    Background Loop - prüft Performance alle 5 Minuten

    Läuft in separatem Thread.
    """
    check_interval = int(os.getenv("ADAPTIVE_CHECK_INTERVAL_SEC", "300"))  # 5min

    logger.info(f"Starting background check loop (interval: {check_interval}s)")

    while True:
        try:
            with CHECK_DURATION.time():
                # Performance prüfen und Profile anpassen
                transition = profile_manager.check_and_adjust()

                if transition:
                    # Profile-Transition Counter updaten
                    PROFILE_TRANSITIONS.labels(
                        from_profile=transition.from_profile.value,
                        to_profile=transition.to_profile.value,
                        reason=transition.reason,
                    ).inc()

                # Metriken updaten
                _update_metrics()

        except Exception as e:
            logger.error(f"Error in background check loop: {e}", exc_info=True)

        # Sleep bis nächster Check
        time.sleep(check_interval)


# === Flask Routes ===


@app.route("/health", methods=["GET"])
def health():
    """Health Check Endpoint"""
    return jsonify({"status": "healthy", "service": "adaptive_intensity"}), 200


@app.route("/status", methods=["GET"])
def status():
    """Status Endpoint - zeigt aktuelles Profil und Performance"""
    if not profile_manager:
        return jsonify({"error": "ProfileManager not initialized"}), 500

    return jsonify(profile_manager.get_status_summary()), 200


@app.route("/profile", methods=["GET"])
def get_profile():
    """GET aktuelles Risk-Profil"""
    if not profile_manager:
        return jsonify({"error": "ProfileManager not initialized"}), 500

    config = profile_manager.get_current_config()

    return jsonify(
        {
            "profile": profile_manager.current_profile.value,
            "description": config.description,
            "config": {
                "signal_threshold_pct": config.signal_threshold_pct,
                "rsi_threshold": config.rsi_threshold,
                "volume_multiplier": config.volume_multiplier,
                "max_position_pct": config.max_position_pct,
                "max_exposure_pct": config.max_exposure_pct,
                "max_daily_drawdown_pct": config.max_daily_drawdown_pct,
            },
        }
    ), 200


@app.route("/profile/<profile_name>", methods=["POST"])
def set_profile(profile_name: str):
    """POST - manuell Profil setzen"""
    if not profile_manager:
        return jsonify({"error": "ProfileManager not initialized"}), 500

    try:
        # Validate profile name
        new_profile = RiskProfile[profile_name.upper()]
    except KeyError:
        return jsonify(
            {
                "error": f"Invalid profile: {profile_name}",
                "valid_profiles": [p.value for p in RiskProfile],
            }
        ), 400

    # Force profile change
    transition = profile_manager.force_profile(new_profile, reason="MANUAL_API")

    if transition:
        # Update Metric
        PROFILE_TRANSITIONS.labels(
            from_profile=transition.from_profile.value,
            to_profile=transition.to_profile.value,
            reason=transition.reason,
        ).inc()
        _update_metrics()

        return jsonify(
            {
                "status": "profile_changed",
                "from_profile": transition.from_profile.value,
                "to_profile": transition.to_profile.value,
            }
        ), 200
    else:
        return jsonify(
            {
                "status": "no_change",
                "current_profile": profile_manager.current_profile.value,
            }
        ), 200


@app.route("/transitions", methods=["GET"])
def get_transitions():
    """GET - letzte Profile-Transitions"""
    if not profile_manager:
        return jsonify({"error": "ProfileManager not initialized"}), 500

    transitions = profile_manager.get_transition_history(limit=10)

    return jsonify(
        {
            "count": len(transitions),
            "transitions": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "from_profile": t.from_profile.value,
                    "to_profile": t.to_profile.value,
                    "reason": t.reason,
                    "metrics": {
                        "winrate": f"{t.metrics.winrate * 100:.1f}%",
                        "profit_factor": f"{t.metrics.profit_factor:.2f}",
                        "max_drawdown": f"{t.metrics.max_drawdown_pct * 100:.1f}%",
                        "trade_count": t.metrics.trade_count,
                    },
                }
                for t in transitions
            ],
        }
    ), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus Metrics Endpoint"""
    return generate_latest(REGISTRY), 200, {"Content-Type": "text/plain"}


# === Main ===


def run_service():
    """Startet Adaptive Intensity Service"""
    # Initialisiere ProfileManager
    init_profile_manager()

    # Starte Background Loop in separatem Thread
    background_thread = threading.Thread(target=background_check_loop, daemon=True)
    background_thread.start()

    # Starte Flask App
    port = int(os.getenv("ADAPTIVE_PORT", "8004"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run_service()
