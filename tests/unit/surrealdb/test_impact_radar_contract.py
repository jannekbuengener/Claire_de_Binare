"""Impact Radar contract tests (#3778).

Refs #3771. Consolidates fixture-backed contracts for compute_impact,
cdb_context_impact MCP handler, and drift-radar adjacency. Covers output
buckets (files, tests, docs, contracts, decisions, gates), scope-growth and
missing-child-issue signals, CLI/MCP alignment, and deterministic outputs.
In-memory/fixture only — no live SurrealDB in CI.

Optional local_only: dependency_edge records in a real SurrealDB instance are
not required for standard CI; use tests/fixtures/surrealdb/impact/ instead.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.mcp.context_bridge import cdb_context_impact_handler
from tools.surrealdb.context_impact_radar import ImpactRadarInput, compute_impact

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "surrealdb" / "impact" / "sample_impact_input.json"

CONTRACT_PATH_PREFIXES = (
    "docs/contracts/",
    "core/contracts/",
    "knowledge/contracts/",
)

IMPACT_PAYLOAD_BUCKETS = frozenset(
    {
        "files",
        "tests",
        "docs",
        "contracts",
        "decisions",
        "gates",
    }
)

IMPACT_CORE_FIELDS = frozenset(
    {
        "schema_version",
        "impact_id",
        "target_refs",
        "impact_level",
        "impact_type",
        "affected_artifacts",
        "affected_symbols",
        "affected_tests",
        "affected_docs",
        "affected_decisions",
        "affected_evidence",
        "affected_memory_refs_read_only",
        "graph_paths",
        "gate_risks",
        "confidence",
        "required_validation",
        "stop_conditions",
    }
)

REQUIRED_VALIDATION_SIGNAL_FIELDS = frozenset(
    {
        "scope_growth_signals",
        "missing_child_issue_signals",
    }
)


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def fixture_to_input(data: dict[str, Any]) -> ImpactRadarInput:
    return ImpactRadarInput(
        target_paths=tuple(data.get("target_paths", [])),
        target_symbols=tuple(data.get("target_symbols", [])),
        target_issue=data.get("target_issue"),
        target_concepts=tuple(data.get("target_concepts", [])),
        operation_mode=data.get("operation_mode", "read_only"),
        dependency_edges=tuple(data.get("dependency_edges", [])),
        code_symbols=tuple(data.get("code_symbols", [])),
        test_cases=tuple(data.get("test_cases", [])),
        artifacts=tuple(data.get("artifacts", [])),
    )


def derive_impact_output_buckets(payload: dict[str, Any]) -> dict[str, list[Any]]:
    """Derive separate visibility buckets from a canonical impact payload."""
    artifacts = payload.get("affected_artifacts", [])
    contracts: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    doc_paths = {d.get("path") for d in payload.get("affected_docs", [])}

    for art in artifacts:
        source = art.get("source_path") or art.get("path") or ""
        atype = art.get("artifact_type", "")
        is_contract = atype == "contract" or any(
            source.startswith(prefix) for prefix in CONTRACT_PATH_PREFIXES
        )
        is_doc = source in doc_paths or atype == "documentation"
        if is_contract:
            contracts.append(art)
        elif not is_doc:
            files.append(art)

    return {
        "files": files,
        "tests": list(payload.get("affected_tests", [])),
        "docs": list(payload.get("affected_docs", [])),
        "contracts": contracts,
        "decisions": list(payload.get("affected_decisions", [])),
        "gates": list(payload.get("gate_risks", [])),
    }


@pytest.fixture
def impact_fixture() -> dict[str, Any]:
    return _load_fixture()


@pytest.fixture
def impact_payload(impact_fixture: dict[str, Any]) -> dict[str, Any]:
    report = compute_impact(fixture_to_input(impact_fixture))
    return report.to_payload()


# ---------------------------------------------------------------------------
# Fixture-backed baseline
# ---------------------------------------------------------------------------


def test_fixture_loads_without_live_surrealdb(impact_fixture: dict[str, Any]) -> None:
    assert impact_fixture["target_paths"] == ["core/utils/clock.py"]
    assert impact_fixture["target_issue"] == "#3778"
    assert len(impact_fixture["dependency_edges"]) >= 1


def test_fixture_produces_ok_impact_payload(impact_payload: dict[str, Any]) -> None:
    assert IMPACT_CORE_FIELDS.issubset(set(impact_payload.keys()))
    assert impact_payload["schema_version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Output buckets
# ---------------------------------------------------------------------------


def test_impact_output_buckets_separate_visibility(
    impact_payload: dict[str, Any],
) -> None:
    buckets = derive_impact_output_buckets(impact_payload)
    assert IMPACT_PAYLOAD_BUCKETS == frozenset(buckets.keys())

    for name, items in buckets.items():
        assert isinstance(items, list), f"bucket {name} must be a list"

    assert any("clock.py" in (f.get("source_path") or "") for f in buckets["files"])
    assert any("test_clock.py" in (t.get("source_path") or "") for t in buckets["tests"])
    assert any("impact-radar-contract" in (d.get("path") or "") for d in buckets["docs"])
    assert any(
        "db_record_evidence.schema.json" in (c.get("source_path") or "")
        for c in buckets["contracts"]
    )
    assert any("ledger" in d for d in buckets["decisions"])
    assert len(buckets["gates"]) >= 0


def test_affected_tests_visible_from_fixture_edges(impact_payload: dict[str, Any]) -> None:
    tests = impact_payload["affected_tests"]
    paths = {t["source_path"] for t in tests}
    assert "tests/unit/core/test_clock.py" in paths
    assert "tests/unit/other/test_other.py" not in paths


def test_affected_docs_visible_separately(impact_payload: dict[str, Any]) -> None:
    docs = impact_payload["affected_docs"]
    assert len(docs) >= 1
    assert all("path" in d for d in docs)
    doc_paths = {d["path"] for d in docs}
    assert "docs/surrealdb/context-impact-radar-contract-v1.md" in doc_paths


def test_affected_contracts_visible_via_artifact_bucket(
    impact_payload: dict[str, Any],
) -> None:
    buckets = derive_impact_output_buckets(impact_payload)
    contract_paths = {c.get("source_path") for c in buckets["contracts"]}
    assert "docs/contracts/context_tooling/db_record_evidence.schema.json" in contract_paths


def test_affected_gates_visible_separately(impact_payload: dict[str, Any]) -> None:
    gate_risks = impact_payload["gate_risks"]
    assert isinstance(gate_risks, list)
    assert "contract_drift_possible" in gate_risks or "risk_surface_touched" in gate_risks


# ---------------------------------------------------------------------------
# Scope-growth and missing-child-issue signals
# ---------------------------------------------------------------------------


def test_scope_growth_signal_from_dependency_propagation(
    impact_fixture: dict[str, Any],
) -> None:
    report = compute_impact(fixture_to_input(impact_fixture))
    signals = report.required_validation.get("scope_growth_signals", [])
    assert isinstance(signals, list)
    assert len(signals) >= 1
    assert any("scope_growth:" in s for s in signals)
    assert any("services/signal/models.py" in s for s in signals)


def test_scope_growth_absent_when_no_propagation() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/readme.md",),
        artifacts=(
            {
                "artifact_id": "a1",
                "artifact_type": "documentation",
                "source_path": "docs/surrealdb/readme.md",
            },
        ),
    )
    report = compute_impact(inp)
    assert report.required_validation["scope_growth_signals"] == []


def test_missing_child_issue_signal_on_multi_domain_write() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py", "docs/surrealdb/readme.md"),
        target_issue="#3771",
        operation_mode="write (code/docs)",
        artifacts=(
            {
                "artifact_id": "a1",
                "artifact_type": "source",
                "source_path": "core/utils/clock.py",
            },
            {
                "artifact_id": "a2",
                "artifact_type": "documentation",
                "source_path": "docs/surrealdb/readme.md",
            },
        ),
    )
    report = compute_impact(inp)
    signals = report.required_validation["missing_child_issue_signals"]
    assert len(signals) == 1
    assert "missing_child_issue:" in signals[0]
    assert "#3771" in signals[0]


def test_missing_child_issue_absent_for_read_only_single_domain() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        target_issue="#3778",
        operation_mode="read_only",
    )
    report = compute_impact(inp)
    assert report.required_validation["missing_child_issue_signals"] == []


def test_required_validation_includes_signal_fields(impact_payload: dict[str, Any]) -> None:
    rv = impact_payload["required_validation"]
    assert REQUIRED_VALIDATION_SIGNAL_FIELDS.issubset(set(rv.keys()))


# ---------------------------------------------------------------------------
# MCP / CLI alignment
# ---------------------------------------------------------------------------


def test_mcp_handler_aligns_with_compute_impact_path_only() -> None:
    """MCP handler mirrors compute_impact for path-only inputs (no graph data)."""
    kwargs = {
        "target_paths": ["core/utils/clock.py"],
        "target_symbols": ["utcnow"],
        "target_issue": "#3778",
        "target_concepts": ["impact", "radar"],
        "operation_mode": "write (code/docs)",
    }
    core_payload = compute_impact(
        ImpactRadarInput(
            target_paths=tuple(kwargs["target_paths"]),
            target_symbols=tuple(kwargs["target_symbols"]),
            target_issue=kwargs["target_issue"],
            target_concepts=tuple(kwargs["target_concepts"]),
            operation_mode=kwargs["operation_mode"],
        )
    ).to_payload()
    mcp_result = cdb_context_impact_handler(**kwargs)
    assert mcp_result["status"] == "ok"
    mcp_impact = mcp_result["impact"]

    for field in IMPACT_CORE_FIELDS:
        assert field in mcp_impact, f"MCP impact missing field {field}"

    for signal_field in REQUIRED_VALIDATION_SIGNAL_FIELDS:
        assert signal_field in mcp_impact["required_validation"]

    assert core_payload["impact_id"] == mcp_impact["impact_id"]
    assert core_payload["impact_level"] == mcp_impact["impact_level"]
    assert core_payload["impact_type"] == mcp_impact["impact_type"]
    assert core_payload["gate_risks"] == mcp_impact["gate_risks"]

    core_buckets = derive_impact_output_buckets(core_payload)
    mcp_buckets = derive_impact_output_buckets(mcp_impact)
    assert set(core_buckets.keys()) == set(mcp_buckets.keys())


def test_mcp_handler_guardrails_present() -> None:
    result = cdb_context_impact_handler(
        target_paths=["core/utils/clock.py"],
        operation_mode="read_only",
    )
    assert result["tool"] == "cdb_context_impact"
    assert isinstance(result.get("guardrails"), list)
    assert len(result["guardrails"]) >= 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_deterministic_output_from_fixture(impact_fixture: dict[str, Any]) -> None:
    inp = fixture_to_input(impact_fixture)
    p1 = compute_impact(inp).to_payload()
    p2 = compute_impact(inp).to_payload()
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


def test_deterministic_mcp_output_from_fixture(impact_fixture: dict[str, Any]) -> None:
    kwargs = {
        "target_paths": impact_fixture["target_paths"],
        "target_symbols": impact_fixture["target_symbols"],
        "target_issue": impact_fixture["target_issue"],
        "target_concepts": impact_fixture["target_concepts"],
        "operation_mode": impact_fixture["operation_mode"],
    }
    r1 = cdb_context_impact_handler(**kwargs)
    r2 = cdb_context_impact_handler(**kwargs)
    assert r1["status"] == "ok" and r2["status"] == "ok"
    assert r1["impact"]["impact_id"] == r2["impact"]["impact_id"]


# ---------------------------------------------------------------------------
# Safety: no secrets / no auto-issue creation semantics
# ---------------------------------------------------------------------------


def test_fixture_output_contains_no_secret_indicators(impact_payload: dict[str, Any]) -> None:
    blob = json.dumps(impact_payload)
    for indicator in (
        "api_key",
        "api_secret",
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "MEXC_API_KEY",
        "MEXC_API_SECRET",
    ):
        assert indicator not in blob
