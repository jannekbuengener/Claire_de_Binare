"""Candle field normalization and rankability provenance (#4065 / #4336 CDB-052).

Preserves legacy producer semantics for ``candles_total`` while emitting explicit
``candles_input_total``, ``warmup_bars``, and ``candles_evaluated`` for rankability.

Warmup must be historically provable from the run's dataset summary. Batch-A
manifest values may only *verify* run warmup — never silently fill missing
warmup provenance (CDB-052 fail-closed / no stale-manifest fallback).

Scorers must call ``enforce_rankability_provenance`` (or ``record_is_rankable``)
before treating a record as rankable — never invent missing provenance.
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
FLAG_MANIFEST_MISSING = "manifest_missing"
FLAG_RANKABILITY_PROVENANCE_MISSING = "rankability_provenance_missing"
FLAG_RANKABILITY_PROVENANCE_MISMATCH = "rankability_provenance_mismatch"
FLAG_STALE_RANKABILITY_VERDICT = "stale_rankability_verdict"
FLAG_WINDOW_MISMATCH = "window_mismatch"
FLAG_REQUEST_FINGERPRINT_MISMATCH = "request_fingerprint_mismatch"
FLAG_WARMUP_MISMATCH = "warmup_mismatch"


class RankabilityProvenanceError(ValueError):
    """Fail-closed CDB-052 rankability provenance violation."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


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


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_dq_content_fp(dataset_summary: Mapping[str, Any]) -> str | None:
    dq_content_fp = _coerce_fp(dataset_summary.get("dq_content_fingerprint"))
    if dq_content_fp is not None:
        return dq_content_fp
    dq_report = dataset_summary.get("dq_verdict")
    if isinstance(dq_report, Mapping):
        return _coerce_fp(dq_report.get("content_fingerprint"))
    return None


def _current_provenance_from_summary(
    dataset_summary: Mapping[str, Any],
    *,
    strategy_id: str,
    parameter_fingerprint: str | None,
    campaign_source_sha: str | None,
    warmup_bars: int | None,
    warmup_source: str | None,
    manifest_ref: str | None,
    manifest_warmup_verified: bool,
) -> dict[str, Any]:
    content_fp = _coerce_fp(dataset_summary.get("content_fingerprint"))
    dq_content_fp = _extract_dq_content_fp(dataset_summary)
    request_fp = _coerce_fp(dataset_summary.get("request_fingerprint")) or _coerce_fp(
        dataset_summary.get("dataset_fingerprint")
    )
    return {
        "warmup_bars": warmup_bars,
        "source": warmup_source,
        "manifest_ref": manifest_ref,
        "parameter_fingerprint": parameter_fingerprint,
        "campaign_source_sha": campaign_source_sha,
        "manifest_warmup_verified": manifest_warmup_verified,
        "strategy_id": strategy_id,
        "content_fingerprint": content_fp,
        "dq_content_fingerprint": dq_content_fp,
        "request_fingerprint": request_fp,
        "silent_manifest_fallback": False,
        "window_id": _coerce_str(dataset_summary.get("window_id")),
        "start_ts_ms": _coerce_int(dataset_summary.get("start_ts_ms")),
        "end_ts_ms": _coerce_int(dataset_summary.get("end_ts_ms")),
    }


