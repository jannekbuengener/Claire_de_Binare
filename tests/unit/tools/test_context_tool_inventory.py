"""
Test-first: CDB Context Tool Inventory & Exposure Matrix.

Reference: Issue #3493
Use Case: Alle CDB Context Tools sind real inventarisiert.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.context_tool_inventory import (
    BACKING_STATUS_VALUES,
    CALLABILITY_STATUS_VALUES,
    EVIDENCE_LEVEL_VALUES,
    EXPOSURE_STATUS_VALUES,
    HANDLER_STATUS_VALUES,
    InventoryEntry,
    OPERATIONAL_STATUS_VALUES,
    SURFACES,
    SURFACE_LIFECYCLE_TERMS,
    build_inventory,
    classify_tools,
    export_inventory_json,
    export_inventory_markdown,
    discover_tools_from_repo,
)


class TestInventorySchemaRequiredFields:
    """Jeder Eintrag der Tool-Matrix hat mindestens: tool_name, purpose,
    handler_path, registry_status, handler_status, exposure_status,
    callability_status, operational_status, evidence_level,
    backing_status, surfaces, evidence."""

    def test_entry_has_all_required_fields(self) -> None:
        entry = InventoryEntry(
            tool_name="context.search",
            purpose="Search the Context Intelligence knowledge base",
            handler_path="tools/mcp/context_bridge.py",
            registry_status="registered",
            handler_status="implemented",
            exposure_status="repo_surface_configured",
            callability_status="not_proven",
            operational_status="not_proven",
            evidence_level="repo_surface_config",
            backing_status="REPO_ONLY",
            surfaces={"ChatGPT": False, "OpenCode": True, "Cursor": True, "Claude": True, "Codex": False},
            evidence=["tools/mcp/registry.py", "tools/mcp/context_bridge.py"],
        )
        assert entry.tool_name == "context.search"
        assert entry.purpose
        assert entry.handler_path
        assert entry.registry_status
        assert entry.handler_status
        assert entry.exposure_status
        assert entry.callability_status
        assert entry.operational_status
        assert entry.evidence_level
        assert entry.backing_status
        assert entry.surfaces
        assert entry.evidence

    def test_entry_requires_purpose_non_empty(self) -> None:
        with pytest.raises(ValueError, match="purpose"):
            InventoryEntry(
                tool_name="test",
                purpose="",
                handler_path="path",
                registry_status="registered",
                handler_status="implemented",
                exposure_status="repo_surface_configured",
                callability_status="not_proven",
                operational_status="not_proven",
                evidence_level="repo_surface_config",
                backing_status="REPO_ONLY",
                surfaces=SURFACES,
                evidence=[],
            )

    def test_entry_requires_handler_path_non_empty(self) -> None:
        with pytest.raises(ValueError, match="handler_path"):
            InventoryEntry(
                tool_name="test",
                purpose="test",
                handler_path="",
                registry_status="registered",
                handler_status="implemented",
                exposure_status="repo_surface_configured",
                callability_status="not_proven",
                operational_status="not_proven",
                evidence_level="repo_surface_config",
                backing_status="REPO_ONLY",
                surfaces=SURFACES,
                evidence=[],
            )


class TestToolsDiscoveredFromRepoSources:
    """Context Tools werden nicht manuell geraten, sondern aus
    Registry/Handler/Docs/Agent-Surfaces abgeleitet."""

    def test_discover_returns_list_of_entries(self) -> None:
        tools = discover_tools_from_repo()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_discovered_tools_include_context_search(self) -> None:
        tools = discover_tools_from_repo()
        names = [t.tool_name for t in tools]
        assert "context.search" in names

    def test_discovered_tools_include_cdb_context_impact(self) -> None:
        tools = discover_tools_from_repo()
        names = [t.tool_name for t in tools]
        assert "cdb_context_impact" in names

    def test_each_discovered_tool_has_handler_path(self) -> None:
        tools = discover_tools_from_repo()
        for t in tools:
            assert t.handler_path, f"{t.tool_name} missing handler_path"

    def test_each_discovered_tool_has_backing_status(self) -> None:
        tools = discover_tools_from_repo()
        for t in tools:
            assert t.backing_status in BACKING_STATUS_VALUES, (
                f"{t.tool_name} invalid backing_status: {t.backing_status}"
            )


class TestBackingStatusEnum:
    """Nur erlaubt: DB_BACKED, IN_MEMORY, REPO_ONLY, CONTRACT_ONLY, PROOF_ONLY, UNKNOWN."""

    def test_enum_has_exact_values(self) -> None:
        expected = {"DB_BACKED", "IN_MEMORY", "REPO_ONLY", "CONTRACT_ONLY", "PROOF_ONLY", "UNKNOWN"}
        assert BACKING_STATUS_VALUES == expected

    def test_repo_only_is_valid(self) -> None:
        assert "REPO_ONLY" in BACKING_STATUS_VALUES

    def test_db_backed_is_valid(self) -> None:
        assert "DB_BACKED" in BACKING_STATUS_VALUES


class TestSurfaceAvailability:
    """Fuer jedes Tool werden die Surface-Spalten geprueft:
    ChatGPT, OpenCode, Cursor, Claude, Codex."""

    def test_surface_keys_are_correct(self) -> None:
        assert set(SURFACES.keys()) == {"ChatGPT", "OpenCode", "Cursor", "Claude", "Codex"}

    def test_each_entry_has_surface_fields(self) -> None:
        tools = discover_tools_from_repo()
        for t in tools:
            assert isinstance(t.surfaces, dict)
            assert set(t.surfaces.keys()) == set(SURFACES.keys()), (
                f"{t.tool_name} surfaces mismatch"
            )

    def test_surface_values_are_bool_or_none(self) -> None:
        tools = discover_tools_from_repo()
        for t in tools:
            for surface, val in t.surfaces.items():
                assert val is True or val is False or val is None, (
                    f"{t.tool_name}.{surface} must be bool or None, got {type(val).__name__}"
                )


class TestStatusFieldEnums:
    """Handler-, Exposure-, Callability-, Operational- und Evidence-Level
    sind getrennte Felder mit konservativen Enums."""

    def test_handler_status_enum_has_expected_values(self) -> None:
        assert HANDLER_STATUS_VALUES == {"implemented", "not_implemented"}

    def test_exposure_status_enum_has_expected_values(self) -> None:
        assert EXPOSURE_STATUS_VALUES == {"repo_surface_configured", "not_exposed"}

    def test_callability_status_enum_has_expected_values(self) -> None:
        assert CALLABILITY_STATUS_VALUES == {"session_callable", "not_proven"}

    def test_operational_status_enum_has_expected_values(self) -> None:
        assert OPERATIONAL_STATUS_VALUES == {"not_proven", "operationally_proven"}

    def test_evidence_level_enum_has_expected_values(self) -> None:
        assert EVIDENCE_LEVEL_VALUES == {
            "session_live_call",
            "repo_surface_config",
            "repo_handler_only",
            "registry_contract",
        }


class TestToolStateTermsNotMixed:
    """present, exposed, callable und operational werden getrennt dokumentiert."""

    def test_lifecycle_terms_are_separate(self) -> None:
        assert "present" in SURFACE_LIFECYCLE_TERMS
        assert "exposed" in SURFACE_LIFECYCLE_TERMS
        assert "callable" in SURFACE_LIFECYCLE_TERMS
        assert "operational" in SURFACE_LIFECYCLE_TERMS

    def test_classification_uses_separate_terms(self) -> None:
        result = classify_tools()
        assert "present" in result
        assert "exposed" in result
        assert "callable" in result
        assert "operational" in result


class TestExposureAndCallabilityTruth:
    """Session-callability, repo-surface exposure und operational proof bleiben getrennt."""

    def test_minimum_session_callable_tools_are_preserved(self) -> None:
        tools = {tool.tool_name: tool for tool in discover_tools_from_repo()}
        assert tools["context.required_reads"].callability_status == "session_callable"
        assert tools["context.readiness"].callability_status == "session_callable"

    def test_session_callable_does_not_upgrade_backing_status(self) -> None:
        tools = {tool.tool_name: tool for tool in discover_tools_from_repo()}
        assert tools["context.required_reads"].backing_status != "DB_BACKED"
        assert tools["context.readiness"].backing_status != "DB_BACKED"

    def test_repo_surface_exposure_is_not_empty(self) -> None:
        result = classify_tools()
        assert "context.required_reads" in result["exposed"]
        assert "context.readiness" in result["exposed"]

    def test_context_briefing_is_not_marked_session_callable_without_live_proof(self) -> None:
        tools = {tool.tool_name: tool for tool in discover_tools_from_repo()}
        assert tools["context.briefing"].callability_status == "not_proven"

    def test_operational_stays_empty_without_operational_proof(self) -> None:
        result = classify_tools()
        assert result["operational"] == []
        for tool in discover_tools_from_repo():
            assert tool.operational_status == "not_proven"


class TestDbBackedRequiresRealEvidence:
    """DB_BACKED darf nur gesetzt werden, wenn konkrete DB-/adapter-/record-backed
    Evidence vorhanden ist."""

    def test_db_backed_tools_have_evidence(self) -> None:
        tools = discover_tools_from_repo()
        for t in tools:
            if t.backing_status == "DB_BACKED":
                assert len(t.evidence) > 0, (
                    f"{t.tool_name} is DB_BACKED but has no evidence"
                )
                # Evidence must reference real repo paths or known DB artifacts
                for ev in t.evidence:
                    assert isinstance(ev, str) and len(ev) > 0


class TestUnknownAllowedWithReason:
    """UNKNOWN ist erlaubt, aber nur mit reason/gap."""

    def test_unknown_entry_has_gap_reason(self) -> None:
        tools = discover_tools_from_repo()
        for t in tools:
            if t.backing_status == "UNKNOWN":
                assert t.gap_reason and len(t.gap_reason) > 0, (
                    f"{t.tool_name} is UNKNOWN but missing gap_reason"
                )

    def test_entry_can_be_unknown_with_reason(self) -> None:
        entry = InventoryEntry(
            tool_name="future.tool",
            purpose="Not yet implemented",
            handler_path="unknown",
            registry_status="not_registered",
            handler_status="not_implemented",
            exposure_status="not_exposed",
            callability_status="not_proven",
            operational_status="not_proven",
            evidence_level="registry_contract",
            backing_status="UNKNOWN",
            surfaces={"ChatGPT": None, "OpenCode": None, "Cursor": None, "Claude": None, "Codex": None},
            evidence=[],
            gap_reason="Tool not yet discovered in any repo source",
        )
        assert entry.backing_status == "UNKNOWN"
        assert entry.gap_reason


class TestMatrixOutputGenerated:
    """Ein maschinenlesbarer Output und ein menschenlesbarer Report werden erzeugt."""

    def test_json_export_is_valid(self, tmp_path: Path) -> None:
        tools = discover_tools_from_repo()
        out = tmp_path / "tool_inventory.json"
        export_inventory_json(tools, out)
        assert out.exists()
        with open(out) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "tool_name" in data[0]
        assert "callability_status" in data[0]
        assert "operational_status" in data[0]
        assert "evidence_level" in data[0]

    def test_markdown_export_is_generated(self, tmp_path: Path) -> None:
        tools = discover_tools_from_repo()
        out = tmp_path / "tool_inventory.md"
        export_inventory_markdown(tools, out)
        assert out.exists()
        content = out.read_text()
        assert "# CDB Context Tool Inventory" in content
        assert "context.search" in content
        assert "Session-callable means the tool was proven callable in this session." in content

    def test_build_inventory_returns_complete_structure(self) -> None:
        inv = build_inventory()
        assert "matrix" in inv
        assert "classification" in inv
        assert "present" in inv["classification"]
        assert "exposed" in inv["classification"]
        assert "callable" in inv["classification"]
        assert "operational" in inv["classification"]
        assert "summary" in inv
        assert "total_tools" in inv["summary"]
        assert "db_backed_count" in inv["summary"]
        assert "repo_only_count" in inv["summary"]
        assert "unknown_count" in inv["summary"]
        assert "exposed_count" in inv["summary"]
        assert "session_callable_count" in inv["summary"]
        assert "operational_count" in inv["summary"]

    def test_build_inventory_summary_matches_conservative_truth(self) -> None:
        inv = build_inventory()
        assert inv["summary"]["db_backed_count"] == 0
        assert inv["summary"]["session_callable_count"] >= 2
        assert inv["summary"]["operational_count"] == 0

    def test_json_and_markdown_summaries_stay_consistent(self, tmp_path: Path) -> None:
        tools = discover_tools_from_repo()
        json_out = tmp_path / "tool_inventory.json"
        md_out = tmp_path / "tool_inventory.md"

        export_inventory_json(tools, json_out)
        export_inventory_markdown(tools, md_out)

        data = json.loads(json_out.read_text(encoding="utf-8"))
        markdown = md_out.read_text(encoding="utf-8")

        db_backed_count = sum(1 for entry in data if entry["backing_status"] == "DB_BACKED")
        callable_count = sum(
            1 for entry in data if entry["callability_status"] == "session_callable"
        )
        operational_count = sum(
            1
            for entry in data
            if entry["operational_status"] == "operationally_proven"
        )

        assert f"| DB_BACKED | {db_backed_count} |" in markdown
        assert f"| session_callable | {callable_count} |" in markdown
        assert f"| operationally_proven | {operational_count} |" in markdown
