"""
test_id: tc_cursor_error_phantom_branch_v1_001
test_name: cursor_terminal_error_claimed_vs_verified_delivery
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/runbooks/agent_control_live_cursor_pilot.md
issue_ref: 4258
pr_ref: 4302
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.agent_control.delivery_verify import (
    claimed_delivery_from_git,
    normalize_cursor_git_branches,
    verify_github_delivery,
)
from tools.agent_control.errors import DispatchError
from tools.agent_control.evidence.redact import sanitize_result_refs
from tools.agent_control.paths import REPO_ROOT
from tools.agent_control.pilot import run_pilot
from tools.agent_control.provider import ProviderRequest
from tools.agent_control.providers.cursor_cloud_api import CursorCloudApiDriver
from tools.agent_control.providers.cursor_common import normalize_cursor_status

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "cursor"
RECORDED = json.loads(
    (FIXTURES / "run_error_phantom_branch.json").read_text(encoding="utf-8")
)
FAKE_KEY = "crsr_test_error_phantom_secret_value_DO_NOT_LEAK"
HEAD = "a" * 40


def _live_manifest(**overrides: object) -> dict:
    data: dict = {
        "schema_id": "cdb.agent_control_pilot_manifest.v1",
        "schema_version": "1.0.0",
        "pilot_id": "acp-live-cursor-4258",
        "scenario_id": "LIVE_ERROR_PHANTOM",
        "agent_id": "acp-live-cursor-pilot",
        "contract_path": "tests/fixtures/agent_control/pilot/contract_live_cursor.json",
        "registry_root": "config/agent-control",
        "head_sha": HEAD,
        "base_sha": "b" * 40,
        "approval_snapshot_path": "tests/fixtures/agent_control/pilot/approval_clean.json",
        "force_approval_head_from_manifest": True,
        "delivery_path_allowlist": [
            "docs/contracts",
            "tools/agent_control",
            "config/agent-control",
            "tests/unit/governance",
            "tests/fixtures/agent_control",
            "knowledge/logs/sessions",
        ],
        "subject": {"repo": "jannekbuengener/Claire_de_Binare", "pr_number": 9999},
        "poll_interval_seconds": 0,
    }
    data.update(overrides)
    return data


@pytest.mark.unit
def test_recorded_error_normalizes_to_failed() -> None:
    status, code = normalize_cursor_status(RECORDED["get_run"]["status"])
    assert status == "FAILED"
    assert code is None or isinstance(code, str)


@pytest.mark.unit
def test_watch_preserves_error_claimed_delivery_never_verified() -> None:
    get_run = RECORDED["get_run"]
    stream_events = list(RECORDED["stream_events"])
    posts: list[str] = []

    def http(*, method, url, json=None, headers=None):
        del headers
        posts.append(f"{method}:{url}")
        if method == "POST" and str(url).endswith("/v1/agents"):
            return {
                "status": 200,
                "json": {
                    "agent": {"id": json["agentId"]},
                    "run": {"id": get_run["id"], "status": "CREATING"},
                },
            }
        if method == "GET" and f"/runs/{get_run['id']}" in str(url):
            return {"status": 200, "json": dict(get_run)}
        raise AssertionError((method, url))

    def sse(*, url, last_event_id=None):
        del url, last_event_id
        return stream_events

    driver = CursorCloudApiDriver(http=http, sse=sse)
    req = ProviderRequest(
        run_id="adr-err",
        contract_id="aec-x",
        contract_digest="sha256:" + "9" * 64,
        agent_id="a",
        prompt_text="recorded error fixture",
        route={
            "repo_url": "https://github.com/jannekbuengener/Claire_de_Binare",
            "starting_ref": "main",
        },
        provider_profile={
            "autoCreatePR": True,
            "workOnCurrentBranch": False,
            "human_go_live": True,
        },
    )
    created = driver.dispatch(req)
    assert created.provider_run_id == get_run["id"]
    assert driver.mutating_posts == 1

    watched = driver.watch(created.provider_run_id)
    assert watched.normalized_status == "FAILED"
    assert watched.error_code == "PROVIDER_RUN_ERROR"
    refs = watched.result_refs or {}
    assert refs.get("delivery_verified") is False
    claimed = refs.get("claimed_delivery") or {}
    assert claimed.get("branch") == "cloud-cursor/cursor-cloud-pilot-marker-3c10"
    assert claimed.get("delivery_verified") is False
    assert refs.get("raw_status") == "ERROR"
    git = normalize_cursor_git_branches(refs)
    assert git.get("branch") == claimed.get("branch")

    diag = driver.read_stream_diagnostics(created.provider_run_id)
    assert any(e.get("event") == "status" for e in diag["events"])
    assert any(e.get("event") == "result" for e in diag["events"])
    assert diag.get("stream_error") is None  # recorded run had no SSE error event

    # Resume/watch again must not create.
    before = driver.mutating_posts
    again = driver.watch(created.provider_run_id)
    assert again.normalized_status == "FAILED"
    assert driver.mutating_posts == before


@pytest.mark.unit
def test_claimed_branch_without_github_object_unverified() -> None:
    claimed = claimed_delivery_from_git(RECORDED["get_run"]["git"])
    assert claimed["branch"] == "cloud-cursor/cursor-cloud-pilot-marker-3c10"
    assert claimed["delivery_verified"] is False

    def gh_404(argv: list[str]) -> dict:
        raise DispatchError("DELIVERY_GITHUB_QUERY_FAILED", "Not Found (HTTP 404)")

    with pytest.raises(DispatchError) as exc:
        verify_github_delivery(
            expected_repo="jannekbuengener/Claire_de_Binare",
            branch=claimed["branch"],
            runner=gh_404,
        )
    assert exc.value.code == "DELIVERY_GITHUB_QUERY_FAILED"


@pytest.mark.unit
def test_missing_commit_sha_blocks_delivery() -> None:
    def gh_no_sha(argv: list[str]) -> dict:
        return {"name": "cloud-cursor/x", "commit": {"sha": None}}

    result = verify_github_delivery(
        expected_repo="jannekbuengener/Claire_de_Binare",
        branch="cloud-cursor/x",
        runner=gh_no_sha,
    )
    assert result.ok is False
    assert result.code == "DELIVERY_HEAD_INVALID"


@pytest.mark.unit
def test_redaction_strips_auth_token_fields() -> None:
    dirty = {
        "agent_id": RECORDED["agent_id"],
        "Authorization": "Bearer crsr_should_never_persist",
        "api_key": FAKE_KEY,
        "claimed_delivery": {
            "branch": "cloud-cursor/cursor-cloud-pilot-marker-3c10",
            "delivery_verified": False,
        },
        "delivery_verified": False,
    }
    clean = sanitize_result_refs(dirty)
    assert "Authorization" not in clean
    assert "api_key" not in clean
    assert clean["claimed_delivery"]["branch"].startswith("cloud-cursor/")
    blob = json.dumps(clean)
    assert FAKE_KEY not in blob
    assert "crsr_should_never_persist" not in blob


@pytest.mark.unit
def test_pilot_terminal_error_never_awaits_approval(tmp_path: Path) -> None:
    get_run = RECORDED["get_run"]
    posts: list[str] = []

    def http(*, method, url, json=None, headers=None):
        del headers
        posts.append(f"{method}:{url}")
        if method == "POST" and str(url).endswith("/v1/agents"):
            return {
                "status": 200,
                "json": {
                    "agent": {"id": json["agentId"]},
                    "run": {"id": get_run["id"], "status": "CREATING"},
                },
            }
        if method == "GET" and "/runs/" in str(url):
            return {"status": 200, "json": dict(get_run)}
        raise AssertionError((method, url))

    def sse(*, url, last_event_id=None):
        del url, last_event_id
        return list(RECORDED["stream_events"])

    def gh_boom(argv: list[str]) -> dict:
        raise AssertionError(f"delivery verify must not run on ERROR: {argv}")

    report = run_pilot(
        _live_manifest(),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=tmp_path / "state.json",
        http_transport=http,
        sse_transport=sse,
        gh_runner=gh_boom,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    assert report["final_status"] in {"FAILED", "BLOCKED", "HOLD"}
    assert report.get("approval_recommendation") != "APPROVE_RECOMMENDED"
    terminal = [s for s in report["step_results"] if s["step"] == "provider_terminal"]
    assert terminal
    detail = terminal[0]["detail"]
    assert detail.get("delivery_verified") is False
    assert detail.get("normalized_status") == "FAILED"
    claimed = detail.get("claimed_delivery") or {}
    assert claimed.get("branch") == "cloud-cursor/cursor-cloud-pilot-marker-3c10"
    delivery_steps = [
        s for s in report["step_results"] if s["step"] == "delivery_verify"
    ]
    assert not delivery_steps
    await_steps = [
        s
        for s in report["step_results"]
        if s["step"] == "provider_watch"
        and (s.get("detail") or {}).get("state") == "AWAITING_APPROVAL"
    ]
    assert not await_steps
    create_posts = [
        p for p in posts if p.startswith("POST:") and p.endswith("/v1/agents")
    ]
    assert len(create_posts) == 1
    blob = json.dumps(report)
    assert FAKE_KEY not in blob


@pytest.mark.unit
def test_resume_terminal_error_zero_creates(tmp_path: Path) -> None:
    get_run = RECORDED["get_run"]
    creates = {"n": 0}

    def http(*, method, url, json=None, headers=None):
        del headers
        if method == "POST" and str(url).endswith("/v1/agents"):
            creates["n"] += 1
            return {
                "status": 200,
                "json": {
                    "agent": {"id": json["agentId"]},
                    "run": {
                        "id": get_run["id"],
                        "status": "ERROR",
                        "git": get_run["git"],
                    },
                },
            }
        if method == "GET" and "/runs/" in str(url):
            return {"status": 200, "json": dict(get_run)}
        raise AssertionError((method, url))

    def sse(*, url, last_event_id=None):
        del url, last_event_id
        return list(RECORDED["stream_events"])

    state = tmp_path / "state.json"
    first = run_pilot(
        _live_manifest(scenario_id="LIVE_ERROR_CREATE"),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=state,
        http_transport=http,
        sse_transport=sse,
        gh_runner=lambda argv: (_ for _ in ()).throw(AssertionError(argv)),
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    assert creates["n"] == 1
    # Prefer report run_id; fall back to dispatch step detail for older shapes.
    run_id = first.get("run_id")
    if not run_id:
        for step in first["step_results"]:
            if step["step"] == "preflight_dispatch":
                run_id = (step.get("detail") or {}).get("run_id")
    assert run_id
    assert first["final_status"] in {"FAILED", "BLOCKED", "HOLD"}

    second = run_pilot(
        _live_manifest(scenario_id="LIVE_ERROR_RESUME"),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=state,
        resume_run_id=run_id,
        http_transport=http,
        sse_transport=sse,
        gh_runner=lambda argv: (_ for _ in ()).throw(AssertionError(argv)),
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    assert creates["n"] == 1
    assert second["provider_call_count"] == 0
    blob = json.dumps(second)
    assert FAKE_KEY not in blob
