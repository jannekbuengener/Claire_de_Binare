"""Unit tests for Impact Radar v1 (#2019, #2108)."""

from __future__ import annotations

import pytest

from tools.surrealdb.context_impact_radar import (
    ImpactRadarInput,
    ImpactReport,
    compute_impact,
)

# ── Fixture builders ────────────────────────────────────────────────────────


def _make_artifact(
    artifact_id: str,
    artifact_type: str,
    source_path: str,
    source_hash: str = "",
) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "source_path": source_path,
        "source_hash": source_hash,
    }


def _make_symbol(
    symbol_id: str,
    name: str,
    source_path: str,
    symbol_type: str = "function",
    qualified_name: str = "",
) -> dict:
    return {
        "symbol_id": symbol_id,
        "name": name,
        "qualified_name": qualified_name or name,
        "symbol_type": symbol_type,
        "source_path": source_path,
    }


def _make_edge(
    edge_id: str,
    from_id: str,
    to_id: str,
    edge_type: str = "contains",
    inferred: bool = False,
) -> dict:
    return {
        "edge_id": edge_id,
        "from_id": from_id,
        "to_id": to_id,
        "edge_type": edge_type,
        "source_path": None,
        "confidence": "high",
        "inferred": inferred,
    }


def _make_test_case(
    test_id: str,
    test_name: str,
    source_path: str,
    test_type: str = "unit",
) -> dict:
    return {
        "test_id": test_id,
        "test_name": test_name,
        "source_path": source_path,
        "test_type": test_type,
    }


# ── Basic input tests ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_empty_input_produces_low_impact() -> None:
    inp = ImpactRadarInput()
    result = compute_impact(inp)

    assert result.impact_level == "low"
    assert result.impact_type == "SOFT"
    assert result.confidence == "low"
    assert len(result.affected_artifacts) == 0
    assert len(result.gate_risks) == 0
    assert isinstance(result.impact_id, str)
    assert len(result.impact_id) == 16


@pytest.mark.unit
def test_docs_path_is_low_soft() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/some-doc.md",),
        artifacts=(
            _make_artifact("art-1", "documentation", "docs/surrealdb/some-doc.md"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "low"
    assert result.impact_type == "SOFT"
    assert len(result.affected_artifacts) == 1


@pytest.mark.unit
def test_core_path_is_medium_hard() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "medium"
    assert result.impact_type == "HARD"


@pytest.mark.unit
def test_services_path_is_high_hard() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/signal/service.py",),
        artifacts=(
            _make_artifact("art-1", "source", "services/signal/service.py"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "high"
    assert result.impact_type == "HARD"


@pytest.mark.unit
def test_governance_path_is_blocking() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/governance/CDB_AGENT_POLICY.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "knowledge/governance/CDB_AGENT_POLICY.md",
            ),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "blocking"


@pytest.mark.unit
def test_risk_service_path_is_blocking() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/risk/service.py",),
        artifacts=(
            _make_artifact("art-1", "source", "services/risk/service.py"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "blocking"


@pytest.mark.unit
def test_execution_service_path_is_blocking() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/execution/service.py",),
        artifacts=(
            _make_artifact("art-1", "source", "services/execution/service.py"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "blocking"


# ── Dependency edge tracing ─────────────────────────────────────────────────


@pytest.mark.unit
def test_edge_tracing_propagates_affected_symbols() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
            _make_artifact("art-2", "source", "services/signal/models.py"),
        ),
        code_symbols=(
            _make_symbol("sym-1", "utcnow", "core/utils/clock.py"),
            _make_symbol("sym-2", "Signal", "services/signal/models.py"),
        ),
        dependency_edges=(
            _make_edge("e-1", "core/utils/clock.py", "sym-1", "contains"),
            _make_edge(
                "e-2", "core/utils/clock.py", "services/signal/models.py",
                "imports",
            ),
        ),
    )
    result = compute_impact(inp)

    # clock.py is medium + hard, but signal/models.py is in the affected set
    # making the overall level high because services/signal/models.py is under
    # services/
    assert result.impact_level == "high"
    assert len(result.affected_symbols) == 2
    affected_sources = {s["source_path"] for s in result.affected_symbols}
    assert "core/utils/clock.py" in affected_sources
    assert "services/signal/models.py" in affected_sources


@pytest.mark.unit
def test_edge_tracing_shows_graph_paths() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        dependency_edges=(
            _make_edge(
                "e-1", "core/utils/clock.py",
                "services/signal/models.py", "imports",
            ),
            _make_edge(
                "e-2", "core/utils/clock.py",
                "core/utils/uuid_gen.py", "imports",
            ),
        ),
    )
    result = compute_impact(inp)

    assert len(result.graph_paths) >= 1
    for gp in result.graph_paths:
        assert "core/utils/clock.py" in gp


# ── Gate risk detection ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_governance_path_emits_governance_touched_risk() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/governance/CDB_CONSTITUTION.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "knowledge/governance/CDB_CONSTITUTION.md",
            ),
        ),
    )
    result = compute_impact(inp)

    assert "governance_touched" in result.gate_risks


@pytest.mark.unit
def test_risk_path_emits_risk_surface_risk() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/risk/service.py",),
        artifacts=(
            _make_artifact("art-1", "source", "services/risk/service.py"),
        ),
    )
    result = compute_impact(inp)

    assert "risk_surface_touched" in result.gate_risks


