"""
CDB MCP Access Boundary generator for #3481.

Builds a deterministic, machine-readable boundary matrix that separates
allowed read-only context tools from blocked, future, forbidden, and unknown
tool surfaces.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.context_tool_inventory import build_inventory
from tools.mcp.context_bridge import create_bridge
from tools.mcp.registry import ContextToolRegistry, ToolDefinition

REPO_ROOT = Path(__file__).resolve().parents[1]

DECISION_VALUES = frozenset(
    {
        "ALLOWED_READONLY",
        "FORBIDDEN_MUTATION",
        "FUTURE",
        "BLOCKED",
        "UNKNOWN",
    }
)

CALLABLE_STATUS_VALUES = frozenset(
    {
        "CALLABLE",
        "NOT_IMPLEMENTED",
        "NOT_EXPOSED",
        "FORBIDDEN",
        "UNKNOWN",
    }
)

OPERATIONAL_STATUS_VALUES = frozenset(
    {
        "REPO_READONLY",
        "IN_MEMORY_READONLY",
        "CONTRACT_READONLY",
        "DB_BACKED_READONLY_PROVEN",
        "DB_BACKED_READONLY_UNPROVEN",
        "NOT_EXPOSED",
        "BLOCKED_RAW_MCP",
        "FORBIDDEN_MUTATION",
        "UNKNOWN",
    }
)

BASE_PERMISSION_EVIDENCE = [
    "tools/mcp/registry.py",
    "tools/mcp/context_bridge.py",
    "tools/mcp/permission_guard.py",
    "docs/surrealdb/context-intelligence-permission-matrix-v0.md",
    "docs/surrealdb/context-mcp-bridge-contract.md",
]

UPSTREAM_MCP_DOC = "https://surrealdb.com/docs/build/ai-agents/mcp"
UPSTREAM_AGENT_SKILLS_DOC = "https://surrealdb.com/docs/build/ai-agents/agent-skills"
UPSTREAM_AGENT_RULES_DOC = "https://surrealdb.com/docs/build/ai-agents/agent-rules"

BRIDGE_TARGET_ALIAS_PATTERN = re.compile(
    r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<purpose>[^|]+?)\s*\|\s*"
    r"(?P<internal>[^|]+?)\s*\|\s*(?P<status>[^|]+?)\s*\|$"
)

DRY_RUN_READONLY_TOOLS = {"cdb_context_memory_write_intent"}

UPSTREAM_TOOL_POLICIES: dict[str, dict[str, str]] = {
    "query": {
        "decision": "BLOCKED",
        "mutation_risk": "raw_query_write_capable",
        "allowed_mode": "none",
        "callable_status": "NOT_EXPOSED",
        "operational_status": "BLOCKED_RAW_MCP",
        "purpose": "Run SurrealQL and return serialised results.",
    },
    "select": {
        "decision": "BLOCKED",
        "mutation_risk": "raw_read_surface",
        "allowed_mode": "none",
        "callable_status": "NOT_EXPOSED",
        "operational_status": "BLOCKED_RAW_MCP",
        "purpose": "Data selection helper.",
    },
    "create": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "direct_mutation",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Data mutation helper.",
    },
    "insert": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "direct_mutation",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Data mutation helper.",
    },
    "upsert": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "direct_mutation",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Data mutation helper.",
    },
    "update": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "direct_mutation",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Data mutation helper.",
    },
    "delete": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "direct_mutation",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Data mutation helper.",
    },
    "relate": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "direct_mutation",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Relation mutation helper.",
    },
    "run": {
        "decision": "FORBIDDEN_MUTATION",
        "mutation_risk": "function_execution",
        "allowed_mode": "none",
        "callable_status": "FORBIDDEN",
        "operational_status": "FORBIDDEN_MUTATION",
        "purpose": "Call a database function with typed arguments.",
    },
    "list": {
        "decision": "BLOCKED",
        "mutation_risk": "raw_read_surface",
        "allowed_mode": "none",
        "callable_status": "NOT_EXPOSED",
        "operational_status": "BLOCKED_RAW_MCP",
        "purpose": "List namespaces, databases, tables, indexes, users, and more.",
    },
    "use": {
        "decision": "BLOCKED",
        "mutation_risk": "session_context_switch",
        "allowed_mode": "none",
        "callable_status": "NOT_EXPOSED",
        "operational_status": "BLOCKED_RAW_MCP",
        "purpose": "Select namespace and database context.",
    },
    "info": {
        "decision": "BLOCKED",
        "mutation_risk": "raw_read_surface",
        "allowed_mode": "none",
        "callable_status": "NOT_EXPOSED",
        "operational_status": "BLOCKED_RAW_MCP",
        "purpose": "Schema or engine information for a scope.",
    },
}


@dataclass(frozen=True)
class BoundaryEntry:
    tool_name: str
    tool_family: str
    repo_present: bool
    exposed: bool
    callable_status: str
    operational_status: str
    decision: str
    mutation_risk: str
    allowed_mode: str
    handler_path: str
    permission_evidence: list[str]
    source_evidence: list[str]
    gap_reason: str = ""

    def __post_init__(self) -> None:
        if self.decision not in DECISION_VALUES:
            raise ValueError(f"Invalid decision: {self.decision}")
        if self.callable_status not in CALLABLE_STATUS_VALUES:
            raise ValueError(f"Invalid callable_status: {self.callable_status}")
        if self.operational_status not in OPERATIONAL_STATUS_VALUES:
            raise ValueError(f"Invalid operational_status: {self.operational_status}")
        if self.decision == "UNKNOWN" and not self.gap_reason.strip():
            raise ValueError("UNKNOWN entries require gap_reason")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _handler_status(tool_def: ToolDefinition | None) -> str:
    if tool_def is None:
        return "UNKNOWN"
    handler = tool_def.handler
    if handler is None:
        return "NOT_IMPLEMENTED"
    if getattr(handler, "__name__", "") == "not_implemented_handler":
        return "NOT_IMPLEMENTED"
    return "CALLABLE"


def _handler_path(tool_def: ToolDefinition | None, fallback: str) -> str:
    if tool_def is None or tool_def.handler is None:
        return fallback
    code = getattr(tool_def.handler, "__code__", None)
    if code is None:
        return fallback
    return _relative_path(Path(code.co_filename))


def _unique_strings(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _load_repo_target_aliases() -> list[dict[str, str]]:
    contract_path = REPO_ROOT / "docs/surrealdb/context-mcp-bridge-contract.md"
    aliases: list[dict[str, str]] = []
    for line in contract_path.read_text(encoding="utf-8").splitlines():
        match = BRIDGE_TARGET_ALIAS_PATTERN.match(line)
        if not match:
            continue
        tool_name = match.group("name").strip().strip("`")
        if not tool_name.startswith("cdb_context_"):
            continue
        aliases.append(
            {
                "tool_name": tool_name,
                "purpose": match.group("purpose").strip().strip("`"),
                "status": match.group("status").strip(),
            }
        )
    return aliases


def _registry_operational_status(tool_name: str, backing_status: str) -> str:
    if tool_name in {
        "context.briefing",
        "cdb_context_briefing",
        "cdb_context_evidence_resolve",
        "cdb_context_claim_resolve",
        "cdb_context_memory_get",
        "cdb_context_memory_write_intent",
        "cdb_context_trust_summary",
        "cdb_context_decision_history",
        "cdb_context_decision_replay",
        "cdb_context_contradictions",
        "cdb_context_stale",
        "cdb_context_scope_drift",
        "cdb_context_quality_score",
        "cdb_context_architect_signals",
        "cdb_control_room_view",
        "cdb_agent_os_readiness",
    }:
        return "DB_BACKED_READONLY_UNPROVEN"
    if backing_status == "IN_MEMORY":
        return "IN_MEMORY_READONLY"
    if backing_status == "CONTRACT_ONLY":
        return "CONTRACT_READONLY"
    if backing_status == "REPO_ONLY":
        return "REPO_READONLY"
    if backing_status == "DB_BACKED":
        return "DB_BACKED_READONLY_UNPROVEN"
    return "UNKNOWN"


def _build_registry_entries() -> list[BoundaryEntry]:
    inventory = build_inventory()
    create_bridge()
    inventory_entries = {entry["tool_name"]: entry for entry in inventory["matrix"]}
    entries: list[BoundaryEntry] = []

    for tool_name in sorted(ContextToolRegistry.list_tool_names()):
        tool_def = ContextToolRegistry.get_tool(tool_name)
        inventory_entry = inventory_entries.get(tool_name, {})
        callable_status = _handler_status(tool_def)
        operational_status = _registry_operational_status(
            tool_name, inventory_entry.get("backing_status", "UNKNOWN")
        )
        allowed_mode = "dry_run_only" if tool_name in DRY_RUN_READONLY_TOOLS else "read_only"
        handler_path = _handler_path(tool_def, inventory_entry.get("handler_path", ""))
        source_evidence = _unique_strings(
            list(inventory_entry.get("evidence", []))
            + [
                "artifacts/context_tool_inventory/tool_inventory.json",
                "tools/context_tool_inventory.py",
                "docs/surrealdb/context-evidence-claim-memory-runbook.md",
            ]
        )
        permission_evidence = _unique_strings(BASE_PERMISSION_EVIDENCE)

        entries.append(
            BoundaryEntry(
                tool_name=tool_name,
                tool_family="cdb_context_registry",
                repo_present=True,
                exposed=True,
                callable_status=callable_status,
                operational_status=operational_status,
                decision="ALLOWED_READONLY",
                mutation_risk="dry_run_gate" if tool_name in DRY_RUN_READONLY_TOOLS else "none",
                allowed_mode=allowed_mode,
                handler_path=handler_path,
                permission_evidence=permission_evidence,
                source_evidence=source_evidence,
                gap_reason="",
            )
        )

    return entries


def _build_repo_present_not_exposed_entries(
    exposed_tool_names: set[str],
) -> list[BoundaryEntry]:
    entries: list[BoundaryEntry] = []
    for alias in _load_repo_target_aliases():
        tool_name = alias["tool_name"]
        status = alias["status"].lower()
        if tool_name in exposed_tool_names:
            continue
        decision = "FUTURE" if "target/future" in status else "BLOCKED"
        entries.append(
            BoundaryEntry(
                tool_name=tool_name,
                tool_family="cdb_repo_contract_alias",
                repo_present=True,
                exposed=False,
                callable_status="NOT_EXPOSED",
                operational_status="NOT_EXPOSED",
                decision=decision,
                mutation_risk="none",
                allowed_mode="read_only",
                handler_path="",
                permission_evidence=_unique_strings(BASE_PERMISSION_EVIDENCE),
                source_evidence=["docs/surrealdb/context-mcp-bridge-contract.md"],
                gap_reason="",
            )
        )
    return entries


def _build_upstream_reference_entries() -> list[BoundaryEntry]:
    entries: list[BoundaryEntry] = []
    shared_source_evidence = [
        "docs/external-docs/index.md",
        UPSTREAM_MCP_DOC,
        UPSTREAM_AGENT_SKILLS_DOC,
        UPSTREAM_AGENT_RULES_DOC,
    ]

    for tool_name, policy in sorted(UPSTREAM_TOOL_POLICIES.items()):
        entries.append(
            BoundaryEntry(
                tool_name=tool_name,
                tool_family="surrealdb_builtin_mcp",
                repo_present=False,
                exposed=False,
                callable_status=policy["callable_status"],
                operational_status=policy["operational_status"],
                decision=policy["decision"],
                mutation_risk=policy["mutation_risk"],
                allowed_mode=policy["allowed_mode"],
                handler_path="",
                permission_evidence=_unique_strings(BASE_PERMISSION_EVIDENCE),
                source_evidence=shared_source_evidence,
                gap_reason="",
            )
        )
    return entries


def build_mcp_access_boundary() -> dict[str, Any]:
    registry_entries = _build_registry_entries()
    exposed_tool_names = {entry.tool_name for entry in registry_entries}
    repo_alias_entries = _build_repo_present_not_exposed_entries(exposed_tool_names)
    upstream_entries = _build_upstream_reference_entries()

    matrix_entries = sorted(
        registry_entries + repo_alias_entries + upstream_entries,
        key=lambda entry: (entry.tool_family, entry.tool_name),
    )
    matrix = [asdict(entry) for entry in matrix_entries]

    groups = {
        "exposed_tools": sorted(
            entry.tool_name for entry in matrix_entries if entry.exposed
        ),
        "repo_present_not_exposed": sorted(
            entry.tool_name
            for entry in matrix_entries
            if entry.repo_present and not entry.exposed
        ),
        "allowed_readonly_tools": sorted(
            entry.tool_name
            for entry in matrix_entries
            if entry.decision == "ALLOWED_READONLY"
        ),
        "forbidden_mutation_tools": sorted(
            entry.tool_name
            for entry in matrix_entries
            if entry.decision == "FORBIDDEN_MUTATION"
        ),
        "future_tools": sorted(
            entry.tool_name for entry in matrix_entries if entry.decision == "FUTURE"
        ),
        "blocked_tools": sorted(
            entry.tool_name for entry in matrix_entries if entry.decision == "BLOCKED"
        ),
        "unknown_tools": sorted(
            entry.tool_name for entry in matrix_entries if entry.decision == "UNKNOWN"
        ),
    }

    summary = {
        "total_tools": len(matrix_entries),
        "exposed_count": len(groups["exposed_tools"]),
        "repo_present_not_exposed_count": len(groups["repo_present_not_exposed"]),
        "allowed_readonly_count": len(groups["allowed_readonly_tools"]),
        "forbidden_mutation_count": len(groups["forbidden_mutation_tools"]),
        "future_count": len(groups["future_tools"]),
        "blocked_count": len(groups["blocked_tools"]),
        "unknown_count": len(groups["unknown_tools"]),
        "live_db_operational_count": sum(
            1
            for entry in matrix_entries
            if entry.operational_status == "DB_BACKED_READONLY_PROVEN"
        ),
    }

    return {
        "matrix": matrix,
        "groups": groups,
        "summary": summary,
        "decision_values": sorted(DECISION_VALUES),
        "source_catalog": {
            "repo_inputs": [
                "artifacts/context_tool_inventory/tool_inventory.json",
                "tools/context_tool_inventory.py",
                "tools/mcp/registry.py",
                "tools/mcp/context_bridge.py",
                "tools/mcp/permission_guard.py",
                "docs/surrealdb/context-intelligence-permission-matrix-v0.md",
                "docs/surrealdb/context-mcp-bridge-contract.md",
                "docs/surrealdb/context-evidence-claim-memory-runbook.md",
            ],
            "official_inputs": [
                UPSTREAM_MCP_DOC,
                UPSTREAM_AGENT_SKILLS_DOC,
                UPSTREAM_AGENT_RULES_DOC,
            ],
        },
    }


def _render_markdown(result: dict[str, Any], title: str) -> str:
    groups = result["groups"]
    summary = result["summary"]
    lines = [
        title,
        "",
        "Machine-readable access boundary for CDB Context/MCP/SurrealDB tooling.",
        "",
        "## Summary",
        "",
        f"- Total tools in matrix: {summary['total_tools']}",
        f"- Exposed CDB context tools: {summary['exposed_count']}",
        f"- Repo-present but not exposed: {summary['repo_present_not_exposed_count']}",
        f"- Allowed read-only: {summary['allowed_readonly_count']}",
        f"- Forbidden mutation: {summary['forbidden_mutation_count']}",
        f"- Future: {summary['future_count']}",
        f"- Blocked: {summary['blocked_count']}",
        f"- Unknown: {summary['unknown_count']}",
        f"- Live DB claims proven: {summary['live_db_operational_count']}",
        "",
        "## Decision Meaning",
        "",
        "- `ALLOWED_READONLY`: read-only use is allowed with registry/guard evidence.",
        "- `FORBIDDEN_MUTATION`: mutative tool surface is not allowed for CDB agents.",
        "- `FUTURE`: repo-documented target alias, not exposed today.",
        "- `BLOCKED`: upstream or raw surface is intentionally not adopted by CDB.",
        "- `UNKNOWN`: classification gap; `gap_reason` required.",
        "",
        "## Allowed Read-only",
        "",
        *(f"- `{tool}`" for tool in groups["allowed_readonly_tools"]),
        "",
        "## Forbidden Mutation",
        "",
        *(f"- `{tool}`" for tool in groups["forbidden_mutation_tools"]),
        "",
        "## Repo-Present Not Exposed",
        "",
        *(f"- `{tool}`" for tool in groups["repo_present_not_exposed"]),
        "",
        "## Blocked Raw MCP",
        "",
        *(f"- `{tool}`" for tool in groups["blocked_tools"]),
        "",
        "## Matrix",
        "",
        "| Tool | Family | Repo | Exposed | Callable | Operational | Decision | Allowed Mode | Mutation Risk | Handler |",
        "|------|--------|------|---------|----------|-------------|----------|--------------|---------------|---------|",
    ]

    for entry in result["matrix"]:
        lines.append(
            "| "
            f"{entry['tool_name']} | {entry['tool_family']} | "
            f"{'Y' if entry['repo_present'] else '-'} | "
            f"{'Y' if entry['exposed'] else '-'} | "
            f"{entry['callable_status']} | {entry['operational_status']} | "
            f"{entry['decision']} | {entry['allowed_mode']} | "
            f"{entry['mutation_risk']} | {entry['handler_path'] or '-'} |"
        )

    lines.extend(
        [
            "",
            "## Evidence Sources",
            "",
            "- Repo: `tools/mcp/registry.py`, `tools/mcp/context_bridge.py`, `tools/mcp/permission_guard.py`",
            "- Inventory: `artifacts/context_tool_inventory/tool_inventory.json`",
            "- Contracts: `docs/surrealdb/context-intelligence-permission-matrix-v0.md`, `docs/surrealdb/context-mcp-bridge-contract.md`",
            f"- Official SurrealDB MCP: `{UPSTREAM_MCP_DOC}`",
            f"- Official SurrealDB Agent Skills: `{UPSTREAM_AGENT_SKILLS_DOC}`",
            f"- Official SurrealDB Agent Rules: `{UPSTREAM_AGENT_RULES_DOC}`",
            "",
            "## Guardrails",
            "",
            "- No DB/MCP writes are authorized by this document.",
            "- `callable_status`, `exposed`, `repo_present`, and `operational_status` stay separate fields.",
            "- No `DB_BACKED_READONLY_PROVEN` claim is emitted without adapter evidence.",
            "- LR remains NO-GO.",
        ]
    )
    return "\n".join(lines) + "\n"


def export_mcp_access_boundary_json(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def export_mcp_access_boundary_markdown(
    result: dict[str, Any], output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _render_markdown(result, "# CDB MCP Access Boundary"),
        encoding="utf-8",
    )


def generate_default_artifacts() -> dict[str, Any]:
    result = build_mcp_access_boundary()
    export_mcp_access_boundary_json(
        result, REPO_ROOT / "artifacts/mcp/mcp_access_boundary_matrix.json"
    )
    export_mcp_access_boundary_markdown(
        result, REPO_ROOT / "artifacts/mcp/mcp_access_boundary_matrix.md"
    )
    (REPO_ROOT / "docs/surrealdb/CDB_MCP_ACCESS_BOUNDARY.md").write_text(
        _render_markdown(result, "# CDB MCP Access Boundary"),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    generate_default_artifacts()
