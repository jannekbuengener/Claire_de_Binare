"""Locked Batch-A Stage-B window selector (#4032 / WP4).

Selects validation, out-of-sample, and stress windows from the Binance window
bank for historical confirmation. Excludes the 39 locked development windows.
Fail-closed on count drift, overlap with development, or purpose mismatch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.market_data.binance_window_bank import IMPORT_REPO, PURPOSES
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    DevelopmentSelectionError,
    default_window_bank_manifest_path,
    load_window_bank_manifest,
)

STAGE_B_SELECTION_SCHEMA = "batch_a_stage_b_selection.v1"

STAGE_B_PURPOSES: frozenset[str] = frozenset(
    {"validation", "out_of_sample", "stress"}
)

EXPECTED_STAGE_B_TOTAL = 62
EXPECTED_VALIDATION = 35
EXPECTED_OUT_OF_SAMPLE = 22
EXPECTED_STRESS = 5
EXPECTED_MONTHLY_VALIDATION = 27
EXPECTED_MONTHLY_OOS = 15


class StageBSelectionError(ValueError):
    """Fail-closed Stage-B window selection violation."""


@dataclass(frozen=True, slots=True)
class StageBSelectionResult:
    """Deterministic Stage-B window selection for Batch-A confirmation."""

    schema_version: str
    venue: str
    symbol: str
    timeframe: str
    window_count: int
    purpose_counts: dict[str, int]
    overlap_class_counts: dict[str, int]
    monthly_validation_count: int
    monthly_out_of_sample_count: int
    stress_count: int
    quarterly_count: int
    yearly_count: int
    corroborative_only_count: int
    window_ids: tuple[str, ...]
    selection_sha256: str
    windows: tuple[Mapping[str, Any], ...]
    excluded_development_window_ids: tuple[str, ...]


def _canonical_selection_payload(
    window_ids: Sequence[str],
    *,
    purpose_counts: Mapping[str, int],
    overlap_class_counts: Mapping[str, int],
) -> dict[str, Any]:
    normalized = tuple(sorted(set(window_ids)))
    return {
        "schema_version": STAGE_B_SELECTION_SCHEMA,
        "candidate_lock_source": "#4030",
        "venue": "binance",
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "purposes": sorted(STAGE_B_PURPOSES),
        "excluded_development_window_ids": sorted(
            LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
        ),
        "window_count": len(normalized),
        "purpose_counts": dict(sorted(purpose_counts.items())),
        "overlap_class_counts": dict(sorted(overlap_class_counts.items())),
        "window_ids": list(normalized),
    }


def compute_stage_b_selection_sha256(
    window_ids: Sequence[str],
    *,
    purpose_counts: Mapping[str, int],
    overlap_class_counts: Mapping[str, int],
) -> str:
    return canonical_hash(
        _canonical_selection_payload(
            window_ids,
            purpose_counts=purpose_counts,
            overlap_class_counts=overlap_class_counts,
        )
    )


def _classify_window(row: Mapping[str, Any]) -> dict[str, str]:
    purpose = str(row.get("purpose", ""))
    overlap = str(row.get("overlap_class", ""))
    return {
        "purpose": purpose,
        "overlap_class": overlap,
        "slice": _slice_name(purpose, overlap),
    }


def _slice_name(purpose: str, overlap_class: str) -> str:
    if purpose == "validation" and overlap_class == "monthly":
        return "validation_monthly"
    if purpose == "out_of_sample" and overlap_class == "monthly":
        return "out_of_sample_monthly"
    if purpose == "stress" and overlap_class == "stress":
        return "stress"
    if overlap_class == "quarterly":
        return "corroborative_quarterly"
    if overlap_class == "yearly":
        return "corroborative_yearly"
    return f"{purpose}_{overlap_class}"


def select_batch_a_stage_b_windows(
    manifest: Mapping[str, Any],
    *,
    require_expected_counts: bool = True,
) -> StageBSelectionResult:
    """Select Stage-B windows fail-closed against the WP4 lock."""
    raw_windows = manifest.get("windows") or []
    if not raw_windows:
        raise StageBSelectionError("Window bank manifest has no windows")

    dev_set = set(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    selected: list[dict[str, Any]] = []
    purpose_counts: dict[str, int] = {}
    overlap_counts: dict[str, int] = {}
    monthly_validation = 0
    monthly_oos = 0
    stress_count = 0
    quarterly_count = 0
    yearly_count = 0

    for window in raw_windows:
        if not isinstance(window, Mapping):
            raise StageBSelectionError("Invalid window record type")
        purpose = str(window.get("purpose", ""))
        overlap = str(window.get("overlap_class", ""))
        window_id = str(window.get("window_id", ""))
        if not window_id:
            raise StageBSelectionError("Window record missing window_id")
        if purpose not in STAGE_B_PURPOSES:
            continue
        if purpose not in PURPOSES:
            raise StageBSelectionError(f"Unknown purpose {purpose!r}")
        if window_id in dev_set:
            raise StageBSelectionError(
                f"Stage-B window overlaps development lock: {window_id}"
            )
        row = dict(window)
        row["stage_b_slice"] = _slice_name(purpose, overlap)
        selected.append(row)
        purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
        overlap_counts[overlap] = overlap_counts.get(overlap, 0) + 1
        if purpose == "validation" and overlap == "monthly":
            monthly_validation += 1
        elif purpose == "out_of_sample" and overlap == "monthly":
            monthly_oos += 1
        elif purpose == "stress" and overlap == "stress":
            stress_count += 1
        elif overlap == "quarterly":
            quarterly_count += 1
        elif overlap == "yearly":
            yearly_count += 1

    selected.sort(key=lambda row: row["window_id"])
    window_ids = tuple(row["window_id"] for row in selected)

    if require_expected_counts:
        if len(window_ids) != EXPECTED_STAGE_B_TOTAL:
            raise StageBSelectionError(
                f"Stage-B window count mismatch: expected={EXPECTED_STAGE_B_TOTAL} "
                f"got={len(window_ids)}"
            )
        if purpose_counts.get("validation") != EXPECTED_VALIDATION:
            raise StageBSelectionError(
                "validation count mismatch: "
                f"expected={EXPECTED_VALIDATION} got={purpose_counts.get('validation')}"
            )
        if purpose_counts.get("out_of_sample") != EXPECTED_OUT_OF_SAMPLE:
            raise StageBSelectionError(
                "out_of_sample count mismatch: "
                f"expected={EXPECTED_OUT_OF_SAMPLE} "
                f"got={purpose_counts.get('out_of_sample')}"
            )
        if purpose_counts.get("stress") != EXPECTED_STRESS:
            raise StageBSelectionError(
                f"stress count mismatch: expected={EXPECTED_STRESS} "
                f"got={purpose_counts.get('stress')}"
            )
        if monthly_validation != EXPECTED_MONTHLY_VALIDATION:
            raise StageBSelectionError(
                "monthly validation count mismatch: "
                f"expected={EXPECTED_MONTHLY_VALIDATION} got={monthly_validation}"
            )
        if monthly_oos != EXPECTED_MONTHLY_OOS:
            raise StageBSelectionError(
                "monthly oos count mismatch: "
                f"expected={EXPECTED_MONTHLY_OOS} got={monthly_oos}"
            )

    selection_sha256 = compute_stage_b_selection_sha256(
        window_ids,
        purpose_counts=purpose_counts,
        overlap_class_counts=overlap_counts,
    )

    return StageBSelectionResult(
        schema_version=STAGE_B_SELECTION_SCHEMA,
        venue=str(manifest.get("venue", "binance")),
        symbol="BTCUSDT",
        timeframe="1m",
        window_count=len(window_ids),
        purpose_counts=dict(sorted(purpose_counts.items())),
        overlap_class_counts=dict(sorted(overlap_counts.items())),
        monthly_validation_count=monthly_validation,
        monthly_out_of_sample_count=monthly_oos,
        stress_count=stress_count,
        quarterly_count=quarterly_count,
        yearly_count=yearly_count,
        corroborative_only_count=quarterly_count + yearly_count,
        window_ids=window_ids,
        selection_sha256=selection_sha256,
        windows=tuple(selected),
        excluded_development_window_ids=LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    )


def load_stage_b_manifest(
    manifest_path: Path | None = None,
    *,
    repo_root: Path = IMPORT_REPO,
) -> dict[str, Any]:
    path = manifest_path or default_window_bank_manifest_path(repo_root)
    if not path.exists():
        raise StageBSelectionError(f"Window bank manifest missing: {path}")
    return load_window_bank_manifest(path, repo_root=repo_root)
