"""Publish trusted live branch-protection attestation via cdb-local-ci (#4505)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from ci.publisher.app_auth import mint_installation_token

from tools.agent_control.approval.canon_loader import load_bootstrap_policy
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.approval.gh_api import gh_api_json
from tools.agent_control.approval.protection_live_evidence import (
    PRODUCER,
    build_protection_live_envelope,
    format_protection_attestation_comment_body,
    load_protection_attestation_schema,
    probe_branch_protection_api,
)
from tools.agent_control.approval.publish import (
    PublishResult,
    fetch_live_pr_subject,
    post_issue_comment,
    resolve_publisher_app_identity,
)
from tools.agent_control.approval.publisher_validate import (
    assert_producer_allowed_by_bootstrap,
    verify_trust_policy_publisher_binding,
)
from tools.agent_control.paths import REPO_ROOT

DEFAULT_REPOSITORY = "jannekbuengener/Claire_de_Binare"


def publish_protection_live_attestation(
    *,
    pr_number: int,
    repository: str = DEFAULT_REPOSITORY,
    repo_root: Path | None = None,
    bootstrap_git_ref: str | None = None,
    transport: Any | None = None,
    token_provider: Callable[[], str] | None = None,
) -> PublishResult:
    """Read live branch protection on publisher host, publish trusted attestation."""
    root = repo_root or REPO_ROOT
    bootstrap = load_bootstrap_policy(root, git_ref=bootstrap_git_ref)
    assert_producer_allowed_by_bootstrap(bootstrap, PRODUCER)
    schema = load_protection_attestation_schema(root)
    app_id, app_slug, _ = resolve_publisher_app_identity(bootstrap, transport=transport)
    verify_trust_policy_publisher_binding(
        publisher_app_slug=app_slug,
        repo_root=root,
        declared_producer=PRODUCER,
    )

    owner, repo = repository.split("/", 1)
    pr = gh_api_json(["api", f"repos/{owner}/{repo}/pulls/{pr_number}"])
    if not isinstance(pr, dict):
        raise ApprovalError("APPROVAL_PUBLISH_PR_INVALID", "invalid pull response")
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    base_ref = base.get("ref")
    base_sha = base.get("sha")
    if not isinstance(base_ref, str) or not isinstance(base_sha, str):
        raise ApprovalError("APPROVAL_PUBLISH_PR_INVALID", "missing base ref/sha")

    head_sha, live_base_sha, _draft = fetch_live_pr_subject(
        repository=repository,
        pr_number=pr_number,
    )
    if live_base_sha.lower() != base_sha.lower():
        raise ApprovalError(
            "APPROVAL_PUBLISH_PR_INVALID", "base sha drift during publish"
        )

    payload, read_error = probe_branch_protection_api(owner, repo, base_ref)
    if payload is None:
        detail = read_error.to_dict() if read_error else {}
        raise ApprovalError(
            "PROTECTION_ATTESTATION_READ_FAILED",
            "publisher cannot read live branch protection: "
            + json.dumps(detail, sort_keys=True),
        )

    envelope = build_protection_live_envelope(
        repository=repository,
        base_ref=base_ref,
        base_sha=base_sha,
        protection_payload=payload,
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(envelope),
        key=lambda e: list(e.path),
    )
    if errors:
        err = errors[0]
        loc = ".".join(str(p) for p in err.path) or "$"
        raise ApprovalError(
            "PROTECTION_ATTESTATION_SCHEMA_INVALID",
            f"{loc}: {err.message}",
        )

    body = format_protection_attestation_comment_body(envelope)
    token = (
        token_provider()
        if token_provider
        else mint_installation_token(transport=transport)
    )
    comment = post_issue_comment(
        repository=repository,
        pr_number=pr_number,
        body=body,
        installation_token=token,
        transport=transport,
    )
    comment_id = comment.comment_id
    if comment_id is None:
        raise ApprovalError("APPROVAL_PUBLISH_COMMENT_FAILED", "missing comment id")

    return PublishResult(
        comment_id=comment_id,
        repository=repository,
        pr_number=pr_number,
        producer=PRODUCER,
        head_sha=head_sha,
        base_sha=live_base_sha,
        github_app_slug=app_slug,
        github_app_id=app_id,
        author_login=comment.author_login,
        author_type=comment.author_type,
        performed_via_github_app_slug=comment.performed_via_github_app_slug,
    )
