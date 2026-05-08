"""Unit tests for Wave-19 Visual Control Room View Builder.

Issues:
    #2185 — [SURREALDB][CONTEXT][CONTROL-ROOM-TESTS] Add control room report tests
    Parent: #2179 (Wave-19 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/control_room_view_builder.py.
    All fixtures are inline — no file loading.
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No real datetime.now() — as_of is passed explicitly for determinism.

Coverage:
    - All 9 view types build successfully from a clean bundle.
    - build_all_views_v1 returns exactly 9 views.
    - view_id is deterministic (SHA-256-based, stable for same inputs).
    - Every view carries non-empty guardrails.
    - Every view carries export_formats.
    - Every view has write_allowed=False on all data sources.
    - Invalid view_type raises ControlRoomError.
    - Missing bundle.meta raises ControlRoomError.
    - Missing bundle.meta.scope_id raises ControlRoomError.
    - Bundle with no findings produces correct warnings.
    - knowledge_graph_view: nodes and edges extracted from bundle sources/deps.
    - architecture_map: modules extracted.
    - decision_chain_view: chain, open_decisions, superseded_count.
    - evidence_map: evidence_by_strength, expired_count, uncovered_decisions.
    - risk_surface_report: blocking_drift/contradiction counts.
    - stale_knowledge_view: actionable_stale_count, stale_by_type.
    - scope_drift_events: blocking/watch/info by_severity split.
    - agent_memory_view: by_trust, expired_count.
    - quality_score_dashboard: entries, worst_grade.
    - Guardrail assertions: no trading console, no runtime control, no live-go.
    - to_dict() structure: all required fields present.
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.surrealdb.control_room_view_builder import (
    GUARDRAILS,
    SCHEMA_VERSION,
    VIEW_TYPES,
    ControlRoomError,
    ControlRoomView,
    build_all_views_v1,
    build_control_room_view_v1,
)

_AS_OF = "2026-05-08T12:00:00+00:00"

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _minimal_bundle(scope_id: str = "test-scope") -> dict[str, Any]:
    """Minimal valid bundle with no findings."""
    return {"meta": {"scope_id": scope_id, "level": "system"}}


def _clean_bundle() -> dict[str, Any]:
    """Full clean bundle covering all view types."""
    return {
        "meta": {"scope_id": "wave19-test-scope", "level": "system"},
        "sources": [
            {
                "source_path": "core/risk/service.py",
                "has_documentation": True,
                "has_tests": True,
                "status": "current",
                "owner": "risk-team",
            },
            {
                "source_path": "services/execution/service.py",
                "has_documentation": True,
                "has_tests": True,
                "status": "current",
            },
        ],
        "decisions": [
            {
                "decision_id": "dec-001",
                "status": "current",
                "evidence_refs": ["ev-001"],
            },
            {
                "decision_id": "dec-002",
                "status": "open",
                "evidence_refs": [],
            },
            {
                "decision_id": "dec-003",
                "status": "superseded",
                "superseded_by": "dec-001",
                "evidence_refs": ["ev-001"],
            },
        ],
        "evidence_items": [
            {"evidence_id": "ev-001", "strength": "strong", "expired": False},
            {"evidence_id": "ev-002", "strength": "moderate", "expired": True},
        ],
        "dependency_edges": [
            {
                "edge_id": "edge-001",
                "from_source": "core/risk/service.py",
                "to_source": "services/execution/service.py",
                "confidence": "high",
            }
        ],
        "contradiction_findings": [
            {"contradiction_id": "c-001", "severity": "watch", "status": "open"},
        ],
        "stale_findings": [
            {"finding_id": "sf-001", "stale_type": "documentation", "status": "open"},
            {"finding_id": "sf-002", "stale_type": "evidence", "status": "refreshed"},
        ],
        "scope_drift_findings": [
            {
                "finding_id": "sdf-001",
                "drift_type": "path_drift",
                "severity": "watch",
                "status": "open",
                "required_action": "review",
                "human_go_required": True,
            },
        ],
        "memory_items": [
            {"memory_id": "m-001", "trust_level": "strong", "ttl_expired": False},
            {"memory_id": "m-002", "trust_level": "weak", "ttl_expired": True},
        ],
        "quality_scores": [
            {
                "scope_id": "wave19-test-scope",
                "overall_grade": "watch",
                "overall_score": 0.45,
                "blocking_dimensions": [],
                "watch_dimensions": ["freshness_score"],
                "scored_at": "2026-05-08T10:00:00+00:00",
            }
        ],
    }


def _blocking_bundle() -> dict[str, Any]:
    """Bundle with blocking findings."""
    return {
        "meta": {"scope_id": "blocking-scope", "level": "system"},
        "scope_drift_findings": [
            {"finding_id": "sdf-b1", "drift_type": "trading_scope", "severity": "blocking", "status": "open", "required_action": "stop", "human_go_required": True},
        ],
        "contradiction_findings": [
            {"contradiction_id": "c-b1", "severity": "blocking", "status": "open"},
        ],
        "quality_scores": [
            {"scope_id": "blocking-scope", "overall_grade": "blocking", "overall_score": 0.1, "blocking_dimensions": ["coverage_score"], "watch_dimensions": [], "scored_at": _AS_OF},
        ],
    }


# ── Basic construction ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildControlRoomViewV1:
    def test_all_view_types_build_from_minimal_bundle(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            assert isinstance(view, ControlRoomView)
            assert view.view_type == vt

    def test_all_view_types_build_from_clean_bundle(self) -> None:
        bundle = _clean_bundle()
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, bundle, as_of=_AS_OF)
            assert view.view_type == vt
            assert view.target_scope == "wave19-test-scope"

    def test_schema_version(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        assert view.schema_version == SCHEMA_VERSION

    def test_generated_at_uses_as_of(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        assert view.generated_at == _AS_OF

    def test_view_id_is_deterministic(self) -> None:
        v1 = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        v2 = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        assert v1.view_id == v2.view_id

    def test_view_id_differs_by_view_type(self) -> None:
        v1 = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        v2 = build_control_room_view_v1("architecture_map", _minimal_bundle(), as_of=_AS_OF)
        assert v1.view_id != v2.view_id

    def test_view_id_starts_with_view_prefix(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        assert view.view_id.startswith("view:")

    def test_filters_passed_through(self) -> None:
        view = build_control_room_view_v1(
            "knowledge_graph_view", _minimal_bundle(), filters={"domain": "risk"}, as_of=_AS_OF
        )
        assert view.filters == {"domain": "risk"}

    def test_empty_filters_by_default(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        assert view.filters == {}


# ── Guardrails ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGuardrails:
    def test_every_view_has_non_empty_guardrails(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            assert len(view.guardrails) > 0, f"View {vt} has empty guardrails"

    def test_guardrails_match_module_constant(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            assert view.guardrails == GUARDRAILS

    def test_no_trading_console_in_guardrails(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            guardrail_text = " ".join(view.guardrails).lower()
            assert "trading console" in guardrail_text or "no trading" in guardrail_text

    def test_no_live_go_in_guardrails(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            guardrail_text = " ".join(view.guardrails).lower()
            assert "live-readiness-go" in guardrail_text or "no live-readiness" in guardrail_text

    def test_no_echtgeld_go_in_guardrails(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            guardrail_text = " ".join(view.guardrails).lower()
            assert "echtgeld" in guardrail_text

    def test_read_only_in_guardrails(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            guardrail_text = " ".join(view.guardrails).lower()
            assert "read-only" in guardrail_text or "no mutations" in guardrail_text


# ── Data sources write_allowed=False ─────────────────────────────────────────


@pytest.mark.unit
class TestDataSourceWriteAllowed:
    def test_all_data_sources_write_allowed_false(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            for ds in view.data_sources:
                assert ds.write_allowed is False, f"View {vt} data source {ds.table} has write_allowed=True"

    def test_to_dict_data_sources_write_allowed_false(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            d = view.to_dict()
            for ds in d["data_sources"]:
                assert ds["write_allowed"] is False


# ── Export formats ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestExportFormats:
    def test_every_view_has_export_formats(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            assert len(view.export_formats) > 0

    def test_export_formats_contain_json(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            assert "json" in view.export_formats

    def test_export_formats_contain_markdown(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            assert "markdown" in view.export_formats


# ── to_dict structure ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestToDictStructure:
    _REQUIRED_KEYS = {
        "schema_version",
        "view_id",
        "view_type",
        "view_label",
        "target_scope",
        "data_sources",
        "filters",
        "required_queries",
        "display_entities",
        "display_edges",
        "warnings",
        "generated_at",
        "generated_by",
        "export_formats",
        "guardrails",
        "payload",
    }

    def test_to_dict_has_all_required_keys(self) -> None:
        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            d = view.to_dict()
            missing = self._REQUIRED_KEYS - set(d.keys())
            assert not missing, f"View {vt} to_dict missing keys: {missing}"

    def test_to_dict_is_json_serialisable(self) -> None:
        import json

        for vt in VIEW_TYPES:
            view = build_control_room_view_v1(vt, _minimal_bundle(), as_of=_AS_OF)
            # Should not raise
            json.dumps(view.to_dict())

    def test_to_dict_guardrails_is_list(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        d = view.to_dict()
        assert isinstance(d["guardrails"], list)

    def test_to_dict_data_sources_is_list_of_dicts(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        d = view.to_dict()
        assert isinstance(d["data_sources"], list)
        for ds in d["data_sources"]:
            assert isinstance(ds, dict)
            assert ds.get("source_type") == "surrealdb_table"
            assert "source_ref" in ds
            assert "query_hint" in ds
            assert "write_allowed" in ds


# ── build_all_views_v1 ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildAllViewsV1:
    def test_returns_9_views(self) -> None:
        views = build_all_views_v1(_minimal_bundle(), as_of=_AS_OF)
        assert len(views) == 9

    def test_all_9_view_types_present(self) -> None:
        views = build_all_views_v1(_minimal_bundle(), as_of=_AS_OF)
        built_types = {v.view_type for v in views}
        assert built_types == VIEW_TYPES

    def test_all_views_same_scope(self) -> None:
        views = build_all_views_v1(_minimal_bundle("my-scope"), as_of=_AS_OF)
        for v in views:
            assert v.target_scope == "my-scope"

    def test_all_views_same_generated_at(self) -> None:
        views = build_all_views_v1(_minimal_bundle(), as_of=_AS_OF)
        for v in views:
            assert v.generated_at == _AS_OF


# ── Error handling ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestErrorHandling:
    def test_unknown_view_type_raises(self) -> None:
        with pytest.raises(ControlRoomError, match="Unknown view_type"):
            build_control_room_view_v1("nonexistent_view", _minimal_bundle(), as_of=_AS_OF)

    def test_none_bundle_raises(self) -> None:
        with pytest.raises(ControlRoomError, match="bundle must be a Mapping"):
            build_control_room_view_v1("knowledge_graph_view", None, as_of=_AS_OF)  # type: ignore[arg-type]

    def test_list_bundle_raises(self) -> None:
        with pytest.raises(ControlRoomError, match="bundle must be a Mapping"):
            build_control_room_view_v1("knowledge_graph_view", [], as_of=_AS_OF)  # type: ignore[arg-type]

    def test_missing_meta_raises(self) -> None:
        with pytest.raises(ControlRoomError, match="bundle.meta"):
            build_control_room_view_v1("knowledge_graph_view", {}, as_of=_AS_OF)

    def test_missing_scope_id_raises(self) -> None:
        with pytest.raises(ControlRoomError, match="scope_id"):
            build_control_room_view_v1("knowledge_graph_view", {"meta": {}}, as_of=_AS_OF)

    def test_empty_scope_id_raises(self) -> None:
        with pytest.raises(ControlRoomError, match="scope_id"):
            build_control_room_view_v1("knowledge_graph_view", {"meta": {"scope_id": ""}}, as_of=_AS_OF)

    def test_build_all_missing_meta_raises(self) -> None:
        with pytest.raises(ControlRoomError):
            build_all_views_v1({}, as_of=_AS_OF)


# ── View-specific payloads ────────────────────────────────────────────────────


@pytest.mark.unit
class TestKnowledgeGraphView:
    def test_nodes_extracted_from_sources(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["node_count"] == 2

    def test_edges_extracted_from_dependency_edges(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["edge_count"] == 1

    def test_empty_bundle_warning(self) -> None:
        view = build_control_room_view_v1("knowledge_graph_view", _minimal_bundle(), as_of=_AS_OF)
        assert len(view.warnings) > 0


@pytest.mark.unit
class TestArchitectureMap:
    def test_modules_extracted(self) -> None:
        view = build_control_room_view_v1("architecture_map", _clean_bundle(), as_of=_AS_OF)
        assert len(view.payload["modules"]) == 2

    def test_dependency_edges_present(self) -> None:
        view = build_control_room_view_v1("architecture_map", _clean_bundle(), as_of=_AS_OF)
        assert len(view.payload["dependency_edges"]) == 1

    def test_empty_sources_warning(self) -> None:
        view = build_control_room_view_v1("architecture_map", _minimal_bundle(), as_of=_AS_OF)
        assert any("source" in w.lower() for w in view.warnings)


@pytest.mark.unit
class TestDecisionChainView:
    def test_chain_length(self) -> None:
        view = build_control_room_view_v1("decision_chain_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["total_decisions"] == 3

    def test_superseded_count(self) -> None:
        view = build_control_room_view_v1("decision_chain_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["superseded_count"] == 1

    def test_open_decisions(self) -> None:
        view = build_control_room_view_v1("decision_chain_view", _clean_bundle(), as_of=_AS_OF)
        assert len(view.payload["open_decisions"]) == 1

    def test_empty_decisions_warning(self) -> None:
        view = build_control_room_view_v1("decision_chain_view", _minimal_bundle(), as_of=_AS_OF)
        assert any("decision" in w.lower() for w in view.warnings)


@pytest.mark.unit
class TestEvidenceMapView:
    def test_expired_count(self) -> None:
        view = build_control_room_view_v1("evidence_map", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["expired_count"] == 1

    def test_uncovered_decisions(self) -> None:
        # dec-002 has no evidence_refs
        view = build_control_room_view_v1("evidence_map", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["uncovered_decisions"] == 1

    def test_total_evidence(self) -> None:
        view = build_control_room_view_v1("evidence_map", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["total_evidence"] == 2

    def test_strength_distribution(self) -> None:
        view = build_control_room_view_v1("evidence_map", _clean_bundle(), as_of=_AS_OF)
        by_str = view.payload["evidence_by_strength"]
        assert by_str["strong"] == 1
        assert by_str["moderate"] == 1

    def test_expired_evidence_warning(self) -> None:
        view = build_control_room_view_v1("evidence_map", _clean_bundle(), as_of=_AS_OF)
        assert any("expired" in w.lower() for w in view.warnings)

    def test_dangling_evidence_refs_counted_as_uncovered(self) -> None:
        """Decision whose evidence_refs point to non-existent IDs must be uncovered."""
        bundle = {
            "meta": {"scope_id": "dangling-test", "level": "system"},
            "decisions": [
                {
                    "decision_id": "dec-dangling",
                    "status": "current",
                    "evidence_refs": ["ev-dangling-999"],  # does not exist in evidence_items
                },
            ],
            "evidence_items": [
                {"evidence_id": "ev-001", "strength": "strong", "expired": False},
            ],
        }
        view = build_control_room_view_v1("evidence_map", bundle, as_of=_AS_OF)
        assert view.payload["covered_decisions"] == 0
        assert view.payload["uncovered_decisions"] == 1
        assert any("decision" in w.lower() for w in view.warnings)

    def test_mixed_valid_and_dangling_refs_covered(self) -> None:
        """Decision with at least one valid ref among dangling ones is still covered."""
        bundle = {
            "meta": {"scope_id": "mixed-test", "level": "system"},
            "decisions": [
                {
                    "decision_id": "dec-mixed",
                    "status": "current",
                    "evidence_refs": ["ev-dangling-999", "ev-001"],  # one valid ref
                },
            ],
            "evidence_items": [
                {"evidence_id": "ev-001", "strength": "strong", "expired": False},
            ],
        }
        view = build_control_room_view_v1("evidence_map", bundle, as_of=_AS_OF)
        assert view.payload["covered_decisions"] == 1
        assert view.payload["uncovered_decisions"] == 0


@pytest.mark.unit
class TestRiskSurfaceReport:
    def test_blocking_drift_count_clean(self) -> None:
        view = build_control_room_view_v1("risk_surface_report", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["blocking_drift_count"] == 0

    def test_blocking_drift_count_blocking(self) -> None:
        view = build_control_room_view_v1("risk_surface_report", _blocking_bundle(), as_of=_AS_OF)
        assert view.payload["blocking_drift_count"] == 1

    def test_blocking_contradiction_count_blocking(self) -> None:
        view = build_control_room_view_v1("risk_surface_report", _blocking_bundle(), as_of=_AS_OF)
        assert view.payload["blocking_contradiction_count"] == 1

    def test_blocking_warning_present(self) -> None:
        view = build_control_room_view_v1("risk_surface_report", _blocking_bundle(), as_of=_AS_OF)
        assert len(view.warnings) > 0

    def test_resolved_findings_not_counted_as_blocking(self) -> None:
        bundle = {
            "meta": {"scope_id": "resolved-scope", "level": "system"},
            "scope_drift_findings": [
                {"finding_id": "sdf-r1", "drift_type": "path_drift", "severity": "blocking", "status": "resolved"},
            ],
            "contradiction_findings": [
                {"contradiction_id": "c-r1", "severity": "blocking", "status": "false_positive"},
            ],
        }
        view = build_control_room_view_v1("risk_surface_report", bundle, as_of=_AS_OF)
        assert view.payload["blocking_drift_count"] == 0
        assert view.payload["blocking_contradiction_count"] == 0


@pytest.mark.unit
class TestStaleKnowledgeView:
    def test_actionable_stale_count(self) -> None:
        view = build_control_room_view_v1("stale_knowledge_view", _clean_bundle(), as_of=_AS_OF)
        # sf-001 is open, sf-002 is refreshed (exempt)
        assert view.payload["actionable_stale_count"] == 1

    def test_stale_by_type(self) -> None:
        view = build_control_room_view_v1("stale_knowledge_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["stale_by_type"]["documentation"] == 1

    def test_expired_memory_count(self) -> None:
        view = build_control_room_view_v1("stale_knowledge_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["expired_memory_count"] == 1


@pytest.mark.unit
class TestScopeDriftEvents:
    def test_watch_drift_in_watch_bucket(self) -> None:
        view = build_control_room_view_v1("scope_drift_events", _clean_bundle(), as_of=_AS_OF)
        assert len(view.payload["watch"]) == 1

    def test_blocking_drift_in_blocking_bucket(self) -> None:
        view = build_control_room_view_v1("scope_drift_events", _blocking_bundle(), as_of=_AS_OF)
        assert len(view.payload["blocking"]) == 1

    def test_blocking_drift_warning(self) -> None:
        view = build_control_room_view_v1("scope_drift_events", _blocking_bundle(), as_of=_AS_OF)
        assert any("blocking" in w.lower() for w in view.warnings)

    def test_total_count(self) -> None:
        view = build_control_room_view_v1("scope_drift_events", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["total"] == 1


@pytest.mark.unit
class TestAgentMemoryView:
    def test_by_trust_distribution(self) -> None:
        view = build_control_room_view_v1("agent_memory_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["by_trust"]["strong"] == 1
        assert view.payload["by_trust"]["weak"] == 1

    def test_expired_count(self) -> None:
        view = build_control_room_view_v1("agent_memory_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["expired_count"] == 1

    def test_total_memory_items(self) -> None:
        view = build_control_room_view_v1("agent_memory_view", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["total_memory_items"] == 2


@pytest.mark.unit
class TestQualityScoreDashboard:
    def test_entry_count(self) -> None:
        view = build_control_room_view_v1("quality_score_dashboard", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["entry_count"] == 1

    def test_worst_grade(self) -> None:
        view = build_control_room_view_v1("quality_score_dashboard", _clean_bundle(), as_of=_AS_OF)
        assert view.payload["worst_grade"] == "watch"

    def test_blocking_worst_grade(self) -> None:
        view = build_control_room_view_v1("quality_score_dashboard", _blocking_bundle(), as_of=_AS_OF)
        assert view.payload["worst_grade"] == "blocking"

    def test_blocking_grade_warning(self) -> None:
        view = build_control_room_view_v1("quality_score_dashboard", _blocking_bundle(), as_of=_AS_OF)
        assert any("blocking" in w.lower() for w in view.warnings)

    def test_empty_quality_scores_warning(self) -> None:
        view = build_control_room_view_v1("quality_score_dashboard", _minimal_bundle(), as_of=_AS_OF)
        assert any("quality score" in w.lower() or "no quality" in w.lower() for w in view.warnings)
