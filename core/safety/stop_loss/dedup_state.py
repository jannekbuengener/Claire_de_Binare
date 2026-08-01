"""Restart-safe dedup state for stop-loss protection events (Issue #4186).

The store is a two-phase, fail-closed ledger:

1. ``prepare`` persists the protection event *before* an exit intent is emitted.
2. ``finalize`` records that the intent was accepted by its sink.

A record left in ``PREPARED`` after a restart means "it is unknown whether the
intent was delivered". That state blocks — it must never lead to a second exit
intent, and it must never be silently ignored.

Missing or corrupt state also blocks. The store must be explicitly initialized
once (``initialize()``); an absent state file is never interpreted as "no
protection has happened yet".

Persistence is an abstraction: ``StopLossDedupStore`` defines the contract, and
``FileStopLossDedupStore`` is the local, non-productive implementation (atomic
temp-file rename, mirroring ``core/safety/kill_switch.py``). No productive DB
migration or mutation is part of this slice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from core.safety.stop_loss.contracts import StopLossContractError, StopLossReason

DEDUP_STATE_SCHEMA_VERSION = "cdb-stop-loss-dedup-state/v1"

_REQUIRED_RECORD_FIELDS = (
    "event_id",
    "fingerprint",
    "state",
    "symbol",
    "position_id",
)


class DedupRecordState(str, Enum):
    """Lifecycle of one dedup record."""

    PREPARED = "PREPARED"
    FINALIZED = "FINALIZED"


class StopLossDedupStateError(StopLossContractError):
    """Raised when the dedup state is missing, corrupt, or unwritable."""

    def __init__(self, reason: StopLossReason, message: str) -> None:
        super().__init__(f"{reason.value}: {message}")
        self.reason = reason


@dataclass(frozen=True)
class StopLossDedupRecord:
    """Persistent dedup entry for exactly one protection event."""

    event_id: str
    fingerprint: str
    state: DedupRecordState
    symbol: str
    position_id: str
    prepared_at_ms: int
    intent_id: Optional[str] = None
    finalized_at_ms: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "fingerprint": self.fingerprint,
            "state": self.state.value,
            "symbol": self.symbol,
            "position_id": self.position_id,
            "prepared_at_ms": self.prepared_at_ms,
            "intent_id": self.intent_id,
            "finalized_at_ms": self.finalized_at_ms,
        }

    @classmethod
    def from_dict(cls, payload: object) -> "StopLossDedupRecord":
        if not isinstance(payload, dict):
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"record must be an object, got {type(payload).__name__}",
            )
        missing = [field for field in _REQUIRED_RECORD_FIELDS if not payload.get(field)]
        if missing:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"record is missing required fields: {sorted(missing)}",
            )
        raw_state = payload.get("state")
        try:
            state = DedupRecordState(raw_state)
        except ValueError as exc:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"unknown dedup record state {raw_state!r}",
            ) from exc
        prepared_at_ms = payload.get("prepared_at_ms")
        if not isinstance(prepared_at_ms, int) or isinstance(prepared_at_ms, bool):
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"prepared_at_ms must be int, got {prepared_at_ms!r}",
            )
        finalized_at_ms = payload.get("finalized_at_ms")
        if finalized_at_ms is not None and (
            not isinstance(finalized_at_ms, int) or isinstance(finalized_at_ms, bool)
        ):
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"finalized_at_ms must be int or null, got {finalized_at_ms!r}",
            )
        if state is DedupRecordState.FINALIZED and not payload.get("intent_id"):
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"finalized record {payload['event_id']} has no intent_id",
            )
        return cls(
            event_id=str(payload["event_id"]),
            fingerprint=str(payload["fingerprint"]),
            state=state,
            symbol=str(payload["symbol"]),
            position_id=str(payload["position_id"]),
            prepared_at_ms=prepared_at_ms,
            intent_id=payload.get("intent_id"),
            finalized_at_ms=finalized_at_ms,
        )


@runtime_checkable
class StopLossDedupStore(Protocol):
    """Persistence abstraction for restart-safe protection dedup."""

    def initialize(self) -> None:
        """Create an empty, valid state surface if it does not exist yet."""

    def load(self, event_id: str) -> Optional[StopLossDedupRecord]:
        """Return the stored record, or ``None`` when the event is unknown.

        Raises:
            StopLossDedupStateError: if the state is missing or corrupt.
        """

    def prepare(self, record: StopLossDedupRecord) -> None:
        """Durably persist a ``PREPARED`` record before any intent is emitted."""

    def finalize(self, record: StopLossDedupRecord) -> None:
        """Durably persist the ``FINALIZED`` record after sink acceptance."""


class InMemoryStopLossDedupStore:
    """Non-persistent store for unit tests and shadow harnesses.

    Restart semantics can be simulated by handing the same ``records`` mapping
    to a new consumer instance.
    """

    def __init__(
        self, records: Optional[dict[str, StopLossDedupRecord]] = None
    ) -> None:
        self._records: dict[str, StopLossDedupRecord] = dict(records or {})
        self._initialized = records is not None

    def initialize(self) -> None:
        self._initialized = True

    def load(self, event_id: str) -> Optional[StopLossDedupRecord]:
        if not self._initialized:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_MISSING,
                "in-memory dedup store was never initialized",
            )
        return self._records.get(event_id)

    def prepare(self, record: StopLossDedupRecord) -> None:
        self._records[record.event_id] = replace(
            record, state=DedupRecordState.PREPARED
        )

    def finalize(self, record: StopLossDedupRecord) -> None:
        self._records[record.event_id] = replace(
            record, state=DedupRecordState.FINALIZED
        )

    @property
    def records(self) -> dict[str, StopLossDedupRecord]:
        return dict(self._records)


class FileStopLossDedupStore:
    """JSON-file backed dedup store with atomic writes and fail-closed reads."""

    def __init__(self, state_file: str | Path) -> None:
        self.state_file = Path(state_file)

    def initialize(self) -> None:
        if self.state_file.exists():
            # Validate instead of overwriting: a corrupt file must stay visible.
            self._read()
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._write({})

    def load(self, event_id: str) -> Optional[StopLossDedupRecord]:
        records = self._read()
        raw = records.get(event_id)
        if raw is None:
            return None
        record = StopLossDedupRecord.from_dict(raw)
        if record.event_id != event_id:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"record stored under {event_id!r} declares event_id {record.event_id!r}",
            )
        return record

    def prepare(self, record: StopLossDedupRecord) -> None:
        self._upsert(replace(record, state=DedupRecordState.PREPARED))

    def finalize(self, record: StopLossDedupRecord) -> None:
        self._upsert(replace(record, state=DedupRecordState.FINALIZED))

    def _upsert(self, record: StopLossDedupRecord) -> None:
        records = self._read()
        records[record.event_id] = record.to_dict()
        self._write(records)

    def _read(self) -> dict:
        if not self.state_file.exists():
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_MISSING,
                f"dedup state file {self.state_file} does not exist; "
                "an absent state is not an empty state",
            )
        try:
            raw = self.state_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"dedup state file {self.state_file} is unreadable: {exc}",
            ) from exc
        if not raw.strip():
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"dedup state file {self.state_file} is empty",
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"dedup state file {self.state_file} is not valid JSON: {exc}",
            ) from exc
        if not isinstance(payload, dict):
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"dedup state root must be an object, got {type(payload).__name__}",
            )
        schema_version = payload.get("schema_version")
        if schema_version != DEDUP_STATE_SCHEMA_VERSION:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"unsupported dedup state schema_version {schema_version!r} "
                f"(expected {DEDUP_STATE_SCHEMA_VERSION})",
            )
        records = payload.get("records")
        if not isinstance(records, dict):
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_STATE_CORRUPT,
                f"dedup state records must be an object, got {type(records).__name__}",
            )
        return records

    def _write(self, records: dict) -> None:
        payload = {
            "schema_version": DEDUP_STATE_SCHEMA_VERSION,
            "records": records,
        }
        temp_file = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
        try:
            temp_file.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            temp_file.replace(self.state_file)
        except OSError as exc:
            raise StopLossDedupStateError(
                StopLossReason.DEDUP_PREPARE_FAILED,
                f"failed to persist dedup state to {self.state_file}: {exc}",
            ) from exc
