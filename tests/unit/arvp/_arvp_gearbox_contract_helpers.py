"""Shared paths for ARVP gearbox design contract tests (#3913)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = REPO_ROOT / "docs" / "contracts"
DESIGN_DOC = (
    REPO_ROOT / "docs" / "design" / "arvp_gearbox_design_contracts_3913.md"
)

GEARBOX_SCHEMAS: tuple[tuple[str, Path, Path], ...] = (
    (
        "strategy_gear_registry.v1",
        CONTRACTS_DIR / "strategy_gear_registry.v1.schema.json",
        CONTRACTS_DIR / "examples" / "strategy_gear_registry_valid.json",
    ),
    (
        "selector_decision.v1",
        CONTRACTS_DIR / "selector_decision.v1.schema.json",
        CONTRACTS_DIR / "examples" / "selector_decision_valid.json",
    ),
    (
        "gear_reason_codes.v1",
        CONTRACTS_DIR / "gear_reason_codes.v1.schema.json",
        CONTRACTS_DIR / "examples" / "gear_reason_codes_valid.json",
    ),
    (
        "protective_idle.v1",
        CONTRACTS_DIR / "protective_idle.v1.schema.json",
        CONTRACTS_DIR / "examples" / "protective_idle_valid.json",
    ),
    (
        "loop_boundary.v1",
        CONTRACTS_DIR / "loop_boundary.v1.schema.json",
        CONTRACTS_DIR / "examples" / "loop_boundary_valid.json",
    ),
)

REQUIRED_REASON_CODES: frozenset[str] = frozenset(
    {
        "SELECTED",
        "PARKED",
        "BLOCKED",
        "IDLE",
        "EVIDENCE_GAP",
        "RISK_BLOCKED",
        "REGIME_MISMATCH",
        "NOT_RUNTIME_READY",
    }
)
