"""Agent Read Order and Bootloader contract tests (#3865).

Static, repo-local contract checks for:
- Root pointer AGENTS.md -> agents/AGENTS.md
- Complete canonical Read Order from agents/AGENTS.md
- Status surface classification (ledger vs live truth vs stale snapshots)
- trade-capable never implies Live-Go / LR-Go
- Context Brain fallback reason enum and misclassification guard
- Fail-closed when canonical reads are missing on disk

No network, Docker, GitHub live, or Context DB required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.agents._bootloader_read_order_helpers import (
    CANONICAL_REGISTRY_READ_ORDER,
    REPO_FALLBACK_REASONS,
    STALE_STATUS_SNAPSHOTS,
    missing_canonical_reads,
    parse_read_order_from_agents_registry,
    root_pointer_targets_agents_registry,
)
from tools.mcp.context_bridge import (
    READINESS_MINIMUM_READS,
    _missing_canon_reads_on_disk,
    _normalize_brain_evidence_fields,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

AGENTS_ROOT_ANCHORS = (
    "agents/AGENTS.md",
    "trade-capable",
    "orthogonal",
    "LR",
    "NO-GO",
    "historische Snapshots",
    "nicht der aktuelle Gesamtstatus",
    "Stage-Aussagen nie als LR-Go/No-Go",
)

AGENTS_REGISTRY_STATUS_ANCHORS = (
    "Status Surfaces",
    "is a ledger, not live truth",
    "Historische Snapshots",
    "orthogonal zum LR-System",
    "LR-050",
    "NO-GO",
    "Board-Stage darf nie als implizite Live-Freigabe",
)

CONTROL_REGISTER_ANCHORS = (
    "trade-capable",
    "NO-GO",
    "LR-Verdikt nie aus einer Board-Stage ableiten",
    "kein Live-Kapital",
)

LR_AUDIT_ANCHORS = (
    "NO-GO",
    "Go/No-Go",
    "No real trades without human gate",
)


# ---------------------------------------------------------------------------
# Root pointer + Read Order
# ---------------------------------------------------------------------------


def test_agents_root_pointer_resolves_to_agents_registry() -> None:
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert root_pointer_targets_agents_registry(text)
    assert "Kanonische Agenten-Registry" in text or "kanonische" in text.lower()


def test_agents_registry_exposes_complete_required_read_order() -> None:
    text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    parsed = parse_read_order_from_agents_registry(text)
    assert parsed == list(CANONICAL_REGISTRY_READ_ORDER)


@pytest.mark.parametrize("relative_path", CANONICAL_REGISTRY_READ_ORDER)
def test_required_read_order_files_exist_on_disk(relative_path: str) -> None:
    path = REPO_ROOT / relative_path
    assert path.is_file(), f"missing canonical read-order file: {relative_path}"


def test_missing_canonical_read_triggers_fail_closed_helper() -> None:
    """Simulated missing canon read must surface via fail-closed helper."""
    fake_root = REPO_ROOT / "tests" / "fixtures" / "nonexistent_bootloader_root"
    missing = missing_canonical_reads(fake_root, CANONICAL_REGISTRY_READ_ORDER)
    assert missing == list(CANONICAL_REGISTRY_READ_ORDER)


def test_context_bridge_minimum_reads_present_on_disk() -> None:
    missing = _missing_canon_reads_on_disk(REPO_ROOT, READINESS_MINIMUM_READS)
    assert missing == [], f"readiness minimum reads missing: {missing}"


# ---------------------------------------------------------------------------
# Status surfaces: ledger vs live truth vs stale snapshots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("needle", AGENTS_ROOT_ANCHORS)
def test_agents_root_status_semantics_anchors(needle: str) -> None:
    text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert needle in text, f"AGENTS.md missing status anchor: {needle!r}"


@pytest.mark.parametrize("needle", AGENTS_REGISTRY_STATUS_ANCHORS)
def test_agents_registry_status_surface_anchors(needle: str) -> None:
    text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    assert needle in text, f"agents/AGENTS.md missing status anchor: {needle!r}"


def test_current_status_marked_as_ledger_not_live_truth() -> None:
    agents_text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    root_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "is a ledger, not live truth" in agents_text
    assert "CURRENT_STATUS.md" in root_text
    assert "Engineering-Status" in root_text or "Repo-/Engineering-Status" in root_text


@pytest.mark.parametrize("stale_path", STALE_STATUS_SNAPSHOTS)
def test_stale_status_snapshots_not_promoted_as_ssot(stale_path: str) -> None:
    agents_text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    root_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert stale_path in agents_text
    assert "Historische" in agents_text or "historische" in agents_text
    assert stale_path in root_text
    assert "historische" in root_text.lower() or "nicht der aktuelle" in root_text


@pytest.mark.parametrize("needle", CONTROL_REGISTER_ANCHORS)
def test_control_register_trade_capable_not_live_go(needle: str) -> None:
    text = (REPO_ROOT / "docs" / "runbooks" / "CONTROL_REGISTER.md").read_text(
        encoding="utf-8"
    )
    assert needle in text, f"CONTROL_REGISTER.md missing anchor: {needle!r}"


@pytest.mark.parametrize("needle", LR_AUDIT_ANCHORS)
def test_lr_audit_status_required_for_go_no_go_semantics(needle: str) -> None:
    text = (
        REPO_ROOT
        / "docs"
        / "live-readiness"
        / "LR-AUDIT-STATUS-2026-03-05.md"
    ).read_text(encoding="utf-8")
    assert needle in text, f"LR-AUDIT-STATUS missing anchor: {needle!r}"


def test_trade_capable_stage_never_implies_lr_go_in_registry() -> None:
    text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    assert "trade-capable" in text
    assert "orthogonal" in text.lower() or "orthogonal" in text
    assert "Live-Go" in text or "Live-Kapital" in text or "Live-Freigabe" in text
    assert "NO-GO" in text


# ---------------------------------------------------------------------------
# Context Brain fallback reason enum + misclassification guard
# ---------------------------------------------------------------------------


def test_repo_fallback_reason_enum_documented_in_agents_registry() -> None:
    text = (REPO_ROOT / "agents" / "AGENTS.md").read_text(encoding="utf-8")
    for reason in REPO_FALLBACK_REASONS:
        assert reason in text, f"agents/AGENTS.md missing fallback reason: {reason!r}"


@pytest.mark.parametrize(
    "brain_source,brain_status,operator_trust_level,records_found,expected_reason",
    [
        ("repo-only", "not-used", "LOW", 0, "insufficient_evidence"),
        ("unavailable", "not-used", "BLOCKED", 0, "unavailable"),
        ("unavailable", "blocked", "BLOCKED", 0, "tool_blocked"),
    ],
)
def test_tool_available_without_records_is_not_unavailable(
    brain_source: str,
    brain_status: str,
    operator_trust_level: str,
    records_found: int,
    expected_reason: str,
) -> None:
    """Available tool + zero records must not classify as unavailable (#3865)."""
    fields = _normalize_brain_evidence_fields(
        brain_source=brain_source,
        brain_status=brain_status,
        operator_trust_level=operator_trust_level,
        records_found=records_found,
    )
    assert fields["repo_fallback_reason"] in REPO_FALLBACK_REASONS
    assert fields["repo_fallback_reason"] == expected_reason
    if brain_source == "repo-only":
        assert fields["context_tool_status"] == "available"
        assert fields["repo_fallback_reason"] != "unavailable"


def test_hold_bootloader_evidence_misclassified_anchor_present() -> None:
    for rel in ("agents/AGENTS.md", "AGENTS.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED" in text
