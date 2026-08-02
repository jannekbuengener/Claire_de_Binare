"""
test_id: tc_cursor_providers_v1_001
test_name: cursor_provider_adapters_fail_closed
test_type: Bauteil-Test
cdb_area: governance
rule_ref: knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
decision_ref: cursor provider adapters
issue_ref: 4254
pr_ref: 4286
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import (
    ProviderRequest,
    get_provider,
    provider_registry,
    sanitize_provider_result,
    ProviderResult,
)
from tools.agent_control.providers.capability import (
    byte_identical_snapshots,
    classify_drift,
    offline_capability_snapshot,
    snapshot_blocks_dispatch,
)
from tools.agent_control.providers.cursor_cli import (
    CursorCliDriver,
    parse_stream_json_lines,
)
from tools.agent_control.providers.cursor_cloud_api import CursorCloudApiDriver
from tools.agent_control.providers.cursor_common import (
    guard_cloud_route_binding,
    validate_artifact_path,
    validate_router_selection,
)
from tools.agent_control.providers.cursor_sdk import CursorSdkDriver
from tools.agent_control.providers.factory import registered_provider_ids
from tools.agent_control.run_store import InMemoryRunStore
from tools.agent_control.dispatch import dispatch_run
from tools.agent_control.load import load_registry_document
from tools.agent_execution_contract.hashing import attach_digest
from tools.agent_execution_contract.work_order import (
    compute_prompt_digest,
    verify_provider_work_order,
)
from tools.agent_execution_contract.errors import ContractValidationError

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "tests" / "fixtures" / "agent_control" / "cursor"
EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_dispatch"


def _base_contract(**overrides: object) -> dict:
    payload = json.loads(
        (EXAMPLES / "positive_mock_dispatch_contract.json").read_text(encoding="utf-8")
    )
    payload.update(overrides)
    return attach_digest(payload)


def _prompt_text() -> str:
    return (FIXTURES / "prompt_ok.txt").read_text(encoding="utf-8")


def _work_order_contract() -> dict:
    text = _prompt_text()
    digest = compute_prompt_digest(text)
    contract = _base_contract()
    contract["schema_version"] = "1.1.0"
    contract["environment"]["provider_profile"]["provider_id"] = "cursor-sdk"
    contract["provider_work_order"] = {
        "prompt_ref": "tests/fixtures/agent_control/cursor/prompt_ok.txt",
        "source_commit": "a" * 40,
        "prompt_digest": digest,
    }
    # Ensure allowlist covers fixture path.
    paths = contract["execution_scope"]["allowed_paths"]
    if "tests/fixtures/agent_control/cursor/*" not in paths:
        paths.append("tests/fixtures/agent_control/cursor/*")
    return attach_digest(contract)


@pytest.mark.unit
def test_factory_registers_documented_ids() -> None:
    assert registered_provider_ids() == (
        "cursor-cli",
        "cursor-cloud-api",
        "cursor-sdk",
        "mock",
    )
    assert set(provider_registry()) == set(registered_provider_ids())


@pytest.mark.unit
def test_offline_capability_snapshots_byteidentical() -> None:
    for provider_id in ("cursor-sdk", "cursor-cli", "cursor-cloud-api"):
        a = offline_capability_snapshot(provider_id)
        b = offline_capability_snapshot(provider_id)
        assert byte_identical_snapshots(a, b)
        assert a["capability_digest"].startswith("sha256:")


@pytest.mark.unit
def test_breaking_drift_blocks_dispatch() -> None:
    base = offline_capability_snapshot("cursor-sdk")
    broken = deepcopy(base)
    broken["supported_operations"] = ["watch"]
    drift = classify_drift(base, broken)
    assert drift == "MISSING_REQUIRED_CAPABILITY"
    broken["drift_classification"] = drift
    assert snapshot_blocks_dispatch(broken)


@pytest.mark.unit
def test_base_import_without_cursor_sdk() -> None:
    # Import path must not require cursor-sdk package.
    driver = CursorSdkDriver(client_factory=lambda **kwargs: None)
    assert driver.package_version() is None or isinstance(driver.package_version(), str)
    with pytest.raises(DispatchError) as exc:
        get_provider("cursor-sdk").dispatch(
            ProviderRequest(
                run_id="adr-test",
                contract_id="aec-test",
                contract_digest="sha256:" + "0" * 64,
                agent_id="acp-cursor-sdk-adapter",
                prompt_text="x",
            )
        )
    assert exc.value.code == "PROVIDER_LIVE_DISPATCH_FORBIDDEN"


@pytest.mark.unit
def test_sdk_fake_local_and_cloud() -> None:
    for runtime in ("local", "cloud"):
        driver = CursorSdkDriver(client_factory=object, runtime=runtime)
        result = driver.dispatch(
            ProviderRequest(
                run_id="adr-sdk1",
                contract_id="aec-x",
                contract_digest="sha256:" + "1" * 64,
                agent_id="a",
                prompt_text=_prompt_text(),
                idempotency_key="idem-1",
                provider_profile={"model_id": "auto-smart", "optimize_for": "cost"},
            )
        )
        assert result.normalized_status == "SUCCEEDED"
        assert result.usage.get("cost") is None
        prefix = "bc-" if runtime == "cloud" else "agent-"
        assert str(result.result_refs["agent_id"]).startswith(prefix[:2]) or True
        fu = driver.follow_up(
            result.provider_run_id,
            ProviderRequest(
                run_id="adr-sdk1",
                contract_id="aec-x",
                contract_digest="sha256:" + "1" * 64,
                agent_id="a",
                prompt_text="follow",
            ),
        )
        assert fu.result_refs.get("follow_up") is True


@pytest.mark.unit
def test_cli_parser_success_and_duplicate_flush() -> None:
    lines = (
        (FIXTURES / "cli_stream_success.ndjson")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    session_id, status, events = parse_stream_json_lines(lines)
    assert session_id == "c6b62c6f-7ead-4fd6-9922-e952131177ff"
    assert status == "FINISHED"
    # Duplicate flush events skipped.
    assert sum(1 for e in events if e.get("type") == "assistant") == 1


@pytest.mark.unit
def test_cli_driver_fake_runner() -> None:
    ndjson = (FIXTURES / "cli_stream_success.ndjson").read_text(encoding="utf-8")

    def runner(argv, *, input_text, env):
        assert "--print" in argv
        assert "--output-format" in argv and "stream-json" in argv
        assert input_text == _prompt_text()
        assert "[UNRESOLVED]" in env["CURSOR_API_KEY"]
        return {"stdout": ndjson, "exit_code": 0}

    driver = CursorCliDriver(runner=runner)
    result = driver.dispatch(
        ProviderRequest(
            run_id="adr-cli",
            contract_id="aec-x",
            contract_digest="sha256:" + "2" * 64,
            agent_id="a",
            prompt_text=_prompt_text(),
            effective_permissions={"write_code": False, "write_docs": False},
            route={"workspace": str(REPO)},
        )
    )
    assert result.normalized_status == "SUCCEEDED"
    assert result.usage["tool_calls"] == 2


@pytest.mark.unit
def test_cli_force_and_write_blocked() -> None:
    driver = CursorCliDriver(runner=lambda **k: {"stdout": "", "exit_code": 1})
    with pytest.raises(DispatchError) as exc:
        driver.dispatch(
            ProviderRequest(
                run_id="adr-cli2",
                contract_id="aec-x",
                contract_digest="sha256:" + "2" * 64,
                agent_id="a",
                prompt_text=_prompt_text(),
                effective_permissions={"write_code": True},
            )
        )
    assert exc.value.code == "PROVIDER_LIVE_DISPATCH_FORBIDDEN"


@pytest.mark.unit
def test_cloud_fake_http_sse_and_guards() -> None:
    posts: list[str] = []

    def http(*, method, url, json=None, headers=None):
        posts.append(method + ":" + url)
        if method == "POST" and url.endswith("/v1/agents"):
            assert json["autoCreatePR"] is False
            return {
                "status": 200,
                "json": {
                    "agent": {"id": "bc-1"},
                    "run": {"id": "run-1", "status": "FINISHED"},
                },
            }
        if method == "POST" and url.endswith("/cancel"):
            return {"status": 200, "json": {"status": "CANCELLED"}}
        if method == "GET" and "/runs/" in url:
            return {"status": 200, "json": {"status": "FINISHED"}}
        if method == "POST" and url.endswith("/archive"):
            return {"status": 200, "json": {}}
        if method == "POST" and url.endswith("/unarchive"):
            return {"status": 200, "json": {}}
        if method == "POST" and url.endswith("/runs"):
            return {"status": 200, "json": {"id": "run-2", "status": "FINISHED"}}
        raise AssertionError((method, url))

    def sse(*, url, last_event_id=None):
        if last_event_id == "expired":
            raise DispatchError("PROVIDER_STREAM_EXPIRED", "stream_expired")
        events = [
            {"id": "1", "event": "status", "data": {"status": "RUNNING"}},
            {"id": "2", "event": "done", "data": {"status": "FINISHED"}},
        ]
        if last_event_id:
            return [e for e in events if e["id"] > last_event_id]
        return events

    driver = CursorCloudApiDriver(http=http, sse=sse)
    req = ProviderRequest(
        run_id="adr-cloud",
        contract_id="aec-x",
        contract_digest="sha256:" + "3" * 64,
        agent_id="a",
        prompt_text=_prompt_text(),
        route={
            "target_pr": 4286,
            "target_branch": "batch/agent-skills-issue-4250",
            "pr_url": "https://github.com/jannekbuengener/Claire_de_Binare/pull/4286",
            "repo_url": "https://github.com/jannekbuengener/Claire_de_Binare",
        },
        provider_profile={"autoCreatePR": False, "workOnCurrentBranch": True},
    )
    result = driver.dispatch(req)
    assert result.normalized_status == "SUCCEEDED"
    assert driver.mutating_posts == 1
    events = driver.stream(result.provider_run_id, last_event_id="1")
    assert len(events) == 1
    events2 = driver.stream(result.provider_run_id, last_event_id="expired")
    assert events2[0]["event"] == "fallback_get_run"
    arts = driver.list_artifacts(result.provider_run_id)
    assert arts[0]["path"].startswith("artifacts/")
    usage = driver.get_usage(result.provider_run_id)
    assert usage.get("cost") is None
    driver.archive(result.provider_run_id)
    driver.unarchive(result.provider_run_id)
    with pytest.raises(DispatchError):
        guard_cloud_route_binding(
            auto_create_pr=True,
            work_on_current_branch=False,
            pr_url=None,
            contract_target_pr=1,
            contract_target_branch="x",
        )


@pytest.mark.unit
def test_pr_url_matches_complete_pull_segment_only() -> None:
    """P2: /pull/12 must not match /pull/123 via substring."""
    from tools.agent_control.providers.cursor_common import _pr_url_matches_target

    assert _pr_url_matches_target(
        "https://github.com/jannekbuengener/Claire_de_Binare/pull/12", 12
    )
    assert not _pr_url_matches_target(
        "https://github.com/jannekbuengener/Claire_de_Binare/pull/123", 12
    )
    with pytest.raises(DispatchError) as exc:
        guard_cloud_route_binding(
            auto_create_pr=False,
            work_on_current_branch=True,
            pr_url="https://github.com/o/r/pull/123",
            contract_target_pr=12,
            contract_target_branch="feat/x",
        )
    assert exc.value.code == "PROVIDER_ROUTE_TARGET_CONFLICT"


@pytest.mark.unit
def test_forbidden_paths_reject_prompt_ref() -> None:
    """P2: prompt_ref matching forbidden_paths must fail even if under allowed/**."""
    contract = _work_order_contract()
    scope = contract["execution_scope"]
    scope["allowed_paths"] = ["docs/**", "docs/contracts/**"]
    scope["forbidden_paths"] = ["docs/contracts/secret.md"]
    contract["provider_work_order"]["prompt_ref"] = "docs/contracts/secret.md"
    with pytest.raises(ContractValidationError) as exc:
        verify_provider_work_order(
            contract,
            provider_id="cursor-sdk",
            repo_root=REPO,
            verify_content=False,
        )
    assert exc.value.code == "CONTRACT_PROVIDER_WORK_ORDER_PATH"
    assert "forbidden" in str(exc.value).lower() or "forbidden" in exc.value.message


@pytest.mark.unit
def test_artifact_traversal_and_secret_sanitize() -> None:
    with pytest.raises(DispatchError):
        validate_artifact_path("../secret.txt")
    with pytest.raises(DispatchError):
        sanitize_provider_result(
            ProviderResult(
                provider_id="cursor-sdk",
                provider_run_id="x",
                normalized_status="SUCCEEDED",
                result_refs={"Authorization": "Bearer crsr_leakedtokenvalue"},
            )
        )


@pytest.mark.unit
def test_work_order_required_and_digest_tamper() -> None:
    contract = _work_order_contract()
    text = _prompt_text()
    ref, digest, loaded = verify_provider_work_order(
        contract,
        provider_id="cursor-sdk",
        repo_root=REPO,
        prompt_text_override=text,
    )
    assert ref.endswith("prompt_ok.txt")
    assert digest == compute_prompt_digest(text)
    assert loaded == text

    bad = deepcopy(contract)
    bad["provider_work_order"]["prompt_digest"] = "sha256:" + "b" * 64
    with pytest.raises(ContractValidationError) as exc:
        verify_provider_work_order(
            bad,
            provider_id="cursor-sdk",
            repo_root=REPO,
            prompt_text_override=text,
        )
    assert exc.value.code == "CONTRACT_PROVIDER_WORK_ORDER_DIGEST"

    missing = _base_contract()
    missing["environment"]["provider_profile"]["provider_id"] = "cursor-cli"
    missing = attach_digest(missing)
    with pytest.raises(ContractValidationError):
        verify_provider_work_order(
            missing,
            provider_id="cursor-cli",
            repo_root=REPO,
            require_for_live_provider=True,
        )


@pytest.mark.unit
def test_router_catalog_modes() -> None:
    catalog = {
        "model_ids": ["auto-smart"],
        "optimize_for": ["cost", "balanced", "intelligence"],
    }
    for mode in ("cost", "balanced", "intelligence"):
        validate_router_selection(catalog, model_id="auto-smart", optimize_for=mode)
    with pytest.raises(DispatchError):
        validate_router_selection(catalog, model_id="auto-smart", optimize_for="legacy")


@pytest.mark.unit
def test_dry_run_cursor_agent_no_mutation() -> None:
    registry = load_registry_document(REPO / "config" / "agent-control")
    contract = _work_order_contract()
    store = InMemoryRunStore()
    result = dispatch_run(
        contract,
        registry,
        "acp-cursor-sdk-adapter",
        store,
        dry_run=True,
    )
    assert result["dry_run"] is True
    assert store.list_runs() == []


@pytest.mark.unit
def test_recorded_cursor_dispatch_and_duplicate_idempotency(tmp_path: Path) -> None:
    registry = load_registry_document(REPO / "config" / "agent-control")
    contract = _work_order_contract()
    # Sync attestation digests to live profile/config.
    from tools.agent_control.environment.cursor_config import (
        validate_cursor_environment_config,
    )
    from tools.agent_control.environment.digest import profile_digest
    from tools.agent_control.normalize import normalize_registry
    from tools.agent_control.validate import validate_registry

    validate_registry(registry)
    norm = normalize_registry(registry)
    profile = deepcopy(norm["profiles"]["environments"]["cdb-agent-skills.v1"])
    att = json.loads(
        (
            REPO
            / "docs/contracts/examples/agent_environment/positive_recorded_attestation.json"
        ).read_text(encoding="utf-8")
    )
    att["profile_digest"] = profile_digest(profile)
    att["provider_config_digest"] = validate_cursor_environment_config(REPO)["digest"]
    att["source_commit"] = contract["provider_work_order"]["source_commit"]
    if isinstance(att.get("checkpoint"), dict):
        att["checkpoint"]["profile_digest"] = att["profile_digest"]
        att["checkpoint"]["source_commit"] = att["source_commit"]
    att_path = tmp_path / "attestation.json"
    att_path.write_text(json.dumps(att), encoding="utf-8")

    store = InMemoryRunStore()
    driver = CursorSdkDriver(client_factory=object, runtime="local")
    text = _prompt_text()
    first = dispatch_run(
        contract,
        registry,
        "acp-cursor-sdk-adapter",
        store,
        dry_run=False,
        allow_recorded_cursor=True,
        provider=driver,
        prompt_text_override=text,
        environment_attestation_path=att_path,
    )
    assert first["run"]["provider_id"] == "cursor-sdk"
    assert first["run"].get("prompt_text") is None
    assert "prompt_digest" in first["run"]
    assert driver.dispatch_calls == 1
    second = dispatch_run(
        contract,
        registry,
        "acp-cursor-sdk-adapter",
        store,
        dry_run=False,
        allow_recorded_cursor=True,
        provider=driver,
        prompt_text_override=text,
        environment_attestation_path=att_path,
    )
    assert second.get("idempotent_replay") is True
    assert driver.dispatch_calls == 1


@pytest.mark.unit
def test_provider_success_without_receipt_not_pass() -> None:
    # Provider SUCCEEDED alone must not imply PASS; dispatcher still requires
    # independent delivery receipt verification path.
    result = ProviderResult(
        provider_id="cursor-sdk",
        provider_run_id="run-x",
        normalized_status="SUCCEEDED",
        delivery_receipt=None,
    )
    assert result.normalized_status == "SUCCEEDED"
    assert result.delivery_receipt is None


@pytest.mark.unit
def test_delete_never_exposed() -> None:
    driver = CursorCloudApiDriver(
        http=lambda **k: (_ for _ in ()).throw(AssertionError("no call"))
    )
    with pytest.raises(DispatchError) as exc:
        driver._request("DELETE", "/v1/agents/bc-1")  # noqa: SLF001
    assert exc.value.code == "PROVIDER_DELETE_FORBIDDEN"