def assert_rankability_provenance(
    current: Mapping[str, Any],
    evidence: Mapping[str, Any] | None,
) -> None:
    """Fail-closed: bound rankability evidence must match the current provenance.

    ``current`` is the live identity (dataset summary / expected fingerprints).
    ``evidence`` is stored rankability / warmup provenance — never invent it.
    """
    if evidence is None or not isinstance(evidence, Mapping) or not evidence:
        raise RankabilityProvenanceError(
            "Rankability provenance evidence missing; not applicable",
            code=FLAG_RANKABILITY_PROVENANCE_MISSING,
        )
    if evidence.get("silent_manifest_fallback") is True:
        raise RankabilityProvenanceError(
            "Silent manifest fallback is blocked for rankability",
            code=FLAG_STALE_MANIFEST_FALLBACK_BLOCKED,
        )
    if evidence.get("silent_manifest_fallback") is not False:
        raise RankabilityProvenanceError(
            "Rankability evidence must explicitly deny silent manifest fallback",
            code=FLAG_RANKABILITY_PROVENANCE_MISSING,
        )

    current_content = _coerce_fp(current.get("content_fingerprint"))
    evidence_content = _coerce_fp(evidence.get("content_fingerprint"))
    if current_content is None:
        raise RankabilityProvenanceError(
            "Current content_fingerprint missing for rankability binding",
            code=FLAG_CONTENT_FINGERPRINT_MISSING,
        )
    if evidence_content is None:
        raise RankabilityProvenanceError(
            "Rankability evidence missing content_fingerprint",
            code=FLAG_RANKABILITY_PROVENANCE_MISSING,
        )
    if current_content != evidence_content:
        raise RankabilityProvenanceError(
            "Rankability content_fingerprint is stale or mismatched",
            code=FLAG_STALE_RANKABILITY_VERDICT,
        )

    current_warmup = _coerce_int(current.get("warmup_bars"))
    if current_warmup is None:
        current_warmup = _coerce_int(current.get("warmup_candles"))
    evidence_warmup = _coerce_int(evidence.get("warmup_bars"))
    if current_warmup is None or evidence_warmup is None:
        raise RankabilityProvenanceError(
            "Warmup provenance missing for rankability binding",
            code=FLAG_WARMUP_PROVENANCE_MISSING,
        )
    if current_warmup != evidence_warmup:
        raise RankabilityProvenanceError(
            "Rankability warmup_bars is stale or mismatched",
            code=FLAG_WARMUP_MISMATCH,
        )

    current_request = _coerce_fp(current.get("request_fingerprint")) or _coerce_fp(
        current.get("dataset_fingerprint")
    )
    evidence_request = _coerce_fp(evidence.get("request_fingerprint"))
    if current_request is not None and evidence_request is not None:
        if current_request != evidence_request:
            raise RankabilityProvenanceError(
                "Rankability request_fingerprint is stale or mismatched",
                code=FLAG_REQUEST_FINGERPRINT_MISMATCH,
            )

    current_window = _coerce_str(current.get("window_id"))
    evidence_window = _coerce_str(evidence.get("window_id"))
    if current_window is not None and evidence_window is not None:
        if current_window != evidence_window:
            raise RankabilityProvenanceError(
                "Rankability window_id is stale or mismatched",
                code=FLAG_WINDOW_MISMATCH,
            )

    for bound_key, flag in (
        ("start_ts_ms", FLAG_WINDOW_MISMATCH),
        ("end_ts_ms", FLAG_WINDOW_MISMATCH),
    ):
        current_bound = _coerce_int(current.get(bound_key))
        evidence_bound = _coerce_int(evidence.get(bound_key))
        if current_bound is not None and evidence_bound is not None:
            if current_bound != evidence_bound:
                raise RankabilityProvenanceError(
                    f"Rankability {bound_key} is stale or mismatched",
                    code=flag,
                )

    current_param = _coerce_str(current.get("parameter_fingerprint"))
    evidence_param = _coerce_str(evidence.get("parameter_fingerprint"))
    if current_param is not None and evidence_param is not None:
        if current_param != evidence_param:
            raise RankabilityProvenanceError(
                "Rankability parameter_fingerprint is stale or mismatched",
                code=FLAG_RANKABILITY_PROVENANCE_MISMATCH,
            )

    current_sha = _coerce_str(current.get("campaign_source_sha"))
    evidence_sha = _coerce_str(evidence.get("campaign_source_sha"))
    if current_sha is not None and evidence_sha is not None:
        if current_sha != evidence_sha:
            raise RankabilityProvenanceError(
                "Rankability campaign_source_sha is stale or mismatched",
                code=FLAG_RANKABILITY_PROVENANCE_MISMATCH,
            )

    current_dq = _coerce_fp(current.get("dq_content_fingerprint"))
    if current_dq is None and current.get("dq_verdict") is not None:
        if isinstance(current.get("dq_verdict"), Mapping):
            current_dq = _coerce_fp(
                current["dq_verdict"].get("content_fingerprint")  # type: ignore[index]
            )
    evidence_dq = _coerce_fp(evidence.get("dq_content_fingerprint"))
    if current.get("dq_verdict") is not None or evidence_dq is not None:
        if current_dq is None or evidence_dq is None:
            raise RankabilityProvenanceError(
                "DQ content binding missing for rankability",
                code=FLAG_DQ_CONTENT_BINDING_MISSING,
            )
        if current_dq != evidence_dq or current_dq != current_content:
            raise RankabilityProvenanceError(
                "DQ content fingerprint disagrees with rankability content",
                code=FLAG_DQ_CONTENT_FINGERPRINT_MISMATCH,
            )


