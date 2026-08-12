from __future__ import annotations

from pathlib import Path

SKILL = Path(__file__).parents[3] / "docs/skills/cdb-control-intake/SKILL.md"


def test_control_intake_requires_truth_order_and_status_separation() -> None:
    text = SKILL.read_text(encoding="utf-8")

    required = (
        "CONTROL_REGISTER.md",
        "GitHub Issue `#1445` live",
        "#1492",
        "`CURRENT_STATUS.md` als Ledger",
        "LR-AUDIT-STATUS-2026-03-05.md",
        "HOLD_GITHUB_LIVE_EVIDENCE_MISSING",
        "HOLD_STATUS_CLASS_MIXUP",
        "Board stage ist keine LR- oder Echtgeld-Freigabe.",
    )
    assert all(marker in text for marker in required)
    assert text.index("CONTROL_REGISTER.md") < text.index("GitHub Issue `#1445` live")
    assert text.index("GitHub Issue `#1445` live") < text.index("#1492")
    assert text.index("#1492") < text.index("`CURRENT_STATUS.md` als Ledger")
    assert text.index("`CURRENT_STATUS.md` als Ledger") < text.index(
        "LR-AUDIT-STATUS-2026-03-05.md"
    )
