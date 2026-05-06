"""Stale Knowledge Scan Service v1 — side-effect-free domain component.

Issues:
    #2154 — [SURREALDB][CONTEXT][STALE-RUNTIME] Implement stale knowledge scan service v1
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Scope:
    Implements a minimal, deterministic stale-knowledge-scan service that works
    purely on in-memory records (input bundles as dicts). No DB access. No
    SurrealDB SDK. No MCP. No networking. No writes. No auto-fix. No live-go.

    Detects stale states for:
        source_hash_changed, source_deleted, decision_superseded,
        evidence_expired, memory_ttl_expired,
        dependency_edge_no_longer_observed,
        stale_context_package, stale_briefing

Guardrails:
    - Detection only: never implies approval, live-go, or decision authority.
    - Blocking findings are surfaced explicitly but do NOT grant permission to act.
    - No write, no mutation, no GitHub/runtime write from this module.
    - No direct wall-clock calls or random UUID generation (use core.utils.clock).
    - LR status remains NO-GO for live trading.
    - Stale Detection is signal, not authorization.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "stale-knowledge-scan/v1"
TOOL_NAME = "stale_knowledge_scan"
DETECTED_BY = "stale-knowledge-scan/v1"

STALE_TYPES = frozenset(
    {
        "source_hash_changed",
        "source_deleted",
        "decision_superseded",
        "evidence_expired",
        "memory_ttl_expired",
        "dependency_edge_no_longer_observed",
        "stale_context_package",
        "stale_briefing",
    }
)

SEVERITY_LEVELS = ("info", "warning", "blocking")

STATUS_VALUES = frozenset(
    {
        "open",
        "accepted_stale",
        "false_positive",
        "refreshed",
    }
)

GUARDRAILS: tuple[str, ...] = (
    "Stale Detection is signal, not authorization.",
    "No automatic delete.",
    "No automatic refresh write.",
    "No Live-Readiness-Go.",
    "No Echtgeld-Go.",
)

_NON_BLOCKING_STATUSES = frozenset({"accepted_stale", "false_positive", "refreshed"})

# Default freshness window in seconds used for context packages and briefings.
_DEFAULT_FRESHNESS_WINDOW_SECONDS = 86400  # 24 hours


class StaleKnowledgeScanError(ValueError):
    """Raised when stale knowledge scan inputs are invalid or unsafe."""


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StaleFinding:
    """A single detected stale-knowledge finding.

    Output contract — all fields guaranteed to be present:
        stale_id            deterministic, stable identifier (SHA256 prefix)
        stale_type          one of STALE_TYPES
        target_ref          ID or path of the stale artifact
        reason              human-readable reason string
        severity            info | warning | blocking
        confidence          float in [0.0, 1.0]
        source_refs         tuple of source IDs involved
        evidence_refs       tuple of evidence record IDs
        detected_by         str — service/version that detected this
        detected_at         ISO-8601 UTC string — via cdb_utcnow (not wall-clock)
        recommended_refresh human-readable refresh guidance string
        blocking            bool — true iff severity=blocking and status not non-blocking
        status              one of STATUS_VALUES
    """

    stale_id: str
    stale_type: str
    target_ref: str
    reason: str
    severity: str
    confidence: float
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    detected_by: str
    detected_at: str
    recommended_refresh: str
    blocking: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "stale_id": self.stale_id,
            "stale_type": self.stale_type,
            "target_ref": self.target_ref,
            "reason": self.reason,
            "severity": self.severity,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "evidence_refs": list(self.evidence_refs),
            "detected_by": self.detected_by,
            "detected_at": self.detected_at,
            "recommended_refresh": self.recommended_refresh,
            "blocking": self.blocking,
            "status": self.status,
        }


@dataclass(frozen=True)
class StaleKnowledgeScanResult:
    """Result of a full stale knowledge scan run."""

    tool: str
    schema_version: str
    status: str
    as_of: str
    total_count: int
    blocking_count: int
    findings: tuple[StaleFinding, ...]
    recommended_refresh: tuple[str, ...]
    guardrails: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        # Compute severity summary dynamically (not stored to keep frozen)
        severity_summary: dict[str, int] = {level: 0 for level in SEVERITY_LEVELS}
        for f in self.findings:
            if f.severity in severity_summary:
                severity_summary[f.severity] += 1

        return {
            "tool": self.tool,
            "schema_version": self.schema_version,
            "status": self.status,
            "as_of": self.as_of,
            "total_count": self.total_count,
            "blocking_count": self.blocking_count,
            "severity_summary": severity_summary,
            "findings": [f.to_dict() for f in self.findings],
            "recommended_refresh": list(self.recommended_refresh),
            "guardrails": list(self.guardrails),
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _stale_id(stale_type: str, target_ref: str, reason: str) -> str:
    """Generate a deterministic, stable stale finding ID.

    Uses SHA256 of the canonical string (stale_type|target_ref|reason).
    No random UUID generation, no random module — guardrails-compliant.
    """
    raw = f"{stale_type}|{target_ref}|{reason}"
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
    stale_type: str,
    target_ref: str,
    reason: str,
    severity: str,
    confidence: float,
    source_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    detected_at: str,
    recommended_refresh: str,
    status: str = "open",
) -> StaleFinding:
    sid = _stale_id(stale_type, target_ref, reason)
    blocking = _is_blocking(severity, status)
    return StaleFinding(
        stale_id=sid,
        stale_type=stale_type,
        target_ref=target_ref,
        reason=reason,
        severity=severity,
        confidence=_clamp_confidence(confidence),
        source_refs=tuple(source_refs),
        evidence_refs=tuple(evidence_refs),
        detected_by=DETECTED_BY,
        detected_at=detected_at,
        recommended_refresh=recommended_refresh,
        blocking=blocking,
        status=status,
    )


def _parse_iso(ts: str | None) -> datetime | None:
    """Parse an ISO-8601 string to a timezone-aware UTC datetime.

    Returns None on parse failure (fail-safe: unknown format → no finding).
    Handles both 'Z' suffix and '+00:00' offset.
    """
    if not ts:
        return None
    normalized = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    # Attach UTC if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ── Detection Rules ───────────────────────────────────────────────────────────


def _rule_source_hash_changed(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: source record's current_hash differs from last_verified_hash.

    Input contract (bundle key: "sources"):
        list of dicts: {
            source_id: str,
            path: str | None,
            current_hash: str,
            last_verified_hash: str,
        }
    """
    findings: list[StaleFinding] = []
    sources = _as_list(bundle.get("sources"))

    for src in sources:
        if not src:
            continue
        current_hash = _as_str(src.get("current_hash"))
        last_verified_hash = _as_str(src.get("last_verified_hash"))
        if not current_hash or not last_verified_hash:
            continue
        if current_hash == last_verified_hash:
            continue

        source_id = _as_str(src.get("source_id")) or "unknown-source"
        path = _as_str(src.get("path")) or source_id
        reason = (
            f"Source '{source_id}' hash changed: last_verified={last_verified_hash[:8]}... "
            f"current={current_hash[:8]}..."
        )
        findings.append(
            _make_finding(
                stale_type="source_hash_changed",
                target_ref=source_id,
                reason=reason,
                severity="warning",
                confidence=0.95,
                source_refs=[source_id],
                evidence_refs=[f"hash:{current_hash[:8]}"],
                detected_at=detected_at,
                recommended_refresh=(
                    f"Re-verify source '{path}'. Hash changed since last verification. "
                    "Update last_verified_hash after review."
                ),
            )
        )
    return findings


