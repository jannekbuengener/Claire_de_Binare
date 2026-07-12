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
from typing import Any, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.market_data.binance_full_archive_import import (
    REPO_ROOT as IMPORT_REPO,
    _enriched_dir,
    _normalized_dir,
)
from tools.market_data.historical_common import (
    HistoricalProbeError,
    month_bounds,
    parse_year_month,
    sha256_file,
    utc_now_iso,
    write_json,
)
from tools.market_data.assign_regime_offline import regime_distribution

WINDOW_BANK_SCHEMA = "binance_window_bank.v1"
EXCLUDED_VERDICTS = frozenset(
    {"SOURCE_INVALID", "SOURCE_UNAVAILABLE", "CHECKSUM_FAILED"}
)
OVERLAP_CLASSES = frozenset(
    {"monthly", "quarterly", "yearly", "stress", "smoke", "pilot"}
)
PURPOSES = frozenset(
    {"development", "validation", "out_of_sample", "stress"}
)


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
        repo_root
        / "artifacts"
        / "market_data"
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


def _load_month_candles(repo_root: Path, month: str, *, enriched: bool = True) -> list[dict[str, Any]]:
    base = _enriched_dir(repo_root, month) if enriched else _normalized_dir(repo_root, month)
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


def _write_window_dataset(
    repo_root: Path,
    window: WindowSpec,
    candles: list[dict[str, Any]],
) -> Path:
    window_dir = (
        repo_root
        / "artifacts"
        / "market_data"
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
) -> list[WindowSpec]:
    """Data-driven stress windows (deduplicated by fingerprint)."""
    all_candles: list[dict[str, Any]] = []
    month_by_ts: dict[int, str] = {}
    for month in sorted(months):
        for row in _load_month_candles(repo_root, month):
            ts = int(row["ts_ms"])
            all_candles.append(row)
            month_by_ts[ts] = month
    if len(all_candles) < window_minutes:
        return []

    def _window_metrics(chunk: list[dict[str, Any]]) -> dict[str, float]:
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

    best: dict[str, tuple[float, int]] = {
        "max_drawdown": (0.0, 0),
        "max_vol": (0.0, 0),
        "min_vol": (float("inf"), 0),
        "max_uptrend": (float("-inf"), 0),
        "max_downtrend": (float("inf"), 0),
    }

    for start_idx in range(0, len(all_candles) - window_minutes, window_minutes // 4):
        chunk = all_candles[start_idx : start_idx + window_minutes]
        m = _window_metrics(chunk)
        if m["max_dd"] > best["max_drawdown"][0]:
            best["max_drawdown"] = (m["max_dd"], start_idx)
        if m["vol"] > best["max_vol"][0]:
            best["max_vol"] = (m["vol"], start_idx)
        if m["vol"] < best["min_vol"][0]:
            best["min_vol"] = (m["vol"], start_idx)
        if m["trend"] > best["max_uptrend"][0]:
            best["max_uptrend"] = (m["trend"], start_idx)
        if m["trend"] < best["max_downtrend"][0]:
            best["max_downtrend"] = (m["trend"], start_idx)

    stress_defs = [
        ("stress_max_drawdown", "max_drawdown"),
        ("stress_max_volatility", "max_vol"),
        ("stress_min_volatility", "min_vol"),
        ("stress_max_uptrend", "max_uptrend"),
        ("stress_max_downtrend", "max_downtrend"),
    ]
    windows: list[WindowSpec] = []
    seen_starts: set[int] = set()
    for wid, key in stress_defs:
        _, start_idx = best[key]
        if start_idx in seen_starts:
            continue
        seen_starts.add(start_idx)
        chunk = all_candles[start_idx : start_idx + window_minutes]
        source_months = sorted(
            {month_by_ts.get(int(c["ts_ms"]), "") for c in chunk} - {""}
        )
        windows.append(
            WindowSpec(
                window_id=f"binance_1m_{wid}",
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
    months = strict_complete_months(manifest)
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
        elif spec.overlap_class in {"quarterly", "yearly", "stress"}:
            candles = []
            for m in spec.source_months:
                candles.extend(_load_month_candles(repo_root, m))
            if spec.overlap_class == "stress":
                candles = _slice_candles(candles, spec.start_ts_ms, spec.end_ts_ms)
        else:
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


def build_vacation_manifest(
    bank: dict[str, Any],
    repo_root: Path = IMPORT_REPO,
    *,
    pilot_only: bool = False,
    smoke_only: bool = False,
) -> Path:
    source_sha = bank.get("source_sha", "RUNTIME_RESOLVE")
    ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
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
            str(
                Path(bank_root)
                / "binance_1m_month_2026_06"
            ).replace("\\", "/")
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
    parser.add_argument("--manifest-path", default=None)
    args = parser.parse_args()

    try:
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
                "windows": json.loads(
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
                else [],
            }
            path = build_vacation_manifest(
                bank_stub,
                pilot_only=args.pilot_manifest,
                smoke_only=args.smoke_manifest,
            )
            print(json.dumps({"vacation_manifest": str(path)}, indent=2))
            return 0

        if args.run_campaign:
            mpath = Path(args.manifest_path) if args.manifest_path else (
                REPO_ROOT
                / "artifacts"
                / "arvp_vacation"
                / "manifests"
                / "binance_historical_campaign_3990.yaml"
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
