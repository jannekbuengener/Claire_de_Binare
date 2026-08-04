"""Read-only Binance window-bank dataset adapter for Batch-A replay (#4031).

Resolves canonical window-bank paths, loads OHLCV candles for replay runners, and
passes through regime enrichment metadata without mutating source files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.dataset_provider import (
    DatasetLoadError,
    DatasetResult,
    FileBackedDatasetProvider,
    _validate_candle_series,
)
from core.replay.dataset_spec import DatasetSpec
from tools.market_data.binance_window_bank import (
    IMPORT_REPO,
    _resolve_bank_candles_path,
)
from tools.market_data.development_window_selector import (
    DevelopmentSelectionError,
    resolve_window_candles_path,
)

BATCH_A_WINDOW_BANK_ROOT = "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m"


class BinanceWindowBankAdapterError(ValueError):
    """Fail-closed Binance window-bank adapter error."""


@dataclass(frozen=True, slots=True)
class BinanceWindowDatasetRef:
    window_id: str
    spec_path: str
    candles_path: str
    dataset_fingerprint: str | None
    purpose: str | None
    overlap_class: str | None
    regime_distribution: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class BinanceWindowDataset:
    ref: BinanceWindowDatasetRef
    spec: Mapping[str, Any]
    candles: tuple[dict[str, Any], ...]
    dataset_result: DatasetResult


def default_window_bank_root(repo_root: Path = IMPORT_REPO) -> Path:
    return repo_root / Path(BATCH_A_WINDOW_BANK_ROOT)


def resolve_window_bank_paths(
    window_id: str,
    *,
    repo_root: Path = IMPORT_REPO,
    window_bank_root: Path | None = None,
) -> BinanceWindowDatasetRef:
    """Resolve dataset_spec and candles paths for a window_id (read-only)."""
    if not window_id:
        raise BinanceWindowBankAdapterError("window_id is required")

    bank_root = window_bank_root or default_window_bank_root(repo_root)
    window_dir = bank_root / window_id
    spec_path = window_dir / "dataset_spec.json"
    candles_path = window_dir / "candles.jsonl"

    if spec_path.exists():
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec_candles = str(spec.get("file_path", "")).strip()
        if spec_candles:
            resolved_candles = _resolve_bank_candles_path(repo_root, spec_candles)
        elif candles_path.exists():
            resolved_candles = candles_path
        else:
            raise BinanceWindowBankAdapterError(
                f"Missing candles for window {window_id!r}: {candles_path}"
            )
        return BinanceWindowDatasetRef(
            window_id=window_id,
            spec_path=_repo_relative(repo_root, spec_path),
            candles_path=_repo_relative(repo_root, resolved_candles),
            dataset_fingerprint=spec.get("fingerprint") or spec.get("candles_sha256"),
            purpose=spec.get("purpose"),
            overlap_class=spec.get("overlap_class"),
            regime_distribution=spec.get("regime_distribution"),
        )

    if not candles_path.exists():
        raise BinanceWindowBankAdapterError(
            f"Window dataset missing for {window_id!r} under {window_dir}"
        )

    return BinanceWindowDatasetRef(
        window_id=window_id,
        spec_path=_repo_relative(repo_root, spec_path) if spec_path.exists() else "",
        candles_path=_repo_relative(repo_root, candles_path),
        dataset_fingerprint=None,
        purpose=None,
        overlap_class=None,
        regime_distribution=None,
    )


def load_dataset_spec(spec_path: Path) -> dict[str, Any]:
    if not spec_path.exists():
        raise BinanceWindowBankAdapterError(f"dataset_spec missing: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    _validate_dataset_spec(spec, spec_path)
    return spec


def _validate_dataset_spec(spec: Mapping[str, Any], spec_path: Path) -> None:
    required = ("window_id", "symbol", "timeframe", "start_ts_ms", "end_ts_ms")
    missing = [key for key in required if spec.get(key) is None]
    if missing:
        raise BinanceWindowBankAdapterError(
            f"dataset_spec missing required fields {missing}: {spec_path}"
        )
    if str(spec.get("symbol")) != "BTCUSDT":
        raise BinanceWindowBankAdapterError(
            f"dataset_spec symbol mismatch: {spec.get('symbol')!r}"
        )
    if str(spec.get("timeframe")) != "1m":
        raise BinanceWindowBankAdapterError(
            f"dataset_spec timeframe mismatch: {spec.get('timeframe')!r}"
        )
    start_ts = int(spec["start_ts_ms"])
    end_ts = int(spec["end_ts_ms"])
    if end_ts < start_ts:
        raise BinanceWindowBankAdapterError(
            f"dataset_spec end_ts_ms < start_ts_ms for {spec.get('window_id')!r}"
        )


def load_window_candles_jsonl(candles_path: Path) -> list[dict[str, Any]]:
    if not candles_path.exists():
        raise BinanceWindowBankAdapterError(f"candles file missing: {candles_path}")
    candles: list[dict[str, Any]] = []
    for line_no, line in enumerate(
        candles_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BinanceWindowBankAdapterError(
                f"Invalid JSONL at {candles_path}:{line_no}"
            ) from exc
        candles.append(row)
    _validate_candle_series(candles, str(candles_path))
    return candles


def load_binance_window_dataset(
    window_id: str,
    *,
    warmup_candles: int = 0,
    repo_root: Path = IMPORT_REPO,
    window_bank_root: Path | None = None,
) -> BinanceWindowDataset:
    """Load a single Binance window-bank dataset for replay runners.

    Builds a ``DatasetSpec`` under the shared CDB-049 contract:
    ``start_ts_ms`` / ``end_ts_ms`` are the *live* window. The candle series
    must include the warmup prefix before ``start_ts_ms``. Window-bank JSON
    metadata that stores the series-first timestamp as ``start_ts_ms`` is
    rebound to the live start when ``warmup_candles > 0``.
    """
    ref = resolve_window_bank_paths(
        window_id,
        repo_root=repo_root,
        window_bank_root=window_bank_root,
    )
    candles_path = repo_root / ref.candles_path
    meta: dict[str, Any]
    if ref.spec_path:
        spec_path = repo_root / ref.spec_path
        meta = load_dataset_spec(spec_path)
    else:
        candles = load_window_candles_jsonl(candles_path)
        meta = {
            "window_id": window_id,
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "start_ts_ms": int(candles[0]["ts_ms"]),
            "end_ts_ms": int(candles[-1]["ts_ms"]),
        }

    candles = load_window_candles_jsonl(candles_path)
    warmup = max(0, int(warmup_candles))
    if len(candles) <= warmup:
        raise BinanceWindowBankAdapterError(
            f"Insufficient candles for window {window_id!r}: {len(candles)} total, "
            f"{warmup} warmup required."
        )

    series_first = int(candles[0]["ts_ms"])
    series_last = int(candles[-1]["ts_ms"])
    live_start = int(candles[warmup]["ts_ms"])
    live_end = series_last
    declared_start = int(meta["start_ts_ms"])
    declared_end = int(meta["end_ts_ms"])

    if declared_end != series_last:
        raise BinanceWindowBankAdapterError(
            f"window {window_id!r} end mismatch: dataset_spec end_ts_ms={declared_end} "
            f"!= last candle ts_ms={series_last}"
        )
    if declared_start not in (series_first, live_start):
        raise BinanceWindowBankAdapterError(
            f"window {window_id!r} start mismatch: dataset_spec start_ts_ms={declared_start} "
            f"matches neither series_first={series_first} nor live_start={live_start}"
        )
    if declared_start == live_start and series_first != live_start - warmup * 60_000:
        raise BinanceWindowBankAdapterError(
            f"window {window_id!r} missing warmup prefix: expected first candle "
            f"ts_ms={live_start - warmup * 60_000}, got {series_first}"
        )

    dataset_spec = DatasetSpec(
        symbol=str(meta["symbol"]),
        timeframe=str(meta["timeframe"]),
        start_ts_ms=live_start,
        end_ts_ms=live_end,
        warmup_candles=warmup,
        source="file",
        file_path=str(candles_path),
    )
    dataset_spec.validate()
    provider = FileBackedDatasetProvider()
    try:
        dataset_result = provider.load(dataset_spec)
    except DatasetLoadError as exc:
        raise BinanceWindowBankAdapterError(str(exc)) from exc

    return BinanceWindowDataset(
        ref=ref,
        spec=meta,
        candles=tuple(candles),
        dataset_result=dataset_result,
    )


def load_binance_window_from_manifest_row(
    row: Mapping[str, Any],
    *,
    warmup_candles: int = 0,
    repo_root: Path = IMPORT_REPO,
) -> BinanceWindowDataset:
    window_id = str(row.get("window_id", ""))
    if not window_id:
        raise DevelopmentSelectionError("Manifest row missing window_id")
    candles_path = resolve_window_candles_path(row, repo_root=repo_root)
    if not candles_path.is_absolute():
        candles_path = repo_root / candles_path
    spec_path_value = str(row.get("spec_path", "")).strip()
    spec_path = (
        _resolve_bank_candles_path(repo_root, spec_path_value)
        if spec_path_value
        else candles_path.parent / "dataset_spec.json"
    )
    if spec_path.exists():
        load_dataset_spec(spec_path)
    else:
        load_window_candles_jsonl(candles_path)
    return load_binance_window_dataset(
        window_id,
        warmup_candles=warmup_candles,
        repo_root=repo_root,
    )


def load_binance_windows_for_strategy(
    window_ids: Sequence[str],
    *,
    warmup_candles: int,
    repo_root: Path = IMPORT_REPO,
) -> list[BinanceWindowDataset]:
    return [
        load_binance_window_dataset(
            window_id,
            warmup_candles=warmup_candles,
            repo_root=repo_root,
        )
        for window_id in window_ids
    ]


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
