"""Validation Plan Generator v1 — deterministic agent-readable validation plan.

Issues:
    #2109 — Implement validation plan generator v1
    Parent: #2103 (Wave-13)
    Epic: #1976

This module consumes an ImpactRadar `ImpactReport` (or its `to_payload()` dict)
and produces a concrete, agent-readable `ValidationPlan` with required checks,
suggested tests, docs to review, evidence to collect, commands to consider
(never auto-run), manual review requirements, blocking preconditions, and
success criteria.

Design intent:
    Pure domain logic. No DB access. No MCP. No networking. No file I/O.
    No GitHub write. No command execution.
    Input: ImpactReport or its payload dict.
    Output: typed ValidationPlan.
    Deterministic: same inputs → same outputs.
    Fail-closed: blocking preconditions from impact are propagated.
    Commands are suggestions only; never auto-run.
    Read-only vs dry-run vs Human-GO distinction is explicit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0.0"

# ── Input / Output types ────────────────────────────────────────────────────


@dataclass
class ValidationPlanInput:
    """Input for validation plan generation.

    Accepts either an ImpactReport directly or its `to_payload()` dict.
    Exactly one must be provided.
    """

    impact_report: Any = None
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.impact_report is None and self.payload is None:
            raise ValueError(
                "Either impact_report or payload must be provided"
            )
        if self.impact_report is not None and self.payload is not None:
            raise ValueError(
                "Provide exactly one of impact_report or payload, not both"
            )


@dataclass(frozen=True)
class ValidationPlan:
    """Deterministic validation plan for agent consumption."""

    plan_id: str
    required_checks: tuple[str, ...]
    suggested_tests: tuple[str, ...]
    docs_to_review: tuple[str, ...]
    evidence_to_collect: tuple[str, ...]
    commands_to_consider: tuple[str, ...]
    manual_review_needed: bool
    blocking_preconditions: tuple[str, ...]
    success_criteria: tuple[str, ...]
    stop_conditions: tuple[dict[str, Any], ...] = field(
        hash=False
    )
    schema_version: str = SCHEMA_VERSION

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "required_checks": list(self.required_checks),
            "suggested_tests": list(self.suggested_tests),
            "docs_to_review": list(self.docs_to_review),
            "evidence_to_collect": list(self.evidence_to_collect),
            "commands_to_consider": list(self.commands_to_consider),
            "manual_review_needed": self.manual_review_needed,
            "blocking_preconditions": list(self.blocking_preconditions),
            "success_criteria": list(self.success_criteria),
            "stop_conditions": [dict(stop) for stop in self.stop_conditions],
        }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _stable_id(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _stable_id_from_plan_content(content: dict[str, Any]) -> str:
    payload = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return _stable_id("plan", payload)


def _resolve_payload(input_data: ValidationPlanInput) -> dict[str, Any]:
    """Extract a payload dict from ValidationPlanInput."""
    if input_data.payload is not None:
        return input_data.payload
    report = input_data.impact_report
    if hasattr(report, "to_payload"):
        return report.to_payload()
    if isinstance(report, dict):
        return report
    raise TypeError(
        "impact_report must be an ImpactReport or dict, "
        f"got {type(report).__name__}"
    )


def _get_required_validation(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract required_validation from an ImpactReport payload."""
    rv = payload.get("required_validation", {})
    if isinstance(rv, dict):
        return rv
    return {}


def _copy_stop_conditions(
    stop_conditions: list[Any],
) -> tuple[dict[str, Any], ...]:
    copied: list[dict[str, Any]] = []
    for stop_condition in stop_conditions:
        if isinstance(stop_condition, dict):
            copied.append(dict(stop_condition))
            continue
        copied.append(
            {
                "type": "invalid_stop_condition_payload",
                "severity": "blocking",
                "reason": str(stop_condition),
                "required_action": (
                    "Normalize stop_conditions to dict payload before proceed"
                ),
                "human_go_required": True,
            }
        )
    return tuple(copied)


