"""Deterministic kill-cancel coordinator and supervisor (#4185).

Kill active and kill unevaluable are both treated as HALT for cancel purposes.
Failed / unconfirmed cancels remain residual and yield HOLD — never silent PASS.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping

from core.contracts.external_adapter_contracts import (
    CancelOrderRequest,
    CancelOrderResponse,
    OpenOrderSnapshot,
)
from core.utils.clock import utcnow
from core.utils.uuid_gen import generate_uuid_hex

from .open_order_registry import OpenOrderRecord, OpenOrderRegistry

logger = logging.getLogger(__name__)

EVIDENCE_SCHEMA_VERSION = "cdb-kill-cancel-evidence/v1"

# Stable machine-readable reason codes (#4185)
RC_KILL_CANCEL_PASS = "KILL_CANCEL_PASS"
RC_KILL_CANCEL_HOLD = "KILL_CANCEL_HOLD"
RC_KILL_STATE_UNEVALUABLE = "KILL_STATE_UNEVALUABLE"
RC_OPEN_ORDER_SOURCE_UNAVAILABLE = "OPEN_ORDER_SOURCE_UNAVAILABLE"
RC_OPEN_ORDER_STATUS_UNKNOWN = "OPEN_ORDER_STATUS_UNKNOWN"
RC_CANCEL_ADAPTER_UNSUPPORTED = "CANCEL_ADAPTER_UNSUPPORTED"
RC_CANCEL_REQUEST_REJECTED = "CANCEL_REQUEST_REJECTED"
RC_CANCEL_EXECUTION_ERROR = "CANCEL_EXECUTION_ERROR"
RC_CANCEL_CONFIRMATION_MISSING = "CANCEL_CONFIRMATION_MISSING"
RC_CANCEL_ALREADY_CONFIRMED = "CANCEL_ALREADY_CONFIRMED"
RC_FILL_AFTER_KILL_ACTIVATION = "FILL_AFTER_KILL_ACTIVATION"
RC_RESIDUAL_OPEN_ORDERS = "RESIDUAL_OPEN_ORDERS"
RC_RESIDUAL_POSITION_UNKNOWN = "RESIDUAL_POSITION_UNKNOWN"

REQUIRED_REASON_CODES = frozenset(
    {
        RC_KILL_CANCEL_PASS,
        RC_KILL_CANCEL_HOLD,
        RC_KILL_STATE_UNEVALUABLE,
        RC_OPEN_ORDER_SOURCE_UNAVAILABLE,
        RC_OPEN_ORDER_STATUS_UNKNOWN,
        RC_CANCEL_ADAPTER_UNSUPPORTED,
        RC_CANCEL_REQUEST_REJECTED,
        RC_CANCEL_EXECUTION_ERROR,
        RC_CANCEL_CONFIRMATION_MISSING,
        RC_CANCEL_ALREADY_CONFIRMED,
        RC_FILL_AFTER_KILL_ACTIVATION,
        RC_RESIDUAL_OPEN_ORDERS,
        RC_RESIDUAL_POSITION_UNKNOWN,
    }
)


class KillCancelOrderState(str, Enum):
    DISCOVERED_OPEN = "DISCOVERED_OPEN"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCEL_CONFIRMED = "CANCEL_CONFIRMED"
    ALREADY_TERMINAL = "ALREADY_TERMINAL"
    CANCEL_REJECTED = "CANCEL_REJECTED"
    CANCEL_ERROR = "CANCEL_ERROR"
    STATUS_UNKNOWN = "STATUS_UNKNOWN"
    FILL_AFTER_KILL_VIOLATION = "FILL_AFTER_KILL_VIOLATION"


class KillCancelBatchVerdict(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    FAIL = "FAIL"


@dataclass
class PerOrderCancelEvidence:
    internal_order_id: str
    venue_order_id: str | None
    symbol: str
    status_at_kill: str
    filled_quantity_at_kill: float
    remaining_quantity_at_kill: float
    cancel_attempt_count: int
    cancel_requested_at_utc: str | None
    adapter_accepted: bool | None
    cancel_confirmed: bool
    terminal_status: str | None
    status_after_cancel: str | None
    reason_code: str
    residual_open: bool
    position_effect: str
    kill_cancel_state: str


@dataclass
class KillCancelEvidenceManifest:
    schema_version: str
    run_id: str
    commit_sha: str
    kill_event_id: str
    kill_state: str
    kill_reason: str
    kill_activated_at_utc: str
    reconciliation_started_at_utc: str
    reconciliation_completed_at_utc: str
    open_order_source: str
    open_order_source_status: str
    orders_discovered: int
    cancel_attempts: int
    orders_confirmed_cancelled: int
    orders_already_terminal: int
    orders_rejected: int
    orders_unknown: int
    residual_open_orders: list[dict[str, Any]]
    residual_positions: list[dict[str, Any]]
    fill_after_kill_events: list[dict[str, Any]]
    overall_verdict: str
    reason_codes: list[str]
    limitations: list[str]
    safety_boundaries: list[str]
    per_order: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _redact(value: str | None, limit: int = 120) -> str | None:
    if value is None:
        return None
    text = str(value)
    lowered = text.lower()
    for needle in ("api_key", "api_secret", "password", "token", "authorization"):
        if needle in lowered:
            return "[REDACTED]"
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def build_kill_event_id(*, kill_state: str, kill_reason: str, activated_at: str) -> str:
    material = f"{kill_state}|{kill_reason}|{activated_at}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"kill_{digest}"


@dataclass
class KillCancelCoordinator:
    """Runs one deterministic cancel reconciliation for a kill event."""

    registry: OpenOrderRegistry
    adapter: Any | None
    commit_sha: str = "unknown"
    position_resolver: Callable[[], list[dict[str, Any]]] | None = None

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._confirmed_by_event: dict[str, set[str]] = {}
        self._fill_after_kill: list[dict[str, Any]] = []
        self._last_manifest: KillCancelEvidenceManifest | None = None
        self._active_kill_event_id: str | None = None
        self._kill_activated_at: str | None = None

    @property
    def last_manifest(self) -> KillCancelEvidenceManifest | None:
        return self._last_manifest

    @property
    def active_kill_event_id(self) -> str | None:
        return self._active_kill_event_id

    def note_fill_after_kill(
        self,
        *,
        internal_order_id: str,
        venue_order_id: str | None,
        symbol: str,
        filled_quantity: float,
    ) -> None:
        with self._lock:
            if not self._active_kill_event_id:
                return
            event = {
                "internal_order_id": internal_order_id,
                "venue_order_id": venue_order_id,
                "symbol": symbol,
                "filled_quantity": filled_quantity,
                "observed_at_utc": utcnow().isoformat(),
                "reason_code": RC_FILL_AFTER_KILL_ACTIVATION,
            }
            self._fill_after_kill.append(event)
            self.registry.mark_cancel_outcome(
                internal_order_id,
                kill_cancel_state=KillCancelOrderState.FILL_AFTER_KILL_VIOLATION.value,
                reason_code=RC_FILL_AFTER_KILL_ACTIVATION,
                confirmed=False,
            )

    def reconcile(
        self,
        *,
        kill_state: str,
        kill_reason: str,
        kill_activated_at_utc: str | None = None,
        run_id: str | None = None,
        open_order_source: str = "execution_open_order_registry",
    ) -> KillCancelEvidenceManifest:
        started = utcnow().isoformat()
        activated_at = kill_activated_at_utc or started
        kill_event_id = build_kill_event_id(
            kill_state=kill_state, kill_reason=kill_reason, activated_at=activated_at
        )
        run_id = run_id or generate_uuid_hex(
            name=f"kill-cancel:{kill_event_id}:{started}"
        )

        with self._lock:
            self._active_kill_event_id = kill_event_id
            self._kill_activated_at = activated_at
            confirmed_set = self._confirmed_by_event.setdefault(kill_event_id, set())

            reason_codes: list[str] = []
            if kill_state in {"unevaluable", "UNEVALUABLE"} or kill_reason in {
                "evaluation_error",
                "missing_state",
                "corrupt_state",
                "unreadable_state",
            }:
                reason_codes.append(RC_KILL_STATE_UNEVALUABLE)

            per_order: list[PerOrderCancelEvidence] = []
            cancel_attempts = 0
            confirmed_cancelled = 0
            already_terminal = 0
            rejected = 0
            unknown = 0
            source_status = "ok"

            try:
                discovered = self.registry.list_open()
            except Exception:  # noqa: BLE001
                logger.exception("open order registry unavailable")
                discovered = []
                source_status = "unavailable"
                reason_codes.append(RC_OPEN_ORDER_SOURCE_UNAVAILABLE)

            cancel_fn = (
                getattr(self.adapter, "cancel_order", None) if self.adapter else None
            )
            get_open_fn = (
                getattr(self.adapter, "get_open_order", None) if self.adapter else None
            )
            supports_flag = getattr(self.adapter, "supports_cancel", None)
            if supports_flag is False:
                supports_cancel = False
            else:
                supports_cancel = callable(cancel_fn)

            if discovered and not supports_cancel:
                reason_codes.append(RC_CANCEL_ADAPTER_UNSUPPORTED)
                for record in discovered:
                    per_order.append(
                        self._residual_evidence(
                            record,
                            state=KillCancelOrderState.STATUS_UNKNOWN,
                            reason_code=RC_CANCEL_ADAPTER_UNSUPPORTED,
                            attempt_count=0,
                        )
                    )
                    unknown += 1
            else:
                for record in discovered:
                    evidence, attempt = self._cancel_one(
                        record=record,
                        kill_event_id=kill_event_id,
                        confirmed_set=confirmed_set,
                        cancel_fn=cancel_fn if supports_cancel else None,
                        get_open_fn=get_open_fn if callable(get_open_fn) else None,
                    )
                    per_order.append(evidence)
                    cancel_attempts += attempt
                    if (
                        evidence.kill_cancel_state
                        == KillCancelOrderState.CANCEL_CONFIRMED.value
                    ):
                        confirmed_cancelled += 1
                    elif (
                        evidence.kill_cancel_state
                        == KillCancelOrderState.ALREADY_TERMINAL.value
                    ):
                        already_terminal += 1
                    elif (
                        evidence.kill_cancel_state
                        == KillCancelOrderState.CANCEL_REJECTED.value
                    ):
                        rejected += 1
                    elif evidence.kill_cancel_state in {
                        KillCancelOrderState.CANCEL_ERROR.value,
                        KillCancelOrderState.STATUS_UNKNOWN.value,
                    }:
                        unknown += 1
                    reason_codes.append(evidence.reason_code)

            residual_open = [
                {
                    "internal_order_id": e.internal_order_id,
                    "venue_order_id": e.venue_order_id,
                    "symbol": e.symbol,
                    "reason_code": e.reason_code,
                    "kill_cancel_state": e.kill_cancel_state,
                }
                for e in per_order
                if e.residual_open
            ]
            if residual_open:
                reason_codes.append(RC_RESIDUAL_OPEN_ORDERS)

            residual_positions = self._resolve_positions()
            if any(p.get("status") == "UNKNOWN" for p in residual_positions):
                reason_codes.append(RC_RESIDUAL_POSITION_UNKNOWN)

            fill_events = list(self._fill_after_kill)
            if fill_events:
                reason_codes.append(RC_FILL_AFTER_KILL_ACTIVATION)

            verdict = self._verdict(
                residual_open=residual_open,
                residual_positions=residual_positions,
                fill_events=fill_events,
                source_status=source_status,
                discovered_count=len(discovered),
                supports_cancel=supports_cancel or not discovered,
            )
            if verdict == KillCancelBatchVerdict.PASS:
                reason_codes.append(RC_KILL_CANCEL_PASS)
            elif verdict == KillCancelBatchVerdict.HOLD:
                reason_codes.append(RC_KILL_CANCEL_HOLD)

            # de-dupe preserve order
            deduped: list[str] = []
            for code in reason_codes:
                if code not in deduped:
                    deduped.append(code)

            completed = utcnow().isoformat()
            manifest = KillCancelEvidenceManifest(
                schema_version=EVIDENCE_SCHEMA_VERSION,
                run_id=run_id,
                commit_sha=self.commit_sha,
                kill_event_id=kill_event_id,
                kill_state=kill_state,
                kill_reason=kill_reason,
                kill_activated_at_utc=activated_at,
                reconciliation_started_at_utc=started,
                reconciliation_completed_at_utc=completed,
                open_order_source=open_order_source,
                open_order_source_status=source_status,
                orders_discovered=len(discovered),
                cancel_attempts=cancel_attempts,
                orders_confirmed_cancelled=confirmed_cancelled,
                orders_already_terminal=already_terminal,
                orders_rejected=rejected,
                orders_unknown=unknown,
                residual_open_orders=residual_open,
                residual_positions=residual_positions,
                fill_after_kill_events=fill_events,
                overall_verdict=verdict.value,
                reason_codes=deduped,
                limitations=[
                    "Mock/dry-run cancel proof only; no productive venue activation",
                    "Positions are reported residual-only; no automatic unwind",
                ],
                safety_boundaries=[
                    "LR remains NO-GO",
                    "No live/echtgeld go",
                    "No automatic position close",
                    "No kill-switch self-heal/deactivate",
                ],
                per_order=[asdict(p) for p in per_order],
            )
            self._last_manifest = manifest
            return manifest

    def _resolve_positions(self) -> list[dict[str, Any]]:
        if self.position_resolver is None:
            return [
                {
                    "symbol": "*",
                    "status": "UNKNOWN",
                    "quantity": None,
                    "reason_code": RC_RESIDUAL_POSITION_UNKNOWN,
                }
            ]
        try:
            positions = list(self.position_resolver())
        except Exception:  # noqa: BLE001
            return [
                {
                    "symbol": "*",
                    "status": "UNKNOWN",
                    "quantity": None,
                    "reason_code": RC_RESIDUAL_POSITION_UNKNOWN,
                }
            ]
        if not positions:
            # Empty known set is not invented zero exposure; report UNKNOWN.
            return [
                {
                    "symbol": "*",
                    "status": "UNKNOWN",
                    "quantity": None,
                    "reason_code": RC_RESIDUAL_POSITION_UNKNOWN,
                }
            ]
        return positions

    def _verdict(
        self,
        *,
        residual_open: list,
        residual_positions: list,
        fill_events: list,
        source_status: str,
        discovered_count: int,
        supports_cancel: bool,
    ) -> KillCancelBatchVerdict:
        if fill_events:
            return KillCancelBatchVerdict.FAIL
        if source_status != "ok":
            return KillCancelBatchVerdict.HOLD
        if residual_open:
            return KillCancelBatchVerdict.HOLD
        if any(p.get("status") == "UNKNOWN" for p in residual_positions):
            return KillCancelBatchVerdict.HOLD
        if discovered_count > 0 and not supports_cancel:
            return KillCancelBatchVerdict.HOLD
        return KillCancelBatchVerdict.PASS

    def _residual_evidence(
        self,
        record: OpenOrderRecord,
        *,
        state: KillCancelOrderState,
        reason_code: str,
        attempt_count: int,
        adapter_accepted: bool | None = None,
        cancel_confirmed: bool = False,
        terminal_status: str | None = None,
        status_after: str | None = None,
        requested_at: str | None = None,
    ) -> PerOrderCancelEvidence:
        self.registry.mark_cancel_outcome(
            record.internal_order_id,
            kill_cancel_state=state.value,
            reason_code=reason_code,
            terminal_status=terminal_status,
            confirmed=cancel_confirmed
            and state
            in {
                KillCancelOrderState.CANCEL_CONFIRMED,
                KillCancelOrderState.ALREADY_TERMINAL,
            },
        )
        residual = state not in {
            KillCancelOrderState.CANCEL_CONFIRMED,
            KillCancelOrderState.ALREADY_TERMINAL,
        }
        return PerOrderCancelEvidence(
            internal_order_id=record.internal_order_id,
            venue_order_id=record.venue_order_id,
            symbol=record.symbol,
            status_at_kill=record.status,
            filled_quantity_at_kill=record.filled_quantity,
            remaining_quantity_at_kill=record.remaining_quantity,
            cancel_attempt_count=attempt_count,
            cancel_requested_at_utc=requested_at,
            adapter_accepted=adapter_accepted,
            cancel_confirmed=cancel_confirmed,
            terminal_status=terminal_status,
            status_after_cancel=status_after,
            reason_code=reason_code,
            residual_open=residual,
            position_effect="none",
            kill_cancel_state=state.value,
        )

    def _cancel_one(
        self,
        *,
        record: OpenOrderRecord,
        kill_event_id: str,
        confirmed_set: set[str],
        cancel_fn: Callable | None,
        get_open_fn: Callable | None,
    ) -> tuple[PerOrderCancelEvidence, int]:
        if record.internal_order_id in confirmed_set:
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.ALREADY_TERMINAL,
                    reason_code=RC_CANCEL_ALREADY_CONFIRMED,
                    attempt_count=0,
                    cancel_confirmed=True,
                    terminal_status="CANCELLED",
                    status_after="CANCELLED",
                ),
                0,
            )

        # Pre-read: already terminal at venue?
        if get_open_fn is not None:
            try:
                snap = get_open_fn(
                    internal_order_id=record.internal_order_id,
                    venue_order_id=record.venue_order_id,
                )
            except Exception:  # noqa: BLE001
                snap = None
            if isinstance(snap, OpenOrderSnapshot) and snap.status in {
                "FILLED",
                "CANCELLED",
                "REJECTED",
            }:
                confirmed_set.add(record.internal_order_id)
                return (
                    self._residual_evidence(
                        record,
                        state=KillCancelOrderState.ALREADY_TERMINAL,
                        reason_code=RC_CANCEL_ALREADY_CONFIRMED,
                        attempt_count=0,
                        cancel_confirmed=True,
                        terminal_status=snap.status,
                        status_after=snap.status,
                    ),
                    0,
                )

        if cancel_fn is None:
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.STATUS_UNKNOWN,
                    reason_code=RC_CANCEL_ADAPTER_UNSUPPORTED,
                    attempt_count=0,
                ),
                0,
            )

        requested_at = utcnow().isoformat()
        request = CancelOrderRequest(
            internal_order_id=record.internal_order_id,
            venue_order_id=record.venue_order_id,
            symbol=record.symbol,
            reason_code="KILL_SWITCH_CANCEL",
            kill_event_id=kill_event_id,
            requested_at_utc=requested_at,
        )
        self.registry.update_status(
            record.internal_order_id,
            status=record.status,
            kill_cancel_state=KillCancelOrderState.CANCEL_REQUESTED.value,
            reason_code="KILL_SWITCH_CANCEL",
        )

        try:
            response = cancel_fn(request)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "cancel_order error for %s: %s",
                record.internal_order_id,
                type(exc).__name__,
            )
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.CANCEL_ERROR,
                    reason_code=RC_CANCEL_EXECUTION_ERROR,
                    attempt_count=1,
                    adapter_accepted=False,
                    requested_at=requested_at,
                    status_after=record.status,
                ),
                1,
            )

        if not isinstance(response, CancelOrderResponse):
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.STATUS_UNKNOWN,
                    reason_code=RC_OPEN_ORDER_STATUS_UNKNOWN,
                    attempt_count=1,
                    requested_at=requested_at,
                ),
                1,
            )

        # Readback confirmation
        status_after = response.terminal_status
        if get_open_fn is not None:
            try:
                snap = get_open_fn(
                    internal_order_id=record.internal_order_id,
                    venue_order_id=response.venue_order_id or record.venue_order_id,
                )
                if isinstance(snap, OpenOrderSnapshot):
                    status_after = snap.status
                    if snap.status == "CANCELLED":
                        response = CancelOrderResponse(
                            internal_order_id=response.internal_order_id,
                            venue_order_id=response.venue_order_id,
                            accepted=response.accepted,
                            confirmed_cancelled=True,
                            terminal_status="CANCELLED",
                            adapter_reason_code=response.adapter_reason_code,
                            raw_status_redacted=_redact(response.raw_status_redacted),
                            observed_at_utc=snap.observed_at_utc,
                        )
                    elif snap.status in {"FILLED", "REJECTED"}:
                        confirmed_set.add(record.internal_order_id)
                        return (
                            self._residual_evidence(
                                record,
                                state=KillCancelOrderState.ALREADY_TERMINAL,
                                reason_code=RC_CANCEL_ALREADY_CONFIRMED,
                                attempt_count=1,
                                adapter_accepted=response.accepted,
                                cancel_confirmed=True,
                                terminal_status=snap.status,
                                status_after=snap.status,
                                requested_at=requested_at,
                            ),
                            1,
                        )
            except Exception:  # noqa: BLE001
                pass

        if response.confirmed_cancelled and response.terminal_status == "CANCELLED":
            confirmed_set.add(record.internal_order_id)
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.CANCEL_CONFIRMED,
                    reason_code=RC_KILL_CANCEL_PASS,
                    attempt_count=1,
                    adapter_accepted=response.accepted,
                    cancel_confirmed=True,
                    terminal_status="CANCELLED",
                    status_after=status_after or "CANCELLED",
                    requested_at=requested_at,
                ),
                1,
            )

        if response.accepted and not response.confirmed_cancelled:
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.STATUS_UNKNOWN,
                    reason_code=RC_CANCEL_CONFIRMATION_MISSING,
                    attempt_count=1,
                    adapter_accepted=True,
                    cancel_confirmed=False,
                    terminal_status=response.terminal_status,
                    status_after=status_after,
                    requested_at=requested_at,
                ),
                1,
            )

        if not response.accepted:
            reason = response.adapter_reason_code or RC_CANCEL_REQUEST_REJECTED
            if reason not in REQUIRED_REASON_CODES and reason not in {
                RC_CANCEL_REQUEST_REJECTED,
                RC_OPEN_ORDER_STATUS_UNKNOWN,
            }:
                reason = RC_CANCEL_REQUEST_REJECTED
            return (
                self._residual_evidence(
                    record,
                    state=KillCancelOrderState.CANCEL_REJECTED,
                    reason_code=(
                        reason
                        if reason in REQUIRED_REASON_CODES
                        else RC_CANCEL_REQUEST_REJECTED
                    ),
                    attempt_count=1,
                    adapter_accepted=False,
                    cancel_confirmed=False,
                    terminal_status=response.terminal_status,
                    status_after=status_after,
                    requested_at=requested_at,
                ),
                1,
            )

        return (
            self._residual_evidence(
                record,
                state=KillCancelOrderState.STATUS_UNKNOWN,
                reason_code=RC_OPEN_ORDER_STATUS_UNKNOWN,
                attempt_count=1,
                adapter_accepted=response.accepted,
                requested_at=requested_at,
                status_after=status_after,
            ),
            1,
        )


class KillCancelSupervisor:
    """Watches kill-switch transitions and runs cancel reconciliation."""

    def __init__(
        self,
        *,
        coordinator: KillCancelCoordinator,
        poll_interval_seconds: float = 1.0,
        get_kill_details: Callable[..., tuple] | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.poll_interval_seconds = poll_interval_seconds
        self._get_kill_details = get_kill_details
        self._lock = threading.RLock()
        self._last_active: bool | None = None
        self._orders_accepted = False
        self._hold_new_orders = True
        self._last_verdict: str | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._startup_done = False

    @property
    def hold_new_orders(self) -> bool:
        with self._lock:
            return self._hold_new_orders

    @property
    def orders_accepted(self) -> bool:
        with self._lock:
            return self._orders_accepted

    @property
    def last_verdict(self) -> str | None:
        with self._lock:
            return self._last_verdict

    def status_snapshot(self) -> dict[str, Any]:
        manifest = self.coordinator.last_manifest
        with self._lock:
            return {
                "kill_cancel_contract": "EXECUTION_KILL_CANCEL_CONTRACT_V1",
                "orders_accepted": self._orders_accepted,
                "hold_new_orders": self._hold_new_orders,
                "last_verdict": self._last_verdict,
                "residual_open_order_count": self.coordinator.registry.count_open(),
                "active_kill_event_id": self.coordinator.active_kill_event_id,
                "last_reason_codes": list(manifest.reason_codes) if manifest else [],
                "ready_for_new_orders": self._orders_accepted
                and not self._hold_new_orders,
            }

    def run_startup_gate(self) -> KillCancelEvidenceManifest | None:
        """Evaluate kill state before accepting orders."""
        active, reason, message, activated_at = self._read_kill()
        with self._lock:
            self._startup_done = True
            self._last_active = active
        if not active:
            with self._lock:
                self._hold_new_orders = False
                self._orders_accepted = True
                self._last_verdict = "PASS_IDLE"
            return None

        kill_state = "unevaluable" if reason == "evaluation_error" else "active"
        activated = (
            activated_at.isoformat()
            if hasattr(activated_at, "isoformat") and activated_at is not None
            else utcnow().isoformat()
        )
        manifest = self.coordinator.reconcile(
            kill_state=kill_state,
            kill_reason=str(reason or message or "kill_active"),
            kill_activated_at_utc=activated,
        )
        with self._lock:
            self._last_verdict = manifest.overall_verdict
            # Remain HOLD for new orders while kill is active (defense in depth)
            self._hold_new_orders = True
            self._orders_accepted = (
                manifest.overall_verdict != KillCancelBatchVerdict.FAIL.value
            )
            # Even on PASS cancel, kill-active still blocks new orders via process_order gate
            # but reconciliation HOLD/FAIL means execution surface is not fully ready
            if manifest.overall_verdict != KillCancelBatchVerdict.PASS.value:
                self._orders_accepted = False
        return manifest

    def on_kill_transition(
        self, *, active: bool, reason: str, activated_at: Any = None
    ) -> KillCancelEvidenceManifest | None:
        with self._lock:
            previous = self._last_active
            self._last_active = active
        if previous is True and active:
            # repeated active → idempotent reconcile (no duplicate confirmed cancels)
            pass
        elif previous is False or previous is None:
            if not active:
                with self._lock:
                    self._hold_new_orders = False
                    self._orders_accepted = True
                return None
        elif previous is True and not active:
            # Deactivation is operator-owned for cancel residuals, but new-order
            # acceptance must resume once kill is inactive (#4185).
            with self._lock:
                self._hold_new_orders = False
                self._orders_accepted = True
            return None

        if not active:
            return None

        kill_state = "unevaluable" if reason == "evaluation_error" else "active"
        activated = (
            activated_at.isoformat()
            if hasattr(activated_at, "isoformat") and activated_at is not None
            else utcnow().isoformat()
        )
        manifest = self.coordinator.reconcile(
            kill_state=kill_state,
            kill_reason=str(reason or "kill_active"),
            kill_activated_at_utc=activated,
        )
        with self._lock:
            self._last_verdict = manifest.overall_verdict
            self._hold_new_orders = True
            if manifest.overall_verdict != KillCancelBatchVerdict.PASS.value:
                self._orders_accepted = False
        return manifest

    def poll_once(self) -> KillCancelEvidenceManifest | None:
        active, reason, _message, activated_at = self._read_kill()
        with self._lock:
            previous = self._last_active
        if previous is None:
            return self.run_startup_gate()
        if previous is False and active:
            return self.on_kill_transition(
                active=True, reason=str(reason), activated_at=activated_at
            )
        if previous is False and not active:
            with self._lock:
                self._last_active = False
                self._hold_new_orders = False
                self._orders_accepted = True
            return None
        if previous is True and active:
            # Keep hold; optional idempotent re-entry is safe
            self._last_active = True
            return None
        if previous is True and not active:
            with self._lock:
                self._last_active = False
                self._hold_new_orders = False
                self._orders_accepted = True
            return None
        return None

    def start(self, *, running_flag: Callable[[], bool] | None = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True

        def _loop() -> None:
            while self._running and (running_flag() if running_flag else True):
                try:
                    self.poll_once()
                except Exception:  # noqa: BLE001
                    logger.exception("kill-cancel supervisor poll failed")
                threading.Event().wait(self.poll_interval_seconds)

        self._thread = threading.Thread(
            target=_loop, name="kill-cancel-supervisor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _read_kill(self) -> tuple[bool, str, str, Any]:
        if self._get_kill_details is not None:
            try:
                return self._get_kill_details(create_if_missing=False)
            except Exception:  # noqa: BLE001
                return True, "evaluation_error", "kill_details_failed", None
        try:
            from core.safety.kill_switch import get_kill_switch_details

            return get_kill_switch_details(create_if_missing=False)
        except Exception:  # noqa: BLE001
            return True, "evaluation_error", "kill_details_failed", None


def write_evidence_manifest(
    manifest: KillCancelEvidenceManifest, path: str | os.PathLike[str]
) -> None:
    payload = manifest.to_dict()
    text = json.dumps(payload, sort_keys=True, indent=2)
    # secret-safe: never include env secrets
    Path = __import__("pathlib").Path
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n", encoding="utf-8")
