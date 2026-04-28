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
from collections import defaultdict

try:
    _FLASK_AVAILABLE = importlib.util.find_spec("flask") is not None
except ModuleNotFoundError as e:
    if e.name == "flask" or (e.name and e.name.startswith("flask.")):
        _FLASK_AVAILABLE = False
    else:
        raise
except ValueError:
    _FLASK_AVAILABLE = False
from typing import Any, Optional
from pathlib import Path

import psycopg2
import psycopg2.extensions

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_signal
from core.utils.uuid_gen import (
    generate_uuid_hex,
    compute_correlation_id,
    compute_event_pk,
)
from core.contracts import PRIMARY_BREAKOUT_V1_STRATEGY_ID
from core.utils.paper_probe_toggle import paper_evidence_probe_enabled
from core.contracts.external_adapter_contracts import (
    StrategyAdapterRequest,
    StrategyAdapterResponse,
    StrategySignalCandidate,
)
from core.contracts.external_adapter_registry import (
    MOMENTUM_BUILTIN,
    SIGNAL_ADAPTER_ENV_VAR,
    build_strategy_adapter,
)

try:
    from .config import SignalConfig, config
    from .models import MarketData, Signal
    from .price_buffer import PriceBuffer
except ImportError:
    # Fallback for script/importlib execution: ensure repo root is on sys.path.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from services.signal.config import SignalConfig, config
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


def _build_runtime_config_snapshot(config: SignalConfig) -> dict[str, Any]:
    return _compact_metadata(
        {
            "strategy_id": config.strategy_id,
            "symbol": config.symbol,
            "bot_id": config.bot_id or "",
            "threshold_pct": config.threshold_pct,
            "lookback_minutes": config.lookback_minutes,
            "min_volume": config.min_volume,
            "entry_lookback_minutes": config.entry_lookback_minutes,
            "exit_lookback_minutes": config.exit_lookback_minutes,
            "breakout_buffer": config.breakout_buffer,
            "min_minutes_between_entries": config.min_minutes_between_entries,
            "trade_side_mode": config.trade_side_mode,
            "market_state_key_prefix": config.market_state_key_prefix,
            "market_state_staleness_s": config.market_state_staleness_s,
        }
    )


def _build_config_hash(snapshot: dict[str, Any]) -> str:
    return canonical_hash(snapshot)


_RESERVED_SIGNAL_METADATA_KEYS = frozenset(
    {
        "strategy_id",
        "bot_id",
        "timing",
        "config_snapshot",
        "config_hash",
        "signal_reason",
        "signal_inputs",
    }
)


