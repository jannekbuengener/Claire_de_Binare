"""Explicit Gap / Duplicate / Out-of-order rules for dataset provenance (CDB-051).

Replay load path is fail-closed. Runtime candle aggregation may accept late ticks
into the current OHLC window; that asymmetry is versioned here and must not be
silently reconciled in fingerprint or DQ binding.

Allowed normalization (content identity sort) is deterministic and always
produces machine-readable evidence — never a silent repair of integrity faults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.replay.dataset_identity import normalize_candle_for_content

INTEGRITY_RULES_SCHEMA_VERSION = "cdb.dataset_integrity_rules.v1"
REPLAY_VS_RUNTIME_CONTRACT_VERSION = "cdb.replay_vs_runtime_data_rules.v1"

REASON_GAP = "GAP"
REASON_DUPLICATE_IDENTICAL = "DUPLICATE_IDENTICAL"
REASON_DUPLICATE_CONFLICTING = "DUPLICATE_CONFLICTING"
REASON_OUT_OF_ORDER = "OUT_OF_ORDER"
REASON_CADENCE_VIOLATION = "CADENCE_VIOLATION"
REASON_EMPTY = "EMPTY_SERIES"
REASON_INCOMPLETE_WINDOW = "INCOMPLETE_WINDOW"

# Deterministic root-cause priority when multiple findings exist (lowest index wins).
ROOT_CAUSE_PRIORITY: tuple[str, ...] = (
    REASON_EMPTY,
    REASON_OUT_OF_ORDER,
    REASON_DUPLICATE_CONFLICTING,
    REASON_DUPLICATE_IDENTICAL,
    REASON_INCOMPLETE_WINDOW,
    REASON_GAP,
    REASON_CADENCE_VIOLATION,
)

_ONE_MINUTE_MS = 60_000

# Versioned Replay vs Runtime contract (documentation + test SSOT).
# Do not mutate services/candles without an explicit runtime GO.
REPLAY_VS_RUNTIME_CONTRACT: dict[str, Any] = {
    "schema_version": REPLAY_VS_RUNTIME_CONTRACT_VERSION,
    "parity_claim": "asymmetric",
    "replay": {
        "gaps": "fail_closed",
        "duplicates": "fail_closed",
        "out_of_order": "fail_closed",
        "cadence": "exact_60000_ms",
        "window_binding": "final_dataset_spec_warmup_to_end",
        "normalization": "content_fingerprint_may_sort_with_evidence_only",
    },
    "runtime_candles": {
        "gaps": "not_synthesized",
        "duplicates": "not_centralized",
        "out_of_order": "late_tick_may_update_current_window_ohlc",
        "cadence": "wall_clock_window_close",
        "note": "Documented asymmetry; not claimed as replay parity.",
    },
}


@dataclass(frozen=True, slots=True)
class IntegrityFinding:
    reason_code: str
    detail: str
    ts_ms: int | None = None


@dataclass(frozen=True, slots=True)
class IntegrityAssessment:
    schema_version: str
    ok_for_replay: bool
    findings: tuple[IntegrityFinding, ...]
    reason_codes: tuple[str, ...]
    primary_reason_code: str | None
    normalization_evidence: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NormalizationEvidence:
    schema_version: str
    normalization_applied: tuple[str, ...]
    reason_codes: tuple[str, ...]
    input_count: int
    output_count: int
    order_changed: bool


class IntegrityError(ValueError):
    """Fail-closed integrity fault with a preserved machine-readable reason code."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        assessment: IntegrityAssessment | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.assessment = assessment


def primary_reason_code(reason_codes: Sequence[str]) -> str | None:
    """Return the highest-priority root cause from ``ROOT_CAUSE_PRIORITY``."""
    if not reason_codes:
        return None
    present = set(reason_codes)
    for code in ROOT_CAUSE_PRIORITY:
        if code in present:
            return code
    # Unknown codes: stable lexicographic fallback.
    return sorted(present)[0]


def _ts(row: Mapping[str, Any]) -> int:
    return int(row["ts_ms"])


def normalize_with_evidence(
    candles: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], NormalizationEvidence]:
    """Normalize content candles and record any sort applied (CDB-051)."""
    projected = [normalize_candle_for_content(c) for c in candles]
    before = [int(row.get("ts_ms", 0)) for row in projected]
    ordered = sorted(projected, key=lambda row: int(row.get("ts_ms", 0)))
    after = [int(row.get("ts_ms", 0)) for row in ordered]
    order_changed = before != after
    applied: list[str] = []
    codes: list[str] = []
    if order_changed:
        applied.append("sort_by_ts_ms")
        codes.append(REASON_OUT_OF_ORDER)
    evidence = NormalizationEvidence(
        schema_version=INTEGRITY_RULES_SCHEMA_VERSION,
        normalization_applied=tuple(applied),
        reason_codes=tuple(codes),
        input_count=len(projected),
        output_count=len(ordered),
        order_changed=order_changed,
    )
    return ordered, evidence


