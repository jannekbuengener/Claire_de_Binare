"""Unit tests for App-bound Check Run publisher backend (#4170)."""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from ci.publisher import EXPECTED_REPOSITORY
from ci.publisher.backends import (
    APP_INSTALLATION_TOKEN_ENV,
    CheckRunBackend,
    CommitStatusBackend,
    build_publisher_backend,
    resolve_app_installation_token,
)
from ci.publisher.exceptions import AuthenticationError, GitHubApiError, PublisherError
from ci.publisher.github_client import GitHubResponse, GitHubStatusClient
from ci.publisher.models import (
    CHECK_RUN_NAME,
    CheckRunPayload,
    StatusPayload,
    build_check_run_external_id,
)
from ci.publisher.redaction import redact_mapping, redact_text

pytestmark = pytest.mark.unit

SHA = "cccccccccccccccccccccccccccccccccccccccc"
RUN_ID = "20260730T120000Z-abcdef"
APP_ID = 123456
INSTALLATION_ID = 654321
EXTERNAL_ID = f"{RUN_ID}:{SHA}"


def _payload(**overrides: Any) -> CheckRunPayload:
    base = dict(
        name=CHECK_RUN_NAME,
        head_sha=SHA,
        conclusion="success",
        started_at="2026-07-30T12:00:00Z",
        completed_at="2026-07-30T12:05:00Z",
        external_id=EXTERNAL_ID,
        output_title="cdb-local-ci success",
        output_summary="Local Docker CI evidence verified for exact commit SHA.",
        details_url="https://example.test/evidence",
    )
    base.update(overrides)
    return CheckRunPayload(**base)


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


def _remote_check_run(**overrides: Any) -> dict[str, Any]:
    data = {
        "id": 99,
        "name": CHECK_RUN_NAME,
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "external_id": EXTERNAL_ID,
        "app": {"id": APP_ID, "slug": "cdb-local-ci"},
    }
    data.update(overrides)
    return data


def test_check_run_payload_is_deterministic():
    a = _payload()
    b = _payload()
    assert a.to_api_body() == b.to_api_body()
    assert a.to_api_body()["name"] == CHECK_RUN_NAME
    assert a.to_api_body()["head_sha"] == SHA
    assert a.to_api_body()["external_id"] == EXTERNAL_ID


def test_external_id_is_deterministic():
    assert build_check_run_external_id(run_id=RUN_ID, commit_sha=SHA) == EXTERNAL_ID
    assert (
        build_check_run_external_id(run_id=RUN_ID, commit_sha=SHA.upper())
        == EXTERNAL_ID
    )


def test_success_without_sha_rejected():
    with pytest.raises(ValueError, match="head_sha"):
        CheckRunPayload(
            name=CHECK_RUN_NAME,
            head_sha="",
            conclusion="success",
            started_at="2026-07-30T12:00:00Z",
            completed_at="2026-07-30T12:05:00Z",
            external_id=EXTERNAL_ID,
            output_title="t",
            output_summary="s",
        )


def test_unknown_conclusion_rejected():
    with pytest.raises(ValueError, match="Unknown Check Run conclusion"):
        CheckRunPayload(
            name=CHECK_RUN_NAME,
            head_sha=SHA,
            conclusion="neutral",  # type: ignore[arg-type]
            started_at="2026-07-30T12:00:00Z",
            completed_at="2026-07-30T12:05:00Z",
            external_id=EXTERNAL_ID,
            output_title="t",
            output_summary="s",
        )


