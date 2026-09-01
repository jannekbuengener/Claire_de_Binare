"""Fail-closed recommendation evaluation for cdb.pr_approval_context.v1."""

from __future__ import annotations

import re
from typing import Any

from tools.agent_control.approval.codes import (
    REASON_ACCEPTANCE_LIFECYCLE_MISMATCH,
    REASON_ACCEPTING_SLICES,
    REASON_APP_ID_MISMATCH,
    REASON_BLOCKING_THREAD,
    REASON_BLOCKING_THREAD_UNKNOWN,
    REASON_BOUND_HEAD_MISMATCH,
    REASON_CHANGES_REQUESTED,
    REASON_CONFLICTING_HEAD,
    REASON_DRAFT_PR,
    REASON_DRIFT,
    REASON_DRIFT_UNKNOWN,
    REASON_FINAL_HEAD_NOT_FROZEN,
    REASON_FINAL_HEAD_NOT_READY,
    REASON_COMPLETENESS_SUBJECT_MISMATCH,
    REASON_COMPLETENESS_VERDICT_MISMATCH,
    REASON_HANDOFF_HEAD_MISMATCH,
    REASON_HANDOFF_BASE_MISMATCH,
    REASON_HANDOFF_PROVENANCE_INCOMPLETE,
    REASON_HANDOFF_SCHEMA_INVALID,
    REASON_INCOMPLETE_SNAPSHOT,
    REASON_INVALID_BASE,
    REASON_INVALID_HEAD,
    REASON_MECHANISM_MISMATCH,
    REASON_MERGE_CANDIDATE_WITHOUT_FINAL_HEAD,
    REASON_MISSING_BASE,
    REASON_MISSING_DRAFT_STATE,
    REASON_MISSING_FINAL_HEAD_STATE,
    REASON_MISSING_HEAD,
    REASON_PROTECTION_INCOMPLETE,
    REASON_REQUIRED_CHECK_FAILED,
    REASON_REQUIRED_CHECK_MISSING,
    REASON_REQUIRED_CHECK_PENDING,
    REASON_RISK_NOT_LOW,
    REASON_SELF_DECLARED_PRODUCER_REJECTED,
    REASON_STALE_HEAD,
    REASON_UNTRUSTED_HANDOFF,
    REASON_UNKNOWN_MECHANISM,
    REASON_UNKNOWN_REVIEW,
    SHA40,
)

_SHA_RE = re.compile(SHA40)