@pytest.mark.unit
def test_contract_path_emits_contract_drift_risk() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/contracts/market_data.schema.json",),
        artifacts=(
            _make_artifact(
                "art-1", "contract",
                "docs/contracts/market_data.schema.json",
            ),
        ),
    )
    result = compute_impact(inp)

    assert "contract_drift_possible" in result.gate_risks


@pytest.mark.unit
def test_lr_path_emits_lr_surface_risk() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
            ),
        ),
    )
    result = compute_impact(inp)

    assert "lr_surface_touched" in result.gate_risks


@ pytest.mark.unit
def test_secrets_path_emits_secrets_risk() -> None:
    inp = ImpactRadarInput(
        target_paths=("secrets/some.key",),
        artifacts=(
            _make_artifact("art-1", "secret", "secrets/some.key"),
        ),
    )
    result = compute_impact(inp)

    assert "secrets_surface_touched" in result.gate_risks


# ── Affected tests ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_affected_tests_from_path() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        test_cases=(
            _make_test_case("t-1", "test_utcnow", "tests/unit/core/test_clock.py"),
            _make_test_case("t-2", "test_other", "tests/unit/other/test_other.py"),
        ),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
        dependency_edges=(
            _make_edge(
                "e-1", "core/utils/clock.py",
                "tests/unit/core/test_clock.py", "imports",
            ),
        ),
    )
    result = compute_impact(inp)

    assert len(result.affected_tests) >= 1
    test_paths = {t["source_path"] for t in result.affected_tests}
    assert "tests/unit/core/test_clock.py" in test_paths


# ── Confidence ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_data_confidence_is_low() -> None:
    inp = ImpactRadarInput(target_paths=("core/utils/foo.py",))
    result = compute_impact(inp)

    assert result.confidence == "low"


@pytest.mark.unit
def test_inferred_edges_confidence_is_medium() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
        dependency_edges=(
            _make_edge("e-1", "core/utils/clock.py", "sym-1", "contains", inferred=True),
        ),
    )
    result = compute_impact(inp)

    assert result.confidence == "medium"


@pytest.mark.unit
def test_full_resolved_data_confidence_is_high() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
        code_symbols=(
            _make_symbol("sym-1", "utcnow", "core/utils/clock.py"),
        ),
        dependency_edges=(
            _make_edge("e-1", "core/utils/clock.py", "sym-1", "contains"),
        ),
    )
    result = compute_impact(inp)

    assert result.confidence == "high"


# ── Stop condition propagation ──────────────────────────────────────────────


@pytest.mark.unit
def test_write_mode_emits_s6_stop_condition() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/doc.md",),
        operation_mode="write (code/docs)",
    )
    result = compute_impact(inp)

    types = {sc["type"] for sc in result.stop_conditions}
    assert "write_requires_human_go" in types


@pytest.mark.unit
def test_blocking_impact_write_propagates_stop_conditions() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/governance/CDB_CONSTITUTION.md",),
        operation_mode="write (code/docs)",
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "knowledge/governance/CDB_CONSTITUTION.md",
            ),
        ),
    )
    result = compute_impact(inp)

    assert len(result.stop_conditions) >= 1
    types = {sc["type"] for sc in result.stop_conditions}
    assert "write_requires_human_go" in types


@pytest.mark.unit
def test_read_only_mode_no_write_stop_conditions() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/governance/CDB_CONSTITUTION.md",),
        operation_mode="read_only",
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "knowledge/governance/CDB_CONSTITUTION.md",
            ),
        ),
    )
    result = compute_impact(inp)

    types = {sc["type"] for sc in result.stop_conditions}
    assert "write_requires_human_go" not in types


