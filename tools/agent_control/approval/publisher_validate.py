"""Fail-closed acceptance envelope validation before trusted publish (#4505)."""

from __future__ import annotations

import re
from typing import Any

from jsonschema import Draft202012Validator

from tools.agent_control.approval.acceptance_provenance import (
    COMPLETENESS_PRODUCER,
    CONDUCTOR_PRODUCER,
    EVIDENCE_MARKER,
)
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.approval.protection_live_evidence import (
    PRODUCER as PROTECTION_PRODUCER,
)
from tools.agent_control.approval.producer_trust import load_producer_trust_policy

SHA40 = re.compile(r"^[a-f0-9]{40}$")

ALLOWED_PUBLISH_PRODUCERS = frozenset(
    {
        COMPLETENESS_PRODUCER,
        CONDUCTOR_PRODUCER,
        PROTECTION_PRODUCER,
    }
)


def _normalize_sha(value: Any) -> str:
    if isinstance(value, str) and SHA40.match(value.lower()):
        return value.lower()
    return ""


def _completeness_subschema_validator(schema: dict[str, Any]) -> Draft202012Validator:
    defs = schema.get("$defs") if isinstance(schema.get("$defs"), dict) else {}
    comp_schema = {
        "allOf": [
            {"$ref": "#/$defs/CommonEnvelopeBase"},
            {
                "type": "object",
                "properties": {
                    "producer": {"const": COMPLETENESS_PRODUCER},
                    "result": {"$ref": "#/$defs/CompletenessReviewResult"},
                },
            },
        ],
        "$defs": defs,
    }
    return Draft202012Validator(comp_schema)


def _conductor_subschema_validator(schema: dict[str, Any]) -> Draft202012Validator:
    defs = schema.get("$defs") if isinstance(schema.get("$defs"), dict) else {}
    cond_schema = {
        "allOf": [
            {"$ref": "#/$defs/CommonEnvelopeBase"},
            {
                "type": "object",
                "properties": {
                    "producer": {"const": CONDUCTOR_PRODUCER},
                    "result": {"$ref": "#/$defs/BatchMergeConductorResult"},
                },
            },
        ],
        "$defs": defs,
    }
    return Draft202012Validator(cond_schema)


