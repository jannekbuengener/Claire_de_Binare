"""Thread-safe open-order registry with optional JSON ledger (#4185).

A volatile Python set without population and restart reconciliation is not
canonical open-order truth. This registry:
- registers orders at/before submission
- keeps internal and venue IDs separate
- removes an order only after a confirmed terminal status
- never deletes on cancel error / unknown status
- can rebuild from a JSON ledger after process restart
"""

from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

from core.utils.clock import utcnow

logger = logging.getLogger(__name__)

OPEN_STATUSES = frozenset({"PENDING", "SUBMITTED", "PARTIALLY_FILLED"})
TERMINAL_STATUSES = frozenset({"FILLED", "CANCELLED", "REJECTED"})
# FAILED is not automatically a confirmed cancel.


@dataclass
class OpenOrderRecord:
    """One open (or residual) order tracked for kill-cancel."""

    internal_order_id: str
    symbol: str
    status: str
    venue_order_id: str | None = None
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    quantity: float = 0.0
    side: str | None = None
    registered_at_utc: str = ""
    updated_at_utc: str = ""
    kill_cancel_state: str | None = None
    last_reason_code: str | None = None
    residual_open: bool = True
    metadata: dict = field(default_factory=dict)

    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES and self.residual_open


class OpenOrderRegistry:
    """Canonical in-process open-order truth with optional disk ledger."""

    def __init__(self, ledger_path: str | Path | None = None) -> None:
        self._lock = threading.RLock()
        self._orders: dict[str, OpenOrderRecord] = {}
        env_path = os.getenv("CDB_OPEN_ORDER_LEDGER_PATH")
        self._ledger_path = (
            Path(ledger_path or env_path) if (ledger_path or env_path) else None
        )
        if self._ledger_path is not None:
            try:
                self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning(
                    "open-order ledger parent not writable (%s): %s",
                    self._ledger_path.parent,
                    exc,
                )
            self.load_from_ledger()

    @property
    def ledger_path(self) -> Path | None:
        return self._ledger_path

    def register(
        self,
        *,
        internal_order_id: str,
        symbol: str,
        status: str = "PENDING",
        venue_order_id: str | None = None,
        quantity: float = 0.0,
        filled_quantity: float = 0.0,
        remaining_quantity: float | None = None,
        side: str | None = None,
        metadata: Mapping | None = None,
    ) -> OpenOrderRecord:
        if not internal_order_id:
            raise ValueError("internal_order_id is required")
        now = utcnow().isoformat()
        remaining = (
            remaining_quantity
            if remaining_quantity is not None
            else max(float(quantity) - float(filled_quantity), 0.0)
        )
        with self._lock:
            existing = self._orders.get(internal_order_id)
            if existing is not None:
                existing.symbol = symbol
                existing.status = status
                if venue_order_id:
                    existing.venue_order_id = venue_order_id
                existing.quantity = float(quantity)
                existing.filled_quantity = float(filled_quantity)
                existing.remaining_quantity = float(remaining)
                if side is not None:
                    existing.side = side
                existing.updated_at_utc = now
                existing.residual_open = status in OPEN_STATUSES
                if metadata:
                    existing.metadata.update(dict(metadata))
                record = existing
            else:
                record = OpenOrderRecord(
                    internal_order_id=internal_order_id,
                    venue_order_id=venue_order_id,
                    symbol=symbol,
                    status=status,
                    quantity=float(quantity),
                    filled_quantity=float(filled_quantity),
                    remaining_quantity=float(remaining),
                    side=side,
                    registered_at_utc=now,
                    updated_at_utc=now,
                    residual_open=status in OPEN_STATUSES,
                    metadata=dict(metadata or {}),
                )
                self._orders[internal_order_id] = record
            self._persist_unlocked()
            return deepcopy(record)

    def update_status(
        self,
        internal_order_id: str,
        *,
        status: str,
        venue_order_id: str | None = None,
        filled_quantity: float | None = None,
        remaining_quantity: float | None = None,
        kill_cancel_state: str | None = None,
        reason_code: str | None = None,
        confirmed_terminal: bool = False,
    ) -> OpenOrderRecord | None:
        with self._lock:
            record = self._orders.get(internal_order_id)
            if record is None:
                return None
            record.status = status
            record.updated_at_utc = utcnow().isoformat()
            if venue_order_id:
                record.venue_order_id = venue_order_id
            if filled_quantity is not None:
                record.filled_quantity = float(filled_quantity)
            if remaining_quantity is not None:
                record.remaining_quantity = float(remaining_quantity)
            if kill_cancel_state is not None:
                record.kill_cancel_state = kill_cancel_state
            if reason_code is not None:
                record.last_reason_code = reason_code

            if confirmed_terminal and status in TERMINAL_STATUSES:
                record.residual_open = False
                del self._orders[internal_order_id]
            elif status in OPEN_STATUSES:
                record.residual_open = True
            # Unknown / FAILED / unconfirmed CANCELLED: keep residual
            self._persist_unlocked()
            return deepcopy(record)

    def mark_cancel_outcome(
        self,
        internal_order_id: str,
        *,
        kill_cancel_state: str,
        reason_code: str,
        terminal_status: str | None = None,
        confirmed: bool = False,
    ) -> OpenOrderRecord | None:
        if not confirmed:
            # Keep in registry as residual open — never delete on error/unknown
            with self._lock:
                record = self._orders.get(internal_order_id)
                if record is None:
                    return None
                record.kill_cancel_state = kill_cancel_state
                record.last_reason_code = reason_code
                record.updated_at_utc = utcnow().isoformat()
                record.residual_open = True
                self._persist_unlocked()
                return deepcopy(record)
        status = terminal_status or "CANCELLED"
        return self.update_status(
            internal_order_id,
            status=status,
            kill_cancel_state=kill_cancel_state,
            reason_code=reason_code,
            confirmed_terminal=True,
        )

    def get(self, internal_order_id: str) -> OpenOrderRecord | None:
        with self._lock:
            record = self._orders.get(internal_order_id)
            return deepcopy(record) if record else None

    def list_open(self) -> list[OpenOrderRecord]:
        with self._lock:
            opens = [deepcopy(r) for r in self._orders.values() if r.is_open()]
            opens.sort(key=lambda r: (r.symbol, r.internal_order_id))
            return opens

    def list_all(self) -> list[OpenOrderRecord]:
        with self._lock:
            items = [deepcopy(r) for r in self._orders.values()]
            items.sort(key=lambda r: (r.symbol, r.internal_order_id))
            return items

    def count_open(self) -> int:
        return len(self.list_open())

    def clear_confirmed_only(self, internal_order_ids: Iterable[str]) -> None:
        """Remove only IDs already marked non-residual; never wipe unknowns."""
        with self._lock:
            for oid in list(internal_order_ids):
                record = self._orders.get(oid)
                if record is not None and not record.residual_open:
                    del self._orders[oid]
            self._persist_unlocked()

    def load_from_ledger(self) -> int:
        if self._ledger_path is None or not self._ledger_path.exists():
            return 0
        with self._lock:
            raw = json.loads(self._ledger_path.read_text(encoding="utf-8"))
            orders = raw.get("orders", raw if isinstance(raw, list) else [])
            self._orders.clear()
            for item in orders:
                record = OpenOrderRecord(
                    internal_order_id=str(item["internal_order_id"]),
                    venue_order_id=item.get("venue_order_id"),
                    symbol=str(item["symbol"]),
                    status=str(item.get("status", "PENDING")),
                    filled_quantity=float(item.get("filled_quantity", 0.0)),
                    remaining_quantity=float(item.get("remaining_quantity", 0.0)),
                    quantity=float(item.get("quantity", 0.0)),
                    side=item.get("side"),
                    registered_at_utc=str(item.get("registered_at_utc") or ""),
                    updated_at_utc=str(item.get("updated_at_utc") or ""),
                    kill_cancel_state=item.get("kill_cancel_state"),
                    last_reason_code=item.get("last_reason_code"),
                    residual_open=bool(item.get("residual_open", True)),
                    metadata=dict(item.get("metadata") or {}),
                )
                if record.residual_open or record.status in OPEN_STATUSES:
                    record.residual_open = True
                    self._orders[record.internal_order_id] = record
            return len(self._orders)

    def _persist_unlocked(self) -> None:
        if self._ledger_path is None:
            return
        payload = {
            "schema_version": "cdb-open-order-ledger/v1",
            "updated_at_utc": utcnow().isoformat(),
            "orders": [asdict(r) for r in self._orders.values()],
        }
        tmp = self._ledger_path.with_suffix(self._ledger_path.suffix + ".tmp")
        try:
            self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(
                json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
            )
            tmp.replace(self._ledger_path)
        except OSError as exc:
            # In-memory registry remains authoritative; do not fail order submit.
            logger.warning(
                "open-order ledger persist failed (%s): %s", self._ledger_path, exc
            )
