"""Read-only offline manifest reconcile for Binance market_data (#4004)."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.market_data.historical_common import HistoricalProbeError, write_json

SCHEMA_VERSION = "binance_archive_reconcile.v1"
SYMBOL = "BTCUSDT"
VENUE = "binance"
TIMEFRAME = "1m"
PRODUCT = "spot"
FAILED_VERDICTS = frozenset(
    {"SOURCE_INVALID", "CHECKSUM_FAILED", "SOURCE_UNAVAILABLE"}
)
EXPECTED = {
    "earliest_month": "2017-08",
    "latest_month": "2026-06",
    "total_months": 107,
    "strict_complete": 81,
    "partial_usable": 26,
    "failed": 0,
    "total_candles": 4_656_799,
    "base_window_count": 106,
    "stress_v2_window_count": 2,
    "total_window_count": 108,
}


class ReconcileError(HistoricalProbeError):
    """Offline reconcile failure."""


class NetworkAttemptError(ReconcileError):
    """Network access attempted during offline reconcile."""


def _guard_network_import() -> None:
    import urllib.request as urllib_request

    if getattr(urllib_request, "_cdb_offline_reconcile_guard", False):
        return

    original = urllib_request.urlopen  # noqa: F841 — preserved for future restore hook

    def _blocked(*args: Any, **kwargs: Any):
        raise NetworkAttemptError(
            "HOLD_OFFLINE_RECONCILE_NETWORK_ATTEMPT: network access blocked"
        )

    urllib_request.urlopen = _blocked  # type: ignore[assignment]
    urllib_request._cdb_offline_reconcile_guard = True  # type: ignore[attr-defined]


def _month_dirs(base: Path) -> list[str]:
    if not base.is_dir():
        return []
    return sorted(child.name for child in base.iterdir() if child.is_dir())


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def reconcile_market_data_root(
    *,
    market_data_root: Path,
    output_dir: Path,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _guard_network_import()
    root = market_data_root.resolve()
    output_dir = output_dir.resolve()
    if not root.is_dir():
        raise ReconcileError(f"market_data root missing: {root}")
    if root in output_dir.parents or root == output_dir:
        raise ReconcileError("output_dir must not be inside market_data_root")
    output_dir.mkdir(parents=True, exist_ok=True)

    norm_base = root / "normalized" / VENUE / PRODUCT / SYMBOL / TIMEFRAME
    raw_base = root / "raw" / VENUE / PRODUCT / SYMBOL / TIMEFRAME
    enrich_base = root / "enriched" / VENUE / PRODUCT / SYMBOL / TIMEFRAME
    wb_manifest_path = (
        root
        / "window_bank"
        / VENUE
        / PRODUCT
        / SYMBOL
        / TIMEFRAME
        / "window_bank_manifest.json"
    )
    import_manifest_path = root / "manifests" / "binance_btcusdt_1m_full_import.json"

    raw_months = _month_dirs(raw_base)
    norm_months = _month_dirs(norm_base)
    enrich_months = _month_dirs(enrich_base)

    contradictions: list[str] = []
    missing_files: list[str] = []
    month_rows: list[dict[str, Any]] = []
    strict_complete = 0
    partial_usable = 0
    failed = 0
    total_candles = 0

    for month in norm_months:
        month_dir = norm_base / month
        quality_path = month_dir / "quality_report.json"
        gap_path = month_dir / "gap_report.json"
        quality = _read_json(quality_path)
        if quality is None:
            missing_files.append(quality_path.relative_to(root).as_posix())
            failed += 1
            continue
        verdict = str(quality.get("verdict", "SOURCE_INVALID"))
        gaps = quality.get("gaps") or {}
        candles = int(gaps.get("actual_candles", 0))
        total_candles += candles
        if verdict == "STRICT_COMPLETE":
            strict_complete += 1
        elif verdict == "PARTIAL_USABLE":
            partial_usable += 1
        elif verdict in FAILED_VERDICTS:
            failed += 1
        else:
            contradictions.append(f"unknown verdict {verdict} for month {month}")
        month_rows.append(
            {
                "month": month,
                "verdict": verdict,
                "candles": candles,
                "quality_report": quality_path.relative_to(root).as_posix(),
                "gap_report_present": gap_path.is_file(),
            }
        )

    quality_report_count = sum(
        1 for _ in root.rglob("quality_report.json") if _.is_file()
    )
    dataset_spec_count = sum(1 for _ in root.rglob("dataset_spec.json") if _.is_file())
    provenance_manifest_count = sum(
        1 for _ in root.rglob("provenance_manifest.json") if _.is_file()
    )

    wb_payload = _read_json(wb_manifest_path)
    if wb_payload is None:
        missing_files.append(wb_manifest_path.relative_to(root).as_posix())
        base_window_count = 0
        stress_v2_window_count = 0
        total_window_count = 0
    else:
        windows = wb_payload.get("windows") or []
        total_window_count = len(windows)
        stress_meta = wb_payload.get("stress_v2_rebuild") or {}
        written_v2 = stress_meta.get("written_v2") or []
        stress_v2_window_count = len(written_v2)
        base_window_count = total_window_count - stress_v2_window_count

    stale = _read_json(import_manifest_path)
    stale_summary: dict[str, Any] = {"present": stale is not None}
    if stale is not None:
        coverage = stale.get("coverage") or {}
        stale_summary.update(
            {
                "import_status": stale.get("import_status"),
                "month_count": coverage.get("month_count")
                or (stale.get("summary") or {}).get("total_months"),
                "strict_complete": coverage.get("strict_complete_months")
                or (stale.get("summary") or {}).get("strict_complete"),
                "partial": coverage.get("partial_months")
                or (stale.get("summary") or {}).get("partial"),
                "total_candles": coverage.get("total_candles"),
                "actual_range": stale.get("actual_range"),
            }
        )

    earliest_month = norm_months[0] if norm_months else None
    latest_month = norm_months[-1] if norm_months else None
    scan_as_of_utc = datetime.now(tz=UTC).isoformat()

    report_core = {
        "schema_version": SCHEMA_VERSION,
        "market_data_root": str(root),
        "scan_as_of_utc": scan_as_of_utc,
        "venue": VENUE,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "product": PRODUCT,
        "earliest_month": earliest_month,
        "latest_month": latest_month,
        "total_months": len(norm_months),
        "strict_complete": strict_complete,
        "partial_usable": partial_usable,
        "failed": failed,
        "total_candles": total_candles,
        "raw_month_coverage": len(raw_months),
        "normalized_month_coverage": len(norm_months),
        "enriched_month_coverage": len(enrich_months),
        "quality_report_count": quality_report_count,
        "dataset_spec_count": dataset_spec_count,
        "provenance_manifest_count": provenance_manifest_count,
        "base_window_count": base_window_count,
        "stress_v2_window_count": stress_v2_window_count,
        "total_window_count": total_window_count,
        "stale_manifest_summary": stale_summary,
        "contradictions": contradictions,
        "missing_files": missing_files,
        "limitations": [
            "read-only reconcile; stale import manifest not rewritten",
            "month verdicts sourced from normalized quality_report.json",
        ],
    }

    expected_values = expected or EXPECTED
    contract_mismatches: list[str] = []
    checks = {
        "earliest_month": earliest_month,
        "latest_month": latest_month,
        "total_months": len(norm_months),
        "strict_complete": strict_complete,
        "partial_usable": partial_usable,
        "failed": failed,
        "total_candles": total_candles,
        "base_window_count": base_window_count,
        "stress_v2_window_count": stress_v2_window_count,
        "total_window_count": total_window_count,
    }
    for key, expected_value in expected_values.items():
        if key not in checks:
            continue
        if checks[key] != expected_value:
            contract_mismatches.append(
                f"{key}: expected {expected_value}, got {checks[key]}"
            )

    verdict = "PASS"
    if contradictions or missing_files or contract_mismatches:
        verdict = "HOLD_DATASET_CONTRACT_MISMATCH"

    report_core["contract_mismatches"] = contract_mismatches
    report_core["verdict"] = verdict
    report_core["deterministic_fingerprint"] = _fingerprint_payload(
        {k: v for k, v in report_core.items() if k != "deterministic_fingerprint"}
    )

    reconciled_import = {
        "schema_version": "binance_full_import.reconciled.v1",
        "reconcile_schema_version": SCHEMA_VERSION,
        "campaign_id": stale.get("campaign_id") if stale else None,
        "source_sha": stale.get("source_sha") if stale else None,
        "symbol": SYMBOL,
        "venue": VENUE,
        "timeframe": TIMEFRAME,
        "product": PRODUCT,
        "actual_range": {"start_month": earliest_month, "end_month": latest_month},
        "import_status": "FULL_IMPORT_PARTIAL" if partial_usable else "FULL_IMPORT_PASS",
        "evidence_class": "historical_cross_venue_research",
        "lr_status": "NO-GO",
        "coverage": {
            "month_count": len(norm_months),
            "strict_complete_months": strict_complete,
            "partial_months": partial_usable,
            "failed_months": failed,
            "total_candles": total_candles,
        },
        "months": month_rows,
        "reconciled_at_utc": scan_as_of_utc,
        "deterministic_fingerprint": report_core["deterministic_fingerprint"],
    }

    write_json(output_dir / "reconciled_import_manifest.json", reconciled_import)
    write_json(output_dir / "reconcile_report.json", report_core)
    md_lines = [
        "# Binance Archive Reconcile Report",
        "",
        f"- **market_data_root:** `{root}`",
        f"- **scan_as_of_utc:** {scan_as_of_utc}",
        f"- **verdict:** `{verdict}`",
        f"- **months:** {len(norm_months)} ({earliest_month} .. {latest_month})",
        f"- **strict / partial / failed:** {strict_complete} / {partial_usable} / {failed}",
        f"- **total_candles:** {total_candles}",
        f"- **windows:** {total_window_count} ({base_window_count} base + {stress_v2_window_count} stress_v2)",
        "",
        "## Stale import manifest (comparison only)",
        "",
        "```json",
        json.dumps(stale_summary, indent=2, sort_keys=True),
        "```",
        "",
    ]
    if contract_mismatches:
        md_lines.extend(["## Contract mismatches", ""] + [f"- {item}" for item in contract_mismatches])
    if missing_files:
        md_lines.extend(["", "## Missing files", ""] + [f"- {item}" for item in missing_files])
    (output_dir / "reconcile_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return report_core


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Binance archive reconcile")
    parser.add_argument("--market-data-root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        report = reconcile_market_data_root(
            market_data_root=Path(args.market_data_root),
            output_dir=Path(args.output_dir),
        )
        print(json.dumps({"verdict": report["verdict"]}, indent=2))
        return 0 if report["verdict"] == "PASS" else 2
    except NetworkAttemptError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except ReconcileError as exc:
        print(f"RECONCILE_ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
