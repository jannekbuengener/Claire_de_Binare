"""CLI policy-gate / PR / dirty-worktree enforcement for status publisher."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ci.lib.evidence import StageResult, build_manifest, hash_artifacts, write_manifest
from ci.publisher import DEFAULT_STATUS_CONTEXT, PREVIEW_STATUS_CONTEXT
from ci.publisher.cli import (
    cmd_dry_run,
    cmd_publish,
    enforce_policy_gate_for_pr,
)
from ci.publisher.exceptions import PublisherError
from ci.publisher.github_client import GitHubResponse, GitHubStatusClient

pytestmark = pytest.mark.unit

SHA = "dddddddddddddddddddddddddddddddddddddddd"
OTHER_SHA = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

SAFE_WORKFLOW = """
name: Safe
on:
  pull_request:
permissions:
  contents: read
jobs:
  j:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""


def _stage(name: str, status: str = "PASS", *, required: bool = True) -> StageResult:
    return StageResult(
        name=name,
        status=status,  # type: ignore[arg-type]
        exit_code=0 if status in ("PASS", "SKIPPED") else 1,
        started_at_utc="2026-07-27T12:00:00Z",
        ended_at_utc="2026-07-27T12:00:01Z",
        duration_seconds=1.0,
        command_summary=[f"cmd-{name}"],
        log_path=f"logs/{name}.log",
        skip_reason="fast profile" if status == "SKIPPED" else None,
        required=required,
    )


def _write_pass_evidence(
    tmp_path: Path, *, sha: str = SHA, run_id: str = "testrun01"
) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    log = run_dir / "logs"
    log.mkdir()
    (log / "lint.log").write_text("ok\n", encoding="utf-8")
    report = run_dir / "reports"
    report.mkdir()
    (report / "check-matrix.json").write_text("{}\n", encoding="utf-8")
    hashes = hash_artifacts(
        [log / "lint.log", report / "check-matrix.json"], relative_to=run_dir
    )
    ended = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    manifest = build_manifest(
        run_id=run_id,
        commit_sha=sha,
        branch="feat/test",
        dirty_worktree=False,
        started_at_utc="2026-07-27T12:00:00Z",
        ended_at_utc=ended,
        host_platform="test",
        tool_versions={"python": "3.12"},
        docker_version="n/a",
        compose_version="n/a",
        profile="fast",
        stages=[
            _stage("lint"),
            _stage("unit"),
            _stage("docs"),
            _stage("governance"),
            _stage("report"),
            _stage("security", "SKIPPED", required=False),
        ],
        skipped_checks=[],
        artifact_hashes=hashes,
        repo_name="Claire_de_Binare",
    )
    write_manifest(run_dir, manifest)
    return run_dir


def _ns(**kwargs: Any) -> SimpleNamespace:
    base = {
        "evidence_dir": "",
        "commit_sha": SHA,
        "repository": "jannekbuengener/Claire_de_Binare",
        "status_context": DEFAULT_STATUS_CONTEXT,
        "freshness_hours": 24.0,
        "pr_number": 0,
        "target_url": "",
        "ledger": "",
        "repo_root": "",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


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
        if not self.responses:
            raise AssertionError(f"No fake response for {method} {url}")
        return self.responses.pop(0)


def test_cdb_local_ci_without_pr_number_rejects_dry_run(tmp_path: Path, capsys):
    run_dir = _write_pass_evidence(tmp_path)
    args = _ns(
        evidence_dir=str(run_dir),
        repo_root=str(tmp_path),
        ledger=str(tmp_path / "ledger.json"),
        pr_number=0,
        status_context=DEFAULT_STATUS_CONTEXT,
    )
    code = cmd_dry_run(args)
    captured = capsys.readouterr()
    assert code == 1
    assert "REJECT:" in captured.err
    assert "--pr-number" in captured.err


def test_preview_without_pr_number_still_allowed(tmp_path: Path, monkeypatch, capsys):
    run_dir = _write_pass_evidence(tmp_path)
    args = _ns(
        evidence_dir=str(run_dir),
        repo_root=str(tmp_path),
        ledger=str(tmp_path / "ledger.json"),
        pr_number=0,
        status_context=PREVIEW_STATUS_CONTEXT,
    )
    git = SimpleNamespace(
        dirty_worktree=False,
        commit_sha=SHA,
        remote_url="https://github.com/jannekbuengener/Claire_de_Binare.git",
        repo_name="Claire_de_Binare",
    )
    monkeypatch.setattr("ci.publisher.cli.collect_git_info", lambda root: git)
    monkeypatch.setattr("ci.publisher.evidence.collect_git_info", lambda root: git)
    code = cmd_dry_run(args)
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True


def test_policy_fail_rejects_via_enforce_helper():
    transport = FakeTransport()
    # get_pull_request
    transport.responses.append(
        GitHubResponse(
            200,
            {
                "number": 99,
                "title": "docs-only: sneak",
                "labels": [{"name": "docs-only"}],
                "head": {"sha": SHA},
            },
            {},
        )
    )
    # list files
    transport.responses.append(
        GitHubResponse(
            200,
            [
                {"filename": "docs/a.md", "status": "modified"},
                {"filename": "core/x.py", "status": "modified"},
            ],
            {},
        )
    )
    client = GitHubStatusClient(token="token", transport=transport)
    with pytest.raises(PublisherError, match="policy-gate local mirror failed"):
        enforce_policy_gate_for_pr(client, pr_number=99, commit_sha=SHA)


def test_pr_head_mismatch_rejects():
    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(
            200,
            {
                "number": 7,
                "title": "feat: ok",
                "labels": [],
                "head": {"sha": OTHER_SHA},
            },
            {},
        )
    )
    client = GitHubStatusClient(token="token", transport=transport)
    with pytest.raises(PublisherError, match="does not match commit_sha"):
        enforce_policy_gate_for_pr(client, pr_number=7, commit_sha=SHA)