# ── Required validation ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_required_validation_has_all_fields() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        operation_mode="write (code/docs)",
    )
    result = compute_impact(inp)

    rv = result.required_validation
    assert "docs_to_review" in rv
    assert "suggested_tests" in rv
    assert "evidence_to_collect" in rv
    assert "commands_to_consider" in rv
    assert "manual_review_needed" in rv
    assert "blocking_preconditions" in rv


@pytest.mark.unit
def test_hard_impact_write_requires_manual_review() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/signal/service.py",),
        operation_mode="write (code/docs)",
        artifacts=(
            _make_artifact("art-1", "source", "services/signal/service.py"),
        ),
    )
    result = compute_impact(inp)

    assert result.required_validation["manual_review_needed"] is True


@pytest.mark.unit
def test_blocking_precondition_for_blocking_impact() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/risk/service.py",),
        operation_mode="write (code/docs)",
        artifacts=(
            _make_artifact("art-1", "source", "services/risk/service.py"),
        ),
    )
    result = compute_impact(inp)

    blocking = result.required_validation["blocking_preconditions"]
    assert len(blocking) >= 1
    assert any("Blocking impact" in bp for bp in blocking)


# ── Determinism ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_determinism_same_input_same_output() -> None:
    def _build() -> ImpactRadarInput:
        return ImpactRadarInput(
            target_paths=("core/utils/clock.py", "services/signal/models.py"),
            target_issue="#2108",
            operation_mode="dry_run",
            artifacts=(
                _make_artifact("art-1", "source", "core/utils/clock.py"),
                _make_artifact("art-2", "source", "services/signal/models.py"),
            ),
            code_symbols=(
                _make_symbol("sym-1", "utcnow", "core/utils/clock.py"),
                _make_symbol("sym-2", "Signal", "services/signal/models.py"),
            ),
            dependency_edges=(
                _make_edge("e-1", "core/utils/clock.py", "sym-1", "contains"),
                _make_edge(
                    "e-2", "core/utils/clock.py",
                    "services/signal/models.py", "imports",
                ),
            ),
        )

    r1 = compute_impact(_build())
    r2 = compute_impact(_build())

    assert r1.impact_id == r2.impact_id
    assert r1.impact_level == r2.impact_level
    assert r1.impact_type == r2.impact_type
    assert r1.gate_risks == r2.gate_risks
    assert r1.confidence == r2.confidence
    assert r1.stop_conditions == r2.stop_conditions


@pytest.mark.unit
def test_deterministic_id_changes_with_input() -> None:
    r1 = compute_impact(ImpactRadarInput(target_paths=("a.py",)))
    r2 = compute_impact(ImpactRadarInput(target_paths=("b.py",)))
    r3 = compute_impact(ImpactRadarInput(target_paths=("a.py",), target_issue="#42"))

    assert r1.impact_id != r2.impact_id
    assert r1.impact_id != r3.impact_id


# ── Output format ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_to_payload_returns_dict_with_all_fields() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        target_symbols=("utcnow",),
        target_issue="#2108",
        operation_mode="read_only",
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
        code_symbols=(
            _make_symbol("sym-1", "utcnow", "core/utils/clock.py"),
        ),
    )
    result = compute_impact(inp)
    payload = result.to_payload()

    required_keys = {
        "schema_version", "impact_id", "target_refs", "impact_level",
        "impact_type", "affected_artifacts", "affected_symbols",
        "affected_tests", "affected_docs", "affected_decisions",
        "affected_evidence", "affected_memory_refs_read_only",
        "graph_paths", "gate_risks", "confidence", "required_validation",
        "stop_conditions",
    }
    assert required_keys.issubset(set(payload.keys()))
    assert payload["schema_version"] == "1.0.0"


# ── Target symbols / concepts ───────────────────────────────────────────────


@pytest.mark.unit
def test_target_symbols_in_refs() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        target_symbols=("utcnow", "now"),
    )
    result = compute_impact(inp)

    assert "symbol:utcnow" in result.target_refs
    assert "symbol:now" in result.target_refs


@pytest.mark.unit
def test_target_issue_in_refs() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        target_issue="#2108",
    )
    result = compute_impact(inp)

    assert "issue:#2108" in result.target_refs


# ── Affected docs / decisions / evidence / memory ───────────────────────────


@pytest.mark.unit
def test_doc_artifacts_in_affected_docs() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/impact-radar.md",),
        artifacts=(
            _make_artifact("art-1", "documentation", "docs/surrealdb/impact-radar.md"),
        ),
    )
    result = compute_impact(inp)

    assert len(result.affected_docs) >= 1
    assert any(
        "impact-radar.md" in d["path"] for d in result.affected_docs
    )


