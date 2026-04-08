"""
Signal Engine - Main Service
Momentum-basierte Signal-Generierung
"""

import os
import sys
import json
import time
import signal
import logging
import logging.config
import redis
import importlib.util

try:
    _FLASK_AVAILABLE = importlib.util.find_spec("flask") is not None
except ModuleNotFoundError as e:
    if e.name == "flask" or (e.name and e.name.startswith("flask.")):
        _FLASK_AVAILABLE = False
    else:
        raise
except ValueError:
    _FLASK_AVAILABLE = False
from typing import Optional
from pathlib import Path

import psycopg2
import psycopg2.extensions

from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_signal
from core.utils.uuid_gen import (
    generate_uuid_hex,
    compute_correlation_id,
    compute_event_pk,
)

try:
    from .config import config
    from .models import MarketData, Signal
    from .price_buffer import PriceBuffer
except ImportError:
    # Fallback for script/importlib execution: ensure repo root is on sys.path.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from services.signal.config import config
    from services.signal.models import MarketData, Signal
    from services.signal.price_buffer import PriceBuffer

# Logging konfigurieren via JSON-Config
logging_config_path = Path(__file__).parent.parent.parent / "logging_config.json"
if logging_config_path.exists():
    with open(logging_config_path) as f:
        logging_conf = json.load(f)
        logging.config.dictConfig(logging_conf)
else:
    # Fallback zu basicConfig wenn logging_config.json nicht gefunden
    # Respect LOG_LEVEL env var (Issue #347 - Dev vs Prod logging policy)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("signal_engine")

# Globale Statistiken
stats = {
    "started_at": None,
    "signals_generated": 0,
    "last_signal": None,
    "status": "initializing",
    # Sprint 1 #622: Latency + Error Tracking
    "latency_samples": [],  # List of latency values (ms) for histogram
    "latency_sum_ms": 0.0,  # Total latency for avg calculation
    "latency_count": 0,  # Number of processed messages
    "errors_total": 0,  # Total errors
    "errors_by_type": {},  # Errors grouped by error type
}


def _compact_metadata(value):
    if isinstance(value, dict):
        compacted = {}
        for key, item in value.items():
            if item is None:
                continue
            nested = _compact_metadata(item)
            if nested in (None, {}, []):
                continue
            compacted[key] = nested
        return compacted
    return value


def _build_signal_metadata(signal: Signal) -> dict:
    return _compact_metadata(
        {
            "strategy_id": signal.strategy_id,
            "bot_id": signal.bot_id,
            "signal_reason": signal.reason,
            "signal_inputs": {
                "price": signal.price,
                "pct_change": signal.pct_change,
                "pct_change_15m": signal.pct_change_15m,
                "volume_15m": signal.volume_15m,
            },
            "timing": {
                "signal_ts_ms": signal.ts_ms,
            },
        }
    )


