"""
Test-first: CDB Context Tool Inventory & Exposure Matrix.

Reference: Issue #3493
Use Case: Alle CDB Context Tools sind real inventarisiert.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.context_tool_inventory import (
    BACKING_STATUS_VALUES,
    InventoryEntry,
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
    handler_path, registry_status, exposure_status, backing_status, surfaces, evidence."""

    def test_entry_has_all_required_fields(self) -> None:
        entry = InventoryEntry(
            tool_name="context.search",
            purpose="Search the Context Intelligence knowledge base",
            handler_path="tools/mcp/context_bridge.py",
            registry_status="registered",
            exposure_status="exposed",
            backing_status="REPO_ONLY",
            surfaces={"ChatGPT": False, "OpenCode": True, "Cursor": True, "Claude": True, "Codex": False},
            evidence=["tools/mcp/registry.py", "tools/mcp/context_bridge.py"],
        )
        assert entry.tool_name == "context.search"
        assert entry.purpose
        assert entry.handler_path
        assert entry.registry_status
        assert entry.exposure_status
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
                exposure_status="exposed",
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
                exposure_status="exposed",
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
            exposure_status="not_exposed",
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

    def test_markdown_export_is_generated(self, tmp_path: Path) -> None:
        tools = discover_tools_from_repo()
        out = tmp_path / "tool_inventory.md"
        export_inventory_markdown(tools, out)
        assert out.exists()
        content = out.read_text()
        assert "# CDB Context Tool Inventory" in content
        assert "context.search" in content

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
