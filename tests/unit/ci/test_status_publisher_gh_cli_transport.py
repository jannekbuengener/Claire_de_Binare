"""Contract tests for gh-cli-only Commit Status writes (#4202)."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from ci.publisher.exceptions import AuthenticationError, GitHubApiError
from ci.publisher.github_client import GhCliStatusWriter, GitHubStatusClient
from ci.publisher.models import StatusPayload
from ci.publisher.ledger import find_exact_publication
from ci.publisher.cli import _latest_context_status

pytestmark = [pytest.mark.unit, pytest.mark.contract]

SHA = "f" * 40


class FakeRunner:
    def __init__(self, result: subprocess.CompletedProcess[str]) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self, argv: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": argv, **kwargs})
        return self.result


def _payload() -> StatusPayload:
    return StatusPayload(
        sha=SHA,
        state="success",
        context="cdb-local-ci",
        description="Exact SHA evidence verified.",
    )


def test_status_write_uses_gh_api_and_stdin_payload_only() -> None:
    runner = FakeRunner(
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "id": 42,
                    "state": "success",
                    "sha": SHA,
                    "context": "cdb-local-ci",
                }
            ),
            stderr="",
        )
    )
    writer = GhCliStatusWriter(runner=runner)
    client = GitHubStatusClient(
        token="read-token",
        status_writer=writer,
    )
    result = client.create_commit_status(_payload())

    call = runner.calls[0]
    assert call["argv"] == [
        "gh",
        "api",
        "--method",
        "POST",
        f"repos/jannekbuengener/Claire_de_Binare/statuses/{SHA}",
        "--input",
        "-",
    ]
    assert json.loads(call["input"])["context"] == "cdb-local-ci"
    assert "read-token" not in " ".join(call["argv"])
    assert "Authorization" not in call["input"]
    assert result["id"] == 42


def test_realistic_gh_status_response_binds_sha_through_exact_url() -> None:
    runner = FakeRunner(
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "id": 42,
                    "state": "success",
                    "context": "cdb-local-ci",
                    "url": (
                        "https://api.github.com/repos/"
                        "jannekbuengener/Claire_de_Binare/statuses/"
                        f"{SHA}"
                    ),
                }
            ),
            stderr="",
        )
    )
    client = GitHubStatusClient(
        token="read-token", status_writer=GhCliStatusWriter(runner=runner)
    )

    assert client.create_commit_status(_payload())["id"] == 42


def test_gh_permission_failure_is_fail_closed_and_redacted() -> None:
    runner = FakeRunner(
        subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="HTTP 403: token ghp_not-for-logs",
        )
    )
    writer = GhCliStatusWriter(runner=runner)
    client = GitHubStatusClient(token="read-token", status_writer=writer)
    with pytest.raises(AuthenticationError, match="permission"):
        client.create_commit_status(_payload())


def test_malformed_gh_response_is_not_reported_as_success() -> None:
    runner = FakeRunner(
        subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="not-json",
            stderr="",
        )
    )
    writer = GhCliStatusWriter(runner=runner)
    client = GitHubStatusClient(token="read-token", status_writer=writer)
    with pytest.raises(GitHubApiError, match="response"):
        client.create_commit_status(_payload())


@pytest.mark.parametrize(
    "response",
    [
        {"id": 42, "state": "success", "sha": "e" * 40, "context": "cdb-local-ci"},
        {
            "id": 42,
            "state": "success",
            "context": "cdb-local-ci",
            "url": (
                "https://api.github.com/repos/"
                "jannekbuengener/Claire_de_Binare/statuses/"
                f"{'e' * 40}"
            ),
        },
        {"id": 42, "state": "success", "sha": SHA, "context": "check-run-lookalike"},
        {"id": 42, "state": "success", "sha": SHA},
    ],
)
def test_gh_response_identity_mismatch_fails_closed(
    response: dict[str, Any],
) -> None:
    runner = FakeRunner(
        subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(response), stderr=""
        )
    )
    client = GitHubStatusClient(
        token="read-token", status_writer=GhCliStatusWriter(runner=runner)
    )
    with pytest.raises(GitHubApiError, match="does not match"):
        client.create_commit_status(_payload())


def test_dry_run_never_invokes_gh() -> None:
    runner = FakeRunner(
        subprocess.CompletedProcess(args=[], returncode=0, stdout="{}", stderr="")
    )
    client = GitHubStatusClient(
        token="read-token",
        status_writer=GhCliStatusWriter(runner=runner),
    )
    result = client.create_commit_status(_payload(), dry_run=True)
    assert result["dry_run"] is True
    assert runner.calls == []


def test_identical_ledger_evidence_is_detected_for_idempotent_noop() -> None:
    entry = {
        "run_id": "run-1",
        "commit_sha": SHA,
        "repository": "jannekbuengener/Claire_de_Binare",
        "status_context": "cdb-local-ci",
        "manifest_sha256": "b" * 64,
        "state": "success",
        "published_at_utc": "2026-07-30T00:00:00Z",
        "github_status_id": 42,
    }
    found = find_exact_publication(
        {"entries": [entry]},
        run_id="run-1",
        commit_sha=SHA,
        repository="jannekbuengener/Claire_de_Binare",
        status_context="cdb-local-ci",
        manifest_sha256="b" * 64,
        state="success",
    )
    assert found == entry


def test_latest_context_status_does_not_reuse_older_success() -> None:
    latest = _latest_context_status(
        [
            {
                "id": 42,
                "context": "cdb-local-ci",
                "state": "success",
                "updated_at": "2026-07-30T10:00:00Z",
            },
            {
                "id": 43,
                "context": "cdb-local-ci",
                "state": "failure",
                "updated_at": "2026-07-30T11:00:00Z",
            },
        ],
        context="cdb-local-ci",
    )
    assert latest is not None
    assert latest["id"] == 43
    assert latest["state"] == "failure"


def test_missing_status_timestamps_disable_idempotent_noop() -> None:
    assert (
        _latest_context_status(
            [{"context": "cdb-local-ci", "state": "success"}],
            context="cdb-local-ci",
        )
        is None
    )