def _derive_manual_review_needed(
    required_validation: dict[str, Any],
    impact_level: str,
    gate_risks: list[str],
    blocking_preconditions: tuple[str, ...],
    stop_conditions: tuple[dict[str, Any], ...],
) -> bool:
    explicit_flag = bool(required_validation.get("manual_review_needed", False))
    blocking_stop_present = any(
        stop.get("severity") == "blocking" for stop in stop_conditions
    )
    fail_closed_signals = (
        impact_level in {"high", "blocking"}
        or bool(gate_risks)
        or bool(blocking_preconditions)
        or blocking_stop_present
    )
    return explicit_flag or fail_closed_signals


def _derive_required_checks(
    impact_level: str,
    gate_risks: list[str],
    blocking_preconditions: list[str],
    stop_conditions: list[dict[str, Any]],
) -> list[str]:
    checks: list[str] = []

    if impact_level == "blocking":
        checks.append(
            "Blocking impact level — confirm change is authorized by Human-GO"
        )
    elif impact_level == "high":
        checks.append(
            "High impact level — verify change scope and invariants"
        )
    elif impact_level == "medium":
        checks.append(
            "Medium impact level — validate affected modules and tests"
        )
    else:
        checks.append(
            "Low impact level — validate affected modules with passing unit tests"
        )

    if "governance_touched" in gate_risks:
        checks.append(
            "Governance paths touched — review constitution and policies"
        )
    if "risk_surface_touched" in gate_risks:
        checks.append(
            "Risk service surface touched — verify risk limits unchanged"
        )
    if "execution_surface_touched" in gate_risks:
        checks.append(
            "Execution surface touched — verify no order/trade side-effects"
        )
    if "contract_drift_possible" in gate_risks:
        checks.append(
            "Contract drift possible — reconcile contracts and schemas"
        )
    if "secrets_surface_touched" in gate_risks:
        checks.append(
            "Secrets surface touched — verify no credential exposure"
        )
    if "lr_surface_touched" in gate_risks:
        checks.append(
            "Live-readiness surface touched — verify no false LR-go claim"
        )

    for bp in blocking_preconditions:
        checks.append(f"BLOCKING: {bp}")

    blocking_stops = [
        s for s in stop_conditions
        if isinstance(s, dict) and s.get("severity") == "blocking"
    ]
    for st in blocking_stops:
        checks.append(
            f"Stop condition: {st.get('reason', st.get('type', 'unknown'))}"
        )

    return checks


def _derive_success_criteria(
    impact_level: str,
    confidence: str,
    gate_risks: list[str],
    has_artifacts: bool,
    has_symbols: bool,
    has_tests: bool,
    has_docs: bool,
    has_stop_conditions: bool,
) -> list[str]:
    criteria: list[str] = []

    if impact_level == "blocking":
        criteria.append(
            "All blocking preconditions resolved with explicit Human-GO"
        )
        criteria.append(
            "All stop conditions addressed and cleared"
        )
    elif impact_level == "high":
        criteria.append(
            "All affected services verified with passing unit tests"
        )
    elif impact_level in ("medium", "low"):
        criteria.append(
            "All affected modules verified with passing unit tests"
        )

    if confidence == "low":
        criteria.append(
            "Confidence is low — validate with real data before proceeding"
        )
    elif confidence == "medium":
        criteria.append(
            "Confidence is medium — cross-check inferred edges"
        )

    if "governance_touched" in gate_risks:
        criteria.append(
            "Governance review completed and signed off"
        )
    if "secrets_surface_touched" in gate_risks:
        criteria.append(
            "Secrets audit completed — no credentials exposed"
        )
    if "contract_drift_possible" in gate_risks:
        criteria.append(
            "Contract reconciliation completed — schemas match"
        )
    if "lr_surface_touched" in gate_risks:
        criteria.append(
            "Live-readiness SSOT reconciled — no false LR-go signals"
        )

    if not has_stop_conditions:
        criteria.append(
            "No stop conditions flagged — proceed with standard review"
        )

    if has_artifacts:
        criteria.append(
            "Affected artifacts identified and reviewed"
        )
    if has_symbols:
        criteria.append(
            "Affected symbols traced and verified"
        )
    if has_tests:
        criteria.append(
            "All suggested tests passing (unit + integration)"
        )
    if has_docs:
        criteria.append(
            "Documentation reviewed and updated as needed"
        )

    return criteria


