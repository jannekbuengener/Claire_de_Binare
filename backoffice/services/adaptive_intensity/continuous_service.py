"""
Continuous Adaptive Intensity Service

Läuft kontinuierlich und updated Parameter in Echtzeit:
- Analysiert permanent die letzten 300 Trades
- Berechnet Performance Score (0.0 - 1.0)
- Updated Trading-Parameter proportional
- Broadcastet via Redis an alle Services
"""

import json
import logging
import os
import threading
import time
from typing import Optional

import redis
from flask import Flask, jsonify
from prometheus_client import Gauge, Histogram, generate_latest, REGISTRY

try:
    from .performance_analyzer import PerformanceAnalyzer
    from .dynamic_adjuster import DynamicAdjuster, DynamicParameters
except ImportError:
    from performance_analyzer import PerformanceAnalyzer
    from dynamic_adjuster import DynamicAdjuster, DynamicParameters

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Prometheus Metriken
PERFORMANCE_SCORE_GAUGE = Gauge(
    "adaptive_intensity_performance_score",
    "Current performance score (0.0 = poor, 1.0 = excellent)"
)

SIGNAL_THRESHOLD_GAUGE = Gauge(
    "adaptive_intensity_signal_threshold_pct",
    "Current dynamic signal threshold percentage"
)

RSI_THRESHOLD_GAUGE = Gauge(
    "adaptive_intensity_rsi_threshold",
    "Current dynamic RSI threshold"
)

MAX_EXPOSURE_GAUGE = Gauge(
    "adaptive_intensity_max_exposure_pct",
    "Current dynamic max exposure percentage"
)

UPDATE_DURATION = Histogram(
    "adaptive_intensity_update_duration_seconds",
    "Time spent calculating and updating parameters"
)

# Global Instances
redis_client: Optional[redis.Redis] = None
dynamic_adjuster: Optional[DynamicAdjuster] = None
current_params: Optional[DynamicParameters] = None


def init_redis():
    """Initialisiert Redis Connection"""
    global redis_client

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD")

    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        db=0,
        decode_responses=True,
    )

    # Test connection
    redis_client.ping()
    logger.info(f"✅ Redis connected: {redis_host}:{redis_port}")


def init_dynamic_adjuster():
    """Initialisiert DynamicAdjuster mit PostgreSQL-Connection"""
    global dynamic_adjuster

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

    # Dynamic Adjuster mit konfigurierbaren Ranges
    dynamic_adjuster = DynamicAdjuster(
        performance_analyzer=analyzer,
        # Score Gewichtung
        winrate_weight=float(os.getenv("ADAPTIVE_WINRATE_WEIGHT", "0.4")),
        profit_factor_weight=float(os.getenv("ADAPTIVE_PF_WEIGHT", "0.4")),
        drawdown_weight=float(os.getenv("ADAPTIVE_DD_WEIGHT", "0.2")),
        # Parameter Ranges
        threshold_range=(
            float(os.getenv("ADAPTIVE_THRESHOLD_MIN", "3.0")),
            float(os.getenv("ADAPTIVE_THRESHOLD_MAX", "1.5")),
        ),
        rsi_range=(
            float(os.getenv("ADAPTIVE_RSI_MIN", "60.0")),
            float(os.getenv("ADAPTIVE_RSI_MAX", "40.0")),
        ),
        exposure_range=(
            float(os.getenv("ADAPTIVE_EXPOSURE_MIN", "0.40")),
            float(os.getenv("ADAPTIVE_EXPOSURE_MAX", "0.80")),
        ),
        # Smooth Transitions
        max_change_per_update=float(os.getenv("ADAPTIVE_MAX_CHANGE", "0.05")),
    )

    logger.info("DynamicAdjuster initialized")


def broadcast_parameters(params: DynamicParameters):
    """
    Broadcastet dynamische Parameter via Redis

    Andere Services (Signal Engine, Risk Manager) können diese abholen.
    """
    if not redis_client:
        logger.error("Redis not initialized")
        return

    # Serialize zu JSON
    params_dict = {
        "timestamp": params.timestamp.isoformat(),
        "performance_score": params.performance_score,
        "signal_threshold_pct": params.signal_threshold_pct,
        "rsi_threshold": params.rsi_threshold,
        "volume_multiplier": params.volume_multiplier,
        "max_position_pct": params.max_position_pct,
        "max_exposure_pct": params.max_exposure_pct,
    }

    # Speichere in Redis mit 1h TTL
    redis_client.setex(
        "adaptive_intensity:current_params",
        3600,  # 1 hour TTL
        json.dumps(params_dict),
    )

    # Publish auf Channel (für Event-Driven Updates)
    redis_client.publish(
        "adaptive_intensity:updates",
        json.dumps(params_dict),
    )

    logger.debug(f"📡 Broadcasted parameters: {params}")


