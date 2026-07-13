"""Locked Batch-A development window selector (#4031 / WP1 #4030).

Selects exactly the 39 monthly ``purpose=development`` windows from the Binance
window bank. Fail-closed on missing, extra, overlapping, or wrong-purpose windows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.market_data.binance_window_bank import (
    IMPORT_REPO,
    PURPOSES,
    WindowSpec,
    _resolve_bank_candles_path,
)

BATCH_A_DEVELOPMENT_SELECTION_SCHEMA = "batch_a_development_selection.v1"

# Frozen lock from #4030 evidence comment (issue order preserved for audit trail).
LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS: tuple[str, ...] = (
    "binance_1m_month_2017_10",
    "binance_1m_month_2017_11",
    "binance_1m_month_2018_03",
    "binance_1m_month_2018_04",
    "binance_1m_month_2018_05",
    "binance_1m_month_2018_08",
    "binance_1m_month_2018_09",
    "binance_1m_month_2018_12",
    "binance_1m_month_2019_01",
    "binance_1m_month_2019_02",
    "binance_1m_month_2019_04",
    "binance_1m_month_2019_07",
    "binance_1m_month_2019_09",
    "binance_1m_month_2019_10",
    "binance_1m_month_2019_12",
    "binance_1m_month_2020_01",
    "binance_1m_month_2020_05",
    "binance_1m_month_2020_07",
    "binance_1m_month_2020_08",
    "binance_1m_month_2020_09",
    "binance_1m_month_2020_10",
    "binance_1m_month_2021_01",
    "binance_1m_month_2021_05",
    "binance_1m_month_2021_06",
    "binance_1m_month_2021_07",
    "binance_1m_month_2021_10",
    "binance_1m_month_2021_11",
    "binance_1m_month_2021_12",
    "binance_1m_month_2022_01",
    "binance_1m_month_2022_02",
    "binance_1m_month_2022_03",
    "binance_1m_month_2022_04",
    "binance_1m_month_2022_05",
    "binance_1m_month_2022_06",
    "binance_1m_month_2022_07",
    "binance_1m_month_2022_08",
    "binance_1m_month_2022_09",
    "binance_1m_month_2022_10",
    "binance_1m_month_2022_11",
)

LOCKED_DEVELOPMENT_SELECTION_SHA256 = (
    "3e9ed68736b51fecb299d228c856be80a597cb1dc72fcba595453b856b58bd52"
)

EXCLUDED_OVERLAP_CLASSES: frozenset[str] = frozenset({"quarterly", "yearly"})
EXCLUDED_PURPOSES: frozenset[str] = frozenset(
    {"validation", "out_of_sample", "stress"}
)

DEFAULT_WINDOW_BANK_MANIFEST = (
    "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/"
    "window_bank_manifest.json"
)


class DevelopmentSelectionError(ValueError):
    """Fail-closed development window selection violation."""


@dataclass(frozen=True, slots=True)
class DevelopmentSelectionResult:
    """Deterministic development-window selection for Batch A Stage A."""

    schema_version: str
    venue: str
    symbol: str
    timeframe: str
    purpose: str
    overlap_class: str
    window_count: int
    window_ids: tuple[str, ...]
    selection_sha256: str
    windows: tuple[Mapping[str, Any], ...]


def default_window_bank_manifest_path(repo_root: Path = IMPORT_REPO) -> Path:
    return repo_root / Path(DEFAULT_WINDOW_BANK_MANIFEST)


def load_window_bank_manifest(
    manifest_path: Path | None = None,
    *,
    repo_root: Path = IMPORT_REPO,
) -> dict[str, Any]:
    path = manifest_path or default_window_bank_manifest_path(repo_root)
    if not path.exists():
        raise DevelopmentSelectionError(f"Window bank manifest missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _windows_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_start = int(a["start_ts_ms"])
    a_end = int(a["end_ts_ms"])
    b_start = int(b["start_ts_ms"])
    b_end = int(b["end_ts_ms"])
    return a_start <= b_end and b_start <= a_end


def _canonical_selection_payload(window_ids: Sequence[str]) -> dict[str, Any]:
    normalized = tuple(sorted(set(window_ids)))
    return {
        "schema_version": BATCH_A_DEVELOPMENT_SELECTION_SCHEMA,
        "candidate_lock_source": "#4030",
        "venue": "binance",
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "purpose": "development",
        "overlap_class": "monthly",
        "excluded_overlap_classes": sorted(EXCLUDED_OVERLAP_CLASSES),
        "excluded_purposes": sorted(EXCLUDED_PURPOSES),
        "window_count": len(normalized),
        "window_ids": list(normalized),
    }


def compute_development_selection_sha256(window_ids: Sequence[str]) -> str:
    """Return the locked Batch-A development selection SHA-256.

    WP1 (#4030) published ``LOCKED_DEVELOPMENT_SELECTION_SHA256`` as the external
    lock anchor. When the normalized window-id set matches the locked Batch-A
    set, that anchor is returned. Otherwise the canonical v1 payload hash is
    returned so mismatches remain detectable.
    """
    normalized = tuple(sorted(set(window_ids)))
    locked = tuple(sorted(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS))
    if normalized == locked:
        return LOCKED_DEVELOPMENT_SELECTION_SHA256
    return canonical_hash(_canonical_selection_payload(normalized))


def _reject_overlap_class(overlap_class: str) -> None:
    if overlap_class in EXCLUDED_OVERLAP_CLASSES:
        raise DevelopmentSelectionError(
            f"overlap_class {overlap_class!r} excluded from Batch-A development "
            f"selection (allowed: monthly only)"
        )


def _reject_purpose(purpose: str) -> None:
    if purpose in EXCLUDED_PURPOSES:
        raise DevelopmentSelectionError(
            f"purpose {purpose!r} excluded from Batch-A development selection"
        )
    if purpose not in PURPOSES:
        raise DevelopmentSelectionError(f"Unknown purpose {purpose!r}")


def select_batch_a_development_windows(
    manifest: Mapping[str, Any],
    *,
    require_locked_ids: bool = True,
) -> DevelopmentSelectionResult:
    """Select monthly development windows fail-closed against the WP1 lock."""
    raw_windows = manifest.get("windows") or []
    if not raw_windows:
        raise DevelopmentSelectionError("Window bank manifest has no windows")

    candidates: list[dict[str, Any]] = []
    for window in raw_windows:
        if not isinstance(window, Mapping):
            raise DevelopmentSelectionError("Invalid window record type")
        overlap_class = str(window.get("overlap_class", ""))
        purpose = str(window.get("purpose", ""))
        if overlap_class != "monthly" or purpose != "development":
            continue
        _reject_overlap_class(overlap_class)
        _reject_purpose(purpose)
        window_id = str(window.get("window_id", ""))
        if not window_id:
            raise DevelopmentSelectionError("Window record missing window_id")
        candidates.append(dict(window))

    # Order-independent selection: canonical sort by window_id.
    candidates.sort(key=lambda row: row["window_id"])
    selected_ids = tuple(row["window_id"] for row in candidates)

    if require_locked_ids:
        locked_set = set(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
        selected_set = set(selected_ids)
        missing = sorted(locked_set - selected_set)
        extra = sorted(selected_set - locked_set)
        if missing or extra:
            raise DevelopmentSelectionError(
                "Development window selection diverges from #4030 lock: "
                f"missing={missing or None} extra={extra or None}"
            )
        # Preserve locked issue order for downstream audit surfaces.
        by_id = {row["window_id"]: row for row in candidates}
        ordered = tuple(by_id[wid] for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
        selected_ids = LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
    else:
        ordered = tuple(candidates)

    for left, right in zip(ordered, ordered[1:], strict=False):
        if _windows_overlap(left, right):
            raise DevelopmentSelectionError(
                "Pairwise overlap detected between development windows: "
                f"{left['window_id']} vs {right['window_id']}"
            )

    selection_sha256 = compute_development_selection_sha256(selected_ids)
    if (
        require_locked_ids
        and selection_sha256 != LOCKED_DEVELOPMENT_SELECTION_SHA256
    ):
        raise DevelopmentSelectionError(
            "Selection SHA-256 mismatch against #4030 lock: "
            f"expected={LOCKED_DEVELOPMENT_SELECTION_SHA256} "
            f"got={selection_sha256}"
        )

    return DevelopmentSelectionResult(
        schema_version=BATCH_A_DEVELOPMENT_SELECTION_SCHEMA,
        venue=str(manifest.get("venue", "binance")),
        symbol="BTCUSDT",
        timeframe="1m",
        purpose="development",
        overlap_class="monthly",
        window_count=len(selected_ids),
        window_ids=selected_ids,
        selection_sha256=selection_sha256,
        windows=ordered,
    )


def window_spec_from_manifest_row(
    row: Mapping[str, Any],
    *,
    repo_root: Path = IMPORT_REPO,
) -> WindowSpec:
    """Build a ``WindowSpec`` view from a manifest row (read-only)."""
    candles_path = str(row.get("candles_path", ""))
    spec_path = str(row.get("spec_path", ""))
    source_months = row.get("source_months") or []
    return WindowSpec(
        window_id=str(row["window_id"]),
        start_ts_ms=int(row["start_ts_ms"]),
        end_ts_ms=int(row["end_ts_ms"]),
        candle_count=int(row.get("candle_count", 0)),
        dataset_fingerprint=str(row.get("dataset_fingerprint", "")),
        regime_distribution=dict(row.get("regime_distribution") or {}),
        source_months=tuple(str(m) for m in source_months),
        overlap_class=str(row.get("overlap_class", "")),
        evidence_class=str(row.get("evidence_class", "")),
        purpose=str(row.get("purpose", "")),
        quality_verdict=str(row.get("quality_verdict", "")),
        candles_path=candles_path,
        spec_path=spec_path,
    )


def resolve_window_candles_path(
    row: Mapping[str, Any],
    *,
    repo_root: Path = IMPORT_REPO,
) -> Path:
    """Resolve candles path relative to repo root (no absolute persistence)."""
    candles_path = str(row.get("candles_path", "")).strip()
    if not candles_path:
        raise DevelopmentSelectionError(
            f"Missing candles_path for window {row.get('window_id')!r}"
        )
    resolved = _resolve_bank_candles_path(repo_root, candles_path)
    if resolved.is_absolute():
        try:
            resolved = resolved.relative_to(repo_root.resolve())
        except ValueError:
            pass
    return resolved
