"""Unit tests for status publisher GitHub client (Issue #4164)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from ci.publisher.exceptions import AuthenticationError, GitHubApiError
from ci.publisher.github_client import GitHubResponse, GitHubStatusClient
from ci.publisher.models import StatusPayload

pytestmark = pytest.mark.unit

SHA = "cccccccccccccccccccccccccccccccccccccccc"


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: list[GitHubResponse] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> GitHubResponse:
        parsed_body = json.loads(body.decode("utf-8")) if body else None
        # Never retain Authorization in call log for assertions beyond presence.
        safe_headers = {
            k: ("[REDACTED]" if k.lower() == "authorization" else v)
            for k, v in headers.items()
        }
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": safe_headers,
                "body": parsed_body,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("No fake response queued")
        return self.responses.pop(0)


class FakeStatusWriter:
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.response = response or {"id": 1, "state": "success", "sha": SHA}

    def __call__(
        self,
        owner: str,
        repo: str,
        sha: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append({"owner": owner, "repo": repo, "sha": sha, "body": body})
        return self.response


def test_dry_run_performs_no_write():
    transport = FakeTransport()
    client = GitHubStatusClient(token="ghs_testtoken12345678", transport=transport)
    payload = StatusPayload(
        sha=SHA,
        state="success",
        context="cdb-local-ci-preview",
        description="ok",
    )
    result = client.create_commit_status(payload, dry_run=True)
    assert result["dry_run"] is True
    assert transport.calls == []
    assert client.write_calls[0]["dry_run"] is True


def test_success_payload_targets_exact_sha():
    writer = FakeStatusWriter()
    client = GitHubStatusClient(token="token", status_writer=writer)
    payload = StatusPayload(
        sha=SHA,
        state="success",
        context="cdb-local-ci",
        description="Local Docker CI evidence verified for exact commit SHA.",
    )
    client.create_commit_status(payload, dry_run=False)
    assert writer.calls[0]["sha"] == SHA
    assert writer.calls[0]["body"]["state"] == "success"
    assert writer.calls[0]["body"]["context"] == "cdb-local-ci"


def test_failure_never_produces_success_conclusion():
    payload = StatusPayload(
        sha=SHA,
        state="failure",
        context="cdb-local-ci",
        description="Local Docker CI evidence rejected or pipeline failed.",
    )
    assert payload.to_api_body()["state"] == "failure"
    assert payload.to_api_body()["state"] != "success"


def test_insufficient_permissions_fail_closed():
    def denied(owner: str, repo: str, sha: str, body: dict[str, Any]) -> dict[str, Any]:
        raise AuthenticationError("Insufficient gh permission")

    client = GitHubStatusClient(token="token", status_writer=denied)
    payload = StatusPayload(
        sha=SHA, state="success", context="cdb-local-ci", description="ok"
    )
    with pytest.raises(AuthenticationError):
        client.create_commit_status(payload, dry_run=False)


def test_api_timeout_fails_closed():
    def boom(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> GitHubResponse:
        raise TimeoutError("timed out")

    client = GitHubStatusClient(token="token", transport=boom)
    with pytest.raises(GitHubApiError, match="timed out"):
        client.assert_commit_exists(SHA)


def test_rate_limit_ambiguity_fails_closed():
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(
            403,
            {"message": "API rate limit exceeded"},
            {"x-ratelimit-remaining": "0"},
        )
    )
    client = GitHubStatusClient(token="token", transport=transport)
    with pytest.raises(GitHubApiError, match="rate limit"):
        client.assert_commit_exists(SHA)


def test_existing_unrelated_statuses_remain_untouched():
    # Client only POSTs the named context; it never deletes or patches others.
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(
            200,
            {
                "state": "pending",
                "statuses": [
                    {
                        "context": "ci (Unit/Integration + Lint gesammelt)",
                        "state": "success",
                    },
                    {"context": "policy-gate", "state": "success"},
                ],
                "total_count": 2,
            },
            {},
        )
    )
    writer = FakeStatusWriter(
        {"id": 99, "state": "success", "context": "cdb-local-ci-preview"}
    )
    client = GitHubStatusClient(
        token="token", transport=transport, status_writer=writer
    )
    before = client.get_commit_status(SHA)
    assert len(before["statuses"]) == 2
    payload = StatusPayload(
        sha=SHA,
        state="success",
        context="cdb-local-ci-preview",
        description="ok",
    )
    client.create_commit_status(payload, dry_run=False)
    assert writer.calls[0]["body"]["context"] == "cdb-local-ci-preview"
    # No call mutated other contexts.
    assert all(c.get("body", {}).get("context") != "policy-gate" for c in writer.calls)


def test_check_run_and_commit_status_payloads_are_deterministic():
    a = StatusPayload(
        sha=SHA,
        state="success",
        context="cdb-local-ci",
        description="Local Docker CI evidence verified for exact commit SHA.",
        target_url="https://example.test/evidence",
    )
    b = StatusPayload(
        sha=SHA,
        state="success",
        context="cdb-local-ci",
        description="Local Docker CI evidence verified for exact commit SHA.",
        target_url="https://example.test/evidence",
    )
    assert a.to_api_body() == b.to_api_body()
    # Phase 3a documents Commit Status only; Check Run adapter is intentionally absent.
    assert not hasattr(GitHubStatusClient, "create_check_run")
