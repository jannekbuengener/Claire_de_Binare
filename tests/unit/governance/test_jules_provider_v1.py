"""
test_id: tc_jules_provider_v1_001
test_name: jules_provider_adapter_fail_closed
test_type: Bauteil-Test
cdb_area: governance
rule_ref: knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
decision_ref: Jules API provider adapter
issue_ref: 4461
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.agent_control.dispatch import dispatch_run, watch_run
from tools.agent_control.errors import DispatchError
from tools.agent_control.load import load_registry_document
from tools.agent_control.provider import (
    ProviderRequest,
    ProviderResult,
    provider_registry,
    sanitize_provider_result,
)
from tools.agent_control.providers.capability import (
    classify_drift,
    offline_capability_snapshot,
    snapshot_blocks_dispatch,
)
from tools.agent_control.providers.factory import registered_provider_ids
from tools.agent_control.providers.jules_api import JulesApiDriver
from tools.agent_control.providers.jules_live_http import _api_key_header_from_env
from tools.agent_control.run_store import InMemoryRunStore
from tools.agent_execution_contract.hashing import attach_digest
from tools.agent_execution_contract.work_order import compute_prompt_digest

REPO = Path(__file__).resolve().parents[3]
EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_dispatch"
PROMPT_REF = "tests/fixtures/agent_control/cursor/prompt_ok.txt"
PROMPT_PATH = REPO / PROMPT_REF


def _request(*, open_pr: bool = False) -> ProviderRequest:
    return ProviderRequest(
        run_id="adr-jules",
        contract_id="aec-jules",
        contract_digest="sha256:" + "1" * 64,
        agent_id="acp-jules-api-adapter",
        prompt_text="Implement the bounded slice.",
        effective_permissions={"open_pr": open_pr},
        provider_profile={
            "source": "sources/github/jannekbuengener/Claire_de_Binare",
            "starting_branch": "main",
            "require_plan_approval": True,
            "auto_create_pr": True,
        },
        route={"lane": "agent-skills"},
        budget={
            "network_policy": {
                "mode": "allowlist",
                "allowed_domains": ["jules.googleapis.com"],
            }
        },
    )


def _jules_contract(*, open_pr: bool = False) -> dict:
    payload = json.loads(
        (EXAMPLES / "positive_mock_dispatch_contract.json").read_text(encoding="utf-8")
    )
    payload["schema_version"] = "1.1.0"
    payload["contract_id"] = "aec-issue-4461-jules-recorded"
    payload["issue"]["number"] = 4461
    payload["issue"]["title"] = "[AGENTS][JULES] Add Jules API provider skill"
    payload["environment"]["provider_profile"]["provider_id"] = "jules-api"
    payload["environment"]["provider_profile"]["profile_name"] = "jules-api.v1"
    payload["environment"]["secret_references"] = [
        {"class": "provider_api_key", "ref": "env:JULES_API_KEY"}
    ]
    payload["permissions"]["open_pr"] = open_pr
    domains = payload["budget"]["network_policy"]["allowed_domains"]
    if "jules.googleapis.com" not in domains:
        domains.append("jules.googleapis.com")
    paths = payload["execution_scope"]["allowed_paths"]
    if "tests/fixtures/agent_control/cursor/*" not in paths:
        paths.append("tests/fixtures/agent_control/cursor/*")
    text = PROMPT_PATH.read_text(encoding="utf-8")
    payload["provider_work_order"] = {
        "prompt_ref": PROMPT_REF,
        "source_commit": "a" * 40,
        "prompt_digest": compute_prompt_digest(text),
    }
    return attach_digest(payload)


@pytest.mark.unit
def test_factory_registry_and_capability_baseline_include_jules() -> None:
    assert "jules-api" in registered_provider_ids()
    assert provider_registry()["jules-api"] == "JulesApiDriver"
    baseline = offline_capability_snapshot("jules-api")
    assert baseline["api_or_sdk_version"] == "v1alpha"
    assert "cancel" in baseline["unsupported_operations"]
    assert baseline["drift_classification"] == "MATCH"


@pytest.mark.unit
def test_jules_capability_version_or_required_operation_drift_blocks() -> None:
    baseline = offline_capability_snapshot("jules-api")
    observed = deepcopy(baseline)
    observed["api_or_sdk_version"] = "v2"
    assert classify_drift(baseline, observed) == "BREAKING"
    observed = deepcopy(baseline)
    observed["supported_operations"].remove("approve_plan")
    drift = classify_drift(baseline, observed)
    assert drift == "MISSING_REQUIRED_CAPABILITY"
    observed["drift_classification"] = drift
    assert snapshot_blocks_dispatch(observed)


@pytest.mark.unit
def test_dispatch_sets_plan_gate_and_attenuates_auto_pr() -> None:
    seen: list[dict] = []

    def http(*, method, url, json=None, headers=None):
        assert method == "POST"
        assert url.endswith("/v1alpha/sessions")
        seen.append(deepcopy(json))
        return {
            "status": 200,
            "json": {
                "name": "sessions/123",
                "id": "123",
                "state": "AWAITING_PLAN_APPROVAL",
                "url": "https://jules.google.com/session/123",
            },
        }

    driver = JulesApiDriver(http=http)
    blocked_pr = driver.dispatch(_request(open_pr=False))
    assert blocked_pr.normalized_status == "RUNNING"
    assert seen[-1]["requirePlanApproval"] is True
    assert "automationMode" not in seen[-1]
    assert blocked_pr.result_refs["awaiting_plan_approval"] is True

    allowed_pr = driver.dispatch(_request(open_pr=True))
    assert allowed_pr.normalized_status == "RUNNING"
    assert seen[-1]["automationMode"] == "AUTO_CREATE_PR"


@pytest.mark.unit
def test_watch_normalizes_activities_and_pr_handoff_without_message_text() -> None:
    def http(*, method, url, json=None, headers=None):
        assert method == "GET"
        if url.endswith("/v1alpha/sessions/123"):
            return {
                "status": 200,
                "json": {
                    "name": "sessions/123",
                    "id": "123",
                    "state": "COMPLETED",
                    "outputs": [
                        {
                            "pullRequest": {
                                "url": "https://github.com/jannekbuengener/Claire_de_Binare/pull/9999",
                                "title": "Jules delivery",
                                "description": "not persisted",
                            }
                        }
                    ],
                },
            }
        assert "/activities?pageSize=100" in url
        return {
            "status": 200,
            "json": {
                "activities": [
                    {
                        "name": "sessions/123/activities/a1",
                        "id": "a1",
                        "originator": "agent",
                        "agentMessaged": {"agentMessage": "sensitive free-form text"},
                    },
                    {
                        "name": "sessions/123/activities/a2",
                        "id": "a2",
                        "originator": "agent",
                        "planGenerated": {
                            "plan": {
                                "id": "plan-1",
                                "steps": [
                                    {
                                        "id": "s1",
                                        "index": 0,
                                        "title": "Implement adapter",
                                    }
                                ],
                            }
                        },
                    },
                ]
            },
        }

    result = JulesApiDriver(http=http).watch("sessions/123")
    assert result.normalized_status == "SUCCEEDED"
    assert result.result_refs["pull_requests"][0]["url"].endswith("/pull/9999")
    rendered = json.dumps(result.result_refs)
    assert "not persisted" not in rendered
    assert "sensitive free-form text" not in rendered
    assert result.result_refs["activities"]["latest_plan"]["id"] == "plan-1"


@pytest.mark.unit
def test_plan_approval_requires_wait_state_and_follow_up_reuses_bound_session() -> None:
    calls: list[tuple[str, str, dict | None]] = []
    states = iter(
        [
            "IN_PROGRESS",
            "AWAITING_PLAN_APPROVAL",
            "IN_PROGRESS",
            "PAUSED",
            "IN_PROGRESS",
        ]
    )

    def http(*, method, url, json=None, headers=None):
        calls.append((method, url, deepcopy(json)))
        if method == "GET" and url.endswith("/activities?pageSize=100"):
            return {"status": 200, "json": {"activities": []}}
        if method == "GET":
            return {
                "status": 200,
                "json": {"name": "sessions/123", "id": "123", "state": next(states)},
            }
        return {"status": 200, "json": {}}

    driver = JulesApiDriver(http=http)
    with pytest.raises(DispatchError) as exc:
        driver.approve_plan("sessions/123")
    assert exc.value.code == "PROVIDER_PLAN_APPROVAL_INVALID_STATE"

    approved = driver.approve_plan("sessions/123")
    assert approved.normalized_status == "RUNNING"
    assert any(url.endswith("sessions/123:approvePlan") for _, url, _ in calls)

    followed = driver.follow_up(
        "sessions/123",
        ProviderRequest(
            run_id="adr-jules",
            contract_id="aec-jules",
            contract_digest="sha256:" + "1" * 64,
            agent_id="a",
            prompt_text="Use the existing review feedback.",
        ),
    )
    assert followed.normalized_status == "RUNNING"
    assert any(
        method == "POST"
        and url.endswith("sessions/123:sendMessage")
        and body == {"prompt": "Use the existing review feedback."}
        for method, url, body in calls
    )


@pytest.mark.unit
def test_cancel_is_fail_closed_without_network_call() -> None:
    driver = JulesApiDriver(
        http=lambda **kwargs: (_ for _ in ()).throw(AssertionError("no call"))
    )
    result = driver.cancel("sessions/123", "TIMEOUT")
    assert result.normalized_status == "UNKNOWN"
    assert result.cancel_confirmed is False
    assert result.error_code == "PROVIDER_CANCEL_UNSUPPORTED"
    assert driver.mutating_posts == 0


@pytest.mark.unit
def test_http_errors_are_classified_without_blind_retry() -> None:
    for status, code in (
        (401, "AUTH_BLOCKED"),
        (403, "AUTH_BLOCKED"),
        (429, "PROVIDER_RATE_LIMITED"),
    ):
        driver = JulesApiDriver(http=lambda **kwargs: {"status": status, "json": {}})
        with pytest.raises(DispatchError) as exc:
            driver.dispatch(_request())
        assert exc.value.code == code
        assert driver.dispatch_calls == 1

    driver = JulesApiDriver(http=lambda **kwargs: {"status": 503, "json": {}})
    with pytest.raises(DispatchError) as exc:
        driver.dispatch(_request())
    assert exc.value.code == "PROVIDER_DISPATCH_OUTCOME_UNKNOWN"
    assert driver.dispatch_calls == 1


def test_jules_api_key_is_runtime_header_only_and_shared_sanitizer_rejects_it() -> None:
    headers = _api_key_header_from_env({"JULES_API_KEY": "example-test-key"})
    assert headers == {"X-Goog-Api-Key": "example-test-key"}
    with pytest.raises(DispatchError) as exc:
        sanitize_provider_result(
            ProviderResult(
                provider_id="jules-api",
                provider_run_id="sessions/123",
                normalized_status="RUNNING",
                result_refs={"X-Goog-Api-Key": "example-test-key"},
            )
        )
    assert exc.value.code == "DISPATCH_PROVIDER_SECRET_PAYLOAD"


@pytest.mark.unit
def test_recorded_acp_dispatch_uses_contract_permissions_and_never_persists_prompt() -> (
    None
):
    registry = load_registry_document(REPO / "config" / "agent-control")
    contract = _jules_contract(open_pr=False)
    text = PROMPT_PATH.read_text(encoding="utf-8")
    posted: list[dict] = []

    def http(*, method, url, json=None, headers=None):
        if method == "POST" and url.endswith("/v1alpha/sessions"):
            posted.append(deepcopy(json))
            return {
                "status": 200,
                "json": {
                    "name": "sessions/4242",
                    "id": "4242",
                    "state": "AWAITING_PLAN_APPROVAL",
                },
            }
        raise AssertionError((method, url))

    store = InMemoryRunStore()
    result = dispatch_run(
        contract,
        registry,
        "acp-jules-api-adapter",
        store,
        dry_run=False,
        # Legacy compatibility gate in dispatch_run; provider preflight treats
        # this as recorded/fake external transport for Jules too.
        allow_recorded_cursor=True,
        provider=JulesApiDriver(http=http),
        prompt_text_override=text,
    )
    run = result["run"]
    assert run["provider_id"] == "jules-api"
    assert run["state"] == "DISPATCHED"
    assert run.get("prompt_text") is None
    assert run["prompt_digest"].startswith("sha256:")
    assert posted[0]["requirePlanApproval"] is True
    assert "automationMode" not in posted[0]


@pytest.mark.unit
def test_completed_jules_pr_is_handoff_not_acp_pass_without_verified_receipt() -> None:
    registry = load_registry_document(REPO / "config" / "agent-control")
    contract = _jules_contract(open_pr=True)
    text = PROMPT_PATH.read_text(encoding="utf-8")

    def http(*, method, url, json=None, headers=None):
        if method == "POST" and url.endswith("/v1alpha/sessions"):
            assert json["automationMode"] == "AUTO_CREATE_PR"
            return {
                "status": 200,
                "json": {"name": "sessions/777", "id": "777", "state": "QUEUED"},
            }
        if method == "GET" and url.endswith("/v1alpha/sessions/777"):
            return {
                "status": 200,
                "json": {
                    "name": "sessions/777",
                    "id": "777",
                    "state": "COMPLETED",
                    "outputs": [
                        {
                            "pullRequest": {
                                "url": "https://github.com/jannekbuengener/Claire_de_Binare/pull/9999",
                                "title": "Delivery",
                                "description": "provider text",
                            }
                        }
                    ],
                },
            }
        if method == "GET" and "/activities?pageSize=100" in url:
            return {"status": 200, "json": {"activities": []}}
        raise AssertionError((method, url))

    store = InMemoryRunStore()
    driver = JulesApiDriver(http=http)
    dispatched = dispatch_run(
        contract,
        registry,
        "acp-jules-api-adapter",
        store,
        dry_run=False,
        allow_recorded_cursor=True,
        provider=driver,
        prompt_text_override=text,
    )
    watched = watch_run(dispatched["run"]["run_id"], store, provider=driver)
    assert watched["state"] == "BLOCKED"
    assert watched["terminal_code"] == "DISPATCH_DELIVERY_RECEIPT_MISSING"
    assert watched["result_refs"]["pull_requests"][0]["url"].endswith("/pull/9999")
