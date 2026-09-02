"""Publisher tests for trusted protection live attestation (#4505)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from ci.publisher.github_client import GitHubResponse
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.producer_trust import (
    load_producer_trust_policy,
    producer_actor_trusted,
)
from tools.agent_control.approval.protection_live_evidence import (
    EVIDENCE_MARKER,
    PRODUCER,
    ProtectionReadError,
    resolve_protection_live_attestation,
)
from tools.agent_control.approval.protection_publish import (
    publish_protection_live_attestation,
)
from tools.agent_control.paths import REPO_ROOT

BASE = "b" * 40
HEAD = "a" * 40
REPO = "jannekbuengener/Claire_de_Binare"
PR = 4530


@pytest.fixture
def publisher_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CDB_GH_APP_ID", "4410232")
    monkeypatch.setattr(
        "tools.agent_control.approval.publish.load_app_private_key_pem",
        lambda: "fake-private-key",
    )
    monkeypatch.setattr(
        "tools.agent_control.approval.publish.mint_app_jwt",
        lambda **_: "fake-jwt",
    )


def _protection_payload(*, contexts: list[str] | None = None) -> dict[str, Any]:
    names = contexts or ["cdb-local-ci"]
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": names,
            "checks": [
                {"context": name, "app_id": 4410232 if name == "cdb-local-ci" else None}
                for name in names
            ],
        }
    }


def _capturing_app_transport() -> tuple[Any, dict[str, str]]:
    captured: dict[str, str] = {}
    base = _app_transport()

    def _transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> GitHubResponse:
        if method == "POST" and "/issues/" in url and url.endswith("/comments"):
            payload = json.loads(body.decode("utf-8")) if body else {}
            captured["body"] = str(payload.get("body", ""))
        return base(method, url, headers, body, timeout)

    return _transport, captured


def _app_transport(*, permissions: dict[str, str] | None = None) -> Any:
    perms = permissions or {
        "checks": "write",
        "contents": "write",
        "issues": "write",
        "metadata": "read",
        "pull_requests": "read",
        "statuses": "write",
    }

    def _transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> GitHubResponse:
        if method == "GET" and url.endswith("/app"):
            return GitHubResponse(
                status_code=200,
                body={"id": 4410232, "slug": "cdb-local-ci", "permissions": perms},
                headers={},
            )
        if method == "POST" and "/issues/" in url and url.endswith("/comments"):
            payload = json.loads(body.decode("utf-8")) if body else {}
            return GitHubResponse(
                status_code=201,
                body={
                    "id": 999001,
                    "body": payload.get("body", ""),
                    "user": {"login": "cdb-local-ci[bot]", "type": "Bot"},
                    "author_association": "NONE",
                    "performed_via_github_app": {
                        "id": 4410232,
                        "slug": "cdb-local-ci",
                    },
                },
                headers={},
            )
        return GitHubResponse(
            status_code=404, body={"message": "not found"}, headers={}
        )

    return _transport


def _wire_publish_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    base_sha: str = BASE,
    live_base_sha: str = BASE,
    protection_payload: dict[str, Any] | None = None,
    read_error: ProtectionReadError | None = None,
) -> None:
    payload = (
        protection_payload if protection_payload is not None else _protection_payload()
    )

    monkeypatch.setattr(
        "tools.agent_control.approval.protection_publish.gh_api_json",
        lambda argv: {
            "base": {"ref": "main", "sha": base_sha},
            "head": {"sha": HEAD},
        },
    )
    monkeypatch.setattr(
        "tools.agent_control.approval.protection_publish.fetch_live_pr_subject",
        lambda **_: (HEAD, live_base_sha, False),
    )
    monkeypatch.setattr(
        "tools.agent_control.approval.protection_publish.probe_branch_protection_api",
        lambda *_args, **_kwargs: (
            (None, read_error) if read_error is not None else (payload, None)
        ),
    )


@pytest.mark.unit
def test_publish_protection_live_attestation_mock_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    publisher_app_env: None,
) -> None:
    _wire_publish_mocks(monkeypatch)
    result = publish_protection_live_attestation(
        pr_number=PR,
        repository=REPO,
        repo_root=REPO_ROOT,
        transport=_app_transport(),
        token_provider=lambda: "test-token",
    )
    assert result.comment_id == 999001
    assert result.producer == PRODUCER
    assert result.base_sha == BASE
    assert result.head_sha == HEAD
    assert result.performed_via_github_app_slug == "cdb-local-ci"
    assert result.github_app_id == 4410232


@pytest.mark.unit
def test_publish_protection_rejects_when_branch_protection_unreadable(
    monkeypatch: pytest.MonkeyPatch,
    publisher_app_env: None,
) -> None:
    read_error = ProtectionReadError(
        endpoint=f"repos/{REPO}/branches/main/protection",
        http_status=403,
        gh_exit_code=1,
        message="403 Forbidden",
        hint="administration read required",
    )
    _wire_publish_mocks(monkeypatch, read_error=read_error)
    with pytest.raises(ApprovalError, match="PROTECTION_ATTESTATION_READ_FAILED"):
        publish_protection_live_attestation(
            pr_number=PR,
            repository=REPO,
            repo_root=REPO_ROOT,
            transport=_app_transport(),
            token_provider=lambda: "test-token",
        )


@pytest.mark.unit
def test_publish_protection_rejects_base_sha_drift(
    monkeypatch: pytest.MonkeyPatch,
    publisher_app_env: None,
) -> None:
    _wire_publish_mocks(
        monkeypatch,
        base_sha=BASE,
        live_base_sha="c" * 40,
    )
    with pytest.raises(ApprovalError, match="APPROVAL_PUBLISH_PR_INVALID"):
        publish_protection_live_attestation(
            pr_number=PR,
            repository=REPO,
            repo_root=REPO_ROOT,
            transport=_app_transport(),
            token_provider=lambda: "test-token",
        )


@pytest.mark.unit
def test_published_protection_attestation_trusted_by_resolver(
    monkeypatch: pytest.MonkeyPatch,
    publisher_app_env: None,
) -> None:
    _wire_publish_mocks(monkeypatch)
    transport, captured = _capturing_app_transport()
    result = publish_protection_live_attestation(
        pr_number=PR,
        repository=REPO,
        repo_root=REPO_ROOT,
        transport=transport,
        token_provider=lambda: "test-token",
    )
    comment = CommentRecord(
        comment_id=result.comment_id,
        body=captured["body"],
        author_login=result.author_login,
        author_type=result.author_type,
        performed_via_github_app_slug=result.performed_via_github_app_slug,
    )
    policy = load_producer_trust_policy(REPO_ROOT)
    ok, detail = producer_actor_trusted(
        producer=PRODUCER,
        comment=comment,
        trust_policy=policy,
    )
    assert ok is True, detail
    resolved = resolve_protection_live_attestation(
        comments=[comment],
        repository=REPO,
        live_base_sha=BASE,
        live_base_ref="main",
        repo_root=REPO_ROOT,
    )
    assert resolved is not None
    assert resolved.required_checks[0]["name"] == "cdb-local-ci"
    assert EVIDENCE_MARKER in captured["body"]
