"""Build the #3152 multi-window MEXC evidence pack from fragmented candles.

This script is intentionally file-backed and readonly-DB-only:
- verifies cdb_readonly identity and SELECT-only privileges on public.candles_1m
- inventories exact 1m-contiguous BTCUSDT windows from the existing DB rows
- exports the top selected windows as independent file-backed datasets
- applies per-window distribution-based ATR p75 calibration
- runs file-backed replay per calibrated window using the existing replay runner
- aggregates economics without pretending the windows are one continuous history

Safety boundaries:
- no DB writes
- no runtime capture
- no Docker actions
- no strategy behavior change
- no production config change
- controlled_lab_evidence only
"""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.profitability.analyze_btcusdt_regime_calibration_3032 import (
    ATR_PERIOD,
    BUFFER_MAXLEN,
    compute_atr,
    compute_distribution_stats,
)
from scripts.profitability.assign_regime_calibrate_3032_expansion import (
    ADX_PERIOD,
    ADX_RANGE_THRESHOLD,
    ADX_TREND_THRESHOLD,
    CONFIRMATION_BARS,
    REGIME_ID_TO_NAME,
    build_derived_candles,
)
from services.validation.strategy_replay_runner import ARVPReplayConfig, run_arvp_replay

PARENT_ISSUE = "#3032"
CHILD_ISSUE = "#3152"
REF_ISSUES = ["#3091", "#3145", "#3147", "#3149", "#3151"]
EVIDENCE_CLASS = "controlled_lab_evidence"
LR_STATUS = "NO-GO"
BOARD_STAGE = "trade-capable"

SYMBOL = "BTCUSDT"
TIMEFRAME = "1m"
ONE_MINUTE_MS = 60_000
REPLAY_WARMUP_CANDLES = 240
MIN_WINDOW_ROWS = 720
MAX_SELECTED_WINDOWS = 20
ATR_THRESHOLD_DECIMALS = 2

OUTPUT_ROOT = REPO_ROOT / "artifacts" / "candles" / "mexc_multi_window_3032"
REPLAY_ROOT = REPO_ROOT / "artifacts" / "replay_reports" / "mexc_multi_window_3032"

WINDOW_INVENTORY_PATH = OUTPUT_ROOT / "window_inventory.json"
SELECTION_MANIFEST_PATH = OUTPUT_ROOT / "selection_manifest.json"

EXECUTION_ECONOMICS_PATH = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "profitability_execution_economics_primary_breakout_v1_mexc_multi_window_3032.json"
)
EVIDENCE_PACKET_PATH = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "profitability_evidence_packet_primary_breakout_v1_mexc_multi_window_3032.json"
)
EVIDENCE_DOC_PATH = (
    REPO_ROOT / "docs" / "evidence" / "profitability_mexc_multi_window_evidence_3032.md"
)

MEXC_VENUE_PROVENANCE_REFS = [
    "docs/evidence/mexc_future_capture_3091.md",
    "docs/evidence/profitability_mexc_sample_size_expansion_3032.md",
]


@dataclass(frozen=True, slots=True)
class CandleRow:
    ts_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    trade_count: int
    regime_id: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": SYMBOL,
            "ts_ms": self.ts_ms,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trade_count": self.trade_count,
            "regime_id": self.regime_id,
        }


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ts_ms_to_iso(ts_ms: int) -> str:
    return (
        datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def require_readonly_dsn() -> str:
    dsn = os.environ.get("POSTGRES_READONLY_PASSWORD_DSN", "").strip()
    if not dsn:
        raise RuntimeError("POSTGRES_READONLY_PASSWORD_DSN is required")
    return dsn


def connect_readonly():
    return psycopg2.connect(require_readonly_dsn())


def decimal_to_str(value: Decimal | int | None) -> str | None:
    if value is None:
        return None
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def fetch_db_context() -> dict[str, Any]:
    conn = connect_readonly()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, session_user")
            current_user, session_user = cur.fetchone()
            cur.execute("""
                SELECT
                    has_table_privilege(current_user, 'public.candles_1m', 'SELECT'),
                    has_table_privilege(current_user, 'public.candles_1m', 'INSERT'),
                    has_table_privilege(current_user, 'public.candles_1m', 'UPDATE'),
                    has_table_privilege(current_user, 'public.candles_1m', 'DELETE')
                """)
            can_select, can_insert, can_update, can_delete = cur.fetchone()
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'candles_1m'
                ORDER BY ordinal_position
                """)
            columns = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    if current_user != "cdb_readonly" or session_user != "cdb_readonly":
        raise RuntimeError(
            "Readonly DB identity mismatch: "
            f"current_user={current_user}, session_user={session_user}"
        )
    if not can_select or can_insert or can_update or can_delete:
        raise RuntimeError(
            "Readonly DB privileges invalid on public.candles_1m: "
            f"SELECT={can_select}, INSERT={can_insert}, UPDATE={can_update}, DELETE={can_delete}"
        )

    return {
        "current_user": current_user,
        "session_user": session_user,
        "privileges": {
            "select": bool(can_select),
            "insert": bool(can_insert),
            "update": bool(can_update),
            "delete": bool(can_delete),
        },
        "columns": columns,
        "venue_provenance_limitations": (
            "public.candles_1m has no source/venue column. MEXC attribution for this BTCUSDT "
            "series is inherited from prior same-venue evidence and runtime canon, not from per-row DB labels."
        ),
        "venue_provenance_refs": MEXC_VENUE_PROVENANCE_REFS,
    }


def fetch_btcusdt_rows() -> list[CandleRow]:
    conn = connect_readonly()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts_ms, open, high, low, close, volume, trade_count, regime_id
                FROM public.candles_1m
                WHERE symbol = %s
                ORDER BY ts_ms ASC
                """,
                (SYMBOL,),
            )
            rows = [
                CandleRow(
                    ts_ms=int(row[0]),
                    open=decimal_to_str(row[1]) or "0",
                    high=decimal_to_str(row[2]) or "0",
                    low=decimal_to_str(row[3]) or "0",
                    close=decimal_to_str(row[4]) or "0",
                    volume=decimal_to_str(row[5]) or "0",
                    trade_count=int(row[6]),
                    regime_id=int(row[7]) if row[7] is not None else None,
                )
                for row in cur.fetchall()
            ]
    finally:
        conn.close()
    return rows


