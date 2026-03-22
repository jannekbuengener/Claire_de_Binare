"""
Risk Manager - Main Service
Multi-Layer Risk Management
"""

from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import json
import logging
import logging.config
import math
import os
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Optional

import psycopg2
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

from core.utils.uuid_gen import (
    generate_uuid,
    generate_decision_pk,
    compute_input_snapshot_hash,
    compute_correlation_id,
    compute_event_pk,
    compute_policy_hash,  # Phase 9
    compute_output_hash,  # Phase 9
    POLICY_ID,  # Phase 9
)
from core.utils.clock import utcnow
from core.utils.redis_payload import sanitize_payload
from core.utils.redis_client import create_redis_client
from core.utils.trace_toggle import trace_contract_v1_enabled, allow_evidence_debt

if TYPE_CHECKING:
    from core.replay.publisher import EnvelopePublisher

from core.replay.policy_snapshot import (
    build_policy_snapshot,
    policy_snapshot_binding_enabled,
)
from core.contracts.decision_contract_v1 import (
    DecisionContractError,
    build_decision_contract_v1_bundle,
    verify_decision_contract_v1_bundle,
    write_decision_contract_audit_record,
)
from core.safety.kill_switch import (
    get_kill_switch_details,
    resolve_kill_switch_state_file,
    KillSwitch,
    KillSwitchReason,
)
from core.auth import validate_all_auth
from core.domain.models import Signal

try:
    from .config import config
    from .models import Order, Alert, RiskState, OrderResult
    from .reason_codes import (
        RC_001,
        RC_002,
        RC_003,
        RC_004,
        RC_010,
        RC_020,
        RC_021,
        RC_022,
    )
    from .balance_fetcher import RealBalanceFetcher
except ImportError:
    # Fallback for script/importlib execution: ensure repo root is on sys.path.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from services.risk.config import config
    from services.risk.models import Order, Alert, RiskState, OrderResult

# Phase 8C: Evidence debt safety valve (default: fail-closed)
# Modul-Level-Konstante entfernt; allow_evidence_debt() aus core.utils.trace_toggle

# Phase 9: Trace Contract v1 toggle → zentral in core.utils.trace_toggle
# (Modul-Level-Konstante entfernt; trace_contract_v1_enabled() wird direkt aufgerufen)

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

logger = logging.getLogger("risk_manager")

