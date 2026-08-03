"""
test_id: tc_agent_control_live_pilot_v1_001
test_name: agent_control_live_cursor_pilot_v1
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/runbooks/agent_control_live_cursor_pilot.md
decision_ref: cdb.agent_control_live_cursor_pilot
issue_ref: 4258
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.agent_control.cli import main as cli_main
from tools.agent_control.errors import AgentControlError
from tools.agent_control.pilot import PilotError, run_pilot
from tools.agent_control.paths import REPO_ROOT
from tools.agent_control.pilot_report import verify_report

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "agent_control" / "pilot"
HEAD = "a" * 40
FAKE_KEY = "crsr_test_live_pilot_secret_value_DO_NOT_LEAK"


def _live_manifest(**overrides: object) -> dict:
    data: dict = {
        "schema_id": "cdb.agent_control_pilot_manifest.v1",
        "schema_version": "1.0.0",
        "pilot_id": "acp-live-cursor-4258",
        "scenario_id": "LIVE_P1",
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
        ],
        "subject": {"repo": "jannekbuengener/Claire_de_Binare", "pr_number": 9999},
    }
    data.update(overrides)
    return data


def _fake_http_finished(*, method, url, json=None, headers=None):
    del headers
    if method == "POST" and str(url).endswith("/v1/agents"):
        assert json is not None
        assert "agentId" in json
        # Without human_go on profile+driver, autoCreatePR stays false.
        return {
            "status": 200,
            "json": {
                "agent": {"id": json["agentId"]},
                "run": {
                    "id": "run-live-1",
                    "status": "FINISHED",
                    "git": {
                        "branches": [
                            {
                                "repoUrl": "github.com/jannekbuengener/Claire_de_Binare",
                                "branch": "batch/agent-skills-issue-4258",
                                "prUrl": (
                                    "https://github.com/jannekbuengener/"
                                    "Claire_de_Binare/pull/9999"
                                ),
                            }
                        ]
                    },
                },
            },
        }
    if method == "GET" and "/runs/" in str(url):
        return {
            "status": 200,
            "json": {
                "status": "FINISHED",
                "git": {
                    "branches": [
                        {
                            "repoUrl": "github.com/jannekbuengener/Claire_de_Binare",
                            "branch": "batch/agent-skills-issue-4258",
                            "prUrl": (
                                "https://github.com/jannekbuengener/"
                                "Claire_de_Binare/pull/9999"
                            ),
                        }
                    ]
                },
            },
        }
    if method == "GET" and "/v1/agents/" in str(url):
        return {
            "status": 200,
            "json": {"id": "bc-existing", "latestRunId": "run-live-1"},
        }
    raise AssertionError(f"unexpected http call {method} {url}")


def _gh_ok(argv: list[str]) -> dict:
    del argv
    return {
        "number": 9999,
        "state": "OPEN",
        "headRefOid": HEAD,
        "baseRefOid": "b" * 40,
        "headRefName": "batch/agent-skills-issue-4258",
        "files": [
            {"path": "docs/contracts/agent_pilot/note.md"},
            {"path": "tools/agent_control/pilot.py"},
        ],
        "url": "https://github.com/jannekbuengener/Claire_de_Binare/pull/9999",
        "headRepository": {"nameWithOwner": "jannekbuengener/Claire_de_Binare"},
    }


def _gh_empty(argv: list[str]) -> dict:
    data = _gh_ok(argv)
    data["files"] = []
    return data


@pytest.mark.unit
def test_n1_no_credential_precondition_blocked_no_dispatch() -> None:
    report = run_pilot(
        _live_manifest(scenario_id="N1"),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        http_transport=_fake_http_finished,
        gh_runner=_gh_ok,
        credential_env={},  # no CURSOR_API_KEY
    )
    assert report["final_status"] == "BLOCKED"
    assert report["provider_call_count"] == 0
    codes = [
        (s.get("detail") or {}).get("code")
        for s in report["step_results"]
        if s["step"] == "credential_precondition"
    ]
    assert "PRECONDITION_BLOCKED" in codes
    assert "live_cursor_pilot" in report["limitations"]
    assert "mock_provider_only" not in report["limitations"]
    blob = json.dumps(report)
    assert FAKE_KEY not in blob


@pytest.mark.unit
def test_no_human_go_raises_pilot_error() -> None:
    with pytest.raises(PilotError) as exc:
        run_pilot(
            _live_manifest(),
            repo_root=REPO_ROOT,
            provider_id="cursor-cloud-api",
            human_go_live_cursor=False,
            credential_env={"CURSOR_API_KEY": FAKE_KEY},
        )
    assert exc.value.code == "PILOT_HUMAN_GO_REQUIRED"


@pytest.mark.unit
def test_cli_no_human_go_fail_closed() -> None:
    code = cli_main(
        [
            "pilot",
            "run",
            "--manifest",
            str(FIXTURES / "p1_pass.manifest.json"),
            "--provider",
            "cursor-cloud-api",
        ]
    )
    assert code != 0


@pytest.mark.unit
def test_positive_recorded_awaiting_approval_no_network(tmp_path: Path) -> None:
    state = tmp_path / "runstore.json"
    report = run_pilot(
        _live_manifest(),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=state,
        http_transport=_fake_http_finished,
        gh_runner=_gh_ok,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    verify_report(report)
    assert report["final_status"] in {"PASS", "HOLD"}
    assert report["provider_call_count"] == 1
    watch = [s for s in report["step_results"] if s["step"] == "provider_watch"]
    assert watch and watch[0]["detail"]["state"] == "AWAITING_APPROVAL"
    assert "awaiting_approval_operator_handoff" in report["limitations"]
    assert "live_cursor_pilot" in report["limitations"]
    assert "not_live_cursor" not in report["limitations"]
    assert "mock_provider_only" not in report["limitations"]
    blob = json.dumps(report)
    assert FAKE_KEY not in blob


@pytest.mark.unit
def test_idempotent_resume_reuses_provider_run_id(tmp_path: Path) -> None:
    state = tmp_path / "runstore.json"
    first = run_pilot(
        _live_manifest(),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=state,
        http_transport=_fake_http_finished,
        gh_runner=_gh_ok,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    run_id = first["run_id"]
    assert run_id
    first_watch = [s for s in first["step_results"] if s["step"] == "provider_watch"][0]
    provider_run_id = first_watch["detail"]["provider_run_id"]

    second = run_pilot(
        _live_manifest(scenario_id="LIVE_RESUME"),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=state,
        resume_run_id=run_id,
        http_transport=_fake_http_finished,
        gh_runner=_gh_ok,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    assert second["run_id"] == run_id
    # Resume skips dispatch → zero new provider dispatch calls on fresh driver.
    assert second["provider_call_count"] == 0
    second_watch = [s for s in second["step_results"] if s["step"] == "provider_watch"]
    assert second_watch
    assert second_watch[0]["detail"]["provider_run_id"] == provider_run_id


@pytest.mark.unit
def test_delivery_empty_blocks_approval_pass(tmp_path: Path) -> None:
    report = run_pilot(
        _live_manifest(scenario_id="N_DELIVERY_EMPTY"),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=tmp_path / "state.json",
        http_transport=_fake_http_finished,
        gh_runner=_gh_empty,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    assert report["final_status"] == "BLOCKED"
    assert report.get("approval_recommendation") != "APPROVE_RECOMMENDED"
    codes = [
        (s.get("detail") or {}).get("code")
        for s in report["step_results"]
        if s["step"] == "delivery_verify"
    ]
    assert "DELIVERY_EMPTY" in codes
    blob = json.dumps(report)
    assert FAKE_KEY not in blob


@pytest.mark.unit
def test_secret_redaction_in_report_json(tmp_path: Path) -> None:
    report = run_pilot(
        _live_manifest(),
        repo_root=REPO_ROOT,
        provider_id="cursor-cloud-api",
        human_go_live_cursor=True,
        state_path=tmp_path / "state.json",
        http_transport=_fake_http_finished,
        gh_runner=_gh_ok,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
    )
    serialized = json.dumps(report, indent=2, sort_keys=True)
    assert FAKE_KEY not in serialized
    assert "CURSOR_API_KEY" not in serialized or FAKE_KEY not in serialized
