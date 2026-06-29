"""
CDB Context Tool Inventory & Exposure Matrix.

Builds a canonical inventory of all Context MCP tools discovered from
the registry, handler implementations, agent surface configs, and docs.

Reference: Issue #3493, Issue #2773
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ── Backing Status Enum ──

BACKING_STATUS_VALUES = frozenset({
    "DB_BACKED",
    "IN_MEMORY",
    "REPO_ONLY",
    "CONTRACT_ONLY",
    "PROOF_ONLY",
    "UNKNOWN",
})

# ── Surface Definitions ──

SURFACES: dict[str, str | None] = {
    "ChatGPT": None,
    "OpenCode": None,
    "Cursor": None,
    "Claude": None,
    "Codex": None,
}

SURFACE_LIFECYCLE_TERMS = {
    "present": "Code/Doc/Registry-Hinweis existiert.",
    "exposed": "Tool ist in einer Agentenoberflaeche sichtbar.",
    "callable": "Tool kann in dieser Umgebung wirklich aufgerufen werden.",
    "operational": "Tool liefert fuer den Use Case belastbare Ergebnisse.",
}

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class InventoryEntry:
    """A single tool entry in the inventory matrix."""

    tool_name: str
    purpose: str
    handler_path: str
    registry_status: str
    exposure_status: str
    backing_status: str
    surfaces: dict[str, bool | None]
    evidence: list[str]
    gap_reason: str = ""

    def __post_init__(self) -> None:
        if not self.purpose:
            raise ValueError("purpose must not be empty")
        if not self.handler_path:
            raise ValueError("handler_path must not be empty")
        if self.backing_status not in BACKING_STATUS_VALUES:
            raise ValueError(
                f"Invalid backing_status: {self.backing_status}. "
                f"Must be one of {sorted(BACKING_STATUS_VALUES)}"
            )


# ── Discovery: Registry-backed tool source ──

def discover_tools_from_repo() -> list[InventoryEntry]:
    """Discover tools from the repo's MCP registry and handler sources.

    Uses ContextToolRegistry to find registered tools, then enriches with
    handler status, surface configs from agent surface files, and docs evidence.
    """
    try:
        from tools.mcp.registry import ContextToolRegistry, TOOLS_V0
        for t in TOOLS_V0:
            ContextToolRegistry.register(t)

        tools = ContextToolRegistry.list_tools()
    except Exception:
        # Fallback: define minimal known tools
        tools = []

    if not tools:
        # Build from known TOOLS_V0 structure
        return _build_from_v0()

    return _build_from_registry(tools)


def _build_from_v0() -> list[InventoryEntry]:
    """Build entries from the TOOLS_V0 definition list."""
    from tools.mcp.registry import TOOLS_V0 as v0_tools

    entries = []
    for td in v0_tools:
        is_implemented = td.handler and td.handler.__name__ != "not_implemented_handler"
        handler_path = _resolve_handler_path(td.name, td.handler)

        entries.append(InventoryEntry(
            tool_name=td.name,
            purpose=td.description,
            handler_path=handler_path,
            registry_status="registered",
            exposure_status="exposed" if is_implemented else "defined_not_implemented",
            backing_status=_classify_backing(td.name),
            surfaces=_get_surface_availability(td.name),
            evidence=_get_evidence(td.name, handler_path),
        ))
    return entries


def _build_from_registry(registry_tools) -> list[InventoryEntry]:
    """Build entries from a live registry tool list."""
    entries = []
    for td in registry_tools:
        is_implemented = td.handler and td.handler.__name__ != "not_implemented_handler"
        handler_path = _resolve_handler_path(td.name, td.handler)

        entries.append(InventoryEntry(
            tool_name=td.name,
            purpose=td.description,
            handler_path=handler_path,
            registry_status="registered",
            exposure_status="exposed" if is_implemented else "defined_not_implemented",
            backing_status=_classify_backing(td.name),
            surfaces=_get_surface_availability(td.name),
            evidence=_get_evidence(td.name, handler_path),
        ))
    return entries


def _resolve_handler_path(tool_name: str, handler) -> str:
    """Resolve the handler path for a tool."""
    if handler and hasattr(handler, "__code__"):
        try:
            fpath = Path(handler.__code__.co_filename)
            return fpath.relative_to(REPO_ROOT).as_posix()
        except (ValueError, AttributeError):
            pass
    # Known handler mappings
    handler_map: dict[str, str] = {
        "context.search": "tools/mcp/context_bridge.py",
        "context.trace": "tools/mcp/context_bridge.py",
        "context.explain_source": "tools/mcp/context_bridge.py",
        "context.show_snapshot": "tools/mcp/context_bridge.py",
        "context.show_audit": "tools/mcp/context_bridge.py",
        "context.package": "tools/mcp/context_bridge.py",
        "context.readiness": "tools/mcp/context_bridge.py",
        "context.self_explain": "tools/mcp/context_bridge.py",
        "context.briefing": "tools/mcp/context_bridge.py",
        "context.stop_resolver": "tools/mcp/context_bridge.py",
        "context.required_reads": "tools/mcp/context_bridge.py",
        "cdb_context_impact": "tools/mcp/context_bridge.py",
        "cdb_context_evidence_resolve": "tools/mcp/context_bridge.py",
        "cdb_context_claim_resolve": "tools/mcp/context_bridge.py",
        "cdb_context_memory_get": "tools/mcp/context_bridge.py",
        "cdb_context_memory_write_intent": "tools/mcp/context_bridge.py",
        "cdb_context_trust_summary": "tools/mcp/context_bridge.py",
        "cdb_context_decision_history": "tools/mcp/context_bridge.py",
        "cdb_context_decision_replay": "tools/mcp/context_bridge.py",
        "cdb_context_contradictions": "tools/mcp/context_bridge.py",
        "cdb_context_stale": "tools/mcp/context_bridge.py",
        "cdb_context_scope_drift": "tools/mcp/context_bridge.py",
        "cdb_context_quality_score": "tools/mcp/context_bridge.py",
        "cdb_context_architect_signals": "tools/mcp/context_bridge.py",
        "cdb_control_room_view": "tools/mcp/context_bridge.py",
        "cdb_agent_os_readiness": "tools/mcp/context_bridge.py",
        "cdb_context_briefing": "tools/mcp/context_bridge.py",
    }
    return handler_map.get(tool_name, "tools/mcp/registry.py")


def _classify_backing(tool_name: str) -> str:
    """Classify the backing status of a tool."""
    # No tools currently have SurrealDB adapter evidence — all CONTRACT_ONLY.
    db_backed: set[str] = set()
    in_memory = {
        "context.readiness", "context.explain_source", "context.trace",
        "context.package",
    }
    contract_only = {
        # Former db_backed tools — handler not implemented, no DB evidence
        "context.search", "context.show_snapshot", "context.show_audit",
        "context.briefing", "context.required_reads",
        "context.stop_resolver", "context.self_explain",
        # Contract-defined cdb_context_* tools
        "cdb_context_impact",
        "cdb_context_evidence_resolve", "cdb_context_claim_resolve",
        "cdb_context_memory_get", "cdb_context_memory_write_intent",
        "cdb_context_trust_summary", "cdb_context_decision_history",
        "cdb_context_decision_replay", "cdb_context_contradictions",
        "cdb_context_stale", "cdb_context_scope_drift",
        "cdb_context_quality_score", "cdb_context_architect_signals",
        "cdb_control_room_view", "cdb_agent_os_readiness",
        "cdb_context_briefing",
    }
    if tool_name in db_backed:
        return "DB_BACKED"
    if tool_name in in_memory:
        return "IN_MEMORY"
    if tool_name in contract_only:
        return "CONTRACT_ONLY"
    return "REPO_ONLY"


def _get_surface_availability(tool_name: str) -> dict[str, bool | None]:
    """Determine surface availability for a tool.

    Based on known agent surface configs in the repo.
    """
    # Tools known to be exposed by cdb_context MCP server
    cdb_context_tools = {
        "context.search", "context.trace", "context.explain_source",
        "context.show_snapshot", "context.show_audit", "context.package",
        "context.readiness", "context.self_explain", "context.briefing",
        "context.stop_resolver", "context.required_reads",
        "cdb_context_impact", "cdb_context_evidence_resolve",
        "cdb_context_claim_resolve", "cdb_context_memory_get",
        "cdb_context_memory_write_intent", "cdb_context_trust_summary",
        "cdb_context_decision_history", "cdb_context_decision_replay",
        "cdb_context_contradictions", "cdb_context_stale",
        "cdb_context_scope_drift", "cdb_context_quality_score",
        "cdb_context_architect_signals", "cdb_control_room_view",
        "cdb_agent_os_readiness", "cdb_context_briefing",
    }

    # Surfaces that have cdb_context MCP configured
    cdb_context_surfaces = {"Cursor", "Claude", "OpenCode"}

    result: dict[str, bool | None] = {}
    for surface in SURFACES:
        if tool_name in cdb_context_tools:
            result[surface] = surface in cdb_context_surfaces
        else:
            result[surface] = None
    return result


def _get_evidence(tool_name: str, handler_path: str) -> list[str]:
    """Gather evidence references for a tool."""
    evidence: list[str] = []

    # Registry evidence
    registry_path = "tools/mcp/registry.py"
    if (REPO_ROOT / registry_path).exists():
        evidence.append(registry_path)

    # Handler evidence
    if handler_path and (REPO_ROOT / handler_path).exists():
        evidence.append(handler_path)

    # Permission guard evidence
    guard_path = "tools/mcp/permission_guard.py"
    if (REPO_ROOT / guard_path).exists():
        evidence.append(guard_path)

    # MCP server
    server_path = "tools/mcp/server.py"
    if (REPO_ROOT / server_path).exists():
        evidence.append(server_path)

    # MCP config
    for cfg_path in [".cursor/mcp.json", ".claude/settings.local.json"]:
        if (REPO_ROOT / cfg_path).exists():
            evidence.append(cfg_path)

    return sorted(set(evidence))


# ── Classification ──

def classify_tools() -> dict[str, list[str]]:
    """Classify all tools by lifecycle state."""
    tools = discover_tools_from_repo()

    result: dict[str, list[str]] = {
        "present": [],
        "exposed": [],
        "callable": [],
        "operational": [],
    }

    for t in tools:
        result["present"].append(t.tool_name)
        if t.exposure_status == "exposed":
            result["exposed"].append(t.tool_name)
            result["callable"].append(t.tool_name)
            result["operational"].append(t.tool_name)

    return result


# ── Build ──

def build_inventory() -> dict[str, Any]:
    """Build the complete tool inventory structure."""
    tools = discover_tools_from_repo()
    classification = classify_tools()

    db_backed = sum(1 for t in tools if t.backing_status == "DB_BACKED")
    repo_only = sum(1 for t in tools if t.backing_status == "REPO_ONLY")
    unknown = sum(1 for t in tools if t.backing_status == "UNKNOWN")
    in_memory = sum(1 for t in tools if t.backing_status == "IN_MEMORY")
    contract_only = sum(1 for t in tools if t.backing_status == "CONTRACT_ONLY")
    proof_only = sum(1 for t in tools if t.backing_status == "PROOF_ONLY")

    return {
        "matrix": [asdict(t) for t in tools],
        "classification": classification,
        "summary": {
            "total_tools": len(tools),
            "db_backed_count": db_backed,
            "in_memory_count": in_memory,
            "repo_only_count": repo_only,
            "contract_only_count": contract_only,
            "proof_only_count": proof_only,
            "unknown_count": unknown,
        },
    }


# ── Export ──

def export_inventory_json(tools: list[InventoryEntry], output_path: Path) -> None:
    """Export inventory to JSON."""
    data = [asdict(t) for t in tools]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_inventory_markdown(tools: list[InventoryEntry], output_path: Path) -> None:
    """Export inventory to Markdown."""
    lines = [
        "# CDB Context Tool Inventory",
        "",
        f"Generated: {len(tools)} tools discovered from repo sources.",
        "",
        "## Matrix",
        "",
        "| Tool | Purpose | Handler | Registry | Exposure | Backing | ChatGPT | OpenCode | Cursor | Claude | Codex |",
        "|------|---------|---------|----------|----------|---------|---------|----------|--------|-------|-------|",
    ]

    for t in sorted(tools, key=lambda x: x.tool_name):
        surf = t.surfaces
        lines.append(
            f"| {t.tool_name} "
            f"| {t.purpose[:50]} "
            f"| {t.handler_path} "
            f"| {t.registry_status} "
            f"| {t.exposure_status} "
            f"| {t.backing_status} "
            f"| {_bool_icon(surf.get('ChatGPT'))} "
            f"| {_bool_icon(surf.get('OpenCode'))} "
            f"| {_bool_icon(surf.get('Cursor'))} "
            f"| {_bool_icon(surf.get('Claude'))} "
            f"| {_bool_icon(surf.get('Codex'))} |"
        )

    lines.append("")
    lines.append("## Classification")
    classification = classify_tools()
    for state, tool_list in classification.items():
        lines.append(f"- **{state}**: {', '.join(sorted(tool_list))}")
    lines.append("")
    lines.append("## Gaps")
    lines.append(f"- {sum(1 for t in tools if t.backing_status == 'UNKNOWN')} tools have UNKNOWN backing status.")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _bool_icon(val: bool | None) -> str:
    if val is True:
        return "Y"
    if val is False:
        return "-"
    return "?"