def _semantic_completeness_checks(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if envelope.get("run_status") != "COMPLETE":
        errors.append("run_status must be COMPLETE")
    lifecycle = (
        envelope.get("lifecycle") if isinstance(envelope.get("lifecycle"), dict) else {}
    )
    if lifecycle.get("state") != "MERGE_CANDIDATE":
        errors.append("lifecycle.state must be MERGE_CANDIDATE")
    result = envelope.get("result") if isinstance(envelope.get("result"), dict) else {}
    if result.get("verdict") != "MERGE_CANDIDATE":
        errors.append("result.verdict must be MERGE_CANDIDATE")
    decision = (
        envelope.get("decision") if isinstance(envelope.get("decision"), dict) else {}
    )
    block_codes = decision.get("block_codes")
    if isinstance(block_codes, list) and block_codes:
        errors.append(
            "decision.block_codes must be empty for positive completeness handoff"
        )
    return errors


def _semantic_conductor_checks(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if envelope.get("run_status") != "COMPLETE":
        errors.append("run_status must be COMPLETE")
    lifecycle = (
        envelope.get("lifecycle") if isinstance(envelope.get("lifecycle"), dict) else {}
    )
    if lifecycle.get("state") != "FINAL_HEAD_READY_FOR_APPROVAL":
        errors.append("lifecycle.state must be FINAL_HEAD_READY_FOR_APPROVAL")
    result = envelope.get("result") if isinstance(envelope.get("result"), dict) else {}
    if result.get("phase") != "HANDOFF_APPROVAL":
        errors.append("result.phase must be HANDOFF_APPROVAL")
    block_codes = result.get("block_codes")
    if isinstance(block_codes, list) and block_codes:
        errors.append("result.block_codes must be empty for positive conductor handoff")
    if result.get("success_decision") != "FINAL_HEAD_READY_FOR_APPROVAL":
        errors.append("result.success_decision must be FINAL_HEAD_READY_FOR_APPROVAL")
    return errors


def verify_trust_policy_publisher_binding(
    *,
    publisher_app_slug: str,
    repo_root: Any,
    declared_producer: str | None = None,
) -> None:
    """Ensure trust allowlists only reference the canonical publisher app slug."""
    policy = load_producer_trust_policy(repo_root)
    producers = (
        policy.get("producers") if isinstance(policy.get("producers"), dict) else {}
    )
    if declared_producer is not None and declared_producer not in producers:
        raise ApprovalError(
            "APPROVAL_TRUST_POLICY_UNBOUND",
            f"declared producer {declared_producer!r} missing from trust policy",
        )
    names = [name for name in ALLOWED_PUBLISH_PRODUCERS if name in producers]
    for name in names:
        rules = producers.get(name) if isinstance(producers.get(name), dict) else {}
        slugs = rules.get("trusted_github_app_slugs") or []
        if not isinstance(slugs, list):
            raise ApprovalError(
                "APPROVAL_TRUST_POLICY_INVALID",
                f"{name} trusted_github_app_slugs must be a list",
            )
        extra = [slug for slug in slugs if slug != publisher_app_slug]
        if extra:
            raise ApprovalError(
                "APPROVAL_TRUST_SELF_GOVERNANCE",
                f"{name} trust slugs {extra!r} do not match publisher app "
                f"{publisher_app_slug!r}",
            )
        if publisher_app_slug not in slugs:
            raise ApprovalError(
                "APPROVAL_TRUST_POLICY_UNBOUND",
                f"{name} missing publisher slug {publisher_app_slug!r}",
            )


def assert_producer_allowed_by_bootstrap(
    bootstrap: dict[str, Any],
    declared_producer: str,
) -> None:
    """Fail closed when producer is outside bootstrap allowlist."""
    allowed = bootstrap.get("allowed_producers")
    if not isinstance(allowed, list):
        raise ApprovalError(
            "APPROVAL_PUBLISH_INVALID", "bootstrap allowed_producers missing"
        )
    if declared_producer not in allowed:
        raise ApprovalError(
            "APPROVAL_PUBLISH_PRODUCER_FORBIDDEN",
            f"producer {declared_producer!r} not allowed by bootstrap",
        )
    if declared_producer not in ALLOWED_PUBLISH_PRODUCERS:
        raise ApprovalError(
            "APPROVAL_PUBLISH_PRODUCER_FORBIDDEN",
            f"unknown producer {declared_producer!r}",
        )


def validate_envelope_for_publish(
    envelope: dict[str, Any],
    *,
    declared_producer: str,
    repository: str,
    pr_number: int,
    live_head_sha: str,
    live_base_sha: str,
    schema: dict[str, Any],
    bootstrap: dict[str, Any],
) -> None:
    """Confused-deputy-safe validation; raises ApprovalError on any violation."""
    assert_producer_allowed_by_bootstrap(bootstrap, declared_producer)

    env_producer = envelope.get("producer")
    if env_producer != declared_producer:
        raise ApprovalError(
            "APPROVAL_PUBLISH_PRODUCER_MISMATCH",
            f"envelope producer {env_producer!r} != declared {declared_producer!r}",
        )

    if declared_producer == COMPLETENESS_PRODUCER:
        sub_errors = sorted(
            _completeness_subschema_validator(schema).iter_errors(envelope),
            key=lambda e: list(e.path),
        )
        if sub_errors:
            err = sub_errors[0]
            path = ".".join(str(p) for p in err.path) or "$"
            raise ApprovalError(
                "APPROVAL_PUBLISH_SCHEMA_INVALID",
                f"completeness subschema {path}: {err.message}",
            )
        sem = _semantic_completeness_checks(envelope)
        if sem:
            raise ApprovalError("APPROVAL_PUBLISH_SEMANTIC_INVALID", "; ".join(sem))
    elif declared_producer == CONDUCTOR_PRODUCER:
        sub_errors = sorted(
            _conductor_subschema_validator(schema).iter_errors(envelope),
            key=lambda e: list(e.path),
        )
        if sub_errors:
            err = sub_errors[0]
            path = ".".join(str(p) for p in err.path) or "$"
            raise ApprovalError(
                "APPROVAL_PUBLISH_SCHEMA_INVALID",
                f"conductor subschema {path}: {err.message}",
            )
        sem = _semantic_conductor_checks(envelope)
        if sem:
            raise ApprovalError("APPROVAL_PUBLISH_SEMANTIC_INVALID", "; ".join(sem))

    subject = (
        envelope.get("subject") if isinstance(envelope.get("subject"), dict) else {}
    )
    subj_repo = subject.get("repository")
    subj_pr = subject.get("pr_number")
    subj_head = _normalize_sha(subject.get("head_sha"))
    subj_base = _normalize_sha(subject.get("base_sha"))
    head = _normalize_sha(live_head_sha)
    base = _normalize_sha(live_base_sha)

    if subj_repo != repository:
        raise ApprovalError(
            "APPROVAL_PUBLISH_SUBJECT_MISMATCH",
            f"subject.repository {subj_repo!r} != live {repository!r}",
        )
    if not isinstance(subj_pr, int) or subj_pr != pr_number:
        raise ApprovalError(
            "APPROVAL_PUBLISH_SUBJECT_MISMATCH",
            f"subject.pr_number {subj_pr!r} != live {pr_number}",
        )
    if subj_head != head:
        raise ApprovalError(
            "APPROVAL_PUBLISH_SUBJECT_MISMATCH",
            f"subject.head_sha != live head {head}",
        )
    if subj_base != base:
        raise ApprovalError(
            "APPROVAL_PUBLISH_SUBJECT_MISMATCH",
            f"subject.base_sha != live base {base}",
        )

    if (
        envelope.get("evidence_marker")
        and envelope.get("evidence_marker") != EVIDENCE_MARKER
    ):
        raise ApprovalError(
            "APPROVAL_PUBLISH_SCHEMA_INVALID", "invalid evidence_marker"
        )


def format_acceptance_comment_body(envelope: dict[str, Any]) -> str:
    import json

    payload = json.dumps(envelope, indent=2, ensure_ascii=False, sort_keys=True)
    return f"{EVIDENCE_MARKER}\n\n```json\n{payload}\n```\n"
