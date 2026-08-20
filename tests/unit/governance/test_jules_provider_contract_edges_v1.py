"""
test_id: tc_jules_provider_v1_002
test_name: jules_provider_contract_edges
test_type: Bauteil-Test
cdb_area: governance
rule_ref: knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
decision_ref: Jules API provider adapter edge contracts
issue_ref: 4461
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json

import pytest

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import ProviderRequest
from tools.agent_control.providers.jules_api import JulesApiDriver


def _request() -> ProviderRequest:
    return ProviderRequest(
        run_id="adr-jules-timeout",
        contract_id="aec-jules-timeout",
        contract_digest="sha256:" + "2" * 64,
        agent_id="acp-jules-api-adapter",
        prompt_text="Execute the bounded recorded work order.",
        effective_permissions={"open_pr": False},
        provider_profile={
            "require_plan_approval": True,
            "auto_create_pr": True,
        },
        route={"lane": "agent-skills", "starting_ref": "main"},
        budget={
            "network_policy": {
                "mode": "allowlist",
                "allowed_domains": ["jules.googleapis.com"],
            }
        },
    )


@pytest.mark.unit
def test_mutating_timeout_is_unknown_and_never_blindly_retried() -> None:
    calls = 0

    def http(**kwargs):
        nonlocal calls
        calls += 1
        raise TimeoutError("recorded timeout")

    driver = JulesApiDriver(http=http)
    with pytest.raises(DispatchError) as exc:
        driver.dispatch(_request())
    assert exc.value.code == "PROVIDER_DISPATCH_OUTCOME_UNKNOWN"
    assert calls == 1
    assert driver.mutating_posts == 1


@pytest.mark.unit
def test_list_sessions_is_bounded_and_prompt_free() -> None:
    def http(*, method, url, json=None, headers=None):
        assert method == "GET"
        assert url.endswith("/v1alpha/sessions?pageSize=2")
        return {
            "status": 200,
            "json": {
                "sessions": [
                    {
                        "name": "sessions/one",
                        "id": "one",
                        "state": "COMPLETED",
                        "url": "https://jules.google.com/session/one",
                        "prompt": "must not persist",
                        "title": "provider-authored title",
                        "outputs": [
                            {
                                "pullRequest": {
                                    "url": "https://github.com/jannekbuengener/Claire_de_Binare/pull/9999",
                                    "title": "Safe PR title",
                                    "description": "must not persist",
                                }
                            }
                        ],
                    },
                    {
                        "name": "sessions/two",
                        "id": "two",
                        "state": "IN_PROGRESS",
                    },
                ],
                "nextPageToken": "opaque-provider-token",
            },
        }

    driver = JulesApiDriver(http=http)
    result = driver.list_sessions(page_size=2)
    rendered = json.dumps(result)
    assert result["count"] == 2
    assert result["next_page_token_present"] is True
    assert result["sessions"][0]["pull_requests"][0]["title"] == "Safe PR title"
    assert "must not persist" not in rendered
    assert "provider-authored title" not in rendered
    assert "opaque-provider-token" not in rendered

    for invalid in (0, 101, True):
        with pytest.raises(DispatchError) as exc:
            driver.list_sessions(page_size=invalid)
        assert exc.value.code == "PROVIDER_LIST_PAGE_SIZE_INVALID"
