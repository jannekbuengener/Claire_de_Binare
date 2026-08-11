"""ARVP window bank builder for Binance historical import (#3990).

Cross-venue research windows only — not MEXC same-venue evidence.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.utils.clock import utcnow
from tools.market_data.binance_full_archive_import import (
    REPO_ROOT as IMPORT_REPO,
    _enriched_dir,
    _normalized_dir,
)
from tools.market_data.historical_common import (
    ONE_MINUTE_MS,
    HistoricalProbeError,
    content_fingerprint_for_candle_rows,
    dq_report_from_dataset_spec,
    enforce_dq_content_binding,
    month_bounds,
    parse_year_month,
    sha256_file,
    utc_now_iso,
    write_json,
)
from tools.market_data.market_data_storage_guard import resolve_market_data_path
from tools.market_data.assign_regime_offline import regime_distribution

WINDOW_BANK_SCHEMA = "binance_window_bank.v1"
EXCLUDED_VERDICTS = frozenset(
    {"SOURCE_INVALID", "SOURCE_UNAVAILABLE", "CHECKSUM_FAILED"}
)
OVERLAP_CLASSES = frozenset(
    {"monthly", "quarterly", "yearly", "stress", "smoke", "pilot"}
)
PURPOSES = frozenset({"development", "validation", "out_of_sample", "stress"})


def _market_data_root(repo_root: Path) -> Path:
    """Resolve the window-bank corpus root, including explicit bulk opt-in."""
    return resolve_market_data_path(repo_root)


@dataclass(frozen=True, slots=True)
class WindowSpec:
    window_id: str
    start_ts_ms: int
    end_ts_ms: int
    candle_count: int
    dataset_fingerprint: str
    regime_distribution: dict[str, Any]
    source_months: tuple[str, ...]
    overlap_class: str
    evidence_class: str
    purpose: str
    quality_verdict: str
    candles_path: str
    spec_path: str


def load_import_manifest(repo_root: Path = IMPORT_REPO) -> dict[str, Any]:
    path = (
        _market_data_root(repo_root)
        / "manifests"
        / "binance_btcusdt_1m_full_import.json"
    )
    if not path.exists():
        raise HistoricalProbeError(f"Import manifest missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def strict_complete_months(manifest: dict[str, Any]) -> list[str]:
    months: list[str] = []
    for entry in manifest.get("months") or []:
        if entry.get("quality_verdict") == "STRICT_COMPLETE":
            months.append(str(entry["month"]))
    return sorted(months)


def resolve_build_months(repo_root: Path = IMPORT_REPO) -> list[str]:
    """Months usable for window-bank builds (STRICT_COMPLETE; disk fallback if manifest partial)."""
    manifest = load_import_manifest(repo_root)
    by_month = {str(entry["month"]): entry for entry in manifest.get("months") or []}
    enriched_base = (
        _market_data_root(repo_root)
        / "enriched"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
    )
    months: list[str] = []
    if enriched_base.is_dir():
        for month_dir in sorted(enriched_base.iterdir()):
            if not month_dir.is_dir():
                continue
            month = month_dir.name
            if not (month_dir / "candles.jsonl").exists():
                continue
            entry = by_month.get(month)
            if entry is not None:
                verdict = str(entry.get("quality_verdict", ""))
                if verdict in EXCLUDED_VERDICTS or verdict == "PARTIAL_USABLE":
                    continue
                if verdict == "STRICT_COMPLETE":
                    months.append(month)
            else:
                months.append(month)
    if months:
        return months
    return strict_complete_months(manifest)


def _load_month_candles(
    repo_root: Path, month: str, *, enriched: bool = True
) -> list[dict[str, Any]]:
    base = (
        _enriched_dir(repo_root, month)
        if enriched
        else _normalized_dir(repo_root, month)
    )
    path = base / "candles.jsonl"
    if not path.exists():
        raise HistoricalProbeError(f"Missing candles: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _slice_candles(
    candles: Sequence[dict[str, Any]],
    start_ts_ms: int,
    end_ts_ms: int,
) -> list[dict[str, Any]]:
    return [c for c in candles if start_ts_ms <= int(c["ts_ms"]) <= end_ts_ms]


def _is_contiguous_cadence(
    candles: Sequence[dict[str, Any]],
    *,
    gap_ms: int = ONE_MINUTE_MS,
) -> bool:
    if len(candles) < 2:
        return bool(candles)
    for prev, cur in zip(candles, candles[1:]):
        if int(cur["ts_ms"]) - int(prev["ts_ms"]) != gap_ms:
            return False
    return True


def _enforce_contiguous_cadence(
    candles: Sequence[dict[str, Any]],
    *,
    gap_ms: int = ONE_MINUTE_MS,
) -> list[dict[str, Any]]:
    """Return longest prefix with strict 1m cadence (stops at first gap)."""
    if not candles:
        return []
    out = [candles[0]]
    for candle in candles[1:]:
        if int(candle["ts_ms"]) - int(out[-1]["ts_ms"]) != gap_ms:
            break
        out.append(candle)
    return out


def _contiguous_islands(
    candles: Sequence[dict[str, Any]],
    *,
    gap_ms: int = ONE_MINUTE_MS,
) -> list[list[dict[str, Any]]]:
    """Split a candle timeline into maximal contiguous 1m islands."""
    if not candles:
        return []
    islands: list[list[dict[str, Any]]] = []
    current = [candles[0]]
    for candle in candles[1:]:
        if int(candle["ts_ms"]) - int(current[-1]["ts_ms"]) != gap_ms:
            islands.append(current)
            current = [candle]
        else:
            current.append(candle)
    islands.append(current)
    return islands


def _cadence_gaps(
    candles: Sequence[dict[str, Any]],
    *,
    gap_ms: int = ONE_MINUTE_MS,
) -> list[dict[str, Any]]:
    """Return cadence violations as index/prev_ts/cur_ts/delta_ms records."""
    gaps: list[dict[str, Any]] = []
    for idx in range(1, len(candles)):
        prev_ts = int(candles[idx - 1]["ts_ms"])
        cur_ts = int(candles[idx]["ts_ms"])
        delta = cur_ts - prev_ts
        if delta != gap_ms:
            gaps.append(
                {
                    "index": idx,
                    "prev_ts_ms": prev_ts,
                    "cur_ts_ms": cur_ts,
                    "delta_ms": delta,
                }
            )
    return gaps


def _validate_stress_window_candles(
    candles: Sequence[dict[str, Any]],
    *,
    window_minutes: int,
    gap_ms: int = ONE_MINUTE_MS,
) -> None:
    """Fail-closed validation before stress replay."""
    if len(candles) != window_minutes:
        raise HistoricalProbeError(
            f"stress window candle_count={len(candles)} expected={window_minutes}"
        )
    seen_ts: set[int] = set()
    for idx, candle in enumerate(candles):
        ts = int(candle["ts_ms"])
        if ts in seen_ts:
            raise HistoricalProbeError(f"duplicate ts_ms at index {idx}: {ts}")
        seen_ts.add(ts)
        if idx > 0:
            prev_ts = int(candles[idx - 1]["ts_ms"])
            if ts - prev_ts != gap_ms:
                raise HistoricalProbeError(
                    f"cadence gap at index {idx}: delta={ts - prev_ts}ms"
                )
        regime = candle.get("regime_id")
        if regime is None:
            regime = candle.get("regime")
        if regime is None or str(regime).strip() == "":
            raise HistoricalProbeError(f"missing regime at index {idx}")


def _load_strict_timeline(
    months: Sequence[str],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """Load STRICT_COMPLETE months in order as one timeline + month lookup."""
    all_candles: list[dict[str, Any]] = []
    month_by_ts: dict[int, str] = {}
    for month in sorted(months):
        for row in _load_month_candles(repo_root, month):
            ts = int(row["ts_ms"])
            all_candles.append(row)
            month_by_ts[ts] = month
    return all_candles, month_by_ts


def _month_candle_bounds(
    repo_root: Path,
    month: str,
) -> tuple[int, int, int, bool] | None:
    """Return first_ts, last_ts, count, contiguous for a month without full parse."""
    candles = _load_month_candles(repo_root, month)
    if not candles:
        return None
    contiguous = _is_contiguous_cadence(candles)
    return int(candles[0]["ts_ms"]), int(candles[-1]["ts_ms"]), len(candles), contiguous


def _cross_month_segments(
    months: Sequence[str], repo_root: Path
) -> list[tuple[str, ...]]:
    """Group consecutive months whose boundary timestamps are contiguous."""
    ordered = sorted(months)
    if not ordered:
        return []
    segments: list[list[str]] = [[ordered[0]]]
    prev_bounds = _month_candle_bounds(repo_root, ordered[0])
    for month in ordered[1:]:
        bounds = _month_candle_bounds(repo_root, month)
        if (
            prev_bounds is not None
            and bounds is not None
            and prev_bounds[3]
            and bounds[3]
            and bounds[0] - prev_bounds[1] == ONE_MINUTE_MS
        ):
            segments[-1].append(month)
        else:
            segments.append([month])
        prev_bounds = bounds
    return [tuple(segment) for segment in segments if segment]


def _load_segment_candles(
    repo_root: Path,
    segment_months: Sequence[str],
) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for month in segment_months:
        candles.extend(_load_month_candles(repo_root, month))
    return candles


def _update_metric_best(
    best: dict[str, tuple[float, int, list[dict[str, Any]], tuple[str, ...]]],
    *,
    metric_key: str,
    reverse: bool,
    islands: Sequence[Sequence[dict[str, Any]]],
    window_minutes: int,
    step: int,
    segment_months: tuple[str, ...],
) -> None:
    metric_field = {
        "max_drawdown": "max_dd",
        "max_vol": "vol",
        "min_vol": "vol",
        "max_uptrend": "trend",
        "max_downtrend": "trend",
    }[metric_key]
    for island in islands:
        for _metric, _island_idx, _start_idx, chunk in _rank_stress_candidates(
            [island],
            metric_key=metric_key,
            window_minutes=window_minutes,
            step=step,
            reverse=reverse,
        ):
            try:
                _validate_stress_window_candles(chunk, window_minutes=window_minutes)
            except HistoricalProbeError:
                continue
            value = _window_metrics(chunk)[metric_field]
            current = best.get(metric_key)
            if current is None:
                best[metric_key] = (
                    value,
                    int(chunk[0]["ts_ms"]),
                    chunk,
                    segment_months,
                )
                continue
            cur_val, cur_start, _, _ = current
            better = value > cur_val if reverse else value < cur_val
            if better or (value == cur_val and int(chunk[0]["ts_ms"]) < cur_start):
                best[metric_key] = (
                    value,
                    int(chunk[0]["ts_ms"]),
                    chunk,
                    segment_months,
                )


def _window_metrics(chunk: Sequence[dict[str, Any]]) -> dict[str, float]:
    closes = [float(c["close"]) for c in chunk]
    rets = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    vol = (sum(r * r for r in rets) / len(rets)) ** 0.5 if rets else 0.0
    peak = closes[0]
    max_dd = 0.0
    for price in closes:
        peak = max(peak, price)
        dd = (peak - price) / peak if peak else 0.0
        max_dd = max(max_dd, dd)
    trend = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0
    return {"vol": vol, "max_dd": max_dd, "trend": trend}


def _rank_stress_candidates(
    islands: Sequence[Sequence[dict[str, Any]]],
    *,
    metric_key: str,
    window_minutes: int,
    step: int,
    reverse: bool = True,
) -> list[tuple[float, int, int, list[dict[str, Any]]]]:
    """Return ranked (metric, island_idx, start_idx, chunk) tuples."""
    metric_field = {
        "max_drawdown": "max_dd",
        "max_vol": "vol",
        "min_vol": "vol",
        "max_uptrend": "trend",
        "max_downtrend": "trend",
    }[metric_key]
    candidates: list[tuple[float, int, int, list[dict[str, Any]]]] = []
    for island_idx, island in enumerate(islands):
        if len(island) < window_minutes:
            continue
        for start_idx in range(0, len(island) - window_minutes + 1, step):
            chunk = list(island[start_idx : start_idx + window_minutes])
            if not _is_contiguous_cadence(chunk):
                continue
            metric = _window_metrics(chunk)[metric_field]
            candidates.append((metric, island_idx, start_idx, chunk))
    if metric_key == "min_vol":
        candidates.sort(key=lambda item: (item[0], int(item[3][0]["ts_ms"])))
    elif metric_key == "max_downtrend":
        candidates.sort(key=lambda item: (item[0], int(item[3][0]["ts_ms"])))
    else:
        candidates.sort(key=lambda item: (-item[0], int(item[3][0]["ts_ms"])))
    if not reverse and metric_key in {"min_vol", "max_downtrend"}:
        return candidates
    if reverse and metric_key in {"min_vol", "max_downtrend"}:
        return list(reversed(candidates))
    return candidates


def _select_stress_chunk(
    candidates: Sequence[tuple[float, int, int, list[dict[str, Any]]]],
    *,
    window_minutes: int,
    reject_start_ts_ms: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    """Pick first valid candidate, optionally skipping a rejected start timestamp."""
    for metric, island_idx, start_idx, chunk in candidates:
        start_ts = int(chunk[0]["ts_ms"])
        if reject_start_ts_ms is not None and start_ts == reject_start_ts_ms:
            continue
        try:
            _validate_stress_window_candles(chunk, window_minutes=window_minutes)
        except HistoricalProbeError:
            continue
        return chunk, {
            "metric_value": metric,
            "island_index": island_idx,
            "start_index": start_idx,
            "start_ts_ms": start_ts,
            "end_ts_ms": int(chunk[-1]["ts_ms"]),
        }
    return None


STRESS_METRIC_DEFS: tuple[tuple[str, str, bool], ...] = (
    ("stress_max_drawdown", "max_drawdown", True),
    ("stress_max_volatility", "max_vol", True),
    ("stress_min_volatility", "min_vol", False),
    ("stress_max_uptrend", "max_uptrend", True),
    ("stress_max_downtrend", "max_downtrend", False),
)


def _write_window_dataset(
    repo_root: Path,
    window: WindowSpec,
    candles: list[dict[str, Any]],
) -> Path:
    window_dir = (
        _market_data_root(repo_root)
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / window.window_id
    )
    window_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = window_dir / "candles.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in candles:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    fingerprint = sha256_file(jsonl_path)
    # CDB-050: content identity of the written series (independent of file SHA).
    content_fp = content_fingerprint_for_candle_rows(candles)
    spec = {
        "schema_version": "dataset_spec.v2",
        "dataset_id": window.window_id,
        "window_id": window.window_id,
        "symbol": "BTCUSDT",
        "venue": "binance",
        "venue_match": False,
        "target_validation_venue": "mexc",
        "source": "file",
        "source_label": "binance_public_data",
        "source_type": "binance_public_data",
        "file_path": str(jsonl_path).replace("\\", "/"),
        "start_ts_ms": window.start_ts_ms,
        "end_ts_ms": window.end_ts_ms,
        "timeframe": "1m",
        "fingerprint": fingerprint,
        "candles_sha256": fingerprint,
        "content_fingerprint": content_fp,
        "data_quality_verdict": window.quality_verdict,
        "regime_enriched": True,
        "overlap_class": window.overlap_class,
        "purpose": window.purpose,
        "source_months": list(window.source_months),
        "regime_distribution": window.regime_distribution,
        "evidence_class": "controlled_lab_evidence",
        "evidence_subclass": "historical_cross_venue_research",
        "not_evidence_class": [
            "mexc_same_venue",
            "natural_paper_evidence",
            "live_evidence",
            "promotion_ready",
        ],
        "ranking_ready": False,
        "lr_status": "NO-GO",
        "issue": "#3990",
    }
    # Bind the stamped DQ verdict to the written content before accepting the
    # window as STRICT/usable for downstream consumers.
    dq_report = dq_report_from_dataset_spec(spec)
    if dq_report is not None:
        enforce_dq_content_binding(report=dq_report, candles=candles)
    spec_path = window_dir / "dataset_spec.json"
    write_json(spec_path, spec)
    return spec_path


def build_monthly_windows(
    months: Sequence[str],
    repo_root: Path = IMPORT_REPO,
) -> list[WindowSpec]:
    windows: list[WindowSpec] = []
    for month in months:
        candles = _load_month_candles(repo_root, month)
        if not candles:
            continue
        start_ts_ms = int(candles[0]["ts_ms"])
        end_ts_ms = int(candles[-1]["ts_ms"])
        purpose = _purpose_for_month(month, months)
        wid = f"binance_1m_month_{month.replace('-', '_')}"
        windows.append(
            WindowSpec(
                window_id=wid,
                start_ts_ms=start_ts_ms,
                end_ts_ms=end_ts_ms,
                candle_count=len(candles),
                dataset_fingerprint="",
                regime_distribution=regime_distribution(candles),
                source_months=(month,),
                overlap_class="monthly",
                evidence_class="controlled_lab_evidence",
                purpose=purpose,
                quality_verdict="STRICT_COMPLETE",
                candles_path="",
                spec_path="",
            )
        )
    return windows


def build_quarterly_windows(
    months: Sequence[str],
    repo_root: Path = IMPORT_REPO,
) -> list[WindowSpec]:
    quarters: dict[str, list[str]] = {}
    for month in months:
        year, month_num = parse_year_month(month)
        q = (month_num - 1) // 3 + 1
        key = f"{year}-Q{q}"
        quarters.setdefault(key, []).append(month)
    windows: list[WindowSpec] = []
    for qkey, qmonths in sorted(quarters.items()):
        if len(qmonths) != 3:
            continue
        all_candles: list[dict[str, Any]] = []
        for m in sorted(qmonths):
            all_candles.extend(_load_month_candles(repo_root, m))
        if not all_candles:
            continue
        purpose = _purpose_for_month(qmonths[0], months)
        wid = f"binance_1m_quarter_{qkey.replace('-', '_')}"
        windows.append(
            WindowSpec(
                window_id=wid,
                start_ts_ms=int(all_candles[0]["ts_ms"]),
                end_ts_ms=int(all_candles[-1]["ts_ms"]),
                candle_count=len(all_candles),
                dataset_fingerprint="",
                regime_distribution=regime_distribution(all_candles),
                source_months=tuple(sorted(qmonths)),
                overlap_class="quarterly",
                evidence_class="controlled_lab_evidence",
                purpose=purpose,
                quality_verdict="STRICT_COMPLETE",
                candles_path="",
                spec_path="",
            )
        )
    return windows


def build_yearly_windows(
    months: Sequence[str],
    repo_root: Path = IMPORT_REPO,
) -> list[WindowSpec]:
    years: dict[str, list[str]] = {}
    for month in months:
        year = month.split("-")[0]
        years.setdefault(year, []).append(month)
    windows: list[WindowSpec] = []
    for year, ymonths in sorted(years.items()):
        if len(ymonths) != 12:
            continue
        all_candles: list[dict[str, Any]] = []
        for m in sorted(ymonths):
            all_candles.extend(_load_month_candles(repo_root, m))
        purpose = _purpose_for_month(ymonths[0], months)
        wid = f"binance_1m_year_{year}"
        windows.append(
            WindowSpec(
                window_id=wid,
                start_ts_ms=int(all_candles[0]["ts_ms"]),
                end_ts_ms=int(all_candles[-1]["ts_ms"]),
                candle_count=len(all_candles),
                dataset_fingerprint="",
                regime_distribution=regime_distribution(all_candles),
                source_months=tuple(sorted(ymonths)),
                overlap_class="yearly",
                evidence_class="controlled_lab_evidence",
                purpose=purpose,
                quality_verdict="STRICT_COMPLETE",
                candles_path="",
                spec_path="",
            )
        )
    return windows


def _purpose_for_month(month: str, all_months: Sequence[str]) -> str:
    split = compute_temporal_split(all_months)
    if month in split["out_of_sample"]:
        return "out_of_sample"
    if month in split["validation"]:
        return "validation"
    return "development"


def compute_temporal_split(
    months: Sequence[str],
    *,
    oos_fraction: float = 0.20,
) -> dict[str, list[str]]:
    """Time-based dev/validation/OOS split (no random mixing)."""
    ordered = sorted(months)
    n = len(ordered)
    if n < 5:
        return {
            "development": list(ordered[: max(1, n // 3)]),
            "validation": list(ordered[max(1, n // 3) : max(2, 2 * n // 3)]),
            "out_of_sample": list(ordered[max(2, 2 * n // 3) :]),
        }
    oos_count = max(1, int(math.ceil(n * oos_fraction)))
    val_count = max(1, int(math.ceil(n * 0.30)))
    dev_count = n - oos_count - val_count
    if dev_count < 1:
        dev_count = 1
        val_count = max(1, n - oos_count - dev_count)
    return {
        "development": ordered[:dev_count],
        "validation": ordered[dev_count : dev_count + val_count],
        "out_of_sample": ordered[dev_count + val_count :],
    }


def build_stress_windows(
    months: Sequence[str],
    repo_root: Path = IMPORT_REPO,
    *,
    window_minutes: int = 7 * 24 * 60,
    revision_suffix: str = "",
    reject_windows: Mapping[str, int] | None = None,
    metrics_filter: Sequence[str] | None = None,
) -> list[WindowSpec]:
    """Data-driven stress windows from contiguous 1m islands only."""
    if len(months) == 0:
        return []

    step = window_minutes // 4
    reject = dict(reject_windows or {})
    best: dict[str, tuple[float, int, list[dict[str, Any]], tuple[str, ...]]] = {}

    for segment in _cross_month_segments(months, repo_root):
        segment_candles = _load_segment_candles(repo_root, segment)
        islands = _contiguous_islands(segment_candles)
        for wid_base, metric_key, reverse in STRESS_METRIC_DEFS:
            if metrics_filter is not None and wid_base not in metrics_filter:
                continue
            _update_metric_best(
                best,
                metric_key=metric_key,
                reverse=reverse,
                islands=islands,
                window_minutes=window_minutes,
                step=step,
                segment_months=segment,
            )

    windows: list[WindowSpec] = []
    seen_starts: set[int] = set()

    for wid_base, metric_key, _reverse in STRESS_METRIC_DEFS:
        if metrics_filter is not None and wid_base not in metrics_filter:
            continue
        entry = best.get(metric_key)
        if entry is None:
            continue
        _value, start_ts, chunk, _segment = entry
        if reject.get(wid_base) == start_ts:
            # pick next-best deterministically within already ranked scan
            candidates: list[
                tuple[float, int, list[dict[str, Any]], tuple[str, ...]]
            ] = []
            for segment in _cross_month_segments(months, repo_root):
                segment_candles = _load_segment_candles(repo_root, segment)
                for island in _contiguous_islands(segment_candles):
                    for metric, _, _, subchunk in _rank_stress_candidates(
                        [island],
                        metric_key=metric_key,
                        window_minutes=window_minutes,
                        step=step,
                        reverse=_reverse,
                    ):
                        try:
                            _validate_stress_window_candles(
                                subchunk, window_minutes=window_minutes
                            )
                        except HistoricalProbeError:
                            continue
                        candidates.append(
                            (metric, int(subchunk[0]["ts_ms"]), subchunk, segment)
                        )
            candidates = [c for c in candidates if c[1] != reject.get(wid_base, -1)]
            if not candidates:
                continue
            if metric_key in {"min_vol", "max_downtrend"}:
                candidates.sort(key=lambda item: (item[0], item[1]))
            else:
                candidates.sort(key=lambda item: (-item[0], item[1]))
            _value, start_ts, chunk, _segment = candidates[0]

        if start_ts in seen_starts:
            continue
        seen_starts.add(start_ts)
        source_months = _source_months_from_chunk(chunk, repo_root, _segment)
        wid = f"binance_1m_{wid_base}{revision_suffix}"
        windows.append(
            WindowSpec(
                window_id=wid,
                start_ts_ms=int(chunk[0]["ts_ms"]),
                end_ts_ms=int(chunk[-1]["ts_ms"]),
                candle_count=len(chunk),
                dataset_fingerprint="",
                regime_distribution=regime_distribution(chunk),
                source_months=tuple(source_months),
                overlap_class="stress",
                evidence_class="controlled_lab_evidence",
                purpose="stress",
                quality_verdict="STRICT_COMPLETE",
                candles_path="",
                spec_path="",
            )
        )
    return windows


def _source_months_from_chunk(
    chunk: Sequence[dict[str, Any]],
    repo_root: Path,
    candidate_months: Sequence[str],
) -> tuple[str, ...]:
    start = int(chunk[0]["ts_ms"])
    end = int(chunk[-1]["ts_ms"])
    selected: list[str] = []
    for month in sorted(candidate_months):
        bounds = _month_candle_bounds(repo_root, month)
        if bounds is None:
            continue
        first, last, _, _ = bounds
        if last < start or first > end:
            continue
        selected.append(month)
    return tuple(selected)


def _extract_stress_window_candles(
    repo_root: Path,
    source_months: Sequence[str],
    *,
    start_ts_ms: int,
    end_ts_ms: int,
    window_minutes: int,
) -> list[dict[str, Any]]:
    """Extract an exact contiguous stress slice from contiguous source months."""
    candles: list[dict[str, Any]] = []
    for month in sorted(source_months):
        candles.extend(_load_month_candles(repo_root, month))
    chunk = _slice_candles(candles, start_ts_ms, end_ts_ms)
    chunk = _enforce_contiguous_cadence(chunk)
    if len(chunk) < window_minutes:
        raise HistoricalProbeError(
            f"stress slice truncated to {len(chunk)} candles (< {window_minutes})"
        )
    chunk = chunk[:window_minutes]
    _validate_stress_window_candles(chunk, window_minutes=window_minutes)
    return chunk


def write_stress_rejection_evidence(
    repo_root: Path,
    *,
    window_id: str,
    reason: str,
    start_ts_ms: int,
    end_ts_ms: int,
    source_months: Sequence[str],
    expected_candles: int,
    actual_candles: int,
    gaps: Sequence[Mapping[str, Any]],
) -> Path:
    """Persist why an original stress window was rejected (no overwrite of candles)."""
    out_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / window_id
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "stress_window_rejection.v1",
        "window_id": window_id,
        "rejected_at_utc": utc_now_iso(),
        "reason": reason,
        "start_ts_ms": start_ts_ms,
        "end_ts_ms": end_ts_ms,
        "source_months": list(source_months),
        "expected_candle_count": expected_candles,
        "actual_candle_count": actual_candles,
        "cadence_gaps": list(gaps),
        "issue": "#3990",
    }
    path = out_dir / "rejection_evidence.json"
    write_json(path, payload)
    return path


STRESS_V2_WINDOW_IDS = (
    "binance_1m_stress_max_drawdown_v2",
    "binance_1m_stress_max_volatility_v2",
)
STRESS_V2_WINDOW_MINUTES = 7 * 24 * 60
_LEGACY_MARKET_DATA_MARKERS = ("E:/CDB_artifacts", "E:\\CDB_artifacts", "CDB_artifacts")


def _assert_no_legacy_market_data_path(path_text: str) -> None:
    normalized = path_text.replace("\\", "/").upper()
    for marker in _LEGACY_MARKET_DATA_MARKERS:
        if marker.replace("\\", "/").upper() in normalized:
            raise HistoricalProbeError(
                f"legacy market_data path reference forbidden: {path_text}"
            )


def _resolve_bank_candles_path(repo_root: Path, candles_path: str) -> Path:
    """Resolve a window-bank candles_path (absolute or repo-relative)."""
    raw = candles_path.strip()
    if not raw:
        return repo_root / "__missing__"
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_root / path


def _verify_stress_v2_storage_readonly(repo_root: Path, file_path: str) -> str:
    """Read-only storage checks for on-disk stress v2 windows (POSIX-safe)."""
    from tools.market_data.market_data_storage_guard import validate_market_data_storage

    _assert_no_legacy_market_data_path(file_path)
    resolved = Path(file_path)
    if not resolved.is_absolute():
        resolved = (repo_root / resolved).resolve()
    else:
        resolved = resolved.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise HistoricalProbeError(
            "stress v2 file_path must live under repo_root"
        ) from exc
    storage = validate_market_data_storage(
        repo_root=repo_root,
        required_write_bytes=0,
        expected_repo_volume_label=None,
    )
    if storage.allowed:
        return storage.reason_code
    if storage.reason_code in {
        "VOLUME_PROBE_FAILED",
        "UNKNOWN_VOLUME_ID",
        "UNKNOWN_FREE_SPACE",
    }:
        return "READ_ONLY_VERIFY_SKIPPED"
    raise HistoricalProbeError(
        f"market_data storage guard blocked: {storage.reason_code}"
    )


def verify_stress_v2_window(
    repo_root: Path,
    window_id: str,
    *,
    window_minutes: int = STRESS_V2_WINDOW_MINUTES,
) -> dict[str, Any]:
    """Fail-closed validation for an on-disk stress v2 window."""
    from core.replay.dataset_provider import FileBackedDatasetProvider
    from core.replay.dataset_spec import DatasetSpec

    window_dir = (
        repo_root
        / "artifacts"
        / "market_data"
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / window_id
    )
    spec_path = window_dir / "dataset_spec.json"
    candles_path = window_dir / "candles.jsonl"
    if not spec_path.exists() or not candles_path.exists():
        raise HistoricalProbeError(f"missing stress v2 artifacts for {window_id}")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    file_path = str(spec.get("file_path", ""))
    storage_reason = _verify_stress_v2_storage_readonly(repo_root, file_path)

    candles = [
        json.loads(line)
        for line in candles_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    _validate_stress_window_candles(candles, window_minutes=window_minutes)

    start_ts = int(spec["start_ts_ms"])
    end_ts = int(spec["end_ts_ms"])
    if int(candles[0]["ts_ms"]) != start_ts or int(candles[-1]["ts_ms"]) != end_ts:
        raise HistoricalProbeError(
            f"{window_id}: candle bounds mismatch spec start/end"
        )

    fp = sha256_file(candles_path)
    spec_fp = str(spec.get("fingerprint", "")).lower()
    candles_fp = str(spec.get("candles_sha256", "")).lower()
    if fp != spec_fp or fp != candles_fp:
        raise HistoricalProbeError(f"{window_id}: fingerprint mismatch")

    if spec.get("data_quality_verdict") != "STRICT_COMPLETE":
        raise HistoricalProbeError(f"{window_id}: quality verdict not STRICT_COMPLETE")
    # CDB-050: file SHA alone is insufficient — bind DQ content identity.
    dq_report = dq_report_from_dataset_spec(spec)
    if dq_report is None:
        raise HistoricalProbeError(
            f"{window_id}: missing data_quality_verdict for DQ content binding"
        )
    enforce_dq_content_binding(report=dq_report, candles=candles)
    if spec.get("venue") != "binance":
        raise HistoricalProbeError(f"{window_id}: venue must be binance")
    if spec.get("evidence_subclass") != "historical_cross_venue_research":
        raise HistoricalProbeError(f"{window_id}: evidence_subclass mismatch")
    if spec.get("ranking_ready") is not False:
        raise HistoricalProbeError(f"{window_id}: ranking_ready must be false")

    resolved_candles = candles_path.resolve()
    dataset_spec = DatasetSpec(
        source="file",
        file_path=str(resolved_candles),
        symbol="BTCUSDT",
        timeframe="1m",
        start_ts_ms=start_ts,
        end_ts_ms=end_ts,
        warmup_candles=0,
    )
    FileBackedDatasetProvider().load(dataset_spec)

    metrics = _window_metrics(candles)
    return {
        "window_id": window_id,
        "candle_count": len(candles),
        "start_ts_ms": start_ts,
        "end_ts_ms": end_ts,
        "source_months": list(spec.get("source_months") or []),
        "fingerprint": fp,
        "cadence_gaps": 0,
        "max_drawdown": metrics["max_dd"],
        "volatility": metrics["vol"],
        "file_path": file_path,
        "storage_guard": storage_reason,
        "dataset_provider_load": "PASS",
    }


def verify_stress_v2_windows(
    repo_root: Path = IMPORT_REPO,
    *,
    window_ids: Sequence[str] = STRESS_V2_WINDOW_IDS,
) -> dict[str, Any]:
    """Validate all configured stress v2 windows; returns per-window evidence."""
    results = [verify_stress_v2_window(repo_root, wid) for wid in window_ids]
    return {
        "verified_at_utc": utc_now_iso(),
        "window_count": len(results),
        "windows": results,
        "all_valid": True,
    }


def rebuild_stress_windows_v2(
    repo_root: Path = IMPORT_REPO,
    *,
    metrics: Sequence[str] = ("stress_max_drawdown", "stress_max_volatility"),
) -> dict[str, Any]:
    """Rebuild selected stress windows as *_v2 from contiguous islands only."""
    try:
        existing_validation = verify_stress_v2_windows(repo_root)
        return {
            "skipped_rebuild": True,
            "reason": "existing_v2_windows_valid",
            "validation": existing_validation,
            "written_v2": [],
            "rejections": [],
        }
    except HistoricalProbeError:
        pass

    months = resolve_build_months(repo_root)
    if not months:
        raise HistoricalProbeError("No STRICT_COMPLETE months in import manifest")

    bank_manifest_path = (
        _market_data_root(repo_root)
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
        / "window_bank_manifest.json"
    )
    existing_bank = (
        json.loads(bank_manifest_path.read_text(encoding="utf-8"))
        if bank_manifest_path.exists()
        else {"windows": []}
    )
    existing_by_id = {
        str(w["window_id"]): w for w in existing_bank.get("windows") or []
    }

    reject_starts: dict[str, int] = {}
    rejections: list[dict[str, Any]] = []
    window_minutes = 7 * 24 * 60

    for metric_base in metrics:
        old_id = f"binance_1m_{metric_base}"
        old = existing_by_id.get(old_id)
        if old is None:
            continue
        old_path = _resolve_bank_candles_path(
            repo_root, str(old.get("candles_path", ""))
        )
        if old_path.exists():
            old_candles = [
                json.loads(line)
                for line in old_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            gaps = _cadence_gaps(old_candles)
            if gaps:
                write_stress_rejection_evidence(
                    repo_root,
                    window_id=old_id,
                    reason="non_contiguous_source_month_reload_gap",
                    start_ts_ms=int(old["start_ts_ms"]),
                    end_ts_ms=int(old["end_ts_ms"]),
                    source_months=old.get("source_months") or [],
                    expected_candles=window_minutes,
                    actual_candles=len(old_candles),
                    gaps=gaps,
                )
                rejections.append(
                    {
                        "window_id": old_id,
                        "v2_id": f"{old_id}_v2",
                        "gap_count": len(gaps),
                        "first_gap": gaps[0],
                        "source_months": old.get("source_months"),
                    }
                )
                reject_starts[metric_base] = int(old["start_ts_ms"])

    v2_specs = build_stress_windows(
        months,
        repo_root,
        revision_suffix="_v2",
        reject_windows=reject_starts,
        metrics_filter=tuple(metrics),
    )

    written: list[dict[str, Any]] = []
    for spec in v2_specs:
        candles = _extract_stress_window_candles(
            repo_root,
            spec.source_months,
            start_ts_ms=spec.start_ts_ms,
            end_ts_ms=spec.end_ts_ms,
            window_minutes=window_minutes,
        )
        spec_path = _write_window_dataset(repo_root, spec, candles)
        fp = sha256_file(spec_path.parent / "candles.jsonl")
        written.append(
            {
                **asdict(spec),
                "dataset_fingerprint": fp,
                "candles_path": str((spec_path.parent / "candles.jsonl")).replace(
                    "\\", "/"
                ),
                "spec_path": str(spec_path).replace("\\", "/"),
                "revision": "v2",
                "replaces_window_id": spec.window_id.replace("_v2", ""),
            }
        )

    merged_windows = list(existing_bank.get("windows") or [])
    merged_ids = {str(w["window_id"]) for w in merged_windows}
    for row in written:
        if row["window_id"] not in merged_ids:
            merged_windows.append(row)
            merged_ids.add(row["window_id"])

    by_class: dict[str, int] = {}
    for w in merged_windows:
        cls = w.get("overlap_class", "unknown")
        by_class[cls] = by_class.get(cls, 0) + 1

    bank_root = bank_manifest_path.parent
    bank_manifest = {
        **existing_bank,
        "schema_version": WINDOW_BANK_SCHEMA,
        "updated_at_utc": utc_now_iso(),
        "window_count": len(merged_windows),
        "windows_by_class": by_class,
        "windows": merged_windows,
        "bank_root": str(bank_root).replace("\\", "/"),
        "stress_v2_rebuild": {
            "rebuilt_at_utc": utc_now_iso(),
            "metrics": list(metrics),
            "rejections": rejections,
            "written_v2": [w["window_id"] for w in written],
        },
    }
    write_json(bank_manifest_path, bank_manifest)
    return {
        "written_v2": written,
        "rejections": rejections,
        "bank_manifest_path": str(bank_manifest_path),
    }


def deduplicate_windows(windows: Sequence[WindowSpec]) -> list[WindowSpec]:
    seen: set[str] = set()
    unique: list[WindowSpec] = []
    for window in windows:
        key = f"{window.start_ts_ms}:{window.end_ts_ms}:{window.candle_count}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(window)
    return unique


def build_window_bank(
    repo_root: Path = IMPORT_REPO,
    *,
    include_stress: bool = True,
) -> dict[str, Any]:
    manifest = load_import_manifest(repo_root)
    months = resolve_build_months(repo_root)
    if not months:
        raise HistoricalProbeError("No STRICT_COMPLETE months in import manifest")

    split = compute_temporal_split(months)
    all_specs: list[WindowSpec] = []
    all_specs.extend(build_monthly_windows(months, repo_root))
    all_specs.extend(build_quarterly_windows(months, repo_root))
    all_specs.extend(build_yearly_windows(months, repo_root))
    if include_stress:
        all_specs.extend(build_stress_windows(months, repo_root))

    all_specs = deduplicate_windows(all_specs)
    written: list[dict[str, Any]] = []
    seen_fingerprints: set[str] = set()

    for spec in all_specs:
        if spec.overlap_class == "monthly":
            candles = _load_month_candles(repo_root, spec.source_months[0])
        elif spec.overlap_class in {"quarterly", "yearly"}:
            candles = []
            for m in spec.source_months:
                candles.extend(_load_month_candles(repo_root, m))
        elif spec.overlap_class == "stress":
            candles = _extract_stress_window_candles(
                repo_root,
                spec.source_months,
                start_ts_ms=spec.start_ts_ms,
                end_ts_ms=spec.end_ts_ms,
                window_minutes=spec.candle_count,
            )
        else:
            continue

        if not candles:
            continue

        spec_path = _write_window_dataset(repo_root, spec, candles)
        fp = sha256_file(spec_path.parent / "candles.jsonl")
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)
        written.append(
            {
                **asdict(spec),
                "dataset_fingerprint": fp,
                "candles_path": str((spec_path.parent / "candles.jsonl")).replace(
                    "\\", "/"
                ),
                "spec_path": str(spec_path).replace("\\", "/"),
            }
        )

    bank_root = (
        repo_root
        / "artifacts"
        / "market_data"
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
    )
    by_class: dict[str, int] = {}
    for w in written:
        cls = w.get("overlap_class", "unknown")
        by_class[cls] = by_class.get(cls, 0) + 1

    bank_manifest = {
        "schema_version": WINDOW_BANK_SCHEMA,
        "issue": "#3990",
        "created_at_utc": utc_now_iso(),
        "import_campaign_id": manifest.get("campaign_id"),
        "source_sha": manifest.get("source_sha"),
        "venue": "binance",
        "evidence_class": "historical_cross_venue_research",
        "not_evidence_class": ["mexc_same_venue", "live_evidence"],
        "temporal_split": split,
        "window_count": len(written),
        "windows_by_class": by_class,
        "windows": written,
        "bank_root": str(bank_root).replace("\\", "/"),
        "ranking_ready": False,
        "lr_status": "NO-GO",
    }
    manifest_path = bank_root / "window_bank_manifest.json"
    write_json(manifest_path, bank_manifest)
    bank_manifest["manifest_path"] = str(manifest_path).replace("\\", "/")
    return bank_manifest


def build_stress_rerun_manifest(
    repo_root: Path = IMPORT_REPO,
    *,
    campaign_id: str,
    source_sha: str | None = None,
) -> Path:
    """Manifest targeting only the two stress v2 windows (6 jobs)."""
    bank_root = (
        repo_root
        / "artifacts"
        / "market_data"
        / "window_bank"
        / "binance"
        / "spot"
        / "BTCUSDT"
        / "1m"
    )
    v2_roots = [
        str(bank_root / "binance_1m_stress_max_drawdown_v2").replace("\\", "/"),
        str(bank_root / "binance_1m_stress_max_volatility_v2").replace("\\", "/"),
    ]
    for root in v2_roots:
        if not Path(root).exists():
            raise HistoricalProbeError(f"Missing v2 stress window: {root}")

    if source_sha is None:
        import_manifest = load_import_manifest(repo_root)
        source_sha = str(import_manifest.get("source_sha", "RUNTIME_RESOLVE"))

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "campaign_id": campaign_id,
        "source_sha": source_sha,
        "evidence_class": "controlled_lab_evidence",
        "artifact_root": "artifacts/arvp_vacation",
        "allow_paper_jobs": False,
        "symbol": "BTCUSDT",
        "speedup_profile": "instant",
        "dataset_roots": v2_roots,
        "strategies": [
            {"strategy_id": "donchian_breakout_v1", "role": "active"},
            {"strategy_id": "breakout_trend_filter_v1", "role": "active"},
            {"strategy_id": "primary_breakout_v1", "role": "active"},
        ],
        "scenarios": ["baseline", "pessimistic_execution", "feed_gap"],
        "max_job_runtime_seconds": 7200,
        "max_attempts_per_job": 2,
        "min_free_disk_gb": 5,
        "metadata": {
            "issue": "#3990",
            "venue": "binance",
            "evidence_subclass": "historical_cross_venue_research",
            "stress_v2_rerun": True,
            "job_count_expected": 6,
        },
    }
    out_dir = repo_root / "artifacts" / "arvp_vacation" / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "binance_stress_v2_rerun_3990.yaml"
    out_path.write_text(yaml.dump(payload, sort_keys=False), encoding="utf-8")
    return out_path


def _repo_relative_path(repo_root: Path, campaign_dir: Path) -> str:
    candidate = campaign_dir
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return campaign_dir.as_posix()


_STRESS_V2_DATASET_SUFFIXES = (
    "stress_max_drawdown_v2",
    "stress_max_volatility_v2",
)
_STRESS_V1_FAIL_SUFFIXES = ("stress_max_drawdown", "stress_max_volatility")


def _is_stress_v2_job(job: dict[str, Any]) -> bool:
    dataset_id = str(job.get("dataset_id", ""))
    return any(dataset_id.endswith(suffix) for suffix in _STRESS_V2_DATASET_SUFFIXES)


def merge_stress_v2_into_campaign(
    *,
    original_campaign_dir: Path,
    rerun_campaign_dir: Path,
    repo_root: Path = IMPORT_REPO,
) -> dict[str, Any]:
    """Merge 6 v2 rerun jobs into the original campaign queue/summary."""
    from tools.arvp_vacation.contract import JOB_FAIL, JOB_PASS, load_manifest
    from tools.arvp_vacation.queue_store import QUEUE_STATE_FILENAME
    from tools.arvp_vacation.summary import write_summary

    orig_state_path = (
        repo_root / original_campaign_dir
    ).resolve() / QUEUE_STATE_FILENAME
    rerun_state_path = (repo_root / rerun_campaign_dir).resolve() / QUEUE_STATE_FILENAME
    rerun_rel = (
        rerun_campaign_dir.as_posix()
        if not rerun_campaign_dir.is_absolute()
        else _repo_relative_path(repo_root, rerun_campaign_dir)
    )
    original_campaign_dir = orig_state_path.parent
    rerun_campaign_dir = rerun_state_path.parent
    if not orig_state_path.exists() or not rerun_state_path.exists():
        raise HistoricalProbeError("Missing queue_state for campaign merge")

    orig_state = json.loads(orig_state_path.read_text(encoding="utf-8"))
    rerun_state = json.loads(rerun_state_path.read_text(encoding="utf-8"))

    orig_jobs = list(orig_state.get("jobs") or [])
    base_jobs = [
        j for j in orig_jobs if isinstance(j, dict) and not _is_stress_v2_job(j)
    ]
    rerun_jobs = [j for j in rerun_state.get("jobs") or [] if isinstance(j, dict)]
    if len(rerun_jobs) != 6:
        raise HistoricalProbeError(
            f"Expected exactly 6 rerun jobs, got {len(rerun_jobs)}"
        )

    superseded_ids = {
        str(j.get("job_id"))
        for j in base_jobs
        if j.get("status") == JOB_FAIL
        and any(
            str(j.get("dataset_id", "")).endswith(suffix)
            for suffix in _STRESS_V1_FAIL_SUFFIXES
        )
        and not _is_stress_v2_job(j)
    }
    for job in base_jobs:
        if job.get("job_id") in superseded_ids:
            job["superseded_by_stress_v2_rerun"] = True
            job["superseded_note"] = (
                "Original FAIL retained; replaced in campaign totals by v2 rerun"
            )

    merged_jobs = base_jobs + rerun_jobs
    pass_orig = sum(1 for j in base_jobs if j.get("status") == JOB_PASS)
    fail_orig = sum(1 for j in base_jobs if j.get("status") == JOB_FAIL)
    pass_v2 = sum(1 for j in rerun_jobs if j.get("status") == JOB_PASS)
    fail_v2 = sum(1 for j in rerun_jobs if j.get("status") == JOB_FAIL)

    merged_state = {
        **orig_state,
        "stress_v2_merge": {
            "merged_at_utc": utc_now_iso(),
            "original_pass": pass_orig,
            "original_fail": fail_orig,
            "v2_rerun_pass": pass_v2,
            "v2_rerun_fail": fail_v2,
            "combined_technical_pass": pass_orig + pass_v2,
            "combined_technical_fail": fail_v2,
            "rerun_campaign_dir": rerun_rel,
        },
        "jobs": merged_jobs,
    }
    write_json(orig_state_path, merged_state)

    manifest_path = (
        repo_root
        / "artifacts/arvp_vacation/manifests/binance_historical_campaign_3990.yaml"
    )
    manifest = load_manifest(manifest_path)
    write_summary(manifest, merged_state, repo_root)

    summary_path = original_campaign_dir / "vacation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["stress_v2_rebuild"] = merged_state["stress_v2_merge"]
    summary["combined_technical_pass"] = pass_orig + pass_v2
    summary["combined_technical_fail"] = fail_v2
    summary["original_pass_fail"] = {"pass": pass_orig, "fail": fail_orig}
    write_json(summary_path, summary)

    return merged_state["stress_v2_merge"]


def build_vacation_manifest(
    bank: dict[str, Any],
    repo_root: Path = IMPORT_REPO,
    *,
    pilot_only: bool = False,
    smoke_only: bool = False,
) -> Path:
    source_sha = bank.get("source_sha", "RUNTIME_RESOLVE")
    ts = utcnow().strftime("%Y%m%dT%H%M%SZ")
    campaign_id = f"arvp_binance_historical_3990_{str(source_sha)[:8]}_{ts}"

    bank_root = bank.get("bank_root", "")
    dataset_roots = [bank_root]

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "campaign_id": campaign_id,
        "source_sha": source_sha,
        "evidence_class": "controlled_lab_evidence",
        "artifact_root": "artifacts/arvp_vacation",
        "allow_paper_jobs": False,
        "symbol": "BTCUSDT",
        "speedup_profile": "instant",
        "dataset_roots": dataset_roots,
        "strategies": [
            {"strategy_id": "donchian_breakout_v1", "role": "active"},
            {"strategy_id": "breakout_trend_filter_v1", "role": "active"},
            {"strategy_id": "primary_breakout_v1", "role": "active"},
        ],
        "scenarios": ["baseline", "pessimistic_execution", "feed_gap"],
        "max_job_runtime_seconds": 7200,
        "max_attempts_per_job": 2,
        "min_free_disk_gb": 5,
        "metadata": {
            "issue": "#3990",
            "venue": "binance",
            "evidence_subclass": "historical_cross_venue_research",
            "not_evidence_class": ["mexc_same_venue", "live_evidence"],
            "pilot_only": pilot_only,
            "smoke_only": smoke_only,
        },
    }

    if smoke_only:
        payload["dataset_roots"] = [
            str(Path(bank_root) / "binance_1m_month_2026_06").replace("\\", "/")
        ]
    elif pilot_only:
        pilot_ids = []
        for w in bank.get("windows") or []:
            if w.get("overlap_class") in {"monthly", "quarterly"}:
                pilot_ids.append(w["window_id"])
                if len(pilot_ids) >= 2:
                    break
        payload["dataset_roots"] = [
            str(Path(bank_root) / wid).replace("\\", "/") for wid in pilot_ids[:2]
        ]

    out_dir = repo_root / "artifacts" / "arvp_vacation" / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "binance_historical_campaign_3990.yaml"
    out_path.write_text(yaml.dump(payload, sort_keys=False), encoding="utf-8")
    return out_path


def run_vacation_campaign(
    manifest_path: Path,
    repo_root: Path = IMPORT_REPO,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "tools.arvp_vacation.coordinator",
        "--manifest",
        str(manifest_path),
        "--run-until-complete",
        "--write-summary",
    ]
    completed = subprocess.run(
        cmd, cwd=str(repo_root), capture_output=True, text=True, check=False
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-4000:],
        "manifest_path": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Binance ARVP window bank (#3990)")
    parser.add_argument("--build-bank", action="store_true")
    parser.add_argument("--vacation-manifest", action="store_true")
    parser.add_argument("--pilot-manifest", action="store_true")
    parser.add_argument("--smoke-manifest", action="store_true")
    parser.add_argument("--run-campaign", action="store_true")
    parser.add_argument("--verify-stress-v2", action="store_true")
    parser.add_argument("--rebuild-stress-v2", action="store_true")
    parser.add_argument("--stress-v2-rerun", action="store_true")
    parser.add_argument("--merge-stress-v2", action="store_true")
    parser.add_argument("--original-campaign-dir", default=None)
    parser.add_argument("--rerun-campaign-dir", default=None)
    parser.add_argument("--manifest-path", default=None)
    args = parser.parse_args()

    try:
        if args.verify_stress_v2:
            result = verify_stress_v2_windows()
            print(json.dumps(result, indent=2))
            return 0

        if args.rebuild_stress_v2:
            result = rebuild_stress_windows_v2()
            print(json.dumps(result, indent=2, default=str))
            return 0

        if args.stress_v2_rerun:
            import_manifest = load_import_manifest()
            source_sha = str(import_manifest.get("source_sha", "RUNTIME_RESOLVE"))[:8]
            campaign_id = (
                f"arvp_binance_historical_3990_stress_v2_{source_sha}_"
                f"{utcnow().strftime('%Y%m%dT%H%M%SZ')}"
            )
            verify_stress_v2_windows()
            manifest_path = build_stress_rerun_manifest(
                campaign_id=campaign_id,
                source_sha=str(import_manifest.get("source_sha", "RUNTIME_RESOLVE")),
            )
            result = run_vacation_campaign(manifest_path)
            print(json.dumps({**result, "campaign_id": campaign_id}, indent=2))
            return 0 if result["exit_code"] == 0 else 2

        if args.merge_stress_v2:
            if not args.original_campaign_dir or not args.rerun_campaign_dir:
                parser.error(
                    "--merge-stress-v2 requires --original-campaign-dir and --rerun-campaign-dir"
                )
            merge_result = merge_stress_v2_into_campaign(
                original_campaign_dir=Path(args.original_campaign_dir),
                rerun_campaign_dir=Path(args.rerun_campaign_dir),
            )
            print(json.dumps(merge_result, indent=2))
            return 0

        if args.build_bank:
            bank = build_window_bank()
            print(json.dumps({"window_count": bank["window_count"]}, indent=2))
            if args.vacation_manifest or args.pilot_manifest or args.smoke_manifest:
                path = build_vacation_manifest(
                    bank,
                    pilot_only=args.pilot_manifest,
                    smoke_only=args.smoke_manifest,
                )
                print(json.dumps({"vacation_manifest": str(path)}, indent=2))
            return 0

        if args.vacation_manifest or args.pilot_manifest or args.smoke_manifest:
            bank = load_import_manifest()
            bank_stub = {
                "source_sha": bank.get("source_sha"),
                "bank_root": str(
                    REPO_ROOT
                    / "artifacts"
                    / "market_data"
                    / "window_bank"
                    / "binance"
                    / "spot"
                    / "BTCUSDT"
                    / "1m"
                ).replace("\\", "/"),
                "windows": (
                    json.loads(
                        (
                            REPO_ROOT
                            / "artifacts"
                            / "market_data"
                            / "window_bank"
                            / "binance"
                            / "spot"
                            / "BTCUSDT"
                            / "1m"
                            / "window_bank_manifest.json"
                        ).read_text(encoding="utf-8")
                    ).get("windows", [])
                    if (
                        REPO_ROOT
                        / "artifacts"
                        / "market_data"
                        / "window_bank"
                        / "binance"
                        / "spot"
                        / "BTCUSDT"
                        / "1m"
                        / "window_bank_manifest.json"
                    ).exists()
                    else []
                ),
            }
            path = build_vacation_manifest(
                bank_stub,
                pilot_only=args.pilot_manifest,
                smoke_only=args.smoke_manifest,
            )
            print(json.dumps({"vacation_manifest": str(path)}, indent=2))
            return 0

        if args.run_campaign:
            mpath = (
                Path(args.manifest_path)
                if args.manifest_path
                else (
                    REPO_ROOT
                    / "artifacts"
                    / "arvp_vacation"
                    / "manifests"
                    / "binance_historical_campaign_3990.yaml"
                )
            )
            result = run_vacation_campaign(mpath)
            print(json.dumps(result, indent=2))
            return 0 if result["exit_code"] == 0 else 2

        parser.print_help()
        return 1
    except (HistoricalProbeError, OSError) as exc:
        print(f"WINDOW_BANK_ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
