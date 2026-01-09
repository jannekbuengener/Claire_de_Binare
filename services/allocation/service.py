"""
Allocation Service
Deterministic allocation decisions based on regime and performance.
"""

import json
import logging
import logging.config
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Optional

import redis
from flask import Flask, jsonify, Response

from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_payload
try:
    from .config import config
except ImportError:
    from config import config

logging_config_path = Path(__file__).parent.parent.parent / "logging_config.json"
if logging_config_path.exists():
    with open(logging_config_path) as f:
        logging_conf = json.load(f)
        logging.config.dictConfig(logging_conf)
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("allocation_service")
app = Flask(__name__)

stats = {
    "started_at": None,
    "regime_updates": 0,
    "fills_processed": 0,
    "decisions_emitted": 0,
    "status": "initializing",
}


@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0


@dataclass
class TradeRecord:
    ts: int
    return_pct: float


@dataclass
class AllocationState:
    allocation_pct: float = 0.0
    cooldown_until: Optional[int] = None
    last_updated: Optional[int] = None


class AllocationService:
    def __init__(self):
        self.config = config
        self.config.validate()
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.current_regime = "UNKNOWN"
        self.regime_candidate: Optional[str] = None
        self.regime_candidate_since: Optional[int] = None
        self.positions: dict[str, dict[str, Position]] = defaultdict(dict)
        self.trades: dict[str, deque[TradeRecord]] = defaultdict(
            lambda: deque(maxlen=2000)
        )
        self.allocations: dict[str, AllocationState] = defaultdict(AllocationState)
        self.shutdown_strategy_ids = set()

    def connect_redis(self):
        self.redis_client = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            password=self.config.redis_password,
            db=self.config.redis_db,
            decode_responses=True,
        )
        self.redis_client.ping()
        logger.info(
            "Redis verbunden: %s:%s", self.config.redis_host, self.config.redis_port
        )

    @staticmethod
    def _parse_ts(value) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(datetime.fromisoformat(value).timestamp())
        except ValueError:
            try:
                return int(float(value))
            except ValueError:
                return None

    def _update_regime(self, regime: str, ts: int) -> bool:
        if regime == self.current_regime:
            self.regime_candidate = None
            self.regime_candidate_since = None
            return False
        if self.regime_candidate != regime:
            self.regime_candidate = regime
            self.regime_candidate_since = ts
            return False
        if self.regime_candidate_since is None:
            self.regime_candidate_since = ts
            return False
        if ts - self.regime_candidate_since < self.config.regime_min_stable_seconds:
            return False
        self.current_regime = regime
        self.regime_candidate = None
        self.regime_candidate_since = None
        stats["regime_updates"] += 1
        return True

    def _record_trade(self, strategy_id: str, ts: int, pnl: float, notional: float):
        if notional <= 0:
            return
        return_pct = pnl / notional
        self.trades[strategy_id].append(TradeRecord(ts=ts, return_pct=return_pct))

    def _handle_fill(self, payload: dict):
        status = (payload.get("status") or "").upper()
        if status != "FILLED":
            return
        strategy_id = payload.get("strategy_id")
        if not strategy_id:
            logger.warning("Fill ohne strategy_id ignoriert")
            return
        symbol = payload.get("symbol")
        side = payload.get("side")
        qty = payload.get("filled_quantity") or payload.get("quantity")
        price = payload.get("price")
        ts = self._parse_ts(payload.get("timestamp"))
        if not symbol or side not in {"BUY", "SELL"} or qty is None or price is None:
            return
        if ts is None:
            return

        qty = float(qty)
        price = float(price)
        pos = self.positions[strategy_id].get(symbol, Position())
        delta = qty if side == "BUY" else -qty

        if pos.qty == 0:
            pos.qty = delta
            pos.avg_price = price
            self.positions[strategy_id][symbol] = pos
            return

        if pos.qty * delta > 0:
            total_qty = abs(pos.qty) + abs(delta)
            pos.avg_price = (pos.avg_price * abs(pos.qty) + price * abs(delta)) / total_qty
            pos.qty += delta
            self.positions[strategy_id][symbol] = pos
            return

        closing_qty = min(abs(pos.qty), abs(delta))
        if pos.qty > 0:
            pnl = (price - pos.avg_price) * closing_qty
        else:
            pnl = (pos.avg_price - price) * closing_qty
        self._record_trade(strategy_id, ts, pnl, pos.avg_price * closing_qty)
        pos.qty += delta
        if abs(pos.qty) < 1e-9:
            pos.qty = 0.0
            pos.avg_price = 0.0
        else:
            pos.avg_price = price
        self.positions[strategy_id][symbol] = pos

    def _compute_performance(self, strategy_id: str, ts: int) -> tuple[Optional[float], bool]:
        trades = list(self.trades.get(strategy_id, []))
        if not trades:
            return None, False
        cutoff = ts - self.config.lookback_days * 86400
        trades_in_window = [t for t in trades if t.ts >= cutoff]
        if len(trades_in_window) >= self.config.lookback_trades:
            window = trades_in_window
        elif len(trades) >= self.config.lookback_trades:
            window = trades[-self.config.lookback_trades :]
        else:
            window = trades

        window_ready = (
            len(window) >= self.config.lookback_trades
            and ts - window[0].ts >= self.config.lookback_days * 86400
        )
        if not window_ready:
            return None, False

        ema = None
        for trade in window:
            ema = (
                trade.return_pct
                if ema is None
                else self.config.ema_alpha * trade.return_pct
                + (1 - self.config.ema_alpha) * ema
            )
        return ema, True

    def _emit_decision(self, strategy_id: str, state: AllocationState, reason: str, ts: int):
        payload = {
            "ts": str(ts),
            "strategy_id": strategy_id,
            "allocation_pct": f"{state.allocation_pct:.6f}",
            "reason": reason,
            "cooldown_until": "" if state.cooldown_until is None else str(state.cooldown_until),
            "schema_version": self.config.schema_version,
            "source_version": self.config.source_version,
        }
        sanitized = sanitize_payload(payload)
        self.redis_client.xadd(self.config.output_stream, sanitized, maxlen=10000)
        stats["decisions_emitted"] += 1

    def _recompute_allocations(self, ts: int):
        scores = {}
        readiness = {}
        for strategy_id in self.config.rules.keys():
            score, ready = self._compute_performance(strategy_id, ts)
            scores[strategy_id] = score
            readiness[strategy_id] = ready

        ready_scores = [v for v in scores.values() if v is not None]
        median_score = median(ready_scores) if ready_scores else None

        for strategy_id, rule in self.config.rules.items():
            state = self.allocations[strategy_id]
            base_alloc = float(rule.get(self.current_regime, 0.0))
            reason = f"regime={self.current_regime}"

            if self.current_regime == "HIGH_VOL_CHAOTIC":
                target = 0.0
                reason += "|risk_off"
            else:
                target = base_alloc

            if state.cooldown_until and state.cooldown_until <= ts:
                state.cooldown_until = None

            if strategy_id in self.shutdown_strategy_ids:
                target = 0.0
                reason += "|shutdown"

            if state.cooldown_until and state.cooldown_until > ts:
                target = 0.0
                reason += "|cooldown"

            if target > 0 and state.allocation_pct == 0.0:
                if not readiness[strategy_id]:
                    target = 0.0
                    reason += "|perf_not_ready"
                elif median_score is not None and scores[strategy_id] is not None:
                    if scores[strategy_id] <= median_score:
                        target = 0.0
                        reason += "|perf_below_median"

            prev_alloc = state.allocation_pct
            prev_cooldown = state.cooldown_until
            is_bootstrap = state.last_updated is None  # First run after service start

            if state.allocation_pct > 0.0 and target == 0.0:
                state.cooldown_until = ts + self.config.cooldown_seconds
                reason += "|cooldown_set"

            changed = prev_alloc != target or prev_cooldown != state.cooldown_until
            state.allocation_pct = target
            state.last_updated = ts

            # Emit decision if changed OR on first bootstrap (to persist initial state)
            if changed or is_bootstrap:
                self._emit_decision(strategy_id, state, reason, ts)

    def _handle_regime_signal(self, payload: dict):
        ts = self._parse_ts(payload.get("ts"))
        if ts is None:
            return
        regime = payload.get("regime") or "UNKNOWN"
        changed = self._update_regime(regime, ts)
        if changed:
            self._recompute_allocations(ts)

    def _handle_shutdown(self, payload: dict):
        strategy_id = payload.get("strategy_id")
        if strategy_id:
            self.shutdown_strategy_ids.add(strategy_id)
        ts = self._parse_ts(payload.get("ts"))
        if ts is None:
            return
        self._recompute_allocations(ts)

    def run(self):
        if not self.redis_client:
            self.connect_redis()
        self.running = True
        stats["status"] = "running"
        stats["started_at"] = utcnow().isoformat()

        # Bootstrap: Process latest regime signal to avoid missing state after restart
        last_regime_id = "0-0"
        try:
            regime_entries = self.redis_client.xrevrange(
                self.config.regime_stream, "+", "-", count=1
            )
            if regime_entries:
                entry_id, payload = regime_entries[0]
                logger.info(f"Bootstrap: Processing latest regime signal {entry_id}")
                ts = self._parse_ts(payload.get("ts"))
                regime = payload.get("regime") or "UNKNOWN"
                # Bootstrap: Set regime directly without stability check (trust existing signal)
                self.current_regime = regime
                self.regime_candidate = None
                self.regime_candidate_since = None
                logger.info(f"Bootstrap: Regime set to {regime}")
                # Always recompute allocations on bootstrap
                self._recompute_allocations(ts if ts else int(utcnow().timestamp()))
                last_regime_id = entry_id
        except Exception as e:
            logger.warning(f"Bootstrap failed, starting from 0-0: {e}")

        last_fill_id = "0-0"
        last_shutdown_id = "0-0"
        logger.info("Allocation-Service gestartet")

        while self.running:
            response = self.redis_client.xread(
                {
                    self.config.regime_stream: last_regime_id,
                    self.config.fills_stream: last_fill_id,
                    self.config.shutdown_stream: last_shutdown_id,
                },
                block=1000,
                count=10,
            )
            if not response:
                continue
            for stream_name, entries in response:
                for entry_id, payload in entries:
                    if stream_name == self.config.regime_stream:
                        last_regime_id = entry_id
                        self._handle_regime_signal(payload)
                    elif stream_name == self.config.fills_stream:
                        last_fill_id = entry_id
                        stats["fills_processed"] += 1
                        self._handle_fill(payload)
                        ts = self._parse_ts(payload.get("timestamp"))
                        if ts is not None:
                            self._recompute_allocations(ts)
                    elif stream_name == self.config.shutdown_stream:
                        last_shutdown_id = entry_id
                        self._handle_shutdown(payload)


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok" if stats["status"] == "running" else "error",
            "service": "allocation_service",
            "version": config.source_version,
        }
    )


@app.route("/metrics")
def metrics():
    body = (
        "# HELP allocation_decisions_total Anzahl Allokationsentscheidungen\n"
        "# TYPE allocation_decisions_total counter\n"
        f"allocation_decisions_total {stats['decisions_emitted']}\n\n"
        "# HELP allocation_fills_processed_total Anzahl verarbeiteter Fills\n"
        "# TYPE allocation_fills_processed_total counter\n"
        f"allocation_fills_processed_total {stats['fills_processed']}\n"
    )
    return Response(body, mimetype="text/plain")


if __name__ == "__main__":
    service = AllocationService()
    service.connect_redis()
    from threading import Thread

    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()
    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    service.run()
