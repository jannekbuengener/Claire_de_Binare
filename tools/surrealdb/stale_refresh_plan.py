"""Stale Refresh Plan Generator v1 — side-effect-free domain component.

Issues:
    #2158 — [SURREALDB][CONTEXT][STALE-RUNTIME] Implement refresh plan generator
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Scope:
    Converts scan_stale_knowledge_v1 results into a deterministic, prioritized
    Refresh Plan. Read-only. No DB access. No SurrealDB SDK. No MCP. No
    networking. No writes. No auto-fix. No live-go.

    Input:  StaleKnowledgeScanResult (or its to_dict() output, or a raw bundle
            that this service will scan internally via scan_stale_knowledge_v1).
    Output: RefreshPlanResult — recommendation only, never action authority.

    Plan items cover all 8 stale types with 7 canonical recommended actions
    plus a manual_review fallback. All plan_ids are deterministic SHA256 prefixes.

Guardrails:
    - Refresh Plan is recommendation only: never implies approval, live-go, or
      decision authority.
    - No automatic delete.
    - No automatic refresh write.
    - No DB write.
    - No Live-Readiness-Go.
    - No Echtgeld-Go.
    - write_authorized is always False on every plan item.
    - No direct wall-clock calls (use core.utils.clock.utcnow).
    - No random UUID generation — plan_ids are SHA256-based and deterministic.
    - LR status remains NO-GO for live trading.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Union

from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.stale_knowledge_scan import (
    StaleFinding,
    StaleKnowledgeScanError,
    StaleKnowledgeScanResult,
    scan_stale_knowledge_v1,
)

# ── Constants ─────────────────────────────────────────────────────────────────

TOOL_NAME = "stale_refresh_plan"
SCHEMA_VERSION = "stale-refresh-plan/v1"
GENERATED_BY = "stale-refresh-plan/v1"

GUARDRAILS: tuple[str, ...] = (
    "Refresh Plan is recommendation only.",
    "No automatic delete.",
    "No automatic refresh write.",
    "No DB write.",
    "No Live-Readiness-Go.",
    "No Echtgeld-Go.",
)

PRIORITIES: tuple[str, ...] = ("P0", "P1", "P2", "P3")

RECOMMENDED_ACTIONS: frozenset[str] = frozenset(
    {
        "reverify_source",
        "refresh_evidence",
        "refresh_memory",
        "recheck_decision",
        "rebuild_context_package",
        "regenerate_briefing",
        "reobserve_dependency_edge",
        "manual_review",
    }
)

# Mapping from stale_type to recommended_action.
# Unknown types fall back to manual_review.
_ACTION_MAP: dict[str, str] = {
    "source_hash_changed": "reverify_source",
    "source_deleted": "reverify_source",
    "decision_superseded": "recheck_decision",
    "evidence_expired": "refresh_evidence",
    "memory_ttl_expired": "refresh_memory",
    "dependency_edge_no_longer_observed": "reobserve_dependency_edge",
    "stale_context_package": "rebuild_context_package",
    "stale_briefing": "regenerate_briefing",
}

# stale_types that always escalate to P1 when severity=warning, regardless of confidence.
_P1_WARNING_TYPES: frozenset[str] = frozenset(
    {"evidence_expired", "memory_ttl_expired"}
)

# stale_types that map to P2 when severity=warning.
_P2_WARNING_TYPES: frozenset[str] = frozenset(
    {"stale_context_package", "stale_briefing", "dependency_edge_no_longer_observed"}
)

# Confidence threshold for escalating decision_superseded / source_hash_changed to P1.
_P1_CONFIDENCE_THRESHOLD = 0.85

# stale_types that always require human review.
_HUMAN_REVIEW_TYPES: frozenset[str] = frozenset({"source_deleted"})

_SCAN_RESULT_SCHEMA = "stale-knowledge-scan/v1"

PLAN_ITEM_STATUS_PENDING = "pending"


# ── Exception ─────────────────────────────────────────────────────────────────


class RefreshPlanError(ValueError):
    """Raised when refresh plan generation inputs are invalid or unsafe."""


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RefreshPlanItem:
    """A single recommended refresh action derived from a StaleFinding.

    Output contract — all fields guaranteed to be present:
        plan_id             deterministic SHA256 prefix (stale_id|action|target_ref)
        stale_id            source StaleFinding identifier
        target_ref          ID or path of the stale artifact
        stale_type          one of STALE_TYPES (or unknown)
        severity            info | warning | blocking
        priority            P0 | P1 | P2 | P3
        recommended_action  canonical action string
        reason              human-readable reason from finding
        source_refs         tuple of source IDs involved
        evidence_refs       tuple of evidence record IDs
        refresh_inputs      deduplicated union of source_refs + target_ref
        blocked_by          tuple of blocking conditions (empty for MVP)
        requires_human_review  bool
        write_authorized    bool — always False
        status              "pending"
    """

    plan_id: str
    stale_id: str
    target_ref: str
    stale_type: str
    severity: str
    priority: str
    recommended_action: str
    reason: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    refresh_inputs: tuple[str, ...]
    blocked_by: tuple[str, ...]
    requires_human_review: bool
    write_authorized: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "stale_id": self.stale_id,
            "target_ref": self.target_ref,
            "stale_type": self.stale_type,
            "severity": self.severity,
            "priority": self.priority,
            "recommended_action": self.recommended_action,
            "reason": self.reason,
            "source_refs": list(self.source_refs),
            "evidence_refs": list(self.evidence_refs),
            "refresh_inputs": list(self.refresh_inputs),
            "blocked_by": list(self.blocked_by),
            "requires_human_review": self.requires_human_review,
            "write_authorized": self.write_authorized,
            "status": self.status,
        }


@dataclass(frozen=True)
class RefreshPlanResult:
    """Result of a refresh plan generation run."""

    tool: str
    schema_version: str
    status: str
    as_of: str
    total_findings: int
    blocking_findings: int
    plan_item_count: int
    plan_items: tuple[RefreshPlanItem, ...]
    guardrails: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        priority_summary: dict[str, int] = {p: 0 for p in PRIORITIES}
        action_summary: dict[str, int] = {}
        for item in self.plan_items:
            if item.priority in priority_summary:
                priority_summary[item.priority] += 1
            action_summary[item.recommended_action] = (
                action_summary.get(item.recommended_action, 0) + 1
            )

        return {
            "tool": self.tool,
            "schema_version": self.schema_version,
            "status": self.status,
            "as_of": self.as_of,
            "summary": {
                "total_findings": self.total_findings,
                "blocking_findings": self.blocking_findings,
                "plan_item_count": self.plan_item_count,
                "priority_summary": priority_summary,
                "action_summary": action_summary,
            },
            "plan_items": [item.to_dict() for item in self.plan_items],
            "guardrails": list(self.guardrails),
            "errors": list(self.errors),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _plan_id(stale_id: str, recommended_action: str, target_ref: str) -> str:
    """Generate a deterministic plan item ID.

    Uses SHA256 of the canonical string (stale_id|recommended_action|target_ref).
    No random UUID generation, no random module — guardrails-compliant.
    """
    raw = f"{stale_id}|{recommended_action}|{target_ref}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _derive_action(stale_type: str) -> str:
    """Map a stale_type to its recommended action.

    Unknown stale_types map to manual_review — no crash.
    """
    return _ACTION_MAP.get(stale_type, "manual_review")


def _derive_priority(
    stale_type: str,
    severity: str,
    confidence: float,
    blocking: bool,
) -> str:
    """Derive priority (P0-P3) from finding attributes.

    P0: blocking severity OR blocking=True (source_deleted is always blocking).
    P1: warning + time-critical types (evidence_expired, memory_ttl_expired)
        OR high-confidence decision_superseded / source_hash_changed.
    P2: context/briefing/edge stale types (warning).
    P3: info severity or low-confidence.
    """
    if blocking or severity == "blocking":
        return "P0"
    if severity == "warning":
        if stale_type in _P1_WARNING_TYPES:
            return "P1"
        if stale_type in {"decision_superseded", "source_hash_changed"} and confidence >= _P1_CONFIDENCE_THRESHOLD:
            return "P1"
        if stale_type in _P2_WARNING_TYPES:
            return "P2"
        return "P2"
    # info or unknown severity
    return "P3"


def _derive_requires_human_review(
    stale_type: str,
    severity: str,
    target_ref: str,
    action: str,
) -> bool:
    """Determine if a plan item requires human review.

    True when:
    - stale_type is in the explicit human-review set (source_deleted)
    - action is manual_review (unknown stale_type)
    - severity is blocking
    - target_ref is missing/unknown
    """
    if not target_ref or target_ref in ("unknown-source", "unknown-decision", "unknown-evidence", "unknown-memory", "unknown-edge", "unknown-package", "unknown-briefing"):
        return True
    if stale_type in _HUMAN_REVIEW_TYPES:
        return True
    if action == "manual_review":
        return True
    if severity == "blocking":
        return True
    return False


def _build_refresh_inputs(source_refs: tuple[str, ...], target_ref: str) -> tuple[str, ...]:
    """Build refresh_inputs as deduplicated union of source_refs + target_ref."""
    seen: set[str] = set()
    result: list[str] = []
    for ref in source_refs:
        if ref and ref not in seen:
            seen.add(ref)
            result.append(ref)
    if target_ref and target_ref not in seen:
        result.append(target_ref)
    return tuple(result)


def _make_plan_item(finding: StaleFinding) -> RefreshPlanItem:
    """Convert a StaleFinding into a RefreshPlanItem."""
    action = _derive_action(finding.stale_type)
    priority = _derive_priority(
        finding.stale_type,
        finding.severity,
        finding.confidence,
        finding.blocking,
    )
    requires_review = _derive_requires_human_review(
        finding.stale_type,
        finding.severity,
        finding.target_ref,
        action,
    )
    refresh_inputs = _build_refresh_inputs(finding.source_refs, finding.target_ref)
    pid = _plan_id(finding.stale_id, action, finding.target_ref)

    return RefreshPlanItem(
        plan_id=pid,
        stale_id=finding.stale_id,
        target_ref=finding.target_ref,
        stale_type=finding.stale_type,
        severity=finding.severity,
        priority=priority,
        recommended_action=action,
        reason=finding.reason,
        source_refs=finding.source_refs,
        evidence_refs=finding.evidence_refs,
        refresh_inputs=refresh_inputs,
        blocked_by=(),
        requires_human_review=requires_review,
        write_authorized=False,
        status=PLAN_ITEM_STATUS_PENDING,
    )


def _reconstruct_finding_from_dict(d: dict[str, Any]) -> StaleFinding:
    """Reconstruct a StaleFinding from its to_dict() representation.

    Used when scan_input is a serialised StaleKnowledgeScanResult dict.
    Tolerant: missing fields use safe defaults.
    """
    return StaleFinding(
        stale_id=str(d.get("stale_id") or ""),
        stale_type=str(d.get("stale_type") or ""),
        target_ref=str(d.get("target_ref") or ""),
        reason=str(d.get("reason") or ""),
        severity=str(d.get("severity") or "info"),
        confidence=float(d.get("confidence") or 0.5),
        source_refs=tuple(d.get("source_refs") or []),
        evidence_refs=tuple(d.get("evidence_refs") or []),
        detected_by=str(d.get("detected_by") or ""),
        detected_at=str(d.get("detected_at") or ""),
        recommended_refresh=str(d.get("recommended_refresh") or ""),
        blocking=bool(d.get("blocking", False)),
        status=str(d.get("status") or "open"),
    )


def _resolve_scan_input(
    scan_input: Any,
    as_of: Optional[str],
) -> StaleKnowledgeScanResult:
    """Resolve scan_input to a StaleKnowledgeScanResult.

    Three input paths:
    1. StaleKnowledgeScanResult — used directly.
    2. Mapping with schema_version == "stale-knowledge-scan/v1" and "findings" key
       — parsed as a serialised scan result dict.
    3. Any other Mapping — treated as a raw bundle; scan_stale_knowledge_v1 is called.

    Raises RefreshPlanError for any other type.
    """
    if isinstance(scan_input, StaleKnowledgeScanResult):
        return scan_input

    if isinstance(scan_input, Mapping):
        schema = scan_input.get("schema_version")
        if schema == _SCAN_RESULT_SCHEMA and "findings" in scan_input:
            # Serialised scan result — reconstruct findings
            raw_as_of = str(scan_input.get("as_of") or (as_of or cdb_utcnow().isoformat()))
            findings_raw = scan_input.get("findings") or []
            findings: list[StaleFinding] = []
            for item in findings_raw:
                if isinstance(item, dict):
                    findings.append(_reconstruct_finding_from_dict(item))
            blocking_count = sum(1 for f in findings if f.blocking)
            from tools.surrealdb.stale_knowledge_scan import (
                GUARDRAILS as SCAN_GUARDRAILS,
                TOOL_NAME as SCAN_TOOL,
                SCHEMA_VERSION as SCAN_SCHEMA,
            )
            return StaleKnowledgeScanResult(
                tool=SCAN_TOOL,
                schema_version=SCAN_SCHEMA,
                status="ok",
                as_of=raw_as_of,
                total_count=len(findings),
                blocking_count=blocking_count,
                findings=tuple(findings),
                recommended_refresh=tuple(scan_input.get("recommended_refresh") or []),
                guardrails=SCAN_GUARDRAILS,
            )
        # Raw bundle path — honour deterministic as_of from bundle meta when
        # the caller did not supply an explicit as_of override.  This avoids
        # falling back to wall-clock time for time-based stale rules.
        effective_as_of = as_of
        if effective_as_of is None:
            meta = scan_input.get("meta") if isinstance(scan_input, Mapping) else None
            if isinstance(meta, Mapping):
                bundle_ts = meta.get("as_of")
                if bundle_ts and isinstance(bundle_ts, str):
                    effective_as_of = bundle_ts
        try:
            return scan_stale_knowledge_v1(scan_input, as_of=effective_as_of)
        except StaleKnowledgeScanError:
            raise

    raise RefreshPlanError(
        f"scan_input must be a StaleKnowledgeScanResult or Mapping, "
        f"got {type(scan_input).__name__}"
    )


def _priority_summary(items: tuple[RefreshPlanItem, ...]) -> dict[str, int]:
    summary: dict[str, int] = {p: 0 for p in PRIORITIES}
    for item in items:
        if item.priority in summary:
            summary[item.priority] += 1
    return summary


def _action_summary(items: tuple[RefreshPlanItem, ...]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in items:
        summary[item.recommended_action] = summary.get(item.recommended_action, 0) + 1
    return summary


# ── Public API ────────────────────────────────────────────────────────────────


def generate_refresh_plan_v1(
    scan_input: Union[StaleKnowledgeScanResult, Mapping[str, Any]],
    as_of: Optional[str] = None,
) -> RefreshPlanResult:
    """Generate a deterministic refresh plan from stale knowledge scan results.

    This is the primary public entry point. Read-only. No writes. No network.
    No DB access. No GitHub calls. No auto-fix. No auto-delete.

    Args:
        scan_input:  One of:
            - StaleKnowledgeScanResult — used directly.
            - dict with schema_version="stale-knowledge-scan/v1" and "findings"
              key — parsed as a serialised scan result.
            - Any other Mapping — treated as a raw input bundle; scan is run
              internally via scan_stale_knowledge_v1.
        as_of:  Optional ISO-8601 UTC string. Used as the reference time when
                running an internal scan. Ignored when scan_input is already a
                StaleKnowledgeScanResult.

    Returns:
        RefreshPlanResult with plan_items, priority/action summaries, guardrails,
        and errors. Status is "ok" on success (even for empty plans) and "error"
        on invalid input.

    Guardrails:
        - No write operations anywhere in this call chain.
        - All timestamps via cdb_utcnow (clock-injected, not wall-clock).
        - No random UUID generation — plan_ids are SHA256-based and deterministic.
        - write_authorized is always False on every plan item.
        - Refresh Plan is recommendation only — no action authority.
        - LR status remains NO-GO for live trading.
    """
    resolved_as_of: str = as_of if as_of is not None else cdb_utcnow().isoformat()
    errors: list[str] = []

    # ── Resolve / scan ────────────────────────────────────────────────────────
    try:
        scan_result = _resolve_scan_input(scan_input, as_of)
    except RefreshPlanError as exc:
        return RefreshPlanResult(
            tool=TOOL_NAME,
            schema_version=SCHEMA_VERSION,
            status="error",
            as_of=resolved_as_of,
            total_findings=0,
            blocking_findings=0,
            plan_item_count=0,
            plan_items=(),
            guardrails=GUARDRAILS,
            errors=(str(exc),),
        )
    except StaleKnowledgeScanError as exc:
        return RefreshPlanResult(
            tool=TOOL_NAME,
            schema_version=SCHEMA_VERSION,
            status="error",
            as_of=resolved_as_of,
            total_findings=0,
            blocking_findings=0,
            plan_item_count=0,
            plan_items=(),
            guardrails=GUARDRAILS,
            errors=(str(exc),),
        )
    except Exception as exc:  # noqa: BLE001
        return RefreshPlanResult(
            tool=TOOL_NAME,
            schema_version=SCHEMA_VERSION,
            status="error",
            as_of=resolved_as_of,
            total_findings=0,
            blocking_findings=0,
            plan_item_count=0,
            plan_items=(),
            guardrails=GUARDRAILS,
            errors=(f"Unexpected error: {type(exc).__name__}: {exc}",),
        )

    # ── Build plan items ──────────────────────────────────────────────────────
    plan_items: list[RefreshPlanItem] = []
    for finding in scan_result.findings:
        try:
            plan_items.append(_make_plan_item(finding))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Failed to build plan item for {finding.stale_id}: {type(exc).__name__}")

    return RefreshPlanResult(
        tool=TOOL_NAME,
        schema_version=SCHEMA_VERSION,
        status="ok",
        as_of=scan_result.as_of,
        total_findings=scan_result.total_count,
        blocking_findings=scan_result.blocking_count,
        plan_item_count=len(plan_items),
        plan_items=tuple(plan_items),
        guardrails=GUARDRAILS,
        errors=tuple(errors),
    )