def test_dirty_live_worktree_rejects_publish(tmp_path: Path, monkeypatch, capsys):
    run_dir = _write_pass_evidence(tmp_path)
    ledger = tmp_path / "ledger.json"
    args = _ns(
        evidence_dir=str(run_dir),
        repo_root=str(tmp_path),
        ledger=str(ledger),
        pr_number=42,
        status_context=DEFAULT_STATUS_CONTEXT,
    )

    class StubClient:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def assert_commit_exists(self, sha: str) -> None:
            return None

        def get_pull_request(self, pr_number: int) -> dict[str, Any]:
            return {
                "number": pr_number,
                "title": "feat: ok",
                "labels": [],
                "head": {"sha": SHA},
            }

        def list_pull_request_files(self, pr_number: int) -> list[dict[str, Any]]:
            return [{"filename": "services/risk/service.py", "status": "modified"}]

        def get_repo_file_content(self, path: str, ref: str) -> str:
            return SAFE_WORKFLOW

        def get_pull_request_head_sha(self, pr_number: int) -> str:
            return SHA

        def create_commit_status(self, payload: Any, *, dry_run: bool = False) -> dict:
            raise AssertionError("must not write when dirty")

    clean_then_dirty = {
        "calls": 0,
        "info": SimpleNamespace(
            dirty_worktree=False,
            commit_sha=SHA,
            remote_url="https://github.com/jannekbuengener/Claire_de_Binare.git",
            repo_name="Claire_de_Binare",
        ),
    }

    def _git_info(repo_root: Path) -> SimpleNamespace:
        # First calls (evidence binding) clean; live re-check before write is dirty.
        clean_then_dirty["calls"] += 1
        if clean_then_dirty["calls"] >= 2:
            return SimpleNamespace(
                dirty_worktree=True,
                commit_sha=SHA,
                remote_url=clean_then_dirty["info"].remote_url,
                repo_name="Claire_de_Binare",
            )
        return clean_then_dirty["info"]

    monkeypatch.setattr("ci.publisher.cli.resolve_token", lambda: "token")
    monkeypatch.setattr("ci.publisher.cli.GitHubStatusClient", StubClient)
    monkeypatch.setattr("ci.publisher.cli.collect_git_info", _git_info)
    monkeypatch.setattr("ci.publisher.evidence.collect_git_info", _git_info)

    code = cmd_publish(args)
    captured = capsys.readouterr()
    assert code == 1
    assert "REJECT:" in captured.err
    assert "dirty" in captured.err.lower()


def test_github_client_list_files_and_content():
    import base64

    transport = FakeTransport()
    transport.responses.append(
        GitHubResponse(
            200,
            {"number": 1, "title": "t", "labels": [], "head": {"sha": SHA}},
            {},
        )
    )
    transport.responses.append(
        GitHubResponse(
            200,
            [{"filename": ".github/workflows/x.yml", "status": "modified"}] * 100,
            {},
        )
    )
    transport.responses.append(
        GitHubResponse(
            200,
            [{"filename": "docs/extra.md", "status": "added"}],
            {},
        )
    )
    encoded = base64.b64encode(SAFE_WORKFLOW.encode("utf-8")).decode("ascii")
    transport.responses.append(
        GitHubResponse(200, {"content": encoded, "encoding": "base64"}, {})
    )
    client = GitHubStatusClient(token="token", transport=transport)
    pr = client.get_pull_request(1)
    assert pr["number"] == 1
    files = client.list_pull_request_files(1)
    assert len(files) == 101
    text = client.get_repo_file_content(".github/workflows/x.yml", SHA)
    assert "permissions:" in text
