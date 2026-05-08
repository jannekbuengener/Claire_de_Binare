"""Architect Signal Service v1 — side-effect-free domain component.

Issues:
    #2174 — [SURREALDB][CONTEXT][ARCHITECT-SIGNALS] Implement architect signal service v1
    Parent: #2170 (Wave-18 anchor)
    Epic: #1976

Scope:
    Pure, deterministic architect signal service. Generates proactive architecture
    signals from quality scores, contradiction findings, stale findings, and scope
    drift findings. No DB access. No SurrealDB SDK. No MCP. No networking.
    No writes. No auto-fix. No live-go. No automatic issue creation.

    Detects 11 signal types:
        stale_area                   — area has multiple stale findings
        weakly_evidenced_decision    — decision lacks strong evidence
        underdocumented_surface      — sources missing documentation
        undertested_surface          — sources missing tests
        high_dependency_risk         — dependency edges with low confidence
        contradiction_hotspot        — area with multiple open contradictions
        scope_drift_hotspot          — area with multiple open scope drift findings
        repeated_agent_confusion     — multiple stale/contradiction findings on same path
        redundant_docs               — documentation coverage exceeds source count (heuristic)
        missing_owner                — sources without owner metadata
        fragile_context_path         — combined stale + contradiction + scope drift on same path

Guardrails:
    - Architect Signal is recommendation, not command.
    - No automatic issue creation.
    - accepted_risk / false_positive is modellable.
    - No auto-fix. No auto-write.
    - LR status remains NO-GO for live trading.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "architect-signals/v1"
DETECTED_BY = "architect-signals/v1"

SIGNAL_TYPES = frozenset(
    {
        "stale_area",
        "weakly_evidenced_decision",
        "underdocumented_surface",
        "undertested_surface",
        "high_dependency_risk",
        "contradiction_hotspot",
        "scope_drift_hotspot",
        "repeated_agent_confusion",
        "redundant_docs",
        "missing_owner",
        "fragile_context_path",
    }
)

SIGNAL_SEVERITIES = ("info", "watch", "blocking")

STATUS_VALUES = frozenset(
    {
        "open",
        "accepted_risk",
        "false_positive",
        "resolved",
        "acknowledged",
    }
)

GUARDRAILS: tuple[str, ...] = (
    "Architect Signal is recommendation, not command.",
    "No automatic issue creation.",
    "No auto-fix. No auto-write.",
    "No Live-Readiness-Go.",
    "No Echtgeld-Go.",
    "Human-GO required for any action after blocking architect signal.",
)

# Thresholds
_STALE_AREA_THRESHOLD = 2          # ≥ N open stale findings → stale_area
_CONTRADICTION_HOTSPOT_THRESHOLD = 2  # ≥ N open contradictions → hotspot
_SCOPE_DRIFT_HOTSPOT_THRESHOLD = 2 # ≥ N open scope drifts → hotspot
_LOW_CONFIDENCE_FRACTION = 0.50    # fraction of low-confidence edges → high_dependency_risk


class ArchitectSignalError(ValueError):
    """Raised when architect signal inputs are invalid or unsafe."""


# ── Data Models ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ArchitectSignal:
    """A single architect signal finding."""

    signal_id: str
    signal_type: str
    severity: str           # info / watch / blocking
    title: str
    explanation: str
    affected_paths: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    recommended_action: str
    status: str = "open"    # open / accepted_risk / false_positive / resolved
    detected_by: str = DETECTED_BY
    detected_at: str = field(default_factory=lambda: cdb_utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "severity": self.severity,
            "title": self.title,
            "explanation": self.explanation,
            "affected_paths": list(self.affected_paths),
            "evidence_refs": list(self.evidence_refs),
            "recommended_action": self.recommended_action,
            "status": self.status,
            "detected_by": self.detected_by,
            "detected_at": self.detected_at,
        }


@dataclass(frozen=True)
class ArchitectSignalResult:
    """Full architect signal scan result."""

    scope_id: str
    total_signals: int
    blocking_count: int
    watch_count: int
    signals: tuple[ArchitectSignal, ...]
    guardrails: tuple[str, ...] = field(default_factory=lambda: GUARDRAILS)
    scanned_at: str = field(default_factory=lambda: cdb_utcnow().isoformat())
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scope_id": self.scope_id,
            "scanned_at": self.scanned_at,
            "total_signals": self.total_signals,
            "blocking_count": self.blocking_count,
            "watch_count": self.watch_count,
            "guardrails": list(self.guardrails),
            "signals": [s.to_dict() for s in self.signals],
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _as_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return str(value).strip() if value is not None else ""


def _signal_id(signal_type: str, *parts: str) -> str:
    raw = "|".join([signal_type, *parts])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_open(item: Mapping[str, Any]) -> bool:
    status = _as_str(item.get("status", "open")).lower()
    return status not in ("false_positive", "accepted_risk", "resolved", "superseded", "refreshed")


def _path_of(item: Any) -> str:
    if not isinstance(item, Mapping):
        return ""
    for key in ("source_path", "target_path", "target_ref", "affected_path", "artifact_ref", "source", "target"):
        val = _as_str(item.get(key, ""))
        if val:
            return val
    return ""


# ── Signal detectors ──────────────────────────────────────────────────────────


def _detect_stale_area(stale_findings: list[Any]) -> list[ArchitectSignal]:
    """stale_area: a path has >= threshold open stale findings."""
    path_counts: dict[str, list[str]] = {}
    for f in stale_findings:
        if not isinstance(f, Mapping) or not _is_open(f):
            continue
        path = _path_of(f) or "unknown"
        ref = _as_str(f.get("stale_id", f.get("artifact_id", "")))
        path_counts.setdefault(path, []).append(ref)

    signals = []
    for path, refs in sorted(path_counts.items()):
        if len(refs) >= _STALE_AREA_THRESHOLD:
            signals.append(
                ArchitectSignal(
                    signal_id=_signal_id("stale_area", path),
                    signal_type="stale_area",
                    severity="watch",
                    title=f"Stale area detected: {path}",
                    explanation=(
                        f"{len(refs)} open stale findings on path '{path}'. "
                        "This area may require a focused refresh review."
                    ),
                    affected_paths=(path,),
                    evidence_refs=tuple(refs[:10]),
                    recommended_action="Review stale findings and schedule a context refresh.",
                )
            )
    return signals


def _detect_weakly_evidenced_decision(decisions: list[Any], evidence_items: list[Any]) -> list[ArchitectSignal]:
    """weakly_evidenced_decision: a decision has no strong evidence refs."""
    strong_ids = {
        _as_str(e.get("evidence_id", ""))
        for e in evidence_items
        if isinstance(e, Mapping)
        and _as_str(e.get("strength", "none")).lower() in ("strong", "moderate")
        and not e.get("expired", False)
    }

    signals = []
    for d in decisions:
        if not isinstance(d, Mapping):
            continue
        status = _as_str(d.get("status", "current")).lower()
        if status in ("superseded", "invalidated"):
            continue
        dec_id = _as_str(d.get("decision_id", "unknown"))
        refs = [_as_str(r) for r in _as_list(d.get("evidence_refs")) if _as_str(r)]
        has_strong = any(r in strong_ids for r in refs) if refs else False
        if not has_strong:
            signals.append(
                ArchitectSignal(
                    signal_id=_signal_id("weakly_evidenced_decision", dec_id),
                    signal_type="weakly_evidenced_decision",
                    severity="watch",
                    title=f"Weakly evidenced decision: {dec_id}",
                    explanation=(
                        f"Decision '{dec_id}' has no strong or moderate evidence references. "
                        "Consider adding evidence to support this decision."
                    ),
                    affected_paths=(),
                    evidence_refs=tuple(refs[:5]),
                    recommended_action="Add strong evidence references to this decision.",
                )
            )
    return signals


def _detect_surface_gaps(sources: list[Any]) -> list[ArchitectSignal]:
    """underdocumented_surface and undertested_surface."""
    signals = []
    undoc_paths = []
    untest_paths = []
    for s in sources:
        if not isinstance(s, Mapping):
            continue
        path = _path_of(s) or _as_str(s.get("source_id", "unknown"))
        if not s.get("has_documentation"):
            undoc_paths.append(path)
        if not s.get("has_tests"):
            untest_paths.append(path)

    if undoc_paths:
        signals.append(
            ArchitectSignal(
                signal_id=_signal_id("underdocumented_surface", *sorted(undoc_paths[:5])),
                signal_type="underdocumented_surface",
                severity="watch",
                title=f"{len(undoc_paths)} source(s) lack documentation",
                explanation=(
                    f"{len(undoc_paths)} source(s) have no associated documentation. "
                    "Documentation gaps reduce agent context quality."
                ),
                affected_paths=tuple(undoc_paths[:20]),
                evidence_refs=(),
                recommended_action="Add documentation for undocumented sources.",
            )
        )
    if untest_paths:
        signals.append(
            ArchitectSignal(
                signal_id=_signal_id("undertested_surface", *sorted(untest_paths[:5])),
                signal_type="undertested_surface",
                severity="watch",
                title=f"{len(untest_paths)} source(s) lack tests",
                explanation=(
                    f"{len(untest_paths)} source(s) have no associated tests. "
                    "Test gaps reduce confidence in the context layer."
                ),
                affected_paths=tuple(untest_paths[:20]),
                evidence_refs=(),
                recommended_action="Add tests for untested sources.",
            )
        )
    return signals


def _detect_high_dependency_risk(dependency_edges: list[Any]) -> list[ArchitectSignal]:
    """high_dependency_risk: majority of dependency edges have low confidence."""
    if not dependency_edges:
        return []
    low_conf_edges = [
        e for e in dependency_edges
        if isinstance(e, Mapping)
        and _as_str(e.get("confidence", "unknown")).lower() in ("low", "unknown")
    ]
    fraction = len(low_conf_edges) / len(dependency_edges)
    if fraction < _LOW_CONFIDENCE_FRACTION:
        return []
    # Collect both source and target endpoints for dependency edges; fall back
    # to _path_of for edges that use other path-key conventions.
    paths_set: set[str] = set()
    for e in low_conf_edges:
        if not isinstance(e, Mapping):
            continue
        src = _as_str(e.get("source", ""))
        tgt = _as_str(e.get("target", ""))
        if src:
            paths_set.add(src)
        if tgt:
            paths_set.add(tgt)
        if not src and not tgt:
            p = _path_of(e)
            if p:
                paths_set.add(p)
    paths = sorted(paths_set)[:20]
    edge_ids = [_as_str(e.get("edge_id", "")) for e in low_conf_edges[:10]]
    return [
        ArchitectSignal(
            signal_id=_signal_id("high_dependency_risk", str(len(low_conf_edges))),
            signal_type="high_dependency_risk",
            severity="watch",
            title=f"{len(low_conf_edges)}/{len(dependency_edges)} dependency edges have low confidence",
            explanation=(
                f"{fraction:.0%} of dependency edges have low or unknown confidence. "
                "This reduces the reliability of impact analysis."
            ),
            affected_paths=tuple(paths),
            evidence_refs=tuple(edge_ids),
            recommended_action="Review and strengthen low-confidence dependency edges.",
        )
    ]


def _detect_contradiction_hotspot(contradiction_findings: list[Any]) -> list[ArchitectSignal]:
    """contradiction_hotspot: a path has >= threshold open contradictions."""
    path_counts: dict[str, list[str]] = {}
    for f in contradiction_findings:
        if not isinstance(f, Mapping) or not _is_open(f):
            continue
        path = _path_of(f) or "unknown"
        ref = _as_str(f.get("contradiction_id", ""))
        path_counts.setdefault(path, []).append(ref)

    signals = []
    for path, refs in sorted(path_counts.items()):
        if len(refs) >= _CONTRADICTION_HOTSPOT_THRESHOLD:
            signals.append(
                ArchitectSignal(
                    signal_id=_signal_id("contradiction_hotspot", path),
                    signal_type="contradiction_hotspot",
                    severity="blocking" if len(refs) >= 4 else "watch",
                    title=f"Contradiction hotspot: {path}",
                    explanation=(
                        f"{len(refs)} open contradictions detected on path '{path}'. "
                        "This area has conflicting knowledge that requires resolution."
                    ),
                    affected_paths=(path,),
                    evidence_refs=tuple(refs[:10]),
                    recommended_action=(
                        "Resolve open contradictions. "
                        "Do not proceed with writes until contradictions are cleared."
                    ),
                )
            )
    return signals


def _detect_scope_drift_hotspot(scope_drift_findings: list[Any]) -> list[ArchitectSignal]:
    """scope_drift_hotspot: a path has >= threshold open scope drift findings."""
    path_counts: dict[str, list[str]] = {}
    for f in scope_drift_findings:
        if not isinstance(f, Mapping) or not _is_open(f):
            continue
        path = _path_of(f) or "unknown"
        ref = _as_str(f.get("drift_id", ""))
        path_counts.setdefault(path, []).append(ref)

    signals = []
    for path, refs in sorted(path_counts.items()):
        if len(refs) >= _SCOPE_DRIFT_HOTSPOT_THRESHOLD:
            signals.append(
                ArchitectSignal(
                    signal_id=_signal_id("scope_drift_hotspot", path),
                    signal_type="scope_drift_hotspot",
                    severity="blocking",
                    title=f"Scope drift hotspot: {path}",
                    explanation=(
                        f"{len(refs)} open scope drift findings on path '{path}'. "
                        "Repeated scope drift indicates persistent boundary violations."
                    ),
                    affected_paths=(path,),
                    evidence_refs=tuple(refs[:10]),
                    recommended_action=(
                        "Stop writes to this path. "
                        "Review scope definitions and obtain Human-GO before continuing."
                    ),
                )
            )
    return signals


def _detect_repeated_agent_confusion(
    stale_findings: list[Any], contradiction_findings: list[Any]
) -> list[ArchitectSignal]:
    """repeated_agent_confusion: same path appears in both stale and contradiction findings."""
    stale_paths = {
        _path_of(f)
        for f in stale_findings
        if isinstance(f, Mapping) and _is_open(f) and _path_of(f)
    }
    contradiction_paths = {
        _path_of(f)
        for f in contradiction_findings
        if isinstance(f, Mapping) and _is_open(f) and _path_of(f)
    }
    overlap = sorted(stale_paths & contradiction_paths)
    if not overlap:
        return []
    return [
        ArchitectSignal(
            signal_id=_signal_id("repeated_agent_confusion", *overlap[:5]),
            signal_type="repeated_agent_confusion",
            severity="watch",
            title=f"{len(overlap)} path(s) have both stale and contradiction findings",
            explanation=(
                f"{len(overlap)} path(s) appear in both stale and contradiction findings: "
                f"{overlap[:5]}. "
                "This pattern suggests persistent knowledge quality issues."
            ),
            affected_paths=tuple(overlap[:20]),
            evidence_refs=(),
            recommended_action=(
                "Review these paths holistically. "
                "Resolve contradictions and refresh stale knowledge together."
            ),
        )
    ]


def _detect_missing_owner(sources: list[Any]) -> list[ArchitectSignal]:
    """missing_owner: sources without owner metadata."""
    no_owner = [
        _path_of(s) or _as_str(s.get("source_id", "unknown"))
        for s in sources
        if isinstance(s, Mapping)
        and not (s.get("owner") or s.get("team") or s.get("author"))
    ]
    if not no_owner:
        return []
    return [
        ArchitectSignal(
            signal_id=_signal_id("missing_owner", str(len(no_owner))),
            signal_type="missing_owner",
            severity="info",
            title=f"{len(no_owner)} source(s) have no owner metadata",
            explanation=(
                f"{len(no_owner)} sources have no owner, team, or author metadata. "
                "Ownerless sources are harder to maintain and review."
            ),
            affected_paths=tuple(no_owner[:20]),
            evidence_refs=(),
            recommended_action="Assign owner metadata to unowned sources.",
        )
    ]


def _detect_fragile_context_path(
    stale_findings: list[Any],
    contradiction_findings: list[Any],
    scope_drift_findings: list[Any],
) -> list[ArchitectSignal]:
    """fragile_context_path: a path appears across all three finding types."""
    def open_paths(findings: list[Any]) -> set[str]:
        return {
            _path_of(f)
            for f in findings
            if isinstance(f, Mapping) and _is_open(f) and _path_of(f)
        }

    triple_overlap = sorted(
        open_paths(stale_findings)
        & open_paths(contradiction_findings)
        & open_paths(scope_drift_findings)
    )
    if not triple_overlap:
        return []
    return [
        ArchitectSignal(
            signal_id=_signal_id("fragile_context_path", *triple_overlap[:5]),
            signal_type="fragile_context_path",
            severity="blocking",
            title=f"{len(triple_overlap)} path(s) have stale + contradiction + scope drift findings",
            explanation=(
                f"{len(triple_overlap)} path(s) are flagged across all three quality dimensions "
                f"(stale, contradiction, scope drift): {triple_overlap[:5]}. "
                "These are the most fragile areas of the context layer."
            ),
            affected_paths=tuple(triple_overlap[:20]),
            evidence_refs=(),
            recommended_action=(
                "Do not proceed with writes. "
                "Prioritise resolution of fragile context paths. Human-GO required."
            ),
        )
    ]


def _detect_redundant_docs(sources: list[Any]) -> list[ArchitectSignal]:
    """redundant_docs: heuristic — sources with has_documentation but no has_tests,
    concentrated in documentation-heavy paths (doc count > code count)."""
    doc_only = [
        _path_of(s) or _as_str(s.get("source_id", "unknown"))
        for s in sources
        if isinstance(s, Mapping)
        and s.get("has_documentation") is True
        and s.get("has_tests") is not True
        and _as_str(s.get("file_type", "")).lower() in ("markdown", "md", "rst", "txt")
    ]
    total_docs = sum(
        1
        for s in sources
        if isinstance(s, Mapping)
        and _as_str(s.get("file_type", "")).lower() in ("markdown", "md", "rst", "txt")
    )
    total_code = sum(
        1
        for s in sources
        if isinstance(s, Mapping)
        and _as_str(s.get("file_type", "")).lower() in ("python", "py", "ts", "js")
    )
    if total_docs <= total_code or len(doc_only) < 3:
        return []
    return [
        ArchitectSignal(
            signal_id=_signal_id("redundant_docs", str(total_docs), str(total_code)),
            signal_type="redundant_docs",
            severity="info",
            title=f"Documentation volume ({total_docs}) exceeds code volume ({total_code})",
            explanation=(
                f"There are {total_docs} documentation sources vs. {total_code} code sources. "
                f"{len(doc_only)} documentation sources have no test coverage. "
                "Consider consolidating or archiving redundant documentation."
            ),
            affected_paths=tuple(doc_only[:20]),
            evidence_refs=(),
            recommended_action="Audit documentation sources for redundancy and consolidation opportunities.",
        )
    ]


# ── Public API ────────────────────────────────────────────────────────────────


def scan_architect_signals_v1(
    bundle: Mapping[str, Any],
    as_of: str | None = None,
) -> ArchitectSignalResult:
    """Scan a context bundle for architect signals.

    The bundle should contain the same structure as the quality scoring bundle,
    optionally enriched with quality score results:

    .. code-block:: json

        {
          "meta": {"scope_id": "...", "level": "system"},
          "sources": [...],
          "decisions": [...],
          "evidence_items": [...],
          "contradiction_findings": [...],
          "stale_findings": [...],
          "dependency_edges": [...],
          "scope_drift_findings": [...]
        }

    Returns an :class:`ArchitectSignalResult` with zero or more signals.

    Raises:
        ArchitectSignalError: if the bundle is structurally invalid.
    """
    if not isinstance(bundle, Mapping):
        raise ArchitectSignalError("bundle must be a mapping")
    meta = bundle.get("meta")
    if not isinstance(meta, Mapping):
        raise ArchitectSignalError("bundle.meta must be a mapping")

    scope_id = _as_str(meta.get("scope_id", "")) or hashlib.sha256(
        str(bundle).encode()
    ).hexdigest()[:16]

    sources = _as_list(bundle.get("sources"))
    decisions = _as_list(bundle.get("decisions"))
    evidence_items = _as_list(bundle.get("evidence_items"))
    contradiction_findings = _as_list(bundle.get("contradiction_findings"))
    stale_findings = _as_list(bundle.get("stale_findings"))
    dependency_edges = _as_list(bundle.get("dependency_edges"))
    scope_drift_findings = _as_list(bundle.get("scope_drift_findings"))

    # Compute one deterministic timestamp for the entire scan so that
    # scanned_at and every signal's detected_at are identical when as_of
    # is provided (fixes non-deterministic output on repeated calls).
    effective_ts: str = as_of or cdb_utcnow().isoformat()

    all_signals: list[ArchitectSignal] = []
    all_signals.extend(_detect_stale_area(stale_findings))
    all_signals.extend(_detect_weakly_evidenced_decision(decisions, evidence_items))
    all_signals.extend(_detect_surface_gaps(sources))
    all_signals.extend(_detect_high_dependency_risk(dependency_edges))
    all_signals.extend(_detect_contradiction_hotspot(contradiction_findings))
    all_signals.extend(_detect_scope_drift_hotspot(scope_drift_findings))
    all_signals.extend(
        _detect_repeated_agent_confusion(stale_findings, contradiction_findings)
    )
    all_signals.extend(_detect_missing_owner(sources))
    all_signals.extend(
        _detect_fragile_context_path(
            stale_findings, contradiction_findings, scope_drift_findings
        )
    )
    all_signals.extend(_detect_redundant_docs(sources))

    # Stamp all signals with the effective scan timestamp.
    all_signals = [replace(s, detected_at=effective_ts) for s in all_signals]

    blocking_count = sum(1 for s in all_signals if s.severity == "blocking")
    watch_count = sum(1 for s in all_signals if s.severity == "watch")

    # Sort: blocking first, then watch, then info
    _sev_order = {"blocking": 0, "watch": 1, "info": 2}
    sorted_signals = sorted(all_signals, key=lambda s: _sev_order.get(s.severity, 3))

    return ArchitectSignalResult(
        scope_id=scope_id,
        total_signals=len(sorted_signals),
        blocking_count=blocking_count,
        watch_count=watch_count,
        signals=tuple(sorted_signals),
        scanned_at=effective_ts,
    )
