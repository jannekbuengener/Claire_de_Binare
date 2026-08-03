"""
test_id: tc_cursor_live_preflight_v1_001
test_name: dashboardless_cursor_live_preflight
test_type: Bauteil-Test
cdb_area: governance
issue_ref: 4258
pr_ref: 4302
security_relevant: true
live_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.agent_control.cursor_preflight import (
    evaluate_named_environment_selection,
    extract_environment_identity,
    run_cursor_live_preflight,
    validate_preflight_report,
)
from tools.agent_control.errors import DispatchError
from tools.agent_control.paths import REPO_ROOT
from tools.agent_control.provider import ProviderRequest
from tools.agent_control.providers.cursor_cloud_api import CursorCloudApiDriver

FAKE_KEY = "crsr_test_preflight_secret_value_DO_NOT_LEAK"
REPO = "jannekbuengener/Claire_de_Binare"


def _http_router(routes: dict[str, tuple[int, dict]]):
    calls = {"GET": 0, "POST": 0}

    def http_get(path: str):
        calls["GET"] += 1
        if path in routes:
            return routes[path]
        if path.startswith("/v1/agents/") and "/runs/" in path:
            return routes.get("run", (200, {"id": "run-x", "status": "ERROR"}))
        if path.startswith("/v1/agents/"):
            return routes.get(
                "agent",
                (
                    200,
                    {
                        "id": "bc-1",
                        "status": "ACTIVE",
                        "env": {"type": "cloud"},
                        "autoCreatePR": True,
                        "repos": [{"url": f"https://github.com/{REPO}"}],
                    },
                ),
            )
        return 404, {"error": "not_found"}

    return http_get, calls


def _gh_ok(argv: list[str]):
    path = argv[0] if argv else ""
    if path.startswith("repos/") and path.endswith("/installation"):
        return 1, {"message": "A JSON web token could not be decoded", "status": "401"}
    if path.startswith("apps/cursor"):
        return 0, {
            "id": 1210556,
            "slug": "cursor",
            "permissions": {"contents": "write", "pull_requests": "write"},
        }
    if path.startswith("repos/") and "/branches/main/protection" in path:
        return 0, {"block_creations": {"enabled": False}}
    if path.startswith("repos/"):
        return 0, {"full_name": REPO, "default_branch": "main"}
    return 1, {"message": "unexpected"}


@pytest.mark.unit
def test_duplicate_environment_names_without_id_blocks() -> None:
    status, gaps, limits = evaluate_named_environment_selection(
        requested_name=REPO,
        resolved={"type": "cloud", "name": REPO, "environment_public_id": None},
        list_environments_http=404,
        dashboard_duplicate_names=True,
    )
    assert status == "BLOCKED"
    assert any(g["id"] == "PUBLIC_API_GAP_ENVIRONMENT_LIST" for g in gaps)
    assert "dashboard_duplicate_environment_names_observed" in limits


@pytest.mark.unit
def test_requested_resolved_environment_match_and_mismatch() -> None:
    ok, _, _ = evaluate_named_environment_selection(
        requested_name="Release workspace",
        resolved={
            "type": "cloud",
            "name": "Release workspace",
            "environment_public_id": None,
        },
        list_environments_http=404,
        dashboard_duplicate_names=False,
    )
    assert ok == "PASS"
    bad, _, limits = evaluate_named_environment_selection(
        requested_name="A",
        resolved={"type": "cloud", "name": "B", "environment_public_id": None},
        list_environments_http=404,
        dashboard_duplicate_names=False,
    )
    assert bad == "BLOCKED"
    assert "requested_resolved_environment_mismatch" in limits


@pytest.mark.unit
def test_missing_environment_metadata_unknown() -> None:
    status, _, _ = evaluate_named_environment_selection(
        requested_name=REPO,
        resolved={"type": "cloud", "name": None, "environment_public_id": None},
        list_environments_http=404,
        dashboard_duplicate_names=False,
    )
    assert status == "UNKNOWN"


@pytest.mark.unit
def test_github_contents_readonly_blocks(tmp_path: Path) -> None:
    http_get, calls = _http_router(
        {
            "/v1/me": (200, {"apiKeyName": "t", "userId": 1}),
            "/v1/models": (200, {"items": [{"id": "default"}]}),
            "/v1/repositories": (
                200,
                {"items": [{"url": f"https://github.com/{REPO}"}]},
            ),
            "/v1/environments": (404, {"error": "missing"}),
        }
    )

    def gh(argv: list[str]):
        path = argv[0]
        if path.endswith("/installation"):
            return 0, {
                "id": 99,
                "suspended_at": None,
                "repository_selection": "selected",
                "permissions": {"contents": "read", "pull_requests": "write"},
            }
        if path.startswith("apps/"):
            return 0, {
                "permissions": {"contents": "write", "pull_requests": "write"},
                "slug": "cursor",
            }
        if "protection" in path:
            return 0, {"block_creations": {"enabled": False}}
        return 0, {"default_branch": "main", "full_name": REPO}

    report = run_cursor_live_preflight(
        repository=REPO,
        binding_mode="repos_plus_repo_config",
        repo_root=REPO_ROOT,
        secrets_dir=tmp_path,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
        http_get=http_get,
        gh_api=gh,
        dashboard_observations=None,
        existing_agent_id=None,
        existing_run_id=None,
    )
    assert report["github_app_status"] == "BLOCKED"
    assert report["ready_for_live_run"] is False
    assert calls["POST"] == 0
    assert report["cursor_http_posts"] == 0
    assert report["github_writes"] == 0
    assert FAKE_KEY not in json.dumps(report)


@pytest.mark.unit
def test_suspended_installation_blocks(tmp_path: Path) -> None:
    http_get, _ = _http_router(
        {
            "/v1/me": (200, {"apiKeyName": "t", "userId": 1}),
            "/v1/models": (200, {"items": [{"id": "default"}]}),
            "/v1/repositories": (
                200,
                {"items": [{"url": f"https://github.com/{REPO}"}]},
            ),
            "/v1/environments": (404, {}),
        }
    )

    def gh(argv: list[str]):
        path = argv[0]
        if path.endswith("/installation"):
            return 0, {
                "id": 99,
                "suspended_at": "2026-01-01T00:00:00Z",
                "permissions": {"contents": "write", "pull_requests": "write"},
            }
        if path.startswith("apps/"):
            return 0, {
                "permissions": {"contents": "write", "pull_requests": "write"},
                "slug": "cursor",
            }
        if "protection" in path:
            return 0, {"block_creations": {"enabled": False}}
        return 0, {"default_branch": "main"}

    report = run_cursor_live_preflight(
        repository=REPO,
        repo_root=REPO_ROOT,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
        http_get=http_get,
        gh_api=gh,
        existing_agent_id=None,
        existing_run_id=None,
    )
    assert report["github_app_status"] == "BLOCKED"
    assert report["ready_for_live_run"] is False


@pytest.mark.unit
def test_preflight_zero_creates_and_schema(tmp_path: Path) -> None:
    http_get, calls = _http_router(
        {
            "/v1/me": (200, {"apiKeyName": "api.CDB", "userId": 1}),
            "/v1/models": (200, {"items": [{"id": "default"}]}),
            "/v1/repositories": (
                200,
                {"items": [{"url": f"https://github.com/{REPO}"}]},
            ),
            "/v1/environments": (404, {"error": "not_found"}),
        }
    )
    report = run_cursor_live_preflight(
        repository=REPO,
        environment_name=REPO,
        binding_mode="repos_plus_repo_config",
        repo_root=REPO_ROOT,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
        http_get=http_get,
        gh_api=_gh_ok,
        dashboard_observations={
            "ambiguity": "two active environments with the same visible name",
            "environments": [
                {"repository": REPO, "status": "Active"},
                {"repository": REPO, "status": "Active"},
            ],
            "create_prs": "Always",
        },
        existing_agent_id=None,
        existing_run_id=None,
    )
    validate_preflight_report(report, repo_root=REPO_ROOT)
    assert report["cursor_http_posts"] == 0
    assert report["github_writes"] == 0
    assert calls["GET"] >= 3
    assert report["repo_config_status"] == "PASS"
    assert report["ready_for_live_run"] is False  # installation UNKNOWN
    assert any(
        g["id"] == "PUBLIC_API_GAP_GITHUB_INSTALLATION_READ"
        for g in report["public_api_gaps"]
    )
    assert FAKE_KEY not in json.dumps(report)


@pytest.mark.unit
def test_named_mode_duplicate_blocks_ready(tmp_path: Path) -> None:
    http_get, _ = _http_router(
        {
            "/v1/me": (200, {"apiKeyName": "t", "userId": 1}),
            "/v1/models": (200, {"items": [{"id": "default"}]}),
            "/v1/repositories": (
                200,
                {"items": [{"url": f"https://github.com/{REPO}"}]},
            ),
            "/v1/environments": (404, {}),
            "agent": (
                200,
                {
                    "id": "bc-1",
                    "status": "ACTIVE",
                    "env": {"type": "cloud", "name": REPO},
                },
            ),
        }
    )

    def gh_pass_install(argv: list[str]):
        path = argv[0]
        if path.endswith("/installation"):
            return 0, {
                "id": 42,
                "suspended_at": None,
                "repository_selection": "all",
                "permissions": {"contents": "write", "pull_requests": "write"},
            }
        if path.startswith("apps/"):
            return 0, {
                "slug": "cursor",
                "permissions": {"contents": "write", "pull_requests": "write"},
            }
        if "protection" in path:
            return 0, {"block_creations": {"enabled": False}}
        return 0, {"default_branch": "main"}

    report = run_cursor_live_preflight(
        repository=REPO,
        environment_name=REPO,
        binding_mode="named_cloud_env",
        repo_root=REPO_ROOT,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
        http_get=http_get,
        gh_api=gh_pass_install,
        dashboard_observations={
            "ambiguity": "two active environments with the same visible name"
        },
        existing_agent_id="bc-1",
        existing_run_id=None,
    )
    assert report["environment_selection_status"] == "BLOCKED"
    assert report["ready_for_live_run"] is False


@pytest.mark.unit
def test_adapter_environment_mismatch_blocks() -> None:
    def http(*, method, url, json=None, headers=None):
        del headers
        if method == "POST" and str(url).endswith("/v1/agents"):
            assert "env" in json
            assert "repos" not in json
            return {
                "status": 200,
                "json": {
                    "agent": {
                        "id": json["agentId"],
                        "env": {"type": "cloud", "name": "Other Env"},
                    },
                    "run": {"id": "run-1", "status": "CREATING"},
                },
            }
        raise AssertionError((method, url))

    driver = CursorCloudApiDriver(http=http, human_go_live=True)
    with pytest.raises(DispatchError) as exc:
        driver.dispatch(
            ProviderRequest(
                run_id="adr-env",
                contract_id="aec-x",
                contract_digest="sha256:" + "1" * 64,
                agent_id="a",
                prompt_text="x",
                route={"repo_url": f"https://github.com/{REPO}"},
                provider_profile={
                    "autoCreatePR": True,
                    "human_go_live_cursor": True,
                    "env": {"type": "cloud", "name": REPO},
                },
            )
        )
    assert exc.value.code == "PROVIDER_ENVIRONMENT_MISMATCH"


@pytest.mark.unit
def test_adapter_persists_requested_and_resolved_env() -> None:
    def http(*, method, url, json=None, headers=None):
        del headers
        if method == "POST" and str(url).endswith("/v1/agents"):
            assert json["repos"][0]["startingRef"] == "main"
            return {
                "status": 200,
                "json": {
                    "agent": {
                        "id": json["agentId"],
                        "env": {"type": "cloud"},
                        "repos": json["repos"],
                    },
                    "run": {"id": "run-1", "status": "FINISHED"},
                },
            }
        if method == "GET":
            return {"status": 200, "json": {"status": "FINISHED"}}
        raise AssertionError((method, url))

    driver = CursorCloudApiDriver(http=http, human_go_live=True)
    result = driver.dispatch(
        ProviderRequest(
            run_id="adr-repos",
            contract_id="aec-x",
            contract_digest="sha256:" + "2" * 64,
            agent_id="a",
            prompt_text="x",
            route={"repo_url": f"https://github.com/{REPO}"},
            provider_profile={"autoCreatePR": True, "human_go_live_cursor": True},
        )
    )
    refs = result.result_refs or {}
    assert refs["environment_requested"]["binding_mode"] == "repos_plus_repo_config"
    assert extract_environment_identity(refs["environment_resolved"])["type"] == "cloud"
    assert driver.mutating_posts == 1


@pytest.mark.unit
def test_public_api_gap_reported_honestly(tmp_path: Path) -> None:
    http_get, _ = _http_router(
        {
            "/v1/me": (200, {"apiKeyName": "t", "userId": 1}),
            "/v1/models": (200, {"items": [{"id": "default"}]}),
            "/v1/repositories": (
                200,
                {"items": [{"url": f"https://github.com/{REPO}"}]},
            ),
            "/v1/environments": (404, {}),
        }
    )
    report = run_cursor_live_preflight(
        repository=REPO,
        repo_root=REPO_ROOT,
        credential_env={"CURSOR_API_KEY": FAKE_KEY},
        http_get=http_get,
        gh_api=_gh_ok,
        existing_agent_id=None,
        existing_run_id=None,
    )
    ids = {g["id"] for g in report["public_api_gaps"]}
    assert "PUBLIC_API_GAP_ENVIRONMENT_LIST" in ids
    assert "PUBLIC_API_GAP_NETWORK_POLICY" in ids
    assert "PUBLIC_API_GAP_ROUTING_RULES" in ids