@pytest.mark.unit
def test_decision_paths_in_affected_decisions() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/agent_trust/ledger/some-event.yaml",),
        artifacts=(
            _make_artifact(
                "art-1", "decision",
                "knowledge/agent_trust/ledger/some-event.yaml",
            ),
        ),
    )
    result = compute_impact(inp)

    assert len(result.affected_decisions) >= 1


@pytest.mark.unit
def test_evidence_paths_in_affected_evidence() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/evidence/LR-030.md",),
        artifacts=(
            _make_artifact("art-1", "evidence", "docs/evidence/LR-030.md"),
        ),
    )
    result = compute_impact(inp)

    assert len(result.affected_evidence) >= 1


@pytest.mark.unit
def test_memory_paths_in_affected_memory() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/logs/sessions/session-log.md",),
        artifacts=(
            _make_artifact(
                "art-1", "log", "knowledge/logs/sessions/session-log.md",
            ),
        ),
    )
    result = compute_impact(inp)

    assert len(result.affected_memory_refs_read_only) >= 1


# ── Impact type edge cases ──────────────────────────────────────────────────


@pytest.mark.unit
def test_github_path_is_soft() -> None:
    inp = ImpactRadarInput(
        target_paths=(".github/workflows/ci.yml",),
        artifacts=(
            _make_artifact("art-1", "workflow", ".github/workflows/ci.yml"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_type == "SOFT"


@pytest.mark.unit
def test_tools_path_is_hard() -> None:
    inp = ImpactRadarInput(
        target_paths=("tools/surrealdb/context_indexer.py",),
        artifacts=(
            _make_artifact(
                "art-1", "source", "tools/surrealdb/context_indexer.py",
            ),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_type == "HARD"


# ── Suggested tests in required_validation ──────────────────────────────────


@pytest.mark.unit
def test_required_validation_has_suggested_tests_when_affected_tests_exist() -> (
    None
):
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
        test_cases=(
            _make_test_case("t-1", "test_utcnow", "tests/unit/core/test_clock.py"),
        ),
        dependency_edges=(
            _make_edge(
                "e-1", "core/utils/clock.py",
                "tests/unit/core/test_clock.py", "imports",
            ),
        ),
    )
    result = compute_impact(inp)

    rv = result.required_validation
    assert len(rv["suggested_tests"]) >= 1


@pytest.mark.unit
def test_required_validation_has_pytest_command_when_tests_exist() -> None:
    inp = ImpactRadarInput(
        target_paths=("core/utils/clock.py",),
        artifacts=(
            _make_artifact("art-1", "source", "core/utils/clock.py"),
        ),
        test_cases=(
            _make_test_case("t-1", "test_utcnow", "tests/unit/core/test_clock.py"),
        ),
        dependency_edges=(
            _make_edge(
                "e-1", "core/utils/clock.py",
                "tests/unit/core/test_clock.py", "imports",
            ),
        ),
    )
    result = compute_impact(inp)

    commands = result.required_validation["commands_to_consider"]
    assert any("pytest" in c for c in commands)


# ── ImpactReport is immutable ───────────────────────────────────────────────


@pytest.mark.unit
def test_impact_report_is_hashable() -> None:
    report = ImpactReport(
        impact_id="test",
        target_refs=(),
        impact_level="low",
        impact_type="SOFT",
        affected_artifacts=(),
        affected_symbols=(),
        affected_tests=(),
        affected_docs=(),
        affected_decisions=(),
        affected_evidence=(),
        affected_memory_refs_read_only=(),
        graph_paths=(),
        gate_risks=(),
        confidence="low",
        required_validation={},
        stop_conditions=(),
    )
    # frozenset/dict requires hashable; this should not raise
    _ = hash(report)


# ── Multiple paths ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_multiple_paths_highest_level_wins() -> None:
    inp = ImpactRadarInput(
        target_paths=(
            "docs/surrealdb/doc.md",
            "core/utils/clock.py",
            "services/signal/service.py",
        ),
        artifacts=(
            _make_artifact("art-1", "documentation", "docs/surrealdb/doc.md"),
            _make_artifact("art-2", "source", "core/utils/clock.py"),
            _make_artifact("art-3", "source", "services/signal/service.py"),
        ),
    )
    result = compute_impact(inp)

    assert result.impact_level == "high"
    assert result.impact_type == "HARD"