def _merge_candidate_signal_metadata(
    core_metadata: dict[str, Any], candidate_signal_metadata: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(core_metadata)
    for key, value in candidate_signal_metadata.items():
        if key in _RESERVED_SIGNAL_METADATA_KEYS:
            continue
        merged[key] = value
    return merged


def _build_signal_metadata(
    signal: Signal,
    *,
    config_snapshot: dict[str, Any],
    config_hash: str,
) -> dict:
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
            "config_snapshot": config_snapshot,
            "config_hash": config_hash,
        }
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return False


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
        self._high_history: dict[str, list[tuple[int, float]]] = defaultdict(list)
        self._low_history: dict[str, list[tuple[int, float]]] = defaultdict(list)
        self._last_entry_ts_ms: dict[str, int] = {}
        self._position_open_by_symbol: dict[str, bool] = defaultdict(bool)

        # Validiere Config
        try:
            self.config.validate()
            logger.info("Config validiert ✓")
        except ValueError as e:
            logger.error(f"Config-Fehler: {e}")
            sys.exit(1)

        adapter_id = os.getenv(SIGNAL_ADAPTER_ENV_VAR)
        if (
            self.config.strategy_id == PRIMARY_BREAKOUT_V1_STRATEGY_ID
            and adapter_id
            and adapter_id.strip() != MOMENTUM_BUILTIN
        ):
            logger.error(
                "Config-Fehler: SIGNAL_ADAPTER_ID=%r ist fuer primary_breakout_v1 ungueltig "
                "(erwartet: %s)",
                adapter_id,
                MOMENTUM_BUILTIN,
            )
            sys.exit(1)
        self.strategy_adapter = build_strategy_adapter(
            adapter_id,
            evaluate_fn=self._evaluate_builtin_strategy,
        )
        logger.info(
            "Strategy adapter resolved: %s",
            getattr(self.strategy_adapter, "adapter_id", "UNKNOWN"),
        )

    def _build_strategy_runtime_context(self, market_data: MarketData) -> dict:
        return {
            "threshold_pct": self.config.threshold_pct,
            "min_volume": self.config.min_volume,
            "strategy_id": self.config.strategy_id,
            "bot_id": self.config.bot_id,
            "market_data_obj": market_data,
        }

    @staticmethod
    def _build_market_snapshot(market_data: MarketData) -> dict:
        return {
            "symbol": market_data.symbol,
            "price": market_data.price,
            "pct_change": market_data.pct_change,
            "volume": market_data.volume,
            "volume_15m": market_data.volume,
            "trade_qty": market_data.trade_qty,
            "timestamp": market_data.timestamp,
        }

    def _signal_from_candidate(
        self, candidate: StrategySignalCandidate, market_data: MarketData
    ) -> Signal:
        now_ms = int(time.time() * 1000)
        config_snapshot = _build_runtime_config_snapshot(self.config)
        config_hash = _build_config_hash(config_snapshot)
        signal = Signal(
            signal_id=f"sig-{generate_uuid_hex(length=32)}",
            symbol=candidate.symbol,
            side=candidate.side,
            reason=candidate.reason,
            timestamp=now_ms // 1000,
            ts_ms=now_ms,
            price=candidate.price if candidate.price is not None else market_data.price,
            pct_change=(
                candidate.pct_change
                if candidate.pct_change is not None
                else market_data.pct_change
            ),
            pct_change_15m=market_data.pct_change,
            volume_15m=market_data.volume,
            strategy_id=candidate.strategy_id,
            bot_id=self.config.bot_id,
            confidence=candidate.confidence,
        )
        metadata = _build_signal_metadata(
            signal,
            config_snapshot=config_snapshot,
            config_hash=config_hash,
        )
        if candidate.metadata:
            adapter_metadata = dict(candidate.metadata)
            signal_metadata = adapter_metadata.pop("signal_metadata", None)
            if isinstance(signal_metadata, dict):
                metadata = _merge_candidate_signal_metadata(metadata, signal_metadata)
            if adapter_metadata:
                metadata["adapter"] = adapter_metadata
        signal.metadata = _compact_metadata(metadata)
        return signal

    def _evaluate_builtin_strategy(
        self, request: StrategyAdapterRequest
    ) -> StrategyAdapterResponse:
        adapter_id = getattr(self.strategy_adapter, "adapter_id", "UNKNOWN")
        market_data_obj = request.runtime_context.get("market_data_obj")
        if isinstance(market_data_obj, MarketData):
            market_data = market_data_obj
        else:
            market_data = MarketData.from_dict(dict(request.market_event))

        if self.config.strategy_id == PRIMARY_BREAKOUT_V1_STRATEGY_ID:
            breakout_signal = self._process_primary_breakout_v1(
                market_data,
                dict(request.market_event),
            )
            if breakout_signal is None:
                return StrategyAdapterResponse(
                    diagnostics={
                        "adapter_id": adapter_id,
                        "status": "no_signal",
                    }
                )
            return StrategyAdapterResponse(
                signals=(
                    StrategySignalCandidate(
                        strategy_id=breakout_signal.strategy_id,
                        symbol=breakout_signal.symbol,
                        side=breakout_signal.side,
                        reason=breakout_signal.reason,
                        confidence=breakout_signal.confidence,
                        price=breakout_signal.price,
                        pct_change=breakout_signal.pct_change,
                        metadata={
                            "adapter_id": adapter_id,
                            "signal_metadata": breakout_signal.metadata or {},
                        },
                    ),
                ),
                diagnostics={
                    "adapter_id": adapter_id,
                    "status": "signal_emitted",
                },
            )

        if (
            market_data.pct_change is None
            or market_data.pct_change < self.config.threshold_pct
            or market_data.volume < self.config.min_volume
        ):
            return StrategyAdapterResponse(
                diagnostics={
                    "adapter_id": adapter_id,
                    "status": "no_signal",
                    "pct_change": market_data.pct_change,
                    "threshold_pct": self.config.threshold_pct,
                    "volume": market_data.volume,
                    "min_volume": self.config.min_volume,
                }
            )

        return StrategyAdapterResponse(
            signals=(
                StrategySignalCandidate(
                    strategy_id=self.config.strategy_id,
                    symbol=market_data.symbol,
                    side="BUY",
                    reason=(
                        f"Momentum: {market_data.pct_change:+.4f}% > "
                        f"{self.config.threshold_pct}%"
                    ),
                    price=market_data.price,
                    pct_change=market_data.pct_change,
                    metadata={"adapter_id": adapter_id},
                ),
            ),
            diagnostics={
                "adapter_id": adapter_id,
                "status": "signal_emitted",
            },
        )

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

    def _load_market_state(self, symbol: str) -> dict[str, Any]:
        if not self.redis_client:
            return {}

        tried: list[str] = []
        for prefix in (
            self.config.market_state_key_prefix,
            "market_state",
            "market_state_shadow",
        ):
            if prefix in tried:
                continue
            tried.append(prefix)
            key = f"{prefix}:{symbol}"
            raw = self.redis_client.get(key)
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid market_state JSON at key=%s", key)
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _update_breakout_history(
        self, symbol: str, high_now: float, low_now: float, now_ms: int
    ) -> None:
        max_lookback_min = max(
            self.config.entry_lookback_minutes, self.config.exit_lookback_minutes
        )
        limit_ms = now_ms - max_lookback_min * 60 * 1000

        highs = self._high_history[symbol]
        lows = self._low_history[symbol]

        highs.append((now_ms, high_now))
        lows.append((now_ms, low_now))

        # Prune old entries
        while highs and highs[0][0] < limit_ms:
            highs.pop(0)
        while lows and lows[0][0] < limit_ms:
            lows.pop(0)

    def _process_primary_breakout_v1(
        self, market_data: MarketData, raw_data: dict[str, Any]
    ) -> Optional[Signal]:
        symbol = market_data.symbol.upper()
        if symbol != self.config.symbol:
            return None

        config_snapshot = _build_runtime_config_snapshot(self.config)
        config_hash = _build_config_hash(config_snapshot)
        close_now = float(market_data.close or market_data.price)
        high_now = float(market_data.high or close_now)
        low_now = float(market_data.low or close_now)
        now_ms = int(market_data.timestamp or int(time.time() * 1000))

        # Time-based windowing
        entry_lookback_ms = self.config.entry_lookback_minutes * 60_000
        exit_lookback_ms = self.config.exit_lookback_minutes * 60_000

        entry_limit = now_ms - entry_lookback_ms
        exit_limit = now_ms - exit_lookback_ms

        prior_high_entries = [e for e in self._high_history[symbol] if e[0] >= entry_limit]
        prior_low_entries = [e for e in self._low_history[symbol] if e[0] >= exit_limit]

        prior_highs = [p for ts, p in prior_high_entries]
        prior_lows = [p for ts, p in prior_low_entries]

        # Warmup check: Do we have at least the required history span in the CURRENT window?
        entry_warmup_ok = (
            bool(prior_high_entries)
            and (now_ms - min(ts for ts, _ in prior_high_entries)) >= entry_lookback_ms
        )
        exit_warmup_ok = (
            bool(prior_low_entries)
            and (now_ms - min(ts for ts, _ in prior_low_entries)) >= exit_lookback_ms
        )

        highest_high = (
            max(prior_highs)
            if prior_highs and entry_warmup_ok
            else None
        )
        lowest_low = (
            min(prior_lows)
            if prior_lows and exit_warmup_ok
            else None
        )

        market_state = self._load_market_state(symbol)
        regime_id = raw_data.get("regime_id", market_state.get("regime_id"))
        state_ts_ms = market_state.get("ts_ms")
        market_state_fresh = False
        regime_fresh = False
        if isinstance(state_ts_ms, (int, float)):
            market_state_fresh = (
                now_ms - int(state_ts_ms)
            ) <= self.config.market_state_staleness_s * 1000
            regime_fresh = market_state_fresh and regime_id is not None
        if not market_state_fresh and "market_state_fresh" in raw_data:
            market_state_fresh = _as_bool(raw_data["market_state_fresh"])
        if not regime_fresh and "regime_fresh" in raw_data:
            regime_fresh = _as_bool(raw_data["regime_fresh"])

        has_trend_regime = regime_id in {0, "TREND"} or paper_evidence_probe_enabled()
        entry_blocked = any(
            _as_bool(raw_data.get(name))
            or _as_bool(market_state.get(name))
            for name in (
                "shutdown_active",
                "kill_switch_active",
                "risk_blocked",
                "allocation_blocked",
                "core_blocked",
            )
        )

        cooldown_active = False
        if symbol in self._last_entry_ts_ms:
            cooldown_ms = self.config.min_minutes_between_entries * 60 * 1000
            cooldown_active = now_ms - self._last_entry_ts_ms[symbol] < cooldown_ms

        # Signal Logic
        result_signal = None

        # Exits are allowed even when entry gates are blocked.
        if (
            self._position_open_by_symbol[symbol]
            and lowest_low is not None
            and close_now < lowest_low
        ):
            result_signal = Signal(
                signal_id=f"sig-{generate_uuid_hex(length=32)}",
                symbol=symbol,
                side="SELL",
                reason="channel_exit",
                timestamp=now_ms // 1000,
                ts_ms=now_ms,
                price=close_now,
                pct_change=market_data.pct_change,
                pct_change_15m=market_data.pct_change,
                volume_15m=market_data.volume,
                strategy_id=self.config.strategy_id,
                bot_id=self.config.bot_id,
            )
            result_signal.metadata = _compact_metadata(
                {
                    **_build_signal_metadata(
                        result_signal,
                        config_snapshot=config_snapshot,
                        config_hash=config_hash,
                    ),
                    "regime_id": regime_id,
                    "close_now": close_now,
                    "highest_high": highest_high,
                    "lowest_low": lowest_low,
                    "entry_lookback_minutes": self.config.entry_lookback_minutes,
                    "exit_lookback_minutes": self.config.exit_lookback_minutes,
                    "breakout_buffer": self.config.breakout_buffer,
                    "min_minutes_between_entries": self.config.min_minutes_between_entries,
                    "trade_side_mode": self.config.trade_side_mode,
                }
            )
            self._position_open_by_symbol[symbol] = False

        else:
            entry_ready = (
                highest_high is not None
                and market_state_fresh
                and regime_fresh
                and has_trend_regime
                and not entry_blocked
                and not cooldown_active
                and close_now > highest_high * (1 + self.config.breakout_buffer)
            )
            if entry_ready:
                result_signal = Signal(
                    signal_id=f"sig-{generate_uuid_hex(length=32)}",
                    symbol=symbol,
                    side="BUY",
                    reason="breakout_entry",
                    timestamp=now_ms // 1000,
                    ts_ms=now_ms,
                    price=close_now,
                    pct_change=market_data.pct_change,
                    pct_change_15m=market_data.pct_change,
                    volume_15m=market_data.volume,
                    strategy_id=self.config.strategy_id,
                    bot_id=self.config.bot_id,
                )
                result_signal.metadata = _compact_metadata(
                    {
                        **_build_signal_metadata(
                            result_signal,
                            config_snapshot=config_snapshot,
                            config_hash=config_hash,
                        ),
                        "regime_id": regime_id,
                        "close_now": close_now,
                        "highest_high": highest_high,
                        "lowest_low": lowest_low,
                        "entry_lookback_minutes": self.config.entry_lookback_minutes,
                        "exit_lookback_minutes": self.config.exit_lookback_minutes,
                        "breakout_buffer": self.config.breakout_buffer,
                        "min_minutes_between_entries": self.config.min_minutes_between_entries,
                        "trade_side_mode": self.config.trade_side_mode,
                    }
                )
                self._last_entry_ts_ms[symbol] = now_ms
                self._position_open_by_symbol[symbol] = True

        # Append AFTER decision
        self._update_breakout_history(symbol, high_now, low_now, now_ms)
        return result_signal

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

            response = self.strategy_adapter.evaluate(
                StrategyAdapterRequest(
                    symbol=market_data.symbol,
                    market_event=data,
                    market_snapshot=self._build_market_snapshot(market_data),
                    runtime_context=self._build_strategy_runtime_context(market_data),
                )
            )
            if response.signals:
                signal = self._signal_from_candidate(response.signals[0], market_data)
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
        if self.config.strategy_id == PRIMARY_BREAKOUT_V1_STRATEGY_ID:
            logger.info("   Strategie: primary_breakout_v1")
            logger.info(
                "   Entry/Exit Lookback: %s/%s min",
                self.config.entry_lookback_minutes,
                self.config.exit_lookback_minutes,
            )
            logger.info("   Breakout Buffer: %s", self.config.breakout_buffer)
        else:
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