def update_prometheus_metrics(params: DynamicParameters, score_obj):
    """Updated Prometheus Metriken"""
    PERFORMANCE_SCORE_GAUGE.set(params.performance_score)
    SIGNAL_THRESHOLD_GAUGE.set(params.signal_threshold_pct)
    RSI_THRESHOLD_GAUGE.set(params.rsi_threshold)
    MAX_EXPOSURE_GAUGE.set(params.max_exposure_pct)


def continuous_update_loop():
    """
    Kontinuierliche Update-Loop

    Läuft in Background-Thread, updated alle N Sekunden die Parameter.
    """
    global current_params

    # Update-Interval (default: 30s)
    update_interval = int(os.getenv("ADAPTIVE_UPDATE_INTERVAL_SEC", "30"))

    logger.info(f"🔄 Starting continuous update loop (interval: {update_interval}s)")

    while True:
        try:
            with UPDATE_DURATION.time():
                # Berechne Performance Score
                score = dynamic_adjuster.calculate_performance_score()

                if not score:
                    logger.warning("No performance score - skipping update")
                    time.sleep(update_interval)
                    continue

                # Berechne dynamische Parameter
                params = dynamic_adjuster.calculate_dynamic_parameters(score)
                current_params = params

                # Broadcast via Redis
                broadcast_parameters(params)

                # Update Prometheus
                update_prometheus_metrics(params, score)

                logger.info(
                    f"✅ Parameters updated - Score: {score.score*100:.1f}%, "
                    f"Threshold: {params.signal_threshold_pct:.2f}%, "
                    f"Exposure: {params.max_exposure_pct*100:.0f}%"
                )

        except Exception as e:
            logger.error(f"Error in update loop: {e}", exc_info=True)

        # Sleep bis nächstes Update
        time.sleep(update_interval)


# === Flask Routes ===


@app.route("/health", methods=["GET"])
def health():
    """Health Check"""
    return jsonify({"status": "healthy", "service": "adaptive_intensity_continuous"}), 200


@app.route("/status", methods=["GET"])
def status():
    """Aktueller Status mit Performance Score und Parametern"""
    if not current_params:
        return jsonify({"status": "initializing", "message": "No parameters yet"}), 503

    score = dynamic_adjuster.calculate_performance_score()

    return jsonify({
        "status": "active",
        "performance_score": {
            "overall": f"{score.score * 100:.1f}%",
            "winrate": f"{score.winrate_score * 100:.1f}%",
            "profit_factor": f"{score.profit_factor_score * 100:.1f}%",
            "drawdown": f"{score.drawdown_score * 100:.1f}%",
            "interpretation": dynamic_adjuster._interpret_score(score.score),
        },
        "raw_metrics": {
            "winrate": f"{score.raw_winrate * 100:.1f}%",
            "profit_factor": f"{score.raw_profit_factor:.2f}",
            "max_drawdown": f"{score.raw_max_drawdown * 100:.1f}%",
            "trade_count": score.trade_count,
        },
        "current_parameters": {
            "signal_threshold_pct": f"{current_params.signal_threshold_pct:.2f}%",
            "rsi_threshold": f"{current_params.rsi_threshold:.1f}",
            "volume_multiplier": f"{current_params.volume_multiplier:.2f}",
            "max_position_pct": f"{current_params.max_position_pct * 100:.1f}%",
            "max_exposure_pct": f"{current_params.max_exposure_pct * 100:.0f}%",
        },
    }), 200


@app.route("/parameters", methods=["GET"])
def get_parameters():
    """GET aktuelle Parameter (für andere Services)"""
    if not current_params:
        return jsonify({"error": "No parameters available"}), 503

    return jsonify({
        "timestamp": current_params.timestamp.isoformat(),
        "performance_score": current_params.performance_score,
        "signal_engine": {
            "threshold_pct": current_params.signal_threshold_pct,
            "rsi_threshold": current_params.rsi_threshold,
            "volume_multiplier": current_params.volume_multiplier,
        },
        "risk_manager": {
            "max_position_pct": current_params.max_position_pct,
            "max_exposure_pct": current_params.max_exposure_pct,
        },
    }), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus Metrics"""
    return generate_latest(REGISTRY), 200, {"Content-Type": "text/plain"}


# === Main ===


def run_service():
    """Startet Continuous Adaptive Intensity Service"""
    # Initialisierung
    init_redis()
    init_dynamic_adjuster()

    # Starte Background Update Loop
    update_thread = threading.Thread(target=continuous_update_loop, daemon=True)
    update_thread.start()

    # Starte Flask App
    port = int(os.getenv("ADAPTIVE_PORT", "8004"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run_service()
