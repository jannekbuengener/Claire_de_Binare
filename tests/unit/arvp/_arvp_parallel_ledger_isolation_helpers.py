"""Shared helpers for parallel strategy ledger/evidence isolation (#3911)."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.replay.paper_reference_window_export import (
    PaperReferenceExportError,
    build_export_request,
    export_paper_reference_window,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

MIXED_FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "arvp"
    / "parallel_ledger_isolation"
    / "mixed_pb1_donchian_chains_v1.json"
)

PARALLEL_BOT_IDS = {
    "primary_breakout_v1": "np-pb1-parallel-01",
    "donchian_breakout_v1": "np-donchian-parallel-01",
}

PARALLEL_CONFIG_HASHES = {
    "primary_breakout_v1": "cfg-pb1-parallel-v1",
    "donchian_breakout_v1": "cfg-donchian-parallel-v1",
}


@dataclass(frozen=True, slots=True)
class ParallelIsolationFixture:
    case_id: str
    symbol: str
    start_ts_ms_utc: int
    end_ts_ms_utc: int
    strategies: dict[str, dict[str, str]]
    ledger_rows: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class StrategyExportResult:
    strategy_id: str
    bot_id: str
    config_hash: str
    payload: dict[str, Any]


def load_parallel_isolation_fixture(
    path: Path = MIXED_FIXTURE_PATH,
) -> ParallelIsolationFixture:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ParallelIsolationFixture(
        case_id=str(raw["case_id"]),
        symbol=str(raw["symbol"]),
        start_ts_ms_utc=int(raw["start_ts_ms_utc"]),
        end_ts_ms_utc=int(raw["end_ts_ms_utc"]),
        strategies=dict(raw["strategies"]),
        ledger_rows=list(raw["ledger_rows"]),
    )


def build_strategy_export_request(
    fixture: ParallelIsolationFixture,
    *,
    strategy_id: str,
    bot_id: str | None = None,
    config_hash: str | None = None,
) -> Any:
    return build_export_request(
        strategy_id=strategy_id,
        symbol=fixture.symbol,
        start_ts_ms_utc=fixture.start_ts_ms_utc,
        end_ts_ms_utc=fixture.end_ts_ms_utc,
        extracted_by="arvp-parallel-isolation-contract-test",
        extracted_at_utc="2026-07-09T00:00:00+00:00",
        source_query_intent=(
            "parallel strategy isolation guard; filter by strategy_id/bot_id/config_hash"
        ),
        bot_id=bot_id,
        config_hash=config_hash,
    )


def ledger_rows_copy(fixture: ParallelIsolationFixture) -> list[dict[str, Any]]:
    return deepcopy(fixture.ledger_rows)


def export_strategy_evidence(
    fixture: ParallelIsolationFixture,
    *,
    strategy_id: str,
    bot_id: str | None = None,
    config_hash: str | None = None,
) -> StrategyExportResult:
    request = build_strategy_export_request(
        fixture,
        strategy_id=strategy_id,
        bot_id=bot_id,
        config_hash=config_hash,
    )
    payload = export_paper_reference_window(
        request=request, rows=ledger_rows_copy(fixture)
    )
    resolved_bot_id = bot_id or PARALLEL_BOT_IDS[strategy_id]
    resolved_config_hash = config_hash or PARALLEL_CONFIG_HASHES[strategy_id]
    return StrategyExportResult(
        strategy_id=strategy_id,
        bot_id=resolved_bot_id,
        config_hash=resolved_config_hash,
        payload=payload,
    )


def export_strategy_evidence_or_raise(
    fixture: ParallelIsolationFixture,
    *,
    strategy_id: str,
    bot_id: str | None = None,
    config_hash: str | None = None,
) -> StrategyExportResult | PaperReferenceExportError:
    try:
        return export_strategy_evidence(
            fixture,
            strategy_id=strategy_id,
            bot_id=bot_id,
            config_hash=config_hash,
        )
    except PaperReferenceExportError as exc:
        return exc


def correlation_ids_in_payload(payload: dict[str, Any]) -> set[str]:
    return {str(event["correlation_id"]) for event in payload.get("events", [])}


def strategy_ids_in_payload(payload: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for event in payload.get("events", []):
        payload_obj = event.get("payload") or {}
        strategy_id = payload_obj.get("strategy_id")
        if isinstance(strategy_id, str) and strategy_id.strip():
            found.add(strategy_id.strip())
    return found


def count_paper_fills(payload: dict[str, Any]) -> int:
    return sum(
        1
        for event in payload.get("events", [])
        if event.get("event_type") == "FILL"
        and str(event.get("order_id", "")).startswith("paper_")
    )


def assert_zero_cross_strategy_rows(
    result: StrategyExportResult,
    *,
    foreign_correlation_ids: set[str],
    foreign_strategy_ids: set[str],
) -> None:
    observed_correlation_ids = correlation_ids_in_payload(result.payload)
    assert not observed_correlation_ids & foreign_correlation_ids
    observed_strategy_ids = strategy_ids_in_payload(result.payload)
    assert observed_strategy_ids == {result.strategy_id}
    assert foreign_strategy_ids.isdisjoint(observed_strategy_ids)
