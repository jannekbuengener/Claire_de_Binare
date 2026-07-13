"""Shared helpers for agent-facing ARVP test map (#3824)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

ARVP_TEST_MAP_JSON = (
    REPO_ROOT
    / ".github"
    / "control-plane"
    / "generated"
    / "agent-arvp-test-map.json"
)

REQUIRED_SURFACES = frozenset(
    {
        "runtime_chain",
        "replay_paper_calibration",
        "campaign_supervisor",
        "scenario_packs",
        "window_qualification",
        "evidence_mapping",
        "negative_controls",
    }
)

P2_LIMITATIONS: tuple[str, ...] = (
    "Partial coverage only — not all ARVP tools or evidence lanes are mapped.",
    "Map lists P0/P1 contract tests from #3821–#3829; broader ARVP suites are out of scope.",
    "Missing mappings are surfaced explicitly; absence does not imply no tests exist.",
    "No coverage percentage or complete-coverage claim.",
    "Natural-paper runtime observation (#3893) is intentionally out of this map.",
)

CANONICAL_ARVP_TEST_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "surface": "runtime_chain",
        "behavior": "paper runtime chain SIGNAL→DECISION→ORDER→FILL via ChainDetector",
        "service": "tools/arvp_chain_detector",
        "test": "tests/unit/arvp/test_arvp_runtime_event_chain_contract.py",
        "fixtures": (
            "tests/fixtures/arvp/event_chain/complete_chain_paper_order.json",
            "tests/fixtures/arvp/event_chain/signal_only.json",
            "tests/fixtures/arvp/event_chain/signal_decision.json",
            "tests/fixtures/arvp/event_chain/signal_decision_order.json",
            "tests/fixtures/arvp/event_chain/malformed_missing_ts.json",
        ),
        "issue_ref": "#3821",
    },
    {
        "surface": "replay_paper_calibration",
        "behavior": "replay→paper reference→compare→calibration→ARVP gate regression",
        "service": "services/validation",
        "test": "tests/unit/arvp/test_arvp_calibration_gate_regression_contract.py",
        "fixtures": (
            "tests/fixtures/arvp/calibration/aligned_happy_path/replay_report.json",
            "tests/fixtures/arvp/calibration/aligned_happy_path/paper_reference_window.json",
        ),
        "issue_ref": "#3822",
    },
    {
        "surface": "campaign_supervisor",
        "behavior": "campaign supervisor terminal states, probe layer, GitHub reporter read-only",
        "service": "tools/arvp_campaign_supervisor",
        "test": "tests/unit/arvp/test_arvp_campaign_supervisor_state_machine_contract.py",
        "fixtures": (
            "tests/fixtures/arvp_campaigns/probe_set_complete_chain.json",
            "tests/fixtures/arvp_campaigns/probe_set_partial_chain.json",
            "tests/fixtures/arvp_campaigns/probe_set_all_ok_running.json",
            "tests/fixtures/arvp_campaigns/manifest_campaign_3.yaml",
        ),
        "issue_ref": "#3823",
    },
    {
        "surface": "scenario_packs",
        "behavior": "strategy×scenario-pack matrix fail-closed for unsupported combos",
        "service": "core/replay/scenario_packs",
        "test": "tests/unit/arvp/test_arvp_scenario_pack_matrix_contract.py",
        "fixtures": ("tests/fixtures/arvp/scenario_pack_matrix_v1.json",),
        "issue_ref": "#3826",
    },
    {
        "surface": "window_qualification",
        "behavior": "window cadence/gap/warmup and regime/paper availability qualification",
        "service": "cross-cutting",
        "test": "tests/unit/arvp/test_arvp_window_qualification_contract.py",
        "fixtures": ("tests/fixtures/arvp/window_qualification/cases_v1.json",),
        "issue_ref": "#3827",
    },
    {
        "surface": "evidence_mapping",
        "behavior": "harvester gaps/safety→profitability packet limitations without promotion",
        "service": "tools/evidence_harvester",
        "test": "tests/unit/arvp/test_arvp_evidence_harvester_mapping_contract.py",
        "fixtures": ("tests/fixtures/arvp/evidence_mapping/cases_v1.json",),
        "issue_ref": "#3828",
    },
    {
        "surface": "negative_controls",
        "behavior": "invalid/blocked runtime inputs produce no orders/fills/executor/DB writes",
        "service": "cross-cutting",
        "test": "tests/unit/arvp/test_arvp_runtime_negative_controls_contract.py",
        "fixtures": (
            "tests/fixtures/arvp/paper_runtime_stimulus_btcusdt_breakout_v1.json",
        ),
        "issue_ref": "#3829",
    },
    {
        "surface": "parallel_ledger_isolation",
        "behavior": "mixed correlation_ledger windows export per strategy/bot/config without cross-rows",
        "service": "core/replay/paper_reference_window_export",
        "test": "tests/unit/arvp/test_arvp_parallel_ledger_evidence_isolation_contract_3911.py",
        "fixtures": (
            "tests/fixtures/arvp/parallel_ledger_isolation/mixed_pb1_donchian_chains_v1.json",
        ),
        "issue_ref": "#3911",
    },
)

KNOWN_UNMAPPED_ARVP_SURFACES: tuple[dict[str, str], ...] = (
    {
        "surface": "arvp_probe_layer",
        "reason": "probe layer covered indirectly via campaign supervisor contracts",
    },
    {
        "surface": "arvp_github_reporter",
        "reason": "reporter read-only semantics covered in campaign supervisor tests",
    },
    {
        "surface": "natural_paper_observation",
        "reason": "runtime observation lane (#3893) is out of P2 test-map scope",
    },
    {
        "surface": "broader_arvp_unit_suite",
        "reason": "non-contract ARVP tests exist but are not indexed here",
    },
)


@dataclass(frozen=True)
class ArvpTestMapFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class ArvpTestMapScan:
    missing_test_paths: tuple[str, ...]
    missing_fixture_paths: tuple[str, ...]
    missing_required_surfaces: tuple[str, ...]
    limitations: tuple[str, ...]
    findings: tuple[ArvpTestMapFinding, ...] = field(default_factory=tuple)


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface": entry["surface"],
        "behavior": entry["behavior"],
        "service": entry["service"],
        "test": entry["test"],
        "fixtures": list(entry.get("fixtures") or ()),
        "issue_ref": entry.get("issue_ref", ""),
    }


def scan_arvp_test_map_entries(
    entries: tuple[dict[str, Any], ...],
) -> ArvpTestMapScan:
    missing_tests: list[str] = []
    missing_fixtures: list[str] = []
    findings: list[ArvpTestMapFinding] = []

    for entry in entries:
        test_path = REPO_ROOT / entry["test"]
        if not test_path.is_file():
            missing_tests.append(entry["test"])
            findings.append(
                ArvpTestMapFinding(kind="missing_test_path", detail=entry["test"])
            )
        for fixture_rel in entry.get("fixtures") or ():
            fixture_path = REPO_ROOT / fixture_rel
            if not fixture_path.is_file():
                missing_fixtures.append(fixture_rel)
                findings.append(
                    ArvpTestMapFinding(kind="missing_fixture_path", detail=fixture_rel)
                )

    mapped_surfaces = {entry["surface"] for entry in entries}
    missing_surfaces = sorted(REQUIRED_SURFACES - mapped_surfaces)
    for surface in missing_surfaces:
        findings.append(
            ArvpTestMapFinding(kind="missing_required_surface", detail=surface)
        )

    return ArvpTestMapScan(
        missing_test_paths=tuple(missing_tests),
        missing_fixture_paths=tuple(missing_fixtures),
        missing_required_surfaces=tuple(missing_surfaces),
        limitations=P2_LIMITATIONS,
        findings=tuple(findings),
    )


def build_arvp_test_map() -> dict[str, Any]:
    canonical = [_normalize_entry(entry) for entry in CANONICAL_ARVP_TEST_ENTRIES]
    scan = scan_arvp_test_map_entries(CANONICAL_ARVP_TEST_ENTRIES)
    mapped_surfaces = sorted({entry["surface"] for entry in canonical})

    return {
        "schema_version": "1",
        "coverage": "partial",
        "catalog_scope": "agent-facing-arvp-test-map-p2",
        "limitations": list(P2_LIMITATIONS),
        "required_surfaces": sorted(REQUIRED_SURFACES),
        "mapped_surfaces": mapped_surfaces,
        "missing_required_surfaces": list(scan.missing_required_surfaces),
        "known_unmapped_arvp_surfaces": [
            dict(item) for item in KNOWN_UNMAPPED_ARVP_SURFACES
        ],
        "entry_count": len(canonical),
        "canonical_entry_count": len(canonical),
        "entries": canonical,
    }


def load_committed_arvp_test_map() -> dict[str, Any]:
    return json.loads(ARVP_TEST_MAP_JSON.read_text(encoding="utf-8"))
