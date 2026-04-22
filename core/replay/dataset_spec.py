"""ARVP dataset specification: frozen contract for historical replay data requests.

Part of ARVP §4.2 — Historical Data Access layer.
See docs/governance/arvp_platform.md for module boundary definitions.

This module defines the immutable spec that callers use to declare *what* data
they want for a replay run. Providers (dataset_provider.py) are responsible for
*how* that data is loaded and validated.

Fingerprint note: ``DatasetSpec.fingerprint()`` is a *request* identity hash,
not a *dataset content* hash. Two specs with identical fields produce the same
fingerprint regardless of the file content at ``file_path``. Content-based
hashing is deferred to the runner/reporting layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.replay.canonical_json import canonical_hash

_VALID_SYMBOLS: frozenset[str] = frozenset({"BTCUSDT"})
_VALID_TIMEFRAMES: frozenset[str] = frozenset({"1m"})


class DatasetSpecError(ValueError):
    """Raised when a ``DatasetSpec`` fails invariant validation."""


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Immutable specification for a historical replay dataset request.

    Fields
    ------
    symbol:
        Trading pair. Must be in the allowed symbol set (currently ``BTCUSDT``).
    timeframe:
        Candle interval. Only ``"1m"`` is supported in this ARVP phase.
    start_ts_ms:
        Inclusive start of the requested window in milliseconds (UTC epoch).
    end_ts_ms:
        Inclusive end of the requested window in milliseconds (UTC epoch).
    warmup_candles:
        Number of candles at the head of the series reserved for indicator
        warm-up. Must be >= 0.
    source:
        ``"file"`` — load from a local file (``file_path`` required).
        ``"db"``  — load from Postgres (``db_dataset_id`` required; not yet
        implemented — see ``DBBackedDatasetProvider``).
    file_path:
        Absolute path to a JSON-array or JSONL file. Required when
        ``source="file"``; must be ``None`` when ``source="db"``.
    db_dataset_id:
        Identifier for a persisted dataset record. Required when
        ``source="db"``; must be ``None`` when ``source="file"``.
    """

    symbol: str
    timeframe: str
    start_ts_ms: int
    end_ts_ms: int
    warmup_candles: int
    source: Literal["file", "db"]
    file_path: str | None = None
    db_dataset_id: str | None = None

    def validate(self) -> None:
        """Fail-closed invariant check. Raises ``DatasetSpecError`` on any violation."""
        if self.symbol not in _VALID_SYMBOLS:
            raise DatasetSpecError(
                f"Invalid symbol {self.symbol!r}. Allowed: {sorted(_VALID_SYMBOLS)}"
            )
        if self.timeframe not in _VALID_TIMEFRAMES:
            raise DatasetSpecError(
                f"Invalid timeframe {self.timeframe!r}. Only '1m' is supported in this phase."
            )
        if self.start_ts_ms > self.end_ts_ms:
            raise DatasetSpecError(
                f"start_ts_ms ({self.start_ts_ms}) must be <= end_ts_ms ({self.end_ts_ms})."
            )
        if self.warmup_candles < 0:
            raise DatasetSpecError(
                f"warmup_candles must be >= 0, got {self.warmup_candles}."
            )
        if self.source == "file":
            if self.file_path is None:
                raise DatasetSpecError("source='file' requires file_path.")
            if self.db_dataset_id is not None:
                raise DatasetSpecError(
                    "source='file' and source='db' fields are mutually exclusive: "
                    "db_dataset_id must be None when source='file'."
                )
        elif self.source == "db":
            if self.db_dataset_id is None:
                raise DatasetSpecError("source='db' requires db_dataset_id.")
            if self.file_path is not None:
                raise DatasetSpecError(
                    "source='file' and source='db' fields are mutually exclusive: "
                    "file_path must be None when source='db'."
                )
        else:
            raise DatasetSpecError(
                f"Unknown source {self.source!r}. Must be 'file' or 'db'."
            )

    def to_dict(self) -> dict:
        """Serialize to dict, omitting ``None``-valued optional fields."""
        d: dict = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_ts_ms": self.start_ts_ms,
            "end_ts_ms": self.end_ts_ms,
            "warmup_candles": self.warmup_candles,
            "source": self.source,
        }
        if self.file_path is not None:
            d["file_path"] = self.file_path
        if self.db_dataset_id is not None:
            d["db_dataset_id"] = self.db_dataset_id
        return d

    def fingerprint(self) -> str:
        """Deterministic 64-char SHA-256 hex of the spec (request identity).

        Two ``DatasetSpec`` instances with identical field values always produce
        the same fingerprint. This is a *request* fingerprint, not a *content*
        fingerprint — it does not depend on what the file at ``file_path``
        actually contains.
        """
        return canonical_hash(self.to_dict())
