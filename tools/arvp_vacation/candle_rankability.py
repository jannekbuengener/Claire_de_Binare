"""Candle field normalization and rankability provenance (#4065 / #4336 CDB-052).

Preserves legacy producer semantics for ``candles_total`` while emitting explicit
``candles_input_total``, ``warmup_bars``, and ``candles_evaluated`` for rankability.

Warmup must be historically provable from the run's dataset summary. Batch-A
manifest values may only *verify* run warmup — never silently fill missing
warmup provenance (CDB-052 fail-closed / no stale-manifest fallback).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

BATCH_A_MANIFEST_PATH = Path("docs/contracts/batch_a_funnel_manifest.v1.json")
BATCH_A_CAMPAIGN_PREFIX = "batch_a_stage_a_"

FLAG_WARMUP_TRIM_APPLIED = "warmup_trim_applied"
FLAG_CANDLES_EVALUATED_MISMATCH = "candles_evaluated_mismatch"
FLAG_WARMUP_PROVENANCE_MISSING = "warmup_provenance_missing"
FLAG_WARMUP_MANIFEST_MISMATCH = "warmup_manifest_mismatch"
FLAG_CANDLES_INPUT_TOTAL_MISSING = "candles_input_total_missing"
FLAG_CANDLES_EVALUATED_MISSING = "candles_evaluated_missing"
FLAG_STALE_MANIFEST_FALLBACK_BLOCKED = "stale_manifest_fallback_blocked"
FLAG_CONTENT_FINGERPRINT_MISSING = "content_fingerprint_missing"
FLAG_DQ_CONTENT_BINDING_MISSING = "dq_content_binding_missing"
FLAG_DQ_CONTENT_FINGERPRINT_MISMATCH = "dq_content_fingerprint_mismatch"
FLAG_REQUEST_FINGERPRINT_ONLY = "request_fingerprint_only_insufficient"


@dataclass(frozen=True, slots=True)
class CandleRankabilityResult:
    candles_total: int | None
    candles_input_total: int | None
    warmup_bars: int | None
    candles_evaluated: int | None
    warmup_provenance: dict[str, Any]
    data_quality_flags: tuple[str, ...]
    rankability_blocking_flags: tuple[str, ...]


def _load_batch_a_manifest(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / BATCH_A_MANIFEST_PATH
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else None


def _manifest_warmup_by_strategy(manifest: Mapping[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        return out
    for row in candidates:
        if not isinstance(row, dict):
            continue
        strategy_id = row.get("strategy_id")
        warmup = row.get("warmup_bars")
        if isinstance(strategy_id, str) and isinstance(warmup, int):
            out[strategy_id] = warmup
    return out


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _coerce_fp(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def resolve_candle_rankability(
    *,
    dataset_summary: Mapping[str, Any],
    strategy_id: str,
    campaign_id: str,
    parameter_fingerprint: str | None,
    campaign_source_sha: str | None,
    repo_root: Path,
) -> CandleRankabilityResult:
    """Resolve candle fields and blocking rankability flags fail-closed."""
    flags: list[str] = []
    blocking: list[str] = []

    candles_input_total = _coerce_int(dataset_summary.get("candles_total"))
    candles_evaluated_observed = _coerce_int(dataset_summary.get("candles_live"))
    warmup_from_run = _coerce_int(dataset_summary.get("warmup_candles"))

    if candles_input_total is None:
        flags.append(FLAG_CANDLES_INPUT_TOTAL_MISSING)
        blocking.append(FLAG_CANDLES_INPUT_TOTAL_MISSING)

    manifest = None
    manifest_warmup: int | None = None
    manifest_verified = False
    batch_a_campaign = campaign_id.startswith(BATCH_A_CAMPAIGN_PREFIX)
    if batch_a_campaign:
        manifest = _load_batch_a_manifest(repo_root)
        if manifest is not None:
            manifest_warmup = _manifest_warmup_by_strategy(manifest).get(strategy_id)

    warmup_bars: int | None = None
    warmup_source: str | None = None

    if warmup_from_run is not None:
        warmup_bars = warmup_from_run
        warmup_source = "dataset_summary.warmup_candles"
        if manifest_warmup is not None and warmup_from_run != manifest_warmup:
            flags.append(FLAG_WARMUP_MANIFEST_MISMATCH)
            blocking.append(FLAG_WARMUP_MANIFEST_MISMATCH)
        elif manifest_warmup is not None:
            manifest_verified = True
    elif batch_a_campaign and manifest_warmup is not None:
        # CDB-052: never silently adopt stale/locked manifest warmup as run truth.
        flags.append(FLAG_STALE_MANIFEST_FALLBACK_BLOCKED)
        blocking.append(FLAG_STALE_MANIFEST_FALLBACK_BLOCKED)
        flags.append(FLAG_WARMUP_PROVENANCE_MISSING)
        blocking.append(FLAG_WARMUP_PROVENANCE_MISSING)

    if warmup_bars is None and (
        candles_input_total is not None
        and candles_evaluated_observed is not None
        and candles_input_total != candles_evaluated_observed
    ):
        if FLAG_WARMUP_PROVENANCE_MISSING not in flags:
            flags.append(FLAG_WARMUP_PROVENANCE_MISSING)
            blocking.append(FLAG_WARMUP_PROVENANCE_MISSING)

    candles_evaluated: int | None = candles_evaluated_observed
    if (
        candles_evaluated is None
        and candles_input_total is not None
        and warmup_bars is not None
    ):
        candles_evaluated = max(0, candles_input_total - warmup_bars)
    elif candles_evaluated is None:
        flags.append(FLAG_CANDLES_EVALUATED_MISSING)
        blocking.append(FLAG_CANDLES_EVALUATED_MISSING)

    expected_evaluated: int | None = None
    if candles_input_total is not None and warmup_bars is not None:
        expected_evaluated = max(0, candles_input_total - warmup_bars)

    if (
        expected_evaluated is not None
        and candles_evaluated is not None
        and candles_evaluated != expected_evaluated
    ):
        flags.append(FLAG_CANDLES_EVALUATED_MISMATCH)
        blocking.append(FLAG_CANDLES_EVALUATED_MISMATCH)
    elif (
        expected_evaluated is not None
        and candles_evaluated is not None
        and candles_evaluated == expected_evaluated
        and candles_input_total is not None
        and candles_input_total != candles_evaluated
        and warmup_bars is not None
        and warmup_bars > 0
    ):
        flags.append(FLAG_WARMUP_TRIM_APPLIED)

    # CDB-050 / CDB-052: content identity required for rankability when DQ is present
    # or when request fingerprint alone is supplied.
    content_fp = _coerce_fp(dataset_summary.get("content_fingerprint"))
    dq_content_fp = _coerce_fp(dataset_summary.get("dq_content_fingerprint"))
    if dq_content_fp is None:
        dq_report = dataset_summary.get("dq_verdict")
        if isinstance(dq_report, Mapping):
            dq_content_fp = _coerce_fp(dq_report.get("content_fingerprint"))
    request_fp = _coerce_fp(dataset_summary.get("request_fingerprint")) or _coerce_fp(
        dataset_summary.get("dataset_fingerprint")
    )

    if content_fp is None:
        flags.append(FLAG_CONTENT_FINGERPRINT_MISSING)
        blocking.append(FLAG_CONTENT_FINGERPRINT_MISSING)
        if request_fp is not None:
            flags.append(FLAG_REQUEST_FINGERPRINT_ONLY)
            blocking.append(FLAG_REQUEST_FINGERPRINT_ONLY)
    elif dq_content_fp is None and dataset_summary.get("dq_verdict") is not None:
        flags.append(FLAG_DQ_CONTENT_BINDING_MISSING)
        blocking.append(FLAG_DQ_CONTENT_BINDING_MISSING)
    elif dq_content_fp is not None and content_fp != dq_content_fp:
        flags.append(FLAG_DQ_CONTENT_FINGERPRINT_MISMATCH)
        blocking.append(FLAG_DQ_CONTENT_FINGERPRINT_MISMATCH)

    warmup_provenance = {
        "warmup_bars": warmup_bars,
        "source": warmup_source,
        "manifest_ref": (
            BATCH_A_MANIFEST_PATH.as_posix() if manifest is not None else None
        ),
        "parameter_fingerprint": parameter_fingerprint,
        "campaign_source_sha": campaign_source_sha,
        "manifest_warmup_verified": manifest_verified,
        "strategy_id": strategy_id,
        "content_fingerprint": content_fp,
        "dq_content_fingerprint": dq_content_fp,
        "request_fingerprint": request_fp,
        "silent_manifest_fallback": False,
    }

    return CandleRankabilityResult(
        candles_total=candles_input_total,
        candles_input_total=candles_input_total,
        warmup_bars=warmup_bars,
        candles_evaluated=candles_evaluated,
        warmup_provenance=warmup_provenance,
        data_quality_flags=tuple(sorted(set(flags))),
        rankability_blocking_flags=tuple(sorted(set(blocking))),
    )


def legacy_resolve_candles_total(
    dataset_summary: Mapping[str, Any],
) -> tuple[int | None, list[str]]:
    """Pre-#4065 behavior retained for impact audit comparison only."""
    flags: list[str] = []
    live = dataset_summary.get("candles_live")
    total = dataset_summary.get("candles_total")
    if live is not None and total is not None and live != total:
        flags.append("candles_live_candles_total_mismatch")
        return int(live), flags
    if live is not None:
        return int(live), flags
    if total is not None:
        return int(total), flags
    flags.append("candles_total_missing")
    return None, flags
