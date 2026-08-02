"""Deterministic read-only Hermes orchestration invariants (#4270).

Companion to ``cdb.hermes_orchestration_run.v1``. No network, no DB, no Hermes
runtime, no worker execution, no writes. Relational fail-closed rules that JSON
Schema cannot express alone.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
HEAD_SHA_RE = re.compile(r"^[a-f0-9]{40}$")

SECURITY_BLOCKING: frozenset[str] = frozenset({"FAIL", "BLOCKED", "REVIEW_REQUIRED"})

DRIFT_INVALIDATING: frozenset[str] = frozenset(
    {
        "HEAD_DRIFT",
        "CANDIDATE_DRIFT",
        "MANIFEST_DRIFT",
        "SECURITY_GATE_DRIFT",
        "DATASET_DRIFT",
        "ARTIFACT_DRIFT",
    }
)

FORBIDDEN_ACTIONS: frozenset[str] = frozenset(
    {
        "change_strategy_parameters",
        "invent_missing_parameters",
        "reclassify_domain_as_technical",
        "rewrite_fail_to_pass",
        "bypass_security_gate",
        "accept_evidence_without_hashes",
        "ignore_drift",
        "mask_drift_with_retry",
        "change_risk_limits",
        "activate_live_trading",
        "release_capital",
        "automatic_strategy_promotion",
        "promote_paper_candidate",
        "free_form_leading_verdict",
    }
)

BINDING_FIELDS: tuple[str, ...] = (
    "strategy_candidate_id",
    "strategy_candidate_version",
    "candidate_content_hash",
    "validation_manifest_id",
    "validation_manifest_hash",
    "security_gate_id",
    "security_gate_hash",
    "code_head_ref",
    "code_head_sha",
)


class HermesOrchestrationContractError(ValueError):
    """Raised when Hermes orchestration cross-contract invariants fail."""


def _as_mapping(value: Any, *, label: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise HermesOrchestrationContractError(f"{label} must be an object")
    return value


def _hash_rows_equal(left: Any, right: Any) -> bool:
    if not isinstance(left, Sequence) or isinstance(left, (str, bytes)):
        return False
    if not isinstance(right, Sequence) or isinstance(right, (str, bytes)):
        return False
    if len(left) != len(right):
        return False
    for lrow, rrow in zip(left, right, strict=True):
        if not isinstance(lrow, Mapping) or not isinstance(rrow, Mapping):
            return False
        if lrow.get("ref") != rrow.get("ref"):
            return False
        if lrow.get("sha256") != rrow.get("sha256"):
            return False
    return True


def validate_bindings(run: Mapping[str, Any]) -> list[str]:
    """Reject malformed or incomplete run bindings."""
    errors: list[str] = []
    bindings = run.get("bindings")
    if not isinstance(bindings, Mapping):
        return ["bindings must be an object"]
    for field in BINDING_FIELDS:
        value = bindings.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"bindings.{field} required")
    for hash_field in (
        "candidate_content_hash",
        "validation_manifest_hash",
        "security_gate_hash",
    ):
        digest = bindings.get(hash_field)
        if isinstance(digest, str) and not SHA256_RE.fullmatch(digest):
            errors.append(f"bindings.{hash_field} must match sha256:<64 hex>")
    head = bindings.get("code_head_sha")
    if isinstance(head, str) and not HEAD_SHA_RE.fullmatch(head):
        errors.append("bindings.code_head_sha must be 40-char hex")
    datasets = bindings.get("dataset_hashes")
    if (
        not isinstance(datasets, Sequence)
        or isinstance(datasets, (str, bytes))
        or not datasets
    ):
        errors.append("bindings.dataset_hashes must be non-empty")
    else:
        for idx, row in enumerate(datasets):
            if not isinstance(row, Mapping):
                errors.append(f"bindings.dataset_hashes[{idx}] must be object")
                continue
            digest = row.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                errors.append(f"bindings.dataset_hashes[{idx}].sha256 invalid")
    gate = run.get("security_gate_binding")
    if isinstance(gate, Mapping):
        if gate.get("security_gate_id") != bindings.get("security_gate_id"):
            errors.append(
                "security_gate_binding.id must match bindings.security_gate_id"
            )
        if gate.get("security_gate_hash") != bindings.get("security_gate_hash"):
            errors.append(
                "security_gate_binding.hash must match bindings.security_gate_hash"
            )
        if gate.get("content_classification") != "UNTRUSTED_INPUT":
            errors.append(
                "security_gate_binding.content_classification must be UNTRUSTED_INPUT"
            )
    return errors


def validate_attempt_binding_stability(run: Mapping[str, Any]) -> list[str]:
    """Bindings must be identical across all attempts and the run record."""
    errors: list[str] = []
    bindings = run.get("bindings")
    attempts = run.get("attempts")
    if not isinstance(bindings, Mapping):
        return ["bindings must be an object"]
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return ["attempts must be an array"]
    seen_ids: list[str] = []
    for idx, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            errors.append(f"attempts[{idx}] must be an object")
            continue
        attempt_id = attempt.get("attempt_id")
        if isinstance(attempt_id, str):
            if attempt_id in seen_ids:
                errors.append(f"duplicate attempt_id: {attempt_id}")
            seen_ids.append(attempt_id)
        snapshot = attempt.get("bindings_snapshot")
        if not isinstance(snapshot, Mapping):
            errors.append(f"attempts[{idx}].bindings_snapshot required")
            continue
        for field in BINDING_FIELDS:
            if snapshot.get(field) != bindings.get(field):
                errors.append(
                    f"attempts[{idx}].bindings_snapshot.{field} drifted from run bindings"
                )
        if not _hash_rows_equal(
            snapshot.get("dataset_hashes"), bindings.get("dataset_hashes")
        ):
            errors.append(
                f"attempts[{idx}].bindings_snapshot.dataset_hashes drifted from run bindings"
            )
        if snapshot.get("security_gate_version") != bindings.get(
            "security_gate_version"
        ):
            errors.append(
                f"attempts[{idx}].bindings_snapshot.security_gate_version drifted"
            )
    return errors


def validate_attempt_failure_coupling(run: Mapping[str, Any]) -> list[str]:
    """FAILED_* attempts must carry the matching failure object."""
    errors: list[str] = []
    attempts = run.get("attempts")
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return ["attempts must be an array"]
    for idx, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            errors.append(f"attempts[{idx}] must be an object")
            continue
        status = attempt.get("status")
        failure = attempt.get("failure")
        if status == "FAILED_TECHNICAL":
            if not isinstance(failure, Mapping):
                errors.append(
                    f"attempts[{idx}] FAILED_TECHNICAL requires TechnicalFailure"
                )
            elif failure.get("failure_class") != "TECHNICAL":
                errors.append(
                    f"attempts[{idx}] FAILED_TECHNICAL requires failure_class=TECHNICAL"
                )
        elif status == "FAILED_DOMAIN":
            if not isinstance(failure, Mapping):
                errors.append(f"attempts[{idx}] FAILED_DOMAIN requires DomainFailure")
            elif failure.get("failure_class") != "DOMAIN":
                errors.append(
                    f"attempts[{idx}] FAILED_DOMAIN requires failure_class=DOMAIN"
                )
        elif isinstance(failure, Mapping) and status in (
            "PENDING",
            "RUNNING",
            "SUCCEEDED",
            "CANCELLED",
        ):
            errors.append(
                f"attempts[{idx}] status {status} must not carry a failure object"
            )
    return errors


def validate_failure_verdict_consistency(run: Mapping[str, Any]) -> list[str]:
    """Domain/terminal technical failure cannot coexist with orchestration PASS."""
    errors: list[str] = []
    verdict_obj = run.get("structured_verdict")
    if not isinstance(verdict_obj, Mapping):
        return ["structured_verdict must be an object"]
    verdict = verdict_obj.get("verdict")
    attempts = run.get("attempts")
    if not isinstance(attempts, Sequence) or isinstance(attempts, (str, bytes)):
        return ["attempts must be an array"]

    domain_failures: list[str] = []
    technical_failures: list[str] = []
    ordered: list[Mapping[str, Any]] = []
    for idx, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            errors.append(f"attempts[{idx}] must be an object")
            continue
        ordered.append(attempt)
        status = attempt.get("status")
        if status == "FAILED_DOMAIN":
            domain_failures.append(f"attempts[{idx}]")
        elif status == "FAILED_TECHNICAL":
            technical_failures.append(f"attempts[{idx}]")

    failure_records = run.get("failure_records")
    if isinstance(failure_records, Sequence) and not isinstance(
        failure_records, (str, bytes)
    ):
        for idx, row in enumerate(failure_records):
            if not isinstance(row, Mapping):
                continue
            if row.get("failure_class") == "DOMAIN":
                domain_failures.append(f"failure_records[{idx}]")

    if domain_failures and verdict == "PASS":
        errors.append(
            "domain failure cannot yield structured_verdict PASS "
            f"({', '.join(domain_failures)})"
        )
    if domain_failures and verdict not in (
        "FAIL",
        "BLOCKED",
        "REVIEW_REQUIRED",
        "CANCELLED",
    ):
        errors.append(
            "domain failure requires structured_verdict "
            "FAIL|BLOCKED|REVIEW_REQUIRED|CANCELLED"
        )

    if verdict == "PASS":
        if not ordered:
            errors.append("PASS requires at least one attempt")
        else:
            last = max(
                ordered,
                key=lambda row: (
                    row.get("attempt_number")
                    if isinstance(row.get("attempt_number"), int)
                    else -1
                ),
            )
            if last.get("status") != "SUCCEEDED":
                errors.append("PASS requires final attempt status SUCCEEDED")
            if technical_failures and last.get("status") != "SUCCEEDED":
                errors.append(
                    "technical failure without succeeding final attempt "
                    "cannot yield PASS"
                )
    return errors


def validate_retry_policy(run: Mapping[str, Any]) -> list[str]:
    """Technical retries only; domain failures never auto-retry."""
    errors: list[str] = []
    policy = run.get("retry_policy")
    disposition = run.get("retry_disposition")
    if not isinstance(policy, Mapping):
        return ["retry_policy must be an object"]
    if policy.get("domain_failures_retryable") is not False:
        errors.append("retry_policy.domain_failures_retryable must be false")
    max_attempts = policy.get("max_technical_attempts")
    if not isinstance(max_attempts, int) or max_attempts < 1:
        errors.append("retry_policy.max_technical_attempts must be >= 1")
    backoff = policy.get("backoff_seconds")
    if (
        not isinstance(backoff, Sequence)
        or isinstance(backoff, (str, bytes))
        or not backoff
    ):
        errors.append("retry_policy.backoff_seconds must be a non-empty array")

    attempts = run.get("attempts")
    if isinstance(attempts, Sequence) and not isinstance(attempts, (str, bytes)):
        technical_attempts = [
            a
            for a in attempts
            if isinstance(a, Mapping) and a.get("status") == "FAILED_TECHNICAL"
        ]
        if isinstance(max_attempts, int) and len(attempts) > max_attempts:
            # Count only when technical retries were used; domain-only runs with
            # a single attempt are fine even if max_attempts is 1.
            if technical_attempts or any(
                isinstance(a, Mapping) and a.get("attempt_number", 1) > 1
                for a in attempts
            ):
                if len(attempts) > max_attempts:
                    errors.append("attempts exceed retry_policy.max_technical_attempts")

        non_retryable_technical = False
        for idx, attempt in enumerate(attempts):
            if not isinstance(attempt, Mapping):
                continue
            failure = attempt.get("failure")
            if not isinstance(failure, Mapping):
                continue
            if failure.get("failure_class") == "DOMAIN":
                if failure.get("retryable") is not False:
                    errors.append(
                        f"attempts[{idx}] domain failure must set retryable=false"
                    )
                if (
                    isinstance(disposition, Mapping)
                    and disposition.get("retryable") is True
                ):
                    errors.append("domain failure cannot yield retryable disposition")
                if isinstance(disposition, Mapping) and disposition.get(
                    "next_attempt_allowed"
                ):
                    errors.append("domain failure cannot allow next technical attempt")
            if failure.get("failure_class") == "TECHNICAL":
                if failure.get("retryable") is True:
                    if not isinstance(disposition, Mapping):
                        errors.append(
                            "retryable technical failure requires retry_disposition"
                        )
                elif failure.get("retryable") is False:
                    non_retryable_technical = True

        if non_retryable_technical and isinstance(disposition, Mapping):
            if disposition.get("retryable") is True:
                errors.append(
                    "non-retryable technical failure cannot yield retryable disposition"
                )
            if disposition.get("next_attempt_allowed") is True:
                errors.append(
                    "non-retryable technical failure cannot allow next attempt"
                )
            reason = disposition.get("reason_code")
            if reason not in (
                None,
                "TECHNICAL_EXHAUSTED",
                "DOMAIN_NOT_RETRYABLE",
                "DRIFT_NOT_RETRYABLE",
                "SECURITY_NOT_RETRYABLE",
                "CANCELLED",
                "NONE",
            ):
                errors.append(
                    "non-retryable technical failure requires non-retry reason_code"
                )
    return errors


def validate_security_gate_blocks_pass(run: Mapping[str, Any]) -> list[str]:
    """Security FAIL/BLOCKED/REVIEW_REQUIRED cannot yield orchestration PASS."""
    errors: list[str] = []
    gate = run.get("security_gate_binding")
    verdict_obj = run.get("structured_verdict")
    if not isinstance(gate, Mapping) or not isinstance(verdict_obj, Mapping):
        return ["security_gate_binding and structured_verdict required"]
    gate_verdict = gate.get("security_gate_verdict")
    verdict = verdict_obj.get("verdict")
    if gate_verdict in SECURITY_BLOCKING and verdict == "PASS":
        errors.append(
            f"security_gate_verdict {gate_verdict} cannot yield structured_verdict PASS"
        )
    return errors


def validate_evidence_and_drift_for_pass(run: Mapping[str, Any]) -> list[str]:
    """PASS requires complete hashed evidence and no invalidating drift."""
    errors: list[str] = []
    verdict_obj = run.get("structured_verdict")
    if not isinstance(verdict_obj, Mapping):
        return ["structured_verdict must be an object"]
    verdict = verdict_obj.get("verdict")
    if verdict != "PASS":
        return errors

    evidence = run.get("evidence_collection")
    if not isinstance(evidence, Mapping):
        return ["evidence_collection must be an object"]
    if evidence.get("status") != "COMPLETE":
        errors.append("PASS requires evidence_collection.status COMPLETE")
    missing = evidence.get("missing_artifacts")
    if (
        isinstance(missing, Sequence)
        and not isinstance(missing, (str, bytes))
        and missing
    ):
        errors.append("PASS forbids missing_artifacts")
    artifact_hashes = evidence.get("artifact_hashes")
    if (
        not isinstance(artifact_hashes, Sequence)
        or isinstance(artifact_hashes, (str, bytes))
        or not artifact_hashes
    ):
        errors.append("PASS requires non-empty evidence_collection.artifact_hashes")
    else:
        for idx, row in enumerate(artifact_hashes):
            if not isinstance(row, Mapping):
                errors.append(
                    f"evidence_collection.artifact_hashes[{idx}] must be object"
                )
                continue
            digest = row.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                errors.append(
                    f"evidence_collection.artifact_hashes[{idx}].sha256 invalid"
                )

    bindings = run.get("bindings")
    if isinstance(bindings, Mapping):
        produced = bindings.get("produced_artifact_hashes")
        if (
            not isinstance(produced, Sequence)
            or isinstance(produced, (str, bytes))
            or not produced
        ):
            errors.append("PASS requires non-empty bindings.produced_artifact_hashes")

    drift = run.get("drift_status")
    if drift in DRIFT_INVALIDATING or drift not in (None, "NONE"):
        errors.append(f"drift_status {drift} invalidates PASS")

    if verdict_obj.get("free_form_opinion_is_leading") is not False:
        errors.append("free_form_opinion_is_leading must be false")
    return errors


def validate_authority_non_escalation(run: Mapping[str, Any]) -> list[str]:
    """Orchestration PASS never becomes validation / live / capital authority."""
    errors: list[str] = []
    authority = run.get("authority_boundaries")
    if not isinstance(authority, Mapping):
        return ["authority_boundaries must be an object"]
    required_false = (
        "research_apps_validation_authority",
        "hermes_live_authority",
        "hermes_validation_authority",
        "automatic_strategy_promotion",
        "paper_candidate_is_live_go",
        "real_money_go",
        "risk_bypass",
        "orchestration_pass_implies_validation_pass",
    )
    for field in required_false:
        if authority.get(field) is not False:
            errors.append(f"authority_boundaries.{field} must be false")
    safety = run.get("safety_boundaries")
    if isinstance(safety, Mapping):
        if safety.get("lr_status") != "NO-GO":
            errors.append("safety_boundaries.lr_status must be NO-GO")
        if safety.get("productive_agent_execution") is not False:
            errors.append("safety_boundaries.productive_agent_execution must be false")
        if safety.get("productive_db_writes") is not False:
            errors.append("safety_boundaries.productive_db_writes must be false")
    forbidden = run.get("forbidden_actions_attempted")
    if isinstance(forbidden, Sequence) and not isinstance(forbidden, (str, bytes)):
        for action in forbidden:
            if action in FORBIDDEN_ACTIONS or action:
                errors.append(f"forbidden action recorded: {action}")
    return errors


def validate_hermes_orchestration_run(run: Mapping[str, Any]) -> list[str]:
    """Aggregate fail-closed invariants for one orchestration run."""
    errors: list[str] = []
    errors.extend(validate_bindings(run))
    errors.extend(validate_attempt_binding_stability(run))
    errors.extend(validate_attempt_failure_coupling(run))
    errors.extend(validate_failure_verdict_consistency(run))
    errors.extend(validate_retry_policy(run))
    errors.extend(validate_security_gate_blocks_pass(run))
    errors.extend(validate_evidence_and_drift_for_pass(run))
    errors.extend(validate_authority_non_escalation(run))
    return errors


def assert_valid(errors: Sequence[str], *, context: str) -> None:
    if errors:
        joined = "; ".join(errors)
        raise HermesOrchestrationContractError(f"{context}: {joined}")


def hermes_pass_grants_validation_authority(run: Mapping[str, Any]) -> bool:
    """Always False — helper for explicit non-escalation assertions in tests."""
    _ = run
    return False


def hermes_pass_grants_live_authority(run: Mapping[str, Any]) -> bool:
    """Always False — orchestration PASS is never Live-Go."""
    _ = run
    return False
