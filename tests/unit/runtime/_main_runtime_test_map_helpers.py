"""Shared helpers for agent-facing main runtime test map (#3841)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

MAIN_RUNTIME_TEST_MAP_JSON = (
    REPO_ROOT
    / ".github"
    / "control-plane"
    / "generated"
    / "agent-main-runtime-test-map.json"
)

REQUIRED_SURFACES = frozenset(
    {"market", "regime", "signal", "risk", "execution", "validation"}
)

P2_LIMITATIONS: tuple[str, ...] = (
    "Partial coverage only — not all runtime services have contract-test entries.",
    "Eventflow surfaces allocation, candles, ws, and db_writer are not mapped here.",
    "Map lists primary P0/P1 contract tests; broader unit suites are out of scope.",
    "Missing mappings are surfaced explicitly; absence does not imply no tests exist.",
    "No coverage percentage or complete-coverage claim.",
)

# Canonical behavior → service → test → fixture rows (source of truth).
CANONICAL_RUNTIME_TEST_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "surface": "market",
        "behavior": "ingest candles and publish market_state with fail-closed validation",
        "service": "cdb_market",
        "test": "tests/unit/market/test_market_candles_ingestion_contract.py",
        "fixtures": (),
        "issue_ref": "#3831",
    },
    {
        "surface": "regime",
        "behavior": "classify market regime and emit UNKNOWN on invalid candles",
        "service": "cdb_regime",
        "test": "tests/unit/regime/test_regime_service_contract.py",
        "fixtures": (),
        "issue_ref": "#3832",
    },
    {
        "surface": "regime",
        "behavior": "regime_id semantics and risk-boundary mapping",
        "service": "cdb_regime",
        "test": "tests/unit/regime/test_regime_id_semantics_contract.py",
        "fixtures": (),
        "issue_ref": "#3832",
    },
    {
        "surface": "signal",
        "behavior": "signal core fail-closed and config hash contract",
        "service": "cdb_signal",
        "test": "tests/unit/signal/test_signal_core_contract.py",
        "fixtures": (),
        "issue_ref": "#3833",
    },
    {
        "surface": "signal",
        "behavior": "optimizer stub contract and unknown adapter fail-closed",
        "service": "cdb_signal",
        "test": "tests/unit/signal/test_optimizer_contract.py",
        "fixtures": (),
        "issue_ref": "#3833",
    },
    {
        "surface": "signal",
        "behavior": "market classifier warmup and UNKNOWN emit contract",
        "service": "cdb_signal",
        "test": "tests/unit/signal/test_market_classifier_contract.py",
        "fixtures": (),
        "issue_ref": "#3832",
    },
    {
        "surface": "risk",
        "behavior": "decision matrix allow/block semantics",
        "service": "cdb_risk",
        "test": "tests/unit/risk/test_decision_matrix_contract.py",
        "fixtures": (),
        "issue_ref": "#3834",
    },
    {
        "surface": "risk",
        "behavior": "reason-code contract and fail-closed blocking",
        "service": "cdb_risk",
        "test": "tests/unit/risk/test_reason_codes_contract.py",
        "fixtures": (),
        "issue_ref": "#3834",
    },
    {
        "surface": "risk",
        "behavior": "live-trading gate blocks without explicit confirmation",
        "service": "cdb_risk",
        "test": "tests/unit/risk/test_live_trading_gate_contract.py",
        "fixtures": (),
        "issue_ref": "#3834",
    },
    {
        "surface": "execution",
        "behavior": "paper/live boundary and mock-trading fail-closed",
        "service": "cdb_execution",
        "test": "tests/unit/execution/test_execution_boundary_contract.py",
        "fixtures": (),
        "issue_ref": "#3835",
    },
    {
        "surface": "execution",
        "behavior": "order state-machine transitions",
        "service": "cdb_execution",
        "test": "tests/unit/execution/test_state_machine_contract.py",
        "fixtures": (),
        "issue_ref": "#3835",
    },
    {
        "surface": "execution",
        "behavior": "paper order result contract",
        "service": "cdb_execution",
        "test": "tests/unit/execution/test_paper_order_contract.py",
        "fixtures": (),
        "issue_ref": "#3835",
    },
    {
        "surface": "validation",
        "behavior": "profitability validation regression and evidence-only scoring",
        "service": "cdb_validation",
        "test": "tests/unit/validation/test_profitability_validation_regression_contract.py",
        "fixtures": (),
        "issue_ref": "#3840",
    },
    {
        "surface": "validation",
        "behavior": "stimulus regime signal contract",
        "service": "cdb_validation",
        "test": "tests/unit/validation/test_stimulus_regime_signal_contract.py",
        "fixtures": (),
        "issue_ref": "#3840",
    },
)

# P1 cross-cutting entries included for agent orientation (not required surfaces).
SUPPLEMENTAL_RUNTIME_TEST_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "surface": "runtime_flow",
        "behavior": "fixture-based market→signal→risk→paper execution chain",
        "service": "cross-cutting",
        "test": "tests/unit/runtime/test_main_runtime_flow_contract.py",
        "fixtures": (
            "tests/fixtures/runtime_flow/market_tick_happy.json",
            "tests/fixtures/runtime_flow/stale_context.json",
            "tests/fixtures/runtime_flow/blocked_regime.json",
            "tests/fixtures/runtime_flow/invalid_execution_order.json",
        ),
        "issue_ref": "#3838",
    },
    {
        "surface": "runtime_io",
        "behavior": "redis/postgres/ledger IO fail-closed contracts",
        "service": "cross-cutting",
        "test": "tests/unit/utils/test_runtime_io_ledger_contract.py",
        "fixtures": (),
        "issue_ref": "#3836",
    },
    {
        "surface": "config_safety",
        "behavior": "trading mode, feature flags, LR NO-GO canon",
        "service": "cross-cutting",
        "test": "tests/unit/config/test_config_safety_gate_contract.py",
        "fixtures": (),
        "issue_ref": "#3837",
    },
    {
        "surface": "health_metrics",
        "behavior": "health/status/metrics without Live-Go markers",
        "service": "cross-cutting",
        "test": "tests/unit/runtime/test_health_metrics_contract.py",
        "fixtures": (),
        "issue_ref": "#3839",
    },
)

KNOWN_UNMAPPED_RUNTIME_SURFACES: tuple[dict[str, str], ...] = (
    {
        "service": "cdb_candles",
        "reason": "no dedicated P0/P1 contract-test entry in this map",
    },
    {
        "service": "cdb_allocation",
        "reason": "no dedicated P0/P1 contract-test entry in this map",
    },
    {
        "service": "cdb_ws",
        "reason": "RED stack feed; no dedicated main-runtime contract entry",
    },
    {
        "service": "cdb_db_writer",
        "reason": "persistence consumer; covered indirectly via IO contract",
    },
)


@dataclass(frozen=True)
class RuntimeTestMapFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class RuntimeTestMapScan:
    missing_test_paths: tuple[str, ...]
    missing_fixture_paths: tuple[str, ...]
    missing_required_surfaces: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[RuntimeTestMapFinding, ...] = field(default_factory=tuple)


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface": entry["surface"],
        "behavior": entry["behavior"],
        "service": entry["service"],
        "test": entry["test"],
        "fixtures": list(entry.get("fixtures") or ()),
        "issue_ref": entry.get("issue_ref", ""),
    }


def scan_runtime_test_map_entries(
    entries: tuple[dict[str, Any], ...],
) -> RuntimeTestMapScan:
    missing_tests: list[str] = []
    missing_fixtures: list[str] = []
    findings: list[RuntimeTestMapFinding] = []

    for entry in entries:
        test_path = REPO_ROOT / entry["test"]
        if not test_path.is_file():
            missing_tests.append(entry["test"])
            findings.append(
                RuntimeTestMapFinding(
                    kind="missing_test_path",
                    detail=entry["test"],
                )
            )
        for fixture_rel in entry.get("fixtures") or ():
            fixture_path = REPO_ROOT / fixture_rel
            if not fixture_path.is_file():
                missing_fixtures.append(fixture_rel)
                findings.append(
                    RuntimeTestMapFinding(
                        kind="missing_fixture_path",
                        detail=fixture_rel,
                    )
                )

    mapped_surfaces = {entry["surface"] for entry in entries}
    missing_surfaces = sorted(REQUIRED_SURFACES - mapped_surfaces)
    for surface in missing_surfaces:
        findings.append(
            RuntimeTestMapFinding(
                kind="missing_required_surface",
                detail=surface,
            )
        )

    return RuntimeTestMapScan(
        missing_test_paths=tuple(missing_tests),
        missing_fixture_paths=tuple(missing_fixtures),
        missing_required_surfaces=tuple(missing_surfaces),
        limitations=P2_LIMITATIONS,
        findings=tuple(findings),
    )


def build_main_runtime_test_map() -> dict[str, Any]:
    canonical = [_normalize_entry(entry) for entry in CANONICAL_RUNTIME_TEST_ENTRIES]
    supplemental = [
        _normalize_entry(entry) for entry in SUPPLEMENTAL_RUNTIME_TEST_ENTRIES
    ]
    all_entries = tuple(CANONICAL_RUNTIME_TEST_ENTRIES) + tuple(
        SUPPLEMENTAL_RUNTIME_TEST_ENTRIES
    )
    scan = scan_runtime_test_map_entries(all_entries)
    mapped_surfaces = sorted({entry["surface"] for entry in canonical})

    return {
        "schema_version": "1",
        "coverage": "partial",
        "catalog_scope": "agent-facing-main-runtime-test-map-p2",
        "limitations": list(P2_LIMITATIONS),
        "required_surfaces": sorted(REQUIRED_SURFACES),
        "mapped_surfaces": mapped_surfaces,
        "missing_required_surfaces": list(scan.missing_required_surfaces),
        "known_unmapped_runtime_surfaces": [
            dict(item) for item in KNOWN_UNMAPPED_RUNTIME_SURFACES
        ],
        "entry_count": len(canonical) + len(supplemental),
        "canonical_entry_count": len(canonical),
        "supplemental_entry_count": len(supplemental),
        "entries": canonical + supplemental,
    }


def load_committed_main_runtime_test_map() -> dict[str, Any]:
    return json.loads(MAIN_RUNTIME_TEST_MAP_JSON.read_text(encoding="utf-8"))
