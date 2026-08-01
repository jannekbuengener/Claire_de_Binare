"""Deterministic read-only Wave-2 cross-contract invariants.

JSON Schema cannot express relational version lineage or multi-artifact
transition rules. This module is the fail-closed companion validator for
Research Validation Wave 2 (#4267/#4268/#4269). No network, no DB, no writes.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

VERSION_RE = re.compile(r"^v([0-9]+)$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")

SAFE_ALLOWED_NEXT_ACTIONS: frozenset[str] = frozenset(
    {
        "revise_candidate_version",
        "collect_missing_gate_evidence",
        "keep_parked",
        "open_validation_run",
        "attach_evidence_artifact",
        "record_reject",
        "record_revise",
        "register_paper_candidate_status",
    }
)

FORBIDDEN_ALLOWED_NEXT_ACTIONS: frozenset[str] = frozenset(
    {
        "live_trading",
        "live_capital_allocation",
        "real_money_go",
        "bypass_risk_layer",
        "automatic_strategy_promotion",
        "promote_to_live",
        "paper_trading_go",
        "capital_allocation",
        "risk_bypass",
    }
)

PASS_COMPATIBLE_VERDICTS: frozenset[str] = frozenset({"PASS", "WARNING"})
BLOCKING_OVERALL_VERDICTS: frozenset[str] = frozenset(
    {"FAIL", "BLOCKED", "INSUFFICIENT_DATA"}
)


class Wave2ContractError(ValueError):
    """Raised when Wave-2 cross-contract invariants fail."""


def parse_candidate_version(value: str) -> int:
    match = VERSION_RE.fullmatch(str(value))
    if not match:
        raise Wave2ContractError(f"invalid candidate_version: {value!r}")
    return int(match.group(1))


def canonical_content_hash(payload: Mapping[str, Any]) -> str:
    """Deterministic sha256 over canonical JSON (sorted keys, no whitespace)."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"sha256:{digest}"


def validate_candidate_lineage(candidate: Mapping[str, Any]) -> list[str]:
    """Enforce parent/child version lineage (PMR-01)."""
    errors: list[str] = []
    version_raw = candidate.get("candidate_version")
    parent_raw = candidate.get("parent_version")
    if not isinstance(version_raw, str) or not VERSION_RE.fullmatch(version_raw):
        errors.append("candidate_version must match ^v[0-9]+$")
        return errors
    version_n = int(VERSION_RE.fullmatch(version_raw).group(1))  # type: ignore[union-attr]
    if version_n < 1:
        errors.append("candidate_version number must be >= 1")
        return errors
    if version_n == 1:
        if parent_raw is not None:
            errors.append("v1 candidate requires parent_version null")
        return errors
    if parent_raw is None:
        errors.append(f"{version_raw} requires parent_version v{version_n - 1}")
        return errors
    if not isinstance(parent_raw, str) or not VERSION_RE.fullmatch(parent_raw):
        errors.append("parent_version must be null or match ^v[0-9]+$")
        return errors
    parent_n = int(VERSION_RE.fullmatch(parent_raw).group(1))  # type: ignore[union-attr]
    if parent_raw == version_raw:
        errors.append("parent_version must not equal candidate_version")
    if parent_n >= version_n:
        errors.append(
            "parent_version must not be identical or future relative to candidate"
        )
    if parent_n != version_n - 1:
        errors.append(
            f"{version_raw} requires exact previous parent_version v{version_n - 1}"
        )
    return errors


def validate_brief_provenance(candidate: Mapping[str, Any]) -> list[str]:
    """Require exact brief version + immutable hash (PMR-02)."""
    errors: list[str] = []
    provenance = candidate.get("provenance")
    if not isinstance(provenance, Mapping):
        return ["provenance object required"]
    brief_id = provenance.get("research_brief_id")
    brief_version = provenance.get("research_brief_version")
    brief_hash = provenance.get("research_brief_content_hash")
    if not isinstance(brief_id, str) or not brief_id.startswith("rb-"):
        errors.append("provenance.research_brief_id required")
    if not isinstance(brief_version, str) or not VERSION_RE.fullmatch(brief_version):
        errors.append("provenance.research_brief_version required (^v[0-9]+$)")
    if not isinstance(brief_hash, str) or not SHA256_RE.fullmatch(brief_hash):
        errors.append(
            "provenance.research_brief_content_hash required (^sha256:[a-f0-9]{64}$)"
        )
    return errors


