"""Self-Explanation Builder v1 — side-effect-free domain component.

Issues:
    #2189 — Implement self-explanation builder v1
    Parent: #2188
    Epic: #1976

This module implements a minimal, side-effect-free Self-Explanation Builder.
It produces structured explanations for governance-relevant conditions without
DB access, MCP access, networking, or secrets. Every output includes mandatory
guardrail text: no action authorization, no Live-Readiness-Go, no Echtgeld-Go,
no autonomy without gates.

Supported explanation types (from #2188):
    why_blocked, why_risky, why_stale, why_decision_current,
    why_decision_superseded, why_scope_blocked, why_evidence_weak,
    why_agent_needs_go, why_doc_untrusted

Design intent:
    Pure domain model. No SurrealDB SDK. No MCP. No CLI.
    Input: structured data. Output: machine-readable dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_SCHEMA_VERSION = "self-explanation/v1"

_EXPLANATION_TYPES = frozenset(
    {
        "why_blocked",
        "why_risky",
        "why_stale",
        "why_decision_current",
        "why_decision_superseded",
        "why_scope_blocked",
        "why_evidence_weak",
        "why_agent_needs_go",
        "why_doc_untrusted",
    }
)

_GUARDRAILS = (
    "Keine Handlungserlaubnis durch diese Erklaerung.",
    "Kein Live-Readiness-Go.",
    "Kein Echtgeld-Go.",
    "Keine Autonomie ohne Gates.",
    "Diese Erklaerung ist Kontext, keine Freigabe.",
)


class SelfExplanationError(Exception):
    """Base error for self-explanation builder."""

    code: str = "SELF_EXPLANATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidExplanationTypeError(SelfExplanationError):
    """Raised when an unsupported explanation type is requested."""

    code = "INVALID_EXPLANATION_TYPE"


class InvalidInputError(SelfExplanationError):
    """Raised when the builder input fails validation."""

    code = "INVALID_INPUT"


@dataclass(frozen=True)
class SelfExplanationInput:
    """Validated input for the Self-Explanation Builder.

    Attributes:
        explanation_type: One of the nine supported types.
        summary: Human-readable summary of what is being explained.
        reasons: Ordered list of reasons contributing to the condition.
        evidence_refs: References to evidence supporting the explanation.
        required_next_step: The next action needed (plain text, not a command).
        confidence: Optional self-assessed confidence (0.0–1.0).
        scope_context: Optional scope identifier for which this applies.
        graph_path: Ordered sequence of context-graph node references leading
            to this explanation (e.g. topic → sub-topic → claim).
        uncertainties: Known unknowns or weaknesses in this explanation.
            Inferred by the builder when confidence is low or evidence is weak.
        decision_refs: References to governance decisions relevant to this
            explanation.
        claim_refs: References to specific claims supporting the explanation.
        memory_refs: References to memory/knowledge items consulted.
        contradictions: Identifiers of contradicting evidence or claims.
        stale_context: Context items known to be potentially outdated.
        recommended_next_reads: Paths or IDs of documents to consult next.
    """

    explanation_type: str
    summary: str
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    required_next_step: str
    confidence: float | None = None
    scope_context: str | None = None
    graph_path: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    claim_refs: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    stale_context: tuple[str, ...] = ()
    recommended_next_reads: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.explanation_type not in _EXPLANATION_TYPES:
            raise InvalidExplanationTypeError(
                f"unsupported explanation_type: {self.explanation_type!r}; "
                f"expected one of {sorted(_EXPLANATION_TYPES)}"
            )
        if not self.summary.strip():
            raise InvalidInputError("summary must be non-empty")
        if not self.reasons:
            raise InvalidInputError("reasons must contain at least one reason")
        if any(not r.strip() for r in self.reasons):
            raise InvalidInputError("each reason must be non-empty")
        if not self.evidence_refs:
            raise InvalidInputError("evidence_refs must contain at least one reference")
        if any(not e.strip() for e in self.evidence_refs):
            raise InvalidInputError("each evidence_ref must be non-empty")
        if not self.required_next_step.strip():
            raise InvalidInputError("required_next_step must be non-empty")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise InvalidInputError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "explanation_type": self.explanation_type,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "evidence_refs": list(self.evidence_refs),
            "required_next_step": self.required_next_step,
            "graph_path": list(self.graph_path),
            "uncertainties": list(self.uncertainties),
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.scope_context is not None:
            payload["scope_context"] = self.scope_context
        if self.decision_refs:
            payload["decision_refs"] = list(self.decision_refs)
        if self.claim_refs:
            payload["claim_refs"] = list(self.claim_refs)
        if self.memory_refs:
            payload["memory_refs"] = list(self.memory_refs)
        if self.contradictions:
            payload["contradictions"] = list(self.contradictions)
        if self.stale_context:
            payload["stale_context"] = list(self.stale_context)
        if self.recommended_next_reads:
            payload["recommended_next_reads"] = list(self.recommended_next_reads)
        return payload


@dataclass(frozen=True)
class SelfExplanationOutput:
    """Structured output of the Self-Explanation Builder.

    Attributes:
        schema_version: Schema identifier for the output format.
        explanation_type: The explanation type that was built.
        summary: Human-readable summary.
        reasons: Ordered list of reasons.
        evidence_refs: References to supporting evidence.
        required_next_step: Required next action.
        guardrails: Mandatory guardrail text (always present).
        confidence: Optional confidence level.
        scope_context: Optional scope context.
        graph_path: Ordered context-graph node references leading to this
            explanation. Always present (may be empty).
        uncertainties: Known unknowns or weaknesses. Always present; inferred
            by the builder when evidence is weak or confidence is low.
        decision_refs: Governance decisions referenced by this explanation.
        claim_refs: Specific claims referenced.
        memory_refs: Memory/knowledge items consulted.
        contradictions: Contradicting evidence or claim identifiers.
        stale_context: Context items known to be potentially outdated.
        recommended_next_reads: Documents to consult for further context.
    """

    schema_version: str = _SCHEMA_VERSION
    explanation_type: str = ""
    summary: str = ""
    reasons: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    required_next_step: str = ""
    guardrails: tuple[str, ...] = ()
    confidence: float | None = None
    scope_context: str | None = None
    graph_path: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    claim_refs: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    stale_context: tuple[str, ...] = ()
    recommended_next_reads: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "explanation_type": self.explanation_type,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "evidence_refs": list(self.evidence_refs),
            "required_next_step": self.required_next_step,
            "guardrails": list(self.guardrails),
            "graph_path": list(self.graph_path),
            "uncertainties": list(self.uncertainties),
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.scope_context is not None:
            payload["scope_context"] = self.scope_context
        if self.decision_refs:
            payload["decision_refs"] = list(self.decision_refs)
        if self.claim_refs:
            payload["claim_refs"] = list(self.claim_refs)
        if self.memory_refs:
            payload["memory_refs"] = list(self.memory_refs)
        if self.contradictions:
            payload["contradictions"] = list(self.contradictions)
        if self.stale_context:
            payload["stale_context"] = list(self.stale_context)
        if self.recommended_next_reads:
            payload["recommended_next_reads"] = list(self.recommended_next_reads)
        return payload


def build_self_explanation(inp: SelfExplanationInput) -> SelfExplanationOutput:
    """Build a structured self-explanation from validated input.

    This is a pure function: no DB access, no MCP, no network, no secrets.
    The output always includes mandatory guardrail text, ``graph_path``, and
    ``uncertainties``. Uncertainties are inferred when ``confidence < 0.5`` or
    when the explanation type is ``why_evidence_weak`` and no uncertainties
    were provided by the caller.

    Args:
        inp: Validated SelfExplanationInput.

    Returns:
        SelfExplanationOutput with the explanation, guardrails, graph_path,
        and uncertainties.

    Raises:
        InvalidInputError: If the input fails post-initialization validation.
    """
    uncertainties = [u for u in inp.uncertainties if u.strip()]
    if not uncertainties:
        if inp.explanation_type == "why_evidence_weak":
            uncertainties.append("Evidence moeglicherweise unvollstaendig.")
        elif inp.confidence is not None and inp.confidence < 0.5:
            uncertainties.append(
                f"Niedrige Konfidenz ({inp.confidence:.2f}):"
                " Ausgabe mit Vorsicht interpretieren."
            )

    return SelfExplanationOutput(
        schema_version=_SCHEMA_VERSION,
        explanation_type=inp.explanation_type,
        summary=inp.summary,
        reasons=inp.reasons,
        evidence_refs=inp.evidence_refs,
        required_next_step=inp.required_next_step,
        guardrails=_GUARDRAILS,
        confidence=inp.confidence,
        scope_context=inp.scope_context,
        graph_path=inp.graph_path,
        uncertainties=tuple(uncertainties),
        decision_refs=inp.decision_refs,
        claim_refs=inp.claim_refs,
        memory_refs=inp.memory_refs,
        contradictions=inp.contradictions,
        stale_context=inp.stale_context,
        recommended_next_reads=inp.recommended_next_reads,
    )


def supported_explanation_types() -> frozenset[str]:
    """Return the set of supported explanation types."""
    return _EXPLANATION_TYPES