def _rule_source_deleted(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: source record is marked deleted or no longer exists.

    Input contract (bundle key: "sources"):
        list of dicts: {
            source_id: str,
            path: str | None,
            exists: bool,         # optional; False → deleted
            deleted_at: str | None,  # ISO-8601; if set → deleted
        }
    """
    findings: list[StaleFinding] = []
    sources = _as_list(bundle.get("sources"))

    for src in sources:
        if not src:
            continue
        source_id = _as_str(src.get("source_id")) or "unknown-source"
        exists = src.get("exists", True)
        deleted_at = _as_str(src.get("deleted_at"))

        is_deleted = (exists is False) or (deleted_at is not None)
        if not is_deleted:
            continue

        when = f" (deleted_at={deleted_at})" if deleted_at else ""
        reason = f"Source '{source_id}' no longer exists{when}."
        findings.append(
            _make_finding(
                stale_type="source_deleted",
                target_ref=source_id,
                reason=reason,
                severity="blocking",
                confidence=0.99,
                source_refs=[source_id],
                evidence_refs=[f"deleted:{source_id}"],
                detected_at=detected_at,
                recommended_refresh=(
                    f"Source '{source_id}' is deleted. All referencing artifacts must be "
                    "updated or tombstoned. No automatic delete from this service."
                ),
            )
        )
    return findings


def _rule_decision_superseded(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: a decision has been superseded (via superseded_by field or status).

    Input contract (bundle key: "decisions"):
        list of dicts: {
            decision_id: str,
            superseded_by: str | None,   # if set → superseded
            status: str,                 # "superseded" → stale
            topic: str | None,
        }
    """
    findings: list[StaleFinding] = []
    decisions = _as_list(bundle.get("decisions"))

    for dec in decisions:
        if not dec:
            continue
        decision_id = _as_str(dec.get("decision_id")) or "unknown-decision"
        superseded_by = _as_str(dec.get("superseded_by"))
        status = _as_str(dec.get("status")) or ""

        is_superseded = bool(superseded_by) or status == "superseded"
        if not is_superseded:
            continue

        by_str = f" by '{superseded_by}'" if superseded_by else ""
        reason = f"Decision '{decision_id}' has been superseded{by_str} (status={status or 'n/a'})."
        findings.append(
            _make_finding(
                stale_type="decision_superseded",
                target_ref=decision_id,
                reason=reason,
                severity="warning",
                confidence=0.90,
                source_refs=[decision_id] + ([superseded_by] if superseded_by else []),
                evidence_refs=[superseded_by or f"status:superseded:{decision_id}"],
                detected_at=detected_at,
                recommended_refresh=(
                    f"Decision '{decision_id}' is stale. "
                    + (f"It has been superseded by '{superseded_by}'. " if superseded_by else "")
                    + "Archive or tombstone this decision after review."
                ),
            )
        )
    return findings


def _rule_evidence_expired(
    bundle: Mapping[str, Any],
    as_of: str,
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: evidence record's expires_at is before as_of.

    Input contract (bundle key: "evidence_records"):
        list of dicts: {
            evidence_id: str,
            expires_at: str,   # ISO-8601 UTC
            topic: str | None,
        }
    """
    findings: list[StaleFinding] = []
    evidence_records = _as_list(bundle.get("evidence_records"))
    as_of_dt = _parse_iso(as_of)

    for ev in evidence_records:
        if not ev:
            continue
        evidence_id = _as_str(ev.get("evidence_id")) or "unknown-evidence"
        expires_at = _as_str(ev.get("expires_at"))
        if not expires_at:
            continue

        expires_dt = _parse_iso(expires_at)
        if expires_dt is None or as_of_dt is None:
            continue
        if expires_dt >= as_of_dt:
            continue

        reason = f"Evidence '{evidence_id}' expired at {expires_at} (as_of={as_of})."
        findings.append(
            _make_finding(
                stale_type="evidence_expired",
                target_ref=evidence_id,
                reason=reason,
                severity="warning",
                confidence=0.90,
                source_refs=[evidence_id],
                evidence_refs=[f"expired:{evidence_id}"],
                detected_at=detected_at,
                recommended_refresh=(
                    f"Evidence '{evidence_id}' has expired. "
                    "Re-collect or replace with current evidence before relying on it."
                ),
            )
        )
    return findings


def _rule_memory_ttl_expired(
    bundle: Mapping[str, Any],
    as_of: str,
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: memory record's expires_at is before as_of.

    Input contract (bundle key: "memory_records"):
        list of dicts: {
            memory_id: str,
            expires_at: str,   # ISO-8601 UTC
            scope: str | None,
        }
    """
    findings: list[StaleFinding] = []
    memory_records = _as_list(bundle.get("memory_records"))
    as_of_dt = _parse_iso(as_of)

    for mem in memory_records:
        if not mem:
            continue
        memory_id = _as_str(mem.get("memory_id")) or "unknown-memory"
        expires_at = _as_str(mem.get("expires_at"))
        if not expires_at:
            continue

        expires_dt = _parse_iso(expires_at)
        if expires_dt is None or as_of_dt is None:
            continue
        if expires_dt >= as_of_dt:
            continue

        reason = f"Memory '{memory_id}' TTL expired at {expires_at} (as_of={as_of})."
        findings.append(
            _make_finding(
                stale_type="memory_ttl_expired",
                target_ref=memory_id,
                reason=reason,
                severity="warning",
                confidence=0.90,
                source_refs=[memory_id],
                evidence_refs=[f"ttl_expired:{memory_id}"],
                detected_at=detected_at,
                recommended_refresh=(
                    f"Memory '{memory_id}' TTL has elapsed. "
                    "Refresh memory content through the appropriate process. "
                    "No automatic write from this service."
                ),
            )
        )
    return findings


def _rule_dependency_edge_stale(
    bundle: Mapping[str, Any],
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: a dependency edge is no longer observed.

    Detection triggers when:
        - observed == False, OR
        - last_observed_run_id != current_run_id (both non-empty, both set)

    Input contract (bundle key: "dependency_edges"):
        list of dicts: {
            edge_id: str,
            from_ref: str,
            to_ref: str,
            observed: bool,                     # optional; False → stale
            last_observed_run_id: str | None,
            current_run_id: str | None,
        }
    """
    findings: list[StaleFinding] = []
    dependency_edges = _as_list(bundle.get("dependency_edges"))

    for edge in dependency_edges:
        if not edge:
            continue
        edge_id = _as_str(edge.get("edge_id")) or "unknown-edge"
        from_ref = _as_str(edge.get("from_ref")) or edge_id
        to_ref = _as_str(edge.get("to_ref")) or edge_id
        observed = edge.get("observed", True)
        last_run = _as_str(edge.get("last_observed_run_id"))
        current_run = _as_str(edge.get("current_run_id"))

        run_id_drift = (
            last_run is not None
            and current_run is not None
            and last_run != current_run
        )
        is_stale = (observed is False) or run_id_drift

        if not is_stale:
            continue

        if observed is False:
            reason = f"Dependency edge '{edge_id}' ({from_ref} → {to_ref}) is marked not observed."
        else:
            reason = (
                f"Dependency edge '{edge_id}' ({from_ref} → {to_ref}) last observed in "
                f"run '{last_run}' but current run is '{current_run}'."
            )
        findings.append(
            _make_finding(
                stale_type="dependency_edge_no_longer_observed",
                target_ref=edge_id,
                reason=reason,
                severity="warning",
                confidence=0.85,
                source_refs=[edge_id, from_ref, to_ref],
                evidence_refs=[f"edge:{edge_id}"],
                detected_at=detected_at,
                recommended_refresh=(
                    f"Dependency edge '{edge_id}' ({from_ref} → {to_ref}) may be stale. "
                    "Re-run dependency analysis to verify or tombstone this edge."
                ),
            )
        )
    return findings


def _rule_stale_context_package(
    bundle: Mapping[str, Any],
    as_of: str,
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: context package has a stale snapshot ID or exceeded its freshness window.

    Detection triggers when:
        - source_snapshot_id != current_snapshot_id (both non-empty), OR
        - generated_at + freshness_window_seconds < as_of

    Input contract (bundle key: "context_packages"):
        list of dicts: {
            package_id: str,
            source_snapshot_id: str | None,
            current_snapshot_id: str | None,
            generated_at: str | None,          # ISO-8601 UTC
            freshness_window_seconds: int | None,  # default: 86400
        }
    """
    findings: list[StaleFinding] = []
    context_packages = _as_list(bundle.get("context_packages"))
    as_of_dt = _parse_iso(as_of)

    for pkg in context_packages:
        if not pkg:
            continue
        package_id = _as_str(pkg.get("package_id")) or "unknown-package"
        src_snap = _as_str(pkg.get("source_snapshot_id"))
        cur_snap = _as_str(pkg.get("current_snapshot_id"))
        generated_at = _as_str(pkg.get("generated_at"))

        try:
            freshness_window = int(pkg.get("freshness_window_seconds") or _DEFAULT_FRESHNESS_WINDOW_SECONDS)
        except (TypeError, ValueError):
            freshness_window = _DEFAULT_FRESHNESS_WINDOW_SECONDS

        # Trigger 1: snapshot ID mismatch
        if src_snap and cur_snap and src_snap != cur_snap:
            reason = (
                f"Context package '{package_id}' snapshot ID mismatch: "
                f"source_snapshot_id='{src_snap}' != current_snapshot_id='{cur_snap}'."
            )
            findings.append(
                _make_finding(
                    stale_type="stale_context_package",
                    target_ref=package_id,
                    reason=reason,
                    severity="warning",
                    confidence=0.90,
                    source_refs=[package_id, src_snap, cur_snap],
                    evidence_refs=[f"snapshot_drift:{package_id}"],
                    detected_at=detected_at,
                    recommended_refresh=(
                        f"Context package '{package_id}' was built from snapshot '{src_snap}' "
                        f"but current snapshot is '{cur_snap}'. Regenerate the package."
                    ),
                )
            )
            continue  # skip freshness check if snapshot already stale

        # Trigger 2: freshness window exceeded
        if generated_at and as_of_dt is not None:
            gen_dt = _parse_iso(generated_at)
            if gen_dt is not None:
                age_seconds = (as_of_dt - gen_dt).total_seconds()
                if age_seconds > freshness_window:
                    reason = (
                        f"Context package '{package_id}' generated at {generated_at} "
                        f"exceeds freshness window of {freshness_window}s "
                        f"(age={int(age_seconds)}s, as_of={as_of})."
                    )
                    findings.append(
                        _make_finding(
                            stale_type="stale_context_package",
                            target_ref=package_id,
                            reason=reason,
                            severity="warning",
                            confidence=0.80,
                            source_refs=[package_id],
                            evidence_refs=[f"freshness:{package_id}"],
                            detected_at=detected_at,
                            recommended_refresh=(
                                f"Context package '{package_id}' is older than "
                                f"{freshness_window}s. Regenerate with a current snapshot."
                            ),
                        )
                    )
    return findings


def _rule_stale_briefing(
    bundle: Mapping[str, Any],
    as_of: str,
    detected_at: str,
) -> list[StaleFinding]:
    """Rule: briefing has a stale snapshot ID or exceeded its freshness window.

    Same detection pattern as context packages, applied to briefing artifacts.

    Input contract (bundle key: "briefings"):
        list of dicts: {
            briefing_id: str,
            source_snapshot_id: str | None,
            current_snapshot_id: str | None,
            generated_at: str | None,          # ISO-8601 UTC
            freshness_window_seconds: int | None,
        }
    """
    findings: list[StaleFinding] = []
    briefings = _as_list(bundle.get("briefings"))
    as_of_dt = _parse_iso(as_of)

    for briefing in briefings:
        if not briefing:
            continue
        briefing_id = _as_str(briefing.get("briefing_id")) or "unknown-briefing"
        src_snap = _as_str(briefing.get("source_snapshot_id"))
        cur_snap = _as_str(briefing.get("current_snapshot_id"))
        generated_at = _as_str(briefing.get("generated_at"))

        try:
            freshness_window = int(briefing.get("freshness_window_seconds") or _DEFAULT_FRESHNESS_WINDOW_SECONDS)
        except (TypeError, ValueError):
            freshness_window = _DEFAULT_FRESHNESS_WINDOW_SECONDS

        # Trigger 1: snapshot ID mismatch
        if src_snap and cur_snap and src_snap != cur_snap:
            reason = (
                f"Briefing '{briefing_id}' snapshot ID mismatch: "
                f"source_snapshot_id='{src_snap}' != current_snapshot_id='{cur_snap}'."
            )
            findings.append(
                _make_finding(
                    stale_type="stale_briefing",
                    target_ref=briefing_id,
                    reason=reason,
                    severity="warning",
                    confidence=0.90,
                    source_refs=[briefing_id, src_snap, cur_snap],
                    evidence_refs=[f"snapshot_drift:{briefing_id}"],
                    detected_at=detected_at,
                    recommended_refresh=(
                        f"Briefing '{briefing_id}' was built from snapshot '{src_snap}' "
                        f"but current snapshot is '{cur_snap}'. Regenerate the briefing."
                    ),
                )
            )
            continue  # skip freshness check if snapshot already stale

        # Trigger 2: freshness window exceeded
        if generated_at and as_of_dt is not None:
            gen_dt = _parse_iso(generated_at)
            if gen_dt is not None:
                age_seconds = (as_of_dt - gen_dt).total_seconds()
                if age_seconds > freshness_window:
                    reason = (
                        f"Briefing '{briefing_id}' generated at {generated_at} "
                        f"exceeds freshness window of {freshness_window}s "
                        f"(age={int(age_seconds)}s, as_of={as_of})."
                    )
                    findings.append(
                        _make_finding(
                            stale_type="stale_briefing",
                            target_ref=briefing_id,
                            reason=reason,
                            severity="warning",
                            confidence=0.80,
                            source_refs=[briefing_id],
                            evidence_refs=[f"freshness:{briefing_id}"],
                            detected_at=detected_at,
                            recommended_refresh=(
                                f"Briefing '{briefing_id}' is older than "
                                f"{freshness_window}s. Regenerate with a current snapshot."
                            ),
                        )
                    )
    return findings


# ── Public API ────────────────────────────────────────────────────────────────


def scan_stale_knowledge_v1(
    bundle: Mapping[str, Any],
    as_of: str | None = None,
) -> StaleKnowledgeScanResult:
    """Run all stale-knowledge detection rules on the provided input bundle.

    This is the primary public entry point. Read-only. No writes. No network.
    No DB access. No GitHub calls. No auto-fix. No auto-delete.

    Args:
        bundle:  Dict of input records keyed by domain (see individual rule
                 docstrings for exact keys). Unknown keys are ignored.
        as_of:   Optional ISO-8601 UTC string representing the reference time
                 for TTL/expiry comparisons. Defaults to cdb_utcnow().isoformat().

    Returns:
        StaleKnowledgeScanResult with all findings, blocking_count, severity_summary,
        recommended_refresh list, and guardrails.

    Guardrails:
        - No write operations anywhere in this call chain.
        - All timestamps via cdb_utcnow (clock-injected, not wall-clock).
        - No random UUID generation — IDs are SHA256-based and deterministic.
        - Blocking findings are surfaced but grant no action authority.
        - LR status remains NO-GO for live trading.
        - Stale Detection is signal, not authorization.
    """
    if not isinstance(bundle, Mapping):
        raise StaleKnowledgeScanError(
            f"bundle must be a Mapping, got {type(bundle).__name__}"
        )

    resolved_as_of: str = as_of if as_of is not None else cdb_utcnow().isoformat()
    detected_at = resolved_as_of

    rule_fns_simple = [
        _rule_source_hash_changed,
        _rule_source_deleted,
        _rule_decision_superseded,
    ]
    rule_fns_time = [
        _rule_evidence_expired,
        _rule_memory_ttl_expired,
        _rule_stale_context_package,
        _rule_stale_briefing,
    ]

    all_findings: list[StaleFinding] = []

    for rule_fn in rule_fns_simple:
        all_findings.extend(rule_fn(bundle, detected_at))

    all_findings.extend(_rule_dependency_edge_stale(bundle, detected_at))

    for rule_fn in rule_fns_time:
        all_findings.extend(rule_fn(bundle, resolved_as_of, detected_at))

    blocking_count = sum(1 for f in all_findings if f.blocking)

    # Deduplicated recommended_refresh list (preserving first-seen order)
    seen: set[str] = set()
    recommended: list[str] = []
    for f in all_findings:
        if f.recommended_refresh and f.recommended_refresh not in seen:
            seen.add(f.recommended_refresh)
            recommended.append(f.recommended_refresh)

    return StaleKnowledgeScanResult(
        tool=TOOL_NAME,
        schema_version=SCHEMA_VERSION,
        status="ok",
        as_of=resolved_as_of,
        total_count=len(all_findings),
        blocking_count=blocking_count,
        findings=tuple(all_findings),
        recommended_refresh=tuple(recommended),
        guardrails=GUARDRAILS,
    )
