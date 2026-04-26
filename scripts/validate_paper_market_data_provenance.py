#!/usr/bin/env python3
"""
Validate paper-run market_data provenance (Issue #1908).

Reads PaperRunner JSONL logs (logs/events/events_YYYYMMDD.jsonl) and fails closed if:
- any market_data event is missing the required `source` field
- any market_data event has a `source` not in the allowed set

Optional: also flags known synthetic signal injections (core_flow_smoke_probe) as a warning
because they can contaminate paper-evidence even without market-data contamination.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class MarketDataStats:
    total: int
    by_source: dict[str, int]
    by_symbol: dict[str, int]
    first_ts_ms_by_symbol: dict[str, int]
    last_ts_ms_by_symbol: dict[str, int]


def _iter_jsonl_files(events_dir: Path, *, glob: str) -> list[Path]:
    if not events_dir.exists():
        raise FileNotFoundError(f"events dir not found: {events_dir}")
    files = sorted(events_dir.glob(glob))
    if not files:
        raise FileNotFoundError(f"no files matched {glob} in {events_dir}")
    return files


def _iter_json_lines(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no} invalid JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError(f"{path}:{line_no} expected object, got {type(parsed).__name__}")
            yield parsed


def _coerce_int(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except ValueError:
            return None
    return None


def analyze_events(
    paths: list[Path],
    *,
    allowed_sources: set[str],
    strict: bool,
) -> tuple[MarketDataStats, list[str], list[str]]:
    by_source: Counter[str] = Counter()
    by_symbol: Counter[str] = Counter()
    first_ts_ms_by_symbol: dict[str, int] = {}
    last_ts_ms_by_symbol: dict[str, int] = {}

    failures: list[str] = []
    warnings: list[str] = []
    total_market_data = 0

    for path in paths:
        for entry in _iter_json_lines(path):
            channel = entry.get("channel")
            event = entry.get("event")
            if channel is None or event is None:
                continue
            if channel != "market_data" and channel != "signals":
                continue
            if not isinstance(event, dict):
                continue

            if channel == "signals":
                reason = event.get("reason")
                if reason == "core_flow_smoke_probe":
                    warnings.append(
                        f"{path.name}: synthetic signal injection detected (reason=core_flow_smoke_probe)"
                    )
                continue

            # market_data validation
            total_market_data += 1
            source = event.get("source")
            symbol = event.get("symbol")
            ts_ms = _coerce_int(event.get("ts_ms"))

            if not isinstance(source, str) or not source.strip():
                failures.append(f"{path.name}: market_data missing/invalid source: {source!r}")
                continue
            source = source.strip()

            if strict and source not in allowed_sources:
                failures.append(f"{path.name}: market_data disallowed source={source!r}")

            by_source[source] += 1

            if isinstance(symbol, str) and symbol.strip():
                sym = symbol.strip().upper()
                by_symbol[sym] += 1
                if ts_ms is not None:
                    if sym not in first_ts_ms_by_symbol:
                        first_ts_ms_by_symbol[sym] = ts_ms
                        last_ts_ms_by_symbol[sym] = ts_ms
                    else:
                        first_ts_ms_by_symbol[sym] = min(first_ts_ms_by_symbol[sym], ts_ms)
                        last_ts_ms_by_symbol[sym] = max(last_ts_ms_by_symbol[sym], ts_ms)

    stats = MarketDataStats(
        total=total_market_data,
        by_source=dict(by_source),
        by_symbol=dict(by_symbol),
        first_ts_ms_by_symbol=first_ts_ms_by_symbol,
        last_ts_ms_by_symbol=last_ts_ms_by_symbol,
    )
    return stats, failures, warnings


def _format_dict(d: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(d.items(), key=lambda kv: (-int(kv[1]), kv[0])))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validator for paper-run market_data provenance (reads PaperRunner JSONL)."
    )
    parser.add_argument(
        "--events-dir",
        type=Path,
        default=Path("logs/events"),
        help="Directory with PaperRunner JSONL logs (default: logs/events).",
    )
    parser.add_argument(
        "--glob",
        default="events_*.jsonl",
        help="Glob for JSONL files inside --events-dir (default: events_*.jsonl).",
    )
    parser.add_argument(
        "--allow-source",
        action="append",
        default=[],
        help="Allowed market_data source value. Repeatable. Example: --allow-source mexc",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any market_data source is not explicitly allowed (recommended).",
    )
    args = parser.parse_args(argv)

    allowed_sources = {s.strip() for s in args.allow_source if s and s.strip()}
    if args.strict and not allowed_sources:
        raise SystemExit("--strict requires at least one --allow-source")

    paths = _iter_jsonl_files(args.events_dir, glob=args.glob)
    stats, failures, warnings = analyze_events(
        paths, allowed_sources=allowed_sources, strict=args.strict
    )

    print("paper_market_data_provenance_validator")
    print(f"files={len(paths)} market_data_total={stats.total}")
    print(f"by_source: {_format_dict(stats.by_source)}" if stats.by_source else "by_source: (none)")
    print(f"by_symbol: {_format_dict(stats.by_symbol)}" if stats.by_symbol else "by_symbol: (none)")

    if stats.first_ts_ms_by_symbol:
        for sym in sorted(stats.first_ts_ms_by_symbol):
            print(
                f"symbol_window {sym}: "
                f"first_ts_ms={stats.first_ts_ms_by_symbol[sym]} "
                f"last_ts_ms={stats.last_ts_ms_by_symbol.get(sym)}"
            )

    if warnings:
        print("\nWARNINGS:")
        for w in warnings[:50]:
            print(f"- {w}")
        if len(warnings) > 50:
            print(f"- ... ({len(warnings) - 50} more)")

    if failures:
        print("\nFAILURES:")
        for f in failures[:100]:
            print(f"- {f}")
        if len(failures) > 100:
            print(f"- ... ({len(failures) - 100} more)")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

