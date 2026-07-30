"""Mock E2E: evidence → Check Run payload → mock POST → readback → ledger (#4170)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ci.publisher import EXPECTED_REPOSITORY
from ci.publisher.backends import CheckRunBackend
from ci.publisher.evidence import build_check_run_payload
from ci.publisher.github_client import GitHubResponse
from ci.publisher.ledger import LedgerEntry, append_entry, load_ledger
from ci.publisher.models import CHECK_RUN_NAME

pytestmark = pytest.mark.unit

SHA = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
RUN_ID = "20260730T150000Z-e2e001"
APP_ID = 424242
INSTALLATION_ID = 313131


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
        parsed = json.loads(body.decode("utf-8")) if body else None
        self.calls.append({"method": method, "url": url, "body": parsed})
        return self.responses.pop(0)


def test_mock_e2e_check_run_publish_and_ledger(tmp_path: Path):
    payload = build_check_run_payload(
        commit_sha=SHA,
        run_id=RUN_ID,
        ok=True,
        started_at_utc="2026-07-30T15:00:00Z",
        ended_at_utc="2026-07-30T15:10:00Z",
        target_url="https://example.test/run",
        optional_skipped=[],
        name=CHECK_RUN_NAME,
    )
    remote = {
        "id": 555,
        "name": CHECK_RUN_NAME,
        "head_sha": SHA,
        "status": "completed",
        "conclusion": "success",
        "external_id": payload.external_id,
        "app": {"id": APP_ID},
    }
    transport = FakeTransport()
    transport.responses.extend(
        [
            GitHubResponse(200, {"check_runs": []}, {}),
            GitHubResponse(200, {"check_runs": []}, {}),
            GitHubResponse(201, remote, {}),
            GitHubResponse(200, remote, {}),
        ]
    )
    backend = CheckRunBackend(
        token="installation-token",
        expected_app_id=APP_ID,
        expected_installation_id=INSTALLATION_ID,
        transport=transport,
    )
    result = backend.publish(check_run_payload=payload, dry_run=False)
    assert result.ok is True
    assert result.remote_id == 555
    assert result.remote_verification_status == "verified"
    assert result.github_app_id == APP_ID

    ledger_path = tmp_path / "published-runs.json"
    append_entry(
        ledger_path,
        LedgerEntry(
            run_id=RUN_ID,
            commit_sha=SHA,
            repository=EXPECTED_REPOSITORY,
            status_context=CHECK_RUN_NAME,
            manifest_sha256="a" * 64,
            published_at_utc="2026-07-30T15:10:01Z",
            state="success",
            publisher_backend="check-run",
            github_object_type="check_run",
            github_check_run_id=result.remote_id,
            github_app_id=APP_ID,
            github_installation_id=INSTALLATION_ID,
            check_run_name=CHECK_RUN_NAME,
            head_sha=SHA,
            external_id=payload.external_id,
            remote_verification_status=result.remote_verification_status,
        ),
    )
    loaded = load_ledger(ledger_path)
    entry = loaded["entries"][0]
    assert entry["publisher_backend"] == "check-run"
    assert entry["github_check_run_id"] == 555
    assert entry["external_id"] == payload.external_id
    assert entry["remote_verification_status"] == "verified"
    assert "token" not in json.dumps(entry).lower()
