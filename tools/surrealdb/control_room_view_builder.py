"""Visual Control Room View Builder v1 — side-effect-free domain component.

Issues:
    #2180 — [SURREALDB][CONTEXT][CONTROL-ROOM] Implement control room view builder v1
    #2181 — [SURREALDB][CONTEXT][GRAPH-REPORTS] Generate graph and architecture reports
    #2182 — [SURREALDB][CONTEXT][DECISION-VIEW] Generate decision chain view
    #2183 — [SURREALDB][CONTEXT][EVIDENCE-VIEW] Generate evidence map view
    #2184 — [SURREALDB][CONTEXT][RISK-SURFACE] Generate risk surface report
    Parent: #2179 (Wave-19 anchor)
    Epic: #1976

Scope:
    Pure, deterministic Visual Control Room View Builder.
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No auto-fix. No live-go. No trading console. No runtime control.

    Builds ``visual_control_view``-conformant view objects from in-memory
    bundles.  Supports 9 view types defined in the Wave-6 information model
    (docs/surrealdb/visual-control-room-model-v0.md):

        knowledge_graph_view      — full context graph nodes/edges
        architecture_map          — service topology, dependency graph
        decision_chain_view       — ordered decision events / supersession chain
        evidence_map              — evidence coverage per domain
        risk_surface_report       — scope drift, blocking findings, quality weak spots
        stale_knowledge_view      — stale contexts, refresh recommendations
        scope_drift_events        — logged scope drift findings by severity
        agent_memory_view         — memory entries, trust levels, TTL status
        quality_score_dashboard   — per-dimension quality scores, grade bands

    Every output carries embedded guardrails (always non-empty).
    Outputs are plain dicts suitable for JSON serialisation or SurrealDB
    insertion.  The builder never writes anything.

Guardrails:
    - View Builder is signal surface, not authorization layer.
    - No trading console. No runtime control. No Live-Freigabe.
    - No Live-Readiness-Go. No Echtgeld-Go.
    - read-only semantics enforced: no mutations in any view path.
    - Human-GO required for any action after blocking findings.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "control-room-view-builder/v1"
GENERATED_BY = "control_room_view_builder/v1"

VIEW_TYPES: frozenset[str] = frozenset(
    {
        "knowledge_graph_view",
        "architecture_map",
        "decision_chain_view",
        "evidence_map",
        "risk_surface_report",
        "stale_knowledge_view",
        "scope_drift_events",
        "agent_memory_view",
        "quality_score_dashboard",
    }
)

EXPORT_FORMATS: tuple[str, ...] = ("json", "markdown", "html", "mermaid")

GUARDRAILS: tuple[str, ...] = (
    "View Builder is signal surface, not authorization layer.",
    "No trading console. No runtime control. No Live-Freigabe.",
    "No Live-Readiness-Go. No Echtgeld-Go.",
    "read-only: no mutations anywhere in the view build path.",
    "Human-GO required for any action after blocking findings.",
)


class ControlRoomError(ValueError):
    """Raised when view builder inputs are invalid or unsafe."""


# ── Data Source Reference ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class DataSourceRef:
    """Reference to a data source used to populate a view."""

    table: str
    query_hint: str
    write_allowed: bool = False  # invariant: always False

    def to_dict(self) -> dict[str, Any]:
        return {
            # Canonical DataSourceRef fields per visual-control-room-model-v0.md §7.
            "source_type": "surrealdb_table",
            "source_ref": self.table,
            "query_hint": self.query_hint,
            "write_allowed": False,  # hard-coded; never allow write
        }


# ── View Result ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ControlRoomView:
    """Single visual_control_view-conformant result object."""

    view_id: str
    view_type: str
    view_label: str
    target_scope: str
    data_sources: tuple[DataSourceRef, ...]
    filters: dict[str, Any]
    required_queries: tuple[str, ...]
    display_entities: tuple[str, ...]
    display_edges: tuple[str, ...]
    warnings: tuple[str, ...]
    generated_at: str
    generated_by: str
    export_formats: tuple[str, ...]
    guardrails: tuple[str, ...]
    payload: dict[str, Any]  # view-type-specific rendered content
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "view_id": self.view_id,
            "view_type": self.view_type,
            "view_label": self.view_label,
            "target_scope": self.target_scope,
            "data_sources": [ds.to_dict() for ds in self.data_sources],
            "filters": dict(self.filters),
            "required_queries": list(self.required_queries),
            "display_entities": list(self.display_entities),
            "display_edges": list(self.display_edges),
            "warnings": list(self.warnings),
            "generated_at": self.generated_at,
            "generated_by": self.generated_by,
            "export_formats": list(self.export_formats),
            "guardrails": list(self.guardrails),
            "payload": self.payload,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────


def _view_id(view_type: str, scope: str, generated_at: str) -> str:
    """Deterministic SHA-256-based view identifier."""
    raw = f"{view_type}:{scope}:{generated_at}"
    return "view:" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _as_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return str(value) if value is not None else ""


def _safe_scope(bundle: Mapping[str, Any]) -> str:
    meta = bundle.get("meta") or {}
    scope_id = meta.get("scope_id") or "unknown"
    return _as_str(scope_id)


def _validate_bundle(bundle: Mapping[str, Any]) -> None:
    if not isinstance(bundle, Mapping):
        raise ControlRoomError("bundle must be a Mapping")
    meta = bundle.get("meta")
    if meta is None or not isinstance(meta, Mapping):
        raise ControlRoomError("bundle.meta is required and must be a Mapping")
    scope_id = meta.get("scope_id")
    if not scope_id or not _as_str(scope_id):
        raise ControlRoomError("bundle.meta.scope_id is required and non-empty")


# ── View Builders ─────────────────────────────────────────────────────────────


def _build_knowledge_graph_view(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    sources = _as_list(bundle.get("sources"))
    dependencies = _as_list(bundle.get("dependency_edges"))

    nodes: list[dict[str, Any]] = []
    for src in sources:
        if not isinstance(src, Mapping):
            continue
        nodes.append(
            {
                "node_id": _as_str(src.get("source_path") or src.get("source_id") or ""),
                "node_type": "repo_artifact",
                "label": _as_str(src.get("source_path") or ""),
                "status": _as_str(src.get("status") or "unknown"),
            }
        )

    edges: list[dict[str, Any]] = []
    for dep in dependencies:
        if not isinstance(dep, Mapping):
            continue
        edges.append(
            {
                "edge_id": _as_str(dep.get("edge_id") or ""),
                "edge_type": "dependency_edge",
                # Canonical indexer rows use from_id/to_id; fall back to
                # from_source/to_source and source_path/target_path for other
                # bundle shapes.
                "from": _as_str(
                    dep.get("from_source")
                    or dep.get("from_id")
                    or dep.get("source_path")
                    or ""
                ),
                "to": _as_str(
                    dep.get("to_source")
                    or dep.get("to_id")
                    or dep.get("target_path")
                    or ""
                ),
                "confidence": _as_str(dep.get("confidence") or "unknown"),
            }
        )

    warnings: list[str] = []
    if not nodes:
        warnings.append("No repo_artifact nodes found in bundle.")

    return ControlRoomView(
        view_id=_view_id("knowledge_graph_view", scope, generated_at),
        view_type="knowledge_graph_view",
        view_label="Knowledge Graph View",
        target_scope=scope,
        data_sources=(
            DataSourceRef("repo_artifact", "SELECT * FROM repo_artifact LIMIT 100"),
            DataSourceRef("dependency_edge", "SELECT * FROM dependency_edge LIMIT 200"),
            DataSourceRef("doc_chunk", "SELECT * FROM doc_chunk LIMIT 200"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM repo_artifact LIMIT 100",
            "SELECT * FROM dependency_edge LIMIT 200",
        ),
        display_entities=("repo_artifact", "doc_chunk", "code_symbol"),
        display_edges=("dependency_edge",),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)},
    )


def _build_architecture_map(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    sources = _as_list(bundle.get("sources"))
    dependencies = _as_list(bundle.get("dependency_edges"))

    modules: list[dict[str, Any]] = []
    for src in sources:
        if not isinstance(src, Mapping):
            continue
        path = _as_str(src.get("source_path") or "")
        # Heuristic: top-level directory is the "module"
        parts = path.split("/")
        module_name = parts[0] if parts else path
        modules.append(
            {
                "module": module_name,
                "source_path": path,
                "has_documentation": bool(src.get("has_documentation")),
                "has_tests": bool(src.get("has_tests")),
                "owner": _as_str(src.get("owner") or ""),
            }
        )

    dep_edges: list[dict[str, Any]] = []
    for dep in dependencies:
        if not isinstance(dep, Mapping):
            continue
        dep_edges.append(
            {
                "edge_id": _as_str(dep.get("edge_id") or ""),
                # Canonical indexer rows use from_id/to_id; fall back to
                # from_source/to_source for bundles that use the display names.
                "from": _as_str(
                    dep.get("from_source") or dep.get("from_id") or dep.get("from") or ""
                ),
                "to": _as_str(
                    dep.get("to_source") or dep.get("to_id") or dep.get("to") or ""
                ),
                "confidence": _as_str(dep.get("confidence") or "unknown"),
            }
        )

    warnings: list[str] = []
    if not modules:
        warnings.append("No source nodes found for architecture map.")

    return ControlRoomView(
        view_id=_view_id("architecture_map", scope, generated_at),
        view_type="architecture_map",
        view_label="Architecture Map",
        target_scope=scope,
        data_sources=(
            DataSourceRef("code_symbol", "SELECT * FROM code_symbol WHERE symbol_type IN ['module','class']"),
            DataSourceRef("dependency_edge", "SELECT * FROM dependency_edge LIMIT 200"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM code_symbol WHERE symbol_type IN ['module','class']",
            "SELECT * FROM dependency_edge LIMIT 200",
        ),
        display_entities=("code_symbol", "repo_artifact"),
        display_edges=("dependency_edge",),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={"modules": modules, "dependency_edges": dep_edges},
    )


def _build_decision_chain_view(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    decisions = _as_list(bundle.get("decisions"))
    evidence_items = _as_list(bundle.get("evidence_items"))

    ev_index: dict[str, dict[str, Any]] = {}
    for ev in evidence_items:
        if isinstance(ev, Mapping):
            eid = _as_str(ev.get("evidence_id") or "")
            if eid:
                ev_index[eid] = dict(ev)

    chain: list[dict[str, Any]] = []
    open_decisions: list[dict[str, Any]] = []
    superseded_count = 0

    for dec in decisions:
        if not isinstance(dec, Mapping):
            continue
        dec_id = _as_str(dec.get("decision_id") or "")
        status = _as_str(dec.get("status") or "unknown")
        ev_refs = _as_list(dec.get("evidence_refs"))
        linked_evidence = [ev_index[r] for r in ev_refs if r in ev_index]

        entry: dict[str, Any] = {
            "decision_id": dec_id,
            "status": status,
            "evidence_count": len(linked_evidence),
            "evidence_refs": [_as_str(r) for r in ev_refs],
            "superseded_by": _as_str(dec.get("superseded_by") or ""),
        }
        chain.append(entry)
        if status in ("superseded", "invalidated"):
            superseded_count += 1
        if status == "open":
            open_decisions.append(entry)

    warnings: list[str] = []
    if not chain:
        warnings.append("No decision events found in bundle.")
    if superseded_count > 0:
        warnings.append(f"{superseded_count} superseded/invalidated decision(s) in chain.")

    return ControlRoomView(
        view_id=_view_id("decision_chain_view", scope, generated_at),
        view_type="decision_chain_view",
        view_label="Decision Chain View",
        target_scope=scope,
        data_sources=(
            DataSourceRef("decision_event", "SELECT * FROM decision_event ORDER BY created_at"),
            DataSourceRef("claim", "SELECT * FROM claim LIMIT 200"),
            DataSourceRef("evidence_ref", "SELECT * FROM evidence_ref LIMIT 200"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM decision_event ORDER BY created_at",
            "SELECT * FROM evidence_ref LIMIT 200",
        ),
        display_entities=("decision_event", "claim", "evidence_ref"),
        display_edges=("supersedes", "evidence_link"),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "decision_chain": chain,
            "open_decisions": open_decisions,
            "total_decisions": len(chain),
            "superseded_count": superseded_count,
        },
    )


def _build_evidence_map(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    evidence_items = _as_list(bundle.get("evidence_items"))
    decisions = _as_list(bundle.get("decisions"))

    # Compute coverage per decision
    evidence_by_strength: dict[str, int] = {"strong": 0, "moderate": 0, "weak": 0, "unknown": 0}
    expired_count = 0
    covered_decisions = 0
    uncovered_decisions = 0

    for ev in evidence_items:
        if not isinstance(ev, Mapping):
            continue
        strength = _as_str(ev.get("strength") or "unknown")
        if strength not in evidence_by_strength:
            strength = "unknown"
        evidence_by_strength[strength] += 1
        if ev.get("expired"):
            expired_count += 1

    # Build index of valid evidence IDs — dangling/mistyped refs must not count
    # as covered.  A decision is covered only if at least one of its refs resolves
    # to an actual evidence item in the bundle.  (#2384 correctness fix)
    valid_evidence_ids: frozenset[str] = frozenset(
        _as_str(ev.get("evidence_id") or ev.get("id") or "")
        for ev in evidence_items
        if isinstance(ev, Mapping) and (ev.get("evidence_id") or ev.get("id"))
    )

    for dec in decisions:
        if not isinstance(dec, Mapping):
            continue
        ev_refs = _as_list(dec.get("evidence_refs"))
        # Covered only when at least one ref resolves to a real evidence item.
        if ev_refs and any(
            isinstance(ref, str) and ref in valid_evidence_ids for ref in ev_refs
        ):
            covered_decisions += 1
        else:
            uncovered_decisions += 1

    warnings: list[str] = []
    if expired_count > 0:
        warnings.append(f"{expired_count} expired evidence item(s) detected.")
    if uncovered_decisions > 0:
        warnings.append(f"{uncovered_decisions} decision(s) have no linked evidence.")
    if not evidence_items:
        warnings.append("No evidence items found in bundle.")

    return ControlRoomView(
        view_id=_view_id("evidence_map", scope, generated_at),
        view_type="evidence_map",
        view_label="Evidence Map",
        target_scope=scope,
        data_sources=(
            DataSourceRef("evidence_ref", "SELECT * FROM evidence_ref LIMIT 200"),
            DataSourceRef("claim", "SELECT * FROM claim LIMIT 200"),
            DataSourceRef("audit_observation", "SELECT * FROM audit_observation LIMIT 100"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM evidence_ref LIMIT 200",
            "SELECT * FROM claim LIMIT 200",
        ),
        display_entities=("evidence_ref", "claim", "audit_observation"),
        display_edges=("evidence_link", "claim_supports"),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "evidence_by_strength": evidence_by_strength,
            "expired_count": expired_count,
            "covered_decisions": covered_decisions,
            "uncovered_decisions": uncovered_decisions,
            "total_evidence": len(evidence_items),
        },
    )


def _build_risk_surface_report(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    scope_drift_findings = _as_list(bundle.get("scope_drift_findings"))
    contradiction_findings = _as_list(bundle.get("contradiction_findings"))
    quality_scores = _as_list(bundle.get("quality_scores"))

    blocking_drift = [
        f for f in scope_drift_findings
        if isinstance(f, Mapping) and _as_str(f.get("severity") or "") == "blocking"
        and _as_str(f.get("status") or "") not in ("resolved", "accepted_risk", "false_positive")
    ]
    blocking_contradictions = [
        f for f in contradiction_findings
        if isinstance(f, Mapping) and _as_str(f.get("severity") or "") == "blocking"
        and _as_str(f.get("status") or "") not in ("resolved", "false_positive", "superseded")
    ]

    weak_quality_dimensions: list[str] = []
    for qs in quality_scores:
        if not isinstance(qs, Mapping):
            continue
        for dim in qs.get("blocking_dimensions", []) or []:
            weak_quality_dimensions.append(f"{_as_str(dim)}:blocking")
        for dim in qs.get("watch_dimensions", []) or []:
            weak_quality_dimensions.append(f"{_as_str(dim)}:watch")

    warnings: list[str] = []
    if blocking_drift:
        warnings.append(f"{len(blocking_drift)} blocking scope drift finding(s).")
    if blocking_contradictions:
        warnings.append(f"{len(blocking_contradictions)} blocking contradiction(s).")
    if weak_quality_dimensions:
        warnings.append(f"Weak/blocking quality dimensions: {', '.join(weak_quality_dimensions[:5])}.")

    return ControlRoomView(
        view_id=_view_id("risk_surface_report", scope, generated_at),
        view_type="risk_surface_report",
        view_label="Risk Surface Report",
        target_scope=scope,
        data_sources=(
            DataSourceRef("scope_drift_event", "SELECT * FROM scope_drift_event WHERE status NOT IN ['resolved','accepted_risk']"),
            DataSourceRef("contradiction", "SELECT * FROM contradiction WHERE status NOT IN ['resolved','false_positive']"),
            DataSourceRef("knowledge_quality_score", "SELECT * FROM knowledge_quality_score ORDER BY computed_at DESC LIMIT 10"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM scope_drift_event WHERE status NOT IN ['resolved','accepted_risk']",
            "SELECT * FROM contradiction WHERE status NOT IN ['resolved','false_positive']",
        ),
        display_entities=("scope_drift_event", "contradiction", "knowledge_quality_score"),
        display_edges=("triggers", "contradicts"),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "blocking_drift_count": len(blocking_drift),
            "blocking_contradiction_count": len(blocking_contradictions),
            "weak_quality_dimensions": weak_quality_dimensions,
            "total_scope_drift": len(scope_drift_findings),
            "total_contradictions": len(contradiction_findings),
        },
    )


def _build_stale_knowledge_view(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    stale_findings = _as_list(bundle.get("stale_findings"))
    memory_items = _as_list(bundle.get("memory_items"))

    actionable_stale = [
        f for f in stale_findings
        if isinstance(f, Mapping)
        and _as_str(f.get("status") or "") not in ("refreshed", "accepted_risk", "false_positive")
    ]
    stale_by_type: dict[str, int] = {}
    for f in actionable_stale:
        if not isinstance(f, Mapping):
            continue
        st = _as_str(f.get("stale_type") or "unknown")
        stale_by_type[st] = stale_by_type.get(st, 0) + 1

    expired_memory = [
        m for m in memory_items
        if isinstance(m, Mapping) and m.get("ttl_expired")
    ]

    warnings: list[str] = []
    if actionable_stale:
        warnings.append(f"{len(actionable_stale)} actionable stale finding(s) detected.")
    if expired_memory:
        warnings.append(f"{len(expired_memory)} memory item(s) with expired TTL.")

    return ControlRoomView(
        view_id=_view_id("stale_knowledge_view", scope, generated_at),
        view_type="stale_knowledge_view",
        view_label="Stale Knowledge View",
        target_scope=scope,
        data_sources=(
            DataSourceRef("stale_context", "SELECT * FROM stale_context WHERE status NOT IN ['refreshed','accepted_risk']"),
            DataSourceRef("agent_memory", "SELECT * FROM agent_memory LIMIT 200"),
            DataSourceRef("doc_chunk", "SELECT * FROM doc_chunk LIMIT 100"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM stale_context WHERE status NOT IN ['refreshed','accepted_risk']",
        ),
        display_entities=("stale_context", "agent_memory", "doc_chunk"),
        display_edges=("refresh_recommended", "supersedes"),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "actionable_stale_count": len(actionable_stale),
            "stale_by_type": stale_by_type,
            "expired_memory_count": len(expired_memory),
            "total_stale": len(stale_findings),
        },
    )


def _build_scope_drift_events(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    findings = _as_list(bundle.get("scope_drift_findings"))
    by_severity: dict[str, list[dict[str, Any]]] = {"blocking": [], "watch": [], "info": []}

    for f in findings:
        if not isinstance(f, Mapping):
            continue
        sev = _as_str(f.get("severity") or "info")
        if sev not in by_severity:
            sev = "info"
        by_severity[sev].append(
            {
                "finding_id": _as_str(f.get("finding_id") or f.get("drift_id") or ""),
                "drift_type": _as_str(f.get("drift_type") or ""),
                "severity": sev,
                "status": _as_str(f.get("status") or "open"),
                "required_action": _as_str(f.get("required_action") or ""),
                "human_go_required": bool(f.get("human_go_required")),
            }
        )

    warnings: list[str] = []
    if by_severity["blocking"]:
        warnings.append(f"{len(by_severity['blocking'])} blocking scope drift finding(s).")

    return ControlRoomView(
        view_id=_view_id("scope_drift_events", scope, generated_at),
        view_type="scope_drift_events",
        view_label="Scope Drift Events",
        target_scope=scope,
        data_sources=(
            DataSourceRef("scope_drift_event", "SELECT * FROM scope_drift_event ORDER BY detected_at DESC"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM scope_drift_event ORDER BY detected_at DESC",
        ),
        display_entities=("scope_drift_event",),
        display_edges=(),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "blocking": by_severity["blocking"],
            "watch": by_severity["watch"],
            "info": by_severity["info"],
            "total": len(findings),
        },
    )


def _build_agent_memory_view(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    memory_items = _as_list(bundle.get("memory_items"))
    by_trust: dict[str, int] = {"strong": 0, "moderate": 0, "weak": 0, "unknown": 0}
    expired_count = 0

    for m in memory_items:
        if not isinstance(m, Mapping):
            continue
        trust = _as_str(m.get("trust_level") or "unknown")
        if trust not in by_trust:
            trust = "unknown"
        by_trust[trust] += 1
        if m.get("ttl_expired"):
            expired_count += 1

    warnings: list[str] = []
    if expired_count > 0:
        warnings.append(f"{expired_count} memory item(s) with expired TTL.")
    if by_trust["weak"] > 0:
        warnings.append(f"{by_trust['weak']} low-trust memory item(s).")

    return ControlRoomView(
        view_id=_view_id("agent_memory_view", scope, generated_at),
        view_type="agent_memory_view",
        view_label="Agent Memory View",
        target_scope=scope,
        data_sources=(
            DataSourceRef("agent_memory", "SELECT * FROM agent_memory LIMIT 200"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM agent_memory LIMIT 200",
        ),
        display_entities=("agent_memory",),
        display_edges=("memory_supersedes",),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "by_trust": by_trust,
            "expired_count": expired_count,
            "total_memory_items": len(memory_items),
        },
    )


def _build_quality_score_dashboard(
    bundle: Mapping[str, Any],
    scope: str,
    generated_at: str,
    filters: dict[str, Any],
) -> ControlRoomView:
    quality_scores = _as_list(bundle.get("quality_scores"))

    dashboard_entries: list[dict[str, Any]] = []
    worst_grade = "good"
    _grade_order = {"blocking": 0, "watch": 1, "weak": 2, "good": 3}

    for qs in quality_scores:
        if not isinstance(qs, Mapping):
            continue
        grade = _as_str(qs.get("overall_grade") or "unknown")
        if grade in _grade_order and _grade_order.get(grade, 3) < _grade_order.get(worst_grade, 3):
            worst_grade = grade
        dashboard_entries.append(
            {
                "scope_id": _as_str(qs.get("scope_id") or ""),
                "overall_grade": grade,
                "overall_score": qs.get("overall_score"),
                "blocking_dimensions": _as_list(qs.get("blocking_dimensions")),
                "watch_dimensions": _as_list(qs.get("watch_dimensions")),
                "scored_at": _as_str(qs.get("scored_at") or ""),
            }
        )

    warnings: list[str] = []
    if not dashboard_entries:
        warnings.append("No quality scores found in bundle.")
    elif worst_grade == "blocking":
        warnings.append("One or more quality scores at BLOCKING grade. Human-GO required before acting.")
    elif worst_grade == "watch":
        warnings.append("One or more quality scores at WATCH grade. Review before acting.")

    return ControlRoomView(
        view_id=_view_id("quality_score_dashboard", scope, generated_at),
        view_type="quality_score_dashboard",
        view_label="Quality Score Dashboard",
        target_scope=scope,
        data_sources=(
            DataSourceRef("knowledge_quality_score", "SELECT * FROM knowledge_quality_score ORDER BY computed_at DESC LIMIT 10"),
        ),
        filters=filters,
        required_queries=(
            "SELECT * FROM knowledge_quality_score ORDER BY computed_at DESC LIMIT 10",
        ),
        display_entities=("knowledge_quality_score",),
        display_edges=(),
        warnings=tuple(warnings),
        generated_at=generated_at,
        generated_by=GENERATED_BY,
        export_formats=EXPORT_FORMATS,
        guardrails=GUARDRAILS,
        payload={
            "entries": dashboard_entries,
            "worst_grade": worst_grade,
            "entry_count": len(dashboard_entries),
        },
    )


_VIEW_BUILDERS: dict[str, Any] = {
    "knowledge_graph_view": _build_knowledge_graph_view,
    "architecture_map": _build_architecture_map,
    "decision_chain_view": _build_decision_chain_view,
    "evidence_map": _build_evidence_map,
    "risk_surface_report": _build_risk_surface_report,
    "stale_knowledge_view": _build_stale_knowledge_view,
    "scope_drift_events": _build_scope_drift_events,
    "agent_memory_view": _build_agent_memory_view,
    "quality_score_dashboard": _build_quality_score_dashboard,
}


# ── Public API ────────────────────────────────────────────────────────────────


def build_control_room_view_v1(
    view_type: str,
    bundle: Mapping[str, Any],
    filters: Mapping[str, Any] | None = None,
    as_of: str | None = None,
) -> ControlRoomView:
    """Build a single visual_control_view-conformant view object.

    Args:
        view_type:  One of VIEW_TYPES.
        bundle:     In-memory context bundle (same shape as quality scoring).
        filters:    Optional filter map (key → value) passed into the view.
        as_of:      Optional ISO-8601 timestamp for deterministic test output.

    Returns:
        A ``ControlRoomView`` (frozen dataclass).  Call ``.to_dict()`` for JSON.

    Raises:
        ControlRoomError: Invalid input.
    """
    if view_type not in VIEW_TYPES:
        raise ControlRoomError(
            f"Unknown view_type '{view_type}'. Valid: {sorted(VIEW_TYPES)}"
        )
    _validate_bundle(bundle)

    generated_at = as_of or cdb_utcnow().isoformat()
    scope = _safe_scope(bundle)
    resolved_filters = dict(filters) if filters else {}

    builder = _VIEW_BUILDERS[view_type]
    return builder(bundle, scope, generated_at, resolved_filters)


def build_all_views_v1(
    bundle: Mapping[str, Any],
    filters: Mapping[str, Any] | None = None,
    as_of: str | None = None,
) -> tuple[ControlRoomView, ...]:
    """Build all 9 view types for the given bundle.

    Builds each view independently.  A failure in one view raises
    ``ControlRoomError`` immediately; remaining views are not built.

    Args:
        bundle:  In-memory context bundle.
        filters: Optional filter map applied to all views.
        as_of:   Optional ISO-8601 timestamp for deterministic test output.

    Returns:
        Tuple of 9 ``ControlRoomView`` instances, one per view type.

    Raises:
        ControlRoomError: Invalid input or builder error.
    """
    _validate_bundle(bundle)
    generated_at = as_of or cdb_utcnow().isoformat()
    resolved_filters = dict(filters) if filters else {}
    scope = _safe_scope(bundle)

    results: list[ControlRoomView] = []
    for vt, builder in _VIEW_BUILDERS.items():
        results.append(builder(bundle, scope, generated_at, resolved_filters))
    return tuple(results)
