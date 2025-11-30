"""
Signal Engine - Main Service
Momentum-basierte Signal-Generierung
"""

import sys
import json
import time
import signal
import logging
import logging.config
import redis
from flask import Flask, jsonify, Response
from datetime import datetime
from typing import Optional
from pathlib import Path
from collections import defaultdict, deque

# Lokale Imports
try:
    from .config import config
    from .models import MarketData, Signal
except ImportError:
    from config import config
    from models import MarketData, Signal

# Logging konfigurieren via JSON-Config
logging_config_path = Path(__file__).parent.parent.parent / "logging_config.json"
if logging_config_path.exists():
    with open(logging_config_path) as f:
        logging_conf = json.load(f)
        logging.config.dictConfig(logging_conf)
else:
    # Fallback zu basicConfig wenn logging_config.json nicht gefunden
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("signal_engine")

# Flask App für Health-Check
app = Flask(__name__)

# Globale Statistiken
stats = {
    "started_at": None,
    "signals_generated": 0,
    "last_signal": None,
    "status": "initializing",
}


class SignalEngine:
    """Momentum-Signal-Engine"""

    def __init__(self):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.running = False

        # Price history für RSI-Berechnung (14 Perioden)
        self.price_history = defaultdict(lambda: deque(maxlen=15))  # 15 für RSI-14

        # Cache für dynamische Parameter (updated aus Redis)
        self.dynamic_params = {
            "threshold_pct": self.config.threshold_pct,
            "rsi_threshold": 50.0,
            "volume_multiplier": 1.0,
        }

        # Validiere Config
        try:
            self.config.validate()
            logger.info("Config validiert ✓")
        except ValueError as e:
            logger.error(f"Config-Fehler: {e}")
            sys.exit(1)

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

            # Initial: Lade dynamische Parameter
            self.update_dynamic_params()

        except redis.ConnectionError as e:
            logger.error(f"Redis-Verbindung fehlgeschlagen: {e}")
            sys.exit(1)

    def update_dynamic_params(self):
        """Holt aktuelle dynamische Parameter aus Redis (von Adaptive Intensity Service)"""
        try:
            params_json = self.redis_client.get("adaptive_intensity:current_params")

            if params_json:
                import json
                params = json.loads(params_json)

                # Update cache
                self.dynamic_params["threshold_pct"] = params.get("signal_threshold_pct", self.config.threshold_pct)
                self.dynamic_params["rsi_threshold"] = params.get("rsi_threshold", 50.0)
                self.dynamic_params["volume_multiplier"] = params.get("volume_multiplier", 1.0)

                logger.info(
                    f"🔄 Dynamic params updated: "
                    f"Threshold={self.dynamic_params['threshold_pct']:.2f}%, "
                    f"RSI={self.dynamic_params['rsi_threshold']:.1f}"
                )
            else:
                logger.debug("No dynamic params in Redis - using ENV fallback")

        except Exception as e:
            logger.warning(f"Failed to fetch dynamic params: {e} - using fallback")

    def calculate_rsi(self, symbol: str, current_price: float) -> Optional[float]:
        """
        Berechnet RSI (Relative Strength Index) für ein Symbol

        Returns:
            RSI-Wert (0-100) oder None wenn nicht genug Daten
        """
        # Aktuellen Preis zur History hinzufügen
        self.price_history[symbol].append(current_price)

        # Mindestens 14 Datenpunkte benötigt für RSI-14
        if len(self.price_history[symbol]) < 14:
            return None

        prices = list(self.price_history[symbol])

        # Preisänderungen berechnen
        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        # Durchschnittliche Gains/Losses (letzte 14 Perioden)
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14

        if avg_loss == 0:
            return 100.0  # Alle Gains, kein Loss

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def process_market_data(self, data: dict) -> Optional[Signal]:
        """
        Verarbeitet Marktdaten und generiert ggf. Signal

        Momentum-Strategie:
        - BUY wenn pct_change > threshold (DYNAMISCH aus Redis!)
        - Confidence basiert auf Stärke des Momentums
        """
        try:
            market_data = MarketData.from_dict(data)

            # Hole DYNAMISCHE Threshold (updated alle 30s von Adaptive Intensity)
            threshold = self.dynamic_params["threshold_pct"]
            rsi_threshold = self.dynamic_params["rsi_threshold"]
            volume_multiplier = self.dynamic_params["volume_multiplier"]

            # Prüfe Momentum-Schwelle (DYNAMISCH!)
            if market_data.pct_change >= threshold:
                # Volume-Check (mit dynamischem Multiplier)
                min_volume = self.config.min_volume * volume_multiplier
                if market_data.volume < min_volume:
                    logger.debug(
                        f"{market_data.symbol}: Volume zu niedrig ({market_data.volume} < {min_volume:.0f})"
                    )
                    return None

                # RSI-Check (DYNAMISCHER Threshold!)
                rsi = self.calculate_rsi(market_data.symbol, market_data.price)
                if rsi is not None and rsi <= rsi_threshold:
                    logger.debug(
                        f"{market_data.symbol}: RSI zu niedrig ({rsi:.1f} <= {rsi_threshold:.1f})"
                    )
                    return None

                # Confidence berechnen (linear mit pct_change)
                confidence = min(market_data.pct_change / 10.0, 1.0)

                # Signal generieren
                signal = Signal(
                    symbol=market_data.symbol,
                    side="BUY",
                    confidence=confidence,
                    reason=Signal.generate_reason(
                        market_data.pct_change, threshold  # Use dynamic threshold
                    ),
                    timestamp=int(time.time()),
                    price=market_data.price,
                    pct_change=market_data.pct_change,
                )

                logger.info(
                    f"✨ Signal generiert: {signal.symbol} {signal.side} @ ${signal.price:.2f} "
                    f"({signal.pct_change:+.2f}%, Confidence: {signal.confidence:.2f}, "
                    f"Threshold: {threshold:.2f}%)"
                )
                return signal

            return None

        except Exception as e:
            logger.error(f"Fehler bei Market-Data-Verarbeitung: {e}")
            return None

    def publish_signal(self, signal: Signal):
        """Publiziert Signal auf Redis"""
        try:
            message = json.dumps(signal.to_dict())
            self.redis_client.publish(self.config.output_topic, message)

            # Statistik
            stats["signals_generated"] += 1
            stats["last_signal"] = {
                "symbol": signal.symbol,
                "side": signal.side,
                "timestamp": signal.timestamp,
            }

        except Exception as e:
            logger.error(f"Fehler beim Signal-Publishing: {e}")

    def run(self):
        """Hauptschleife"""
        self.running = True
        stats["status"] = "running"
        stats["started_at"] = datetime.now().isoformat()

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
    body = (
        "# HELP signals_generated_total Anzahl generierter Signale\n"
        "# TYPE signals_generated_total counter\n"
        f"signals_generated_total {stats['signals_generated']}\n\n"
        "# HELP signal_engine_status Service Status (1=running, 0=stopped)\n"
        "# TYPE signal_engine_status gauge\n"
        f"signal_engine_status {1 if stats['status'] == 'running' else 0}\n"
    )
    return Response(body, mimetype="text/plain")


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
    from threading import Thread

    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()

    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Hauptschleife
    engine.run()
