"""ARVP dataset provider: load historical candle data for replay.

Part of ARVP §4.2 — Historical Data Access layer.
See docs/governance/arvp_platform.md for module boundary definitions.

Providers in this module are responsible for resolving a ``DatasetSpec`` into
an ordered, validated candle series ready for replay injection.

Current implementation status
------------------------------
``FileBackedDatasetProvider`` — **implemented**.
    Loads from a local JSON-array or JSONL file. Validates ordering, 1-minute
    cadence, required fields, warmup sufficiency, and exact window bounds
    (CDB-049 File/DB parity), except the explicit discover sentinel
    ``start_ts_ms == end_ts_ms == 0``.

``DBBackedDatasetProvider`` — **implemented** (Issue #1841 / PR #1857).
    Queries the ``candles_1m`` Postgres table populated by ``cdb_db_writer``
    from ``stream.candles_1m``. Persistence layer landed in Issue #1855 / PR #1856.

Boundary note
-------------
This provider layer validates transport/data-shape and the shared exact-window
contract (``start_ts_ms`` / ``end_ts_ms`` are the live window; the series must
include warmup bars before ``start_ts_ms``). It does NOT enforce bridge-level
semantics such as ``regime_id`` (added by ``historical_bridge.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from core.replay.dataset_identity import content_fingerprint, request_fingerprint
from core.replay.dataset_spec import (
    DatasetSpec,
    DatasetSpecError as DatasetSpecError,
)  # noqa: F401 — re-exported for caller convenience

__all__ = [
    "DatasetSpec",
    "DatasetSpecError",
    "DatasetLoadError",
    "DatasetResult",
    "FileBackedDatasetProvider",
    "DBBackedDatasetProvider",
    "is_file_discover_window",
    "warmup_start_ms",
    "enforce_exact_window",
]

_REQUIRED_CANDLE_FIELDS: frozenset[str] = frozenset({"ts_ms", "high", "low", "close"})
_ONE_MINUTE_MS: int = 60_000


def warmup_start_ms(spec: DatasetSpec) -> int:
    """First candle timestamp required for the live window + warmup prefix."""
    return int(spec.start_ts_ms) - int(spec.warmup_candles) * _ONE_MINUTE_MS


def is_file_discover_window(spec: DatasetSpec) -> bool:
    """Runner file-discover sentinel: bounds unknown until content is inspected.

    ``start_ts_ms == end_ts_ms == 0`` skips exact-window enforcement. Discover
    must not be claimed as window-parity proof until bounds are rebound and
    ``enforce_exact_window`` succeeds on the final spec (CDB-049).
    """
    return int(spec.start_ts_ms) == 0 and int(spec.end_ts_ms) == 0


def enforce_exact_window(
    candles: Sequence[dict],
    spec: DatasetSpec,
    source_label: str,
) -> None:
    """Fail-closed exact-window parity shared by File and DB providers (CDB-049).

    Requires:
      - non-empty ``candles``
      - first ``ts_ms`` == ``warmup_start_ms(spec)``
      - last ``ts_ms`` == ``spec.end_ts_ms``
      - ``len(candles) > spec.warmup_candles``
    """
    if not candles:
        raise DatasetLoadError(f"No candles in dataset: {source_label}")

    expected_first = warmup_start_ms(spec)
    actual_first = candles[0]["ts_ms"]
    if actual_first != expected_first:
        raise DatasetLoadError(
            f"exact-window violation for {source_label}: "
            f"expected first candle at ts_ms={expected_first} "
            f"(start_ts_ms={spec.start_ts_ms} - warmup_candles={spec.warmup_candles}), "
            f"got ts_ms={actual_first}."
        )

    actual_last = candles[-1]["ts_ms"]
    if actual_last != spec.end_ts_ms:
        raise DatasetLoadError(
            f"exact-window violation for {source_label}: "
            f"expected last candle at ts_ms={spec.end_ts_ms}, "
            f"got ts_ms={actual_last}."
        )

    if len(candles) <= spec.warmup_candles:
        raise DatasetLoadError(
            f"Insufficient candles for {source_label}: {len(candles)} total, "
            f"{spec.warmup_candles} warmup required. "
            f"Need at least {spec.warmup_candles + 1} candles."
        )


class DatasetLoadError(ValueError):
    """Raised when a dataset cannot be loaded or fails data-shape validation."""


@dataclass(frozen=True, slots=True)
class DatasetResult:
    """Immutable result of a successful dataset load operation.

    ``candles`` is a tuple of dicts (shallow-immutable at the container level).
    Inner dict values are all numeric primitives (int/float) and are effectively
    immutable. Do not mutate candle dicts after construction.

    Identity fields (#4151)
    -----------------------
    ``fingerprint`` / ``request_fingerprint``:
        Spec-level *request* identity (compatible alias pair).
    ``content_fingerprint``:
        Hash of the actually loaded candle content after semantic normalization.
        ``None`` only for synthetic/non-provider constructions that omit it.
    """

    spec: DatasetSpec
    candles: tuple  # tuple[dict, ...] — full series including warmup rows
    fingerprint: str
    warmup_count: int
    effective_candle_count: int
    request_fingerprint: str | None = None
    content_fingerprint: str | None = None


class DatasetProvider(Protocol):
    """Protocol for all ARVP dataset providers."""

    def load(self, spec: DatasetSpec) -> DatasetResult:
        pass


def _validate_candle_series(candles: list[dict], source_label: str) -> None:
    """Validate a candle series for shape, ordering, and 1-minute cadence.

    Shared by all providers. ``source_label`` is included in error messages
    for diagnostic clarity (e.g. ``str(file_path)`` or ``"db:BTCUSDT"``).

    Checks (in order):
      - Non-empty series
      - All ``_REQUIRED_CANDLE_FIELDS`` present and non-None in every row
      - ``ts_ms`` strictly increasing across consecutive rows
      - Exactly ``_ONE_MINUTE_MS`` (60 000 ms) gap between consecutive rows
    """
    if not candles:
        raise DatasetLoadError(f"No candles in dataset: {source_label}")

    for idx, candle in enumerate(candles):
        missing = _REQUIRED_CANDLE_FIELDS - candle.keys()
        if missing:
            raise DatasetLoadError(
                f"Candle at index {idx} is missing required fields "
                f"{sorted(missing)}: {candle!r}"
            )
        for key in _REQUIRED_CANDLE_FIELDS:
            if candle[key] is None:
                raise DatasetLoadError(
                    f"Candle at index {idx} has None value for required field "
                    f"{key!r}: {candle!r}"
                )

    for idx in range(1, len(candles)):
        prev_ts = candles[idx - 1]["ts_ms"]
        curr_ts = candles[idx]["ts_ms"]
        if curr_ts <= prev_ts:
            raise DatasetLoadError(
                f"ts_ms must be strictly increasing: "
                f"candle[{idx - 1}]={prev_ts}, candle[{idx}]={curr_ts}. "
                f"Source: {source_label}"
            )
        delta = curr_ts - prev_ts
        if delta != _ONE_MINUTE_MS:
            raise DatasetLoadError(
                f"1m cadence violation: expected {_ONE_MINUTE_MS}ms gap, "
                f"got {delta}ms between candle[{idx - 1}] (ts={prev_ts}) "
                f"and candle[{idx}] (ts={curr_ts}). Source: {source_label}"
            )


class FileBackedDatasetProvider:
    """Load historical candle data from a local JSON-array or JSONL file.

    Accepts:
      - JSON array (``[{...}, ...]``) — all objects in one file
      - JSONL — one JSON object per line; blank lines are skipped

    Validates:
      - Non-empty series after parsing
      - All required fields present in each row: ``ts_ms``, ``high``, ``low``,
        ``close``
      - ``ts_ms`` strictly increasing across consecutive rows
      - Exactly 1-minute (60 000 ms) cadence between consecutive rows
      - Exact window parity with DB (CDB-049), unless discover sentinel
        ``start_ts_ms == end_ts_ms == 0``: first candle at warmup start,
        last candle at ``end_ts_ms``, and ``len(candles) > warmup_candles``

    The file is not sliced; content must already match the requested window.
    """

    def load(self, spec: DatasetSpec) -> DatasetResult:
        spec.validate()

        if spec.source != "file":
            raise DatasetLoadError(
                f"FileBackedDatasetProvider requires source='file', "
                f"got source={spec.source!r}."
            )

        file_path = Path(spec.file_path)  # type: ignore[arg-type]  # validated non-None above

        if not file_path.exists():
            raise DatasetLoadError(f"Dataset file not found: {file_path}")

        try:
            raw = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DatasetLoadError(
                f"Cannot read dataset file {file_path}: {exc}"
            ) from exc

        candles = self._parse(raw, file_path)
        source_label = str(file_path)
        _validate_candle_series(candles, source_label)

        if is_file_discover_window(spec):
            # Discover path: shape/cadence/warmup-length only; no window claim.
            if len(candles) <= spec.warmup_candles:
                raise DatasetLoadError(
                    f"Insufficient candles: {len(candles)} total, "
                    f"{spec.warmup_candles} warmup required. "
                    f"Need at least {spec.warmup_candles + 1} candles."
                )
        else:
            enforce_exact_window(candles, spec, source_label)

        loaded = tuple(dict(c) for c in candles)
        req_fp = request_fingerprint(spec)
        return DatasetResult(
            spec=spec,
            candles=loaded,
            fingerprint=req_fp,
            warmup_count=spec.warmup_candles,
            effective_candle_count=len(candles) - spec.warmup_candles,
            request_fingerprint=req_fp,
            content_fingerprint=content_fingerprint(loaded),
        )

    def _parse(self, raw: str, file_path: Path) -> list[dict]:
        text = raw.strip()
        if not text:
            raise DatasetLoadError(f"Dataset file is empty: {file_path}")

        if text.startswith("["):
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise DatasetLoadError(
                    f"Invalid JSON in dataset file {file_path}: {exc}"
                ) from exc
            if not isinstance(data, list):
                raise DatasetLoadError(
                    f"Expected JSON array in {file_path}, got {type(data).__name__}."
                )
            if not data:
                raise DatasetLoadError(
                    f"Dataset file contains an empty array: {file_path}"
                )
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise DatasetLoadError(
                        f"Expected JSON object at index {idx} in {file_path}, "
                        f"got {type(item).__name__}."
                    )
            return data

        # JSONL: one JSON object per line
        rows: list[dict] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetLoadError(
                    f"Invalid JSON on line {lineno} of {file_path}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise DatasetLoadError(
                    f"Expected JSON object on line {lineno} of {file_path}, "
                    f"got {type(row).__name__}."
                )
            rows.append(row)

        if not rows:
            raise DatasetLoadError(f"Dataset file contains no candle rows: {file_path}")
        return rows


class DBBackedDatasetProvider:
    """Load historical candle data from the Postgres ``candles_1m`` table.

    Requires an injected psycopg2-compatible database connection. The provider
    does not manage the connection lifecycle.

    Validates:
      - ``spec.source == "db"`` (fail-closed on source mismatch)
      - DB result covers the full requested window including warmup rows:
        first row ``ts_ms`` == ``warmup_start_ms``, last row ``ts_ms`` ==
        ``spec.end_ts_ms``
      - All required fields present and non-None in each row
      - ``ts_ms`` strictly increasing at exactly 1-minute cadence

    Note on ``db_dataset_window``
    -------------------------
    ``spec.db_dataset_window`` is a **caller-provided logical label** used for
    audit trail and deterministic fingerprinting via ``DatasetSpec.fingerprint()``.
    It does NOT resolve to a persisted dataset record and does NOT constrain
    the DB query. The query is keyed solely on ``spec.symbol`` and the time
    window ``[warmup_start_ms(spec), spec.end_ts_ms]``. Exact first/last candle
    bounds are enforced via shared ``enforce_exact_window`` (CDB-049).

    Candle persistence is provided by ``cdb_db_writer`` from
    ``stream.candles_1m`` (landed in GitHub Issue #1855 / PR #1856).
    Tracked in GitHub Issue #1841.
    """

    def __init__(self, db_conn) -> None:
        """Inject a psycopg2 connection. Provider does not manage connection lifecycle."""
        self._db_conn = db_conn

    def load(self, spec: DatasetSpec) -> DatasetResult:
        spec.validate()

        if spec.source != "db":
            raise DatasetLoadError(
                f"DBBackedDatasetProvider requires source='db', "
                f"got source={spec.source!r}."
            )

        window_first_ms: int = warmup_start_ms(spec)

        try:
            cursor = self._db_conn.cursor()
            cursor.execute(
                """
                SELECT ts_ms, open, high, low, close, volume, trade_count, regime_id
                FROM candles_1m
                WHERE symbol = %s
                  AND ts_ms >= %s
                  AND ts_ms <= %s
                ORDER BY ts_ms ASC
                """,
                (spec.symbol, window_first_ms, spec.end_ts_ms),
            )
            rows = cursor.fetchall()
        except Exception as exc:
            raise DatasetLoadError(
                f"DB query failed for candles_1m (symbol={spec.symbol!r}, "
                f"window=[{window_first_ms}, {spec.end_ts_ms}]): {exc}"
            ) from exc

        if not rows:
            raise DatasetLoadError(
                f"No candles found in candles_1m for symbol={spec.symbol!r} "
                f"in window [{window_first_ms}, {spec.end_ts_ms}]. "
                f"Hint: candles_1m is populated by cdb_db_writer from stream.candles_1m."
            )

        candles: list[dict] = [
            {
                "symbol": spec.symbol,
                "ts_ms": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "trade_count": row[6],
                "regime_id": row[7],
            }
            for row in rows
        ]

        source_label = f"db:{spec.symbol}"
        _validate_candle_series(candles, source_label=source_label)
        enforce_exact_window(candles, spec, source_label)

        loaded = tuple(dict(c) for c in candles)
        req_fp = request_fingerprint(spec)
        return DatasetResult(
            spec=spec,
            candles=loaded,
            fingerprint=req_fp,
            warmup_count=spec.warmup_candles,
            effective_candle_count=len(candles) - spec.warmup_candles,
            request_fingerprint=req_fp,
            content_fingerprint=content_fingerprint(loaded),
        )