def enforce_rankability_provenance(
    *,
    current: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
    record: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Single fail-closed CDB-052 enforcement point for rankability consumers.

    Prefer passing an extracted ``record`` (with ``warmup_provenance``) plus an
    independent ``current`` identity. When only ``record`` is supplied, the
    record's own provenance is checked for structural completeness and must
    already deny silent fallback — scorers must not invent missing fields.
    """
    if record is not None:
        evidence = evidence if evidence is not None else record.get("warmup_provenance")
        if current is None:
            # Structural gate for already-bound records: require explicit fields.
            current = {
                "content_fingerprint": (
                    (evidence or {}).get("content_fingerprint")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "warmup_bars": (
                    (evidence or {}).get("warmup_bars")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "request_fingerprint": (
                    (evidence or {}).get("request_fingerprint")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "window_id": (
                    (evidence or {}).get("window_id")
                    if isinstance(evidence, Mapping)
                    else record.get("window_id")
                ),
                "start_ts_ms": (
                    (evidence or {}).get("start_ts_ms")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "end_ts_ms": (
                    (evidence or {}).get("end_ts_ms")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "parameter_fingerprint": (
                    (evidence or {}).get("parameter_fingerprint")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "campaign_source_sha": (
                    (evidence or {}).get("campaign_source_sha")
                    if isinstance(evidence, Mapping)
                    else None
                ),
                "dq_content_fingerprint": (
                    (evidence or {}).get("dq_content_fingerprint")
                    if isinstance(evidence, Mapping)
                    else None
                ),
            }
            # When only a record is supplied, also reject historical rankable=true
            # without blocking-flag emptiness / provenance object.
            if not isinstance(evidence, Mapping) or not evidence:
                raise RankabilityProvenanceError(
                    "Scorer received unbound rankability input",
                    code=FLAG_RANKABILITY_PROVENANCE_MISSING,
                )
            blocking = record.get("rankability_blocking_flags")
            if blocking is None:
                reasons = record.get("not_rankable_reasons")
                if isinstance(reasons, list) and reasons:
                    raise RankabilityProvenanceError(
                        "Scorer received non-rankable record with reasons",
                        code=FLAG_RANKABILITY_PROVENANCE_MISMATCH,
                    )
            elif isinstance(blocking, (list, tuple)) and blocking:
                raise RankabilityProvenanceError(
                    "Scorer received record with rankability blocking flags",
                    code=FLAG_RANKABILITY_PROVENANCE_MISMATCH,
                )

    if current is None:
        raise RankabilityProvenanceError(
            "Rankability enforcement requires current provenance",
            code=FLAG_RANKABILITY_PROVENANCE_MISSING,
        )
    assert_rankability_provenance(current, evidence)
    assert isinstance(evidence, Mapping)
    return evidence


def record_has_bound_rankability_provenance(record: Mapping[str, Any]) -> bool:
    """Return True only when record carries enforceable warmup/content provenance."""
    try:
        enforce_rankability_provenance(record=record)
    except RankabilityProvenanceError:
        return False
    return True


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
        if manifest is None:
            # CDB-052: Batch-A campaigns require the locked funnel manifest.
            flags.append(FLAG_MANIFEST_MISSING)
            blocking.append(FLAG_MANIFEST_MISSING)
        else:
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
    dq_content_fp = _extract_dq_content_fp(dataset_summary)
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

    warmup_provenance = _current_provenance_from_summary(
        dataset_summary,
        strategy_id=strategy_id,
        parameter_fingerprint=parameter_fingerprint,
        campaign_source_sha=campaign_source_sha,
        warmup_bars=warmup_bars,
        warmup_source=warmup_source,
        manifest_ref=(
            BATCH_A_MANIFEST_PATH.as_posix() if manifest is not None else None
        ),
        manifest_warmup_verified=manifest_verified,
    )

    # Self-bind: when producer identity is complete and no blocking flags, enforce
    # that emitted provenance matches the current dataset summary (no silent drift).
    if not blocking and content_fp is not None and warmup_bars is not None:
        try:
            assert_rankability_provenance(
                {
                    "content_fingerprint": content_fp,
                    "warmup_bars": warmup_bars,
                    "request_fingerprint": request_fp,
                    "window_id": warmup_provenance.get("window_id"),
                    "start_ts_ms": warmup_provenance.get("start_ts_ms"),
                    "end_ts_ms": warmup_provenance.get("end_ts_ms"),
                    "parameter_fingerprint": parameter_fingerprint,
                    "campaign_source_sha": campaign_source_sha,
                    "dq_content_fingerprint": dq_content_fp,
                    "dq_verdict": dataset_summary.get("dq_verdict"),
                },
                warmup_provenance,
            )
        except RankabilityProvenanceError as exc:
            flags.append(exc.code)
            blocking.append(exc.code)

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
