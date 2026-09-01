"""Build GitHub APPROVE body and mutation eligibility from approval context (#4505)."""

from __future__ import annotations

from typing import Any


def github_approve_mutation_allowed(envelope: dict[str, Any]) -> tuple[bool, list[str]]:
    """True only when recommendation is APPROVE_RECOMMENDED with exact head binding."""
    rec = envelope.get("recommendation")
    reasons = list(envelope.get("reason_codes") or [])
    if rec != "APPROVE_RECOMMENDED":
        return False, reasons
    fh = envelope.get("final_head_state") if isinstance(envelope.get("final_head_state"), dict) else {}
    subject = envelope.get("subject") if isinstance(envelope.get("subject"), dict) else {}
    head = subject.get("head_sha")
    bound = fh.get("bound_final_head_sha")
    if not isinstance(head, str) or not isinstance(bound, str) or head.lower() != bound.lower():
        return False, reasons + ["BOUND_HEAD_MISMATCH"]
    if fh.get("final_head_ready_for_approval") is not True:
        return False, reasons + ["FINAL_HEAD_NOT_READY"]
    if fh.get("risk") != "LOW":
        return False, reasons + ["RISK_NOT_LOW"]
    return True, reasons


def build_github_approve_body(envelope: dict[str, Any], policy: dict[str, Any] | None = None) -> str:
    """Contract body for cdb_final_head_pr_approval_gate GitHub APPROVE mutation."""
    allowed, _ = github_approve_mutation_allowed(envelope)
    if not allowed:
        raise ValueError("approve body requires APPROVE_RECOMMENDED with bound final head")

    doc = {}
    if policy and isinstance(policy.get("document"), dict):
        doc = policy["document"]
    elif policy:
        doc = policy
    mutation = doc.get("github_approve_mutation") if isinstance(doc.get("github_approve_mutation"), dict) else {}

    subject = envelope.get("subject") if isinstance(envelope.get("subject"), dict) else {}
    head_sha = subject.get("head_sha", "")

    decision = mutation.get("decision_value", "APPROVE")
    risk = mutation.get("risk_value", "LOW")
    verdict = mutation.get("completeness_verdict_value", "MERGE_CANDIDATE")
    blockers = mutation.get("blockers_value", "NONE")
    next_action = mutation.get("required_next_action_value", "HANDOFF_TO_MERGE_AGENT")

    lines = [
        f"DECISION: {decision}",
        f"RISK: {risk}",
        f"HEAD_SHA: {head_sha}",
        f"COMPLETENESS_VERDICT: {verdict}",
        f"BLOCKERS: {blockers}",
        f"REQUIRED_NEXT_ACTION: {next_action}",
    ]
    return "\n".join(lines) + "\n"
