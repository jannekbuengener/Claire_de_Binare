"""Shared helpers for agent bootloader / read-order contract tests (#3865)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_FALLBACK_REASONS: frozenset[str] = frozenset(
    {
        "none",
        "unavailable",
        "stale",
        "contradictory",
        "insufficient_evidence",
        "missing_record",
        "tool_blocked",
    }
)

CANONICAL_REGISTRY_READ_ORDER: tuple[str, ...] = (
    "knowledge/governance/CDB_CONSTITUTION.md",
    "knowledge/governance/CDB_GOVERNANCE.md",
    "knowledge/governance/CDB_AGENT_POLICY.md",
    "knowledge/governance/SYSTEM_INVARIANTS.md",
    "knowledge/CDB_KNOWLEDGE_HUB.md",
    "docs/meta/REPOSITORY_CANON.md",
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "agents/OPEN_CODE_AGENTS.md",
)

STALE_STATUS_SNAPSHOTS: tuple[str, ...] = (
    "PROJECT_STATUS.md",
    "knowledge/CURRENT_STATUS.md",
)

READ_ORDER_ITEM_RE = re.compile(r"^\d+\.\s+`([^`]+)`", re.MULTILINE)


def parse_read_order_from_agents_registry(text: str) -> list[str]:
    """Extract numbered Read Order paths from agents/AGENTS.md."""
    section_match = re.search(
        r"^## Read Order\s*\n(.*?)(?:\n## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if section_match is None:
        return []
    return READ_ORDER_ITEM_RE.findall(section_match.group(1))


def missing_canonical_reads(repo_root: Path, paths: tuple[str, ...]) -> list[str]:
    """Return repo-relative paths that are missing on disk (fail-closed signal)."""
    return [rel for rel in paths if not (repo_root / rel).is_file()]


def root_pointer_targets_agents_registry(agents_root_text: str) -> bool:
    """AGENTS.md must point at agents/AGENTS.md as canonical registry."""
    return "agents/AGENTS.md" in agents_root_text and (
        "[`agents/AGENTS.md`](agents/AGENTS.md)" in agents_root_text
        or "agents/AGENTS.md" in agents_root_text
    )
