"""
Read-only Permission Guardrails for Context MCP Tools.

Enforces three-layer defense-in-depth for #2099:
1. Registry Gate: non-read-only ToolDefinitions are blocked.
2. Execute Gate: ToolDefinition.read_only + Input Gate before handler dispatch.
3. Input Gate: mutative query/operation patterns in tool parameters are blocked.

The Input Gate applies pattern scanning only to query/command tools
(context.search, context.trace, context.explain_source, context.package,
context.show_snapshot, context.show_audit) whose free-text parameters could
contain SQL/SurrealQL injection or command vectors.

Structural tools (context.readiness, context.briefing, context.self_explain,
context.stop_resolver, context.required_reads, cdb_context_impact) are exempt from input scanning
because their handlers already validate inputs with operation_mode enums,
stop_conditions, and structural field checks. Task descriptions like
"Deploy system" or "Update config" are legitimate scope descriptions
that the readiness/briefing handlers evaluate correctly.

This module does NOT perform any writes, runtime actions, or live assertions.
It is a pure, stateless, deterministic guard layer.

Reference: Issue #2099
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

FORBIDDEN_SQL_KEYWORDS: frozenset[str] = frozenset({
    "INSERT",
    "UPDATE",
    "DELETE",
    "CREATE",
    "DROP",
    "ALTER",
    "MUTATE",
    "REPLACE",
    "REMOVE",
    "MERGE",
    "RELATE",
    "DEFINE",
    "REBUILD",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
})

FORBIDDEN_QUERY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bINSERT\b\s", re.IGNORECASE),
    re.compile(r"\bUPDATE\b\s", re.IGNORECASE),
    re.compile(r"\bDELETE\b\s", re.IGNORECASE),
    re.compile(r"\bCREATE\b\s", re.IGNORECASE),
    re.compile(r"\bDROP\b\s", re.IGNORECASE),
    re.compile(r"\bALTER\b\s", re.IGNORECASE),
    re.compile(r"\bMERGE\b\s", re.IGNORECASE),
    re.compile(r"\bRELATE\b\s", re.IGNORECASE),
    re.compile(
        r"\bDEFINE\b\s+(TABLE|FUNCTION|INDEX|TOKEN|SCOPE| PARAM)", re.IGNORECASE
    ),
    re.compile(
        r"\bREMOVE\b\s+(TABLE|FUNCTION|INDEX|TOKEN|SCOPE| PARAM)", re.IGNORECASE
    ),
    re.compile(r"\bREBUILD\b\s", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b\s", re.IGNORECASE),
    re.compile(r"\bGRANT\b\s", re.IGNORECASE),
    re.compile(r"\bREVOKE\b\s", re.IGNORECASE),
    re.compile(r"\bMUTATE\b\s", re.IGNORECASE),
)

FORBIDDEN_RUNTIME_OPERATIONS: frozenset[str] = frozenset({
    "git_commit",
    "git_push",
    "git_merge",
    "git_rebase",
    "git_reset",
    "git_checkout_write",
    "issue_create",
    "issue_update",
    "issue_close",
    "issue_comment",
    "issue_label",
    "pr_create",
    "pr_merge",
    "pr_review_submit",
    "docker_build",
    "docker_push",
    "docker_compose_up",
    "db_migration_apply",
    "db_schema_mutate",
    "file_write",
    "file_delete",
    "file_move",
    "secret_write",
    "secret_rotate",
    "env_write",
    "deploy",
    "release",
    "publish",
})

FORBIDDEN_REPO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bgit\s+(commit|push|merge|rebase|reset|checkout\b)", re.IGNORECASE
    ),
    re.compile(
        r"\bgh\s+(issue|pr|release)\s+(create|close|merge|edit)", re.IGNORECASE
    ),
    re.compile(r"\bdocker\s+(build|push|compose\s+up)", re.IGNORECASE),
)

INPUT_SCAN_TOOLS: frozenset[str] = frozenset({
    "context.search",
    "context.trace",
    "context.explain_source",
    "context.package",
    "context.show_snapshot",
    "context.show_audit",
})

INPUT_SCAN_EXEMPT_TOOLS: frozenset[str] = frozenset({
    "context.readiness",
    "context.briefing",
    "cdb_context_briefing",
    "context.self_explain",
    "context.stop_resolver",
    "context.required_reads",
    "cdb_context_impact",
    # Wave-14 read-only record context tools (#2122).
    # These tools process evidence/claim/memory/decision records whose titles
    # and content legitimately contain words like "Create", "Update", "Delete",
    # "migration", "runbook" — blocking them via mutation scan would make the
    # tools unusable for normal context records.
    "cdb_context_evidence_resolve",
    "cdb_context_claim_resolve",
    "cdb_context_memory_get",
    "cdb_context_trust_summary",
    "cdb_context_decision_history",
    "cdb_context_decision_replay",
    # Wave-15 contradiction scan MCP tool (#2148).
    # Processes doc/code/decision/claim/evidence records whose content legitimately
    # contains words like "Create", "Update", "Delete", "migration", "runbook".
    # The tool is read-only and fail-closed; the scan service itself enforces
    # no-write, no-network, no-auto-fix guardrails.
    "cdb_context_contradictions",
    # Wave-16-C stale context MCP tool (#2157).
    # Processes scan bundles whose source paths, reasons, and recommended_refresh
    # strings legitimately contain words like "Create", "Update", "Delete",
    # "migration", "runbook". The tool is read-only, bundle-driven, and
    # fail-closed; the scan service enforces no-write, no-network, no-auto-fix.
    "cdb_context_stale",
    # Wave-17-C scope drift MCP tool (#2165).
    # Processes scan bundles including generated_findings.content whose
    # legitimate values are exactly the write-intent strings the firewall
    # scans for (e.g. "commit", "push", "create file", "git push").
    # The tool is read-only, bundle-driven, and fail-closed; the scope drift
    # firewall service enforces no-write, no-network, no-auto-fix guardrails.
    "cdb_context_scope_drift",
})


@dataclass(frozen=True)
class PermissionCheckResult:
    code: str
    message: str
    tool_name: str
    details: dict[str, Any] = field(default_factory=dict)


class PermissionGuard:
    """
    Stateless, deterministic permission guard for Context MCP Tools.

    All checks are pure functions — no IO, no state, no side effects.
    """

    @staticmethod
    def check_tool_definition(
        tool_name: str,
        read_only: bool,
    ) -> Optional[PermissionCheckResult]:
        if not read_only:
            return PermissionCheckResult(
                code="non_read_only_tool",
                message=(
                    f"Tool {tool_name} is not read-only. "
                    "Only read-only tools are permitted in the Context MCP layer."
                ),
                tool_name=tool_name,
                details={"read_only": read_only},
            )
        return None

    @staticmethod
    def check_registry_consistency(
        tool_entries: dict[str, Any],
    ) -> Optional[PermissionCheckResult]:
        non_read_only = [
            name
            for name, tool in tool_entries.items()
            if not getattr(tool, "read_only", False)
        ]
        if non_read_only:
            return PermissionCheckResult(
                code="registry_inconsistency",
                message=(
                    f"Registry contains non-read-only tools: {non_read_only}. "
                    "All Context MCP tools must be read-only."
                ),
                tool_name="__registry__",
                details={"non_read_only_tools": non_read_only},
            )
        return None

    @staticmethod
    def check_tool_inputs(
        tool_name: str,
        parameters: dict[str, Any],
    ) -> list[PermissionCheckResult]:
        if tool_name in INPUT_SCAN_EXEMPT_TOOLS:
            return []
        should_scan = tool_name in INPUT_SCAN_TOOLS
        results: list[PermissionCheckResult] = []

        for key, value in _walk_parameters(parameters):
            if isinstance(value, str):
                violations = _scan_string(value, tool_name, key, should_scan)
                results.extend(violations)

        return results

    @staticmethod
    def scan_parameters_for_mutations(
        parameters: dict[str, Any],
        tool_name: str = "__unknown__",
    ) -> list[PermissionCheckResult]:
        return PermissionGuard.check_tool_inputs(tool_name, parameters)


def _walk_parameters(
    params: dict[str, Any], prefix: str = "",
) -> list[tuple[str, Any]]:
    flat: list[tuple[str, Any]] = []
    for key, value in params.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.extend(_walk_parameters(value, path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    flat.extend(_walk_parameters(item, f"{path}[{i}]"))
                elif isinstance(item, str):
                    flat.append((f"{path}[{i}]", item))
        else:
            flat.append((path, value))
    return flat


def _scan_string(
    value: str, tool_name: str, param_path: str, full_scan: bool,
) -> list[PermissionCheckResult]:
    results: list[PermissionCheckResult] = []
    upper = value.strip().upper()

    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if keyword in upper and len(value.strip()) < 500:
            boundary = r"\b" + keyword + r"\b"
            if re.search(boundary, value, re.IGNORECASE):
                nearby = value[:120]
                results.append(
                    PermissionCheckResult(
                        code="forbidden_keyword",
                        message=(
                            f"Tool {tool_name} parameter {param_path} contains "
                            f"forbidden keyword '{keyword}'. "
                            "Mutative operations are not permitted "
                            "in Context MCP tools."
                        ),
                        tool_name=tool_name,
                        details={
                            "parameter": param_path,
                            "keyword": keyword,
                            "snippet": nearby,
                        },
                    )
                )
                break

    for pattern in FORBIDDEN_QUERY_PATTERNS:
        if pattern.search(value):
            nearby = value[:120]
            results.append(
                PermissionCheckResult(
                    code="forbidden_query_pattern",
                    message=(
                        f"Tool {tool_name} parameter {param_path} matches "
                        f"a forbidden query pattern. Mutative query operations "
                        f"are not permitted in Context MCP tools."
                    ),
                    tool_name=tool_name,
                    details={
                        "parameter": param_path,
                        "pattern": pattern.pattern,
                        "snippet": nearby,
                    },
                )
            )
            break

    if full_scan:
        for runtime_op in FORBIDDEN_RUNTIME_OPERATIONS:
            if runtime_op in value.lower():
                results.append(
                    PermissionCheckResult(
                        code="forbidden_runtime_operation",
                        message=(
                            f"Tool {tool_name} parameter {param_path} contains "
                            f"forbidden runtime operation '{runtime_op}'. "
                            f"Repo/GitHub/Runtime write operations are not "
                            f"permitted in Context MCP tools."
                        ),
                        tool_name=tool_name,
                        details={
                            "parameter": param_path,
                            "operation": runtime_op,
                            "snippet": value[:120],
                        },
                    )
                )
                break

    if full_scan:
        for repo_pattern in FORBIDDEN_REPO_PATTERNS:
            if repo_pattern.search(value):
                nearby = value[:120]
                results.append(
                    PermissionCheckResult(
                        code="forbidden_repo_pattern",
                        message=(
                            f"Tool {tool_name} parameter {param_path} matches "
                            f"a forbidden repo/GitHub pattern. "
                            f"Repo write operations are not permitted "
                            f"in Context MCP tools."
                        ),
                        tool_name=tool_name,
                        details={
                            "parameter": param_path,
                            "pattern": repo_pattern.pattern,
                            "snippet": nearby,
                        },
                    )
                )
                break

    return results
