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
from threading import Thread

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
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
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
    "status": "initializing"
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
        self.running = False
        
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
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info(f"Redis verbunden: {self.config.redis_host}:{self.config.redis_port}")
            
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.config.input_topic)
            logger.info(f"Subscribed zu Topic: {self.config.input_topic}")
            
            self.pubsub_results = self.redis_client.pubsub()
            self.pubsub_results.subscribe(self.config.input_topic_order_results)
            logger.info(f"Subscribed zu Order-Result Topic: {self.config.input_topic_order_results}")
            
        except redis.ConnectionError as e:
            logger.error(f"Redis-Verbindung fehlgeschlagen: {e}")
            sys.exit(1)
    
    def check_position_limit(self, signal: Signal) -> tuple[bool, str]:
        """Prüft Positions-Limit

        Returns:
            tuple[bool, str]: (approved, reason)
        """
        # Max allowed position value in USD
        max_position_usd = self.config.test_balance * self.config.max_position_pct

        # ✅ FIX Bug #2: Calculate actual position value
        quantity = self.calculate_position_size(signal)
        position_value_usd = quantity * signal.price

        if position_value_usd > max_position_usd:
            return False, (
                f"Position zu groß: {position_value_usd:.2f} USD "
                f"> {max_position_usd:.2f} USD (Limit)"
            )

        return True, f"Position OK ({position_value_usd:.2f} / {max_position_usd:.2f} USD)"
    
    def check_exposure_limit(self, signal: Signal) -> tuple[bool, str]:
        """Prüft Gesamt-Exposure (inkl. zukünftiger Position)

        Args:
            signal: Signal to evaluate

        Returns:
            tuple[bool, str]: (approved, reason)
        """
        max_exposure = self.config.test_balance * self.config.max_exposure_pct

        # ✅ FIX Bug #3: Calculate FUTURE exposure (current + new position)
        quantity = self.calculate_position_size(signal)
        estimated_new_position = quantity * signal.price
        future_exposure = risk_state.total_exposure + estimated_new_position

        if future_exposure >= max_exposure:
            return False, (
                f"Exposure-Limit würde überschritten: "
                f"{risk_state.total_exposure:.2f} + {estimated_new_position:.2f} "
                f"= {future_exposure:.2f} >= {max_exposure:.2f} USD"
            )

        return True, (
            f"Exposure OK ({future_exposure:.2f} / {max_exposure:.2f} USD, "
            f"aktuell: {risk_state.total_exposure:.2f})"
        )
    
    def check_drawdown_limit(self) -> tuple[bool, str]:
        """Prüft Daily-Drawdown (Circuit Breaker)"""
        max_drawdown = self.config.test_balance * self.config.max_daily_drawdown_pct
        
        if risk_state.daily_pnl <= -max_drawdown:
            risk_state.circuit_breaker_active = True
            return False, f"Circuit Breaker! Daily Loss: {risk_state.daily_pnl:.2f} <= -{max_drawdown:.2f}"
        
        return True, "Drawdown OK"
    
    def process_signal(self, signal: Signal) -> Optional[Order]:
        """Prüft Signal gegen alle Risk-Layers"""
        
        # Layer 1: Circuit Breaker
        ok, reason = self.check_drawdown_limit()
        if not ok:
            self.send_alert("CRITICAL", "CIRCUIT_BREAKER", reason, {"signal": signal.symbol})
            logger.warning(f"🚨 {reason}")
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None
        
        # Layer 2: Exposure-Limit
        ok, reason = self.check_exposure_limit(signal)
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
            client_id=f"{signal.symbol}-{signal.timestamp}"
        )
        
        logger.info(f"✅ Order freigegeben: {order.symbol} {order.side} qty={order.quantity:.4f}")
        stats["orders_approved"] += 1
        risk_state.signals_approved += 1
        risk_state.pending_orders += 1
        
        return order
    
    def calculate_position_size(self, signal: Signal) -> float:
        """Berechnet Position-Size basierend auf Confidence

        Returns:
            float: Position size in COINS (not USD)
        """
        # Calculate max USD value for this position
        max_usd = self.config.test_balance * self.config.max_position_pct

        # Adjust by confidence (higher confidence = larger position)
        target_usd = max_usd * signal.confidence

        # ✅ FIX Bug #1: Convert USD to COINS
        if signal.price <= 0:
            logger.error(f"Invalid price for {signal.symbol}: {signal.price}")
            return 0.0

        # Calculate quantity in base currency (e.g., BTC)
        quantity = target_usd / signal.price

        logger.debug(
            f"Position sizing: {signal.symbol} "
            f"max_usd={max_usd:.2f} confidence={signal.confidence:.2f} "
            f"target_usd={target_usd:.2f} price={signal.price:.2f} "
            f"→ quantity={quantity:.6f}"
        )

        return max(quantity, 0.0)
    
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
                timestamp=int(time.time())
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

        # Check if position was closed
        if abs(new_position) < 1e-6:
            # Position closed → calculate realized P&L
            if result.price is not None and result.symbol in risk_state.entry_prices:
                entry_price = risk_state.entry_prices[result.symbol]
                side = risk_state.position_sides.get(result.symbol, "BUY")

                if side == "BUY":
                    realized_pnl = abs(current) * (result.price - entry_price)
                else:  # SHORT
                    realized_pnl = abs(current) * (entry_price - result.price)

                risk_state.realized_pnl_today += realized_pnl
                logger.info(
                    f"Position closed: {result.symbol} "
                    f"realized_pnl={realized_pnl:.2f} "
                    f"total_realized_today={risk_state.realized_pnl_today:.2f}"
                )

            # Clean up closed position
            risk_state.positions.pop(result.symbol, None)
            risk_state.last_prices.pop(result.symbol, None)
            risk_state.entry_prices.pop(result.symbol, None)
            risk_state.position_sides.pop(result.symbol, None)
        else:
            # Position opened or increased
            risk_state.positions[result.symbol] = new_position

            # ✅ FIX Bug #4: Track entry price and side for P&L calculation
            if result.price is not None:
                # Store entry price (only on first entry, not on increases)
                if result.symbol not in risk_state.entry_prices:
                    risk_state.entry_prices[result.symbol] = result.price
                    risk_state.position_sides[result.symbol] = result.side
                    logger.debug(
                        f"Position opened: {result.symbol} side={result.side} "
                        f"entry={result.price:.2f} qty={new_position:.6f}"
                    )

                # Always update last price
                risk_state.last_prices[result.symbol] = result.price

        # Recalculate total exposure
        risk_state.total_exposure = sum(
            abs(qty) * risk_state.last_prices.get(symbol, 0.0)
            for symbol, qty in risk_state.positions.items()
        )
        risk_state.open_positions = sum(1 for qty in risk_state.positions.values() if abs(qty) > 1e-6)

    def _update_pnl(self):
        """✅ FIX Bug #4: Berechnet Daily P&L (Realized + Unrealized)

        Daily P&L = Realized P&L (from closed trades today) + Unrealized P&L (from open positions)
        """
        unrealized_pnl = 0.0

        # Calculate unrealized P&L for all open positions
        for symbol, qty in risk_state.positions.items():
            if abs(qty) < 1e-6:
                continue

            entry_price = risk_state.entry_prices.get(symbol, 0.0)
            current_price = risk_state.last_prices.get(symbol, 0.0)

            if entry_price <= 0 or current_price <= 0:
                logger.warning(f"Invalid prices for {symbol}: entry={entry_price} current={current_price}")
                continue

            side = risk_state.position_sides.get(symbol, "BUY")

            if side == "BUY":
                # Long position: profit if current > entry
                pnl = qty * (current_price - entry_price)
            else:  # SHORT
                # Short position: profit if entry > current
                pnl = qty * (entry_price - current_price)

            unrealized_pnl += pnl

        # Total Daily P&L = Realized (closed trades) + Unrealized (open positions)
        risk_state.daily_pnl = risk_state.realized_pnl_today + unrealized_pnl

        logger.debug(
            f"P&L Update: realized={risk_state.realized_pnl_today:.2f} "
            f"unrealized={unrealized_pnl:.2f} "
            f"total_daily={risk_state.daily_pnl:.2f}"
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
            "timestamp": result.timestamp
        }

        if risk_state.pending_orders > 0:
            risk_state.pending_orders -= 1

        if result.status == "FILLED":
            self._update_exposure(result)
            # ✅ FIX Bug #4: Update P&L after exposure update
            self._update_pnl()
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
                }
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
                        logger.debug("Ignoriere Fremd-Event im order_results Topic: %s", payload.get("type"))
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
        logger.info(f"   Max Position: {self.config.max_position_pct*100}%")
        logger.info(f"   Max Exposure: {self.config.max_exposure_pct*100}%")
        logger.info(f"   Max Drawdown: {self.config.max_daily_drawdown_pct*100}%")
        logger.info(f"   Stop-Loss: {self.config.stop_loss_pct*100}%")

        if self.pubsub_results and (self._order_result_thread is None or not self._order_result_thread.is_alive()):
            self._order_result_thread = Thread(target=self.listen_order_results, daemon=True)
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
                        logger.info(f"📨 Signal empfangen: {signal.symbol} {signal.side}")
                        
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
    return jsonify({
        "status": "ok" if stats["status"] == "running" else "error",
        "service": "risk_manager",
        "version": "0.1.0"
    })

@app.route("/status")
def status():
    return jsonify({
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
            "last_prices": risk_state.last_prices
        }
    })

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
    
    manager = RiskManager()
    manager.connect_redis()
    
    # Flask in Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()
    
    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")
    
    # Hauptschleife
    manager.run()
