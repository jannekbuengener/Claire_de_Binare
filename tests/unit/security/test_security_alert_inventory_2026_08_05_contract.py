"""Contract for 2026-08-05 full code-scanning inventory (#2513 campaign)."""

from __future__ import annotations
import json
from pathlib import Path
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]
REPO = Path(__file__).resolve().parents[3]
INV = REPO / "docs/evidence/security/CDB_SECURITY_ALERT_INVENTORY_2026-08-05.json"
RECON = (
    REPO / "docs/evidence/security/CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-05.json"
)
MD = REPO / "docs/evidence/security/CDB_SECURITY_BACKLOG_RECONCILIATION_2026-08-05.md"
ALLOWED = frozenset(
    {
        "FIX_READY",
        "FIXED_SCAN_VERIFIED",
        "UPSTREAM_BLOCKED",
        "DUPLICATE_CANONICAL_TRACKER",
        "FALSE_POSITIVE_WITH_PROOF",
        "SECRET_OWNER_ACTION_REQUIRED",
        "NEEDS_EVIDENCE",
        "ACCEPTED_RISK_OWNER_DECISION_REQUIRED",
    }
)


def test_inventory_covers_exactly_1010_unique_alerts() -> None:
    data = json.loads(INV.read_text(encoding="utf-8"))
    nums = [a["alert_number"] for a in data["alerts"]]
    assert data["total_open_alerts"] == 1010
    assert len(nums) == 1010
    assert len(set(nums)) == 1010


def test_every_alert_has_disposition_and_root_cause() -> None:
    data = json.loads(INV.read_text(encoding="utf-8"))
    for a in data["alerts"]:
        assert a["disposition"] in ALLOWED
        assert a["root_cause_id"]
        assert a["closure_condition"]


def test_recon_and_markdown_exist_and_forbid_shortcuts() -> None:
    assert RECON.is_file() and MD.is_file()
    md = MD.read_text(encoding="utf-8").lower()
    assert "no alert dismissal" in md or "no dismissals" in md
    assert ".trivyignore" in md
    assert "1010" in MD.read_text(encoding="utf-8")


def test_governance_flags() -> None:
    data = json.loads(INV.read_text(encoding="utf-8"))
    g = data["governance"]
    assert g["dismissals_allowed"] is False
    assert g["trivyignore_growth_allowed"] is False
    assert g["scanner_weakening_allowed"] is False
