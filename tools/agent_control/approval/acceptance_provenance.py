"""Fail-closed Final-Head handoff provenance from PR acceptance evidence (#4505)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.codes import (
    REASON_ACCEPTING_SLICES,
    REASON_COMPLETENESS_SUBJECT_MISMATCH,
    REASON_FINAL_HEAD_NOT_FROZEN,
    REASON_FINAL_HEAD_NOT_READY,
    REASON_HANDOFF_BASE_MISMATCH,
    REASON_HANDOFF_HEAD_MISMATCH,
    REASON_HANDOFF_PROVENANCE_INCOMPLETE,
    REASON_HANDOFF_SCHEMA_INVALID,
    REASON_MERGE_CANDIDATE_WITHOUT_FINAL_HEAD,
    REASON_MISSING_FINAL_HEAD_STATE,
    REASON_SELF_DECLARED_PRODUCER_REJECTED,
    REASON_UNTRUSTED_HANDOFF,
    ApprovalError,
)
from tools.agent_control.approval.producer_trust import (
    load_producer_trust_policy,
    producer_actor_trusted,
)
from tools.agent_control.paths import REPO_ROOT

EVIDENCE_MARKER = "<!-- cdb-pr-acceptance:v1 -->"
ACCEPTANCE_SCHEMA_RELPATH = "docs/contracts/pr_acceptance_skill_family.v1.schema.json"
CONDUCTOR_PRODUCER = "cdb-batch-merge-conductor"
COMPLETENESS_PRODUCER = "cdb-pr-completeness-review"
SHA40 = re.compile(r"^[a-f0-9]{40}$")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass(frozen=True)
class FinalHeadProvenance:
    trusted: bool
    final_head_ready_for_approval: bool
    steward_state: str | None
    acceptance_lifecycle_state: str | None
    bound_final_head_sha: str
    completeness_verdict: str | None
    risk: str
    reason_codes: tuple[str, ...]
    validation_errors: tuple[str, ...] = ()
    conductor_comment_id: int | None = None
    completeness_comment_id: int | None = None
    envelope_digest: str | None = None

    def to_snapshot_final_head(self) -> dict[str, Any]:
        return {
            "steward_state": self.steward_state,
            "acceptance_lifecycle_state": self.acceptance_lifecycle_state,
            "final_head_ready_for_approval": self.final_head_ready_for_approval,
            "bound_final_head_sha": self.bound_final_head_sha or "",
            "completeness_verdict": self.completeness_verdict,
            "risk": self.risk,
            "provenance": {
                "trusted": self.trusted,
                "envelope_digest": self.envelope_digest,
                "conductor_comment_id": self.conductor_comment_id,
                "completeness_comment_id": self.completeness_comment_id,
                "validation_errors": list(self.validation_errors),
            },
        }


def load_acceptance_schema(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    path = root / ACCEPTANCE_SCHEMA_RELPATH
    if not path.is_file():
        raise ApprovalError(
            "APPROVAL_SCHEMA_INVALID", f"missing acceptance schema: {path}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _envelope_digest(envelope: dict[str, Any]) -> str:
    material = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def extract_json_envelopes(text: str) -> list[dict[str, Any]]:
    """Extract JSON object envelopes from comment/body text (marker required)."""
    if EVIDENCE_MARKER not in text:
        return []
    out: list[dict[str, Any]] = []
    for match in _JSON_FENCE_RE.finditer(text):
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    # Bare JSON after marker (single object)
    if not out:
        idx = text.find(EVIDENCE_MARKER)
        tail = text[idx + len(EVIDENCE_MARKER) :].strip()
        if tail.startswith("{"):
            try:
                parsed = json.loads(tail)
                if isinstance(parsed, dict):
                    out.append(parsed)
            except json.JSONDecodeError:
                pass
    return out


def validate_acceptance_envelope(
    envelope: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
    if not errors:
        return []
    err = errors[0]
    path = ".".join(str(p) for p in err.path) or "$"
    return [f"{path}: {err.message}"]


def _normalize_sha(value: Any) -> str:
    if isinstance(value, str) and SHA40.match(value.lower()):
        return value.lower()
    return ""


def _is_conductor_ready(envelope: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if envelope.get("producer") != CONDUCTOR_PRODUCER:
        return False, ["producer is not cdb-batch-merge-conductor"]
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
    if result.get("success_decision") != "FINAL_HEAD_READY_FOR_APPROVAL":
        errors.append("result.success_decision must be FINAL_HEAD_READY_FOR_APPROVAL")
    if result.get("handoff_role") != "cdb_final_head_pr_approval_gate":
        errors.append("result.handoff_role must be cdb_final_head_pr_approval_gate")
    block_codes = result.get("block_codes")
    if isinstance(block_codes, list) and block_codes:
        errors.append("result.block_codes must be empty")
    return len(errors) == 0, errors


def _steward_state_reason(steward_state: str | None) -> str | None:
    """Return blocking reason when steward_state is not exactly frozen."""
    if steward_state == "frozen":
        return None
    if steward_state == "accepting_slices":
        return REASON_ACCEPTING_SLICES
    return REASON_FINAL_HEAD_NOT_FROZEN


def _completeness_subject_matches(
    subject: dict[str, Any],
    *,
    pr_number: int,
    repository: str,
    head_sha: str,
    base_sha: str,
) -> bool:
    subj_head = _normalize_sha(subject.get("head_sha"))
    subj_base = _normalize_sha(subject.get("base_sha"))
    subj_pr = subject.get("pr_number")
    subj_repo = subject.get("repository")
    return (
        subj_head == head_sha
        and subj_base == base_sha
        and isinstance(subj_pr, int)
        and subj_pr == pr_number
        and isinstance(subj_repo, str)
        and subj_repo == repository
    )


def _is_completeness_semantically_green(
    envelope: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if envelope.get("run_status") != "COMPLETE":
        errors.append(
            f"run_status must be COMPLETE, got {envelope.get('run_status')!r}"
        )
    lifecycle = (
        envelope.get("lifecycle") if isinstance(envelope.get("lifecycle"), dict) else {}
    )
    if lifecycle.get("state") != "MERGE_CANDIDATE":
        errors.append("lifecycle.state must be MERGE_CANDIDATE")
    result = envelope.get("result") if isinstance(envelope.get("result"), dict) else {}
    if result.get("verdict") != "MERGE_CANDIDATE":
        errors.append("result.verdict must be MERGE_CANDIDATE")
    return len(errors) == 0, errors


def _find_completeness_merge_candidate(
    envelopes: list[dict[str, Any]], *, head_sha: str
) -> dict[str, Any] | None:
    """Legacy helper retained for direct envelope-list tests."""
    head = _normalize_sha(head_sha)
    for envelope in reversed(envelopes):
        if envelope.get("producer") != COMPLETENESS_PRODUCER:
            continue
        schema_errors = validate_acceptance_envelope(envelope, load_acceptance_schema())
        if schema_errors:
            continue
        green, _ = _is_completeness_semantically_green(envelope)
        if not green:
            return None
        subject = (
            envelope.get("subject") if isinstance(envelope.get("subject"), dict) else {}
        )
        subj_head = _normalize_sha(subject.get("head_sha"))
        if subj_head and subj_head == head:
            return envelope
    return None


def _resolve_latest_completeness_envelope(
    all_envelopes: list[tuple[CommentRecord, dict[str, Any]]],
    *,
    pr_number: int,
    repository: str,
    head: str,
    base: str,
    schema: dict[str, Any],
    trust_policy: dict[str, Any],
    repo_root: Path | None,
) -> tuple[
    dict[str, Any] | None,
    CommentRecord | None,
    str | None,
    list[str],
    list[str],
]:
    """Resolve latest trusted completeness envelope; never fall back to older green."""
    reasons: list[str] = []
    validation_errors: list[str] = []
    latest: tuple[CommentRecord, dict[str, Any]] | None = None

    for comment, envelope in reversed(all_envelopes):
        if envelope.get("producer") != COMPLETENESS_PRODUCER:
            continue
        actor_ok, actor_detail = producer_actor_trusted(
            producer=COMPLETENESS_PRODUCER,
            comment=comment,
            trust_policy=trust_policy,
            repo_root=repo_root,
        )
        if not actor_ok:
            validation_errors.append(f"completeness actor untrusted: {actor_detail}")
            continue
        latest = (comment, envelope)
        break

    if latest is None:
        reasons.append(REASON_HANDOFF_PROVENANCE_INCOMPLETE)
        validation_errors.append(
            "missing trusted completeness envelope for live head/base"
        )
        return None, None, None, reasons, validation_errors

    comment, envelope = latest
    comp_errors = validate_acceptance_envelope(envelope, schema)
    if comp_errors:
        validation_errors.extend(comp_errors)
        reasons.append(REASON_HANDOFF_SCHEMA_INVALID)
        return None, comment, None, reasons, validation_errors
    subject = (
        envelope.get("subject") if isinstance(envelope.get("subject"), dict) else {}
    )
    if not _completeness_subject_matches(
        subject,
        pr_number=pr_number,
        repository=repository,
        head_sha=head,
        base_sha=base,
    ):
        reasons.append(REASON_COMPLETENESS_SUBJECT_MISMATCH)
        validation_errors.append(
            "completeness subject must match live repository/pr/head/base exactly"
        )
        return None, comment, None, reasons, validation_errors

    green, sem_errors = _is_completeness_semantically_green(envelope)
    result = envelope.get("result") if isinstance(envelope.get("result"), dict) else {}
    verdict = result.get("verdict")
    completeness_verdict = str(verdict) if isinstance(verdict, str) else None
    if not green:
        validation_errors.extend(sem_errors)
        reasons.append(REASON_FINAL_HEAD_NOT_READY)
        validation_errors.append(
            f"latest completeness envelope is not semantically green "
            f"(verdict={completeness_verdict!r})"
        )
        return envelope, comment, completeness_verdict, reasons, validation_errors

    return envelope, comment, completeness_verdict, reasons, validation_errors


def resolve_final_head_provenance(
    *,
    comments: list[CommentRecord],
    pr_number: int,
    repository: str,
    live_head_sha: str,
    live_base_sha: str,
    steward_state: str | None,
    schema: dict[str, Any] | None = None,
    trust_policy: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> FinalHeadProvenance:
    """Validate trusted Conductor handoff; never trust self-declared producer alone."""
    schema = schema or load_acceptance_schema(repo_root)
    trust_policy = trust_policy or load_producer_trust_policy(repo_root)
    head = _normalize_sha(live_head_sha)
    base = _normalize_sha(live_base_sha)
    reasons: list[str] = []
    validation_errors: list[str] = []

    if steward_state == "accepting_slices":
        reasons.append(REASON_ACCEPTING_SLICES)
    else:
        steward_reason = _steward_state_reason(steward_state)
        if steward_reason and steward_reason != REASON_ACCEPTING_SLICES:
            reasons.append(steward_reason)

    all_envelopes: list[tuple[CommentRecord, dict[str, Any]]] = []
    for comment in comments:
        for envelope in extract_json_envelopes(comment.body):
            all_envelopes.append((comment, envelope))

    if not all_envelopes:
        reasons.append(REASON_MISSING_FINAL_HEAD_STATE)
        return FinalHeadProvenance(
            trusted=False,
            final_head_ready_for_approval=False,
            steward_state=steward_state,
            acceptance_lifecycle_state=None,
            bound_final_head_sha=head,
            completeness_verdict=None,
            risk="UNKNOWN",
            reason_codes=tuple(_dedupe(reasons)),
            validation_errors=tuple(["no acceptance envelopes with marker"]),
        )

    conductor_pair: tuple[CommentRecord, dict[str, Any]] | None = None
    for comment, envelope in reversed(all_envelopes):
        producer = envelope.get("producer")
        if producer != CONDUCTOR_PRODUCER:
            continue
        actor_ok, actor_detail = producer_actor_trusted(
            producer=CONDUCTOR_PRODUCER,
            comment=comment,
            trust_policy=trust_policy,
            repo_root=repo_root,
        )
        if not actor_ok:
            validation_errors.append(f"conductor actor untrusted: {actor_detail}")
            continue
        schema_errors = validate_acceptance_envelope(envelope, schema)
        if schema_errors:
            validation_errors.extend(schema_errors)
            reasons.append(REASON_HANDOFF_SCHEMA_INVALID)
            continue
        ready, sem_errors = _is_conductor_ready(envelope)
        if not ready:
            validation_errors.extend(sem_errors)
            reasons.append(REASON_UNTRUSTED_HANDOFF)
            continue
        conductor_pair = (comment, envelope)
        break

    if conductor_pair is None:
        reasons.append(REASON_FINAL_HEAD_NOT_READY)
        if any("conductor actor untrusted" in err for err in validation_errors):
            reasons.append(REASON_UNTRUSTED_HANDOFF)
        if not validation_errors:
            validation_errors.append(
                "no trusted schema-valid conductor handoff envelope"
            )
        return FinalHeadProvenance(
            trusted=False,
            final_head_ready_for_approval=False,
            steward_state=steward_state,
            acceptance_lifecycle_state=None,
            bound_final_head_sha=head,
            completeness_verdict=None,
            risk="UNKNOWN",
            reason_codes=tuple(_dedupe(reasons)),
            validation_errors=tuple(validation_errors),
        )

    comment, conductor = conductor_pair
    comment_id = comment.comment_id
    subject = (
        conductor.get("subject") if isinstance(conductor.get("subject"), dict) else {}
    )
    bound_head = _normalize_sha(subject.get("head_sha"))
    bound_base = _normalize_sha(subject.get("base_sha"))
    subj_pr = subject.get("pr_number")
    subj_repo = subject.get("repository")

    if not bound_head or bound_head != head:
        reasons.append(REASON_HANDOFF_HEAD_MISMATCH)
        validation_errors.append(
            f"conductor subject.head_sha {bound_head!r} != live {head!r}"
        )
    if not bound_base or bound_base != base:
        reasons.append(REASON_HANDOFF_BASE_MISMATCH)
        validation_errors.append(
            f"conductor subject.base_sha {bound_base!r} != live {base!r}"
        )
    if isinstance(subj_pr, int) and subj_pr != pr_number:
        reasons.append(REASON_HANDOFF_HEAD_MISMATCH)
        validation_errors.append(
            f"conductor subject.pr_number {subj_pr} != {pr_number}"
        )
    if isinstance(subj_repo, str) and subj_repo and subj_repo != repository:
        reasons.append(REASON_UNTRUSTED_HANDOFF)
        validation_errors.append("conductor subject.repository mismatch")

    (
        completeness,
        completeness_comment,
        completeness_verdict,
        comp_reasons,
        comp_errors,
    ) = _resolve_latest_completeness_envelope(
        all_envelopes,
        pr_number=pr_number,
        repository=repository,
        head=head,
        base=base,
        schema=schema,
        trust_policy=trust_policy,
        repo_root=repo_root,
    )
    reasons.extend(comp_reasons)
    validation_errors.extend(comp_errors)
    completeness_comment_id = (
        completeness_comment.comment_id if completeness_comment is not None else None
    )

    lifecycle = (
        conductor.get("lifecycle")
        if isinstance(conductor.get("lifecycle"), dict)
        else {}
    )
    lifecycle_state = lifecycle.get("state")
    completeness_green = (
        completeness is not None
        and _is_completeness_semantically_green(completeness)[0]
    )
    trusted = (
        REASON_HANDOFF_HEAD_MISMATCH not in reasons
        and REASON_HANDOFF_BASE_MISMATCH not in reasons
        and REASON_HANDOFF_PROVENANCE_INCOMPLETE not in reasons
        and REASON_HANDOFF_SCHEMA_INVALID not in reasons
        and REASON_UNTRUSTED_HANDOFF not in reasons
        and REASON_ACCEPTING_SLICES not in reasons
        and REASON_FINAL_HEAD_NOT_FROZEN not in reasons
        and REASON_COMPLETENESS_SUBJECT_MISMATCH not in reasons
        and REASON_FINAL_HEAD_NOT_READY not in reasons
        and steward_state == "frozen"
        and lifecycle_state == "FINAL_HEAD_READY_FOR_APPROVAL"
        and completeness_green
    )
    final_ready = trusted and bound_head == head and bound_base == base

    if not final_ready and REASON_FINAL_HEAD_NOT_READY not in reasons:
        if REASON_MISSING_FINAL_HEAD_STATE not in reasons:
            reasons.append(REASON_FINAL_HEAD_NOT_READY)

    return FinalHeadProvenance(
        trusted=trusted,
        final_head_ready_for_approval=final_ready,
        steward_state=steward_state,
        acceptance_lifecycle_state=(
            str(lifecycle_state) if lifecycle_state is not None else None
        ),
        bound_final_head_sha=bound_head or head,
        completeness_verdict=completeness_verdict,
        risk="LOW" if final_ready else "UNKNOWN",
        reason_codes=tuple(_dedupe(reasons)),
        validation_errors=tuple(validation_errors),
        conductor_comment_id=comment_id,
        completeness_comment_id=completeness_comment_id,
        envelope_digest=_envelope_digest(conductor),
    )


def reject_self_declared_producer(
    envelope: dict[str, Any], schema: dict[str, Any]
) -> bool:
    """True when producer string exists but schema validation fails (forged handoff)."""
    if "producer" not in envelope:
        return False
    return bool(validate_acceptance_envelope(envelope, schema))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
