"""Acceptance evidence publisher tests (#4505 trusted publisher wiring)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from ci.publisher.github_client import GitHubResponse
from tools.agent_control.approval.acceptance_provenance import (
    COMPLETENESS_PRODUCER,
    EVIDENCE_MARKER,
    resolve_final_head_provenance,
)
from tools.agent_control.approval.codes import ApprovalError
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.producer_trust import producer_actor_trusted
from tools.agent_control.approval.publish import (
    fetch_live_pr_subject,
    post_issue_comment,
    publish_acceptance_envelope,
    resolve_publisher_app_identity,
)
from tools.agent_control.approval.publisher_validate import (
    validate_envelope_for_publish,
    verify_trust_policy_publisher_binding,
)
from tools.agent_control.paths import REPO_ROOT

FIX = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "approval"
SHA = "c" * 40
SHA_B = "d" * 40
REPO = "jannekbuengener/Claire_de_Binare"
PR = 4530


def _bootstrap() -> dict[str, Any]:
    return yaml.safe_load(
        (
            REPO_ROOT
            / "config/agent-control/policies/approval/acceptance_publisher_bootstrap.v1.yaml"
        ).read_text(encoding="utf-8")
    )


def _dims() -> list[dict[str, Any]]:
    from tools.agent_control.approval.canon_loader import (
        load_acceptance_schema_from_canon,
    )

    schema = load_acceptance_schema_from_canon(_bootstrap(), repo_root=REPO_ROOT)
    enum = schema["$defs"]["CompletenessDimensionRow"]["properties"]["dimension"][
        "enum"
    ]
    return [{"dimension": name, "state": "PASS", "reason": "ok"} for name in enum]


def _completeness_envelope(
    *, head: str = SHA, base: str = SHA_B, pr: int = PR
) -> dict[str, Any]:
    return {
        "schema_version": "cdb-pr-acceptance-skill-family/v1",
        "policy_id": "cdb-pr-acceptance-v1",
        "producer": COMPLETENESS_PRODUCER,
        "subject": {
            "repository": REPO,
            "pr_number": pr,
            "head_sha": head,
            "base_sha": base,
        },
        "observed_at": "2026-09-01T19:30:00Z",
        "run_status": "COMPLETE",
        "lifecycle": {"state": "MERGE_CANDIDATE"},
        "decision": {"verdict": "MERGE_CANDIDATE", "block_codes": []},
        "findings": [],
        "evidence": [{"evidence_id": "e1", "kind": "test", "ref": "ref"}],
        "limitations": [],
        "handoff": {
            "next_producer": "cdb-batch-merge-conductor",
            "notes": "handoff",
        },
        "evidence_marker": EVIDENCE_MARKER,
        "result": {"dimensions": _dims(), "verdict": "MERGE_CANDIDATE"},
    }


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


@pytest.mark.unit
def test_verify_trust_policy_binds_cdb_local_ci_slug() -> None:
    verify_trust_policy_publisher_binding(
        publisher_app_slug="cdb-local-ci",
        repo_root=REPO_ROOT,
    )


@pytest.mark.unit
def test_validate_envelope_rejects_producer_impersonation() -> None:
    from tools.agent_control.approval.canon_loader import (
        load_acceptance_schema_from_canon,
    )

    env = _completeness_envelope()
    schema = load_acceptance_schema_from_canon(_bootstrap(), repo_root=REPO_ROOT)
    with pytest.raises(ApprovalError, match="PRODUCER_MISMATCH"):
        validate_envelope_for_publish(
            env,
            declared_producer="cdb-batch-merge-conductor",
            repository=REPO,
            pr_number=PR,
            live_head_sha=SHA,
            live_base_sha=SHA_B,
            schema=schema,
            bootstrap=_bootstrap(),
        )


@pytest.mark.unit
def test_validate_envelope_rejects_wrong_pr() -> None:
    from tools.agent_control.approval.canon_loader import (
        load_acceptance_schema_from_canon,
    )

    env = _completeness_envelope(pr=999)
    schema = load_acceptance_schema_from_canon(_bootstrap(), repo_root=REPO_ROOT)
    with pytest.raises(ApprovalError, match="PUBLISH_SUBJECT_MISMATCH"):
        validate_envelope_for_publish(
            env,
            declared_producer=COMPLETENESS_PRODUCER,
            repository=REPO,
            pr_number=PR,
            live_head_sha=SHA,
            live_base_sha=SHA_B,
            schema=schema,
            bootstrap=_bootstrap(),
        )


@pytest.mark.unit
def test_resolve_publisher_app_identity_requires_issues_write() -> None:
    transport = _app_transport(permissions={"checks": "write", "metadata": "read"})
    with pytest.raises(ApprovalError, match="PERMISSION_DENIED"):
        resolve_publisher_app_identity(_bootstrap(), transport=transport)


@pytest.mark.unit
def test_producer_trust_matrix() -> None:
    policy = yaml.safe_load(
        (FIX / "acceptance_producer_trust_test.v1.yaml").read_text(encoding="utf-8")
    )
    env = _completeness_envelope()
    comment = CommentRecord(
        comment_id=1,
        body="x",
        author_login="cdb-local-ci[bot]",
        author_type="Bot",
        performed_via_github_app_slug="cdb-test-completeness-app",
    )
    ok, _ = producer_actor_trusted(
        producer=COMPLETENESS_PRODUCER,
        comment=comment,
        trust_policy=policy,
    )
    assert ok is True

    wrong_slug = CommentRecord(
        comment_id=2,
        body="x",
        author_login="cursor[bot]",
        author_type="Bot",
        performed_via_github_app_slug="cursor",
    )
    ok2, _ = producer_actor_trusted(
        producer=COMPLETENESS_PRODUCER,
        comment=wrong_slug,
        trust_policy=policy,
    )
    assert ok2 is False

    user = CommentRecord(
        comment_id=3,
        body="x",
        author_login="jannekbuengener",
        author_type="User",
        performed_via_github_app_slug=None,
    )
    ok3, _ = producer_actor_trusted(
        producer=COMPLETENESS_PRODUCER,
        comment=user,
        trust_policy=policy,
    )
    assert ok3 is False


@pytest.mark.unit
def test_publish_acceptance_envelope_mock_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.agent_control.approval.canon_loader import (
        load_acceptance_schema_from_canon,
    )

    env = _completeness_envelope()
    monkeypatch.setattr(
        "tools.agent_control.approval.publish.fetch_live_pr_subject",
        lambda **_: (SHA, SHA_B, False),
    )
    result = publish_acceptance_envelope(
        env,
        declared_producer=COMPLETENESS_PRODUCER,
        pr_number=PR,
        repository=REPO,
        repo_root=REPO_ROOT,
        transport=_app_transport(),
        token_provider=lambda: "test-token",
    )
    assert result.comment_id == 999001
    assert result.performed_via_github_app_slug == "cdb-local-ci"
    assert result.github_app_id == 4410232


@pytest.mark.unit
def test_published_comment_trusted_by_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = _completeness_envelope()
    monkeypatch.setattr(
        "tools.agent_control.approval.publish.fetch_live_pr_subject",
        lambda **_: (SHA, SHA_B, False),
    )
    result = publish_acceptance_envelope(
        env,
        declared_producer=COMPLETENESS_PRODUCER,
        pr_number=PR,
        repository=REPO,
        repo_root=REPO_ROOT,
        transport=_app_transport(),
        token_provider=lambda: "test-token",
    )
    body = (
        f"{EVIDENCE_MARKER}\n\n```json\n"
        f"{json.dumps(env, indent=2, sort_keys=True)}\n```\n"
    )
    comment = CommentRecord(
        comment_id=result.comment_id,
        body=body,
        author_login=result.author_login,
        author_type=result.author_type,
        performed_via_github_app_slug=result.performed_via_github_app_slug,
    )
    from tools.agent_control.approval.producer_trust import load_producer_trust_policy

    policy = load_producer_trust_policy(REPO_ROOT)
    ok, detail = producer_actor_trusted(
        producer=COMPLETENESS_PRODUCER,
        comment=comment,
        trust_policy=policy,
    )
    assert ok is True, detail


@pytest.mark.unit
def test_publish_rejects_malformed_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _completeness_envelope()
    broken = deepcopy(env)
    broken["lifecycle"] = {"state": "ACCEPTING_SLICES"}
    monkeypatch.setattr(
        "tools.agent_control.approval.publish.fetch_live_pr_subject",
        lambda **_: (SHA, SHA_B, False),
    )
    with pytest.raises(ApprovalError, match="SEMANTIC_INVALID"):
        publish_acceptance_envelope(
            broken,
            declared_producer=COMPLETENESS_PRODUCER,
            pr_number=PR,
            repository=REPO,
            repo_root=REPO_ROOT,
            transport=_app_transport(),
            token_provider=lambda: "test-token",
        )