def segment_rows(rows: list[CandleRow]) -> list[dict[str, Any]]:
    if not rows:
        return []

    segments: list[dict[str, Any]] = []
    start_idx = 0
    for idx in range(1, len(rows)):
        if rows[idx].ts_ms - rows[idx - 1].ts_ms != ONE_MINUTE_MS:
            segments.append(
                {
                    "start_idx": start_idx,
                    "end_idx": idx - 1,
                    "gap_after_ms": rows[idx].ts_ms - rows[idx - 1].ts_ms,
                }
            )
            start_idx = idx
    segments.append(
        {
            "start_idx": start_idx,
            "end_idx": len(rows) - 1,
            "gap_after_ms": None,
        }
    )

    inventory: list[dict[str, Any]] = []
    for offset, segment in enumerate(segments, start=1):
        start_idx = int(segment["start_idx"])
        end_idx = int(segment["end_idx"])
        segment_rows_list = rows[start_idx : end_idx + 1]
        start_ts = segment_rows_list[0].ts_ms
        end_ts = segment_rows_list[-1].ts_ms
        gap_before_ms = (
            None
            if offset == 1
            else start_ts - rows[int(segments[offset - 2]["end_idx"])].ts_ms
        )
        inventory.append(
            {
                "segment_id": offset,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "start_ts_ms": start_ts,
                "end_ts_ms": end_ts,
                "start_utc": ts_ms_to_iso(start_ts),
                "end_utc": ts_ms_to_iso(end_ts),
                "row_count": len(segment_rows_list),
                "duration_hours": round(len(segment_rows_list) / 60.0, 2),
                "gap_before_ms": gap_before_ms,
                "gap_after_ms": segment["gap_after_ms"],
                "exact_1m_cadence": True,
                "contains_regime_ids": any(
                    row.regime_id is not None for row in segment_rows_list
                ),
            }
        )
    return inventory


def build_window_inventory(
    rows: list[CandleRow], inventory: list[dict[str, Any]]
) -> dict[str, Any]:
    eligible = [item for item in inventory if int(item["row_count"]) >= MIN_WINDOW_ROWS]
    top20 = sorted(
        eligible, key=lambda item: (-int(item["row_count"]), int(item["start_ts_ms"]))
    )[:MAX_SELECTED_WINDOWS]
    summary = {
        "schema_version": "mexc_multi_window_inventory.v1",
        "generated_at": utc_now_iso(),
        "parent_issue": PARENT_ISSUE,
        "child_issue": CHILD_ISSUE,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "exact_cadence_ms": ONE_MINUTE_MS,
        "replay_warmup_candles": REPLAY_WARMUP_CANDLES,
        "minimum_window_rows": MIN_WINDOW_ROWS,
        "selection_cap": MAX_SELECTED_WINDOWS,
        "db_row_count": len(rows),
        "segment_count": len(inventory),
        "eligible_window_count": len(eligible),
        "selected_window_count": len(top20),
        "longest_window_rows": max(
            (item["row_count"] for item in inventory), default=0
        ),
        "windows_ge_threshold": {
            str(threshold): sum(
                1 for item in inventory if int(item["row_count"]) >= threshold
            )
            for threshold in (720, 1440, 2880, 4320, 5760, 7200)
        },
        "windows": inventory,
    }
    return summary


