"""
Risk Manager - Main Service
Multi-Layer Risk Management
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
from threading import Thread, Event

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - handled gracefully in runtime
    psycopg2 = None
    RealDictCursor = None

try:
    from .config import config
    from .models import Signal, Order, Alert, RiskState, OrderResult
except ImportError:
    from config import config
    from models import Signal, Order, Alert, RiskState, OrderResult

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

logger = logging.getLogger("risk_manager")

# Flask App
app = Flask(__name__)

# Globale Stats
stats = {
    "started_at": None,
    "signals_received": 0,
    "orders_approved": 0,
    "orders_blocked": 0,
    "alerts_generated": 0,
    "order_results_received": 0,
    "orders_rejected_execution": 0,
    "last_order_result": None,
    "status": "initializing",
    "risk_state_inconsistency_total": 0,
    "risk_state_resync_total": 0,
    "risk_state_recovery_total": 0,
}

# Risk-State
risk_state = RiskState()


class RiskManager:
    """Multi-Layer Risk-Management"""

    def __init__(self):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.pubsub_results: Optional[redis.client.PubSub] = None
        self._order_result_thread: Optional[Thread] = None
        self._heal_thread: Optional[Thread] = None
        self._heal_stop_event: Event = Event()
        self.running = False

        # Cache für dynamische Parameter (updated aus Redis)
        self.dynamic_params = {
            "max_position_pct": self.config.max_position_pct,
            "max_exposure_pct": self.config.max_exposure_pct,
        }

        # Validiere Config
        try:
            self.config.validate()
            logger.info("Config validiert ✓")
        except ValueError as e:
            logger.error(f"Config-Fehler: {e}")
            sys.exit(1)

    # =========================================================================
    # DB (Source of Truth)
    # =========================================================================

    def _postgres_available(self) -> bool:
        if psycopg2 is None:
            logger.warning("psycopg2 nicht installiert - DB-Sync deaktiviert")
            return False
        return True

    def _get_db_connection(self):
        """Create a new Postgres connection (caller closes)."""
        return psycopg2.connect(
            host=self.config.postgres_host,
            port=self.config.postgres_port,
            dbname=self.config.postgres_db,
            user=self.config.postgres_user,
            password=self.config.postgres_password,
        )

    def _fetch_latest_snapshot(self) -> Optional[dict]:
        """Fetch the latest portfolio snapshot from Postgres."""
        if not self._postgres_available():
            return None
        try:
            with self._get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            total_equity,
                            available_balance,
                            daily_pnl,
                            total_exposure_pct,
                            open_positions,
                            timestamp
                        FROM portfolio_snapshots
                        ORDER BY timestamp DESC
                        LIMIT 1
                        """
                    )
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception as exc:
            logger.warning("DB-Snapshot konnte nicht geladen werden: %s", exc)
            return None

    @staticmethod
    def _normalize_exposure_pct(raw_value: float) -> float:
        try:
            value = float(raw_value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if value < 0:
            return 0.0
        if value > 1:
            return value / 100.0
        return value

    def _apply_db_snapshot_to_state(self, snapshot: dict) -> float:
        """Apply DB snapshot to in-memory risk_state. Returns derived exposure."""
        equity = float(snapshot.get("total_equity") or snapshot.get("equity") or 0.0)
        exposure_pct = self._normalize_exposure_pct(snapshot.get("total_exposure_pct"))
        exposure_value = equity * exposure_pct

        risk_state.total_exposure = exposure_value
        risk_state.daily_pnl = float(snapshot.get("daily_pnl") or 0.0)
        risk_state.open_positions = int(snapshot.get("open_positions") or 0)
        risk_state.positions = {}
        risk_state.last_prices = {}
        risk_state.pending_orders = 0
        # leave circuit_breaker_active/signals counters untouched on sync
        return exposure_value

    def _read_redis_state(self) -> Optional[dict]:
        """Read persisted state from Redis without mutating local state."""
        try:
            data = self.redis_client.get("risk_state:persistence")
            return json.loads(data) if data else None
        except Exception as exc:
            logger.warning("Redis-State konnte nicht gelesen werden: %s", exc)
            return None

    def perform_startup_sync(self):
        """Sync DB -> RiskState -> Redis on startup, favoring DB as truth."""
        db_snapshot = self._fetch_latest_snapshot()
        if not db_snapshot:
            logger.warning(
                "Kein Portfolio-Snapshot in DB gefunden - starte mit frischem State"
            )
            return

        db_exposure = self._apply_db_snapshot_to_state(db_snapshot)
        redis_state = self._read_redis_state()
        redis_exposure = 0.0
        if redis_state:
            redis_exposure = float(redis_state.get("total_exposure") or 0.0)

        drift = 0.0
        if db_exposure or redis_exposure:
            denominator = db_exposure if db_exposure != 0 else max(redis_exposure, 1.0)
            drift = abs(redis_exposure - db_exposure) / denominator

        if drift > 0.05:
            stats["risk_state_inconsistency_total"] += 1
            stats["risk_state_resync_total"] += 1
            logger.warning(
                "RESET REDIS - DB in control (startup). db_exposure=%.2f redis_exposure=%.2f drift=%.3f",
                db_exposure,
                redis_exposure,
                drift,
            )
            self.save_risk_state_to_redis()
        else:
            logger.info(
                "Startup-Sync erfolgreich: DB-Exposure=%.2f, Redis-Exposure=%.2f, Drift=%.3f",
                db_exposure,
                redis_exposure,
                drift,
            )
            # Optional soft refresh to Redis if none existed
            if redis_state is None:
                self.save_risk_state_to_redis()

    def _auto_heal_tick(self):
        """Single heal tick comparing DB truth vs Redis cache."""
        db_snapshot = self._fetch_latest_snapshot()
        if not db_snapshot:
            logger.debug("Auto-Heal: kein DB-Snapshot gefunden")
            return

        db_exposure = self._apply_db_snapshot_to_state(db_snapshot)
        redis_state = self._read_redis_state()
        redis_exposure = (
            float(redis_state.get("total_exposure") or 0.0) if redis_state else 0.0
        )

        denominator = db_exposure if db_exposure != 0 else max(redis_exposure, 1.0)
        drift = abs(redis_exposure - db_exposure) / denominator if denominator else 0.0

        if drift > 0.05:
            stats["risk_state_inconsistency_total"] += 1
            stats["risk_state_recovery_total"] += 1
            logger.warning(
                "State mismatch: triggering DB->Redis recovery. db_exposure=%.2f redis_exposure=%.2f drift=%.3f",
                db_exposure,
                redis_exposure,
                drift,
            )
            self.save_risk_state_to_redis()
        else:
            logger.debug(
                "Auto-Heal Check OK: db_exposure=%.2f redis_exposure=%.2f drift=%.3f",
                db_exposure,
                redis_exposure,
                drift,
            )

    def _start_heal_loop(self, interval_seconds: int = 30):
        """Start background auto-heal loop."""
        if self._heal_thread and self._heal_thread.is_alive():
            return

        def _loop():
            while not self._heal_stop_event.is_set():
                try:
                    self._auto_heal_tick()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Auto-Heal Fehler: %s", exc)
                self._heal_stop_event.wait(interval_seconds)

        self._heal_thread = Thread(target=_loop, daemon=True)
        self._heal_thread.start()

    def connect_redis(self):
        """Redis-Verbindung"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                db=self.config.redis_db,
                decode_responses=True,
            )
            self.redis_client.ping()
            logger.info(
                f"Redis verbunden: {self.config.redis_host}:{self.config.redis_port}"
            )

            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.config.input_topic)
            logger.info(f"Subscribed zu Topic: {self.config.input_topic}")

            self.pubsub_results = self.redis_client.pubsub()
            self.pubsub_results.subscribe(self.config.input_topic_order_results)
            logger.info(
                f"Subscribed zu Order-Result Topic: {self.config.input_topic_order_results}"
            )

            # Risk-State Sync: DB -> Redis (Truth), Redis als Cache
            self.perform_startup_sync()

            # Initial: Lade dynamische Parameter
            self.update_dynamic_params()

            # Auto-Healing aktivieren
            self._start_heal_loop()

        except redis.ConnectionError as e:
            logger.error(f"Redis-Verbindung fehlgeschlagen: {e}")
            sys.exit(1)

    def load_risk_state_from_redis(self):
        """Lädt risk_state aus Redis (Persistence bei Restart). Returns dict or None."""
        global risk_state
        try:
            state_data = self.redis_client.get("risk_state:persistence")
            if state_data:
                state_dict = json.loads(state_data)
                risk_state.total_exposure = state_dict.get("total_exposure", 0.0)
                risk_state.daily_pnl = state_dict.get("daily_pnl", 0.0)
                risk_state.open_positions = state_dict.get("open_positions", 0)
                risk_state.signals_blocked = state_dict.get("signals_blocked", 0)
                risk_state.signals_approved = state_dict.get("signals_approved", 0)
                risk_state.circuit_breaker_active = state_dict.get(
                    "circuit_breaker_active", False
                )
                risk_state.positions = state_dict.get("positions", {})
                risk_state.pending_orders = state_dict.get("pending_orders", 0)
                risk_state.last_prices = state_dict.get("last_prices", {})
                logger.info(
                    f"Risk-State aus Redis geladen: Exposure={risk_state.total_exposure:.2f}, "
                    f"Positions={risk_state.open_positions}, PnL={risk_state.daily_pnl:.2f}"
                )
                return state_dict
            else:
                logger.info(
                    "Kein persistierter Risk-State gefunden - starte mit frischem State"
                )
                return None
        except Exception as e:
            logger.warning(
                f"Risk-State-Load fehlgeschlagen: {e} - verwende frischen State"
            )
            return None

    def save_risk_state_to_redis(self):
        """Speichert risk_state in Redis mit 7-Tage TTL"""
        try:
            state_dict = {
                "total_exposure": risk_state.total_exposure,
                "daily_pnl": risk_state.daily_pnl,
                "open_positions": risk_state.open_positions,
                "signals_blocked": risk_state.signals_blocked,
                "signals_approved": risk_state.signals_approved,
                "circuit_breaker_active": risk_state.circuit_breaker_active,
                "positions": risk_state.positions,
                "pending_orders": risk_state.pending_orders,
                "last_prices": risk_state.last_prices,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.redis_client.setex(
                "risk_state:persistence",
                7 * 24 * 60 * 60,  # 7 Tage TTL
                json.dumps(state_dict),
            )
            logger.info(
                f"💾 Risk-State → Redis: Exposure={risk_state.total_exposure:.2f}, "
                f"Pos={risk_state.open_positions}, Approved={risk_state.signals_approved}"
            )
        except Exception as e:
            logger.error(f"❌ Risk-State-Save fehlgeschlagen: {e}")

    def update_dynamic_params(self):
        """Holt aktuelle dynamische Parameter aus Redis (von Adaptive Intensity Service)"""
        try:
            params_json = self.redis_client.get("adaptive_intensity:current_params")

            if params_json:
                import json
                params = json.loads(params_json)

                # Update cache
                self.dynamic_params["max_position_pct"] = params.get(
                    "max_position_pct", self.config.max_position_pct
                )
                self.dynamic_params["max_exposure_pct"] = params.get(
                    "max_exposure_pct", self.config.max_exposure_pct
                )

                logger.info(
                    f"🔄 Dynamic params updated: "
                    f"Max Position={self.dynamic_params['max_position_pct']*100:.1f}%, "
                    f"Max Exposure={self.dynamic_params['max_exposure_pct']*100:.1f}%"
                )
            else:
                logger.debug("No dynamic params in Redis - using ENV fallback")

        except Exception as e:
            logger.warning(f"Failed to fetch dynamic params: {e} - using fallback")

    def check_position_limit(self, signal: Signal) -> tuple[bool, str]:
        """Prüft Positions-Limit"""
        # Hole DYNAMISCHE Max Position (updated alle 30s von Adaptive Intensity)
        max_position_size = self.config.test_balance * self.dynamic_params["max_position_pct"]

        # Vereinfachte Berechnung (später mit echtem Portfolio)
        estimated_position = max_position_size * 0.8  # 80% vom Limit nutzen

        if estimated_position > max_position_size:
            return (
                False,
                f"Position zu groß: {estimated_position:.2f} > {max_position_size:.2f}",
            )

        return True, "Position OK"

    def check_exposure_limit(self) -> tuple[bool, str]:
        """Prüft Gesamt-Exposure"""
        # Hole DYNAMISCHE Max Exposure (updated alle 30s von Adaptive Intensity)
        max_exposure = self.config.test_balance * self.dynamic_params["max_exposure_pct"]

        if risk_state.total_exposure >= max_exposure:
            return (
                False,
                f"Max Exposure erreicht: {risk_state.total_exposure:.2f} >= {max_exposure:.2f}",
            )

        return True, "Exposure OK"

    def check_drawdown_limit(self) -> tuple[bool, str]:
        """Prüft Daily-Drawdown (Circuit Breaker)"""
        max_drawdown = self.config.test_balance * self.config.max_daily_drawdown_pct

        if risk_state.daily_pnl <= -max_drawdown:
            risk_state.circuit_breaker_active = True
            self.save_risk_state_to_redis()  # Persist circuit breaker activation
            return (
                False,
                f"Circuit Breaker! Daily Loss: {risk_state.daily_pnl:.2f} <= -{max_drawdown:.2f}",
            )

        return True, "Drawdown OK"

    def process_signal(self, signal: Signal) -> Optional[Order]:
        """Prüft Signal gegen alle Risk-Layers"""

        # Layer 1: Circuit Breaker
        ok, reason = self.check_drawdown_limit()
        if not ok:
            self.send_alert(
                "CRITICAL", "CIRCUIT_BREAKER", reason, {"signal": signal.symbol}
            )
            logger.warning(f"🚨 {reason}")
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        # Layer 2: Exposure-Limit
        ok, reason = self.check_exposure_limit()
        if not ok:
            self.send_alert("WARNING", "RISK_LIMIT", reason, {"signal": signal.symbol})
            logger.warning(f"⚠️ {reason}")
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        # Layer 3: Position-Size
        ok, reason = self.check_position_limit(signal)
        if not ok:
            self.send_alert("WARNING", "RISK_LIMIT", reason, {"signal": signal.symbol})
            logger.warning(f"⚠️ {reason}")
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        # Alle Checks passed → Order erstellen
        quantity = self.calculate_position_size(signal)

        order = Order(
            symbol=signal.symbol,
            side=signal.side,
            quantity=quantity,
            stop_loss_pct=self.config.stop_loss_pct,
            signal_id=signal.timestamp,
            reason=signal.reason,
            timestamp=int(time.time()),
            price=signal.price,  # Pass signal price to execution
            client_id=f"{signal.symbol}-{signal.timestamp}",
        )

        logger.info(
            f"✅ Order freigegeben: {order.symbol} {order.side} qty={order.quantity:.4f}"
        )
        stats["orders_approved"] += 1
        risk_state.signals_approved += 1
        risk_state.pending_orders += 1

        # Persist risk_state nach Order-Approval
        self.save_risk_state_to_redis()

        return order

    def calculate_position_size(self, signal: Signal) -> float:
        """Berechnet Position-Size basierend auf Confidence"""
        # Hole DYNAMISCHE Max Position (updated alle 30s von Adaptive Intensity)
        max_size = self.config.test_balance * self.dynamic_params["max_position_pct"]

        # Confidence-basiert (höhere Confidence = größere Position)
        position_size = max_size * signal.confidence

        # Vereinfacht: Menge proportional zur Confidence, Mindestmenge 0
        return max(position_size, 0.0)

    def send_order(self, order: Order):
        """Publiziert Order"""
        try:
            message = json.dumps(order.to_dict(), ensure_ascii=False)
            self.redis_client.publish(self.config.output_topic_orders, message)
            logger.debug(f"Order publiziert: {order.symbol}")
        except Exception as e:
            logger.error(f"Fehler beim Order-Publishing: {e}")
            if risk_state.pending_orders > 0:
                risk_state.pending_orders -= 1

    def send_alert(self, level: str, code: str, message: str, context: dict):
        """Publiziert Alert"""
        try:
            alert = Alert(
                level=level,
                code=code,
                message=message,
                context=context,
                timestamp=int(time.time()),
            )
            msg = json.dumps(alert.to_dict())
            self.redis_client.publish(self.config.output_topic_alerts, msg)
            stats["alerts_generated"] += 1
            logger.warning(f"Alert: [{level}] {code}: {message}")
        except Exception as e:
            logger.error(f"Fehler beim Alert-Publishing: {e}")

    def _update_exposure(self, result: OrderResult):
        """Aktualisiert Exposure basierend auf Order-Result"""
        direction = 1 if result.side == "BUY" else -1
        delta = direction * result.filled_quantity
        if delta == 0:
            return

        current = risk_state.positions.get(result.symbol, 0.0)
        new_position = current + delta
        if abs(new_position) < 1e-6:
            risk_state.positions.pop(result.symbol, None)
            risk_state.last_prices.pop(result.symbol, None)
        else:
            risk_state.positions[result.symbol] = new_position
            if result.price is not None:
                risk_state.last_prices[result.symbol] = result.price

        if result.price is not None:
            risk_state.last_prices[result.symbol] = result.price

        risk_state.total_exposure = sum(
            abs(qty) * risk_state.last_prices.get(symbol, 0.0)
            for symbol, qty in risk_state.positions.items()
        )
        risk_state.open_positions = sum(
            1 for qty in risk_state.positions.values() if abs(qty) > 1e-6
        )

        # Persist risk_state nach Exposure-Update
        self.save_risk_state_to_redis()

    def handle_order_result(self, result: OrderResult):
        """Verarbeitet Order-Result Events vom Execution-Service"""
        stats["order_results_received"] += 1
        stats["last_order_result"] = {
            "order_id": result.order_id,
            "status": result.status,
            "symbol": result.symbol,
            "filled_quantity": result.filled_quantity,
            "client_id": result.client_id,
            "price": result.price,
            "timestamp": result.timestamp,
        }

        if risk_state.pending_orders > 0:
            risk_state.pending_orders -= 1

        if result.status == "FILLED":
            self._update_exposure(result)
        else:
            stats["orders_rejected_execution"] += 1
            self.send_alert(
                "WARNING" if result.status == "REJECTED" else "CRITICAL",
                "EXECUTION_ERROR",
                result.error_message or "Execution-Service meldete einen Fehler",
                {
                    "order_id": result.order_id,
                    "symbol": result.symbol,
                    "client_id": result.client_id,
                },
            )

    def listen_order_results(self):
        """Hintergrund-Listener für order_result Topic"""
        if not self.pubsub_results:
            return

        logger.info("Order-Result Listener aktiv")

        try:
            for message in self.pubsub_results.listen():
                if not self.running:
                    break
                if message.get("type") != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    if payload.get("type") != "order_result":
                        logger.debug(
                            "Ignoriere Fremd-Event im order_results Topic: %s",
                            payload.get("type"),
                        )
                        continue
                    result = OrderResult.from_dict(payload)
                    logger.info(
                        "Order-Result empfangen: %s status=%s qty=%.4f",
                        result.order_id,
                        result.status,
                        result.filled_quantity,
                    )
                    self.handle_order_result(result)
                except json.JSONDecodeError as err:
                    logger.warning(f"Ungültiges JSON im order_results Topic: {err}")
                except (KeyError, ValueError) as err:
                    logger.warning(f"Order-Result unvollständig: {err}")
        finally:
            logger.info("Order-Result Listener beendet")

    def run(self):
        """Hauptschleife"""
        self.running = True
        stats["status"] = "running"
        stats["started_at"] = datetime.now().isoformat()

        logger.info("🚀 Risk-Manager gestartet")
        logger.info(
            f"   Max Position: {self.dynamic_params['max_position_pct']*100:.1f}% (DYNAMIC)"
        )
        logger.info(
            f"   Max Exposure: {self.dynamic_params['max_exposure_pct']*100:.1f}% (DYNAMIC)"
        )
        logger.info(f"   Max Drawdown: {self.config.max_daily_drawdown_pct*100}%")
        logger.info(f"   Stop-Loss: {self.config.stop_loss_pct*100}%")

        if self.pubsub_results and (
            self._order_result_thread is None
            or not self._order_result_thread.is_alive()
        ):
            self._order_result_thread = Thread(
                target=self.listen_order_results, daemon=True
            )
            self._order_result_thread.start()
            logger.info("Order-Result Listener Thread gestartet")

        try:
            for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        signal = Signal.from_dict(data)

                        stats["signals_received"] += 1
                        logger.info(
                            f"📨 Signal empfangen: {signal.symbol} {signal.side}"
                        )

                        # Risk-Checks durchführen
                        order = self.process_signal(signal)

                        # Falls approved, Order senden
                        if order:
                            self.send_order(order)

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
        logger.info("Shutdown Risk-Manager...")
        self.running = False
        stats["status"] = "stopped"

        if self.pubsub:
            self.pubsub.close()
        if self.pubsub_results:
            self.pubsub_results.close()
        if self._heal_thread and self._heal_thread.is_alive():
            self._heal_stop_event.set()
            self._heal_thread.join(timeout=2)
        if self._order_result_thread and self._order_result_thread.is_alive():
            self._order_result_thread.join(timeout=2)
        if self.redis_client:
            self.redis_client.close()

        logger.info("Risk-Manager gestoppt ✓")


# ===== FLASK ENDPOINTS =====


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok" if stats["status"] == "running" else "error",
            "service": "risk_manager",
            "version": "0.1.0",
        }
    )


@app.route("/status")
def status():
    return jsonify(
        {
            **stats,
            "risk_state": {
                "total_exposure": risk_state.total_exposure,
                "daily_pnl": risk_state.daily_pnl,
                "open_positions": risk_state.open_positions,
                "signals_approved": risk_state.signals_approved,
                "signals_blocked": risk_state.signals_blocked,
                "circuit_breaker": risk_state.circuit_breaker_active,
                "positions": risk_state.positions,
                "pending_orders": risk_state.pending_orders,
                "last_prices": risk_state.last_prices,
            },
        }
    )


@app.route("/metrics")
def metrics():
    body = (
        "# HELP orders_approved_total Orders freigegeben\n"
        "# TYPE orders_approved_total counter\n"
        f"orders_approved_total {stats['orders_approved']}\n\n"
        "# HELP orders_blocked_total Orders blockiert\n"
        "# TYPE orders_blocked_total counter\n"
        f"orders_blocked_total {stats['orders_blocked']}\n\n"
        "# HELP circuit_breaker_active Circuit Breaker Status\n"
        "# TYPE circuit_breaker_active gauge\n"
        f"circuit_breaker_active {1 if risk_state.circuit_breaker_active else 0}\n\n"
        "# HELP order_results_received_total Anzahl verarbeiteter Order-Result Events\n"
        "# TYPE order_results_received_total counter\n"
        f"order_results_received_total {stats['order_results_received']}\n\n"
        "# HELP orders_rejected_execution_total Abgelehnte Orders durch Execution-Service\n"
        "# TYPE orders_rejected_execution_total counter\n"
        f"orders_rejected_execution_total {stats['orders_rejected_execution']}\n\n"
        "# HELP risk_pending_orders_total Anzahl offener Auftragsbestätigungen\n"
        "# TYPE risk_pending_orders_total gauge\n"
        f"risk_pending_orders_total {risk_state.pending_orders}\n\n"
        "# HELP risk_total_exposure_value Gesamtposition (Notional)\n"
        "# TYPE risk_total_exposure_value gauge\n"
        f"risk_total_exposure_value {risk_state.total_exposure}\n\n"
        "# HELP risk_state_inconsistency_total Detektierte State-Divergenzen\n"
        "# TYPE risk_state_inconsistency_total counter\n"
        f"risk_state_inconsistency_total {stats['risk_state_inconsistency_total']}\n\n"
        "# HELP risk_state_resync_total Startup-Sync Events (DB -> Redis)\n"
        "# TYPE risk_state_resync_total counter\n"
        f"risk_state_resync_total {stats['risk_state_resync_total']}\n\n"
        "# HELP risk_state_recovery_total Auto-Heal Resync Events\n"
        "# TYPE risk_state_recovery_total counter\n"
        f"risk_state_recovery_total {stats['risk_state_recovery_total']}\n"
    )
    return Response(body, mimetype="text/plain")


# ===== SIGNAL HANDLER =====


def signal_handler(signum, frame):
    logger.warning(f"Signal empfangen: {signum}")
    manager.shutdown()
    sys.exit(0)


# ===== MAIN =====

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    manager = RiskManager()
    manager.connect_redis()

    # Flask in Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()

    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Hauptschleife
    manager.run()