# ── Core computation ────────────────────────────────────────────────────────


def build_validation_plan(input_data: ValidationPlanInput) -> ValidationPlan:
    """Build a ValidationPlan from ImpactReport data.

    Args:
        input_data: ValidationPlanInput wrapping an ImpactReport or its
                    to_payload() dict.

    Returns:
        ValidationPlan with required_checks, suggested_tests, docs_to_review,
        evidence_to_collect, commands_to_consider, manual_review_needed,
        blocking_preconditions, success_criteria, and stop_conditions.

    Deterministic. Same inputs always produce the same outputs.
    No DB, network, filesystem, GitHub, or MCP calls.
    Commands are suggestions only — never auto-executed.
    """
    payload = _resolve_payload(input_data)

    impact_level = payload.get("impact_level", "low")
    impact_id = payload.get("impact_id", "unknown")
    confidence = payload.get("confidence", "low")
    gate_risks: list[str] = payload.get("gate_risks", [])
    raw_stop_conditions: list[dict[str, Any]] = payload.get(
        "stop_conditions", []
    )

    rv = _get_required_validation(payload)

    docs_to_review: tuple[str, ...] = tuple(rv.get("docs_to_review", []))
    suggested_tests: tuple[str, ...] = tuple(rv.get("suggested_tests", []))
    evidence_to_collect: tuple[str, ...] = tuple(
        rv.get("evidence_to_collect", [])
    )
    commands_to_consider: tuple[str, ...] = tuple(
        rv.get("commands_to_consider", [])
    )
    blocking_preconditions: tuple[str, ...] = tuple(
        rv.get("blocking_preconditions", [])
    )
    stop_conditions = _copy_stop_conditions(raw_stop_conditions)
    manual_review_needed = _derive_manual_review_needed(
        required_validation=rv,
        impact_level=impact_level,
        gate_risks=gate_risks,
        blocking_preconditions=blocking_preconditions,
        stop_conditions=stop_conditions,
    )

    has_artifacts = bool(payload.get("affected_artifacts", []))
    has_symbols = bool(payload.get("affected_symbols", []))
    has_tests = bool(payload.get("affected_tests", []))
    has_docs = bool(payload.get("affected_docs", []))
    has_stop_conditions = bool(stop_conditions)

    required_checks = _derive_required_checks(
        impact_level=impact_level,
        gate_risks=gate_risks,
        blocking_preconditions=list(blocking_preconditions),
        stop_conditions=list(stop_conditions),
    )

    success_criteria = _derive_success_criteria(
        impact_level=impact_level,
        confidence=confidence,
        gate_risks=gate_risks,
        has_artifacts=has_artifacts,
        has_symbols=has_symbols,
        has_tests=has_tests,
        has_docs=has_docs,
        has_stop_conditions=has_stop_conditions,
    )

    plan_id = _stable_id_from_plan_content(
        {
            "impact_id": impact_id,
            "impact_level": impact_level,
            "confidence": confidence,
            "required_checks": required_checks,
            "suggested_tests": suggested_tests,
            "docs_to_review": docs_to_review,
            "evidence_to_collect": evidence_to_collect,
            "commands_to_consider": commands_to_consider,
            "manual_review_needed": manual_review_needed,
            "blocking_preconditions": blocking_preconditions,
            "success_criteria": success_criteria,
            "stop_conditions": stop_conditions,
        }
    )

    return ValidationPlan(
        plan_id=plan_id,
        required_checks=tuple(required_checks),
        suggested_tests=suggested_tests,
        docs_to_review=docs_to_review,
        evidence_to_collect=evidence_to_collect,
        commands_to_consider=commands_to_consider,
        manual_review_needed=manual_review_needed,
        blocking_preconditions=blocking_preconditions,
        success_criteria=tuple(success_criteria),
        stop_conditions=stop_conditions,
    )
