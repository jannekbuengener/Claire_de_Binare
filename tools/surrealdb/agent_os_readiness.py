"""Agent OS Readiness Evaluator v1 — side-effect-free domain component.

Issues:
    #2191 — [SURREALDB][CONTEXT][AGENT-OS-READINESS] Implement Agent OS readiness evaluator
    #2193 — [SURREALDB][CONTEXT][AGENT-OS-REPORT] Generate Agent OS readiness report
    Parent: #2188 (Wave-20 anchor)
    Epic: #1976

Scope:
    Pure, deterministic Agent OS Readiness Evaluator v1.
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No auto-fix. No live-go. No trading console. No runtime control.

    Evaluates the health/readiness of the Agent OS context intelligence system
    itself by aggregating signals from all existing quality, trust, scope-drift,
    stale, contradiction, and architect-signal modules.

    This is orthogonal to the Wave-13 ``context.readiness`` tool, which
    evaluates whether an *agent task* is ready to proceed.  This evaluator
    asks: "Is the *Agent OS context intelligence system* healthy and ready?"

    Readiness levels (fail-closed):
        blocked     — one or more blocking findings present; action required
        weak        — no blockers, but multiple watch-level or missing inputs
        acceptable  — no blockers, few weak findings; proceed with caution
        strong      — no blockers, no weak findings; system healthy

    Every output carries embedded guardrails (always non-empty).
    Outputs are plain-dict-serialisable via .to_dict().
    The evaluator never writes anything.

Guardrails:
    - Agent OS Readiness is a signal, not an authorization.
    - No trading console. No runtime control. No Live-Freigabe.
    - No Live-Readiness-Go. No Echtgeld-Go.
    - read-only: no mutations anywhere in the readiness evaluation path.
    - Human-GO required for any action after blocking findings.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "agent-os-readiness/v1"
EVALUATED_BY = "agent_os_readiness/v1"

READINESS_LEVELS: frozenset[str] = frozenset(
    {"blocked", "weak", "acceptable", "strong"}
)

GUARDRAILS: tuple[str, ...] = (
    "Agent OS Readiness is a signal, not an authorization.",
    "No trading console. No runtime control. No Live-Freigabe.",
    "No Live-Readiness-Go. No Echtgeld-Go.",
    "read-only: no mutations anywhere in the readiness evaluation path.",
    "Human-GO required for any action after blocking findings.",
)

# Minimum recommended reads for any agent operating on this system.
RECOMMENDED_NEXT_READS: tuple[str, ...] = (
    "AGENTS.md",
    "agents/AGENTS.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    "docs/surrealdb/context-wave20-agent-os-readiness-runbook.md",
)


class AgentOsReadinessError(ValueError):
    """Raised when evaluator inputs are invalid or unsafe."""


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentOsReadinessResult:
    """Full Agent OS readiness evaluation result."""

    readiness_id: str               # SHA-256(scope_id|generated_at)[:16]
    target_scope: str
    readiness_level: str            # blocked / weak / acceptable / strong
    blocking_findings: tuple[str, ...]
    weak_findings: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    recommended_next_reads: tuple[str, ...]
    required_validation: tuple[str, ...]
    guardrails: tuple[str, ...]     # always GUARDRAILS (5 items)
    confidence: float               # 0.0–1.0; capped to 0.3 when blocked
    generated_at: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "readiness_id": self.readiness_id,
            "target_scope": self.target_scope,
            "generated_at": self.generated_at,
            "readiness_level": self.readiness_level,
            "confidence": round(self.confidence, 4),
            "blocking_findings": list(self.blocking_findings),
            "weak_findings": list(self.weak_findings),
            "missing_inputs": list(self.missing_inputs),
            "recommended_next_reads": list(self.recommended_next_reads),
            "required_validation": list(self.required_validation),
            "guardrails": list(self.guardrails),
        }

    def to_report_markdown(self) -> str:
        """Render a human-readable Markdown report of this readiness result.

        Covers #2193 (Generate Agent OS readiness report).
        No IO, no DB, no network.  Pure string rendering.
        """
        lines: list[str] = [
            "# Agent OS Readiness Report",
            "",
            f"**Schema version:** `{self.schema_version}`  ",
            f"**Readiness ID:** `{self.readiness_id}`  ",
            f"**Target scope:** `{self.target_scope}`  ",
            f"**Generated at:** `{self.generated_at}`  ",
            "",
            f"## Readiness Level: `{self.readiness_level.upper()}`",
            "",
            f"**Confidence:** {self.confidence:.2f}",
            "",
        ]

        if self.blocking_findings:
            lines += [
                "## Blocking Findings",
                "",
                *(f"- {f}" for f in self.blocking_findings),
                "",
            ]
        else:
            lines += ["## Blocking Findings", "", "_None._", ""]

        if self.weak_findings:
            lines += [
                "## Weak / Watch Findings",
                "",
                *(f"- {f}" for f in self.weak_findings),
                "",
            ]
        else:
            lines += ["## Weak / Watch Findings", "", "_None._", ""]

        if self.missing_inputs:
            lines += [
                "## Missing Inputs",
                "",
                *(f"- `{m}`" for m in self.missing_inputs),
                "",
            ]

        if self.required_validation:
            lines += [
                "## Required Validation",
                "",
                *(f"- {v}" for v in self.required_validation),
                "",
            ]

        lines += [
            "## Recommended Next Reads",
            "",
            *(f"- `{r}`" for r in self.recommended_next_reads),
            "",
            "## Guardrails",
            "",
            *(f"- {g}" for g in self.guardrails),
            "",
            "---",
            "",
            "_Agent OS Readiness is a signal, not a Live-Readiness-Go._",
            "_LR remains NO-GO. Board stage `trade-capable` is orthogonal._",
        ]

        return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, Mapping):
        # Wrap a lone mapping in a list instead of iterating its keys.
        return [value]
    return list(value)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _readiness_id(scope_id: str, generated_at: str) -> str:
    """Deterministic SHA-256-based readiness ID."""
    raw = f"{scope_id}|{generated_at}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_open(item: Mapping[str, Any]) -> bool:
    """Return True if a finding is open (not resolved / accepted / fp)."""
    status = _as_str(item.get("status", "")).lower()
    return status not in {"resolved", "accepted_risk", "accepted_stale", "false_positive"}


def _is_blocking_severity(item: Mapping[str, Any]) -> bool:
    """Return True if finding severity is 'blocking'."""
    severity = _as_str(item.get("severity", "")).lower()
    return severity == "blocking"


def _validate_bundle(bundle: Any) -> Mapping[str, Any]:
    """Validate bundle structure; raise AgentOsReadinessError on failure."""
    if bundle is None or not isinstance(bundle, Mapping):
        raise AgentOsReadinessError(
            "bundle must be a non-None mapping "
            "(got %s)" % type(bundle).__name__
        )
    meta = bundle.get("meta")
    if not isinstance(meta, Mapping):
        raise AgentOsReadinessError(
            "bundle.meta must be a mapping (got %s)" % type(meta).__name__
        )
    return bundle


# ── Evaluation sub-routines ───────────────────────────────────────────────────


def _evaluate_quality(
    bundle: Mapping[str, Any],
    as_of: str | None,
) -> tuple[list[str], list[str]]:
    """Evaluate quality score signals.

    Returns (blocking_findings, weak_findings).
    Calls score_knowledge_quality_v1 internally; errors map to weak findings
    so a malformed quality bundle never silently inflates the readiness level.
    """
    blocking: list[str] = []
    weak: list[str] = []
    try:
        from tools.surrealdb.quality_scoring import (
            GRADE_BLOCKING,
            GRADE_WATCH,
            score_knowledge_quality_v1,
        )

        result = score_knowledge_quality_v1(bundle, as_of=as_of)
        if result.overall_grade == GRADE_BLOCKING:
            blocking.append(
                f"quality grade=blocking "
                f"(score={result.overall_score:.3f}, "
                f"blocking_dimensions={list(result.blocking_dimensions)})"
            )
        elif result.overall_grade == GRADE_WATCH:
            weak.append(
                f"quality grade=watch "
                f"(score={result.overall_score:.3f}, "
                f"watch_dimensions={list(result.watch_dimensions)})"
            )
    except Exception as exc:  # noqa: BLE001
        weak.append(f"quality scoring error: {exc!s}")
    return blocking, weak


def _evaluate_scope_drift(
    bundle: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    """Evaluate scope drift findings from the bundle.

    Returns (blocking_findings, weak_findings).
    """
    blocking: list[str] = []
    weak: list[str] = []
    findings = _as_list(bundle.get("scope_drift_findings"))
    for f in findings:
        if not isinstance(f, Mapping):
            continue
        if not _is_open(f):
            continue
        drift_type = _as_str(f.get("drift_type", ""))
        if _is_blocking_severity(f):
            blocking.append(
                f"scope_drift blocking: {drift_type or 'unknown'} "
                f"(id={_as_str(f.get('drift_id', '?'))})"
            )
        else:
            severity = _as_str(f.get("severity", "unknown"))
            weak.append(
                f"scope_drift {severity}: {drift_type or 'unknown'} "
                f"(id={_as_str(f.get('drift_id', '?'))})"
            )
    return blocking, weak


def _evaluate_contradictions(
    bundle: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    """Evaluate contradiction findings from the bundle.

    Returns (blocking_findings, weak_findings).
    """
    blocking: list[str] = []
    weak: list[str] = []
    findings = _as_list(bundle.get("contradiction_findings"))
    for f in findings:
        if not isinstance(f, Mapping):
            continue
        if not _is_open(f):
            continue
        c_type = _as_str(f.get("contradiction_type", ""))
        if _is_blocking_severity(f):
            blocking.append(
                f"contradiction blocking: {c_type or 'unknown'} "
                f"(id={_as_str(f.get('contradiction_id', '?'))})"
            )
        else:
            severity = _as_str(f.get("severity", "unknown"))
            weak.append(
                f"contradiction {severity}: {c_type or 'unknown'} "
                f"(id={_as_str(f.get('contradiction_id', '?'))})"
            )
    return blocking, weak


def _evaluate_stale(
    bundle: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    """Evaluate stale knowledge findings from the bundle.

    source_deleted is treated as blocking; all other open stale findings
    are treated as weak.

    Returns (blocking_findings, weak_findings).
    """
    blocking: list[str] = []
    weak: list[str] = []
    findings = _as_list(bundle.get("stale_findings"))
    for f in findings:
        if not isinstance(f, Mapping):
            continue
        if not _is_open(f):
            continue
        stale_type = _as_str(f.get("stale_type", ""))
        if stale_type == "source_deleted" or _is_blocking_severity(f):
            blocking.append(
                f"stale blocking: {stale_type or 'unknown'} "
                f"(id={_as_str(f.get('finding_id', '?'))})"
            )
        else:
            weak.append(
                f"stale warning: {stale_type or 'unknown'} "
                f"(id={_as_str(f.get('finding_id', '?'))})"
            )
    return blocking, weak


def _evaluate_architect_signals(
    bundle: Mapping[str, Any],
    as_of: str | None,
) -> tuple[list[str], list[str]]:
    """Evaluate architect signals.

    Returns (blocking_findings, weak_findings).
    """
    blocking: list[str] = []
    weak: list[str] = []
    try:
        from tools.surrealdb.architect_signals import scan_architect_signals_v1

        result = scan_architect_signals_v1(bundle, as_of=as_of)
        for sig in result.signals:
            if not isinstance(sig, object):
                continue
            severity = _as_str(getattr(sig, "severity", ""))
            title = _as_str(getattr(sig, "title", ""))
            signal_type = _as_str(getattr(sig, "signal_type", ""))
            status = _as_str(getattr(sig, "status", "open"))
            if status in {"resolved", "accepted_risk", "false_positive"}:
                continue
            if severity == "blocking":
                blocking.append(
                    f"architect signal blocking: {title or signal_type}"
                )
            elif severity in {"watch", "info"}:
                weak.append(
                    f"architect signal {severity}: {title or signal_type}"
                )
    except Exception as exc:  # noqa: BLE001
        weak.append(f"architect signals error: {exc!s}")
    return blocking, weak


def _evaluate_missing_inputs(
    bundle: Mapping[str, Any],
) -> list[str]:
    """Identify missing or empty bundle inputs.

    Returns a list of missing input descriptions.
    """
    missing: list[str] = []
    for key in ("sources", "decisions", "evidence_items"):
        val = bundle.get(key)
        if val is None or (isinstance(val, (list, tuple)) and len(val) == 0):
            missing.append(f"bundle.{key} is empty or missing")
    return missing


def _derive_confidence(
    readiness_level: str,
    blocking_count: int,
    weak_count: int,
    missing_count: int,
) -> float:
    """Derive a deterministic confidence score from the readiness level."""
    if readiness_level == "blocked":
        # Confidence falls as more blockers accumulate; never exceeds 0.30
        return max(0.05, min(0.30, 0.30 - (blocking_count - 1) * 0.05))
    if readiness_level == "weak":
        return max(0.35, min(0.55, 0.55 - weak_count * 0.02 - missing_count * 0.03))
    if readiness_level == "acceptable":
        return max(0.60, min(0.80, 0.80 - weak_count * 0.05))
    # strong
    return 0.95


def _derive_required_validation(readiness_level: str) -> tuple[str, ...]:
    """Return required validation steps based on readiness level."""
    if readiness_level == "blocked":
        return (
            "Resolve all blocking findings before proceeding.",
            "Re-run evaluate_agent_os_readiness_v1 after fixes.",
            "Human-GO required before any write action.",
        )
    if readiness_level == "weak":
        return (
            "Address weak findings to improve readiness.",
            "Review missing inputs and populate bundle where possible.",
            "Re-run evaluate_agent_os_readiness_v1 after improvements.",
        )
    if readiness_level == "acceptable":
        return (
            "Proceed with caution; monitor weak findings.",
            "Consider resolving watch-level signals before major changes.",
        )
    return ("System healthy. No immediate validation required.",)


# ── Public API ────────────────────────────────────────────────────────────────


def evaluate_agent_os_readiness_v1(
    bundle: Any,
    as_of: str | None = None,
) -> AgentOsReadinessResult:
    """Evaluate Agent OS readiness from an in-memory context bundle.

    Pure, deterministic, read-only.  No DB/network/file writes.

    Args:
        bundle: In-memory context bundle.  Must be a mapping with at least
                a ``meta`` key containing a ``scope_id`` string.
        as_of:  Optional ISO-8601 UTC timestamp for deterministic output.
                Defaults to ``cdb_utcnow().isoformat()``.

    Returns:
        :class:`AgentOsReadinessResult` with readiness_level, findings,
        confidence, guardrails, and a Markdown report method.

    Raises:
        AgentOsReadinessError: if the bundle is None, not a mapping, or
                               missing ``meta.scope_id``.
    """
    validated = _validate_bundle(bundle)

    meta = validated.get("meta", {})
    scope_id = _as_str(meta.get("scope_id", "")).strip()
    if not scope_id:
        raise AgentOsReadinessError(
            "bundle.meta.scope_id is required and must be a non-empty string"
        )

    generated_at = as_of if isinstance(as_of, str) and as_of.strip() else cdb_utcnow().isoformat()

    # Aggregate signals from all sub-evaluators
    all_blocking: list[str] = []
    all_weak: list[str] = []

    b1, w1 = _evaluate_quality(validated, as_of)
    all_blocking.extend(b1)
    all_weak.extend(w1)

    b2, w2 = _evaluate_scope_drift(validated)
    all_blocking.extend(b2)
    all_weak.extend(w2)

    b3, w3 = _evaluate_contradictions(validated)
    all_blocking.extend(b3)
    all_weak.extend(w3)

    b4, w4 = _evaluate_stale(validated)
    all_blocking.extend(b4)
    all_weak.extend(w4)

    b5, w5 = _evaluate_architect_signals(validated, as_of)
    all_blocking.extend(b5)
    all_weak.extend(w5)

    missing_inputs = _evaluate_missing_inputs(validated)

    # Derive readiness level (fail-closed: any blocker → blocked)
    if all_blocking:
        readiness_level = "blocked"
    elif len(all_weak) >= 3 or missing_inputs:
        readiness_level = "weak"
    elif all_weak:
        readiness_level = "acceptable"
    else:
        readiness_level = "strong"

    confidence = _derive_confidence(
        readiness_level,
        blocking_count=len(all_blocking),
        weak_count=len(all_weak),
        missing_count=len(missing_inputs),
    )

    required_validation = _derive_required_validation(readiness_level)

    r_id = _readiness_id(scope_id, generated_at)

    return AgentOsReadinessResult(
        readiness_id=r_id,
        target_scope=scope_id,
        readiness_level=readiness_level,
        blocking_findings=tuple(all_blocking),
        weak_findings=tuple(all_weak),
        missing_inputs=tuple(missing_inputs),
        recommended_next_reads=RECOMMENDED_NEXT_READS,
        required_validation=required_validation,
        guardrails=GUARDRAILS,
        confidence=confidence,
        generated_at=generated_at,
        schema_version=SCHEMA_VERSION,
    )
