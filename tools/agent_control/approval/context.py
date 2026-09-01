"""Build schema-valid cdb.pr_approval_context.v1 envelopes (fixture-first)."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.agent_control.approval.codes import (
    AUTHORITY_LIMITS,
    DEFAULT_BASELINE_RELPATH,
    DEFAULT_POLICY_RELPATH,
    DEFAULT_PROMPT_RELPATH,
    DEFAULT_SCHEMA_RELPATH,
    REASON_MISSING_POLICY,
    REASON_MISSING_PROMPT,
    REASON_SCHEMA_INVALID,
    REASON_SECRET_DETECTED,
    SCHEMA_ID,
    SCHEMA_VERSION,
    ApprovalError,
)
from tools.agent_control.approval.digest import attach_context_digest
from tools.agent_control.approval.drift import audit_drift, load_baseline
from tools.agent_control.approval.evaluate import (
    detect_stale_head,
    evaluate_final_head_gates,
    evaluate_recommendation,
    match_required_checks,
    validate_subject,
)
from tools.agent_control.approval.policy import load_policy
from tools.agent_control.approval.prompt import load_prompt
from tools.agent_control.evidence.redact import assert_no_secrets, strip_secrets
from tools.agent_control.paths import REPO_ROOT


@dataclass(frozen=True)
class RepoPaths:
    repo_root: Path
    policy_path: Path
    prompt_path: Path
    baseline_path: Path | None
    schema_path: Path


def default_repo_paths(repo_root: Path | None = None) -> RepoPaths:
    root = repo_root or REPO_ROOT
    return RepoPaths(
        repo_root=root,
        policy_path=root / DEFAULT_POLICY_RELPATH,
        prompt_path=root / DEFAULT_PROMPT_RELPATH,
        baseline_path=root / DEFAULT_BASELINE_RELPATH,
        schema_path=root / DEFAULT_SCHEMA_RELPATH,
    )


def load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_envelope(envelope: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        path = ".".join(str(p) for p in err.path) or "$"
        raise ApprovalError(REASON_SCHEMA_INVALID, f"{path}: {err.message}")


def build_approval_context(
    snapshot: dict[str, Any],
    repo_paths: RepoPaths | None = None,
) -> dict[str, Any]:
    """Pure builder: injected snapshot + repo-backed policy/prompt → envelope.

    No network, no GitHub writes, no file writes. Fail-closed.
    """
    paths = repo_paths or default_repo_paths()
    if not isinstance(snapshot, dict):
        raise ApprovalError(REASON_SCHEMA_INVALID, "snapshot must be a mapping")

    # Redact before any digest / evaluation material is derived.
    cleaned = strip_secrets(copy.deepcopy(snapshot))
    if not isinstance(cleaned, dict):
        raise ApprovalError(REASON_SECRET_DETECTED, "snapshot redaction failed")
    try:
        assert_no_secrets(cleaned)
    except Exception as exc:  # EvidenceError or ApprovalError
        code = getattr(exc, "code", REASON_SECRET_DETECTED)
        raise ApprovalError(str(code), str(getattr(exc, "message", exc))) from exc

    try:
        policy = load_policy(paths.policy_path, repo_root=paths.repo_root)
    except ApprovalError:
        raise
    except OSError as exc:
        raise ApprovalError(REASON_MISSING_POLICY, str(exc)) from exc

    try:
        prompt = load_prompt(paths.prompt_path, repo_root=paths.repo_root)
    except ApprovalError:
        raise
    except OSError as exc:
        raise ApprovalError(REASON_MISSING_PROMPT, str(exc)) from exc

    baseline = load_baseline(paths.baseline_path)
    subject, subject_reasons = validate_subject(cleaned)
    stale_reasons = detect_stale_head(subject, cleaned)
    required_checks, check_reasons = match_required_checks(cleaned, subject)
    final_head_state, final_head_reasons = evaluate_final_head_gates(cleaned, subject)
    extra_codes = cleaned.get("final_head_reason_codes")
    if isinstance(extra_codes, list):
        for code in extra_codes:
            if isinstance(code, str) and code not in final_head_reasons:
                final_head_reasons.append(code)
    drift = audit_drift(
        policy=policy, prompt=prompt, snapshot=cleaned, baseline=baseline
    )
    recommendation, reason_codes, limitations = evaluate_recommendation(
        subject_reasons=subject_reasons,
        check_reasons=check_reasons,
        stale_reasons=stale_reasons,
        final_head_reasons=final_head_reasons,
        drift=drift,
        snapshot=cleaned,
        required_checks=required_checks,
    )

    pr = cleaned.get("pr") if isinstance(cleaned.get("pr"), dict) else {}
    envelope: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "subject": {
            "pr_number": subject.get("pr_number"),
            "head_sha": subject.get("head_sha") or "",
            "base_sha": subject.get("base_sha") or "",
        },
        "recommendation": recommendation,
        "reason_codes": reason_codes,
        "policy": {
            "version": policy["version"],
            "source_path": policy["source_path"],
            "content_sha256": policy["content_sha256"],
        },
        "prompt": {
            "version": prompt["version"],
            "source_path": prompt["source_path"],
            "content_sha256": prompt["content_sha256"],
        },
        "required_checks": required_checks,
        "drift": {
            "status": drift["status"],
            "sources": list(drift.get("sources") or []),
        },
        "pr_state": {
            "is_draft": (
                bool(pr.get("is_draft")) if pr.get("is_draft") is not None else False
            ),
            "review_decision": pr.get("review_decision"),
            "blocking_threads": (
                int(pr["blocking_threads"])
                if isinstance(pr.get("blocking_threads"), int)
                else 0
            ),
        },
        "final_head_state": final_head_state,
        "authority_limits": dict(AUTHORITY_LIMITS),
        "limitations": limitations,
    }

    # Optional non-digest metadata (wall-clock must not affect digest).
    if isinstance(cleaned.get("observed_at"), str):
        envelope["metadata"] = {"observed_at": cleaned["observed_at"]}

    # Authority limits are immutable — re-assert after construction.
    envelope["authority_limits"] = dict(AUTHORITY_LIMITS)

    envelope = attach_context_digest(envelope)

    schema = load_schema(paths.schema_path)
    validate_envelope(envelope, schema)

    # Final hard assert: no route may flip authority limits.
    for key, value in AUTHORITY_LIMITS.items():
        if envelope["authority_limits"].get(key) is not value:
            raise ApprovalError(
                REASON_SCHEMA_INVALID,
                f"authority_limits.{key} must be {value}",
            )
    return envelope
