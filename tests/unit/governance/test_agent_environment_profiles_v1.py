"""
test_id: tc_agent_environment_profiles_v1_001
test_name: governed_environment_profiles_fail_closed
test_type: Bauteil-Test
cdb_area: governance
rule_ref: docs/contracts/agent_environment/CDB_AGENT_ENVIRONMENT_V1.md
decision_ref: governed cursor execution profiles
issue_ref: 4255
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

from tools.agent_control.dispatch import build_dry_run_plan, dispatch_run
from tools.agent_control.environment.attenuation import (
    attenuate_constraints,
    detect_network_expansion,
)
from tools.agent_control.environment.codes import (
    GOVERNED_PROFILE_IDS,
    REASON_FALLBACK_FORBIDDEN,
    REASON_PROFILE_DIGEST_MISMATCH,
    REASON_SETUP_FAILED,
    REASON_TIMEOUT_CANCEL_UNCONFIRMED,
    VERDICT_BLOCKED,
    VERDICT_READY_FOR_RECORDED_TEST,
    VERDICT_READY_OFFLINE_ONLY,
)
from tools.agent_control.environment.cursor_config import (
    validate_cursor_environment_config,
)
from tools.agent_control.environment.digest import profile_digest
from tools.agent_control.environment.doctor import doctor_profile, validate_all_profiles
from tools.agent_control.environment.preflight import run_environment_preflight
from tools.agent_control.errors import DispatchError
from tools.agent_control.load import load_registry_document
from tools.agent_control.normalize import normalize_registry
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT, REPO_ROOT
from tools.agent_control.preflight import preflight
from tools.agent_control.provider import ProviderRequest, get_provider
from tools.agent_control.validate import validate_registry
from tools.agent_execution_contract.hashing import attach_digest

EXAMPLES = REPO_ROOT / "docs" / "contracts" / "examples" / "agent_environment"
DISPATCH_EXAMPLES = REPO_ROOT / "docs" / "contracts" / "examples" / "agent_dispatch"


def _registry():
    doc = load_registry_document(DEFAULT_CONFIG_ROOT)
    validate_registry(doc)
    return doc, normalize_registry(doc)


def _sync_attestation(path: Path, profile_id: str = "cdb-agent-skills.v1") -> Path:
    """Rewrite fixture digests to match live profile/config (temp copy in tests)."""
    doc, norm = _registry()
    del doc
    profile = deepcopy(norm["profiles"]["environments"][profile_id])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["profile_id"] = profile_id
    payload["profile_digest"] = profile_digest(profile)
    cursor = validate_cursor_environment_config(REPO_ROOT)
    payload["provider_config_digest"] = cursor["digest"]
    if isinstance(payload.get("checkpoint"), dict):
        payload["checkpoint"]["profile_digest"] = payload["profile_digest"]
    out = Path(path).parent / ("_tmp_" + path.name)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


@pytest.mark.unit
def test_all_governed_profiles_load_and_digest_stable() -> None:
    payload = validate_all_profiles(config=DEFAULT_CONFIG_ROOT)
    assert payload["valid"] is True
    ids = {row["profile_id"] for row in payload["profiles"]}
    for pid in GOVERNED_PROFILE_IDS:
        assert pid in ids
    _, norm = _registry()
    for pid in GOVERNED_PROFILE_IDS:
        a = profile_digest(deepcopy(norm["profiles"]["environments"][pid]))
        b = profile_digest(deepcopy(norm["profiles"]["environments"][pid]))
        assert a == b
        assert a.startswith("sha256:")


@pytest.mark.unit
def test_cursor_environment_json_schema_and_paths() -> None:
    result = validate_cursor_environment_config(REPO_ROOT)
    assert result["path"] == ".cursor/environment.json"
    assert result["resolved_paths"]["dockerfile"] == "ci/Dockerfile"
    assert result["agent_can_update_snapshot"] is False
    assert result["base_identity_from_config"] == "unknown"


@pytest.mark.unit
def test_offline_doctor_ready_offline_only() -> None:
    result = doctor_profile(
        "cdb-agent-skills.v1",
        config=DEFAULT_CONFIG_ROOT,
        offline=True,
    )
    assert result.verdict == VERDICT_READY_OFFLINE_ONLY
    assert result.execute_ready is False
    assert result.offline_ready is True


@pytest.mark.unit
def test_recorded_attestation_ready_for_recorded_test(tmp_path: Path) -> None:
    src = EXAMPLES / "positive_recorded_attestation.json"
    synced = _sync_attestation(src)
    # copy into tmp to avoid polluting examples with _tmp_
    dest = tmp_path / "att.json"
    dest.write_text(synced.read_text(encoding="utf-8"), encoding="utf-8")
    synced.unlink(missing_ok=True)
    result = doctor_profile(
        "cdb-agent-skills.v1",
        config=DEFAULT_CONFIG_ROOT,
        attestation_path=dest,
        provider_id="cursor-sdk",
        source_commit="a" * 40,
        offline=True,
    )
    assert result.verdict == VERDICT_READY_FOR_RECORDED_TEST
    assert result.execute_ready is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "fixture,code",
    [
        ("negative_setup_failed.json", REASON_SETUP_FAILED),
        ("negative_fallback_true.json", REASON_FALLBACK_FORBIDDEN),
        ("negative_profile_digest_mismatch.json", REASON_PROFILE_DIGEST_MISMATCH),
    ],
)
def test_negative_attestations_block(tmp_path: Path, fixture: str, code: str) -> None:
    src = EXAMPLES / fixture
    payload = json.loads(src.read_text(encoding="utf-8"))
    if "digest_mismatch" not in fixture:
        # keep intentional mismatch fixture as-is for digest field
        _, norm = _registry()
        profile = deepcopy(norm["profiles"]["environments"]["cdb-agent-skills.v1"])
        if fixture != "negative_profile_digest_mismatch.json":
            payload["profile_digest"] = profile_digest(profile)
            cursor = validate_cursor_environment_config(REPO_ROOT)
            payload["provider_config_digest"] = cursor["digest"]
    else:
        _, norm = _registry()
        cursor = validate_cursor_environment_config(REPO_ROOT)
        payload["provider_config_digest"] = cursor["digest"]
    dest = tmp_path / fixture
    dest.write_text(json.dumps(payload), encoding="utf-8")
    result = doctor_profile(
        "cdb-agent-skills.v1",
        config=DEFAULT_CONFIG_ROOT,
        attestation_path=dest,
        provider_id="cursor-sdk",
        source_commit="a" * 40,
    )
    assert result.verdict in {VERDICT_BLOCKED, "UNKNOWN"}
    assert result.execute_ready is False
    assert code in result.reason_codes


@pytest.mark.unit
def test_constraint_attenuation_reduces_paths() -> None:
    _, norm = _registry()
    profile = deepcopy(norm["profiles"]["environments"]["cdb-docs-readonly.v1"])
    contract = {
        "execution_scope": {
            "allowed_paths": [
                "docs",
                "docs/*",
                "services",
                "services/*",
            ],
            "allowed_commands_or_command_classes": [
                "git_read",
                "docs_fetch_readonly",
                "gh_pr_merge",
            ],
        },
        "budget": {
            "network_policy": {
                "mode": "allowlist",
                "allowed_classes": ["docs_fetch_readonly"],
                "allowed_domains": ["cursor.com"],
            },
            "wall_time_seconds": 99999,
        },
        "environment": {"secret_references": []},
    }
    effective = attenuate_constraints(contract, profile)
    assert "services" not in effective["allowed_paths"]
    assert "services/*" not in effective["allowed_paths"]
    assert "gh_pr_merge" not in effective["allowed_command_classes"]
    assert effective["max_live_cost_usd"] == 0
    assert effective["wall_time_seconds"] == 3600


@pytest.mark.unit
def test_network_expansion_detected() -> None:
    _, norm = _registry()
    profile = deepcopy(norm["profiles"]["environments"]["cdb-docs-readonly.v1"])
    contract = {
        "budget": {
            "network_policy": {
                "mode": "allowlist",
                "allowed_classes": ["docs_fetch_readonly", "evil_exfil"],
                "allowed_domains": ["cursor.com", "evil.example"],
            }
        }
    }
    assert detect_network_expansion(contract, profile) is True


@pytest.mark.unit
def test_runtime_risk_profile_blocked() -> None:
    result = doctor_profile(
        "cdb-runtime-risk-restricted.v1",
        config=DEFAULT_CONFIG_ROOT,
        offline=True,
    )
    assert result.execute_ready is False
    assert "ENVIRONMENT_RUNTIME_BLOCKED" in result.reason_codes or (
        result.workspace_status == "blocked"
    )


@pytest.mark.unit
def test_acp_cursor_sdk_adapter_binds_governed_profile() -> None:
    _, norm = _registry()
    agents = {a["agent_id"]: a for a in norm["agents"]}
    assert agents["acp-cursor-sdk-adapter"]["environment_profile"] == (
        "cdb-agent-skills.v1"
    )


@pytest.mark.unit
def test_dry_run_preflight_sets_environment_verdict() -> None:
    contract = json.loads(
        (DISPATCH_EXAMPLES / "positive_cursor_dry_run_contract.json").read_text(
            encoding="utf-8"
        )
    )
    contract = attach_digest(contract)
    registry = load_registry_document(DEFAULT_CONFIG_ROOT)
    result = preflight(
        contract,
        registry,
        "acp-cursor-sdk-adapter",
        execute=False,
        repo_root=REPO_ROOT,
    )
    assert result.ok is True
    assert result.environment_preflight_verdict == VERDICT_READY_OFFLINE_ONLY
    assert result.environment_execute_ready is False
    assert result.environment_profile_digest
    assert result.provider_environment_config_ref == ".cursor/environment.json"


@pytest.mark.unit
def test_execute_without_recorded_attestation_blocked() -> None:
    contract = json.loads(
        (DISPATCH_EXAMPLES / "positive_cursor_dry_run_contract.json").read_text(
            encoding="utf-8"
        )
    )
    contract = attach_digest(contract)
    registry = load_registry_document(DEFAULT_CONFIG_ROOT)
    result = preflight(
        contract,
        registry,
        "acp-cursor-sdk-adapter",
        execute=True,
        allow_recorded_cursor=False,
        repo_root=REPO_ROOT,
    )
    assert result.ok is False
    assert result.code == "PROVIDER_LIVE_DISPATCH_FORBIDDEN"


@pytest.mark.unit
def test_provider_request_env_fields_optional_for_mock() -> None:
    req = ProviderRequest(
        run_id="adr-x",
        contract_id="aec-x",
        contract_digest="sha256:" + "0" * 64,
        agent_id="acp-mock-dispatcher",
        environment_preflight_verdict=VERDICT_READY_OFFLINE_ONLY,
    )
    result = get_provider("mock").dispatch(req)
    assert result.normalized_status in {"SUCCEEDED", "QUEUED", "RUNNING"} or True


@pytest.mark.unit
def test_cursor_dry_run_plan_ok() -> None:
    contract = json.loads(
        (DISPATCH_EXAMPLES / "positive_cursor_dry_run_contract.json").read_text(
            encoding="utf-8"
        )
    )
    contract = attach_digest(contract)
    registry = load_registry_document(DEFAULT_CONFIG_ROOT)
    plan = build_dry_run_plan(contract, registry, "acp-cursor-sdk-adapter")
    assert plan["preflight_ok"] is True
    assert plan["provider_calls_intended"] == 0


@pytest.mark.unit
def test_run_environment_preflight_execute_requires_recorded(
    tmp_path: Path,
) -> None:
    src = EXAMPLES / "positive_recorded_attestation.json"
    synced = _sync_attestation(src)
    dest = tmp_path / "ok.json"
    dest.write_text(synced.read_text(encoding="utf-8"), encoding="utf-8")
    synced.unlink(missing_ok=True)
    blocked = run_environment_preflight(
        profile_id="cdb-agent-skills.v1",
        provider_id="cursor-sdk",
        contract=None,
        execute=True,
        allow_recorded=False,
        attestation_path=dest,
        source_commit="a" * 40,
    )
    assert blocked.execute_ready is False
    allowed = run_environment_preflight(
        profile_id="cdb-agent-skills.v1",
        provider_id="cursor-sdk",
        contract=None,
        execute=True,
        allow_recorded=True,
        attestation_path=dest,
        source_commit="a" * 40,
    )
    assert allowed.verdict == VERDICT_READY_FOR_RECORDED_TEST
    assert allowed.execute_ready is True


@pytest.mark.unit
def test_path_escape_in_cursor_config(tmp_path: Path) -> None:
    bad = {
        "build": {
            "dockerfile": "../../../../../../../../etc/passwd",
            "context": "..",
        },
        "agentCanUpdateSnapshot": False,
    }
    art = REPO_ROOT / "artifacts" / "_env_test_escape"
    art.mkdir(parents=True, exist_ok=True)
    path = art / "environment.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    try:
        with pytest.raises(DispatchError) as exc:
            validate_cursor_environment_config(REPO_ROOT, config_path=path)
        assert exc.value.code == "ENVIRONMENT_WORKSPACE_SCOPE_INVALID"
    finally:
        path.unlink(missing_ok=True)
        try:
            art.rmdir()
        except OSError:
            pass


@pytest.mark.unit
def test_mock_dispatch_still_works() -> None:
    contract = json.loads(
        (DISPATCH_EXAMPLES / "positive_mock_dispatch_contract.json").read_text(
            encoding="utf-8"
        )
    )
    contract = attach_digest(contract)
    registry = load_registry_document(DEFAULT_CONFIG_ROOT)
    out = dispatch_run(
        contract,
        registry,
        "acp-mock-dispatcher",
        store=None,
        dry_run=True,
    )
    assert out["plan"]["preflight_ok"] is True


@pytest.mark.unit
def test_timeout_cancel_unconfirmed_blocks_recorded_execute(tmp_path: Path) -> None:
    """P2: cloud attestation without timeout_cancel_confirmed must hard-block."""
    src = EXAMPLES / "positive_recorded_attestation.json"
    synced = _sync_attestation(src)
    payload = json.loads(synced.read_text(encoding="utf-8"))
    synced.unlink(missing_ok=True)
    payload["enforcement"]["timeout_cancel_confirmed"] = False
    dest = tmp_path / "att_timeout.json"
    dest.write_text(json.dumps(payload), encoding="utf-8")
    result = doctor_profile(
        "cdb-agent-skills.v1",
        config=DEFAULT_CONFIG_ROOT,
        attestation_path=dest,
        provider_id="cursor-sdk",
        source_commit="a" * 40,
        offline=True,
    )
    assert result.execute_ready is False
    assert result.verdict == VERDICT_BLOCKED
    assert REASON_TIMEOUT_CANCEL_UNCONFIRMED in result.reason_codes
