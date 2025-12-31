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
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path
from threading import Thread

from core.utils.clock import utcnow
from core.auth import validate_all_auth
from core.security_headers import init_security_headers
try:
    from .config import config
    from .models import Order, Alert, RiskState, OrderResult
except ImportError:
    from config import config
    from models import Order, Alert, RiskState, OrderResult

from core.domain.models import Signal

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
init_security_headers(app)

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
}

# Risk-State
risk_state = RiskState()
current_regime = "UNKNOWN"
risk_off_active = False
shutdown_strategy_ids = set()
shutdown_bot_ids = set()


@dataclass
class AllocationState:
    allocation_pct: float = 0.0
    cooldown_until: int | None = None


class RiskManager:
    """Multi-Layer Risk-Management"""

    def __init__(self):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.pubsub_results: Optional[redis.client.PubSub] = None
        self._order_result_thread: Optional[Thread] = None
        self._regime_thread: Optional[Thread] = None
        self._allocation_thread: Optional[Thread] = None
        self._shutdown_thread: Optional[Thread] = None
        self.running = False
        self.allocation_state: dict[str, AllocationState] = {}
        self._circuit_shutdown_emitted = False

        # Validiere Config
        try:
            self.config.validate()
            logger.info("Config validiert ✓")
        except ValueError as e:
            logger.error(f"Config-Fehler: {e}")
            sys.exit(1)

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

        except redis.ConnectionError as e:
            logger.error(f"Redis-Verbindung fehlgeschlagen: {e}")
            sys.exit(1)

    @staticmethod
    def _parse_timestamp(value) -> int | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(datetime.fromisoformat(value).timestamp())
            except ValueError:
                try:
                    return int(float(value))
                except ValueError:
                    return None
        return None

    def _get_allocation_state(self, strategy_id: str) -> AllocationState:
        return self.allocation_state.get(strategy_id, AllocationState())

    def _allocation_allowed(self, strategy_id: str) -> tuple[bool, str]:
        state = self._get_allocation_state(strategy_id)
        if state.cooldown_until and state.cooldown_until > int(time.time()):
            return False, "Cooldown aktiv"
        if state.allocation_pct <= 0:
            return False, "Keine Allokation"
        return True, "Allokation OK"

    def _is_reduce_only_allowed(self, signal: Signal) -> bool:
        position = risk_state.positions.get(signal.symbol, 0.0)
        if abs(position) < 1e-9:
            return False
        if position > 0 and signal.side == "SELL":
            return True
        if position < 0 and signal.side == "BUY":
            return True
        return False

    def _listen_regime_stream(self):
        if not self.redis_client or not self.config.regime_stream:
            return
        last_id = "0-0"
        while self.running:
            try:
                response = self.redis_client.xread(
                    {self.config.regime_stream: last_id}, block=1000, count=10
                )
                if not response:
                    continue
                for _, entries in response:
                    for entry_id, payload in entries:
                        last_id = entry_id
                        regime = payload.get("regime", "UNKNOWN")
                        global current_regime, risk_off_active
                        current_regime = regime
                        risk_off_active = regime == "HIGH_VOL_CHAOTIC"
                        logger.info("Regime-Update: %s (risk_off=%s)", regime, risk_off_active)
            except Exception as err:  # noqa: BLE001
                logger.error("Regime-Stream Fehler: %s", err)
                time.sleep(1)

    def _listen_allocation_stream(self):
        if not self.redis_client or not self.config.allocation_stream:
            return
        last_id = "0-0"
        while self.running:
            try:
                response = self.redis_client.xread(
                    {self.config.allocation_stream: last_id}, block=1000, count=10
                )
                if not response:
                    continue
                for _, entries in response:
                    for entry_id, payload in entries:
                        last_id = entry_id
                        strategy_id = payload.get("strategy_id")
                        if not strategy_id:
                            continue
                        allocation_pct = float(payload.get("allocation_pct", 0.0))
                        cooldown_until = self._parse_timestamp(payload.get("cooldown_until"))
                        self.allocation_state[strategy_id] = AllocationState(
                            allocation_pct=allocation_pct,
                            cooldown_until=cooldown_until,
                        )
            except Exception as err:  # noqa: BLE001
                logger.error("Allocation-Stream Fehler: %s", err)
                time.sleep(1)

    def _listen_shutdown_stream(self):
        if not self.redis_client or not self.config.bot_shutdown_stream:
            return
        last_id = "0-0"
        while self.running:
            try:
                response = self.redis_client.xread(
                    {self.config.bot_shutdown_stream: last_id}, block=1000, count=10
                )
                if not response:
                    continue
                for _, entries in response:
                    for entry_id, payload in entries:
                        last_id = entry_id
                        strategy_id = payload.get("strategy_id")
                        bot_id = payload.get("bot_id")
                        if strategy_id:
                            shutdown_strategy_ids.add(strategy_id)
                        if bot_id:
                            shutdown_bot_ids.add(bot_id)
                        logger.warning(
                            "Bot-Shutdown empfangen: strategy_id=%s bot_id=%s",
                            strategy_id,
                            bot_id,
                        )
            except Exception as err:  # noqa: BLE001
                logger.error("Shutdown-Stream Fehler: %s", err)
                time.sleep(1)
    def check_position_limit(self, signal: Signal) -> tuple[bool, str]:
        """Prüft Positions-Limit"""
        # REAL BALANCE - NO MORE FAKE test_balance
        from .balance_fetcher import RealBalanceFetcher

        if self.config.use_real_balance:
            balance_fetcher = RealBalanceFetcher()
            current_balance = balance_fetcher.get_usdt_balance()
        else:
            current_balance = self.config.fallback_balance

        # Max 10% des REAL Kapitals pro Position
        max_position_size = current_balance * self.config.max_position_pct

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
        # REAL BALANCE - NO MORE FAKE
        from .balance_fetcher import RealBalanceFetcher

        if self.config.use_real_balance:
            balance_fetcher = RealBalanceFetcher()
            current_balance = balance_fetcher.get_usdt_balance()
        else:
            current_balance = self.config.fallback_balance

        max_exposure = current_balance * self.config.max_total_exposure_pct

        if risk_state.total_exposure >= max_exposure:
            return (
                False,
                f"Max Exposure erreicht: {risk_state.total_exposure:.2f} >= {max_exposure:.2f}",
            )

        return True, "Exposure OK"

    def check_drawdown_limit(self) -> tuple[bool, str]:
        """Prüft Daily-Drawdown (Circuit Breaker)"""
        # REAL BALANCE - NO MORE FAKE
        from .balance_fetcher import RealBalanceFetcher

        if self.config.use_real_balance:
            balance_fetcher = RealBalanceFetcher()
            current_balance = balance_fetcher.get_usdt_balance()
        else:
            current_balance = self.config.fallback_balance

        max_drawdown = current_balance * self.config.max_daily_drawdown_pct

        if risk_state.daily_pnl <= -max_drawdown:
            risk_state.circuit_breaker_active = True
            return (
                False,
                f"Circuit Breaker! Daily Loss: {risk_state.daily_pnl:.2f} <= -{max_drawdown:.2f}",
            )

        return True, "Drawdown OK"

    def process_signal(self, signal: Signal) -> Optional[Order]:
        """Prüft Signal gegen alle Risk-Layers"""

        if not signal.strategy_id:
            self.send_alert(
                "CRITICAL",
                "MISSING_STRATEGY_ID",
                "Signal ohne strategy_id abgelehnt",
                {"symbol": signal.symbol},
            )
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        if signal.strategy_id in shutdown_strategy_ids or (
            signal.bot_id and signal.bot_id in shutdown_bot_ids
        ):
            logger.warning("Signal blockiert: Bot-Shutdown aktiv")
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        allowed, alloc_reason = self._allocation_allowed(signal.strategy_id)
        if not allowed:
            logger.warning("Signal blockiert: %s", alloc_reason)
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        if risk_off_active and not self._is_reduce_only_allowed(signal):
            logger.warning("Signal blockiert: Risk-Off Reduce-Only")
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        # Layer 1: Circuit Breaker
        ok, reason = self.check_drawdown_limit()
        if not ok:
            self.send_alert(
                "CRITICAL", "CIRCUIT_BREAKER", reason, {"signal": signal.symbol}
            )
            if not self._circuit_shutdown_emitted:
                self.emit_bot_shutdown(reason)
                self._circuit_shutdown_emitted = True
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
        allocation = self._get_allocation_state(signal.strategy_id)
        quantity = self.calculate_position_size(signal, allocation.allocation_pct)

        order = Order(
            symbol=signal.symbol,
            side=signal.side,
            quantity=quantity,
            stop_loss_pct=self.config.stop_loss_pct,
            signal_id=signal.timestamp,
            reason=signal.reason,
            timestamp=int(time.time()),
            client_id=f"{signal.symbol}-{signal.timestamp}",
            strategy_id=signal.strategy_id,
            bot_id=signal.bot_id,
        )

        logger.info(
            f"✅ Order freigegeben: {order.symbol} {order.side} qty={order.quantity:.4f}"
        )
        stats["orders_approved"] += 1
        risk_state.signals_approved += 1
        risk_state.pending_orders += 1

        return order

    def calculate_position_size(self, signal: Signal, allocation_pct: float) -> float:
        """Berechnet Position-Size basierend auf Allokation"""
        # REAL BALANCE - NO MORE FAKE
        from .balance_fetcher import RealBalanceFetcher

        if self.config.use_real_balance:
            balance_fetcher = RealBalanceFetcher()
            current_balance = balance_fetcher.get_usdt_balance()
        else:
            current_balance = self.config.fallback_balance

        max_size = current_balance * self.config.max_position_pct

        # Allokationsbasiert (keine Confidence im Control-Pfad)
        position_size = max_size * max(allocation_pct, 0.0)

        # Vereinfacht: Menge proportional zur Allokation, Mindestmenge 0
        return max(position_size, 0.0)

    def send_order(self, order: Order):
        """Publiziert Order"""
        try:
            message = json.dumps(order.to_dict(), ensure_ascii=False)
            self.redis_client.publish(self.config.output_topic_orders, message)
            if self.redis_client:
                self.redis_client.xadd(
                    self.config.orders_stream, json.loads(message), maxlen=10000
                )
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

    def emit_bot_shutdown(
        self, reason: str, strategy_id: str | None = None, bot_id: str | None = None
    ) -> None:
        """Publiziert BotShutdownEvent mit Safety-Priorität."""
        if not self.redis_client or not self.config.bot_shutdown_stream:
            return
        payload = {
            "ts": int(time.time()),
            "reason": reason,
            "priority": "SAFETY",
        }
        if strategy_id:
            payload["strategy_id"] = strategy_id
        if bot_id:
            payload["bot_id"] = bot_id
        self.redis_client.xadd(self.config.bot_shutdown_stream, payload, maxlen=10000)
        logger.warning("Bot-Shutdown emittiert: %s", payload)

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
        stats["started_at"] = utcnow().isoformat()

        logger.info("🚀 Risk-Manager gestartet")
        logger.info(f"   Max Position: {self.config.max_position_pct*100}%")
        logger.info(f"   Max Exposure: {self.config.max_total_exposure_pct*100}%")
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
        if self._regime_thread is None or not self._regime_thread.is_alive():
            self._regime_thread = Thread(target=self._listen_regime_stream, daemon=True)
            self._regime_thread.start()
            logger.info("Regime-Stream Listener Thread gestartet")
        if self._allocation_thread is None or not self._allocation_thread.is_alive():
            self._allocation_thread = Thread(
                target=self._listen_allocation_stream, daemon=True
            )
            self._allocation_thread.start()
            logger.info("Allocation-Stream Listener Thread gestartet")
        if self._shutdown_thread is None or not self._shutdown_thread.is_alive():
            self._shutdown_thread = Thread(
                target=self._listen_shutdown_stream, daemon=True
            )
            self._shutdown_thread.start()
            logger.info("Shutdown-Stream Listener Thread gestartet")

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
        f"risk_total_exposure_value {risk_state.total_exposure}\n"
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

    # Validate Redis auth before startup
    from core.auth import validate_redis_auth
    redis_ok, redis_msg = validate_redis_auth(
        config.redis_host, config.redis_port, config.redis_password, config.redis_db
    )
    if not redis_ok:
        logger.critical("Auth validation FAILED. Service cannot start.")
        logger.critical(f"Redis: {redis_msg}")
        sys.exit(1)

    manager = RiskManager()
    manager.connect_redis()

    # Flask in Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()

    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Hauptschleife
    manager.run()
