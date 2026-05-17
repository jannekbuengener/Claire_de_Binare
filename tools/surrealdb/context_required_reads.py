"""Required Reads Resolver v1 — side-effect-free domain component.

Issues:
    #2106 — Implement required reads resolver v1
    Parent: #2103 (Wave-13)
    Epic: #1976

This module implements a deterministic, fail-closed Required Reads Resolver.
It derives prioritized required reads from task scope, target issue, target
paths, target symbols, and operation mode.

Design intent:
    Pure domain logic. No DB access. No MCP. No networking. No GitHub calls.
    Input: task_scope + target_issue + paths/symbols + operation_mode.
    Output: list of structured RequiredRead dicts with path/priority/reason/
            source_ref/available/warning.
    Deterministic: same inputs → same outputs.
    Fail-closed: unsafe paths → available=false + warning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MINIMUM_READS: list[dict[str, str]] = [
    {
        "path": "AGENTS.md",
        "reason": "Root pointer and session compass for all agent work",
        "source_ref": "#2021 §6.3",
    },
    {
        "path": "agents/AGENTS.md",
        "reason": "Canonical agent registry with read order and status surfaces",
        "source_ref": "#2021 §6.3",
    },
    {
        "path": "agents/OPEN_CODE_AGENTS.md",
        "reason": "OpenCode shared contract, skill routing, and trust rules",
        "source_ref": "#2021 §6.3",
    },
    {
        "path": "docs/runbooks/CONTROL_REGISTER.md",
        "reason": "Board stage, operating focus, and control context",
        "source_ref": "#2021 §6.3",
    },
    {
        "path": "CURRENT_STATUS.md",
        "reason": "Repo/engineering status ledger and session history",
        "source_ref": "#2021 §6.3",
    },
    {
        "path": "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
        "reason": "Live-readiness SSOT — Go/No-Go verdict for Echtgeld",
        "source_ref": "#2021 §6.3",
    },
]

DOMAIN_READS: dict[str, list[dict[str, str]]] = {
    "governance": [
        {
            "path": "knowledge/governance/CDB_CONSTITUTION.md",
            "reason": "System constitution — highest governance authority",
            "source_ref": "agents/AGENTS.md read order",
        },
        {
            "path": "knowledge/governance/CDB_GOVERNANCE.md",
            "reason": "Roles, rights, zones, and change control",
            "source_ref": "agents/AGENTS.md read order",
        },
        {
            "path": "knowledge/governance/CDB_AGENT_POLICY.md",
            "reason": "Agent operating rules, single-writer locks, write gates",
            "source_ref": "agents/AGENTS.md read order",
        },
        {
            "path": "knowledge/governance/SYSTEM_INVARIANTS.md",
            "reason": "Non-negotiable system contracts and deterministic behaviour",
            "source_ref": "agents/AGENTS.md read order",
        },
        {
            "path": "knowledge/governance/DELIVERY_APPROVED.yaml",
            "reason": "Human-controlled delivery gate — agents must not modify",
            "source_ref": "AGENTS.md",
        },
    ],
    "surrealdb": [
        {
            "path": "docs/surrealdb/context-package-model-v1.md",
            "reason": "Context Package model — structured retrieval output contract",
            "source_ref": "#2016",
        },
        {
            "path": "docs/surrealdb/context-agent-briefing-schema-v1.md",
            "reason": "Agent Briefing schema v1 — request/result contract",
            "source_ref": "#2104",
        },
        {
            "path": "docs/surrealdb/context-action-readiness-contract.md",
            "reason": "Action readiness contract — status model and required checks",
            "source_ref": "#2021",
        },
    ],
    "knowledge": [
        {
            "path": "knowledge/CDB_KNOWLEDGE_HUB.md",
            "reason": "Shared decisions and agent handoffs",
            "source_ref": "agents/AGENTS.md read order",
        },
    ],
    "docs": [
        {
            "path": "docs/meta/WORKING_REPO_CANON.md",
            "reason": "Working repo canon matrix and status SSOT rule",
            "source_ref": "agents/AGENTS.md read order",
        },
    ],
    "runbooks": [
        {
            "path": "knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md",
            "reason": "Control board runbook with stage mapping and board rules",
            "source_ref": "AGENTS.md",
        },
    ],
    "risk": [
        {
            "path": "knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md",
            "reason": "Risk governance — control board rules and limits",
            "source_ref": "AGENTS.md",
        },
    ],
    "trading": [
        {
            "path": "knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md",
            "reason": "Trading scope — stage mapping and execution guardrails",
            "source_ref": "AGENTS.md",
        },
    ],
    "ci": [
        {
            "path": ".github/workflows/ci.yml",
            "reason": "CI/CD primary pipeline with test and build steps",
            "source_ref": "#2021 §6.5",
        },
        {
            "path": ".github/workflows/policy-gate.yml",
            "reason": "Policy gate enforcing branch and PR rules",
            "source_ref": "#2021 §6.5",
        },
        {
            "path": ".github/workflows/docs-conflict-guard.yml",
            "reason": "Documentation conflict detection guard",
            "source_ref": "#2021 §6.5",
        },
    ],
    "mcp": [
        {
            "path": "tools/mcp/registry.py",
            "reason": "Context MCP tool registry with all tool definitions",
            "source_ref": "tools/mcp/registry.py",
        },
        {
            "path": "tools/mcp/context_bridge.py",
            "reason": "Context MCP bridge with tool handlers",
            "source_ref": "tools/mcp/context_bridge.py",
        },
    ],
}

DOMAIN_KEYWORD_MAP: dict[str, list[str]] = {
    "governance": [
        "governance", "govern", "policy", "constitution", "agent policy",
        "invariant", "delivery approved",
    ],
    "surrealdb": [
        "surrealdb", "surreal", "context intelligence", "cis",
        "context package", "context bridge", "context tool", "context",
        "briefing", "required reads", "stop condition", "impact radar",
        "validation plan",
    ],
    "knowledge": ["knowledge", "decision", "handoff", "audit"],
    "docs": ["docs", "documentation", "runbook", "canon", "meta"],
    "runbooks": ["runbook", "control board", "operating", "cockpit"],
    "risk": ["risk", "drawdown", "exposure", "kill switch", "fail-closed"],
    "trading": ["trading", "execution", "strategy", "trade", "order", "exchange"],
    "ci": ["ci", "cd", "github actions", "pipeline", "check", "ruleset"],
    "mcp": ["mcp", "bridge", "registry", "handler", "tool"],
}

WRITE_MODE_READS: list[dict[str, str]] = [
    {
        "path": "knowledge/governance/CDB_AGENT_POLICY.md",
        "reason": "Write operation — agent policy section 4 (single-writer locks, write gates)",
        "source_ref": "AGENTS.md",
    },
    {
        "path": "knowledge/governance/DELIVERY_APPROVED.yaml",
        "reason": "Write operation — verify human-controlled delivery gate status",
        "source_ref": "AGENTS.md",
    },
    {
        "path": "knowledge/governance/CDB_CONSTITUTION.md",
        "reason": "Write operation — verify no constitution violation",
        "source_ref": "AGENTS.md",
    },
]

VALID_OPERATION_MODES = frozenset({
    "read_only",
    "dry_run",
    "write (code/docs)",
    "write (config/infra)",
    "write (DB/migration)",
    "write (MCP live)",
})


def _is_path_safe(path_str: str, repo_root: Path = REPO_ROOT) -> tuple[bool, Optional[str]]:
    """Check if a repo-relative path is safe to resolve.

    Returns (is_safe, warning_message_or_None).
    Blocks absolute paths, UNC paths, drive letters, and .. traversal.
    """
    clean = path_str.strip()

    if not clean:
        return False, "empty path string"

    if not isinstance(path_str, str):
        return False, f"path is not a string: {type(path_str).__name__}"

    try:
        p = Path(clean)
    except (TypeError, ValueError):
        return False, f"invalid path: {clean!r}"

    if p.is_absolute():
        return False, f"absolute path blocked: {clean!r}"

    # Detect UNC paths (e.g. \\server\share)
    if clean.startswith("\\\\") or clean.startswith("//"):
        return False, f"UNC path blocked: {clean!r}"

    # Detect drive letters (e.g. C: or C:\)
    if ":" in clean.split("/")[0].split("\\")[0]:
        return False, f"drive-letter path blocked: {clean!r}"

    # Detect path traversal
    parts = p.parts
    for part in parts:
        if part == "..":
            return False, f"path traversal blocked (..): {clean!r}"

    # Resolve to check if it escapes root
    try:
        resolved = (repo_root / p).resolve(strict=False)
        resolved_relative = resolved.relative_to(repo_root)
        if ".." in str(resolved_relative).split("\\"):
            return False, f"path escapes repo root after resolution: {clean!r}"
    except (ValueError, OSError):
        return False, f"path resolution failed: {clean!r}"

    return True, None


def _check_availability(path_str: str, repo_root: Path = REPO_ROOT) -> tuple[bool, Optional[str]]:
    """Check if a repo-relative path exists and is a file.

    Returns (available, warning_or_None).
    """
    clean = path_str.strip()

    is_safe, unsafe_warning = _is_path_safe(clean, repo_root)
    if not is_safe:
        return False, unsafe_warning or "unsafe path"

    try:
        candidate = (repo_root / Path(clean)).resolve(strict=False)
    except (TypeError, ValueError, OSError):
        return False, f"path resolution failed: {clean!r}"

    if not candidate.exists():
        return False, f"file not found: {clean}"

    if not candidate.is_file():
        return False, f"path is not a file: {clean}"

    return True, None


def _detect_domains(task_scope: str, target_paths: list[str]) -> frozenset[str]:
    """Detect domain keywords from task_scope and target_paths.

    Returns a frozenset of domain keys.
    """
    scope_lower = task_scope.lower()
    paths_lower = " ".join(target_paths).lower()

    domains: set[str] = set()
    for domain, keywords in DOMAIN_KEYWORD_MAP.items():
        for kw in keywords:
            if kw.lower() in scope_lower or kw.lower() in paths_lower:
                domains.add(domain)
                break

    return frozenset(domains)


def _deduplicate_reads(reads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate reads by path, keeping the highest-priority entry.

    Priority order: must_read > should_read > optional.
    """
    priority_order: dict[str, int] = {
        "must_read": 0,
        "should_read": 1,
        "optional": 2,
    }
    seen: dict[str, dict[str, Any]] = {}
    for read in reads:
        path = read["path"]
        if path in seen:
            existing_prio = priority_order.get(seen[path]["priority"], 99)
            new_prio = priority_order.get(read["priority"], 99)
            if new_prio < existing_prio:
                seen[path] = read
        else:
            seen[path] = read

    result = list(seen.values())
    result.sort(key=lambda r: priority_order.get(r["priority"], 99))
    return result