def validate_decision_allowed_actions(decision: Mapping[str, Any]) -> list[str]:
    """Reject safety-critical allowed_next_actions (PMR-03)."""
    errors: list[str] = []
    actions = decision.get("allowed_next_actions")
    if not isinstance(actions, list) or not actions:
        return ["allowed_next_actions must be a non-empty list"]
    for action in actions:
        if not isinstance(action, str):
            errors.append(f"allowed_next_actions entry must be string: {action!r}")
            continue
        if action in FORBIDDEN_ALLOWED_NEXT_ACTIONS:
            errors.append(f"forbidden allowed_next_action: {action}")
        elif action not in SAFE_ALLOWED_NEXT_ACTIONS:
            errors.append(
                f"unknown allowed_next_action outside safe vocabulary: {action}"
            )
    return errors


def _evidence_pass_compatible(evidence: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    overall = evidence.get("overall_verdict")
    if overall in BLOCKING_OVERALL_VERDICTS:
        errors.append(
            f"PAPER_CANDIDATE forbidden when evidence overall_verdict={overall}"
        )
    if overall != "PASS":
        errors.append(
            "PAPER_CANDIDATE requires evidence overall_verdict PASS "
            f"(got {overall!r})"
        )
    gate_results = evidence.get("gate_results")
    if not isinstance(gate_results, list) or not gate_results:
        errors.append("PAPER_CANDIDATE requires gate_results")
        return errors
    for row in gate_results:
        if not isinstance(row, Mapping):
            errors.append("gate_results entries must be objects")
            continue
        verdict = row.get("verdict")
        if verdict not in PASS_COMPATIBLE_VERDICTS:
            errors.append(
                f"PAPER_CANDIDATE blocked by gate {row.get('gate')!r} "
                f"verdict={verdict!r}"
            )
    hashes = evidence.get("artifact_hashes")
    if not isinstance(hashes, list) or not hashes:
        errors.append("PAPER_CANDIDATE requires artifact_hashes")
    for key in ("evidence_id", "run_id", "candidate_id", "candidate_version"):
        if not evidence.get(key):
            errors.append(f"PAPER_CANDIDATE requires evidence.{key}")
    return errors


def validate_paper_candidate_transition(
    *,
    candidate: Mapping[str, Any],
    evidence: Mapping[str, Any] | None,
    decision: Mapping[str, Any] | None,
    transition: Mapping[str, Any] | None = None,
) -> list[str]:
    """Bind candidate version + DecisionRecord + PASS evidence (PMR-04)."""
    errors: list[str] = []
    if decision is None:
        return ["PAPER_CANDIDATE transition requires DecisionRecord"]
    if decision.get("decision") != "PAPER_CANDIDATE":
        return ["decision.decision must be PAPER_CANDIDATE for this check"]
    if evidence is None:
        return ["PAPER_CANDIDATE transition requires CandidateEvidence"]

    for left, right, label in (
        (candidate.get("candidate_id"), decision.get("candidate_id"), "decision"),
        (
            candidate.get("candidate_version"),
            decision.get("candidate_version"),
            "decision",
        ),
        (candidate.get("candidate_id"), evidence.get("candidate_id"), "evidence"),
        (
            candidate.get("candidate_version"),
            evidence.get("candidate_version"),
            "evidence",
        ),
    ):
        if left != right:
            errors.append(
                f"candidate/{label} identity mismatch: "
                f"candidate=({candidate.get('candidate_id')},"
                f"{candidate.get('candidate_version')}) "
                f"{label}=({right if label == 'decision' else evidence.get('candidate_id')},"
                f"{decision.get('candidate_version') if label == 'decision' else evidence.get('candidate_version')})"
            )

    if decision.get("evidence_id") != evidence.get("evidence_id"):
        errors.append("decision.evidence_id must equal evidence.evidence_id")
    if decision.get("run_id") != evidence.get("run_id"):
        errors.append("decision.run_id must equal evidence.run_id")

    errors.extend(_evidence_pass_compatible(evidence))
    errors.extend(validate_decision_allowed_actions(decision))

    if transition is not None:
        if transition.get("to_status") != "PAPER_CANDIDATE":
            errors.append("transition.to_status must be PAPER_CANDIDATE")
        if transition.get("candidate_id") != candidate.get("candidate_id"):
            errors.append("transition.candidate_id mismatch")
        if transition.get("candidate_version") != candidate.get("candidate_version"):
            errors.append("transition.candidate_version mismatch")
        if transition.get("decision_id") != decision.get("decision_id"):
            errors.append("transition.decision_id mismatch")
        if transition.get("evidence_id") != evidence.get("evidence_id"):
            errors.append("transition.evidence_id mismatch")
        if not transition.get("decision_record_hash"):
            errors.append("transition.decision_record_hash required")
        if not transition.get("evidence_hash"):
            errors.append("transition.evidence_hash required")
    return errors


def validate_source_evidence_non_authority(
    source_evidence: Mapping[str, Any],
) -> list[str]:
    """SourceEvidence must never claim validation/decision authority."""
    errors: list[str] = []
    for field in (
        "validation_authority",
        "decision_authority",
        "contains_secrets",
        "contains_account_data",
    ):
        if source_evidence.get(field) is not False:
            errors.append(f"{field} must be false")
    if source_evidence.get("trust_classification") != "UNTRUSTED_INPUT":
        errors.append("trust_classification must be UNTRUSTED_INPUT")
    claim_type = source_evidence.get("claim_type")
    banned = {"PASS", "FAIL", "PAPER_CANDIDATE", "VALIDATION_VERDICT"}
    if claim_type in banned:
        errors.append(
            f"claim_type must not be validation/decision outcome: {claim_type}"
        )
    claim = str(source_evidence.get("claim", ""))
    for token in (" overall PASS", " overall FAIL", " set PAPER_CANDIDATE"):
        if token.strip() in claim:
            errors.append("claim must not assert PASS/FAIL/PAPER_CANDIDATE outcomes")
    return errors


def validate_compiler_input_completeness(
    *,
    research_brief: Mapping[str, Any] | None,
    source_evidence_refs: Sequence[Mapping[str, Any]] | None,
    candidate_draft: Mapping[str, Any] | None,
) -> tuple[str, list[str]]:
    """Return (status, reject_reasons) for compiler contract semantics.

    Status: READY | BLOCKED | NEEDS_RESEARCH
    Does not invent missing entry/exit/risk/execution rules.
    """
    reasons: list[str] = []
    if research_brief is None:
        return "BLOCKED", ["missing ResearchBrief"]
    if not research_brief.get("brief_id") or not research_brief.get("brief_version"):
        reasons.append("ResearchBrief missing brief_id or brief_version")
    if source_evidence_refs is None or len(source_evidence_refs) == 0:
        reasons.append("missing SourceEvidence references")
        return "NEEDS_RESEARCH", reasons
    if candidate_draft is None:
        return "BLOCKED", ["missing candidate draft fields"]

    required_lists = (
        "entry_rules",
        "exit_rules",
        "risk_assumptions",
        "execution_assumptions",
    )
    for key in required_lists:
        value = candidate_draft.get(key)
        if not isinstance(value, list) or not value:
            reasons.append(f"missing or empty {key} — compiler must not invent rules")
    hypothesis = candidate_draft.get("falsifiable_hypothesis")
    if not isinstance(hypothesis, str) or not hypothesis.strip():
        reasons.append("non-falsifiable or missing hypothesis — BLOCKED")
        return "BLOCKED", reasons
    if reasons:
        # Missing rules with a falsifiable target → needs more research, not invention.
        if any(r.startswith("missing or empty") for r in reasons):
            return "NEEDS_RESEARCH", reasons
        return "BLOCKED", reasons
    return "READY", []


def assert_valid(errors: Sequence[str], *, context: str) -> None:
    if errors:
        joined = "; ".join(errors)
        raise Wave2ContractError(f"{context}: {joined}")
