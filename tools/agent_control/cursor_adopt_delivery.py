"""Adopt an external Cursor Cloud GitHub delivery into the ACP pilot (#4258).

Read-only toward Cursor and the source PR. Never creates Cursor agents/runs,
never posts to Cursor create/resume endpoints, never mutates the evidence PR.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from tools.agent_control.errors import AgentControlError
from tools.agent_control.evidence.redact import assert_no_secrets, strip_secrets
from tools.agent_control.paths import REPO_ROOT
from tools.agent_execution_contract.jcs import canonicalize_bytes

SCHEMA_ID = "cdb.cursor_delivery_adoption.v1"
SCHEMA_VERSION = "1.0.0"
SCHEMA_RELPATH = "docs/contracts/cdb_cursor_delivery_adoption.v1.schema.json"
DIGEST_PREFIX = "sha256:"
SHA40 = re.compile(r"^[a-f0-9]{40}$")
AGENT_ID_RE = re.compile(r"^bc-[0-9a-fA-F-]{36}$")
CURSOR_AUTHOR_LOGIN = "cursoragent"
CURSOR_AUTHOR_EMAIL = "cursoragent@cursor.com"

AUTHORITY_LIMITS: dict[str, bool] = {
    "merge": False,
    "approval": False,
    "live": False,
    "runtime_mutation": False,
    "github_delivery_create": False,
    "cursor_http_posts": False,
    "publish_cdb_local_ci": False,
}

DEFAULT_LIMITATIONS = [
    "external_delivery_not_cdb_dispatch",
    "provider_dispatch_proven_false",
    "not_full_e2e_chain",
    "not_issue_closure",
    "not_final_ci",
    "not_merge_authority",
    "not_approval_authority",
    "hosted_checks_are_github_snapshot_only",
    "refs_4258_not_closes",
    "lr_no_go",
]

# Prior failed CDB Cursor runs for #4258 — immutable references only.
IMMUTABLE_FAILED_RUN_IDS = (
    "run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b",
    "run-c2c3898b-af9e-4f73-ad91-830f600561b9",
)

GhRunner = Callable[[list[str]], dict[str, Any]]
_NON_DIGEST_KEYS = frozenset(
    {"observed_at", "snapshot_observed_at", "wall_clock", "metadata"}
)


class CursorAdoptError(AgentControlError):
    """Fail-closed adoption / provenance error."""


def _default_gh_runner(argv: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise CursorAdoptError(
            "ADOPT_GITHUB_QUERY_FAILED",
            (completed.stderr or completed.stdout or "gh failed")[:500],
        )
    if not (completed.stdout or "").strip():
        return {}
    return json.loads(completed.stdout)


def _strip_digest_fields(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    payload.pop("canonical_digest", None)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity = dict(integrity)
        integrity.pop("digest", None)
        if integrity:
            payload["integrity"] = integrity
        else:
            payload.pop("integrity", None)
    for key in _NON_DIGEST_KEYS:
        payload.pop(key, None)
    return payload


def compute_adoption_digest(receipt: dict[str, Any]) -> str:
    material = canonicalize_bytes(_strip_digest_fields(receipt))
    return f"{DIGEST_PREFIX}{hashlib.sha256(material).hexdigest()}"


def attach_adoption_digest(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    integrity = dict(payload.get("integrity") or {})
    integrity["canonicalization"] = "RFC8785"
    integrity["digest_algorithm"] = "sha256"
    integrity["digest_encoding"] = "sha256:<lowercase-hex>"
    payload["integrity"] = integrity
    integrity.pop("digest", None)
    digest = compute_adoption_digest(payload)
    payload["integrity"]["digest"] = digest
    payload["canonical_digest"] = digest
    return payload


def derive_adoption_id(bindings: dict[str, Any]) -> str:
    material = canonicalize_bytes(bindings)
    digest = hashlib.sha256(material).hexdigest()
    return f"cad-{digest[:24]}"


def derive_adopted_delivery_id(bindings: dict[str, Any]) -> str:
    material = canonicalize_bytes(bindings)
    digest = hashlib.sha256(material).hexdigest()
    return f"add-{digest[:24]}"


def load_adoption_schema(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    path = root / SCHEMA_RELPATH
    return json.loads(path.read_text(encoding="utf-8"))


def validate_adoption_receipt(
    receipt: dict[str, Any], *, repo_root: Path | None = None
) -> None:
    schema = load_adoption_schema(repo_root)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(receipt), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        path = ".".join(str(p) for p in err.path) or "$"
        raise CursorAdoptError("ADOPT_SCHEMA_INVALID", f"{path}: {err.message}")
    assert_no_secrets(receipt)
    for key, expected in AUTHORITY_LIMITS.items():
        if receipt.get("authority_limits", {}).get(key) is not expected:
            raise CursorAdoptError(
                "ADOPT_AUTHORITY_LIMIT_VIOLATION",
                f"authority_limits.{key} must be {expected}",
            )
    if receipt.get("provider_dispatch_proven") is True:
        raise CursorAdoptError(
            "ADOPT_DISPATCH_CLAIM_FORBIDDEN",
            "external adoption must not claim provider_dispatch_proven=true",
        )
    expected = compute_adoption_digest(receipt)
    if receipt.get("canonical_digest") != expected:
        raise CursorAdoptError(
            "ADOPT_DIGEST_MISMATCH",
            "canonical_digest does not match RFC8785/SHA-256 material",
        )


def _agent_ref_in_text(text: str | None, agent_id: str) -> bool:
    if not text:
        return False
    return agent_id in text


def _classify_hosted_checks(rollup: list[Any] | None) -> str | None:
    if not isinstance(rollup, list) or not rollup:
        return None
    conclusions = []
    for item in rollup:
        if not isinstance(item, dict):
            continue
        conclusions.append(str(item.get("conclusion") or "").upper())
    if conclusions and all(c == "SUCCESS" for c in conclusions):
        return "all_success"
    if any(c in {"FAILURE", "CANCELLED", "TIMED_OUT"} for c in conclusions):
        return "has_failure"
    return "mixed_or_incomplete"


def verify_cursor_cloud_delivery(
    *,
    repository: str,
    cursor_agent_id: str,
    delivery_pr: int,
    expected_head: str,
    expected_branch: str | None = None,
    runner: GhRunner | None = None,
) -> dict[str, Any]:
    """Live-verify Cursor Cloud GitHub delivery provenance (read-only gh)."""
    run = runner or _default_gh_runner
    if not repository or "/" not in repository:
        raise CursorAdoptError("ADOPT_REPO_INVALID", "repository must be owner/name")
    if not AGENT_ID_RE.match(cursor_agent_id):
        raise CursorAdoptError(
            "ADOPT_AGENT_ID_INVALID",
            "cursor_agent_id must match bc-<uuid>",
        )
    if not SHA40.match(expected_head):
        raise CursorAdoptError(
            "ADOPT_HEAD_INVALID", "expected_head must be 40-hex lowercase"
        )

    pr = run(
        [
            "gh",
            "pr",
            "view",
            str(delivery_pr),
            "--repo",
            repository,
            "--json",
            "number,state,title,body,headRefOid,baseRefOid,headRefName,"
            "baseRefName,url,author,commits,statusCheckRollup,isDraft,mergeable",
        ]
    )
    pr_head = pr.get("headRefOid")
    pr_branch = pr.get("headRefName")
    body = pr.get("body") if isinstance(pr.get("body"), str) else ""
    if not isinstance(pr_head, str) or not SHA40.match(pr_head):
        raise CursorAdoptError(
            "HOLD_CURSOR_DELIVERY_PROVENANCE_INSUFFICIENT",
            "PR head SHA missing or invalid",
        )
    if pr_head != expected_head:
        raise CursorAdoptError(
            "ADOPT_HEAD_DRIFT",
            f"PR head {pr_head} != expected_head {expected_head}",
        )
    if expected_branch and pr_branch != expected_branch:
        raise CursorAdoptError(
            "ADOPT_BRANCH_MISMATCH",
            f"PR branch {pr_branch} != expected_branch {expected_branch}",
        )

    # Branch tip must exist and match head (no phantom branch).
    branch_name = expected_branch or (pr_branch if isinstance(pr_branch, str) else None)
    if not branch_name:
        raise CursorAdoptError(
            "HOLD_CURSOR_DELIVERY_PROVENANCE_INSUFFICIENT",
            "branch name missing",
        )
    branch_ref = run(
        [
            "gh",
            "api",
            f"repos/{repository}/git/ref/heads/{branch_name}",
        ]
    )
    tip = (branch_ref.get("object") or {}).get("sha")
    if tip != expected_head:
        raise CursorAdoptError(
            "ADOPT_PHANTOM_OR_DRIFT_BRANCH",
            f"branch tip {tip} != expected_head {expected_head}",
        )

    commit = run(
        [
            "gh",
            "api",
            f"repos/{repository}/commits/{expected_head}",
        ]
    )
    author = commit.get("author") if isinstance(commit.get("author"), dict) else {}
    commit_author = (
        (commit.get("commit") or {}).get("author")
        if isinstance((commit.get("commit") or {}).get("author"), dict)
        else {}
    )
    author_login = author.get("login")
    author_email = commit_author.get("email")
    commit_agent_match = (
        author_login == CURSOR_AUTHOR_LOGIN and author_email == CURSOR_AUTHOR_EMAIL
    )
    pr_body_agent_ref = _agent_ref_in_text(body, cursor_agent_id)
    # Footer-only without commit author match is insufficient.
    if pr_body_agent_ref and not commit_agent_match:
        raise CursorAdoptError(
            "HOLD_CURSOR_DELIVERY_PROVENANCE_INSUFFICIENT",
            "PR agent ref present but commit lacks cursoragent provenance",
        )
    if not pr_body_agent_ref:
        raise CursorAdoptError(
            "HOLD_CURSOR_DELIVERY_PROVENANCE_INSUFFICIENT",
            "PR body does not bind cursor_agent_id",
        )
    if not commit_agent_match:
        raise CursorAdoptError(
            "HOLD_CURSOR_DELIVERY_PROVENANCE_INSUFFICIENT",
            "commit author is not cursoragent",
        )

    coauthors: list[str] = []
    message = ((commit.get("commit") or {}).get("message")) or ""
    for line in str(message).splitlines():
        if line.lower().startswith("co-authored-by:"):
            coauthors.append(line.split(":", 1)[1].strip())

    hosted = _classify_hosted_checks(pr.get("statusCheckRollup"))
    return {
        "pr": pr,
        "branch_name": branch_name,
        "pr_body_agent_ref_present": pr_body_agent_ref,
        "commit_agent_author_match": commit_agent_match,
        "author_login": author_login,
        "author_email": author_email,
        "coauthors": coauthors,
        "hosted_checks_snapshot": hosted,
        "branch_exists": True,
        "commit_exists": True,
        "pr_exists": True,
        "pr_head_matches_expected": True,
        "branch_tip_matches_expected": True,
    }


def build_adoption_receipt(
    *,
    issue_number: int,
    repository: str,
    cursor_agent_id: str,
    delivery_pr: int,
    expected_head: str,
    expected_branch: str | None = None,
    owner_coauthor_login: str | None = "jannekbuengener",
    original_cdb_run_ids: list[str] | None = None,
    verification: dict[str, Any] | None = None,
    runner: GhRunner | None = None,
    repo_root: Path | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Verify delivery (unless verification injected) and build adoption receipt."""
    verified = verification or verify_cursor_cloud_delivery(
        repository=repository,
        cursor_agent_id=cursor_agent_id,
        delivery_pr=delivery_pr,
        expected_head=expected_head,
        expected_branch=expected_branch,
        runner=runner,
    )
    branch_name = str(verified["branch_name"])
    bindings = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "issue_number": int(issue_number),
        "repository": repository,
        "source_type": "external_cursor_cloud_github_delivery",
        "cursor_agent_id": cursor_agent_id,
        "source_pr_number": int(delivery_pr),
        "source_branch": branch_name,
        "source_head_sha": expected_head,
        "provider_dispatch_proven": False,
    }
    adoption_id = derive_adoption_id(bindings)
    adopted_delivery_id = derive_adopted_delivery_id(bindings)
    prior_runs = list(original_cdb_run_ids or IMMUTABLE_FAILED_RUN_IDS)

    receipt: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "adoption_id": adoption_id,
        "issue_number": int(issue_number),
        "repository": repository,
        "source_type": "external_cursor_cloud_github_delivery",
        "cursor_agent_id": cursor_agent_id,
        "source_pr_number": int(delivery_pr),
        "source_branch": branch_name,
        "source_head_sha": expected_head,
        "original_cdb_run_ids": prior_runs,
        "adopted_delivery_id": adopted_delivery_id,
        "commit_provenance": {
            "cursor_author_login": CURSOR_AUTHOR_LOGIN,
            "cursor_author_email": CURSOR_AUTHOR_EMAIL,
            "owner_coauthor_login": owner_coauthor_login,
            "pr_body_agent_ref_present": bool(
                verified.get("pr_body_agent_ref_present")
            ),
            "commit_agent_author_match": bool(
                verified.get("commit_agent_author_match")
            ),
            "footer_only_insufficient": True,
        },
        "delivery_verified": True,
        "provider_dispatch_proven": False,
        "evidence_boundaries": {
            "binds_repository": True,
            "binds_agent_id": True,
            "binds_branch": True,
            "binds_commit": True,
            "binds_pr": True,
            "no_phantom_branch": True,
            "claimed_equals_verified": True,
            "hosted_checks_classification": (
                "github_snapshot_not_final_head_merge_evidence"
            ),
        },
        "authority_limits": dict(AUTHORITY_LIMITS),
        "github_verification": {
            "branch_exists": bool(verified.get("branch_exists")),
            "commit_exists": bool(verified.get("commit_exists")),
            "pr_exists": bool(verified.get("pr_exists")),
            "pr_head_matches_expected": bool(verified.get("pr_head_matches_expected")),
            "branch_tip_matches_expected": bool(
                verified.get("branch_tip_matches_expected")
            ),
            "pr_state": str((verified.get("pr") or {}).get("state") or "UNKNOWN"),
            "hosted_checks_snapshot": verified.get("hosted_checks_snapshot"),
        },
        "limitations": list(DEFAULT_LIMITATIONS),
        "adoption_verdict": "ADOPTABLE_WITH_EXPLICIT_RECONCILIATION_RECEIPT",
        "delivery_classification": "VERIFIED_CURSOR_CLOUD_GITHUB_DELIVERY",
    }
    if observed_at:
        receipt["metadata"] = {"observed_at": observed_at}

    receipt = attach_adoption_digest(receipt)
    cleaned = strip_secrets(receipt)
    if not isinstance(cleaned, dict):
        raise CursorAdoptError("ADOPT_REDACT_FAILED", "receipt redaction failed")
    validate_adoption_receipt(cleaned, repo_root=repo_root)
    return cleaned