def validate_subject(snapshot: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Extract and validate subject SHAs. Returns (subject, reason_codes)."""
    reasons: list[str] = []
    pr = snapshot.get("pr") if isinstance(snapshot.get("pr"), dict) else {}
    head = pr.get("head_sha")
    base = pr.get("base_sha")
    number = pr.get("number")

    if head is None or head == "":
        reasons.append(REASON_MISSING_HEAD)
    elif not isinstance(head, str) or not _SHA_RE.fullmatch(head):
        reasons.append(REASON_INVALID_HEAD)

    if base is None or base == "":
        reasons.append(REASON_MISSING_BASE)
    elif not isinstance(base, str) or not _SHA_RE.fullmatch(base):
        reasons.append(REASON_INVALID_BASE)

    # Conflicting head sources across snapshot surfaces.
    head_candidates: list[str] = []
    if isinstance(head, str) and _SHA_RE.fullmatch(head):
        head_candidates.append(head)
    for key in ("head_sha", "headRefOid", "commit_sha"):
        alt = snapshot.get(key)
        if isinstance(alt, str) and alt:
            head_candidates.append(alt)
    unique = {h.lower() for h in head_candidates if isinstance(h, str)}
    if len(unique) > 1:
        reasons.append(REASON_CONFLICTING_HEAD)

    subject = {
        "pr_number": int(number) if isinstance(number, int) else number,
        "head_sha": head if isinstance(head, str) else "",
        "base_sha": base if isinstance(base, str) else "",
    }
    return subject, reasons


def detect_stale_head(subject: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    """Return STALE_HEAD reason when checks/reviews bound to a different head."""
    head = subject.get("head_sha")
    if not isinstance(head, str) or not _SHA_RE.fullmatch(head):
        return []
    reasons: list[str] = []
    checks = snapshot.get("checks") if isinstance(snapshot.get("checks"), list) else []
    for item in checks:
        if not isinstance(item, dict):
            continue
        source = item.get("source_sha")
        if isinstance(source, str) and source and source != head:
            reasons.append(REASON_STALE_HEAD)
            break
    previous = snapshot.get("previous_context_head_sha")
    if isinstance(previous, str) and previous and previous != head:
        if REASON_STALE_HEAD not in reasons:
            reasons.append(REASON_STALE_HEAD)
    return reasons


def match_required_checks(
    snapshot: dict[str, Any], subject: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Typed required-check matching against injected protection snapshot."""
    reasons: list[str] = []
    protection = (
        snapshot.get("protection")
        if isinstance(snapshot.get("protection"), dict)
        else {}
    )
    required = protection.get("required_checks")
    if not isinstance(required, list) or not required:
        reasons.append(REASON_PROTECTION_INCOMPLETE)
        return [], reasons

    observed = (
        snapshot.get("checks") if isinstance(snapshot.get("checks"), list) else []
    )
    observed_items = [c for c in observed if isinstance(c, dict)]
    head = subject.get("head_sha")
    out: list[dict[str, Any]] = []

    for req in required:
        if not isinstance(req, dict):
            reasons.append(REASON_INCOMPLETE_SNAPSHOT)
            continue
        name = req.get("name")
        mech = req.get("mechanism", "unknown")
        req_app = req.get("app_id")
        if not isinstance(name, str) or not name:
            reasons.append(REASON_INCOMPLETE_SNAPSHOT)
            continue
        if mech not in ("check_run", "commit_status", "unknown"):
            mech = "unknown"

        match = _find_observation(
            observed_items, name=name, mechanism=mech, app_id=req_app
        )
        entry: dict[str, Any] = {
            "name": name,
            "mechanism": mech if isinstance(mech, str) else "unknown",
            "status": "missing",
            "matches_protection": False,
        }
        if req_app is not None:
            entry["app_id"] = req_app

        if match is None:
            # Same-name wrong mechanism must not satisfy protection.
            same_name = next((c for c in observed_items if c.get("name") == name), None)
            if same_name is not None:
                obs_mech = same_name.get("mechanism", "unknown")
                entry["status"] = str(same_name.get("status") or "observed")
                if same_name.get("conclusion") is not None:
                    entry["conclusion"] = same_name.get("conclusion")
                if same_name.get("source_sha") is not None:
                    entry["source_sha"] = same_name.get("source_sha")
                if same_name.get("app_id") is not None:
                    entry["app_id"] = same_name.get("app_id")
                if obs_mech != mech:
                    reasons.append(REASON_MECHANISM_MISMATCH)
                    entry["matches_protection"] = False
                elif req_app is not None and same_name.get("app_id") != req_app:
                    reasons.append(REASON_APP_ID_MISMATCH)
                    entry["matches_protection"] = False
                else:
                    reasons.append(REASON_REQUIRED_CHECK_MISSING)
            else:
                reasons.append(REASON_REQUIRED_CHECK_MISSING)
            out.append(entry)
            continue

        obs_mech = match.get("mechanism", "unknown")
        if obs_mech == "unknown":
            reasons.append(REASON_UNKNOWN_MECHANISM)
        entry["status"] = str(match.get("status") or "unknown")
        if match.get("conclusion") is not None:
            entry["conclusion"] = match.get("conclusion")
        if match.get("source_sha") is not None:
            entry["source_sha"] = match.get("source_sha")
        if match.get("app_id") is not None:
            entry["app_id"] = match.get("app_id")

        source_sha = match.get("source_sha")
        if not isinstance(source_sha, str) or not source_sha:
            # Successful required checks must bind to the subject head.
            reasons.append(REASON_STALE_HEAD)
            entry["matches_protection"] = False
            out.append(entry)
            continue
        if source_sha != head:
            reasons.append(REASON_STALE_HEAD)
            entry["matches_protection"] = False
            out.append(entry)
            continue

        if req_app is not None and match.get("app_id") != req_app:
            reasons.append(REASON_APP_ID_MISMATCH)
            entry["matches_protection"] = False
            out.append(entry)
            continue

        if obs_mech != mech:
            reasons.append(REASON_MECHANISM_MISMATCH)
            entry["matches_protection"] = False
            out.append(entry)
            continue

        success = _is_success(match)
        pending = _is_pending(match)
        failed = _is_failed(match)
        if pending:
            reasons.append(REASON_REQUIRED_CHECK_PENDING)
            entry["matches_protection"] = False
        elif failed:
            reasons.append(REASON_REQUIRED_CHECK_FAILED)
            entry["matches_protection"] = False
        elif success and obs_mech == mech:
            entry["matches_protection"] = True
            entry["status"] = "success"
        else:
            reasons.append(REASON_REQUIRED_CHECK_MISSING)
            entry["matches_protection"] = False
        out.append(entry)

    return out, _dedupe(reasons)


def evaluate_final_head_gates(
    snapshot: dict[str, Any], subject: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Fail-closed Final-Head lifecycle gates from injected snapshot.final_head."""
    reasons: list[str] = []
    fh = (
        snapshot.get("final_head")
        if isinstance(snapshot.get("final_head"), dict)
        else {}
    )
    provenance = fh.get("provenance") if isinstance(fh.get("provenance"), dict) else {}

    steward = fh.get("steward_state")
    if steward == "accepting_slices":
        reasons.append(REASON_ACCEPTING_SLICES)
    elif steward != "frozen":
        reasons.append(REASON_FINAL_HEAD_NOT_FROZEN)

    if not fh:
        reasons.append(REASON_MISSING_FINAL_HEAD_STATE)
        return _empty_final_head_state(), reasons

    if provenance.get("trusted") is not True:
        if REASON_UNTRUSTED_HANDOFF not in reasons:
            reasons.append(REASON_UNTRUSTED_HANDOFF)
        for code in (
            REASON_HANDOFF_SCHEMA_INVALID,
            REASON_HANDOFF_HEAD_MISMATCH,
            REASON_HANDOFF_BASE_MISMATCH,
            REASON_HANDOFF_PROVENANCE_INCOMPLETE,
            REASON_SELF_DECLARED_PRODUCER_REJECTED,
            REASON_FINAL_HEAD_NOT_FROZEN,
            REASON_COMPLETENESS_SUBJECT_MISMATCH,
            REASON_ACCEPTANCE_LIFECYCLE_MISMATCH,
            REASON_COMPLETENESS_VERDICT_MISMATCH,
        ):
            if code in (snapshot.get("final_head_reason_codes") or []):
                if code not in reasons:
                    reasons.append(code)

    ready = fh.get("final_head_ready_for_approval")
    if ready is not True:
        if REASON_FINAL_HEAD_NOT_READY not in reasons:
            reasons.append(REASON_FINAL_HEAD_NOT_READY)

    verdict = fh.get("completeness_verdict")
    lifecycle = fh.get("acceptance_lifecycle_state")
    if lifecycle != "FINAL_HEAD_READY_FOR_APPROVAL":
        reasons.append(REASON_ACCEPTANCE_LIFECYCLE_MISMATCH)
    if verdict != "MERGE_CANDIDATE":
        reasons.append(REASON_COMPLETENESS_VERDICT_MISMATCH)
    if verdict == "MERGE_CANDIDATE" and ready is not True:
        reasons.append(REASON_MERGE_CANDIDATE_WITHOUT_FINAL_HEAD)

    bound = fh.get("bound_final_head_sha")
    head = subject.get("head_sha")
    if isinstance(bound, str) and bound and isinstance(head, str) and head:
        if bound.lower() != head.lower():
            reasons.append(REASON_BOUND_HEAD_MISMATCH)

    risk = fh.get("risk")
    if ready is True and risk not in (None, "LOW"):
        reasons.append(REASON_RISK_NOT_LOW)
    elif ready is not True and risk not in (None, "LOW", "UNKNOWN"):
        reasons.append(REASON_RISK_NOT_LOW)

    state = {
        "steward_state": steward,
        "acceptance_lifecycle_state": fh.get("acceptance_lifecycle_state"),
        "final_head_ready_for_approval": bool(ready is True),
        "bound_final_head_sha": bound if isinstance(bound, str) else "",
        "completeness_verdict": verdict,
        "risk": risk if isinstance(risk, str) else "UNKNOWN",
        "provenance_trusted": provenance.get("trusted"),
    }
    return state, _dedupe(reasons)


def _empty_final_head_state() -> dict[str, Any]:
    return {
        "steward_state": None,
        "acceptance_lifecycle_state": None,
        "final_head_ready_for_approval": False,
        "bound_final_head_sha": "",
        "completeness_verdict": None,
        "risk": "UNKNOWN",
        "provenance_trusted": False,
    }


def evaluate_recommendation(
    *,
    subject_reasons: list[str],
    check_reasons: list[str],
    stale_reasons: list[str],
    final_head_reasons: list[str],
    drift: dict[str, Any],
    snapshot: dict[str, Any],
    required_checks: list[dict[str, Any]],
) -> tuple[str, list[str], list[str]]:
    """Return (recommendation, reason_codes, limitations)."""
    reasons = _dedupe(
        subject_reasons + check_reasons + stale_reasons + final_head_reasons
    )
    limitations: list[str] = []
    pr = snapshot.get("pr") if isinstance(snapshot.get("pr"), dict) else {}

    drift_status = drift.get("status")
    if drift_status == "UNKNOWN":
        reasons.append(REASON_DRIFT_UNKNOWN)
    elif drift_status not in (None, "NONE"):
        reasons.append(REASON_DRIFT)

    if "is_draft" not in pr:
        reasons.append(REASON_MISSING_DRAFT_STATE)
    elif pr.get("is_draft") is True:
        reasons.append(REASON_DRAFT_PR)

    review = pr.get("review_decision")
    if review is None:
        reasons.append(REASON_UNKNOWN_REVIEW)
    elif review == "CHANGES_REQUESTED":
        reasons.append(REASON_CHANGES_REQUESTED)
    elif review not in (
        "APPROVED",
        "REVIEW_REQUIRED",
        "NONE",
        "",
    ):
        reasons.append(REASON_UNKNOWN_REVIEW)

    blocking = pr.get("blocking_threads")
    thread_state = snapshot.get("review_thread_state")
    if thread_state == "unknown" or (blocking is None and thread_state is not None):
        reasons.append(REASON_BLOCKING_THREAD_UNKNOWN)
    elif isinstance(blocking, int) and blocking > 0:
        reasons.append(REASON_BLOCKING_THREAD)
    elif blocking is not None and not isinstance(blocking, int):
        reasons.append(REASON_INCOMPLETE_SNAPSHOT)

    reasons = _dedupe(reasons)

    hard_block = {
        REASON_MISSING_HEAD,
        REASON_INVALID_HEAD,
        REASON_MISSING_BASE,
        REASON_INVALID_BASE,
        REASON_CONFLICTING_HEAD,
        REASON_STALE_HEAD,
        REASON_PROTECTION_INCOMPLETE,
        REASON_INCOMPLETE_SNAPSHOT,
        REASON_MISSING_DRAFT_STATE,
    }
    if any(r in hard_block for r in reasons):
        return "BLOCKED", reasons, _limitations(reasons, limitations)

    if REASON_CHANGES_REQUESTED in reasons:
        return "REQUEST_CHANGES", reasons, _limitations(reasons, limitations)

    if REASON_DRAFT_PR in reasons or REASON_BLOCKING_THREAD in reasons:
        return "HOLD", reasons, _limitations(reasons, limitations)

    if REASON_BLOCKING_THREAD_UNKNOWN in reasons:
        return "UNKNOWN", reasons, _limitations(reasons, limitations)

    final_head_blocks = {
        REASON_FINAL_HEAD_NOT_READY,
        REASON_ACCEPTING_SLICES,
        REASON_ACCEPTANCE_LIFECYCLE_MISMATCH,
        REASON_COMPLETENESS_VERDICT_MISMATCH,
        REASON_MERGE_CANDIDATE_WITHOUT_FINAL_HEAD,
        REASON_MISSING_FINAL_HEAD_STATE,
        REASON_BOUND_HEAD_MISMATCH,
        REASON_RISK_NOT_LOW,
        REASON_UNTRUSTED_HANDOFF,
        REASON_HANDOFF_SCHEMA_INVALID,
        REASON_HANDOFF_HEAD_MISMATCH,
        REASON_HANDOFF_BASE_MISMATCH,
        REASON_HANDOFF_PROVENANCE_INCOMPLETE,
        REASON_SELF_DECLARED_PRODUCER_REJECTED,
        REASON_FINAL_HEAD_NOT_FROZEN,
    }
    if any(r in final_head_blocks for r in reasons):
        return "HOLD", reasons, _limitations(reasons, limitations)

    unknown_markers = {
        REASON_REQUIRED_CHECK_MISSING,
        REASON_UNKNOWN_MECHANISM,
        REASON_UNKNOWN_REVIEW,
        REASON_DRIFT_UNKNOWN,
        REASON_MECHANISM_MISMATCH,
        REASON_APP_ID_MISMATCH,
    }
    if any(r in unknown_markers for r in reasons):
        return "UNKNOWN", reasons, _limitations(reasons, limitations)

    if (
        REASON_REQUIRED_CHECK_PENDING in reasons
        or REASON_REQUIRED_CHECK_FAILED in reasons
    ):
        return "HOLD", reasons, _limitations(reasons, limitations)

    if REASON_DRIFT in reasons:
        return "HOLD", reasons, _limitations(reasons, limitations)

    all_matched = bool(required_checks) and all(
        c.get("matches_protection") is True for c in required_checks
    )
    if not all_matched:
        limitations.append("required_checks_incomplete")
        return "UNKNOWN", reasons + [REASON_REQUIRED_CHECK_MISSING], limitations

    # Clean path — recommendation only, never merge authority.
    limitations.append("recommendation_only_not_merge_authority")
    return "APPROVE_RECOMMENDED", reasons, limitations


def _find_observation(
    items: list[dict[str, Any]],
    *,
    name: str,
    mechanism: str,
    app_id: Any,
) -> dict[str, Any] | None:
    for item in items:
        if item.get("name") != name:
            continue
        if item.get("mechanism") != mechanism:
            continue
        if app_id is not None and item.get("app_id") != app_id:
            continue
        return item
    return None


def _is_success(check: dict[str, Any]) -> bool:
    status = str(check.get("status") or "").lower()
    conclusion = str(check.get("conclusion") or "").lower()
    if conclusion == "success":
        return True
    if status == "success":
        return True
    return False


def _is_pending(check: dict[str, Any]) -> bool:
    status = str(check.get("status") or "").lower()
    conclusion = str(check.get("conclusion") or "").lower()
    return status in {"queued", "in_progress", "pending"} or conclusion == "pending"


def _is_failed(check: dict[str, Any]) -> bool:
    status = str(check.get("status") or "").lower()
    conclusion = str(check.get("conclusion") or "").lower()
    return conclusion in {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
    } or status in {
        "failure",
        "failed",
        "error",
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _limitations(reasons: list[str], base: list[str]) -> list[str]:
    out = list(base)
    for reason in reasons:
        token = reason.lower()
        if token not in out:
            out.append(token)
    out.append("not_merge_authority")
    out.append("not_cdb_local_ci_publisher")
    return out