def build_selection_manifest(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [item for item in inventory if int(item["row_count"]) >= MIN_WINDOW_ROWS]
    selected = sorted(
        eligible, key=lambda item: (-int(item["row_count"]), int(item["start_ts_ms"]))
    )[:MAX_SELECTED_WINDOWS]
    selected_ids = {int(item["segment_id"]) for item in selected}
    excluded: list[dict[str, Any]] = []
    for item in inventory:
        row_count = int(item["row_count"])
        segment_id = int(item["segment_id"])
        if row_count < MIN_WINDOW_ROWS:
            reason = f"below_min_rows_{MIN_WINDOW_ROWS}"
        elif segment_id not in selected_ids:
            reason = f"ranked_beyond_top_{MAX_SELECTED_WINDOWS}_by_row_count"
        else:
            continue
        excluded.append(
            {
                "segment_id": segment_id,
                "row_count": row_count,
                "start_ts_ms": int(item["start_ts_ms"]),
                "end_ts_ms": int(item["end_ts_ms"]),
                "reason": reason,
            }
        )

    selected_payload: list[dict[str, Any]] = []
    for index, item in enumerate(selected, start=1):
        selected_payload.append(
            {
                "window_id": f"window_{index:03d}",
                "window_rank": index,
                "source_segment_id": int(item["segment_id"]),
                "selection_basis": "ranked_by_row_count_desc_then_start_ts_asc",
                "row_count": int(item["row_count"]),
                "duration_hours": float(item["duration_hours"]),
                "start_ts_ms": int(item["start_ts_ms"]),
                "end_ts_ms": int(item["end_ts_ms"]),
                "start_utc": item["start_utc"],
                "end_utc": item["end_utc"],
            }
        )

    return {
        "schema_version": "mexc_multi_window_selection_manifest.v1",
        "generated_at": utc_now_iso(),
        "parent_issue": PARENT_ISSUE,
        "child_issue": CHILD_ISSUE,
        "selection_rule": (
            f"Select all exact-1m contiguous windows with row_count >= {MIN_WINDOW_ROWS}; "
            f"if more than {MAX_SELECTED_WINDOWS} qualify, keep the top {MAX_SELECTED_WINDOWS} "
            "by row_count descending, then start_ts ascending. Selection is based only on continuity and length, never replay profitability."
        ),
        "minimum_window_rows": MIN_WINDOW_ROWS,
        "selection_cap": MAX_SELECTED_WINDOWS,
        "replay_warmup_candles": REPLAY_WARMUP_CANDLES,
        "selected_windows": selected_payload,
        "excluded_windows": excluded,
    }


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json_text(payload), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def candle_dicts(rows: list[CandleRow | dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, CandleRow):
            output.append(row.to_dict())
        else:
            output.append(dict(row))
    return output


def compute_window_atr_threshold(
    raw_rows: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    buffer: list[dict[str, Any]] = []
    atr_values: list[float] = []
    for row in raw_rows:
        buffer.append(row)
        if len(buffer) > BUFFER_MAXLEN:
            buffer.pop(0)
        atr = compute_atr(buffer, ATR_PERIOD)
        if atr is not None:
            atr_values.append(float(atr))
    stats = compute_distribution_stats(atr_values)
    threshold = round(float(stats["p75"]), ATR_THRESHOLD_DECIMALS)
    return threshold, stats


def export_window_bundle(
    *,
    db_context: dict[str, Any],
    window_meta: dict[str, Any],
    source_rows: list[CandleRow],
    window_id: str,
) -> dict[str, Any]:
    window_dir = OUTPUT_ROOT / window_id
    raw_path = window_dir / "candles.jsonl"
    raw_dicts = candle_dicts(source_rows)
    raw_text = jsonl_text(raw_dicts)
    raw_sha256 = sha256_text(raw_text)
    write_text(raw_path, raw_text)

    dataset_id = f"mexc_multi_window_3032_{window_id}"
    dataset_spec = {
        "spec_version": "1.0",
        "dataset_id": dataset_id,
        "source": "file",
        "file_path": str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "symbol": SYMBOL,
        "interval": TIMEFRAME,
        "venue": "mexc",
        "venue_match": True,
        "venue_provenance_inherited": True,
        "venue_provenance_refs": db_context["venue_provenance_refs"],
        "venue_provenance_limitations": db_context["venue_provenance_limitations"],
        "row_count": len(source_rows),
        "start_ts_ms": source_rows[0].ts_ms,
        "end_ts_ms": source_rows[-1].ts_ms,
        "start_utc": ts_ms_to_iso(source_rows[0].ts_ms),
        "end_utc": ts_ms_to_iso(source_rows[-1].ts_ms),
        "replay_warmup_candles": REPLAY_WARMUP_CANDLES,
        "candles_sha256": raw_sha256,
        "exact_1m_cadence": True,
        "evidence_class": EVIDENCE_CLASS,
    }
    write_json(window_dir / "dataset_spec.json", dataset_spec)

    provenance_manifest = {
        "schema_version": "mexc_multi_window_provenance_manifest.v1",
        "generated_at": utc_now_iso(),
        "parent_issue": PARENT_ISSUE,
        "child_issue": CHILD_ISSUE,
        "window_id": window_id,
        "source_segment_id": int(window_meta["source_segment_id"]),
        "selection_rank": int(window_meta["window_rank"]),
        "query_semantics": {
            "dsn_env": "POSTGRES_READONLY_PASSWORD_DSN",
            "table": "public.candles_1m",
            "symbol_filter": SYMBOL,
            "ordering": "ORDER BY ts_ms ASC",
            "exact_contiguity_rule": "next_ts_ms - current_ts_ms == 60000",
            "selection_rule": "top windows by exact continuity and row_count only",
        },
        "readonly_identity": {
            "current_user": db_context["current_user"],
            "session_user": db_context["session_user"],
            "privileges": db_context["privileges"],
        },
        "window": {
            "row_count": len(source_rows),
            "start_ts_ms": source_rows[0].ts_ms,
            "end_ts_ms": source_rows[-1].ts_ms,
            "start_utc": ts_ms_to_iso(source_rows[0].ts_ms),
            "end_utc": ts_ms_to_iso(source_rows[-1].ts_ms),
            "duration_hours": round(len(source_rows) / 60.0, 2),
            "gap_before_ms": window_meta.get("gap_before_ms"),
            "gap_after_ms": window_meta.get("gap_after_ms"),
            "exact_1m_cadence": True,
        },
        "hashes": {
            "candles_sha256": raw_sha256,
            "dataset_spec_sha256": sha256_text(json_text(dataset_spec)),
        },
        "venue": {
            "value": "mexc",
            "inherited_from_prior_evidence": True,
            "refs": db_context["venue_provenance_refs"],
            "limitations": db_context["venue_provenance_limitations"],
        },
        "safety": {
            "db_writes": False,
            "runtime_capture": False,
            "docker_actions": False,
            "strategy_change": False,
            "production_config_change": False,
            "live_go": False,
            "real_money_go": False,
            "lr_status": LR_STATUS,
        },
    }
    write_json(window_dir / "provenance_manifest.json", provenance_manifest)

    return {
        "dataset_id": dataset_id,
        "window_dir": window_dir,
        "raw_path": raw_path,
        "raw_sha256": raw_sha256,
        "raw_rows": raw_dicts,
        "source_segment_id": int(window_meta["source_segment_id"]),
    }


def write_calibrated_bundle(
    *,
    raw_bundle: dict[str, Any],
    atr_threshold: float,
    atr_stats: dict[str, Any],
    derived_rows: list[dict[str, Any]],
    distribution: dict[int, int],
) -> dict[str, Any]:
    derived_dir = Path(raw_bundle["window_dir"]) / "regime_calibrated"
    derived_path = derived_dir / "candles.jsonl"
    derived_text = jsonl_text(derived_rows)
    derived_sha256 = sha256_text(derived_text)
    write_text(derived_path, derived_text)

    derived_dataset_id = f"{raw_bundle['dataset_id']}_regime_calibrated"
    derived_dataset_spec = {
        "spec_version": "1.0",
        "dataset_id": derived_dataset_id,
        "derived_from": raw_bundle["dataset_id"],
        "source": "file",
        "file_path": str(derived_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "symbol": SYMBOL,
        "interval": TIMEFRAME,
        "venue": "mexc",
        "venue_match": True,
        "row_count": len(derived_rows),
        "replay_warmup_candles": REPLAY_WARMUP_CANDLES,
        "regime_assigned": True,
        "regime_calibrated": True,
        "candles_sha256": derived_sha256,
        "evidence_class": EVIDENCE_CLASS,
        "estimation": True,
    }
    write_json(derived_dir / "dataset_spec.json", derived_dataset_spec)

    calibration_manifest = {
        "schema_version": "mexc_multi_window_calibration_manifest.v1",
        "generated_at": utc_now_iso(),
        "parent_issue": PARENT_ISSUE,
        "child_issue": CHILD_ISSUE,
        "dataset_id": raw_bundle["dataset_id"],
        "derived_dataset_id": derived_dataset_id,
        "method": "offline_heuristic_adx_atr",
        "method_detail": (
            "Deterministic offline ADX/ATR regime classification reusing the existing #3145/#3147 logic. "
            "ADX thresholds stay committed; ATR high-vol threshold is selected from this window's ATR(14) distribution at p75."
        ),
        "calibration_rule": "distribution_based_p75",
        "calibration_rule_refs": ["#3145", "#3147"],
        "calibration_parameters": {
            "atr_period": ATR_PERIOD,
            "adx_period": ADX_PERIOD,
            "adx_trend_threshold": ADX_TREND_THRESHOLD,
            "adx_range_threshold": ADX_RANGE_THRESHOLD,
            "confirmation_bars": CONFIRMATION_BARS,
            "buffer_maxlen": BUFFER_MAXLEN,
            "atr_p75_threshold": atr_threshold,
            "atr_distribution_p50": round(float(atr_stats["p50"]), 6),
            "atr_distribution_p75": round(float(atr_stats["p75"]), 6),
            "atr_distribution_p90": round(float(atr_stats["p90"]), 6),
        },
        "estimation": True,
        "estimation_note": (
            "All regime labels are estimated=true and evidence_class=controlled_lab_evidence. "
            "No runtime regime service was used."
        ),
        "evidence_class": EVIDENCE_CLASS,
        "distribution": {
            str(regime_id): {
                "regime_name": REGIME_ID_TO_NAME.get(regime_id, "UNKNOWN"),
                "count": count,
                "pct": round(count / len(derived_rows) * 100.0, 3),
            }
            for regime_id, count in sorted(distribution.items())
        },
        "hashes": {
            "raw_candles_sha256": raw_bundle["raw_sha256"],
            "derived_candles_sha256": derived_sha256,
            "dataset_spec_sha256": sha256_text(json_text(derived_dataset_spec)),
        },
        "no_threshold_selection_by_profit": True,
    }
    write_json(derived_dir / "calibration_manifest.json", calibration_manifest)

    return {
        "derived_dir": derived_dir,
        "derived_dataset_id": derived_dataset_id,
        "derived_path": derived_path,
        "derived_sha256": derived_sha256,
        "calibration_manifest_path": derived_dir / "calibration_manifest.json",
        "atr_threshold": atr_threshold,
        "atr_stats": atr_stats,
        "distribution": distribution,
    }


def latest_replay_bundle(output_dir: Path) -> Path | None:
    candidates = [
        path
        for path in output_dir.iterdir()
        if path.is_dir() and path.name.startswith("replay-")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def run_window_replay(window_id: str, calibrated_path: Path) -> dict[str, Any]:
    replay_output_dir = REPLAY_ROOT / window_id
    replay_output_dir.mkdir(parents=True, exist_ok=True)
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=str(calibrated_path),
        strategy_id="primary_breakout_v1",
        symbol=SYMBOL,
        adapter_id="primary_breakout_runner_v1",
        output_directory=str(replay_output_dir),
        deterministic_verify=True,
    )
    config.validate()
    exit_code = run_arvp_replay(config)
    bundle_dir = latest_replay_bundle(replay_output_dir)
    if exit_code != 0 or bundle_dir is None:
        return {
            "window_id": window_id,
            "exit_code": exit_code,
            "status": "failed",
            "failure_reason": "replay runner failed before writing a replay bundle",
        }

    report_path = bundle_dir / "report.json"
    if not report_path.exists():
        return {
            "window_id": window_id,
            "exit_code": exit_code,
            "status": "failed",
            "failure_reason": f"report.json missing under {bundle_dir}",
        }

    report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = report.get("metrics", {})
    gate_result = report.get("gate_result", {})
    return {
        "window_id": window_id,
        "status": "ok",
        "exit_code": exit_code,
        "bundle_dir": str(bundle_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "report_path": str(report_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "run_id": report.get("execution_result", {}).get("run_id")
        or report.get("run_metadata", {}).get("run_id"),
        "deterministic_replay_ok": bool(metrics.get("deterministic_replay_ok", False)),
        "gate_result": gate_result.get("status"),
        "gate_failed_criteria": gate_result.get("failed_criteria", []),
        "signals_total": int(metrics.get("signals_total", 0)),
        "buy_signals_total": int(metrics.get("buy_signals_total", 0)),
        "sell_signals_total": int(metrics.get("sell_signals_total", 0)),
        "closed_trades_total": int(metrics.get("closed_trades_total", 0)),
        "trades_win_count": int(metrics.get("trades_win_count", 0)),
        "trades_loss_count": int(metrics.get("trades_loss_count", 0)),
        "win_rate": float(metrics.get("win_rate", 0.0)),
        "profit_factor": float(metrics.get("profit_factor", 0.0)),
        "gross_return_r": float(metrics.get("gross_return_r", 0.0)),
        "expectancy_r": float(metrics.get("expectancy_r", 0.0)),
        "fee_adjusted_expectancy_r": metrics.get("fee_adjusted_expectancy_r"),
        "fee_adjusted_profit_factor": metrics.get("fee_adjusted_profit_factor"),
        "max_drawdown_r": float(metrics.get("max_drawdown_r", 0.0)),
        "gross_pnl_quote": float(metrics.get("gross_pnl_quote", 0.0)),
        "net_pnl_quote": float(metrics.get("net_pnl_quote", 0.0)),
        "fees_total_quote": float(metrics.get("fees_total_quote", 0.0)),
        "avg_win_r": metrics.get("avg_win_r"),
        "avg_loss_r": metrics.get("avg_loss_r"),
        "largest_win_r": metrics.get("largest_win_r"),
        "largest_loss_r": metrics.get("largest_loss_r"),
        "sample_size_verdict": metrics.get("sample_size_verdict"),
        "metrics_availability": metrics.get("metrics_availability", {}),
        "data_integrity_ok": bool(metrics.get("data_integrity_ok", False)),
    }


def aggregate_results(window_runs: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [item for item in window_runs if item["replay"]["status"] == "ok"]
    failed = [item for item in window_runs if item["replay"]["status"] != "ok"]
    total_closed_trades = sum(
        int(item["replay"].get("closed_trades_total", 0)) for item in successful
    )
    total_wins = sum(
        int(item["replay"].get("trades_win_count", 0)) for item in successful
    )
    total_losses = sum(
        int(item["replay"].get("trades_loss_count", 0)) for item in successful
    )
    windows_with_trades = sum(
        1
        for item in successful
        if int(item["replay"].get("closed_trades_total", 0)) > 0
    )
    aggregate_gross_pnl = sum(
        float(item["replay"].get("gross_pnl_quote", 0.0)) for item in successful
    )
    aggregate_net_pnl = sum(
        float(item["replay"].get("net_pnl_quote", 0.0)) for item in successful
    )
    aggregate_fees = sum(
        float(item["replay"].get("fees_total_quote", 0.0)) for item in successful
    )
    aggregate_gross_return_r = sum(
        float(item["replay"].get("gross_return_r", 0.0)) for item in successful
    )
    aggregate_signals = sum(
        int(item["replay"].get("signals_total", 0)) for item in successful
    )
    aggregate_fee_adjusted_return_r = sum(
        float(item["replay"].get("fee_adjusted_expectancy_r") or 0.0)
        * int(item["replay"].get("closed_trades_total", 0))
        for item in successful
    )
    economics_materially_negative = (
        aggregate_net_pnl < 0
        or aggregate_gross_return_r < 0
        or total_wins < total_losses
    )

    if total_closed_trades >= 20 and windows_with_trades >= 3:
        sample_size_verdict = "PASS"
        if economics_materially_negative:
            recommendation = (
                "Multi-window sample threshold reached, but aggregate economics are materially negative. "
                "Create a narrow PARK/REJECT decision slice and, if useful, a seed league-table entry explicitly marked PARK."
            )
        else:
            recommendation = "Multi-window sample threshold reached for controlled-lab evidence. Still no promotion or live-readiness implication."
        overall_status = "DONE_MERGED_MEXC_MULTI_WINDOW_EVIDENCE"
    else:
        sample_size_verdict = "INSUFFICIENT"
        recommendation = (
            "Sample still insufficient. Continue with a narrow evidence-backed follow-up: either replay more independent windows, "
            "or pursue a separate continuity/capture path."
        )
        overall_status = "HOLD_SAMPLE_STILL_INSUFFICIENT"

    return {
        "successful_windows": len(successful),
        "failed_windows": len(failed),
        "total_windows": len(window_runs),
        "windows_with_trades": windows_with_trades,
        "total_closed_trades": total_closed_trades,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "aggregate_signals_total": aggregate_signals,
        "aggregate_win_rate": (
            (total_wins / total_closed_trades) if total_closed_trades else 0.0
        ),
        "aggregate_gross_pnl_quote": aggregate_gross_pnl,
        "aggregate_net_pnl_quote": aggregate_net_pnl,
        "aggregate_fees_total_quote": aggregate_fees,
        "aggregate_gross_return_r": aggregate_gross_return_r,
        "aggregate_fee_adjusted_return_r": aggregate_fee_adjusted_return_r,
        "economics_materially_negative": economics_materially_negative,
        "sample_size_verdict": sample_size_verdict,
        "recommendation": recommendation,
        "overall_status": overall_status,
    }


def fee_adjusted_window_return(window_result: dict[str, Any]) -> float | None:
    replay = window_result["replay"]
    if replay["status"] != "ok":
        return None
    expectancy = replay.get("fee_adjusted_expectancy_r")
    if expectancy is None:
        return None
    return float(expectancy) * int(replay.get("closed_trades_total", 0))


def build_window_result_payload(item: dict[str, Any]) -> dict[str, Any]:
    replay = item["replay"]
    calibrated = item["calibrated"]
    raw = item["raw"]
    return {
        "window_id": item["window_id"],
        "source_segment_id": raw["source_segment_id"],
        "dataset_id": raw["dataset_id"],
        "derived_dataset_id": calibrated["derived_dataset_id"],
        "row_count": item["row_count"],
        "duration_hours": item["duration_hours"],
        "start_ts_ms": item["start_ts_ms"],
        "end_ts_ms": item["end_ts_ms"],
        "start_utc": item["start_utc"],
        "end_utc": item["end_utc"],
        "atr_p75_threshold": calibrated["atr_threshold"],
        "regime_distribution": {
            REGIME_ID_TO_NAME.get(int(regime_id), str(regime_id)): {
                "count": count,
                "pct": round(count / item["row_count"] * 100.0, 3),
            }
            for regime_id, count in sorted(calibrated["distribution"].items())
        },
        "replay": replay,
    }


def build_execution_economics_json(
    window_runs: list[dict[str, Any]], aggregate: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "execution_economics_summary.v1",
        "summary_id": "econ-primary-breakout-v1-btcusdt-mexc-multi-window-3032",
        "evidence_packet_ref": str(EVIDENCE_PACKET_PATH.relative_to(REPO_ROOT)).replace(
            "\\", "/"
        ),
        "candidate_id": "cand-primary-breakout-v1-btcusdt-mexc-3032",
        "generated_at": utc_now_iso(),
        "dataset_id": "mexc_multi_window_3032",
        "selection": {
            "minimum_window_rows": MIN_WINDOW_ROWS,
            "selection_cap": MAX_SELECTED_WINDOWS,
            "replay_warmup_candles": REPLAY_WARMUP_CANDLES,
            "window_count": len(window_runs),
        },
        "aggregate_trade_metrics": {
            "signals_total": aggregate["aggregate_signals_total"],
            "closed_trades_total": aggregate["total_closed_trades"],
            "trades_win_count": aggregate["total_wins"],
            "trades_loss_count": aggregate["total_losses"],
            "windows_with_trades": aggregate["windows_with_trades"],
            "win_rate": aggregate["aggregate_win_rate"],
        },
        "aggregate_return_metrics_quote": {
            "gross_pnl_quote": aggregate["aggregate_gross_pnl_quote"],
            "net_pnl_quote": aggregate["aggregate_net_pnl_quote"],
            "fees_total_quote": aggregate["aggregate_fees_total_quote"],
        },
        "aggregate_return_metrics_r": {
            "gross_return_r": aggregate["aggregate_gross_return_r"],
            "fee_adjusted_return_r": aggregate["aggregate_fee_adjusted_return_r"],
            "note": "Summed per-window gross_return_r across independent windows. Windows are independent fragments, not one continuous market history.",
        },
        "window_results": [build_window_result_payload(item) for item in window_runs],
        "sample_size_gate": {
            "verdict": aggregate["sample_size_verdict"],
            "closed_trades_total": aggregate["total_closed_trades"],
            "windows_with_trades": aggregate["windows_with_trades"],
            "required_closed_trades": 20,
            "required_windows_with_trades": 3,
            "note": "PASS only if total closed trades >= 20 and at least 3 windows have trades; otherwise INSUFFICIENT.",
        },
        "execution_quality": {
            "successful_windows": aggregate["successful_windows"],
            "failed_windows": aggregate["failed_windows"],
            "deterministic_replay_ok_all_successful": all(
                bool(item["replay"].get("deterministic_replay_ok", False))
                for item in window_runs
                if item["replay"]["status"] == "ok"
            ),
        },
        "verdict": {
            "overall": (
                "PARK"
                if aggregate["economics_materially_negative"]
                else "CONTROLLED_LAB_ONLY"
            ),
            "economic_assessment": (
                "Aggregate economics are materially negative. Do not promote."
                if aggregate["economics_materially_negative"]
                else "Controlled-lab sample threshold met, but still no promotion or live implication."
            ),
            "next_recommended_step": aggregate["recommendation"],
        },
        "evidence_class": EVIDENCE_CLASS,
        "lr_status": LR_STATUS,
        "parent_issue": PARENT_ISSUE,
        "child_issue": CHILD_ISSUE,
    }


def longest_loss_streak(window_runs: list[dict[str, Any]]) -> int | None:
    successful = [item for item in window_runs if item["replay"]["status"] == "ok"]
    if not successful:
        return None
    streak = 0
    best = 0
    for item in successful:
        wins = int(item["replay"].get("trades_win_count", 0))
        losses = int(item["replay"].get("trades_loss_count", 0))
        if wins == 0 and losses > 0:
            streak += losses
            best = max(best, streak)
        elif losses > 0:
            best = max(best, max(losses, streak))
            streak = 0
        else:
            streak = 0
    return best


def build_evidence_packet_json(
    window_runs: list[dict[str, Any]], aggregate: dict[str, Any]
) -> dict[str, Any]:
    dataset_fingerprint_input = {
        "selected_windows": [
            {
                "window_id": item["window_id"],
                "raw_sha256": item["raw"]["raw_sha256"],
                "derived_sha256": item["calibrated"]["derived_sha256"],
            }
            for item in window_runs
        ]
    }
    recommendation = (
        "PARK" if aggregate["economics_materially_negative"] else "CONTROLLED_LAB_ONLY"
    )
    source_run_refs = [
        str(WINDOW_INVENTORY_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        str(SELECTION_MANIFEST_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
    ]
    for item in window_runs:
        raw_dir = Path(item["raw"]["window_dir"]).relative_to(REPO_ROOT)
        source_run_refs.extend(
            [
                str((raw_dir / "dataset_spec.json").as_posix()),
                str((raw_dir / "provenance_manifest.json").as_posix()),
                str((raw_dir / "regime_calibrated" / "dataset_spec.json").as_posix()),
                str(
                    (
                        raw_dir / "regime_calibrated" / "calibration_manifest.json"
                    ).as_posix()
                ),
            ]
        )
        if item["replay"]["status"] == "ok":
            source_run_refs.append(item["replay"]["report_path"])

    gross_return = aggregate["aggregate_gross_return_r"]
    net_return = aggregate["aggregate_fee_adjusted_return_r"]

    return {
        "schema_version": "profitability_evidence_packet.v1",
        "evidence_packet_id": "pep-primary-breakout-v1-btcusdt-mexc-multi-window-3032",
        "candidate_id": "cand-primary-breakout-v1-btcusdt-mexc-3032",
        "generated_at": utc_now_iso(),
        "dataset_id": "mexc_multi_window_3032",
        "dataset_fingerprint": f"sha256:{sha256_text(json.dumps(dataset_fingerprint_input, sort_keys=True))}",
        "source_run_refs": source_run_refs,
        "gross_return": gross_return,
        "net_return": net_return,
        "fees": aggregate["aggregate_fees_total_quote"],
        "spread_cost": 0.0,
        "slippage_cost": 0.0,
        "profit_factor": None,
        "expectancy": (
            aggregate["aggregate_gross_return_r"] / aggregate["total_closed_trades"]
            if aggregate["total_closed_trades"]
            else 0.0
        ),
        "win_rate": aggregate["aggregate_win_rate"],
        "avg_win": None,
        "avg_loss": None,
        "max_drawdown": None,
        "loss_streak": longest_loss_streak(window_runs),
        "trade_count": aggregate["total_closed_trades"],
        "regime_scorecard": {
            "status": "ok",
            "artifact_ref": str(SELECTION_MANIFEST_PATH.relative_to(REPO_ROOT)).replace(
                "\\", "/"
            ),
            "summary": "Per-window regime labels were estimated via offline ADX/ATR heuristic using a distribution-based ATR p75 calibration rule. controlled_lab_evidence only.",
        },
        "scenario_results": [
            {
                "scenario_id": item["window_id"],
                "status": "PASS" if item["replay"]["status"] == "ok" else "FAIL",
                "net_return": fee_adjusted_window_return(item),
                "max_drawdown": (
                    item["replay"].get("max_drawdown_r")
                    if item["replay"]["status"] == "ok"
                    else None
                ),
                "notes": (
                    f"run_id={item['replay'].get('run_id')}; closed_trades={item['replay'].get('closed_trades_total')}; gate_result={item['replay'].get('gate_result')}; sample_size_verdict={item['replay'].get('sample_size_verdict')}"
                    if item["replay"]["status"] == "ok"
                    else item["replay"].get("failure_reason")
                ),
            }
            for item in window_runs
        ],
        "replay_vs_paper_status": "not_run",
        "simulator_drift": "not_assessed",
        "risk_blocks": 0,
        "kill_switch_events": 0,
        "recommendation": recommendation,
        "limitations": [
            "controlled_lab_evidence only.",
            "Windows are independent fragments, not one continuous market history.",
            "No production config change.",
            "No strategy change.",
            "No runtime capture.",
            "No Live-Go, no Echtgeld-Go, LR remains NO-GO.",
            "public.candles_1m has no source/venue column; MEXC attribution for this BTCUSDT series is inherited from prior same-venue evidence and runtime canon, not from per-row DB labels.",
        ],
        "evidence_class": EVIDENCE_CLASS,
        "lr_status": LR_STATUS,
        "board_stage": BOARD_STAGE,
        "board_stage_note": "Board stage is orthogonal to LR. Does not authorize live trading.",
        "sample_size_verdict": aggregate["sample_size_verdict"].lower(),
        "sample_size_note": aggregate["recommendation"],
        "parent_issue": PARENT_ISSUE,
        "child_issue": CHILD_ISSUE,
    }


def build_markdown_doc(
    *,
    db_context: dict[str, Any],
    inventory_payload: dict[str, Any],
    selection_manifest: dict[str, Any],
    window_runs: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> str:
    brain_evidence_lines = [
        "## Brain Evidence",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| `brain_source` | `repo-only` |",
        "| `brain_status` | `not-used` |",
        "| `tools_or_queries` | `git fetch`, `gh issue view/create/comment`, `python psycopg2 readonly SELECT`, `python -m services.validation.strategy_replay_runner`, `python -m json.tool` |",
        (
            "| `records_or_results` | "
            f"DB rows={inventory_payload['db_row_count']}, exact-1m windows={inventory_payload['segment_count']}, "
            f"selected windows={selection_manifest['selected_windows'].__len__()}, total closed trades={aggregate['total_closed_trades']}, "
            f"sample_size_verdict={aggregate['sample_size_verdict']}. |"
        ),
        (
            "| `repo_crosscheck` | `docs/evidence/mexc_future_capture_3091.md`, "
            "`docs/evidence/profitability_mexc_sample_size_expansion_3032.md`, "
            "`services/validation/strategy_replay_runner.py`, `services/validation/strategy_backtest_runner.py` |"
        ),
        (
            "| `impact_on_plan` | Existing readonly fragmented BTCUSDT inventory is large enough for multi-window evidence. "
            "Windows are replayed independently instead of forcing a broken continuous chain. |"
        ),
        (
            "| `limitations` | No SurrealDB/Context Brain used. public.candles_1m has no venue column; MEXC attribution is inherited from prior same-venue evidence. |"
        ),
        "",
    ]

    selected_count = len(selection_manifest["selected_windows"])
    replay_rows = []
    for item in window_runs:
        replay = item["replay"]
        if replay["status"] == "ok":
            replay_rows.append(
                "| {window_id} | {source_segment_id} | {row_count} | {atr_threshold:.2f} | {signals_total} | {closed_trades_total} | {win_rate:.3f} | {profit_factor:.3f} | {net_pnl_quote:.2f} | {fees_total_quote:.2f} | {sample_size_verdict} | {gate_result} |".format(
                    window_id=item["window_id"],
                    source_segment_id=item["raw"]["source_segment_id"],
                    row_count=item["row_count"],
                    atr_threshold=item["calibrated"]["atr_threshold"],
                    signals_total=replay["signals_total"],
                    closed_trades_total=replay["closed_trades_total"],
                    win_rate=replay["win_rate"],
                    profit_factor=replay["profit_factor"],
                    net_pnl_quote=replay["net_pnl_quote"],
                    fees_total_quote=replay["fees_total_quote"],
                    sample_size_verdict=replay["sample_size_verdict"],
                    gate_result=replay["gate_result"],
                )
            )
        else:
            replay_rows.append(
                f"| {item['window_id']} | {item['raw']['source_segment_id']} | {item['row_count']} | {item['calibrated']['atr_threshold']:.2f} | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |"
            )

    lines = [
        "# CDB Profitability -- MEXC Multi-Window Evidence #3032",
        "",
        f"**Date:** {utc_now_iso()}",
        f"**Parent:** {PARENT_ISSUE}",
        f"**Issue:** {CHILD_ISSUE}",
        "**Refs:** #3091, #3145, #3147, #3149, #3151",
        "**Status:** Complete -- multi-window controlled-lab evidence pack built from fragmented exact-1m windows",
        "",
        *brain_evidence_lines,
        "## Scope and Non-goals",
        "",
        "### In scope",
        "- Readonly DB inventory of existing BTCUSDT 1m rows.",
        "- Exact-1m contiguous window detection.",
        "- Export of selected windows as independent file-backed datasets.",
        "- Per-window distribution-based ATR p75 calibration.",
        "- Per-window file-backed replay with #3149 economics fields.",
        "- Aggregate economics without pretending the windows form one continuous history.",
        "",
        "### Non-goals",
        "- No runtime capture.",
        "- No DB writes.",
        "- No Docker / compose.",
        "- No production config change.",
        "- No strategy change.",
        "- No schema change.",
        "- No threshold selection by profit.",
        "",
        "## Readonly DB Inventory",
        "",
        "| Check | Result |",
        "|-------|--------|",
        f"| `current_user` | `{db_context['current_user']}` |",
        f"| `session_user` | `{db_context['session_user']}` |",
        f"| `SELECT public.candles_1m` | `{db_context['privileges']['select']}` |",
        f"| `INSERT public.candles_1m` | `{db_context['privileges']['insert']}` |",
        f"| `UPDATE public.candles_1m` | `{db_context['privileges']['update']}` |",
        f"| `DELETE public.candles_1m` | `{db_context['privileges']['delete']}` |",
        f"| `BTCUSDT rows` | `{inventory_payload['db_row_count']}` |",
        "",
        f"Venue limitation: {db_context['venue_provenance_limitations']}",
        "",
        "## Segment Detection",
        "",
        "The inventory uses the strict continuity rule `next_ts_ms - current_ts_ms == 60000`.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Exact-1m windows | {inventory_payload['segment_count']} |",
        f"| Windows >= 720 rows | {inventory_payload['windows_ge_threshold']['720']} |",
        f"| Windows >= 1440 rows | {inventory_payload['windows_ge_threshold']['1440']} |",
        f"| Windows >= 2880 rows | {inventory_payload['windows_ge_threshold']['2880']} |",
        f"| Longest window rows | {inventory_payload['longest_window_rows']} |",
        "",
        "## Window Selection",
        "",
        f"Selection kept all exact-1m windows with at least `{MIN_WINDOW_ROWS}` rows, then capped to the top `{MAX_SELECTED_WINDOWS}` by row count.",
        "",
        "| Selected windows | Value |",
        "|------------------|-------|",
        f"| Count | {selected_count} |",
        f"| Smallest selected rows | {min(item['row_count'] for item in window_runs)} |",
        f"| Largest selected rows | {max(item['row_count'] for item in window_runs)} |",
        f"| Total selected rows | {sum(item['row_count'] for item in window_runs)} |",
        f"| Total selected hours | {round(sum(item['row_count'] for item in window_runs) / 60.0, 2)} |",
        "",
        f"Window inventory JSON: `{WINDOW_INVENTORY_PATH.relative_to(REPO_ROOT).as_posix()}`",
        f"Selection manifest JSON: `{SELECTION_MANIFEST_PATH.relative_to(REPO_ROOT).as_posix()}`",
        "",
        "## Produced Multi-Window Dataset",
        "",
        f"Raw and calibrated datasets were written under `{OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix()}/window_###/`.",
        "Each window contains `candles.jsonl`, `dataset_spec.json`, and `provenance_manifest.json`; the calibrated derivative lives under `regime_calibrated/` with its own `candles.jsonl`, `dataset_spec.json`, and `calibration_manifest.json`.",
        "",
        "## Regime/Calibration Method",
        "",
        "Each selected window was calibrated independently using the predeclared distribution-based ATR p75 rule from #3145/#3147.",
        "",
        "- ADX thresholds remain at committed values.",
        "- ATR threshold is derived from that window's ATR(14) distribution.",
        "- Regime labels are `estimated=true`.",
        "- Evidence class is controlled_lab_evidence only.",
        "- Windows are independent fragments, not one continuous market history.",
        "",
        "## Replay Results by Window",
        "",
        "| Window | Segment | Rows | ATR p75 | Signals | Closed Trades | Win Rate | Profit Factor | Net PnL Quote | Fees Quote | Sample Verdict | Gate |",
        "|--------|---------|------|---------|---------|---------------|----------|---------------|----------------|------------|----------------|------|",
        *replay_rows,
        "",
        "## Aggregate Economics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total windows | {aggregate['total_windows']} |",
        f"| Successful windows | {aggregate['successful_windows']} |",
        f"| Failed windows | {aggregate['failed_windows']} |",
        f"| Windows with trades | {aggregate['windows_with_trades']} |",
        f"| Total closed trades | {aggregate['total_closed_trades']} |",
        f"| Total wins | {aggregate['total_wins']} |",
        f"| Total losses | {aggregate['total_losses']} |",
        f"| Aggregate win rate | {aggregate['aggregate_win_rate']:.4f} |",
        f"| Aggregate gross PnL quote | {aggregate['aggregate_gross_pnl_quote']:.2f} |",
        f"| Aggregate net PnL quote | {aggregate['aggregate_net_pnl_quote']:.2f} |",
        f"| Aggregate fees quote | {aggregate['aggregate_fees_total_quote']:.2f} |",
        f"| Aggregate fee-adjusted return R | {aggregate['aggregate_fee_adjusted_return_r']:.6f} |",
        "",
        "## Replay + Economics Result",
        "",
        f"Machine-readable economics: `{EXECUTION_ECONOMICS_PATH.relative_to(REPO_ROOT).as_posix()}`",
        f"Machine-readable evidence packet: `{EVIDENCE_PACKET_PATH.relative_to(REPO_ROOT).as_posix()}`",
        "",
        "## Sample-Size Verdict",
        "",
        f"**{aggregate['sample_size_verdict']}**",
        "",
        f"Rule: PASS only if total closed trades >= 20 and at least 3 windows have trades. Actual: total closed trades = {aggregate['total_closed_trades']}, windows with trades = {aggregate['windows_with_trades']}.",
        "",
        "## Decision",
        "",
        (
            "Do not promote. This slice produces controlled_lab_evidence only. "
            "No production config change, no strategy change, no runtime capture, no Live-Go, no Echtgeld-Go, LR remains NO-GO."
        ),
        "",
        "## Recommended Next Step",
        "",
        aggregate["recommendation"],
        "",
        "## Safety Boundaries",
        "",
        "| Boundary | Status |",
        "|----------|--------|",
        f"| Evidence class | `{EVIDENCE_CLASS}` |",
        f"| LR status | `{LR_STATUS}` |",
        "| Live-Go | false |",
        "| Echtgeld-Go | false |",
        "| DB writes | none |",
        "| Runtime capture | none |",
        "| Docker actions | none |",
        "| Production config change | none |",
        "| Strategy change | none |",
        "",
        "## Limitations",
        "",
        "- controlled_lab_evidence only.",
        "- Windows are independent fragments, not one continuous market history.",
        "- public.candles_1m has no source/venue column; MEXC attribution for this BTCUSDT series is inherited from prior same-venue evidence and runtime canon, not from per-row DB labels.",
        "- No production config change.",
        "- No strategy change.",
        "- No runtime capture.",
        "- No Live-Go, no Echtgeld-Go, LR remains NO-GO.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    db_context = fetch_db_context()
    rows = fetch_btcusdt_rows()
    inventory = segment_rows(rows)
    if (
        len([item for item in inventory if int(item["row_count"]) >= MIN_WINDOW_ROWS])
        < 2
    ):
        raise RuntimeError("Fewer than 2 usable contiguous windows exist")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPLAY_ROOT.mkdir(parents=True, exist_ok=True)

    inventory_payload = build_window_inventory(rows, inventory)
    selection_manifest = build_selection_manifest(inventory)
    write_json(WINDOW_INVENTORY_PATH, inventory_payload)
    write_json(SELECTION_MANIFEST_PATH, selection_manifest)

    indexed_inventory = {int(item["segment_id"]): item for item in inventory}
    window_runs: list[dict[str, Any]] = []

    for selected in selection_manifest["selected_windows"]:
        window_id = str(selected["window_id"])
        source_segment_id = int(selected["source_segment_id"])
        inventory_item = indexed_inventory[source_segment_id]
        start_idx = int(inventory_item["start_idx"])
        end_idx = int(inventory_item["end_idx"])
        source_rows = rows[start_idx : end_idx + 1]

        raw_bundle = export_window_bundle(
            db_context=db_context,
            window_meta={
                **selected,
                "gap_before_ms": inventory_item.get("gap_before_ms"),
                "gap_after_ms": inventory_item.get("gap_after_ms"),
            },
            source_rows=source_rows,
            window_id=window_id,
        )
        raw_dicts = raw_bundle["raw_rows"]
        atr_threshold, atr_stats = compute_window_atr_threshold(raw_dicts)
        derived_rows, distribution = build_derived_candles(raw_dicts, atr_threshold)
        calibrated_bundle = write_calibrated_bundle(
            raw_bundle=raw_bundle,
            atr_threshold=atr_threshold,
            atr_stats=atr_stats,
            derived_rows=derived_rows,
            distribution=dict(distribution),
        )
        replay_result = run_window_replay(window_id, calibrated_bundle["derived_path"])
        window_runs.append(
            {
                "window_id": window_id,
                "row_count": int(selected["row_count"]),
                "duration_hours": float(selected["duration_hours"]),
                "start_ts_ms": int(selected["start_ts_ms"]),
                "end_ts_ms": int(selected["end_ts_ms"]),
                "start_utc": selected["start_utc"],
                "end_utc": selected["end_utc"],
                "raw": raw_bundle,
                "calibrated": calibrated_bundle,
                "replay": replay_result,
            }
        )

    infrastructure_failures = sum(
        1 for item in window_runs if item["replay"]["status"] != "ok"
    )
    if infrastructure_failures > len(window_runs) // 2:
        raise RuntimeError("Most selected windows failed for infrastructure reasons")

    aggregate = aggregate_results(window_runs)
    execution_json = build_execution_economics_json(window_runs, aggregate)
    evidence_packet_json = build_evidence_packet_json(window_runs, aggregate)
    evidence_doc = build_markdown_doc(
        db_context=db_context,
        inventory_payload=inventory_payload,
        selection_manifest=selection_manifest,
        window_runs=window_runs,
        aggregate=aggregate,
    )

    write_json(EXECUTION_ECONOMICS_PATH, execution_json)
    write_json(EVIDENCE_PACKET_PATH, evidence_packet_json)
    write_text(EVIDENCE_DOC_PATH, evidence_doc)

    print(f"Selected windows: {len(window_runs)}")
    print(f"Successful windows: {aggregate['successful_windows']}")
    print(f"Failed windows: {aggregate['failed_windows']}")
    print(f"Total closed trades: {aggregate['total_closed_trades']}")
    print(f"Sample-size verdict: {aggregate['sample_size_verdict']}")
    print(f"Status: {aggregate['overall_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