def test_missing_installation_token_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(APP_INSTALLATION_TOKEN_ENV, raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_should_not_be_used_abcdefgh")
    monkeypatch.setenv("GH_TOKEN", "ghs_also_not_used_abcdefghijkl")
    with pytest.raises(AuthenticationError, match=APP_INSTALLATION_TOKEN_ENV):
        resolve_app_installation_token()


def test_empty_installation_token_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(APP_INSTALLATION_TOKEN_ENV, "   ")
    with pytest.raises(AuthenticationError, match=APP_INSTALLATION_TOKEN_ENV):
        resolve_app_installation_token()


def test_gh_auth_token_not_auto_used(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(APP_INSTALLATION_TOKEN_ENV, raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(AuthenticationError, match="refuses"):
        resolve_app_installation_token()


def test_missing_expected_app_id_rejected():
    with pytest.raises(PublisherError, match="expected-app-id"):
        build_publisher_backend(
            backend="check-run",
            app_token="installation-token-test",
            expected_app_id=None,
            expected_installation_id=INSTALLATION_ID,
        )


def test_invalid_installation_id_rejected():
    with pytest.raises(PublisherError, match="positive integer"):
        CheckRunBackend(
            token="tok",
            expected_app_id=APP_ID,
            expected_installation_id=0,
        )


def test_correct_check_run_post_route_and_headers():
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    created = _remote_check_run()
    transport.responses.append(GitHubResponse(201, created, {}))
    transport.responses.append(GitHubResponse(200, created, {}))
    backend = CheckRunBackend(
        token="ghs_app_installation_token_value",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    result = backend.publish(check_run_payload=_payload(), dry_run=False)
    assert result.ok is True
    assert result.remote_verification_status == "verified"
    post = next(c for c in transport.calls if c["method"] == "POST")
    assert post["url"].endswith(f"/repos/{EXPECTED_REPOSITORY}/check-runs")
    assert post["headers"]["Accept"] == "application/vnd.github+json"
    assert post["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
    assert post["headers"]["Authorization"] == "[REDACTED]"
    assert post["body"]["name"] == CHECK_RUN_NAME
    assert post["body"]["head_sha"] == SHA
    assert post["body"]["external_id"] == EXTERNAL_ID


def test_auth_errors_map_to_authentication_error():
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(401, {"message": "bad creds"}, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(AuthenticationError):
        backend.publish(check_run_payload=_payload(), dry_run=False)


def test_404_and_422_map_to_github_api_error():
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(422, {"message": "invalid"}, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(GitHubApiError, match="422"):
        backend.publish(check_run_payload=_payload(), dry_run=False)


def test_rate_limit_fails_closed():
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(
            403,
            {"message": "API rate limit exceeded"},
            {"x-ratelimit-remaining": "0"},
        )
    )
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(GitHubApiError, match="rate limit"):
        backend.list_check_runs_for_sha(SHA)


def test_timeout_fails_closed():
    def boom(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> GitHubResponse:
        raise TimeoutError("timed out")

    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=boom,
    )
    with pytest.raises(GitHubApiError, match="timed out"):
        backend.list_check_runs_for_sha(SHA)


def test_remote_app_id_match_passes():
    transport = FakeTransport()
    existing = _remote_check_run()
    transport.responses.append(GitHubResponse(200, {"check_runs": [existing]}, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    result = backend.publish(check_run_payload=_payload(), dry_run=False)
    assert result.idempotent_noop is True
    assert result.github_app_id == APP_ID


def test_remote_app_id_missing_fails():
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(201, _remote_check_run(app=None), {}))
    transport.responses.append(GitHubResponse(200, _remote_check_run(app=None), {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(GitHubApiError, match="app identity"):
        backend.publish(check_run_payload=_payload(), dry_run=False)


def test_remote_app_id_mismatch_fails():
    transport = FakeTransport()
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    transport.responses.append(GitHubResponse(200, {"check_runs": []}, {}))
    bad = _remote_check_run(app={"id": 999})
    transport.responses.append(GitHubResponse(201, bad, {}))
    transport.responses.append(GitHubResponse(200, bad, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(GitHubApiError, match="does not match"):
        backend.publish(check_run_payload=_payload(), dry_run=False)


def test_remote_head_sha_mismatch_fails():
    remote = _remote_check_run(head_sha="dddddddddddddddddddddddddddddddddddddddd")
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=FakeTransport(),
    )
    with pytest.raises(GitHubApiError, match="head_sha"):
        backend.verify_remote_check_run(remote, payload=_payload())


def test_remote_name_mismatch_fails():
    remote = _remote_check_run(name="other")
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=FakeTransport(),
    )
    with pytest.raises(GitHubApiError, match="name"):
        backend.verify_remote_check_run(remote, payload=_payload())


def test_remote_conclusion_mismatch_fails():
    remote = _remote_check_run(conclusion="failure")
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=FakeTransport(),
    )
    with pytest.raises(GitHubApiError, match="conclusion"):
        backend.verify_remote_check_run(remote, payload=_payload())


def test_identical_external_id_noop():
    transport = FakeTransport()
    existing = _remote_check_run()
    transport.responses.append(GitHubResponse(200, {"check_runs": [existing]}, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    result = backend.publish(check_run_payload=_payload(), dry_run=False)
    assert result.idempotent_noop is True
    assert not any(c["method"] == "POST" for c in transport.calls)


def test_identical_external_id_other_sha_rejected():
    transport = FakeTransport()
    existing = _remote_check_run(head_sha="dddddddddddddddddddddddddddddddddddddddd")
    transport.responses.append(GitHubResponse(200, {"check_runs": [existing]}, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(PublisherError, match="already bound to SHA"):
        backend.publish(check_run_payload=_payload(), dry_run=False)


def test_identical_external_id_conflicting_conclusion_rejected():
    transport = FakeTransport()
    existing = _remote_check_run(conclusion="failure")
    transport.responses.append(GitHubResponse(200, {"check_runs": [existing]}, {}))
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    with pytest.raises(PublisherError, match="already concluded"):
        backend.publish(check_run_payload=_payload(), dry_run=False)


def test_no_fallback_to_commit_status():
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=FakeTransport(),
    )
    status = StatusPayload(
        sha=SHA, state="success", context=CHECK_RUN_NAME, description="ok"
    )
    with pytest.raises(PublisherError, match="no silent fallback"):
        backend.publish(status_payload=status, dry_run=False)


def test_commit_status_backend_still_works():
    calls: list[dict[str, Any]] = []

    def writer(owner: str, repo: str, sha: str, body: dict[str, Any]) -> dict[str, Any]:
        calls.append({"owner": owner, "repo": repo, "sha": sha, "body": body})
        return {"id": 7, "state": body["state"], "sha": sha, "context": body["context"]}

    client = GitHubStatusClient(token="tok", status_writer=writer)
    backend = CommitStatusBackend(client=client)
    payload = StatusPayload(
        sha=SHA, state="success", context=CHECK_RUN_NAME, description="ok"
    )
    result = backend.publish(status_payload=payload, dry_run=False)
    assert result.ok is True
    assert result.publisher_backend == "commit-status"
    assert calls[0]["body"]["context"] == CHECK_RUN_NAME


def test_dry_run_never_writes_network():
    transport = FakeTransport()
    backend = CheckRunBackend(
        token="tok",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    result = backend.publish(check_run_payload=_payload(), dry_run=True)
    assert result.dry_run is True
    assert transport.calls == []


def test_authorization_header_redacted_in_errors():
    text = redact_text("Authorization: Bearer ghs_secretvalue1234567890")
    assert "ghs_secretvalue1234567890" not in text
    assert "[REDACTED]" in text


def test_token_in_api_error_body_redacted():
    payload = redact_mapping(
        {"message": "bad token ghs_secretvalue1234567890", "authorization": "Bearer x"}
    )
    assert "ghs_secretvalue1234567890" not in json.dumps(payload)
    assert payload["authorization"] == "[REDACTED]"


def test_private_key_like_material_redacted():
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF6PZGBw=\n"
        "-----END RSA PRIVATE KEY-----"
    )
    assert "BEGIN RSA PRIVATE KEY" not in redact_text(pem)
    assert "[REDACTED_PRIVATE_KEY]" in redact_text(pem)


def test_non_canonical_repository_rejected():
    with pytest.raises(PublisherError, match="non-canonical"):
        CheckRunBackend(
            token="tok",
            expected_app_id=APP_ID,
            expected_installation_id=INSTALLATION_ID,
            owner="evil",
            repo="repo",
        )


def test_github_status_client_still_has_no_create_check_run():
    assert not hasattr(GitHubStatusClient, "create_check_run")


def test_unknown_backend_rejected():
    with pytest.raises(PublisherError, match="Unknown publisher backend"):
        build_publisher_backend(backend="webhook")  # type: ignore[arg-type]
