"""Verdict derivation for cdb.agent_run_evidence.v1 (bound data only)."""

from __future__ import annotations

from typing import Any

from tools.agent_control.evidence.codes import (
    REASON_EVIDENCE_INCOMPLETE,
    REASON_NO_DELIVERY_RECEIPT,
    REASON_NON_TERMINAL,
)
from tools.agent_control.lifecycle import TERMINAL_STATES

PASS_REQUIRES_STATE = "PASS"


def derive_verdict(run: dict[str, Any], *, incomplete: bool = False) -> dict[str, Any]:
    state = run.get("state")
    reasons: list[str] = []
    limitations: list[str] = [
        "not_final_ci",
        "not_cdb_local_ci",
        "not_completeness_review",
        "not_approval",
        "not_merge_authority",
        "not_merge_readiness",
        "not_live_go",
        "pilot_store_only",
    ]

    if state not in TERMINAL_STATES:
        return {
            "verdict": "HOLD",
            "reason_codes": [REASON_NON_TERMINAL],
            "limitations": limitations,
        }

    if state == "BLOCKED":
        code = run.get("terminal_code") or "BLOCKED"
        return {
            "verdict": "BLOCKED",
            "reason_codes": [str(code)],
            "limitations": limitations,
        }
    if state == "FAILED":
        code = run.get("terminal_code") or "FAILED"
        return {
            "verdict": "FAILED",
            "reason_codes": [str(code)],
            "limitations": limitations,
        }
    if state == "CANCELLED":
        code = run.get("terminal_code") or "CANCELLED"
        return {
            "verdict": "CANCELLED",
            "reason_codes": [str(code)],
            "limitations": limitations,
        }
    if state == "HOLD":
        code = run.get("terminal_code") or "HOLD"
        return {
            "verdict": "HOLD",
            "reason_codes": [str(code)],
            "limitations": limitations,
        }

    if state != PASS_REQUIRES_STATE:
        return {
            "verdict": "HOLD",
            "reason_codes": [REASON_NON_TERMINAL],
            "limitations": limitations,
        }

    receipt = run.get("delivery_receipt")
    if not isinstance(receipt, dict) or not receipt:
        reasons.append(REASON_NO_DELIVERY_RECEIPT)
    if incomplete:
        reasons.append(REASON_EVIDENCE_INCOMPLETE)

    if reasons:
        return {
            "verdict": "HOLD",
            "reason_codes": reasons,
            "limitations": limitations,
        }

    return {
        "verdict": "PASS",
        "reason_codes": ["DELIVERY_GOALS_MET"],
        "limitations": limitations,
    }
