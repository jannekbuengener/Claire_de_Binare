"""Knowledge Refresh Loop Report v1 — read-only closure orchestrator.

Issues:
    #2717 — [SURREALDB][CONTEXT][REFRESH-LOOP] Add read-only Knowledge Refresh Loop report
    Parent Epic: #1976

Scope:
    Composes stale scan, refresh plan, quality scoring, architect signals, and
    optional Agent OS readiness into a single deterministic JSON/Markdown report.
    Pure in-memory. No DB. No SurrealDB SDK. No MCP. No network. No writes.

Guardrails:
    - Read-only first; write_authorized is always False on every item.
    - Canon-protected sources are never classified as archive-only/delete-only.
    - Issue proposals are text blocks only — no GitHub API calls.
    - LR status remains NO-GO for live trading.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from core.replay.canonical_json import canonical_json_dumps
from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.agent_os_readiness import (
    AgentOsReadinessResult,
    evaluate_agent_os_readiness_v1,
)
from tools.surrealdb.architect_signals import (
    ArchitectSignal,
    ArchitectSignalResult,
    scan_architect_signals_v1,
)
from tools.surrealdb.quality_scoring import QualityScoreResult, score_knowledge_quality_v1
from tools.surrealdb.stale_knowledge_scan import (
    GUARDRAILS as STALE_GUARDRAILS,
    StaleFinding,
    StaleKnowledgeScanResult,
    scan_stale_knowledge_v1,
)
from tools.surrealdb.stale_refresh_plan import (
    RefreshPlanItem,
    RefreshPlanResult,
    generate_refresh_plan_v1,
)

SCHEMA_VERSION = "knowledge-refresh-report/v1"
TOOL_NAME = "knowledge_refresh_report"
GENERATED_BY = "knowledge-refresh-report/v1"

CLASSIFICATIONS: frozenset[str] = frozenset(
    {
        "canon_protected",
        "refresh_required",
        "archive_candidate",
        "needs_issue_proposal",
        "stale_but_accepted",
        "orphan_candidate",
        "no_action",
    }
)

CANON_PROTECTED_PREFIXES: tuple[str, ...] = (
    "AGENTS.md",
    "agents/AGENTS.md",
    "agents/roles/",
    "knowledge/governance/",
    "docs/live-readiness/",
    "docs/runbooks/CONTROL_REGISTER.md",
    "CURRENT_STATUS.md",
    "CLAUDE.md",
)

GUARDRAILS: tuple[str, ...] = (
    "Knowledge Refresh Report is signal, not authorization.",
    "No automatic delete.",
    "No automatic archive.",
    "No automatic issue creation.",
    "No DB write. No memory write. No GitHub write.",
    "No Live-Readiness-Go.",
    "No Echtgeld-Go.",
    "Git/Repo remains source of truth.",
)

_ACCEPTED_STALE_STATUSES = frozenset({"accepted_stale", "false_positive"})


class KnowledgeRefreshReportError(ValueError):
    """Raised when report inputs are invalid or unsafe."""


@dataclass(frozen=True)
class RefreshReportItem:
    """A single classified refresh candidate in the knowledge refresh report."""

    item_id: str
    target_ref: str
    classification: str
    reason: str
    write_authorized: bool
    canon_protected: bool
    stale_type: str | None = None
    severity: str | None = None
    priority: str | None = None
    plan_id: str | None = None
    recommended_action: str | None = None
    architect_signal_ids: tuple[str, ...] = ()
    issue_proposal: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "item_id": self.item_id,
            "target_ref": self.target_ref,
            "classification": self.classification,
            "reason": self.reason,
            "write_authorized": self.write_authorized,
            "canon_protected": self.canon_protected,
        }
        if self.stale_type is not None:
            payload["stale_type"] = self.stale_type
        if self.severity is not None:
            payload["severity"] = self.severity
        if self.priority is not None:
            payload["priority"] = self.priority
        if self.plan_id is not None:
            payload["plan_id"] = self.plan_id
        if self.recommended_action is not None:
            payload["recommended_action"] = self.recommended_action
        if self.architect_signal_ids:
            payload["architect_signal_ids"] = list(self.architect_signal_ids)
        if self.issue_proposal is not None:
            payload["issue_proposal"] = self.issue_proposal
        return payload


@dataclass(frozen=True)
class KnowledgeRefreshReportResult:
    """Full knowledge refresh loop report."""

    report_id: str
    scope_id: str
    as_of: str
    status: str
    classification_summary: dict[str, int]
    items: tuple[RefreshReportItem, ...]
    stale_scan: dict[str, Any]
    refresh_plan: dict[str, Any]
    quality: dict[str, Any]
    architect_signals: dict[str, Any]
    agent_os_readiness: dict[str, Any] | None
    guardrails: tuple[str, ...]
    errors: tuple[str, ...]
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool": TOOL_NAME,
            "generated_by": GENERATED_BY,
            "report_id": self.report_id,
            "scope_id": self.scope_id,
            "as_of": self.as_of,
            "status": self.status,
            "classification_summary": dict(self.classification_summary),
            "items": [item.to_dict() for item in self.items],
            "stale_scan": self.stale_scan,
            "refresh_plan": self.refresh_plan,
            "quality": self.quality,
            "architect_signals": self.architect_signals,
            "agent_os_readiness": self.agent_os_readiness,
            "guardrails": list(self.guardrails),
            "errors": list(self.errors),
        }

    def to_json(self) -> str:
        return canonical_json_dumps(self.to_dict())

    def to_markdown(self) -> str:
        lines: list[str] = [
            "# Knowledge Refresh Loop Report",
            "",
            f"**Schema:** `{self.schema_version}`  ",
            f"**Report ID:** `{self.report_id}`  ",
            f"**Scope:** `{self.scope_id}`  ",
            f"**As of:** `{self.as_of}`  ",
            f"**Status:** `{self.status}`  ",
            "",
            "## Classification Summary",
            "",
        ]
        for cls in sorted(CLASSIFICATIONS):
            count = self.classification_summary.get(cls, 0)
            if count:
                lines.append(f"- `{cls}`: {count}")
        if not any(self.classification_summary.values()):
            lines.append("_No classified items._")
        lines.append("")

        if self.agent_os_readiness:
            level = self.agent_os_readiness.get("readiness_level", "unknown")
            lines += [
                "## Agent OS Readiness (summary signal)",
                "",
                f"- **Level:** `{level}`",
                f"- **Confidence:** {self.agent_os_readiness.get('confidence', 0):.2f}",
                "",
            ]

        quality_grade = self.quality.get("overall_grade")
        if quality_grade:
            lines += [
                "## Quality Summary",
                "",
                f"- **Overall grade:** `{quality_grade}`",
                f"- **Overall score:** {self.quality.get('overall_score', 0):.2f}",
                "",
            ]

        lines += ["## Items", ""]
        if not self.items:
            lines.append("_No refresh candidates._")
        else:
            for item in self.items:
                lines.append(f"### `{item.target_ref}` — `{item.classification}`")
                lines.append("")
                lines.append(f"- **Reason:** {item.reason}")
                if item.stale_type:
                    lines.append(f"- **Stale type:** `{item.stale_type}`")
                if item.priority:
                    lines.append(f"- **Priority:** `{item.priority}`")
                if item.recommended_action:
                    lines.append(f"- **Recommended action:** `{item.recommended_action}`")
                lines.append(f"- **Canon protected:** `{item.canon_protected}`")
                lines.append(f"- **Write authorized:** `{item.write_authorized}`")
                if item.issue_proposal:
                    lines += ["", "**Issue proposal (text only — not submitted):**", "", item.issue_proposal, ""]
                lines.append("")

        lines += ["## Guardrails", ""]
        lines.extend(f"- {g}" for g in self.guardrails)
        lines.append("")
        if self.errors:
            lines += ["## Errors", ""]
            lines.extend(f"- {err}" for err in self.errors)
            lines.append("")
        return "\n".join(lines)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_canon_protected(path: str) -> bool:
    normalized = normalize_path(path)
    for prefix in CANON_PROTECTED_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix):
            return True
    return False


def _item_id(target_ref: str, classification: str, stale_type: str | None) -> str:
    raw = f"{target_ref}|{classification}|{stale_type or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _report_id(scope_id: str, as_of: str) -> str:
    raw = f"{scope_id}|{as_of}|{SCHEMA_VERSION}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else str(value) if value is not None else ""


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _validate_bundle(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise KnowledgeRefreshReportError("bundle must be a mapping")
    return dict(bundle)


def _resolve_as_of(bundle: Mapping[str, Any], as_of: str | None) -> str:
    if isinstance(as_of, str) and as_of.strip():
        return as_of.strip()
    meta = bundle.get("meta")
    if isinstance(meta, Mapping):
        meta_as_of = meta.get("as_of")
        if isinstance(meta_as_of, str) and meta_as_of.strip():
            return meta_as_of.strip()
    return cdb_utcnow().isoformat()


def _resolve_scope_id(bundle: Mapping[str, Any]) -> str:
    meta = bundle.get("meta")
    if isinstance(meta, Mapping):
        scope_id = _as_str(meta.get("scope_id", "")).strip()
        if scope_id:
            return scope_id
    return "knowledge-refresh-default"


def _finding_to_stale_dict(finding: StaleFinding) -> dict[str, Any]:
    return {
        "finding_id": finding.stale_id,
        "stale_id": finding.stale_id,
        "stale_type": finding.stale_type,
        "target_ref": finding.target_ref,
        "severity": finding.severity,
        "status": finding.status,
        "blocking": finding.blocking,
        "confidence": finding.confidence,
    }


def _enrich_bundle(
    bundle: Mapping[str, Any],
    scan_result: StaleKnowledgeScanResult,
) -> dict[str, Any]:
    enriched: dict[str, Any] = dict(bundle)
    meta = dict(enriched.get("meta") or {})
    if not _as_str(meta.get("scope_id", "")).strip():
        meta["scope_id"] = _resolve_scope_id(bundle)
    if not _as_str(meta.get("level", "")).strip():
        meta["level"] = "domain"
    enriched["meta"] = meta

    if not enriched.get("evidence_items") and enriched.get("evidence_records"):
        evidence_items: list[dict[str, Any]] = []
        for record in _as_list(enriched.get("evidence_records")):
            if isinstance(record, Mapping):
                evidence_items.append(
                    {
                        "evidence_id": record.get("evidence_id", record.get("id", "")),
                        "strength": record.get("strength", "medium"),
                        "expires_at": record.get("expires_at"),
                        "description": record.get("topic", record.get("description", "")),
                    }
                )
        enriched["evidence_items"] = evidence_items

    enriched["stale_findings"] = [_finding_to_stale_dict(f) for f in scan_result.findings]
    return enriched


def _plan_by_stale_id(plan: RefreshPlanResult) -> dict[str, RefreshPlanItem]:
    return {item.stale_id: item for item in plan.plan_items}


def _signals_by_path(signals: ArchitectSignalResult) -> dict[str, list[ArchitectSignal]]:
    by_path: dict[str, list[ArchitectSignal]] = {}
    for signal in signals.signals:
        for path in signal.affected_paths:
            normalized = normalize_path(path)
            by_path.setdefault(normalized, []).append(signal)
    return by_path


def _issue_proposal_text(
    target_ref: str,
    classification: str,
    stale_type: str | None,
    priority: str | None,
    reason: str,
) -> str:
    title_kind = stale_type or classification
    return (
        f"Proposed issue (NOT auto-created):\n"
        f"Title: [SURREALDB][CONTEXT][REFRESH] Review {title_kind} for `{target_ref}`\n"
        f"Priority hint: {priority or 'review'}\n"
        f"Reason: {reason}\n"
        f"Parent: #1976 / #2717"
    )


def classify_finding(
    finding: StaleFinding,
    plan_item: RefreshPlanItem | None,
    path_signals: list[ArchitectSignal],
) -> str:
    target = normalize_path(finding.target_ref)
    canon = is_canon_protected(target)

    if finding.status in _ACCEPTED_STALE_STATUSES:
        return "stale_but_accepted"

    blocking_architect = any(s.severity == "blocking" for s in path_signals)
    priority = plan_item.priority if plan_item else None

    if finding.stale_type == "source_deleted":
        if canon:
            return "refresh_required"
        if finding.blocking or finding.severity == "blocking" or priority == "P0":
            return "needs_issue_proposal"
        return "archive_candidate"

    if blocking_architect or priority == "P0" or (
        plan_item and plan_item.requires_human_review and finding.blocking
    ):
        return "needs_issue_proposal"

    if finding.severity in ("warning", "blocking") or finding.blocking:
        return "refresh_required"

    return "no_action"


def _classify_orphan(path: str) -> str:
    if is_canon_protected(path):
        return "canon_protected"
    return "orphan_candidate"


def _referenced_paths(bundle: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for decision in _as_list(bundle.get("decisions")):
        if isinstance(decision, Mapping):
            for key in ("path", "target_ref", "source_path"):
                val = _as_str(decision.get(key, "")).strip()
                if val:
                    refs.add(normalize_path(val))
    for edge in _as_list(bundle.get("dependency_edges")):
        if isinstance(edge, Mapping):
            for key in ("source", "target", "from_ref", "to_ref"):
                val = _as_str(edge.get(key, "")).strip()
                if val:
                    refs.add(normalize_path(val))
    return refs


def _detect_orphan_sources(
    bundle: Mapping[str, Any],
    covered_targets: set[str],
) -> list[RefreshReportItem]:
    items: list[RefreshReportItem] = []
    referenced = _referenced_paths(bundle)
    for source in _as_list(bundle.get("sources")):
        if not isinstance(source, Mapping):
            continue
        if source.get("exists") is False:
            continue
        path = _as_str(source.get("path", "")).strip()
        if not path:
            continue
        normalized = normalize_path(path)
        if normalized in covered_targets:
            continue
        owner = _as_str(source.get("owner", "")).strip()
        has_docs = bool(source.get("has_documentation"))
        has_tests = bool(source.get("has_tests"))
        source_id = _as_str(source.get("source_id", "")).strip()
        if (
            owner
            or has_docs
            or has_tests
            or normalized in referenced
            or source_id in covered_targets
        ):
            if is_canon_protected(normalized) and normalized not in covered_targets:
                classification = "canon_protected"
                reason = "Canon-protected source; no open stale findings."
            else:
                continue
        else:
            classification = _classify_orphan(normalized)
            reason = "Source has no owner, coverage flags, or observed references."
        items.append(
            RefreshReportItem(
                item_id=_item_id(normalized, classification, None),
                target_ref=normalized,
                classification=classification,
                reason=reason,
                write_authorized=False,
                canon_protected=is_canon_protected(normalized),
            )
        )
    return items


def _build_source_index(
    bundle: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    by_path: dict[str, Mapping[str, Any]] = {}
    for source in _as_list(bundle.get("sources")):
        if not isinstance(source, Mapping):
            continue
        source_id = _as_str(source.get("source_id", "")).strip()
        path = _as_str(source.get("path", "")).strip()
        if source_id:
            by_id[source_id] = source
        if path:
            by_path[normalize_path(path)] = source
    return by_id, by_path


def _resolve_item_ref(
    finding: StaleFinding,
    sources_by_id: dict[str, Mapping[str, Any]],
) -> str:
    if finding.stale_type in {"source_hash_changed", "source_deleted"}:
        source = sources_by_id.get(finding.target_ref)
        if source is not None:
            path = _as_str(source.get("path", "")).strip()
            if path:
                return normalize_path(path)
    return normalize_path(finding.target_ref)


def _build_items_from_findings(
    bundle: Mapping[str, Any],
    scan_result: StaleKnowledgeScanResult,
    plan: RefreshPlanResult,
    signals: ArchitectSignalResult,
) -> list[RefreshReportItem]:
    plan_map = _plan_by_stale_id(plan)
    signal_map = _signals_by_path(signals)
    sources_by_id, _ = _build_source_index(bundle)
    items: list[RefreshReportItem] = []

    for finding in scan_result.findings:
        target = _resolve_item_ref(finding, sources_by_id)
        plan_item = plan_map.get(finding.stale_id)
        path_signals = signal_map.get(target, [])
        classification = classify_finding(finding, plan_item, path_signals)
        if classification not in CLASSIFICATIONS:
            classification = "no_action"

        issue_proposal: str | None = None
        if classification == "needs_issue_proposal":
            issue_proposal = _issue_proposal_text(
                target,
                classification,
                finding.stale_type,
                plan_item.priority if plan_item else None,
                finding.reason,
            )

        items.append(
            RefreshReportItem(
                item_id=_item_id(target, classification, finding.stale_type),
                target_ref=target,
                classification=classification,
                reason=finding.reason,
                write_authorized=False,
                canon_protected=is_canon_protected(target),
                stale_type=finding.stale_type,
                severity=finding.severity,
                priority=plan_item.priority if plan_item else None,
                plan_id=plan_item.plan_id if plan_item else None,
                recommended_action=plan_item.recommended_action if plan_item else None,
                architect_signal_ids=tuple(s.signal_id for s in path_signals),
                issue_proposal=issue_proposal,
            )
        )
    return items


def _classification_summary(items: tuple[RefreshReportItem, ...]) -> dict[str, int]:
    summary = {cls: 0 for cls in CLASSIFICATIONS}
    for item in items:
        if item.classification in summary:
            summary[item.classification] += 1
    return summary


def _quality_summary(result: QualityScoreResult) -> dict[str, Any]:
    data = result.to_dict()
    return {
        "overall_score": data.get("overall_score"),
        "overall_grade": data.get("overall_grade"),
        "scope_id": data.get("scope_id"),
    }


def _architect_summary(result: ArchitectSignalResult) -> dict[str, Any]:
    return {
        "total_signals": result.total_signals,
        "blocking_count": result.blocking_count,
        "watch_count": result.watch_count,
    }


def _readiness_summary(result: AgentOsReadinessResult) -> dict[str, Any]:
    return {
        "readiness_level": result.readiness_level,
        "confidence": result.confidence,
        "blocking_findings_count": len(result.blocking_findings),
        "weak_findings_count": len(result.weak_findings),
    }


def generate_knowledge_refresh_report_v1(
    bundle: Mapping[str, Any],
    as_of: str | None = None,
    *,
    include_readiness: bool = True,
) -> KnowledgeRefreshReportResult:
    """Generate a deterministic knowledge refresh loop report from a bundle.

    Read-only. No DB/network/file writes. No GitHub calls.
    """
    validated = _validate_bundle(bundle)
    resolved_as_of = _resolve_as_of(validated, as_of)
    scope_id = _resolve_scope_id(validated)
    errors: list[str] = []

    scan_result = scan_stale_knowledge_v1(validated, as_of=resolved_as_of)
    plan_result = generate_refresh_plan_v1(scan_result, as_of=resolved_as_of)
    enriched = _enrich_bundle(validated, scan_result)

    quality_result: QualityScoreResult | None = None
    architect_result: ArchitectSignalResult | None = None
    readiness_result: AgentOsReadinessResult | None = None

    try:
        quality_result = score_knowledge_quality_v1(enriched, as_of=resolved_as_of)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"quality_scoring: {type(exc).__name__}: {exc}")

    try:
        architect_result = scan_architect_signals_v1(enriched, as_of=resolved_as_of)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"architect_signals: {type(exc).__name__}: {exc}")

    if include_readiness:
        try:
            readiness_result = evaluate_agent_os_readiness_v1(enriched, as_of=resolved_as_of)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"agent_os_readiness: {type(exc).__name__}: {exc}")

    items: list[RefreshReportItem] = []
    if architect_result is not None:
        items.extend(
            _build_items_from_findings(
                validated, scan_result, plan_result, architect_result
            )
        )
    else:
        empty_signals = ArchitectSignalResult(
            scope_id=scope_id,
            total_signals=0,
            blocking_count=0,
            watch_count=0,
            signals=(),
            scanned_at=resolved_as_of,
        )
        items.extend(
            _build_items_from_findings(
                validated, scan_result, plan_result, empty_signals
            )
        )

    covered = {item.target_ref for item in items}
    items.extend(_detect_orphan_sources(validated, covered))

    items.sort(key=lambda i: (i.classification, i.target_ref, i.item_id))
    item_tuple = tuple(items)
    status = "error" if errors and not item_tuple else "ok"
    if errors and item_tuple:
        status = "ok"

    return KnowledgeRefreshReportResult(
        report_id=_report_id(scope_id, resolved_as_of),
        scope_id=scope_id,
        as_of=resolved_as_of,
        status=status,
        classification_summary=_classification_summary(item_tuple),
        items=item_tuple,
        stale_scan={
            "total_count": scan_result.total_count,
            "blocking_count": scan_result.blocking_count,
            "status": scan_result.status,
            "guardrails": list(STALE_GUARDRAILS),
        },
        refresh_plan={
            "plan_item_count": plan_result.plan_item_count,
            "blocking_findings": plan_result.blocking_findings,
            "status": plan_result.status,
            "write_authorized": False,
        },
        quality=_quality_summary(quality_result) if quality_result else {},
        architect_signals=_architect_summary(architect_result) if architect_result else {},
        agent_os_readiness=_readiness_summary(readiness_result) if readiness_result else None,
        guardrails=GUARDRAILS,
        errors=tuple(errors),
    )