class SignalEngine:
    """Momentum-Signal-Engine"""

    def __init__(self):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.running = False
        self.price_buffer = (
            PriceBuffer()
        )  # Stateful pct_change calculation (Issue #345)
        self._pg_conn: Optional[psycopg2.extensions.connection] = None  # Phase 8C

        # Validiere Config
        try:
            self.config.validate()
            logger.info("Config validiert ✓")
        except ValueError as e:
            logger.error(f"Config-Fehler: {e}")
            sys.exit(1)

    def _get_postgres_conn(self) -> Optional[psycopg2.extensions.connection]:
        """Get or create Postgres connection for correlation_ledger writes."""
        try:
            if self._pg_conn is None or self._pg_conn.closed:
                self._pg_conn = psycopg2.connect(
                    host=self.config.postgres_host,
                    port=self.config.postgres_port,
                    database=self.config.postgres_db,
                    user=self.config.postgres_user,
                    password=self.config.postgres_password,
                )
                self._pg_conn.autocommit = True
            return self._pg_conn
        except Exception as e:
            logger.error(f"❌ Failed to connect Postgres for correlation_ledger: {e}")
            self._pg_conn = None
            return None

    def _persist_correlation_event(self, signal: "Signal", *, event_type: str) -> bool:
        """
        Persist SIGNAL event to correlation_ledger (Phase 8C).

        Fail-closed: If signal_id missing, raises ValueError.
        ON CONFLICT (event_pk) DO NOTHING for idempotent writes.
        """
        if not signal.signal_id:
            raise ValueError(
                "signal_id is required for correlation_ledger (fail-closed)"
            )

        try:
            correlation_id = compute_correlation_id(signal.signal_id)
            event_pk = compute_event_pk(signal.signal_id, event_type)

            conn = self._get_postgres_conn()
            if conn is None:
                logger.warning("⚠️ correlation_ledger write skipped (no DB connection)")
                return False

            cursor = conn.cursor()
            cursor.execute("SET LOCAL statement_timeout = '250ms'")
            cursor.execute(
                """
                INSERT INTO correlation_ledger
                    (event_pk, correlation_id, signal_id, decision_id, order_id, fill_id,
                     event_type, symbol, timestamp_ms, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_pk) DO NOTHING
                """,
                (
                    event_pk,
                    correlation_id,
                    signal.signal_id,
                    None,  # decision_id (not applicable for SIGNAL)
                    None,  # order_id (not applicable for SIGNAL)
                    None,  # fill_id (not applicable for SIGNAL)
                    event_type,
                    signal.symbol,
                    signal.ts_ms,
                    json.dumps(signal.to_dict()),
                ),
            )
            logger.debug(f"📊 correlation_ledger SIGNAL: {signal.signal_id}")
            return True
        except Exception as e:
            logger.error(f"❌ correlation_ledger write failed: {e}")
            return False

    def connect_redis(self):
        """Verbindung zu Redis herstellen"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                db=self.config.redis_db,
                decode_responses=True,
            )
            # Verbindung testen
            self.redis_client.ping()
            logger.info(
                f"Redis verbunden: {self.config.redis_host}:{self.config.redis_port}"
            )

            # Pub/Sub initialisieren
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.config.input_topic)
            logger.info(f"Subscribed zu Topic: {self.config.input_topic}")

        except redis.ConnectionError as e:
            logger.error(f"Redis-Verbindung fehlgeschlagen: {e}")
            sys.exit(1)

    def process_market_data(self, data: dict) -> Optional[Signal]:
        """
        Verarbeitet Marktdaten und generiert ggf. Signal

        Momentum-Strategie:
        - BUY wenn pct_change > threshold
        """
        # Sprint 1 #622: Track processing latency
        start_time = time.time()

        try:
            market_data = MarketData.from_dict(data)

            # Calculate pct_change if missing (raw trade data from cdb_ws)
            # Issue #345: Stateful calculation using price history buffer
            if market_data.pct_change is None:
                market_data.pct_change = self.price_buffer.calculate_pct_change(
                    market_data.symbol, market_data.price
                )
                logger.debug(
                    f"{market_data.symbol}: pct_change calculated from price buffer "
                    f"(@ ${market_data.price:.2f} → {market_data.pct_change:+.4f}%)"
                )

            # Prüfe Momentum-Schwelle
            if market_data.pct_change >= self.config.threshold_pct:
                # Volume-Check
                if market_data.volume < self.config.min_volume:
                    logger.debug(
                        f"{market_data.symbol}: Volume zu niedrig ({market_data.volume})"
                    )
                    return None

                # Signal generieren
                now_ms = int(time.time() * 1000)
                signal = Signal(
                    signal_id=f"sig-{generate_uuid_hex(length=32)}",
                    symbol=market_data.symbol,
                    side="BUY",
                    reason=f"Momentum: {market_data.pct_change:+.4f}% > {self.config.threshold_pct}%",
                    timestamp=now_ms // 1000,
                    ts_ms=now_ms,
                    price=market_data.price,
                    pct_change=market_data.pct_change,
                    pct_change_15m=market_data.pct_change,
                    volume_15m=market_data.volume,
                    strategy_id=self.config.strategy_id,
                    bot_id=self.config.bot_id,
                )
                signal.metadata = _build_signal_metadata(signal)

                logger.info(
                    f"✨ Signal generiert: {signal.symbol} {signal.side} @ ${signal.price:.2f} "
                    f"({signal.pct_change:+.2f}%)"
                )

                # Sprint 1 #622: Record latency for successful signal generation
                latency_ms = (time.time() - start_time) * 1000
                self._record_latency(latency_ms)

                return signal

            # Sprint 1 #622: Record latency even when no signal generated
            latency_ms = (time.time() - start_time) * 1000
            self._record_latency(latency_ms)
            return None

        except Exception as e:
            logger.error(f"Fehler bei Market-Data-Verarbeitung: {e}")

            # Sprint 1 #622: Track errors
            self._record_error(type(e).__name__)

            # Still record latency for failed processing
            latency_ms = (time.time() - start_time) * 1000
            self._record_latency(latency_ms)

            return None

    def _record_latency(self, latency_ms: float):
        """
        Record processing latency for metrics.

        Sprint 1 #622: Track signal_processing_latency_ms
        """
        stats["latency_samples"].append(latency_ms)
        stats["latency_sum_ms"] += latency_ms
        stats["latency_count"] += 1

        # Keep only last 1000 samples to avoid memory bloat
        if len(stats["latency_samples"]) > 1000:
            stats["latency_samples"].pop(0)

    def _record_error(self, error_type: str):
        """
        Record error for metrics.

        Sprint 1 #622: Track signal_errors_total by error type
        """
        stats["errors_total"] += 1

        if error_type not in stats["errors_by_type"]:
            stats["errors_by_type"][error_type] = 0
        stats["errors_by_type"][error_type] += 1

    def publish_signal(self, signal: Signal):
        """Publiziert Signal auf Redis + correlation_ledger (Phase 8C)"""
        try:
            # Phase 8C: Persist SIGNAL event to correlation_ledger
            # ValueError (missing signal_id) = fail-closed (bubble up)
            # DB errors = warn-only (evidence debt, don't block trading)
            if not self._persist_correlation_event(signal, event_type="SIGNAL"):
                logger.warning(
                    f"⚠️ correlation_ledger write failed for {signal.signal_id} (evidence debt)"
                )

            # Sanitize payload (Issue #349: None-filtering + contract v1.0 enforcement)
            sanitized = sanitize_signal(signal.to_dict())
            message = json.dumps(sanitized)
            self.redis_client.publish(self.config.output_topic, message)
            if self.redis_client:
                self.redis_client.xadd(
                    self.config.output_stream, sanitized, maxlen=10000
                )

            # Statistik
            stats["signals_generated"] += 1
            stats["last_signal"] = {
                "symbol": signal.symbol,
                "side": signal.side,
                "timestamp": signal.timestamp,
            }

        except ValueError:
            # Phase 8C: missing signal_id = fail-closed (bubble up)
            raise
        except Exception as e:
            logger.error(f"Fehler beim Signal-Publishing: {e}")

    def run(self):
        """Hauptschleife"""
        self.running = True
        stats["status"] = "running"
        stats["started_at"] = utcnow().isoformat()

        logger.info("🚀 Signal-Engine gestartet")
        logger.info(f"   Schwelle: {self.config.threshold_pct}%")
        logger.info(f"   Lookback: {self.config.lookback_minutes}min")
        logger.info(f"   Min. Volume: {self.config.min_volume}")

        try:
            for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])

                        # Signal generieren
                        signal = self.process_market_data(data)

                        # Falls Signal generiert, publizieren
                        if signal:
                            self.publish_signal(signal)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Ungültiges JSON: {e}")
                    except Exception as e:
                        logger.error(f"Fehler in Hauptschleife: {e}")

        except KeyboardInterrupt:
            logger.info("Shutdown via Keyboard")
        finally:
            self.shutdown()

    def shutdown(self):
        """Graceful Shutdown"""
        logger.info("Shutdown Signal-Engine...")
        self.running = False
        stats["status"] = "stopped"

        if self.pubsub:
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()

        logger.info("Signal-Engine gestoppt ✓")


# ===== FLASK ENDPOINTS =====

if _FLASK_AVAILABLE:
    from flask import Flask, jsonify, Response

    app = Flask(__name__)

    @app.route("/health")
    def health():
        """Health-Check Endpoint"""
        return jsonify(
            {
                "status": "ok" if stats["status"] == "running" else "error",
                "service": "signal_engine",
                "version": "0.1.0",
            }
        )

    @app.route("/status")
    def status():
        """Status & Statistiken"""
        return jsonify(stats)

    @app.route("/metrics")
    def metrics():
        """Prometheus Metriken (text/plain)"""
        # Sprint 1 #622: Extended metrics with latency histogram and error counter

        # Calculate histogram buckets for latency
        buckets = [1, 5, 10, 25, 50, 100, 250, 500, 1000]
        latency_buckets = {b: 0 for b in buckets}
        latency_buckets["+Inf"] = 0

        for sample in stats["latency_samples"]:
            for bucket in buckets:
                if sample <= bucket:
                    latency_buckets[bucket] += 1
            latency_buckets["+Inf"] += 1

        # Build histogram output
        histogram_lines = []
        cumulative = 0
        for bucket in buckets + ["+Inf"]:
            if bucket == "+Inf":
                cumulative = latency_buckets["+Inf"]
            else:
                cumulative += latency_buckets[bucket]
            histogram_lines.append(
                f'signal_processing_latency_ms_bucket{{le="{bucket}"}} {cumulative}'
            )

        histogram_lines.append(
            f"signal_processing_latency_ms_sum {stats['latency_sum_ms']}"
        )
        histogram_lines.append(
            f"signal_processing_latency_ms_count {stats['latency_count']}"
        )

        # Build error counter with labels
        error_lines = []
        for error_type, count in stats["errors_by_type"].items():
            error_lines.append(
                f'signal_errors_total{{error_type="{error_type}"}} {count}'
            )

        body = (
            "# HELP signals_generated_total Anzahl generierter Signale\n"
            "# TYPE signals_generated_total counter\n"
            f"signals_generated_total {stats['signals_generated']}\n\n"
            "# HELP signal_engine_status Service Status (1=running, 0=stopped)\n"
            "# TYPE signal_engine_status gauge\n"
            f"signal_engine_status {1 if stats['status'] == 'running' else 0}\n\n"
            "# HELP signal_processing_latency_ms Signal processing latency in milliseconds\n"
            "# TYPE signal_processing_latency_ms histogram\n"
            + "\n".join(histogram_lines)
            + "\n\n"
            "# HELP signal_errors_total Total signal processing errors\n"
            "# TYPE signal_errors_total counter\n"
            + ("\n".join(error_lines) if error_lines else "signal_errors_total 0")
            + "\n"
        )
        return Response(body, mimetype="text/plain")

else:
    app = None


# ===== SIGNAL HANDLER =====


def signal_handler(signum, frame):
    """Signal-Handler für SIGTERM/SIGINT"""
    logger.warning(f"Signal empfangen: {signum}")
    engine.shutdown()
    sys.exit(0)


# ===== MAIN =====

if __name__ == "__main__":
    # Signal-Handler
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Engine initialisieren
    engine = SignalEngine()
    engine.connect_redis()

    # Flask in separatem Thread starten
    if not _FLASK_AVAILABLE or app is None:
        raise RuntimeError(
            "Flask ist nicht installiert. HTTP-Endpoints (health/status/metrics) "
            "benötigen Flask als optionale Abhängigkeit: pip install flask"
        )
    from threading import Thread

    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()

    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Hauptschleife
    engine.run()