def _build_read_entry(
    path: str,
    priority: str,
    reason: str,
    source_ref: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Build a single RequiredRead dict with availability check."""
    available, warning = _check_availability(path, repo_root)
    return {
        "path": path,
        "priority": priority,
        "reason": reason,
        "source_ref": source_ref,
        "available": available,
        "warning": warning,
    }


def resolve_required_reads(
    task_scope: str,
    target_issue: Optional[str],
    target_paths: Optional[list[str]],
    target_symbols: Optional[list[str]],
    operation_mode: str,
    target_concepts: Optional[list[str]] = None,
    repo_root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Resolve prioritized required reads from task scope and context.

    Args:
        task_scope: What the agent is asked to do (one concise sentence).
        target_issue: GitHub issue number (e.g. "#2106") or None.
        target_paths: File paths or glob patterns in scope.
        target_symbols: Code symbols (functions, classes, modules) in scope.
        operation_mode: read_only | dry_run | write (code/docs) | etc.
        target_concepts: Optional domain concepts from CIS ontology.
        repo_root: Override repo root for testing. Defaults to REPO_ROOT.

    Returns:
        List of RequiredRead dicts, each with:
        path, priority, reason, source_ref, available, warning.
    """
    root = repo_root if repo_root is not None else REPO_ROOT

    task_scope = task_scope.strip() if isinstance(task_scope, str) else ""
    paths = [p.strip() for p in (target_paths or []) if isinstance(p, str) and p.strip()]
    symbols = [s.strip() for s in (target_symbols or []) if isinstance(s, str) and s.strip()]
    concepts = [c.strip() for c in (target_concepts or []) if isinstance(c, str) and c.strip()]
    issue = target_issue.strip() if target_issue and isinstance(target_issue, str) else None

    reads: list[dict[str, Any]] = []

    # --- Layer 1: Minimum baseline (always must_read) ---
    for entry in MINIMUM_READS:
        reads.append(
            _build_read_entry(
                path=entry["path"],
                priority="must_read",
                reason=entry["reason"],
                source_ref=entry["source_ref"],
                repo_root=root,
            )
        )

    # --- Layer 2: Domain-specific reads from scope/paths ---
    scope_text = task_scope + " " + " ".join(concepts)
    detected_domains = _detect_domains(scope_text, paths)

    for domain in sorted(detected_domains):
        domain_entries = DOMAIN_READS.get(domain, [])
        for entry in domain_entries:
            reads.append(
                _build_read_entry(
                    path=entry["path"],
                    priority="should_read",
                    reason=entry["reason"],
                    source_ref=entry["source_ref"],
                    repo_root=root,
                )
            )

    # --- Layer 3: Issue-driven reads ---
    if issue:
        issue_lower = issue.lower()
        for domain, keywords in DOMAIN_KEYWORD_MAP.items():
            if any(kw.lower() in issue_lower for kw in keywords):
                domain_entries = DOMAIN_READS.get(domain, [])
                for entry in domain_entries:
                    reads.append(
                        _build_read_entry(
                            path=entry["path"],
                            priority="should_read",
                            reason=f"Issue {issue} — {entry['reason']}",
                            source_ref=entry["source_ref"],
                            repo_root=root,
                        )
                    )
                break

    # --- Layer 4: Path-driven reads (READMEs, __init__.py in target tree) ---
    for path_str in paths[:5]:
        is_safe, _ = _is_path_safe(path_str)
        if not is_safe:
            continue

        try:
            p = Path(path_str)
        except (TypeError, ValueError):
            continue

        if p.suffix in (".py", ".md", ".yaml", ".yml", ".json", ".toml"):
            parent = p.parent
            for candidate_name in ("README.md", "readme.md", "__init__.py"):
                candidate = str(parent / candidate_name).replace("\\", "/")
                reads.append(
                    _build_read_entry(
                        path=candidate,
                        priority="optional",
                        reason=f"Adjacent documentation for target path: {path_str}",
                        source_ref=path_str,
                        repo_root=root,
                    )
                )

    # --- Layer 5: Target symbols (no invented file paths) ---
    if symbols:
        for sym in symbols[:10]:
            reads.append(
                {
                    "path": f"<symbol>{sym}</symbol>",
                    "priority": "optional",
                    "reason": (
                        f"Target symbol: {sym}. "
                        "Cannot derive file path from symbol alone — "
                        "symbol-to-path mapping requires SurrealDB index (not yet available)."
                    ),
                    "source_ref": "target_symbols",
                    "available": False,
                    "warning": (
                        "Symbol-to-file-path mapping not available in v1. "
                        "Use context.search to locate containing file."
                    ),
                }
            )

    # --- Layer 6: Target concepts (reference to docs domain) ---
    if concepts:
        for concept in concepts[:5]:
            concept_lower = concept.lower()
            mapped = False
            for domain, keywords in DOMAIN_KEYWORD_MAP.items():
                if any(kw.lower() in concept_lower for kw in keywords):
                    for entry in DOMAIN_READS.get(domain, []):
                        reads.append(
                            _build_read_entry(
                                path=entry["path"],
                                priority="should_read",
                                reason=f"Concept '{concept}' → {entry['reason']}",
                                source_ref=entry["source_ref"],
                                repo_root=root,
                            )
                        )
                    mapped = True
                    break
            if not mapped:
                reads.append(
                    {
                        "path": f"<concept>{concept}</concept>",
                        "priority": "optional",
                        "reason": (
                            f"Target concept: {concept}. "
                            "No known documentation mapping for this concept."
                        ),
                        "source_ref": "target_concepts",
                        "available": False,
                        "warning": (
                            f"Concept '{concept}' has no known documentation mapping. "
                            "Use context.search to find related docs."
                        ),
                    }
                )

    # --- Layer 7: Write mode governance reads ---
    if operation_mode.startswith("write"):
        for entry in WRITE_MODE_READS:
            reads.append(
                _build_read_entry(
                    path=entry["path"],
                    priority="must_read",
                    reason=entry["reason"],
                    source_ref=entry["source_ref"],
                    repo_root=root,
                )
            )

    # --- Deduplicate and sort ---
    return _deduplicate_reads(reads)
