"""Contradiction Scan Runtime v1 — side-effect-free domain component.

Issues:
    #2146 — [SURREALDB][CONTEXT][CONTRADICTION-RUNTIME] Implement contradiction scan service v1
    Parent: #2145 (Wave-15)
    Epic: #1976

Scope:
    Implements a minimal, deterministic contradiction-scan service that works
    purely on in-memory records. No DB access. No SurrealDB SDK. No MCP.
    No networking. No writes. No auto-fix. No live-go.

    Detects contradictions between:
        doc_vs_code, doc_vs_decision, decision_vs_evidence,
        claim_vs_evidence, memory_vs_source, current_status_vs_live_surface,
        runbook_vs_contract, test_vs_claim, stale_decision_vs_new_evidence

Guardrails:
    - Detection only: never implies approval, live-go, or decision authority.
    - Blocking findings are surfaced explicitly but do NOT grant permission to act.
    - No write, no mutation, no GitHub/runtime write from this module.
    - No direct wall-clock calls or random UUID generation (use core.utils.clock).
    - LR status remains NO-GO for live trading.
    - Detection is signal, not action.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "contradiction-scan/v1"
DETECTED_BY = "contradiction-scan/v1"

CONTRADICTION_TYPES = frozenset(
    {
        "doc_vs_code",
        "doc_vs_decision",
        "decision_vs_evidence",
        "claim_vs_evidence",
        "memory_vs_source",
        "current_status_vs_live_surface",
        "runbook_vs_contract",
        "test_vs_claim",
        "stale_decision_vs_new_evidence",
    }
)

SEVERITY_LEVELS = ("info", "warning", "blocking")

# Forward-compatible status set — covers #2025 (acknowledged) and #2146 (accepted_risk)
STATUS_VALUES = frozenset(
    {
        "open",
        "acknowledged",
        "false_positive",
        "accepted_risk",
        "resolved",
        "superseded",
    }
)

_NON_BLOCKING_STATUSES = frozenset({"false_positive", "accepted_risk", "resolved", "superseded"})


class ContradictionScanError(ValueError):
    """Raised when contradiction scan inputs are invalid or unsafe."""


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SourceRef:
    """Reference to a source artifact involved in a contradiction."""

    ref_id: str
    ref_type: str  # e.g. "doc", "code_symbol", "decision", "claim", "memory", "runbook", "test", "status_ledger", "live_surface"
    path: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class EvidenceRef:
    """Reference to an evidence record supporting or refuting a finding."""

    evidence_id: str
    evidence_type: str  # e.g. "test_run", "audit_log", "decision_record", "doc_claim"
    strength: str = "none"  # none | weak | moderate | strong | blocking_missing
    description: str | None = None


@dataclass(frozen=True)
class ContradictionFinding:
    """A single detected contradiction between two sources.

    Output contract — all fields guaranteed to be present:
        contradiction_id    deterministic, stable identifier
        contradiction_type  one of CONTRADICTION_TYPES
        source_a_ref        SourceRef of first party
        source_b_ref        SourceRef of second party
        claim_refs          list[str] — claim IDs involved (may be empty)
        evidence_refs       list[EvidenceRef] — supporting/refuting evidence
        severity            info | warning | blocking
        confidence          float in [0.0, 1.0]
        detected_by         str — service/version that detected this
        detected_at         ISO-8601 UTC string — via cdb_utcnow (clock-injected, not wall-clock)
        status              one of STATUS_VALUES
        recommended_action  human-readable guidance string
        blocking            bool — true iff severity=blocking and status not non-blocking
    """

    contradiction_id: str
    contradiction_type: str
    source_a_ref: SourceRef
    source_b_ref: SourceRef
    claim_refs: tuple[str, ...]
    evidence_refs: tuple[EvidenceRef, ...]
    severity: str
    confidence: float
    detected_by: str
    detected_at: str
    status: str
    recommended_action: str
    blocking: bool


@dataclass(frozen=True)
class ContradictionScanResult:
    """Result of a full contradiction scan run."""

    schema_version: str
    scanned_at: str
    findings: tuple[ContradictionFinding, ...]
    blocking_count: int
    total_count: int


# ── Helpers ───────────────────────────────────────────────────────────────────


def _contradiction_id(ctype: str, ref_a_id: str, ref_b_id: str) -> str:
    """Generate a deterministic, stable contradiction ID.

    Uses SHA256 of the canonical string (ctype|ref_a_id|ref_b_id).
    No random UUID generation, no random module — guardrails-compliant.
    """
    raw = f"{ctype}|{ref_a_id}|{ref_b_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return str(value).strip() or None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clamp_confidence(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))


def _is_blocking(severity: str, status: str) -> bool:
    return severity == "blocking" and status not in _NON_BLOCKING_STATUSES


def _make_finding(
    *,
    ctype: str,
    source_a: SourceRef,
    source_b: SourceRef,
    claim_refs: Sequence[str] = (),
    evidence_refs: Sequence[EvidenceRef] = (),
    severity: str,
    confidence: float,
    status: str = "open",
    recommended_action: str,
    detected_at: str,
) -> ContradictionFinding:
    cid = _contradiction_id(ctype, source_a.ref_id, source_b.ref_id)
    blocking = _is_blocking(severity, status)
    return ContradictionFinding(
        contradiction_id=cid,
        contradiction_type=ctype,
        source_a_ref=source_a,
        source_b_ref=source_b,
        claim_refs=tuple(claim_refs),
        evidence_refs=tuple(evidence_refs),
        severity=severity,
        confidence=_clamp_confidence(confidence),
        detected_by=DETECTED_BY,
        detected_at=detected_at,
        status=status,
        recommended_action=recommended_action,
        blocking=blocking,
    )


def _apply_overrides(
    findings: list[ContradictionFinding],
    overrides: Mapping[str, str] | None,
) -> list[ContradictionFinding]:
    """Apply false_positive / accepted_risk overrides to matched findings.

    Matching is done by contradiction_id. When matched:
        - status is updated to the override value
        - blocking is set to False (non-blocking)
        - recommended_action is updated to reflect the override
        - finding is retained (never discarded)
    """
    if not overrides:
        return findings
    result = []
    for f in findings:
        override_status = overrides.get(f.contradiction_id)
        if override_status in {"false_positive", "accepted_risk"}:
            action_suffix = (
                "no action unless evidence changes"
                if override_status == "false_positive"
                else "review accepted risk periodically"
            )
            result.append(
                ContradictionFinding(
                    contradiction_id=f.contradiction_id,
                    contradiction_type=f.contradiction_type,
                    source_a_ref=f.source_a_ref,
                    source_b_ref=f.source_b_ref,
                    claim_refs=f.claim_refs,
                    evidence_refs=f.evidence_refs,
                    severity=f.severity,
                    confidence=f.confidence,
                    detected_by=f.detected_by,
                    detected_at=f.detected_at,
                    status=override_status,
                    recommended_action=f"{f.recommended_action} [override: {action_suffix}]",
                    blocking=False,
                )
            )
        else:
            result.append(f)
    return result


# ── Detection Rules ───────────────────────────────────────────────────────────


def _rule_doc_vs_code(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: doc claims a symbol/feature exists but no code symbol record present.

    Input contract (records keys):
        "doc_claims"    list of dicts: {claim_id, path, symbol, exists: bool}
        "code_symbols"  list of dicts: {symbol_id, symbol}
    """
    findings: list[ContradictionFinding] = []
    doc_claims = _as_list(records.get("doc_claims"))
    code_symbols = _as_list(records.get("code_symbols"))
    known_symbols = {_as_str(cs.get("symbol")) for cs in code_symbols if cs}

    for claim in doc_claims:
        if not claim:
            continue
        symbol = _as_str(claim.get("symbol"))
        exists_asserted = bool(claim.get("exists", False))
        if exists_asserted and symbol and symbol not in known_symbols:
            src_a = SourceRef(
                ref_id=_as_str(claim.get("claim_id")) or f"doc:{symbol}",
                ref_type="doc",
                path=_as_str(claim.get("path")),
                description=f"Doc asserts symbol '{symbol}' exists",
            )
            src_b = SourceRef(
                ref_id=f"code:{symbol}",
                ref_type="code_symbol",
                description=f"Code symbol '{symbol}' not found in code_symbols",
            )
            severity = "blocking" if claim.get("blocking", False) else "warning"
            findings.append(
                _make_finding(
                    ctype="doc_vs_code",
                    source_a=src_a,
                    source_b=src_b,
                    claim_refs=[_as_str(claim.get("claim_id")) or f"doc:{symbol}"],
                    evidence_refs=[
                        EvidenceRef(
                            evidence_id=f"missing:{symbol}",
                            evidence_type="code_symbol_absence",
                            strength="blocking_missing",
                            description=f"Symbol '{symbol}' declared in doc but absent in code",
                        )
                    ],
                    severity=severity,
                    confidence=0.85,
                    recommended_action=(
                        f"Implement or remove doc claim for symbol '{symbol}'. "
                        "Verify the doc is not ahead of the implementation."
                    ),
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_doc_vs_decision(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: a doc/runbook rule contradicts a decision that supersedes it.

    Input contract (records keys):
        "doc_rules"    list of dicts: {rule_id, path, rule_text, decision_ref: str|None}
        "decisions"    list of dicts: {decision_id, supersedes: list[str], status}
    """
    findings: list[ContradictionFinding] = []
    doc_rules = _as_list(records.get("doc_rules"))
    decisions = _as_list(records.get("decisions"))

    # Build a map of which doc_rules are superseded by decisions
    superseded_rule_ids: dict[str, str] = {}  # rule_id -> decision_id that supersedes it
    for dec in decisions:
        if not dec:
            continue
        if _as_str(dec.get("status")) in {"superseded", "resolved"}:
            continue
        for rule_id in _as_list(dec.get("supersedes")):
            rid = _as_str(rule_id)
            if rid:
                superseded_rule_ids[rid] = _as_str(dec.get("decision_id")) or "unknown-decision"

    for rule in doc_rules:
        if not rule:
            continue
        rule_id = _as_str(rule.get("rule_id")) or "unknown-rule"
        if rule_id in superseded_rule_ids:
            dec_id = superseded_rule_ids[rule_id]
            src_a = SourceRef(
                ref_id=rule_id,
                ref_type="doc",
                path=_as_str(rule.get("path")),
                description=_as_str(rule.get("rule_text")) or f"Doc rule '{rule_id}'",
            )
            src_b = SourceRef(
                ref_id=dec_id,
                ref_type="decision",
                description=f"Decision '{dec_id}' supersedes doc rule '{rule_id}'",
            )
            findings.append(
                _make_finding(
                    ctype="doc_vs_decision",
                    source_a=src_a,
                    source_b=src_b,
                    claim_refs=[rule_id],
                    evidence_refs=[
                        EvidenceRef(
                            evidence_id=dec_id,
                            evidence_type="decision_record",
                            strength="strong",
                            description=f"Decision '{dec_id}' supersedes this rule",
                        )
                    ],
                    severity="warning",
                    confidence=0.80,
                    recommended_action=(
                        f"Update doc rule '{rule_id}' to reflect decision '{dec_id}'. "
                        "Mark old rule as superseded or remove it."
                    ),
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_decision_vs_evidence(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: a decision requires evidence but the referenced evidence is missing/weak.

    Input contract (records keys):
        "decisions"        list of dicts: {decision_id, requires_evidence: bool, evidence_refs: list[str]}
        "evidence_records" list of dicts: {evidence_id, strength}
    """
    findings: list[ContradictionFinding] = []
    decisions = _as_list(records.get("decisions"))
    evidence_records = _as_list(records.get("evidence_records"))

    evidence_by_id: dict[str, Any] = {}
    for ev in evidence_records:
        if ev:
            eid = _as_str(ev.get("evidence_id"))
            if eid:
                evidence_by_id[eid] = ev

    _weak_strengths = frozenset({"none", "weak", "blocking_missing"})

    for dec in decisions:
        if not dec:
            continue
        if not dec.get("requires_evidence", False):
            continue
        dec_id = _as_str(dec.get("decision_id")) or "unknown-decision"
        ev_refs = _as_list(dec.get("evidence_refs"))
        if not ev_refs:
            # No evidence referenced at all
            src_a = SourceRef(
                ref_id=dec_id,
                ref_type="decision",
                description=f"Decision '{dec_id}' requires evidence but has no evidence refs",
            )
            src_b = SourceRef(
                ref_id=f"missing:evidence:{dec_id}",
                ref_type="evidence_absence",
                description="No evidence records referenced by this decision",
            )
            findings.append(
                _make_finding(
                    ctype="decision_vs_evidence",
                    source_a=src_a,
                    source_b=src_b,
                    evidence_refs=[
                        EvidenceRef(
                            evidence_id=f"missing:{dec_id}",
                            evidence_type="decision_record",
                            strength="blocking_missing",
                            description="No evidence referenced",
                        )
                    ],
                    severity="blocking",
                    confidence=0.90,
                    recommended_action=(
                        f"Provide evidence refs for decision '{dec_id}'. "
                        "Decision cannot be validated without evidence."
                    ),
                    detected_at=detected_at,
                )
            )
            continue

        for ev_ref_id in ev_refs:
            eid = _as_str(ev_ref_id)
            if not eid:
                continue
            ev_rec = evidence_by_id.get(eid)
            if ev_rec is None:
                strength = "blocking_missing"
                severity = "blocking"
            else:
                strength = _as_str(ev_rec.get("strength")) or "none"
                severity = "blocking" if strength in _weak_strengths else "info"

            if severity != "info":
                src_a = SourceRef(
                    ref_id=dec_id,
                    ref_type="decision",
                    description=f"Decision '{dec_id}' references evidence '{eid}'",
                )
                src_b = SourceRef(
                    ref_id=eid,
                    ref_type="evidence",
                    description=f"Evidence '{eid}' is {strength}",
                )
                findings.append(
                    _make_finding(
                        ctype="decision_vs_evidence",
                        source_a=src_a,
                        source_b=src_b,
                        evidence_refs=[
                            EvidenceRef(
                                evidence_id=eid,
                                evidence_type="evidence_record",
                                strength=strength,
                                description=f"Evidence strength: {strength}",
                            )
                        ],
                        severity=severity,
                        confidence=0.85,
                        recommended_action=(
                            f"Strengthen or replace evidence '{eid}' for decision '{dec_id}'. "
                            f"Current strength: {strength}."
                        ),
                        detected_at=detected_at,
                    )
                )
    return findings


def _rule_claim_vs_evidence(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: a claim's status is disputed, invalidated (blocking) or stale (warning).

    Input contract (records keys):
        "claims" list of dicts: {claim_id, status, topic, evidence_refs: list[str]}
    """
    findings: list[ContradictionFinding] = []
    claims = _as_list(records.get("claims"))

    _blocking_statuses = frozenset({"disputed", "invalidated"})
    _warning_statuses = frozenset({"stale"})

    for claim in claims:
        if not claim:
            continue
        claim_id = _as_str(claim.get("claim_id")) or "unknown-claim"
        status = _as_str(claim.get("status")) or "proposed"
        if status not in (_blocking_statuses | _warning_statuses):
            continue

        severity = "blocking" if status in _blocking_statuses else "warning"
        ev_refs = _as_list(claim.get("evidence_refs"))
        evidence_refs_out: list[EvidenceRef] = [
            EvidenceRef(
                evidence_id=eid,
                evidence_type="claim_evidence_ref",
                strength="weak" if status == "stale" else "none",
                description=f"Evidence for claim '{claim_id}' (status: {status})",
            )
            for eid in [_as_str(r) for r in ev_refs]
            if eid
        ]
        if not evidence_refs_out:
            # No evidence refs provided — emit an explicit absence EvidenceRef so
            # downstream consumers can distinguish "no evidence" from malformed output.
            evidence_refs_out = [
                EvidenceRef(
                    evidence_id=f"missing:claim:{claim_id}",
                    evidence_type="claim_evidence_absence",
                    strength="blocking_missing",
                    description=f"No evidence refs for claim '{claim_id}' (status: {status})",
                )
            ]

        src_a = SourceRef(
            ref_id=claim_id,
            ref_type="claim",
            description=f"Claim '{claim_id}' has status '{status}'",
        )
        src_b = SourceRef(
            ref_id=f"evidence:claim:{claim_id}",
            ref_type="evidence",
            description=f"Evidence supporting claim '{claim_id}' is insufficient or contradicted",
        )
        findings.append(
            _make_finding(
                ctype="claim_vs_evidence",
                source_a=src_a,
                source_b=src_b,
                claim_refs=[claim_id],
                evidence_refs=evidence_refs_out,
                severity=severity,
                confidence=0.80,
                recommended_action=(
                    f"Resolve claim '{claim_id}' (status: {status}). "
                    "Update or retract the claim based on current evidence."
                ),
                detected_at=detected_at,
            )
        )
    return findings


def _rule_memory_vs_source(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: memory record is older than the source or the source explicitly contradicts it.

    Memory is a hint, not the truth. Contradictions are warnings only.

    Input contract (records keys):
        "memory_records" list of dicts: {memory_id, scope, content, updated_at: ISO str, source_ref: str|None}
        "source_records" list of dicts: {source_id, updated_at: ISO str, contradicts_memory: list[str]}
    """
    findings: list[ContradictionFinding] = []
    memory_records = _as_list(records.get("memory_records"))
    source_records = _as_list(records.get("source_records"))

    # Build map: memory_id -> memory record
    mem_by_id: dict[str, Any] = {}
    for mem in memory_records:
        if mem:
            mid = _as_str(mem.get("memory_id"))
            if mid:
                mem_by_id[mid] = mem

    # Check explicit contradictions from source records
    for src_rec in source_records:
        if not src_rec:
            continue
        src_id = _as_str(src_rec.get("source_id")) or "unknown-source"
        for mem_id in _as_list(src_rec.get("contradicts_memory")):
            mid = _as_str(mem_id)
            if not mid:
                continue
            src_a = SourceRef(
                ref_id=mid,
                ref_type="memory",
                description=f"Memory '{mid}' is contradicted by source '{src_id}'",
            )
            src_b = SourceRef(
                ref_id=src_id,
                ref_type="source",
                description=f"Source '{src_id}' explicitly contradicts memory '{mid}'",
            )
            findings.append(
                _make_finding(
                    ctype="memory_vs_source",
                    source_a=src_a,
                    source_b=src_b,
                    evidence_refs=[
                        EvidenceRef(
                            evidence_id=src_id,
                            evidence_type="source_record",
                            strength="strong",
                            description=f"Source '{src_id}' contradicts memory '{mid}'",
                        )
                    ],
                    severity="warning",
                    confidence=0.75,
                    recommended_action=(
                        f"Review memory '{mid}'. Source '{src_id}' contradicts it. "
                        "Update memory to reflect current source truth. No memory write from this service."
                    ),
                    detected_at=detected_at,
                )
            )

    # Check staleness: memory updated_at < source updated_at
    for mem in memory_records:
        if not mem:
            continue
        mid = _as_str(mem.get("memory_id")) or "unknown-memory"
        mem_source_ref = _as_str(mem.get("source_ref"))
        mem_updated_at = _as_str(mem.get("updated_at")) or ""
        if not mem_source_ref or not mem_updated_at:
            continue
        for src_rec in source_records:
            if not src_rec:
                continue
            src_id = _as_str(src_rec.get("source_id"))
            if src_id != mem_source_ref:
                continue
            src_updated_at = _as_str(src_rec.get("updated_at")) or ""
            # Simple lexicographic ISO-8601 comparison (UTC assumed)
            if src_updated_at > mem_updated_at:
                src_a = SourceRef(
                    ref_id=mid,
                    ref_type="memory",
                    description=f"Memory '{mid}' updated at {mem_updated_at}",
                )
                # Append ':stale_timestamp' to disambiguate from the explicit-contradiction
                # path which uses ref_id=src_id — both would otherwise produce the same
                # contradiction_id (same ctype + same ref_a + same ref_b).
                src_b = SourceRef(
                    ref_id=f"{src_id}:stale_timestamp",
                    ref_type="source",
                    description=f"Source '{src_id}' updated at {src_updated_at} (newer than memory)",
                )
                findings.append(
                    _make_finding(
                        ctype="memory_vs_source",
                        source_a=src_a,
                        source_b=src_b,
                        evidence_refs=[
                            EvidenceRef(
                                evidence_id=src_id,
                                evidence_type="source_record",
                                strength="moderate",
                                description=f"Source updated at {src_updated_at}, memory at {mem_updated_at}",
                            )
                        ],
                        severity="warning",
                        confidence=0.65,
                        recommended_action=(
                            f"Memory '{mid}' may be stale. Source '{src_id}' is newer. "
                            "Review and refresh memory through the appropriate process."
                        ),
                        detected_at=detected_at,
                    )
                )
    return findings


def _rule_current_status_vs_live_surface(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: status ledger claims closed/green but live_surface shows open/red.

    No live GitHub calls — only on passed-in snapshot/live-surface records.

    Input contract (records keys):
        "status_ledger_records" list of dicts: {ledger_id, item_id, status: "closed"|"open"|"green"|"red"|str}
        "live_surface_records"  list of dicts: {surface_id, item_id, status: "open"|"closed"|"green"|"red"|str}
    """
    findings: list[ContradictionFinding] = []
    ledger_records = _as_list(records.get("status_ledger_records"))
    live_records = _as_list(records.get("live_surface_records"))

    _closed_or_green = frozenset({"closed", "green", "done", "resolved"})
    _open_or_red = frozenset({"open", "red", "failing", "blocked", "in_progress"})

    # Build map: item_id -> live surface status
    live_by_item: dict[str, Any] = {}
    for live in live_records:
        if live:
            item_id = _as_str(live.get("item_id"))
            if item_id:
                live_by_item[item_id] = live

    for ledger in ledger_records:
        if not ledger:
            continue
        item_id = _as_str(ledger.get("item_id"))
        if not item_id:
            continue
        ledger_status = _as_str(ledger.get("status")) or ""
        live_rec = live_by_item.get(item_id)
        if not live_rec:
            continue
        live_status = _as_str(live_rec.get("status")) or ""

        if ledger_status in _closed_or_green and live_status in _open_or_red:
            ledger_id = _as_str(ledger.get("ledger_id")) or f"ledger:{item_id}"
            surface_id = _as_str(live_rec.get("surface_id")) or f"surface:{item_id}"
            src_a = SourceRef(
                ref_id=ledger_id,
                ref_type="status_ledger",
                description=f"Ledger '{ledger_id}' reports item '{item_id}' as '{ledger_status}'",
            )
            src_b = SourceRef(
                ref_id=surface_id,
                ref_type="live_surface",
                description=f"Live surface reports item '{item_id}' as '{live_status}'",
            )
            findings.append(
                _make_finding(
                    ctype="current_status_vs_live_surface",
                    source_a=src_a,
                    source_b=src_b,
                    evidence_refs=[
                        EvidenceRef(
                            evidence_id=surface_id,
                            evidence_type="live_surface_snapshot",
                            strength="strong",
                            description=f"Live surface shows '{live_status}' vs. ledger '{ledger_status}'",
                        )
                    ],
                    severity="blocking",
                    confidence=0.90,
                    recommended_action=(
                        f"Item '{item_id}' is reported as '{ledger_status}' in ledger "
                        f"but '{live_status}' on live surface. Reconcile before proceeding."
                    ),
                    detected_at=detected_at,
                )
            )
    return findings


def _rule_runbook_vs_contract(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: runbook instruction violates a contract/governance constraint.

    Input contract (records keys):
        "runbook_steps"  list of dicts: {step_id, runbook_id, instruction, violates_contract: str|None, severity_hint: str|None}
        "contracts"      list of dicts: {contract_id, constraint}
    """
    findings: list[ContradictionFinding] = []
    runbook_steps = _as_list(records.get("runbook_steps"))

    for step in runbook_steps:
        if not step:
            continue
        violates = _as_str(step.get("violates_contract"))
        if not violates:
            continue
        step_id = _as_str(step.get("step_id")) or "unknown-step"
        runbook_id = _as_str(step.get("runbook_id")) or "unknown-runbook"
        severity = _as_str(step.get("severity_hint")) or "warning"
        if severity not in SEVERITY_LEVELS:
            severity = "warning"

        src_a = SourceRef(
            ref_id=step_id,
            ref_type="runbook",
            path=runbook_id,
            description=_as_str(step.get("instruction")) or f"Runbook step '{step_id}'",
        )
        src_b = SourceRef(
            ref_id=violates,
            ref_type="contract",
            description=f"Contract/governance constraint violated by step '{step_id}'",
        )
        findings.append(
            _make_finding(
                ctype="runbook_vs_contract",
                source_a=src_a,
                source_b=src_b,
                evidence_refs=[
                    EvidenceRef(
                        evidence_id=violates,
                        evidence_type="governance_constraint",
                        strength="strong",
                        description=f"Constraint '{violates}' violated by runbook step '{step_id}'",
                    )
                ],
                severity=severity,
                confidence=0.80,
                recommended_action=(
                    f"Runbook step '{step_id}' in '{runbook_id}' violates contract '{violates}'. "
                    "Align runbook with contract or raise a governance decision to update the constraint."
                ),
                detected_at=detected_at,
            )
        )
    return findings


def _rule_test_vs_claim(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: a claim says 'tested/covered' but the test ref is missing or failed.

    Input contract (records keys):
        "claims"      list of dicts: {claim_id, coverage_claim: "tested"|"covered"|None, test_refs: list[str]}
        "test_results" list of dicts: {test_id, status: "passed"|"failed"|"missing"|str}
    """
    findings: list[ContradictionFinding] = []
    claims = _as_list(records.get("claims"))
    test_results = _as_list(records.get("test_results"))

    test_by_id: dict[str, Any] = {}
    for tr in test_results:
        if tr:
            tid = _as_str(tr.get("test_id"))
            if tid:
                test_by_id[tid] = tr

    _coverage_assertions = frozenset({"tested", "covered", "verified"})

    for claim in claims:
        if not claim:
            continue
        coverage = _as_str(claim.get("coverage_claim")) or ""
        if coverage.lower() not in _coverage_assertions:
            continue
        claim_id = _as_str(claim.get("claim_id")) or "unknown-claim"
        test_refs = [_as_str(r) for r in _as_list(claim.get("test_refs")) if _as_str(r)]

        if not test_refs:
            # Claim says tested but no test refs
            src_a = SourceRef(
                ref_id=claim_id,
                ref_type="claim",
                description=f"Claim '{claim_id}' asserts '{coverage}' but has no test refs",
            )
            src_b = SourceRef(
                ref_id=f"missing:test:{claim_id}",
                ref_type="test",
                description="No test references found for this coverage claim",
            )
            findings.append(
                _make_finding(
                    ctype="test_vs_claim",
                    source_a=src_a,
                    source_b=src_b,
                    claim_refs=[claim_id],
                    evidence_refs=[
                        EvidenceRef(
                            evidence_id=f"missing:{claim_id}",
                            evidence_type="test_ref_absence",
                            strength="blocking_missing",
                            description=f"No test refs for coverage claim '{claim_id}'",
                        )
                    ],
                    severity="blocking",
                    confidence=0.85,
                    recommended_action=(
                        f"Claim '{claim_id}' asserts '{coverage}' without test references. "
                        "Add test refs or retract the coverage assertion."
                    ),
                    detected_at=detected_at,
                )
            )
            continue

        for test_id in test_refs:
            tr = test_by_id.get(test_id)
            if tr is None:
                status = "missing"
                severity = "warning"
            else:
                status = _as_str(tr.get("status")) or "missing"
                severity = "blocking" if status == "failed" else ("warning" if status == "missing" else "info")

            if severity != "info":
                src_a = SourceRef(
                    ref_id=claim_id,
                    ref_type="claim",
                    description=f"Claim '{claim_id}' asserts '{coverage}'",
                )
                src_b = SourceRef(
                    ref_id=test_id,
                    ref_type="test",
                    description=f"Test '{test_id}' status: {status}",
                )
                findings.append(
                    _make_finding(
                        ctype="test_vs_claim",
                        source_a=src_a,
                        source_b=src_b,
                        claim_refs=[claim_id],
                        evidence_refs=[
                            EvidenceRef(
                                evidence_id=test_id,
                                evidence_type="test_result",
                                strength="none" if status in {"failed", "missing"} else "weak",
                                description=f"Test '{test_id}' is {status}",
                            )
                        ],
                        severity=severity,
                        confidence=0.80,
                        recommended_action=(
                            f"Test '{test_id}' referenced by claim '{claim_id}' is {status}. "
                            f"Fix or re-run the test, or retract the '{coverage}' assertion."
                        ),
                        detected_at=detected_at,
                    )
                )
    return findings


def _rule_stale_decision_vs_new_evidence(
    records: Mapping[str, Any],
    detected_at: str,
) -> list[ContradictionFinding]:
    """Rule: a decision is older than evidence that supersedes or invalidates it.

    Input contract (records keys):
        "decisions"        list of dicts: {decision_id, created_at: ISO str, status}
        "evidence_records" list of dicts: {evidence_id, created_at: ISO str, supersedes_decision: str|None}
    """
    findings: list[ContradictionFinding] = []
    decisions = _as_list(records.get("decisions"))
    evidence_records = _as_list(records.get("evidence_records"))

    dec_by_id: dict[str, Any] = {}
    for dec in decisions:
        if dec:
            did = _as_str(dec.get("decision_id"))
            if did:
                dec_by_id[did] = dec

    for ev in evidence_records:
        if not ev:
            continue
        supersedes = _as_str(ev.get("supersedes_decision"))
        if not supersedes:
            continue
        dec_rec = dec_by_id.get(supersedes)
        if not dec_rec:
            continue

        dec_created = _as_str(dec_rec.get("created_at")) or ""
        ev_created = _as_str(ev.get("created_at")) or ""
        dec_status = _as_str(dec_rec.get("status")) or "open"

        if dec_status in {"resolved", "superseded"}:
            continue

        if not ev_created or not dec_created or ev_created <= dec_created:
            continue

        ev_id = _as_str(ev.get("evidence_id")) or "unknown-evidence"
        severity = "blocking" if dec_status not in {"acknowledged"} else "warning"

        src_a = SourceRef(
            ref_id=supersedes,
            ref_type="decision",
            description=f"Decision '{supersedes}' created at {dec_created}, status: {dec_status}",
        )
        src_b = SourceRef(
            ref_id=ev_id,
            ref_type="evidence",
            description=f"Evidence '{ev_id}' created at {ev_created} supersedes decision '{supersedes}'",
        )
        findings.append(
            _make_finding(
                ctype="stale_decision_vs_new_evidence",
                source_a=src_a,
                source_b=src_b,
                evidence_refs=[
                    EvidenceRef(
                        evidence_id=ev_id,
                        evidence_type="superseding_evidence",
                        strength="strong",
                        description=f"Evidence '{ev_id}' invalidates/supersedes decision '{supersedes}'",
                    )
                ],
                severity=severity,
                confidence=0.80,
                recommended_action=(
                    f"Decision '{supersedes}' is stale. Evidence '{ev_id}' (created {ev_created}) "
                    "supersedes it. Update or close the decision."
                ),
                detected_at=detected_at,
            )
        )
    return findings


# ── Public API ────────────────────────────────────────────────────────────────


def scan_contradictions_v1(
    records: Mapping[str, Any],
    overrides: Mapping[str, str] | None = None,
) -> ContradictionScanResult:
    """Run all contradiction detection rules on the provided records.

    This is the primary public entry point. Read-only. No writes. No network.
    No DB access. No GitHub calls. No auto-fix.

    Args:
        records:   Dict of input records keyed by domain (see individual rule
                   docstrings for exact keys). Unknown keys are ignored.
        overrides: Optional mapping of contradiction_id -> override_status
                   (e.g. {"abc123": "false_positive", "def456": "accepted_risk"}).
                   Matched findings retain their original fields but get
                   status updated and blocking set to False.

    Returns:
        ContradictionScanResult with all findings, blocking_count, total_count.

    Guardrails:
        - No write operations anywhere in this call chain.
        - All timestamps via cdb_utcnow (clock-injected, not wall-clock).
        - No random UUID generation — IDs are SHA256-based and deterministic.
        - Blocking findings are surfaced but grant no action authority.
        - LR status remains NO-GO for live trading.
    """
    if not isinstance(records, Mapping):
        raise ContradictionScanError(
            f"records must be a Mapping, got {type(records).__name__}"
        )

    detected_at = cdb_utcnow().isoformat()

    rule_fns = [
        _rule_doc_vs_code,
        _rule_doc_vs_decision,
        _rule_decision_vs_evidence,
        _rule_claim_vs_evidence,
        _rule_memory_vs_source,
        _rule_current_status_vs_live_surface,
        _rule_runbook_vs_contract,
        _rule_test_vs_claim,
        _rule_stale_decision_vs_new_evidence,
    ]

    all_findings: list[ContradictionFinding] = []
    for rule_fn in rule_fns:
        all_findings.extend(rule_fn(records, detected_at))

    all_findings = _apply_overrides(all_findings, overrides)

    blocking_count = sum(1 for f in all_findings if f.blocking)

    return ContradictionScanResult(
        schema_version=SCHEMA_VERSION,
        scanned_at=detected_at,
        findings=tuple(all_findings),
        blocking_count=blocking_count,
        total_count=len(all_findings),
    )
