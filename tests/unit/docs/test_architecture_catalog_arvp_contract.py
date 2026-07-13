"""Stable architecture-catalog contracts for ARVP validation pipeline (#4023/#4026)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHITECTURE_MAP = REPO_ROOT / "knowledge" / "ARCHITECTURE_MAP.md"
SERVICE_CATALOG = REPO_ROOT / "knowledge" / "governance" / "SERVICE_CATALOG.md"

LIBRARY_PATHS = (
    "services/validation/arvp_candidate_evidence_assembler.py",
    "services/validation/profitability_league_table_report_assembler.py",
)

TOOL_PATHS = (
    "tools/arvp_vacation/candidate_evidence_assembly.py",
    "tools/arvp_vacation/league_table_report.py",
)

CONTRACT_PATHS = (
    "docs/contracts/arvp_strategy_metrics.v1.schema.json",
    "docs/contracts/profitability_evidence_packet.v1.schema.json",
    "docs/contracts/profitability_league_table_report.v1.schema.json",
)

SCORER_PATH = "services/validation/profitability_league_scorer.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("relative_path", LIBRARY_PATHS)
def test_architecture_map_references_arvp_library_paths(relative_path: str) -> None:
    content = _read(ARCHITECTURE_MAP)
    assert relative_path in content


@pytest.mark.parametrize("relative_path", LIBRARY_PATHS)
def test_service_catalog_references_arvp_library_paths(relative_path: str) -> None:
    content = _read(SERVICE_CATALOG)
    assert relative_path in content


@pytest.mark.parametrize("relative_path", LIBRARY_PATHS + TOOL_PATHS + CONTRACT_PATHS)
def test_documented_paths_exist(relative_path: str) -> None:
    assert (REPO_ROOT / relative_path).is_file()


def test_scorer_and_report_assembler_are_distinct_in_catalog() -> None:
    catalog = _read(SERVICE_CATALOG)
    assert SCORER_PATH in catalog
    assert "profitability_league_table_report_assembler.py" in catalog
    assert "not interchangeable with the scorer CLI" in catalog


def test_architecture_map_distinguishes_scorer_and_governance_assembler() -> None:
    content = _read(ARCHITECTURE_MAP)
    assert SCORER_PATH in content
    assert "profitability_league_table_report_assembler.py" in content
    assert "Distinct from standalone" in content