def build_adoption_approval_snapshot(
    receipt: dict[str, Any],
    *,
    base_sha: str,
    checks: list[dict[str, Any]] | None = None,
    protection: dict[str, Any] | None = None,
    is_draft: bool = False,
) -> dict[str, Any]:
    """Build an approval-context snapshot bound to the adoption receipt.

    Does not grant approval or merge. Omits fabricated cdb-local-ci SUCCESS
    unless the caller injects real check observations.
    """
    head = str(receipt["source_head_sha"])
    if not SHA40.match(base_sha):
        raise CursorAdoptError("ADOPT_BASE_SHA_INVALID", "base_sha must be 40-hex")
    snapshot: dict[str, Any] = {
        "pr": {
            "number": int(receipt["source_pr_number"]),
            "is_draft": bool(is_draft),
            "head_sha": head,
            "base_sha": base_sha,
            "review_decision": None,
            "blocking_threads": 0,
        },
        "checks": list(checks or []),
        "protection": protection
        or {
            "required_checks": [
                {
                    "name": "cdb-local-ci",
                    "mechanism": "check_run",
                    "app_id": 4410232,
                }
            ]
        },
        "adapter": {
            "adapter_id": "cursor-delivery-adoption",
            "capability_fingerprint": receipt["canonical_digest"],
        },
        "adoption": {
            "adoption_id": receipt["adoption_id"],
            "canonical_digest": receipt["canonical_digest"],
            "issue_number": receipt["issue_number"],
            "cursor_agent_id": receipt["cursor_agent_id"],
            "provider_dispatch_proven": False,
            "desired_state": "AWAITING_APPROVAL",
            "forbidden_states": ["APPROVED", "MERGE_READY", "MERGED"],
        },
    }
    return snapshot


