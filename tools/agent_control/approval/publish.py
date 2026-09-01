"""Trusted acceptance evidence publisher via repo-canonical GitHub App (#4505)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ci.publisher.app_auth import (
    load_private_key_pem as load_app_private_key_pem,
    mint_app_jwt,
    mint_installation_token,
    resolve_app_id_from_env,
)
from ci.publisher.github_client import GITHUB_API, GitHubResponse, _default_transport

from tools.agent_control.approval.canon_loader import (
    load_acceptance_schema_from_canon,
    load_bootstrap_policy,
)
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.gh_api import gh_api_json
from tools.agent_control.approval.publisher_validate import (
    format_acceptance_comment_body,
    validate_envelope_for_publish,
    verify_trust_policy_publisher_binding,
)
from tools.agent_control.paths import REPO_ROOT

Transport = Callable[[str, str, dict[str, str], bytes | None, float], GitHubResponse]

DEFAULT_REPOSITORY = "jannekbuengener/Claire_de_Binare"


@dataclass(frozen=True)
class PublishResult:
    comment_id: int
    repository: str
    pr_number: int
    producer: str
    head_sha: str
    base_sha: str
    github_app_slug: str
    github_app_id: int
    author_login: str | None
    author_type: str | None
    performed_via_github_app_slug: str | None


def resolve_publisher_app_identity(
    bootstrap: dict[str, Any],
    *,
    transport: Transport | None = None,
) -> tuple[int, str, dict[str, str]]:
    """Resolve live app slug + permissions; must match bootstrap binding."""
    publisher = (
        bootstrap.get("publisher")
        if isinstance(bootstrap.get("publisher"), dict)
        else {}
    )
    expected_id = publisher.get("github_app_id")
    expected_slug = publisher.get("github_app_slug")
    if not isinstance(expected_id, int) or expected_id <= 0:
        raise ApprovalError(
            "APPROVAL_PUBLISH_BOOTSTRAP_INVALID", "publisher.github_app_id invalid"
        )
    if not isinstance(expected_slug, str) or not expected_slug.strip():
        raise ApprovalError(
            "APPROVAL_PUBLISH_BOOTSTRAP_INVALID", "publisher.github_app_slug invalid"
        )

    governance = bootstrap.get("self_governance")
    if isinstance(governance, dict) and governance.get(
        "publisher_app_id_must_match_env"
    ):
        env_id = resolve_app_id_from_env()
        if env_id != expected_id:
            raise ApprovalError(
                "APPROVAL_PUBLISH_APP_MISMATCH",
                f"env app_id {env_id} != bootstrap {expected_id}",
            )

    jwt = mint_app_jwt(app_id=expected_id, private_key_pem=load_app_private_key_pem())
    runner = transport or _default_transport
    response = runner(
        "GET",
        f"{GITHUB_API}/app",
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {jwt}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        None,
        30.0,
    )
    if response.status_code >= 400:
        raise ApprovalError(
            "APPROVAL_PUBLISH_APP_LOOKUP_FAILED",
            f"GET /app HTTP {response.status_code}",
        )
    body = response.body if isinstance(response.body, dict) else {}
    live_id = body.get("id")
    live_slug = body.get("slug")
    if live_id != expected_id:
        raise ApprovalError(
            "APPROVAL_PUBLISH_APP_MISMATCH",
            f"live app id {live_id} != bootstrap {expected_id}",
        )
    if live_slug != expected_slug:
        raise ApprovalError(
            "APPROVAL_PUBLISH_APP_MISMATCH",
            f"live app slug {live_slug!r} != bootstrap {expected_slug!r}",
        )
    perms = body.get("permissions") if isinstance(body.get("permissions"), dict) else {}
    perm_map = {str(k): str(v) for k, v in perms.items()}
    required = bootstrap.get("permissions_required")
    if isinstance(required, list):
        for perm in required:
            key = str(perm)
            if ":" in key:
                name, level = key.split(":", 1)
            else:
                name, level = key, "write"
            actual = perm_map.get(name, "none")
            if actual in {"none", "read"} and level == "write":
                raise ApprovalError(
                    "APPROVAL_PUBLISH_APP_PERMISSION_DENIED",
                    f"GitHub App missing required permission {key!r} "
                    f"(have {actual!r}). Operator must grant {key!r} on app "
                    f"{expected_slug!r} (id {expected_id}) in GitHub Settings.",
                )
    return int(live_id), str(live_slug), perm_map


def fetch_live_pr_subject(
    *,
    repository: str,
    pr_number: int,
) -> tuple[str, str, bool]:
    owner, repo = repository.split("/", 1)
    pr = gh_api_json(["api", f"repos/{owner}/{repo}/pulls/{pr_number}"])
    if not isinstance(pr, dict):
        raise ApprovalError("APPROVAL_PUBLISH_PR_INVALID", "invalid pull response")
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    head_sha = head.get("sha")
    base_sha = base.get("sha")
    draft = bool(pr.get("draft"))
    if not isinstance(head_sha, str) or not isinstance(base_sha, str):
        raise ApprovalError("APPROVAL_PUBLISH_PR_INVALID", "missing head/base sha")
    return head_sha.lower(), base_sha.lower(), draft


def post_issue_comment(
    *,
    repository: str,
    pr_number: int,
    body: str,
    installation_token: str,
    transport: Transport | None = None,
) -> CommentRecord:
    owner, repo = repository.split("/", 1)
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    encoded = json.dumps({"body": body}, ensure_ascii=False).encode("utf-8")
    runner = transport or _default_transport
    response = runner(
        "POST",
        url,
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {installation_token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        encoded,
        30.0,
    )
    if response.status_code == 403:
        raise ApprovalError(
            "APPROVAL_PUBLISH_APP_PERMISSION_DENIED",
            "GitHub rejected comment create (403). Grant issues:write on the "
            "cdb-local-ci GitHub App (id 4410232).",
        )
    if response.status_code >= 400:
        raise ApprovalError(
            "APPROVAL_PUBLISH_COMMENT_FAILED",
            f"POST comment HTTP {response.status_code}: {response.body}",
        )
    item = response.body if isinstance(response.body, dict) else {}
    return CommentRecord.from_github_issue_comment(item)


def publish_acceptance_envelope(
    envelope: dict[str, Any],
    *,
    declared_producer: str,
    pr_number: int,
    repository: str = DEFAULT_REPOSITORY,
    repo_root: Path | None = None,
    bootstrap_git_ref: str | None = None,
    transport: Transport | None = None,
    token_provider: Callable[[], str] | None = None,
) -> PublishResult:
    """Validate fail-closed, then publish as GitHub App issue comment."""
    root = repo_root or REPO_ROOT
    bootstrap = load_bootstrap_policy(root, git_ref=bootstrap_git_ref)
    schema = load_acceptance_schema_from_canon(bootstrap, repo_root=root)

    app_id, app_slug, _ = resolve_publisher_app_identity(bootstrap, transport=transport)
    verify_trust_policy_publisher_binding(publisher_app_slug=app_slug, repo_root=root)

    head_sha, base_sha, _draft = fetch_live_pr_subject(
        repository=repository,
        pr_number=pr_number,
    )
    validate_envelope_for_publish(
        envelope,
        declared_producer=declared_producer,
        repository=repository,
        pr_number=pr_number,
        live_head_sha=head_sha,
        live_base_sha=base_sha,
        schema=schema,
        bootstrap=bootstrap,
    )

    body = format_acceptance_comment_body(envelope)
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
        producer=declared_producer,
        head_sha=head_sha,
        base_sha=base_sha,
        github_app_slug=app_slug,
        github_app_id=app_id,
        author_login=comment.author_login,
        author_type=comment.author_type,
        performed_via_github_app_slug=comment.performed_via_github_app_slug,
    )
