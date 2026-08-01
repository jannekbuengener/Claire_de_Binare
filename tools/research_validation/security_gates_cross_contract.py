"""Deterministic read-only Security/Provenance/Integrity gate invariants (#4271).

Companion to ``cdb.research_security_gate.v1``. No network, no DB, no scanner
execution, no writes. Relational fail-closed rules that JSON Schema cannot
express alone.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
HEAD_SHA_RE = re.compile(r"^[a-f0-9]{40}$")

REQUIRED_CHECK_IDS: frozenset[str] = frozenset(
    {
        "untrusted_input_classification",
        "prompt_injection_resistance",
        "sensitive_data_exclusion",
        "source_provenance_complete",
        "artifact_hash_bindings",
        "head_and_dataset_integrity",
        "codex_security_review",
        "read_only_enforcement",
    }
)

BLOCKING_VERDICTS: frozenset[str] = frozenset({"FAIL", "BLOCKED", "REVIEW_REQUIRED"})

PASS_COMPATIBLE_VERDICTS: frozenset[str] = frozenset({"PASS", "WARNING"})

FORBIDDEN_NEXT_ACTIONS: frozenset[str] = frozenset(
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

DRIFT_INVALIDATING: frozenset[str] = frozenset(
    {
        "HEAD_DRIFT",
        "CANDIDATE_DRIFT",
        "MANIFEST_DRIFT",
        "DATASET_DRIFT",
        "ARTIFACT_DRIFT",
    }
)


class SecurityGateContractError(ValueError):
    """Raised when security-gate cross-contract invariants fail."""


def _as_mapping(value: Any, *, label: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SecurityGateContractError(f"{label} must be an object")
    return value


def validate_required_checks(gate: Mapping[str, Any]) -> list[str]:
    """Every required check_id must appear exactly once."""
    errors: list[str] = []
    rows = gate.get("check_results")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ["check_results must be an array"]
    seen: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"check_results[{idx}] must be an object")
            continue
        check_id = row.get("check_id")
        if not isinstance(check_id, str):
            errors.append(f"check_results[{idx}].check_id required")
            continue
        seen.append(check_id)
    missing = sorted(REQUIRED_CHECK_IDS - set(seen))
    if missing:
        errors.append(f"missing required checks: {missing}")
    duplicates = sorted({c for c in seen if seen.count(c) > 1})
    if duplicates:
        errors.append(f"duplicate checks: {duplicates}")
    return errors


def validate_source_provenance(gate: Mapping[str, Any]) -> list[str]:
    """Reject missing or incomplete source provenance rows."""
    errors: list[str] = []
    rows = gate.get("source_provenance")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return ["source_provenance must be a non-empty array"]
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"source_provenance[{idx}] must be an object")
            continue
        for field in ("source_id", "provider", "locator", "content_hash"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"source_provenance[{idx}].{field} required")
        content_hash = row.get("content_hash")
        if isinstance(content_hash, str) and not SHA256_RE.fullmatch(content_hash):
            errors.append(
                f"source_provenance[{idx}].content_hash must match sha256:<64 hex>"
            )
    return errors


def validate_integrity_bindings(gate: Mapping[str, Any]) -> list[str]:
    """Reject missing candidate/manifest/head/dataset/artifact hashes."""
    errors: list[str] = []
    bindings = gate.get("integrity_bindings")
    if not isinstance(bindings, Mapping):
        return ["integrity_bindings must be an object"]
    for field in (
        "candidate_content_hash",
        "validation_manifest_hash",
    ):
        value = bindings.get(field)
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            errors.append(f"integrity_bindings.{field} must match sha256:<64 hex>")
    head = bindings.get("code_head_sha")
    if not isinstance(head, str) or not HEAD_SHA_RE.fullmatch(head):
        errors.append("integrity_bindings.code_head_sha must be 40-char hex")
    if (
        not isinstance(bindings.get("code_head_ref"), str)
        or not str(bindings.get("code_head_ref")).strip()
    ):
        errors.append("integrity_bindings.code_head_ref required")
    if not isinstance(bindings.get("validation_manifest_id"), str) or not str(
        bindings.get("validation_manifest_id")
    ).startswith("vm-"):
        errors.append("integrity_bindings.validation_manifest_id required (vm-*)")
    for list_field in ("dataset_hashes", "artifact_hashes"):
        rows = bindings.get(list_field)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            errors.append(f"integrity_bindings.{list_field} must be non-empty")
            continue
        for idx, row in enumerate(rows):
            if not isinstance(row, Mapping):
                errors.append(f"integrity_bindings.{list_field}[{idx}] must be object")
                continue
            digest = row.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                errors.append(f"integrity_bindings.{list_field}[{idx}].sha256 invalid")
    return errors


def validate_fail_closed_verdicts(gate: Mapping[str, Any]) -> list[str]:
    """FAIL/BLOCKED/REVIEW_REQUIRED and suspicion flags cannot yield PASS."""
    errors: list[str] = []
    overall = gate.get("overall_verdict")
    rows = gate.get("check_results")
    if not isinstance(rows, Sequence):
        return ["check_results must be an array"]
    blocking_checks: list[str] = []
    warning_checks: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        verdict = row.get("verdict")
        check_id = row.get("check_id")
        if verdict in BLOCKING_VERDICTS:
            blocking_checks.append(str(check_id))
        if verdict == "WARNING":
            warning_checks.append(str(check_id))
            disposition = row.get("disposition")
            if not isinstance(disposition, str) or not disposition.strip():
                errors.append(f"{check_id}: WARNING requires disposition")
    if overall == "PASS" and blocking_checks:
        errors.append(
            "overall_verdict PASS forbidden when checks are "
            f"FAIL/BLOCKED/REVIEW_REQUIRED: {blocking_checks}"
        )
    if overall == "PASS" and warning_checks:
        limitations = gate.get("limitations")
        if not isinstance(limitations, Sequence) or not limitations:
            errors.append("WARNING checks require non-empty limitations")
    injection = _as_mapping(
        gate.get("injection_assessment"), label="injection_assessment"
    )
    sensitive = _as_mapping(
        gate.get("sensitive_data_assessment"), label="sensitive_data_assessment"
    )
    if overall == "PASS" and injection is not None:
        if injection.get("suspicion") is True:
            errors.append("injection suspicion cannot yield overall PASS")
        if injection.get("verdict") in BLOCKING_VERDICTS:
            errors.append("injection blocking verdict cannot yield overall PASS")
    if overall == "PASS" and sensitive is not None:
        if sensitive.get("suspicion") is True:
            errors.append("secret/credential suspicion cannot yield overall PASS")
        if sensitive.get("verdict") in BLOCKING_VERDICTS:
            errors.append("sensitive-data blocking verdict cannot yield overall PASS")
    if sensitive is not None:
        redactions = sensitive.get("redactions")
        if isinstance(redactions, Sequence):
            for idx, row in enumerate(redactions):
                if not isinstance(row, Mapping):
                    continue
                # Redaction must never carry a raw secret value field.
                if "value" in row or "secret" in row or "raw" in row:
                    errors.append(
                        f"sensitive_data_assessment.redactions[{idx}] must not "
                        "contain raw secret values"
                    )
    return errors


def validate_authority_non_escalation(gate: Mapping[str, Any]) -> list[str]:
    """Security/integrity PASS never becomes validation or live authority."""
    errors: list[str] = []
    authority = gate.get("authority_boundaries")
    if not isinstance(authority, Mapping):
        return ["authority_boundaries must be an object"]
    required_false = (
        "research_apps_validation_authority",
        "hermes_live_authority",
        "automatic_strategy_promotion",
        "security_integrity_implies_semantic_correctness",
        "paper_candidate_is_live_go",
        "real_money_go",
        "risk_bypass",
    )
    for field in required_false:
        if authority.get(field) is not False:
            errors.append(f"authority_boundaries.{field} must be false")
    if gate.get("content_classification") != "UNTRUSTED_INPUT":
        errors.append("content_classification must be UNTRUSTED_INPUT")
    codex = gate.get("codex_security_review")
    if isinstance(codex, Mapping):
        if codex.get("may_authorize_live") is not False:
            errors.append("codex_security_review.may_authorize_live must be false")
        if codex.get("may_authorize_risk_bypass") is not False:
            errors.append(
                "codex_security_review.may_authorize_risk_bypass must be false"
            )
        if codex.get("may_authorize_capital") is not False:
            errors.append("codex_security_review.may_authorize_capital must be false")
        if codex.get("scanner_executed") is not False:
            errors.append(
                "codex_security_review.scanner_executed must be false in contract slice"
            )
        status = codex.get("status")
        if status in ("NOT_RUN", "PENDING") and gate.get("overall_verdict") == "PASS":
            # Deferred Codex review is allowed only as WARNING check + limitation.
            rows = gate.get("check_results")
            codex_check = None
            if isinstance(rows, Sequence):
                for row in rows:
                    if isinstance(row, Mapping) and row.get("check_id") == (
                        "codex_security_review"
                    ):
                        codex_check = row
                        break
            if codex_check is None or codex_check.get("verdict") != "WARNING":
                errors.append(
                    "codex status NOT_RUN/PENDING with overall PASS requires "
                    "codex_security_review check verdict WARNING"
                )
    return errors


def validate_drift_invalidates_pass(gate: Mapping[str, Any]) -> list[str]:
    """Head/candidate/manifest/dataset drift cannot keep PASS eligibility."""
    errors: list[str] = []
    drift = gate.get("drift_status", "NONE")
    overall = gate.get("overall_verdict")
    if drift in DRIFT_INVALIDATING and overall in ("PASS", "WARNING"):
        errors.append(
            f"drift_status {drift} invalidates PASS/WARNING evidence eligibility"
        )
    if overall == "PASS" and drift not in (None, "NONE"):
        errors.append("overall_verdict PASS requires drift_status NONE")
    return errors


def validate_forbidden_actions(actions: Sequence[Any] | None) -> list[str]:
    """Reject live/capital/risk-bypass/auto-promotion actions if supplied."""
    if actions is None:
        return []
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)):
        return ["actions must be a sequence when provided"]
    errors: list[str] = []
    for action in actions:
        if action in FORBIDDEN_NEXT_ACTIONS:
            errors.append(f"forbidden action not allowed: {action}")
    return errors


def validate_security_gate_record(gate: Mapping[str, Any]) -> list[str]:
    """Aggregate fail-closed invariants for one security gate record."""
    errors: list[str] = []
    errors.extend(validate_required_checks(gate))
    errors.extend(validate_source_provenance(gate))
    errors.extend(validate_integrity_bindings(gate))
    errors.extend(validate_fail_closed_verdicts(gate))
    errors.extend(validate_authority_non_escalation(gate))
    errors.extend(validate_drift_invalidates_pass(gate))
    return errors


def assert_valid(errors: Sequence[str], *, context: str) -> None:
    if errors:
        joined = "; ".join(errors)
        raise SecurityGateContractError(f"{context}: {joined}")


def security_pass_grants_validation_authority(gate: Mapping[str, Any]) -> bool:
    """Always False — helper for explicit non-escalation assertions in tests."""
    _ = gate
    return False