# Globale Stats
stats = {
    "started_at": None,
    "signals_received": 0,
    "orders_approved": 0,
    "orders_blocked": 0,
    "orders_skipped": 0,  # NEW: qty=0, silent drops
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


def _envelope_toggle_enabled() -> bool:
    primary = os.getenv("CDB_ENVELOPE_EMISSION")
    if primary is not None:
        return primary == "1"
    return os.getenv("LR021_ENVELOPE_EMIT_ENABLED", "0") == "1"


@dataclass
class AllocationState:
    allocation_pct: float = 0.0
    cooldown_until: int | None = None


DECISION_CONTRACT_VERSION = "decision_contract_v1"
# Canonical quantity precision: bundles serialise to 8 decimal places.
_CANONICAL_QTY_DP = Decimal("0.00000001")
DECISION_ALLOW = "ALLOW"
DECISION_BLOCK = "BLOCK"
KILL_SWITCH_BLOCK_REASON_CODE = "KILL_SWITCH_ACTIVE"
KILL_SWITCH_UNEVALUABLE_REASON_CODE = "KILL_SWITCH_UNEVALUABLE"

DECISION_THRESHOLDS = {
    "return_1m_min": -2.0,
    "return_5m_min": -5.0,
    "price_change_5m_abs_max": 10.0,
    "staleness_s_max": 5.0,
    "data_silence_s_max": 30.0,
    # P90-calibrated thresholds (see RISK_RC002_CALIBRATION_EVIDENCE.md)
    # Data arrives as fractions (0.01 = 1%), not percentages
    "signal_pct_change_15m_min": 0.03,  # ~10% pass rate (P90 = 0.034)
    "signal_volume_15m_min": 0.165,  # ~10% pass rate (P90 = 0.166)
    "daily_drawdown_pct_max": 5.0,
    "total_exposure_pct_max": 50.0,
    "slippage_pct_max": 1.0,
    "allowed_regimes": [0, 1],
    "blocked_regimes": [2, 3],
}


def _get_value(obj: object | None, key: str):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _parse_number(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        if not math.isfinite(parsed):
            return None
        return parsed
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = float(raw)
        except ValueError:
            return None
        if not math.isfinite(parsed):
            return None
        return parsed
    return None


def _parse_int(value) -> int | None:
    parsed = _parse_number(value)
    if parsed is None:
        return None
    if not float(parsed).is_integer():
        return None
    return int(parsed)


def decide_trade(
    signal,
    market_state,
    account_state,
    market_health,
    now_ms,
) -> tuple[str, str | None, dict]:
    # Generate correlation IDs for replay/audit (Correlation Backbone)
    decision_id = generate_uuid()
    trace_id = generate_uuid()
    signal_id = _get_value(signal, "signal_id")  # Preserve from Signal service

    now_ms_value = _parse_int(now_ms)
    symbol = _get_value(signal, "symbol")

    pct_change_15m = _parse_number(_get_value(signal, "pct_change_15m"))
    volume_15m = _parse_number(_get_value(signal, "volume_15m"))
    signal_ts_ms = _parse_int(_get_value(signal, "ts_ms"))

    regime_id = _parse_int(_get_value(market_state, "regime_id"))
    return_1m = _parse_number(_get_value(market_state, "return_1m"))
    return_5m = _parse_number(_get_value(market_state, "return_5m"))
    price_change_5m = _parse_number(_get_value(market_state, "price_change_5m"))
    market_state_ts_ms = _parse_int(_get_value(market_state, "ts_ms"))
    last_tick_ts_ms = _parse_int(_get_value(market_state, "last_tick_ts_ms"))

    daily_drawdown_pct = _parse_number(_get_value(account_state, "daily_drawdown_pct"))
    total_exposure_pct = _parse_number(_get_value(account_state, "total_exposure_pct"))
    account_state_ts_ms = _parse_int(_get_value(account_state, "ts_ms"))

    slippage_pct = _parse_number(_get_value(market_health, "slippage_pct"))
    market_health_ts_ms = _parse_int(_get_value(market_health, "ts_ms"))

    # Staleness V2: Compute from available timestamps (market_health optional)
    staleness_candidates = []
    staleness_sources = []
    if signal_ts_ms is not None:
        staleness_candidates.append(signal_ts_ms)
        staleness_sources.append("signal")
    if market_state_ts_ms is not None:
        staleness_candidates.append(market_state_ts_ms)
        staleness_sources.append("market_state")
    if account_state_ts_ms is not None:
        staleness_candidates.append(account_state_ts_ms)
        staleness_sources.append("account_state")
    if market_health_ts_ms is not None:
        staleness_candidates.append(market_health_ts_ms)
        staleness_sources.append("market_health")

    max_ts_ms = None
    staleness_s = None
    if now_ms_value is not None and staleness_candidates:
        max_ts_ms = max(staleness_candidates)
        staleness_s = (now_ms_value - max_ts_ms) / 1000.0

    data_silence_s = None
    if now_ms_value is not None and last_tick_ts_ms is not None:
        data_silence_s = (now_ms_value - last_tick_ts_ms) / 1000.0

    evidence = {
        "contract_version": DECISION_CONTRACT_VERSION,
        # Correlation IDs for replay/audit (Correlation Backbone)
        "signal_id": signal_id,
        "decision_id": decision_id,
        "trace_id": trace_id,
        "timestamp_ms": now_ms_value,
        "symbol": symbol,
        "regime_id": regime_id,
        "return_1m": return_1m,
        "return_5m": return_5m,
        "price_change_5m": price_change_5m,
        "pct_change_15m": pct_change_15m,
        "volume_15m": volume_15m,
        "daily_drawdown_pct": daily_drawdown_pct,
        "total_exposure_pct": total_exposure_pct,
        "slippage_pct": slippage_pct,
        "staleness_s": staleness_s,
        "staleness_sources": staleness_sources,
        "data_silence_s": data_silence_s,
        "thresholds": DECISION_THRESHOLDS.copy(),
        "timestamps_ms": {
            "now_ms": now_ms_value,
            "signal_ts_ms": signal_ts_ms,
            "market_state_ts_ms": market_state_ts_ms,
            "account_state_ts_ms": account_state_ts_ms,
            "market_health_ts_ms": market_health_ts_ms,
            "last_tick_ts_ms": last_tick_ts_ms,
            "max_ts_ms": max_ts_ms,
        },
    }

    # 1) Safety/Anomaly
    if return_1m is None or return_5m is None or price_change_5m is None:
        return DECISION_BLOCK, RC_002, evidence
    if (
        return_1m <= DECISION_THRESHOLDS["return_1m_min"]
        or return_5m <= DECISION_THRESHOLDS["return_5m_min"]
        or abs(price_change_5m) > DECISION_THRESHOLDS["price_change_5m_abs_max"]
    ):
        return DECISION_BLOCK, RC_002, evidence

    # 2) Data Freshness
    if staleness_s is None:
        return DECISION_BLOCK, RC_003, evidence
    if staleness_s > DECISION_THRESHOLDS["staleness_s_max"]:
        return DECISION_BLOCK, RC_003, evidence
    if data_silence_s is None:
        return DECISION_BLOCK, RC_004, evidence
    if data_silence_s > DECISION_THRESHOLDS["data_silence_s_max"]:
        return DECISION_BLOCK, RC_004, evidence

    # 3) Regime
    if regime_id is None or regime_id not in {0, 1, 2, 3}:
        return DECISION_BLOCK, RC_001, evidence
    if regime_id in {2, 3}:
        return DECISION_BLOCK, RC_001, evidence

    # 4) Signal
    if symbol is None or symbol == "" or pct_change_15m is None or volume_15m is None:
        return DECISION_BLOCK, RC_010, evidence
    if (
        pct_change_15m < DECISION_THRESHOLDS["signal_pct_change_15m_min"]
        or volume_15m < DECISION_THRESHOLDS["signal_volume_15m_min"]
    ):
        return DECISION_BLOCK, RC_010, evidence

    # 5) Portfolio/Execution
    if daily_drawdown_pct is None:
        return DECISION_BLOCK, RC_020, evidence
    if daily_drawdown_pct >= DECISION_THRESHOLDS["daily_drawdown_pct_max"]:
        return DECISION_BLOCK, RC_020, evidence
    if total_exposure_pct is None:
        return DECISION_BLOCK, RC_021, evidence
    if total_exposure_pct >= DECISION_THRESHOLDS["total_exposure_pct_max"]:
        return DECISION_BLOCK, RC_021, evidence
    # RC_022: Slippage check - skip ONLY if market_health not available
    # If market_health exists but slippage_pct is invalid → still block
    if slippage_pct is not None:
        if slippage_pct > DECISION_THRESHOLDS["slippage_pct_max"]:
            return DECISION_BLOCK, RC_022, evidence

    return DECISION_ALLOW, None, evidence


def _phase9_enrich_evidence(
    evidence: dict,
    decision: str,
    reason_code: str | None,
    symbol: str,
    ts_ms: int,
) -> tuple[dict, str | None, str | None]:
    """
    Phase 9: Enrich evidence with policy governance fields for Trace Contract v1.

    MUST be called ONCE before both:
    - emitting DECISION event
    - creating Order object

    Args:
        evidence: The evidence dict from decide_trade() (mutated in place when toggle ON)
        decision: "ALLOW" or "BLOCK"
        reason_code: RC_XXX or None
        symbol: Trading symbol
        ts_ms: Deterministischer Timestamp für decision_pk (signal_ts_ms, NICHT wall-clock)

    Returns:
        (enriched_evidence, input_hash, decision_pk)
        - When toggle OFF: returns (evidence, None, None) - ZERO IMPACT
        - When toggle ON: returns enriched evidence with computed hashes
    """
    # ZERO-IMPACT when toggle OFF: no mutations, no validations, no computations
    if not trace_contract_v1_enabled():
        return evidence, None, None

    # Toggle ON: proceed with enrichment

    # Ensure thresholds are set BEFORE computing hashes
    # (so input_hash/decision_pk reflect the same immutable context)
    # Use deepcopy because DECISION_THRESHOLDS contains lists (allowed_regimes, blocked_regimes)
    if "thresholds" not in evidence or evidence["thresholds"] is None:
        evidence["thresholds"] = copy.deepcopy(DECISION_THRESHOLDS)

    # Compute hashes ONCE (deterministic, AFTER thresholds are set)
    input_hash = compute_input_snapshot_hash(evidence)
    decision_pk = generate_decision_pk(symbol, ts_ms, evidence)

    # Compute policy_hash from evidence["thresholds"] (same as used in input_hash)
    policy_hash = compute_policy_hash(evidence["thresholds"])

    # Enrich evidence with Phase 9 fields
    evidence["policy_id"] = POLICY_ID
    evidence["policy_hash"] = policy_hash
    evidence["input_hash"] = (
        input_hash  # alias, keep input_snapshot_hash for backwards compat
    )

    # output_hash uses the SAME decision_pk that will be written to event
    evidence["output_hash"] = compute_output_hash(
        decision=decision,
        reason_code=reason_code,
        decision_pk=decision_pk,
        decision_id=evidence.get("decision_id"),
        contract_version=evidence.get("contract_version", DECISION_CONTRACT_VERSION),
        input_hash=input_hash,
        policy_hash=policy_hash,
    )

    # Minimal immutable decision_context for replay
    evidence["decision_context"] = {
        "thresholds": evidence["thresholds"],
        "inputs": {
            "regime_id": evidence.get("regime_id"),
            "return_1m": evidence.get("return_1m"),
            "return_5m": evidence.get("return_5m"),
            "price_change_5m": evidence.get("price_change_5m"),
            "pct_change_15m": evidence.get("pct_change_15m"),
            "volume_15m": evidence.get("volume_15m"),
            "daily_drawdown_pct": evidence.get("daily_drawdown_pct"),
            "total_exposure_pct": evidence.get("total_exposure_pct"),
            "slippage_pct": evidence.get("slippage_pct"),
            "staleness_s": evidence.get("staleness_s"),
            "data_silence_s": evidence.get("data_silence_s"),
        },
        "contract_version": DECISION_CONTRACT_VERSION,
    }

    return evidence, input_hash, decision_pk


class RiskManager:
    """Multi-Layer Risk-Management"""

    def __init__(self):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.balance_fetcher: Optional[RealBalanceFetcher] = None
        if self.config.use_real_balance:
            try:
                self.balance_fetcher = RealBalanceFetcher()
                logger.info("RealBalanceFetcher initialisiert")
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren von RealBalanceFetcher: {e}")
        self.pubsub: Optional[redis.client.PubSub] = None
        self.pubsub_results: Optional[redis.client.PubSub] = None
        self._order_result_thread: Optional[Thread] = None
        self._regime_thread: Optional[Thread] = None
        self._allocation_thread: Optional[Thread] = None
        self._shutdown_thread: Optional[Thread] = None
        self.running = False
        self.allocation_state: dict[str, AllocationState] = {}
        self._circuit_shutdown_emitted = False
        self._pg_conn: Optional[psycopg2.extensions.connection] = None
        self._envelope_redis_client: Optional[redis.Redis] = None
        self._envelope_publisher: EnvelopePublisher | None = None

        # Validiere Config
        try:
            self.config.validate()
            logger.info("Config validiert ✓")
        except ValueError as e:
            logger.error(f"Config-Fehler: {e}")
            sys.exit(1)

    # --- LR-762: Kill-switch gate + Decision Contract enforcement ---

    def _kill_switch_gate(self) -> tuple[bool, str, dict]:
        """Evaluate kill-switch state for fail-closed execution gating."""
        try:
            active, reason, message, activated_at = get_kill_switch_details(
                create_if_missing=False
            )
        except Exception as exc:
            logger.exception("Kill-switch evaluation failed (fail-closed)")
            return (
                True,
                KILL_SWITCH_UNEVALUABLE_REASON_CODE,
                {
                    "reason": None,
                    "message": f"kill-switch evaluation error: {exc}",
                    "activated_at": None,
                },
            )
        if not active:
            return False, "", {}
        return (
            True,
            KILL_SWITCH_BLOCK_REASON_CODE,
            {
                "reason": reason,
                "message": message,
                "activated_at": activated_at,
            },
        )

    @staticmethod
    def _to_ms_timestamp(value: object) -> int:
        if value is None or isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            if value <= 0:
                return 0
            as_int = int(value)
            return as_int * 1000 if as_int < 10_000_000_000 else as_int
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return 0
            try:
                parsed = float(raw)
            except ValueError:
                return 0
            if parsed <= 0:
                return 0
            as_int = int(parsed)
            return as_int * 1000 if as_int < 10_000_000_000 else as_int
        return 0

    def _resolve_contract_run_mode(
        self,
        *,
        strategy_id: str | None = None,
        payload: dict | None = None,
        run_mode_override: str | None = None,
    ) -> str:
        candidates: list[str | None] = [run_mode_override]
        if isinstance(payload, dict):
            candidates.append(payload.get("run_mode"))
        candidates.extend([os.getenv("RUN_MODE"), os.getenv("TRADING_MODE")])
        for candidate in candidates:
            if not candidate:
                continue
            mode = str(candidate).strip().lower()
            if mode == "staged":
                mode = "shadow"
            if mode in {"shadow", "paper", "replay", "live"}:
                return mode
        strategy_mode = (strategy_id or "").strip().lower()
        if strategy_mode in {"shadow", "paper", "replay", "live"}:
            return strategy_mode
        return "paper"

    def _build_decision_contract_input(
        self,
        order: Order,
        *,
        source: str,
        account_state_snapshot: dict | None = None,
        payload: dict | None = None,
        run_mode_override: str | None = None,
    ) -> dict:
        if account_state_snapshot is None:
            account_state_snapshot = {}

        balance_usdt = float(self.config.test_balance)
        if "balance_usdt" in account_state_snapshot:
            parsed_balance = _parse_number(account_state_snapshot.get("balance_usdt"))
            if parsed_balance is not None:
                balance_usdt = parsed_balance
        if balance_usdt <= 0:
            raise DecisionContractError(
                "balance_usdt must be > 0 for contract evaluation"
            )

        daily_drawdown_pct = _parse_number(
            account_state_snapshot.get("daily_drawdown_pct")
        )
        if daily_drawdown_pct is None:
            daily_drawdown_pct = (
                max(0.0, -float(risk_state.daily_pnl) / balance_usdt * 100.0)
                if balance_usdt > 0
                else 0.0
            )

        total_exposure_usdt = float(risk_state.total_exposure) + float(
            risk_state.pending_exposure_usdt
        )
        price_ref = float(order.price or risk_state.last_prices.get(order.symbol, 0.0))
        if price_ref <= 0:
            raise DecisionContractError(
                f"price_ref unavailable for order {order.symbol} ({source})"
            )

        timestamp_input_ms = self._to_ms_timestamp(order.timestamp)
        if timestamp_input_ms <= 0:
            timestamp_input_ms = self._to_ms_timestamp(
                account_state_snapshot.get("ts_ms")
                or account_state_snapshot.get("timestamp_ms")
            )

        max_notional_usdt = balance_usdt * float(self.config.max_position_pct)
        max_total_exposure_usdt = balance_usdt * float(
            self.config.max_total_exposure_pct
        )
        max_daily_drawdown_pct = float(self.config.max_daily_drawdown_pct) * 100.0

        open_positions = {
            symbol: str(qty)
            for symbol, qty in sorted(
                risk_state.positions.items(), key=lambda item: item[0]
            )
        }

        return {
            "run_mode": self._resolve_contract_run_mode(
                strategy_id=order.strategy_id,
                payload=payload,
                run_mode_override=run_mode_override,
            ),
            "order": {
                "symbol": order.symbol,
                "side": order.side,
                "quantity": str(order.quantity),
                "price_ref": str(price_ref),
                "timestamp_input_ms": int(timestamp_input_ms),
                "reduce_only": bool(
                    order.side == "SELL"
                    and risk_state.positions.get(order.symbol, 0.0) > 0.0
                ),
            },
            "account_state": {
                "balance_usdt": str(balance_usdt),
                "total_exposure_usdt": str(total_exposure_usdt),
                "daily_drawdown_pct": str(daily_drawdown_pct),
            },
            "open_positions": open_positions,
            "risk_policy": {
                "max_notional_usdt": str(max_notional_usdt),
                "max_total_exposure_usdt": str(max_total_exposure_usdt),
                "max_daily_drawdown_pct": str(max_daily_drawdown_pct),
            },
            "system_config": {
                "paper_auto_unwind": bool(self.config.paper_auto_unwind),
                "use_real_balance": bool(self.config.use_real_balance),
                "service": "risk_manager",
            },
            "context": {
                "source": source,
                "signal_id": order.signal_id or "",
                "strategy_id": order.strategy_id or "",
                "bot_id": order.bot_id or "",
            },
        }

    def _ensure_decision_contract_for_order(
        self,
        order: Order,
        *,
        source: str,
        account_state_snapshot: dict | None = None,
        payload: dict | None = None,
        run_mode_override: str | None = None,
    ) -> dict:
        bundle = order.decision_contract_v1
        if bundle is None:
            contract_input = self._build_decision_contract_input(
                order,
                source=source,
                account_state_snapshot=account_state_snapshot,
                payload=payload,
                run_mode_override=run_mode_override,
            )
            bundle = build_decision_contract_v1_bundle(contract_input)
        ok, reason = verify_decision_contract_v1_bundle(bundle, require_allow=True)
        if not ok:
            raise DecisionContractError(reason)

        # --- HARDENING FIX 1: Strict order-identity binding ---
        # The bundle must match the active order's identity fields.
        # Without this check, a stale/injected bundle could pass verification.
        bundle_order = bundle.get("input", {}).get("order", {})
        if bundle_order.get("symbol") != order.symbol:
            raise DecisionContractError(
                f"Contract bundle symbol mismatch: "
                f"bundle={bundle_order.get('symbol')!r} vs order={order.symbol!r}"
            )
        if bundle_order.get("side") != order.side:
            raise DecisionContractError(
                f"Contract bundle side mismatch: "
                f"bundle={bundle_order.get('side')!r} vs order={order.side!r}"
            )
        bundle_qty_str = str(bundle_order.get("quantity", ""))
        order_qty_str = str(order.quantity)
        # Normalise both to 8 dp (bundle canonical precision) before comparing.
        # This absorbs serialisation rounding without opening the gate to genuine
        # quantity mismatches, which differ by more than 0.5 ULP at 8 dp.
        try:
            bundle_qty_d = Decimal(bundle_qty_str).quantize(
                _CANONICAL_QTY_DP, rounding=ROUND_HALF_EVEN
            )
            order_qty_d = Decimal(order_qty_str).quantize(
                _CANONICAL_QTY_DP, rounding=ROUND_HALF_EVEN
            )
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise DecisionContractError(
                f"Contract bundle quantity not comparable: "
                f"bundle={bundle_qty_str!r} vs order={order_qty_str!r}"
            ) from exc
        if bundle_qty_d != order_qty_d:
            raise DecisionContractError(
                f"Contract bundle quantity mismatch: "
                f"bundle={bundle_qty_str!r} vs order={order_qty_str!r}"
            )

        audit_path = write_decision_contract_audit_record(bundle)
        evidence = bundle["output"]["evidence"]
        order.decision_contract_v1 = bundle
        if not order.decision_id:
            order.decision_id = f"dcv1-{evidence['decision_hash'][:16]}"

        # --- HARDENING FIX 2: Always overwrite hash provenance ---
        # Unconditionally set order hashes from contract evidence.
        # The previous code only set when None, allowing Phase9 trace hashes
        # to drift from contract evidence hashes.
        order.input_hash = evidence["input_hash"]
        order.output_hash = evidence["decision_hash"]

        logger.debug("Decision Contract audit written: %s", audit_path)
        return bundle

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
        else:
            self._setup_envelope_emitter()

    def _setup_envelope_emitter(self) -> None:
        if not _envelope_toggle_enabled():
            self._envelope_redis_client = None
            self._envelope_publisher = None
            return

        try:
            from core.replay.emitter import configure_envelope_emission
            from core.replay.publisher import EnvelopePublisher

            envelope_client = create_redis_client(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                db=self.config.redis_db,
                decode_responses=True,
            )
            mode = os.getenv("CDB_ENVELOPE_REDIS_MODE", "stream").lower()
            if mode != "pubsub":
                mode = "stream"
            stream = os.getenv("CDB_ENVELOPE_REDIS_STREAM", "cdb:envelopes:v1")
            channel = os.getenv("CDB_ENVELOPE_REDIS_CHANNEL", "cdb.envelopes.v1")
            publisher = EnvelopePublisher(
                redis_client=envelope_client,
                mode=mode,
                stream=stream,
                channel=channel,
            )
            self._envelope_redis_client = envelope_client
            self._envelope_publisher = publisher
            configure_envelope_emission(True, publisher)
            logger.info(
                "Envelope emission enabled (mode=%s stream=%s channel=%s)",
                mode,
                stream,
                channel,
            )
        except Exception:
            logger.exception("Envelope emission setup failed, disabling emission")
            try:
                configure_envelope_emission(False, None)
            except NameError:
                pass
            self._envelope_redis_client = None
            self._envelope_publisher = None

    def _get_postgres_conn(self) -> Optional[psycopg2.extensions.connection]:
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
            logger.error(f"❌ Failed to connect Postgres for risk events: {e}")
            self._pg_conn = None
            return None

    def _persist_risk_event(self, event: dict) -> bool:
        """
        Persist risk_event to Postgres with idempotency guarantee.

        Returns True if persisted (or already exists), False on failure.
        Decision logic is independent - persist failure = evidence debt.

        Requires: decision_pk and input_snapshot_hash must be set in event.
        Gate: Migration 005 must be applied before this code is deployed.
        """
        decision_pk = event.get("decision_pk")
        if not decision_pk:
            logger.error("❌ risk_event missing decision_pk")
            return False

        max_retries = 3
        backoffs_ms = [0, 50, 100]

        for attempt in range(max_retries):
            if attempt > 0:
                time.sleep(backoffs_ms[attempt] / 1000.0)

            conn = self._get_postgres_conn()
            if conn is None:
                return False

            try:
                payload = json.dumps(event, allow_nan=False)
                cursor = conn.cursor()
                cursor.execute("SET LOCAL statement_timeout = '250ms'")
                cursor.execute(
                    """
                    INSERT INTO risk_events
                        (timestamp_ms, symbol, decision, reason_code, contract_version,
                         decision_pk, input_snapshot_hash, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_pk) DO NOTHING
                    """,
                    (
                        event.get("timestamp_ms"),
                        event.get("symbol"),
                        event.get("decision"),
                        event.get("reason_code"),
                        event.get("contract_version"),
                        decision_pk,
                        event.get("input_snapshot_hash"),
                        payload,
                    ),
                )
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ risk_event persist attempt {attempt+1}/{max_retries}: {e}"
                    )
                else:
                    logger.error(
                        f"❌ risk_event persist FAILED after {max_retries} attempts: {e}"
                    )
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
                self._pg_conn = None

        return False

    def _lookup_market_state(self, symbol: str) -> dict | None:
        """
        Lookup market_state V1 from Redis (BLUE-owned).

        Key: market_state:{symbol}
        Source: Candles Service computes returns from stream.candles_1m

        Fail-closed: Returns None if key missing/expired/invalid.
        BLACK does not compute returns - only validates and gates.
        """
        try:
            key = f"market_state:{symbol}"
            data = self.redis_client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except (json.JSONDecodeError, Exception):
            return None

    def _emit_risk_event(
        self,
        decision: str,
        reason_code: str | None,
        evidence: dict,
        decision_pk: str | None = None,
        input_hash: str | None = None,
    ) -> bool:
        """Emit risk event with deterministic decision_pk for idempotent persistence.

        Args:
            decision: "ALLOW" or "BLOCK"
            reason_code: RC_XXX or None
            evidence: The evidence dict from decide_trade
            decision_pk: Pre-computed decision_pk (Phase 9), or None to compute here
            input_hash: Pre-computed input_hash (Phase 9), or None to compute here
        """
        symbol = evidence.get("symbol", "")
        ts_ms = evidence.get("timestamp_ms", 0)

        # Use pre-computed values if provided (Phase 9), else compute (backwards compat)
        if input_hash is None:
            input_hash = compute_input_snapshot_hash(evidence)
        if decision_pk is None:
            decision_pk = generate_decision_pk(symbol, ts_ms, evidence)

        event = {
            **evidence,
            "decision": decision,
            "reason_code": reason_code,
            "decision_pk": decision_pk,
            "input_snapshot_hash": input_hash,
        }
        return self._persist_risk_event(event)

    def _persist_correlation_event(
        self,
        signal_id: str,
        event_type: str,
        symbol: str,
        timestamp_ms: int,
        decision_id: str | None = None,
        order_id: str | None = None,
        fill_id: str | None = None,
        payload: dict | None = None,
    ) -> bool:
        """
        Persist event to correlation_ledger (Phase 8C).

        Fail-closed: If signal_id missing, raises ValueError.
        ON CONFLICT (event_pk) DO NOTHING for idempotent writes.
        """
        if not signal_id:
            raise ValueError(
                "signal_id is required for correlation_ledger (fail-closed)"
            )

        try:
            canonical_event_type = event_type.upper()
            correlation_id = compute_correlation_id(signal_id)
            event_pk = compute_event_pk(
                signal_id, canonical_event_type, order_id, fill_id
            )

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
                    signal_id,
                    decision_id,
                    order_id,
                    fill_id,
                    canonical_event_type,
                    symbol,
                    timestamp_ms,
                    json.dumps(payload) if payload else None,
                ),
            )
            logger.debug(
                f"📊 correlation_ledger {canonical_event_type}: signal={signal_id}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ correlation_ledger write failed: {e}")
            return False

    def _persist_blocked_decision(
        self,
        signal_id: str,
        decision_id: str,
        symbol: str,
        reason_code: str,
        timestamp_ms: int,
        evidence: dict,
    ) -> bool:
        """
        Persist BLOCK decision to blocked_decisions (Phase 8C).

        Uses Phase 8B decision_pk algorithm for idempotency.
        ON CONFLICT (decision_pk) DO NOTHING.
        """
        if not signal_id:
            raise ValueError(
                "signal_id is required for blocked_decisions (fail-closed)"
            )

        try:
            decision_pk = generate_decision_pk(symbol, timestamp_ms, evidence)

            conn = self._get_postgres_conn()
            if conn is None:
                logger.warning("⚠️ blocked_decisions write skipped (no DB connection)")
                return False

            cursor = conn.cursor()
            cursor.execute("SET LOCAL statement_timeout = '250ms'")
            cursor.execute(
                """
                INSERT INTO blocked_decisions
                    (decision_pk, signal_id, decision_id, symbol, reason_code,
                     timestamp_ms, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (decision_pk) DO NOTHING
                """,
                (
                    decision_pk,
                    signal_id,
                    decision_id,
                    symbol,
                    reason_code,
                    timestamp_ms,
                    json.dumps(evidence),
                ),
            )
            logger.debug(
                f"📊 blocked_decisions: signal={signal_id} reason={reason_code}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ blocked_decisions write failed: {e}")
            return False

    def bootstrap_state_from_db(self):
        """
        Bootstrap risk state from positions table (source-of-truth).

        Reconciles in-memory risk state with persistent DB positions.
        This ensures risk manager operates on accurate state after restarts.

        Recovery strategy:
        - Query positions table for all open positions (closed_at IS NULL)
        - Rebuild risk_state.positions dict from DB
        - Calculate total_exposure from position sizes * current_prices
        - Log reconciliation results

        Safety gate:
        - If positions table empty BUT orders show net open position:
          FAIL-CLOSED with actionable error message
        - Prevents starting with incorrect state

        Called during startup before processing signals.
        """
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_db,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
            )
            cursor = conn.cursor()

            # Query open positions
            cursor.execute("""
                SELECT symbol, side, size, entry_price, current_price
                FROM positions
                WHERE closed_at IS NULL AND size > 0
                ORDER BY symbol
                """)
            positions = cursor.fetchall()

            if not positions:
                # SAFETY GATE: Check for state mismatch
                # If positions empty, but orders show net open position, FAIL
                logger.info("Positions table empty - checking for state mismatch...")

                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN side = 'buy' THEN filled_size ELSE 0 END), 0) as buy_total,
                        COALESCE(SUM(CASE WHEN side = 'sell' THEN filled_size ELSE 0 END), 0) as sell_total
                    FROM orders
                    WHERE status = 'filled'
                      AND filled_size > 0
                      AND created_at >= '2026-01-17 14:15:00'
                    """)
                buy_total, sell_total = cursor.fetchone()
                net_position = float(buy_total) - float(sell_total)

                # Threshold: consider position "open" if net > 0.0001 BTC (~$5 at 50k)
                POSITION_THRESHOLD = 0.0001

                if abs(net_position) > POSITION_THRESHOLD:
                    error_msg = (
                        f"\n{'=' * 80}\n"
                        f"❌ CRITICAL: STATE MISMATCH DETECTED\n"
                        f"{'=' * 80}\n"
                        f"Positions table: EMPTY (0 open positions)\n"
                        f"Orders table:    NET {net_position:.8f} BTC\n"
                        f"  BUY fills:     {buy_total:.8f} BTC\n"
                        f"  SELL fills:    {sell_total:.8f} BTC\n"
                        f"\n"
                        f"Risk manager CANNOT start with incorrect state.\n"
                        f"\n"
                        f"ACTION REQUIRED:\n"
                        f"Run positions reconciliation script to reconstruct positions table:\n"
                        f"\n"
                        f"  python infrastructure/scripts/reconcile_positions.py\n"
                        f"\n"
                        f"Or set POSTGRES_PASSWORD environment variable and run:\n"
                        f"\n"
                        f"  docker compose exec cdb_risk python infrastructure/scripts/reconcile_positions.py\n"
                        f"\n"
                        f"This will rebuild positions table from order history.\n"
                        f"After reconciliation completes, restart risk service.\n"
                        f"{'=' * 80}\n"
                    )
                    logger.critical(error_msg)
                    cursor.close()
                    conn.close()
                    raise RuntimeError(
                        "State mismatch: positions table empty but orders show open position"
                    )

                logger.info(
                    "✅ Risk state bootstrap: No open positions in DB (clean state)"
                )
                cursor.close()
                conn.close()
                return

            # Rebuild risk state
            global risk_state
            total_exposure = 0.0

            for symbol, side, size, entry_price, current_price in positions:
                # Convert side to position value (long=positive, short=negative)
                position_size = float(size) if side == "long" else -float(size)
                risk_state.positions[symbol] = position_size

                # Use current_price for exposure calculation (fallback to entry_price if NULL)
                price = float(current_price) if current_price else float(entry_price)
                risk_state.last_prices[symbol] = price

                # Calculate notional exposure
                exposure = abs(position_size) * price
                total_exposure += exposure

                logger.info(
                    "  Position loaded: %s %s %.8f @ %.2f (exposure: %.2f USD)",
                    symbol,
                    side.upper(),
                    abs(position_size),
                    price,
                    exposure,
                )

            # Update risk state
            risk_state.total_exposure = total_exposure
            risk_state.open_positions = len(positions)

            logger.info(
                "✅ Risk state bootstrap complete: %d positions, total exposure: %.2f USD",
                len(positions),
                total_exposure,
            )

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            logger.error(f"❌ Failed to bootstrap risk state from DB: {e}")
            logger.warning(
                "⚠️ Risk manager starting with EMPTY state (no reconciliation)"
            )
            # Continue startup with empty state rather than crashing
        except Exception as e:
            logger.error(f"❌ Unexpected error during risk state bootstrap: {e}")
            logger.warning(
                "⚠️ Risk manager starting with EMPTY state (no reconciliation)"
            )

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

    def _is_early_live_exception(self, strategy_id: str) -> bool:
        """Check if Early-Live exception applies (risk_off but small allocation)"""
        if not risk_off_active:
            return False
        allocation = self._get_allocation_state(strategy_id)
        return 0 < allocation.allocation_pct <= self.config.early_live_max_alloc

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
                        logger.info(
                            "Regime-Update: %s (risk_off=%s)", regime, risk_off_active
                        )
            except Exception as err:  # noqa: BLE001
                logger.error("Regime-Stream Fehler: %s", err)
                time.sleep(1)

    def _listen_allocation_stream(self):
        if not self.redis_client or not self.config.allocation_stream:
            return

        # Bootstrap: Read latest allocation to avoid missing state after restart
        last_id = "0-0"
        try:
            allocation_entries = self.redis_client.xrevrange(
                self.config.allocation_stream, "+", "-", count=10
            )
            seen_strategies = set()
            for entry_id, payload in allocation_entries:
                strategy_id = payload.get("strategy_id")
                if not strategy_id or strategy_id in seen_strategies:
                    continue
                seen_strategies.add(strategy_id)
                allocation_pct = float(payload.get("allocation_pct", 0.0))
                cooldown_until = self._parse_timestamp(payload.get("cooldown_until"))
                self.allocation_state[strategy_id] = AllocationState(
                    allocation_pct=allocation_pct,
                    cooldown_until=cooldown_until,
                )
                logger.info(
                    "Bootstrap allocation: strategy_id=%s allocation_pct=%.4f",
                    strategy_id,
                    allocation_pct,
                )
            if allocation_entries:
                last_id = allocation_entries[0][0]
        except Exception as e:
            logger.warning(f"Allocation bootstrap failed, starting from 0-0: {e}")

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
                        cooldown_until = self._parse_timestamp(
                            payload.get("cooldown_until")
                        )
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
        """
        Prüft das Positions-Limit für ein Symbol.
        Verhindert den Aufbau von Positionen, die das konfigurierte Limit (max_position_pct) überschreiten.
        """
        if self.config.use_real_balance and self.balance_fetcher:
            try:
                current_balance = self.balance_fetcher.get_usdt_balance()
            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Balance: {e}")
                return False, f"Balance-Fehler: {e}"
        else:
            current_balance = self.config.test_balance

        # Max. Notional-Wert pro Position (z.B. 10% des Kapitals)
        max_notional_usdt = current_balance * self.config.max_position_pct

        # Aktuelle Position und Preis ermitteln
        current_qty = risk_state.positions.get(signal.symbol, 0.0)
        current_price = signal.price or risk_state.last_prices.get(signal.symbol, 0.0)

        if current_price <= 0:
            # Ohne Preis können wir keine Notional-Prüfung machen.
            # Da calculate_position_size dies auch prüft, lassen wir es hier durch.
            return True, "Position OK (Preis unbekannt)"

        current_notional = abs(current_qty) * current_price

        # Wenn wir bereits am oder über dem Limit sind, blockieren wir weitere Positionsvergrößerungen.
        # Hinweis: Reduce-only Orders werden in process_signal vorab gefiltert und umgehen Exposure-Checks.
        if current_notional >= max_notional_usdt:
            return (
                False,
                f"Position für {signal.symbol} am Limit: {current_notional:.2f} >= {max_notional_usdt:.2f}",
            )

        return True, "Position OK"

    def check_exposure_limit(self) -> tuple[bool, str]:
        """Prüft Gesamt-Exposure (filled + pending reserved)"""
        if self.config.use_real_balance and self.balance_fetcher:
            try:
                current_balance = self.balance_fetcher.get_usdt_balance()
            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Balance: {e}")
                return False, f"Balance-Fehler: {e}"
        else:
            current_balance = self.config.test_balance

        max_exposure = current_balance * self.config.max_total_exposure_pct

        # PR #617: Include pending reserved exposure to prevent race condition
        effective_exposure = (
            risk_state.total_exposure + risk_state.pending_exposure_usdt
        )

        if effective_exposure >= max_exposure:
            return (
                False,
                f"Max Exposure erreicht: {effective_exposure:.2f} >= {max_exposure:.2f} "
                f"(filled: {risk_state.total_exposure:.2f}, pending: {risk_state.pending_exposure_usdt:.2f})",
            )

        return True, "Exposure OK"

    def check_drawdown_limit(self) -> tuple[bool, str]:
        """Prüft Daily-Drawdown (Circuit Breaker)"""
        if self.config.use_real_balance and self.balance_fetcher:
            try:
                current_balance = self.balance_fetcher.get_usdt_balance()
            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Balance: {e}")
                return False, f"Balance-Fehler: {e}"
        else:
            current_balance = self.config.test_balance

        max_drawdown = current_balance * self.config.max_daily_drawdown_pct

        if risk_state.daily_pnl <= -max_drawdown:
            risk_state.circuit_breaker_active = True
            return (
                False,
                f"Circuit Breaker! Daily Loss: {risk_state.daily_pnl:.2f} <= -{max_drawdown:.2f}",
            )

        return True, "Drawdown OK"

    def process_signal(
        self, signal: Signal, raw_payload: dict | None = None
    ) -> Optional[Order]:
        """Prüft Signal gegen alle Risk-Layers"""
        payload = raw_payload or {}

        # LR-762: Kill-switch gate (fail-closed, HARDENING FIX 3)
        kill_switch_active, kill_switch_code, kill_switch_context = (
            self._kill_switch_gate()
        )
        if kill_switch_active:
            block_message = (
                f"Kill-switch active: reason={kill_switch_context.get('reason') or 'unknown'}; "
                f"activated_at={kill_switch_context.get('activated_at') or 'unknown'}"
                if kill_switch_code == KILL_SWITCH_BLOCK_REASON_CODE
                else kill_switch_context.get("message", "kill-switch evaluation error")
            )
            self.send_alert(
                "CRITICAL",
                kill_switch_code,
                block_message,
                {
                    "signal_id": signal.signal_id,
                    "strategy_id": signal.strategy_id,
                    "symbol": signal.symbol,
                    "side": signal.side,
                },
            )
            logger.warning("Signal blockiert durch Kill-Switch: %s", block_message)
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        # Market State V1: Lookup from Redis (BLUE-owned, fail-closed)
        # Key: market_state:{symbol} - set by Candles Service with TTL
        market_state = payload.get("market_state")
        if market_state is None and signal.symbol:
            market_state = self._lookup_market_state(signal.symbol)

        account_state = payload.get("account_state")
        market_health = payload.get("market_health")
        now_ms = int(time.time() * 1000)

        decision, reason_code, evidence = decide_trade(
            signal=signal,
            market_state=market_state,
            account_state=account_state,
            market_health=market_health,
            now_ms=now_ms,
        )

        # Phase 9: Enrich evidence ONCE (before DECISION emit AND Order creation)
        # ts_ms: deterministisch (signal_ts_ms), NICHT wall-clock (now_ms).
        # Fallback auf now_ms nur wenn Signal kein ts_ms liefert (Compat).
        deterministic_ts_ms = (
            evidence.get("timestamps_ms", {}).get("signal_ts_ms") or now_ms
        )
        evidence, input_hash, decision_pk = _phase9_enrich_evidence(
            evidence=evidence,
            decision=decision,
            reason_code=reason_code,
            symbol=signal.symbol,
            ts_ms=deterministic_ts_ms,
        )

        # Issue #748 Slice 2: Build policy_snapshot (toggle-gated, default OFF)
        policy_snapshot = None
        if policy_snapshot_binding_enabled():
            try:
                policy_snapshot = build_policy_snapshot(
                    thresholds=evidence.get("thresholds") or DECISION_THRESHOLDS,
                    effective_at_ms=deterministic_ts_ms,
                )
            except Exception:
                pass  # Guardrail: never break trading path

        if evidence.get("decision_id"):
            if _envelope_toggle_enabled():
                try:
                    from core.replay.emitter import emit_decision_envelope

                    emit_decision_envelope(
                        event_id=str(evidence["decision_id"]),
                        ts_ms=deterministic_ts_ms,
                        decision=decision,
                        reason_code=reason_code,
                        symbol=signal.symbol,
                        evidence=evidence,
                        signal_id=evidence.get("signal_id"),
                        trace_id=evidence.get("trace_id"),
                        decision_context=evidence.get("decision_context"),
                        policy_id=evidence.get("policy_id"),
                        policy_hash=evidence.get("policy_hash"),
                        input_hash=evidence.get("input_hash"),
                        output_hash=evidence.get("output_hash"),
                        policy_snapshot=policy_snapshot,
                    )
                except RuntimeError:
                    raise
                except Exception:
                    logger.exception("Decision envelope emission failed")

        # Trace-Writes: nur wenn Toggle ON (Toggle OFF = zero side effects)
        signal_id = evidence.get("signal_id")
        decision_id = evidence.get("decision_id")

        if trace_contract_v1_enabled():
            # risk_events INSERT
            self._emit_risk_event(
                decision=decision,
                reason_code=reason_code,
                evidence=evidence,
                decision_pk=decision_pk,
                input_hash=input_hash,
            )

            # Phase 8C: correlation_ledger DECISION INSERT
            # BLOCK-Entscheidungen nutzen event_type="DECISION" (BLOCK ist Entscheidungsergebnis,
            # kein eigener Event-Typ). Details in blocked_decisions-Tabelle.
            if not signal_id or not decision_id:
                if allow_evidence_debt():
                    logger.warning(
                        f"⚠️ correlation_ledger DECISION skipped: "
                        f"signal_id={signal_id}, decision_id={decision_id} (ALLOW_EVIDENCE_DEBT=1)"
                    )
                else:
                    raise ValueError(
                        f"signal_id and decision_id required for correlation_ledger DECISION "
                        f"(signal_id={signal_id}, decision_id={decision_id})"
                    )
            else:
                if not self._persist_correlation_event(
                    signal_id=signal_id,
                    event_type="DECISION",
                    symbol=signal.symbol,
                    timestamp_ms=now_ms,
                    decision_id=decision_id,
                    payload=evidence,
                ):
                    logger.warning(
                        f"⚠️ correlation_ledger DECISION write failed (evidence debt)"
                    )

        if decision == DECISION_BLOCK:
            logger.warning("Decision contract BLOCK: %s", reason_code)
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1

            # Trace-Writes: blocked_decisions + Redis blocked_order (nur bei Toggle ON)
            if trace_contract_v1_enabled():
                # Phase 8C: blocked_decisions INSERT (fail-closed)
                if not signal_id or not decision_id:
                    if allow_evidence_debt():
                        logger.warning(
                            f"⚠️ blocked_decisions skipped: "
                            f"signal_id={signal_id}, decision_id={decision_id} (ALLOW_EVIDENCE_DEBT=1)"
                        )
                    else:
                        raise ValueError(
                            f"signal_id and decision_id required for blocked_decisions "
                            f"(signal_id={signal_id}, decision_id={decision_id})"
                        )
                else:
                    if not self._persist_blocked_decision(
                        signal_id=signal_id,
                        decision_id=decision_id,
                        symbol=signal.symbol,
                        reason_code=reason_code or "UNKNOWN",
                        timestamp_ms=now_ms,
                        evidence=evidence,
                    ):
                        logger.warning(
                            f"⚠️ blocked_decisions write failed (evidence debt)"
                        )

                # Redis blocked_order Artefakt (audit/replay)
                blocked_order = {
                    "type": "blocked_order",
                    "order_id": generate_uuid(),
                    "decision_id": decision_id,
                    "signal_id": signal_id,
                    "trace_id": evidence.get("trace_id"),
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "reason_code": reason_code,
                    "timestamp_ms": int(time.time() * 1000),
                }
                try:
                    self.redis_client.xadd(
                        self.config.orders_blocked_stream,
                        sanitize_payload(blocked_order),
                        maxlen=10000,
                    )
                except Exception:
                    logger.exception("Failed to persist blocked_order artifact")

            return None

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
            # Early-Live exception: allow small allocations despite risk_off
            if not self._is_early_live_exception(signal.strategy_id):
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
        reduce_only = self._is_reduce_only_allowed(signal)
        if not reduce_only:
            ok, reason = self.check_exposure_limit()
            if not ok:
                self.send_alert(
                    "WARNING", "RISK_LIMIT", reason, {"signal": signal.symbol}
                )
                logger.warning(f"⚠️ {reason}")
                stats["orders_blocked"] += 1
                risk_state.signals_blocked += 1

                # PROACTIVE AUTO-UNWIND: If over limit and have open positions, trigger unwind
                self._trigger_proactive_unwind()

                return None
        else:
            # Reduce-only order bypasses exposure limit (allowed to close positions)
            logger.info(
                f"✅ Reduce-only SELL allowed while over limit: {signal.symbol} (closes position)"
            )
            stats["reduce_only_approved"] = stats.get("reduce_only_approved", 0) + 1

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
        quantity, skip_reason = self.calculate_position_size(
            signal, allocation.allocation_pct
        )

        # SKIP: qty=0 wegen invalid price oder sanity check
        if quantity <= 0.0 or skip_reason:
            logger.warning(
                f"Signal SKIPPED: {signal.symbol} {signal.side} - {skip_reason}"
            )
            stats["orders_skipped"] += 1
            return None

        # Mark order if Early-Live exception applies
        reason = signal.reason
        if self._is_early_live_exception(signal.strategy_id):
            reason = (
                f"{signal.reason}|risk_off_limited"
                if signal.reason
                else "risk_off_limited"
            )

        # PR #617 Hotfix: Use price fallback for exposure reservation
        price_used = signal.price or risk_state.last_prices.get(signal.symbol, 0.0)
        if price_used <= 0.0:
            logger.warning(
                f"Signal SKIPPED: {signal.symbol} {signal.side} - No valid price for exposure reservation (signal.price={signal.price}, last_price={risk_state.last_prices.get(signal.symbol, 'N/A')})"
            )
            stats["orders_skipped"] += 1
            return None

        order = Order(
            symbol=signal.symbol,
            side=signal.side,
            quantity=quantity,
            stop_loss_pct=self.config.stop_loss_pct,
            signal_id=signal.signal_id or "",  # BUG-FIX: was signal.timestamp
            reason=reason,
            timestamp=int(time.time()),
            client_id=f"{signal.symbol}-{signal.timestamp}",
            strategy_id=signal.strategy_id,
            bot_id=signal.bot_id,
            price=price_used,
            # Correlation IDs from decide_trade evidence
            order_id=generate_uuid(),
            decision_id=evidence.get("decision_id"),
            trace_id=evidence.get("trace_id"),
            # Phase 9: Trace Contract v1 - Policy governance (None when toggle OFF)
            policy_id=evidence.get("policy_id"),
            policy_hash=evidence.get("policy_hash"),
            input_hash=evidence.get("input_hash"),
            output_hash=evidence.get("output_hash"),
            # Issue #748 Slice 2: Policy snapshot (None when toggle OFF)
            policy_snapshot=policy_snapshot,
        )

        # PR #619: HARD EXPOSURE GATE - Block order if projected exposure exceeds limit
        # This MUST happen AFTER order creation (when we have final qty/price)
        # but BEFORE reservation and publish to prevent race condition
        # Skip for reduce-only orders (they close positions, reducing exposure)
        if not reduce_only:
            from .balance_fetcher import RealBalanceFetcher

            if self.config.use_real_balance:
                balance_fetcher = RealBalanceFetcher()
                current_balance = balance_fetcher.get_usdt_balance()
            else:
                current_balance = self.config.test_balance

            max_exposure_usdt = current_balance * self.config.max_total_exposure_pct
            estimated_notional_usdt = order.quantity * price_used
            projected_exposure = (
                risk_state.total_exposure
                + risk_state.pending_exposure_usdt
                + estimated_notional_usdt
            )

            if projected_exposure > max_exposure_usdt:
                logger.warning(
                    f"⛔ HARD EXPOSURE GATE: Order rejected BEFORE publish. "
                    f"Projected exposure {projected_exposure:.2f} > limit {max_exposure_usdt:.2f} "
                    f"(total: {risk_state.total_exposure:.2f}, pending: {risk_state.pending_exposure_usdt:.2f}, "
                    f"new_order: {estimated_notional_usdt:.2f}, client_id: {order.client_id})"
                )
                self.send_alert(
                    "WARNING",
                    "EXPOSURE_LIMIT_PROJECTED",
                    f"Order blocked: projected exposure {projected_exposure:.2f} > {max_exposure_usdt:.2f}",
                    {
                        "symbol": signal.symbol,
                        "client_id": order.client_id,
                        "projected_exposure": projected_exposure,
                        "max_exposure": max_exposure_usdt,
                        "total_exposure": risk_state.total_exposure,
                        "pending_exposure": risk_state.pending_exposure_usdt,
                        "new_order_notional": estimated_notional_usdt,
                    },
                )
                stats["orders_blocked"] += 1
                risk_state.signals_blocked += 1

                # Trigger proactive unwind if we have open positions
                self._trigger_proactive_unwind()

                return None

        # LR-762: Deterministic Decision Contract gate (fail-closed).
        try:
            self._ensure_decision_contract_for_order(
                order,
                source="risk.process_signal",
                account_state_snapshot=(
                    account_state if isinstance(account_state, dict) else None
                ),
                payload=payload,
            )
        except DecisionContractError as exc:
            logger.error(
                "⛔ Decision Contract v1 failed in process_signal (fail-closed): %s",
                exc,
            )
            stats["orders_blocked"] += 1
            risk_state.signals_blocked += 1
            return None

        logger.info(
            f"✅ Order freigegeben: {order.symbol} {order.side} qty={order.quantity:.4f}"
        )
        stats["orders_approved"] += 1
        risk_state.signals_approved += 1
        risk_state.pending_orders += 1

        # PR #617: Reserve exposure for pending order to prevent race condition
        estimated_notional = order.quantity * price_used
        risk_state.pending_exposure_usdt += estimated_notional
        risk_state.pending_reservations[order.client_id] = estimated_notional
        logger.debug(
            f"Reserved {estimated_notional:.2f} USDT exposure for {order.client_id} "
            f"(total pending: {risk_state.pending_exposure_usdt:.2f})"
        )

        if getattr(order, "order_id", None):
            if order.price is None:
                logger.debug("order.price is None — skip order envelope")
            elif _envelope_toggle_enabled():
                try:
                    from core.replay.emitter import emit_order_envelope

                    emit_order_envelope(
                        event_id=str(order.order_id),
                        ts_ms=(
                            int(order.timestamp * 1000)
                            if getattr(order, "timestamp", None)
                            else deterministic_ts_ms
                        ),
                        symbol=order.symbol,
                        side=str(order.side),
                        quantity=float(order.quantity),
                        price=float(order.price),
                        signal_id=order.signal_id or None,
                        decision_id=order.decision_id or None,
                        order_id=order.order_id or None,
                        trace_id=order.trace_id or None,
                        decision_context=evidence.get("decision_context"),
                        policy_id=getattr(order, "policy_id", None),
                        policy_hash=getattr(order, "policy_hash", None),
                        input_hash=getattr(order, "input_hash", None),
                        output_hash=getattr(order, "output_hash", None),
                        policy_snapshot=getattr(order, "policy_snapshot", None),
                    )
                except RuntimeError:
                    raise
                except Exception:
                    logger.exception("Order envelope emission failed")

        return order

    def calculate_position_size(
        self, signal: Signal, allocation_pct: float
    ) -> tuple[float, str | None]:
        """Berechnet Position-Size basierend auf Allokation

        Returns:
            (quantity, skip_reason): qty=0.0 mit reason wenn skipped
        """
        if self.config.use_real_balance and self.balance_fetcher:
            try:
                current_balance = self.balance_fetcher.get_usdt_balance()
            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Balance: {e}")
                return 0.0, f"Balance-Fehler: {e}"
        else:
            current_balance = self.config.test_balance

        max_notional_usdt = current_balance * self.config.max_position_pct

        # Allokationsbasiert (keine Confidence im Control-Pfad)
        notional_usdt = max_notional_usdt * max(allocation_pct, 0.0)

        # Hole Price vom Signal, fallback auf 0.0
        price = float(getattr(signal, "price", 0.0) or 0.0)

        if price <= 0.0:
            logger.warning(
                f"calculate_position_size: invalid price={price} for {signal.symbol}, returning qty=0.0"
            )
            return 0.0, "Invalid price"

        # Konvertiere USDT-Notional zu Coin-Quantity
        qty = notional_usdt / price

        # Dev/Paper-only sanity check: catch absurdly large quantities
        if not self.config.use_real_balance:
            # For BTC pairs, qty > 1.0 is extremely suspicious (likely sizing bug)
            if "BTC" in signal.symbol and qty > 1.0:
                logger.error(
                    f"SANITY CHECK FAILED: qty={qty:.4f} for {signal.symbol} is absurdly large "
                    f"(notional={notional_usdt:.2f} USDT, price={price:.2f}). "
                    f"Possible sizing regression detected! Blocking order in dev/paper mode."
                )
                return 0.0, "Sanity check failed (qty too large)"

        return float(max(qty, 0.0)), None

    def send_order(self, order: Order):
        """Publiziert Order"""
        # LR-762: Second contract gate before publish (fail-closed).
        try:
            self._ensure_decision_contract_for_order(
                order,
                source="risk.send_order",
            )
        except DecisionContractError as exc:
            logger.error("⛔ Order blocked by Decision Contract gate: %s", exc)
            stats["orders_blocked"] += 1
            if risk_state.pending_orders > 0:
                risk_state.pending_orders -= 1
            return

        try:
            payload = sanitize_payload(order.to_dict())
            message = json.dumps(payload, ensure_ascii=False)
            self.redis_client.publish(self.config.output_topic_orders, message)
            if self.redis_client:
                self.redis_client.xadd(self.config.orders_stream, payload, maxlen=10000)
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
        sanitized = sanitize_payload(payload)
        self.redis_client.xadd(self.config.bot_shutdown_stream, sanitized, maxlen=10000)
        logger.warning("Bot-Shutdown emittiert: %s", sanitized)

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

    def _trigger_proactive_unwind(self) -> None:
        """
        Proactive auto-unwind: Generate SELL orders when over limit.

        This method is called when a signal is blocked due to max_exposure.
        If we have open positions, we generate SELL orders to reduce exposure.

        This breaks the deadlock where:
        - Exposure > limit → all BUYs blocked
        - No BUYs → no fills → reactive unwind never triggers
        - Position stays open forever

        Solution: Proactively unwind when blocked.
        """
        # LR-030: No unwind orders in shadow mode
        if self._resolve_contract_run_mode() == "shadow":
            logger.info(
                "Proactive unwind suppressed: shadow mode (positions=%d)",
                len(risk_state.positions),
            )
            return

        if not self.config.paper_auto_unwind:
            return

        # Check if we have any open positions
        if not risk_state.positions:
            return

        # Generate SELL order for each open LONG position
        for symbol, position_qty in list(risk_state.positions.items()):
            if position_qty <= 0:
                continue  # Skip short positions or zero positions

            # Get current price for this symbol
            current_price = risk_state.last_prices.get(symbol, 0.0)
            if current_price <= 0:
                logger.warning(
                    f"⚠️ Proactive unwind skipped for {symbol}: no price data"
                )
                continue

            order = Order(
                symbol=symbol,
                side="SELL",
                quantity=abs(position_qty),
                stop_loss_pct=self.config.stop_loss_pct,
                signal_id=int(time.time()),
                reason="proactive_unwind:over_limit",
                timestamp=int(time.time()),
                client_id=f"proactive-unwind-{symbol}-{int(time.time())}",
                strategy_id="paper",  # Use paper strategy for auto-unwind
                bot_id=None,
                price=current_price,
            )

            logger.warning(
                f"🔄 PROACTIVE AUTO-UNWIND: queued SELL {symbol} qty={abs(position_qty):.8f} "
                f"(exposure over limit, forcing position close)"
            )
            stats["proactive_unwind_triggered"] = (
                stats.get("proactive_unwind_triggered", 0) + 1
            )
            stats["orders_approved"] += 1
            risk_state.pending_orders += 1
            self.send_order(order)

            # Only unwind one position per trigger to avoid flooding
            break

    def _maybe_auto_unwind(self, result: OrderResult) -> None:
        """
        Reactive auto-unwind: Generate SELL after BUY fills.

        This is the original auto-unwind logic that triggers after successful BUY fills.
        Complements the proactive unwind above.
        """
        # LR-030: No unwind orders in shadow mode
        if self._resolve_contract_run_mode() == "shadow":
            logger.info(
                "Reactive unwind suppressed: shadow mode (symbol=%s, qty=%s)",
                result.symbol,
                result.filled_quantity,
            )
            return

        if not self.config.paper_auto_unwind:
            return
        if result.status != "FILLED":
            return
        if result.side != "BUY":
            return
        if result.strategy_id != "paper":
            return
        if result.filled_quantity <= 0:
            return

        order = Order(
            symbol=result.symbol,
            side="SELL",
            quantity=result.filled_quantity,
            stop_loss_pct=self.config.stop_loss_pct,
            signal_id=int(time.time()),
            reason=f"paper_auto_unwind:{result.order_id}",
            timestamp=int(time.time()),
            client_id=f"paper-unwind-{result.order_id}",
            strategy_id=result.strategy_id,
            bot_id=result.bot_id,
            price=result.price,
        )

        logger.info(
            "PAPER_AUTO_UNWIND: queued SELL %s qty=%.4f (order_id=%s)",
            order.symbol,
            order.quantity,
            result.order_id,
        )
        stats["orders_approved"] += 1
        risk_state.pending_orders += 1
        self.send_order(order)

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

        # PR #617: Release reserved exposure when order result arrives
        if result.client_id and result.client_id in risk_state.pending_reservations:
            reserved = risk_state.pending_reservations.pop(result.client_id)
            risk_state.pending_exposure_usdt = max(
                0.0, risk_state.pending_exposure_usdt - reserved
            )
            logger.debug(
                f"Released {reserved:.2f} USDT exposure for {result.client_id} "
                f"(status={result.status}, total pending: {risk_state.pending_exposure_usdt:.2f})"
            )

        if result.status == "FILLED":
            self._update_exposure(result)
            self._maybe_auto_unwind(result)
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
                        order = self.process_signal(signal, raw_payload=data)

                        # Falls approved, Order senden
                        if order:
                            self.send_order(order)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Ungültiges JSON: {e}")
                        stats["orders_skipped"] += 1  # Silent drop: JSON parse error
                    except Exception as e:
                        logger.error(f"Fehler in Hauptschleife: {e}")
                        stats[
                            "orders_skipped"
                        ] += 1  # Silent drop: Signal parsing error

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
        if self._pg_conn and not self._pg_conn.closed:
            self._pg_conn.close()

        logger.info("Risk-Manager gestoppt ✓")


# ===== FLASK ENDPOINTS =====

if _FLASK_AVAILABLE:
    from flask import Flask, jsonify, Response

    app = Flask(__name__)

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
            "# HELP signals_received_total Signals empfangen (Redis PubSub)\n"
            "# TYPE signals_received_total counter\n"
            f"signals_received_total {stats['signals_received']}\n\n"
            "# HELP orders_approved_total Orders freigegeben\n"
            "# TYPE orders_approved_total counter\n"
            f"orders_approved_total {stats['orders_approved']}\n\n"
            "# HELP orders_blocked_total Orders blockiert (Risk Checks)\n"
            "# TYPE orders_blocked_total counter\n"
            f"orders_blocked_total {stats['orders_blocked']}\n\n"
            "# HELP orders_skipped_total Orders übersprungen (qty=0, parse errors)\n"
            "# TYPE orders_skipped_total counter\n"
            f"orders_skipped_total {stats['orders_skipped']}\n\n"
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
            "# HELP risk_reduce_only_approved_total Reduce-only SELL orders approved while over exposure limit\n"
            "# TYPE risk_reduce_only_approved_total counter\n"
            f"risk_reduce_only_approved_total {stats.get('reduce_only_approved', 0)}\n\n"
            "# HELP risk_proactive_unwind_triggered_total Proactive auto-unwind triggers (SELL orders generated when over limit)\n"
            "# TYPE risk_proactive_unwind_triggered_total counter\n"
            f"risk_proactive_unwind_triggered_total {stats.get('proactive_unwind_triggered', 0)}\n\n"
            "# HELP risk_alerts_generated_total Alerts published to alerts topic\n"
            "# TYPE risk_alerts_generated_total counter\n"
            f"risk_alerts_generated_total {stats['alerts_generated']}\n\n"
            "# HELP risk_kill_switch_active Kill-switch state (1=active/trading halted, 0=inactive/unknown)\n"
            "# TYPE risk_kill_switch_active gauge\n"
        )
        try:
            ks_active = 1 if get_kill_switch_details(create_if_missing=False)[0] else 0
        except Exception:
            ks_active = 0  # conservative: report inactive on read failure
        body += f"risk_kill_switch_active {ks_active}\n"
        return Response(body, mimetype="text/plain")

    @app.route("/kill-switch", methods=["GET"])
    def kill_switch_status():
        state_file = str(resolve_kill_switch_state_file())
        try:
            active, reason, message, activated_at = get_kill_switch_details(
                state_file=state_file, create_if_missing=False
            )
        except Exception as exc:
            return jsonify({"error": f"state read failed: {exc}"}), 500
        return jsonify(
            {
                "active": active,
                "reason": reason,
                "message": message,
                "activated_at": activated_at,
            }
        )

    @app.route("/kill-switch/activate", methods=["POST"])
    def kill_switch_activate():
        from flask import request as flask_request

        body = flask_request.get_json(silent=True) or {}
        reason_str = body.get("reason", "manual")
        message = body.get("message", "")
        operator = body.get("operator", "")
        if not operator:
            return jsonify({"error": "operator required"}), 400
        try:
            ks_reason = KillSwitchReason(reason_str)
        except ValueError:
            ks_reason = KillSwitchReason.MANUAL
        state_file = str(resolve_kill_switch_state_file())
        ks = KillSwitch(state_file)
        ok = ks.activate(ks_reason, message, operator=operator)
        if not ok:
            return jsonify({"error": "activation failed"}), 500
        _, reason_val, msg, activated_at = get_kill_switch_details(
            state_file=state_file, create_if_missing=False
        )
        return jsonify(
            {
                "active": True,
                "activated": True,
                "reason": reason_val,
                "activated_at": activated_at,
                "message": msg,
            }
        )

    @app.route("/kill-switch/deactivate", methods=["POST"])
    def kill_switch_deactivate():
        from flask import request as flask_request

        body = flask_request.get_json(silent=True) or {}
        operator = body.get("operator", "")
        justification = body.get("justification", "")
        if not operator or not justification:
            return jsonify({"error": "operator and justification required"}), 400
        state_file = str(resolve_kill_switch_state_file())
        ks = KillSwitch(state_file)
        ok = ks.deactivate(operator, justification)
        if not ok:
            return jsonify({"error": "deactivation failed (check operator/justification)"}), 400
        active_after, _, _, _ = get_kill_switch_details(
            state_file=state_file, create_if_missing=False
        )
        return jsonify({"deactivated": True, "active": active_after})

else:
    app = None


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

    # Bootstrap risk state from DB positions (source-of-truth reconciliation)
    manager.bootstrap_state_from_db()

    # Flask in Thread (nur wenn Flask verfügbar)
    if not _FLASK_AVAILABLE or app is None:
        raise RuntimeError(
            "Flask ist nicht installiert. HTTP-Endpoints (health/status/metrics) "
            "benötigen Flask als optionale Abhängigkeit: pip install flask"
        )

    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=config.port))
    flask_thread.daemon = True
    flask_thread.start()

    logger.info(f"Health-Check: http://0.0.0.0:{config.port}/health")

    # Hauptschleife
    manager.run()