def build_approval_agent_handoff(
    *,
    approval_context: dict[str, Any],
    adoption_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Advisory handoff binding approval context + adoption receipt.

    Never mutates GitHub reviews, never merges, never publishes cdb-local-ci.
    """
    subject = approval_context.get("subject") or {}
    handoff = {
        "schema_id": "cdb.cursor_adoption_approval_handoff.v1",
        "schema_version": "1.0.0",
        "verdict": "APPROVAL_HANDOFF_PREPARED_NOT_EXECUTED",
        "desired_state": "READY_FOR_APPROVAL_AGENT_HANDOFF",
        "bindings": {
            "issue_number": adoption_receipt.get("issue_number"),
            "pr_number": subject.get("pr_number")
            or adoption_receipt.get("source_pr_number"),
            "head_sha": subject.get("head_sha")
            or adoption_receipt.get("source_head_sha"),
            "adoption_id": adoption_receipt.get("adoption_id"),
            "adoption_digest": adoption_receipt.get("canonical_digest"),
            "approval_context_digest": approval_context.get("context_digest"),
            "approval_recommendation": approval_context.get("recommendation"),
        },
        "authority_limits": dict(AUTHORITY_LIMITS),
        "surface": {
            "cursor_approval_agents": "MANUAL_BOOTSTRAP_ONLY",
            "github_review_mutation": False,
            "merge_execution": False,
            "completeness_bypass": False,
            "final_ci_bypass": False,
            "cdb_local_ci_bypass": False,
        },
        "limitations": [
            "advisory_read_only",
            "approval_agents_manual_bootstrap_only",
            "no_github_review_mutation",
            "no_merge",
            "no_cdb_local_ci_publish",
            "external_delivery_adoption_not_cdb_dispatch",
        ],
    }
    assert_no_secrets(handoff)
    return handoff


def adopt_cursor_delivery(
    *,
    issue_number: int,
    repository: str,
    cursor_agent_id: str,
    delivery_pr: int,
    expected_head: str,
    expected_branch: str | None = None,
    base_sha: str | None = None,
    out_dir: Path | None = None,
    runner: GhRunner | None = None,
    repo_root: Path | None = None,
    build_approval: bool = True,
    verification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """End-to-end adoption: verify → receipt → optional approval context/handoff."""
    from tools.agent_control.approval.context import (
        build_approval_context,
        default_repo_paths,
    )

    root = repo_root or REPO_ROOT
    verified = verification or verify_cursor_cloud_delivery(
        repository=repository,
        cursor_agent_id=cursor_agent_id,
        delivery_pr=delivery_pr,
        expected_head=expected_head,
        expected_branch=expected_branch,
        runner=runner,
    )
    receipt = build_adoption_receipt(
        issue_number=issue_number,
        repository=repository,
        cursor_agent_id=cursor_agent_id,
        delivery_pr=delivery_pr,
        expected_head=expected_head,
        expected_branch=expected_branch,
        verification=verified,
        runner=runner,
        repo_root=root,
    )

    resolved_base = base_sha or (verified.get("pr") or {}).get("baseRefOid")

    result: dict[str, Any] = {
        "adoption_receipt": receipt,
        "delivery_classification": receipt["delivery_classification"],
        "adoption_verdict": receipt["adoption_verdict"],
        "acceptance_matrix": {
            "L1_provider_api_path": {
                "status": "PARTIAL",
                "note": (
                    "Prior CDB creates executed and ended ERROR; "
                    "PR delivery was not produced by those runs."
                ),
                "immutable_failed_runs": list(IMMUTABLE_FAILED_RUN_IDS),
            },
            "L2_github_delivery": {
                "status": "PROVEN",
                "evidence_pr": delivery_pr,
                "head_sha": expected_head,
                "classification": receipt["delivery_classification"],
            },
            "L3_approval_context_handoff": {
                "status": "PENDING",
            },
            "final_verdict": "PARTIAL_4258_ACCEPTANCE_L2_ONLY",
        },
        "http_posts_to_cursor": 0,
        "github_writes": 0,
    }

    approval_envelope = None
    handoff = None
    if build_approval:
        if not resolved_base or not SHA40.match(str(resolved_base)):
            raise CursorAdoptError(
                "HOLD_APPROVAL_CONTEXT_INVALID",
                "base_sha required to bind approval context",
            )
        # Do not invent cdb-local-ci SUCCESS — leave checks empty / snapshot-only.
        snapshot = build_adoption_approval_snapshot(
            receipt,
            base_sha=str(resolved_base),
            checks=[],
            is_draft=False,
        )
        approval_envelope = build_approval_context(snapshot, default_repo_paths(root))
        handoff = build_approval_agent_handoff(
            approval_context=approval_envelope,
            adoption_receipt=receipt,
        )
        result["approval_context"] = approval_envelope
        result["approval_handoff"] = handoff
        result["acceptance_matrix"]["L3_approval_context_handoff"] = {
            "status": "PREPARED",
            "desired_state": handoff["desired_state"],
            "verdict": handoff["verdict"],
            "approval_recommendation": approval_envelope.get("recommendation"),
            "context_digest": approval_envelope.get("context_digest"),
            "note": (
                "Approval context bound; Approval-Agent surface remains "
                "MANUAL_BOOTSTRAP_ONLY; no GitHub review mutation."
            ),
        }
        result["acceptance_matrix"][
            "final_verdict"
        ] = "PARTIAL_4258_ACCEPTANCE_L2_L3_PROVEN"

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "adoption_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if approval_envelope is not None:
            (out_dir / "approval_context.json").write_text(
                json.dumps(approval_envelope, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if handoff is not None:
            (out_dir / "approval_handoff.json").write_text(
                json.dumps(handoff, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        (out_dir / "acceptance_matrix.json").write_text(
            json.dumps(result["acceptance_matrix"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return result