def classify_candle_integrity(
    candles: Sequence[Mapping[str, Any]],
    *,
    start_ts_ms: int | None = None,
    end_ts_ms: int | None = None,
    step_ms: int = _ONE_MINUTE_MS,
) -> IntegrityAssessment:
    """Classify gaps, duplicates, out-of-order, and cadence faults."""
    findings: list[IntegrityFinding] = []
    if not candles:
        findings.append(
            IntegrityFinding(reason_code=REASON_EMPTY, detail="empty candle series")
        )
        codes = (REASON_EMPTY,)
        return IntegrityAssessment(
            schema_version=INTEGRITY_RULES_SCHEMA_VERSION,
            ok_for_replay=False,
            findings=tuple(findings),
            reason_codes=codes,
            primary_reason_code=REASON_EMPTY,
            normalization_evidence={
                "schema_version": INTEGRITY_RULES_SCHEMA_VERSION,
                "normalization_applied": [],
                "reason_codes": [],
                "input_count": 0,
                "output_count": 0,
                "order_changed": False,
            },
        )

    _, norm_evidence = normalize_with_evidence(candles)
    if norm_evidence.order_changed:
        findings.append(
            IntegrityFinding(
                reason_code=REASON_OUT_OF_ORDER,
                detail="candle timestamps are not strictly increasing in input order",
            )
        )

    seen: dict[int, Mapping[str, Any]] = {}
    prev_ts: int | None = None
    for row in candles:
        ts = _ts(row)
        if prev_ts is not None:
            if ts < prev_ts:
                findings.append(
                    IntegrityFinding(
                        reason_code=REASON_OUT_OF_ORDER,
                        detail=f"ts_ms={ts} precedes previous ts_ms={prev_ts}",
                        ts_ms=ts,
                    )
                )
            elif ts == prev_ts:
                prior = seen[ts]
                # Compare semantic OHLCV projection for identical vs conflicting.
                a = normalize_candle_for_content(prior)
                b = normalize_candle_for_content(row)
                if a == b:
                    findings.append(
                        IntegrityFinding(
                            reason_code=REASON_DUPLICATE_IDENTICAL,
                            detail=f"identical duplicate at ts_ms={ts}",
                            ts_ms=ts,
                        )
                    )
                else:
                    findings.append(
                        IntegrityFinding(
                            reason_code=REASON_DUPLICATE_CONFLICTING,
                            detail=f"conflicting duplicate at ts_ms={ts}",
                            ts_ms=ts,
                        )
                    )
            elif ts - prev_ts != step_ms:
                findings.append(
                    IntegrityFinding(
                        reason_code=REASON_CADENCE_VIOLATION,
                        detail=(
                            f"cadence {ts - prev_ts}ms between "
                            f"{prev_ts} and {ts}; expected {step_ms}ms"
                        ),
                        ts_ms=ts,
                    )
                )
        seen[ts] = row
        prev_ts = ts

    if start_ts_ms is not None and end_ts_ms is not None and step_ms > 0:
        expected = set(range(int(start_ts_ms), int(end_ts_ms) + 1, int(step_ms)))
        actual = {_ts(row) for row in candles}
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            findings.append(
                IntegrityFinding(
                    reason_code=REASON_GAP,
                    detail=(
                        f"{len(missing)} missing interval(s); "
                        f"first_missing={missing[0]}"
                    ),
                    ts_ms=missing[0],
                )
            )
        if extra:
            findings.append(
                IntegrityFinding(
                    reason_code=REASON_INCOMPLETE_WINDOW,
                    detail=(
                        f"{len(extra)} candle(s) outside bound window "
                        f"[{start_ts_ms}, {end_ts_ms}]; first_extra={extra[0]}"
                    ),
                    ts_ms=extra[0],
                )
            )
        # Warmup/live incomplete: series ends before declared end or starts late.
        if candles:
            first = _ts(candles[0])
            last = _ts(candles[-1])
            if first > int(start_ts_ms) or last < int(end_ts_ms):
                findings.append(
                    IntegrityFinding(
                        reason_code=REASON_INCOMPLETE_WINDOW,
                        detail=(
                            f"series bounds [{first}, {last}] do not cover "
                            f"declared window [{start_ts_ms}, {end_ts_ms}]"
                        ),
                        ts_ms=first if first > int(start_ts_ms) else last,
                    )
                )

    codes = tuple(sorted({f.reason_code for f in findings}))
    primary = primary_reason_code(codes)
    ok = len(findings) == 0
    return IntegrityAssessment(
        schema_version=INTEGRITY_RULES_SCHEMA_VERSION,
        ok_for_replay=ok,
        findings=tuple(findings),
        reason_codes=codes,
        primary_reason_code=primary,
        normalization_evidence={
            "schema_version": norm_evidence.schema_version,
            "normalization_applied": list(norm_evidence.normalization_applied),
            "reason_codes": list(norm_evidence.reason_codes),
            "input_count": norm_evidence.input_count,
            "output_count": norm_evidence.output_count,
            "order_changed": norm_evidence.order_changed,
        },
    )


def assert_replay_integrity(
    candles: Sequence[Mapping[str, Any]],
    *,
    start_ts_ms: int | None = None,
    end_ts_ms: int | None = None,
    step_ms: int = _ONE_MINUTE_MS,
) -> IntegrityAssessment:
    """Fail-closed gate for replay datasets (CDB-051).

    Raises ``IntegrityError`` with ``.code`` set to the primary root cause.
    """
    assessment = classify_candle_integrity(
        candles,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        step_ms=step_ms,
    )
    if not assessment.ok_for_replay:
        code = assessment.primary_reason_code or "UNKNOWN"
        codes = ",".join(assessment.reason_codes) or code
        raise IntegrityError(
            f"replay integrity blocked ({INTEGRITY_RULES_SCHEMA_VERSION}): {codes}",
            code=code,
            assessment=assessment,
        )
    return assessment
