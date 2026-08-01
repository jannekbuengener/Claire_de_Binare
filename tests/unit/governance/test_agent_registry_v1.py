"""
test_id: tc_agent_registry_v1_001
test_name: agent_registry_v1_fail_closed_reconciler
test_type: Bauteil-Test
cdb_area: governance
rule_ref: knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
decision_ref: cdb.agent_registry.v1
issue_ref: 4252
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

from tools.agent_control.backend import MockBackend
from tools.agent_control.cli import main as cli_main
from tools.agent_control.errors import RegistryError
from tools.agent_control.load import dump_json, load_registry_document
from tools.agent_control.normalize import (
    agent_desired_fingerprint,
    normalize_registry,
    registry_fingerprint,
)
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT, SCHEMA_PATH
from tools.agent_control.reconcile import build_plan, reconcile
from tools.agent_control.validate import validate_registry, validate_registry_path

REPO = Path(__file__).resolve().parents[3]
EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_registry"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.unit
def test_schema_file_declares_draft_2020_12() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_id"]["const"] == "cdb.agent_registry.v1"


@pytest.mark.unit
def test_repo_config_root_validates() -> None:
    document = validate_registry_path(DEFAULT_CONFIG_ROOT)
    assert document["schema_id"] == "cdb.agent_registry.v1"
    assert any(a["agent_id"] == "acp-disabled-placeholder" for a in document["agents"])


@pytest.mark.unit
@pytest.mark.parametrize(
    "name",
    [
        "positive_enabled_valid.json",
        "positive_disabled_agent.json",
        "positive_multi_stable_order.json",
        "positive_aligned_noop_source.json",
    ],
)
def test_positive_fixtures_validate(name: str) -> None:
    validate_registry(_load(name))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("negative_unknown_field.json", "REGISTRY_UNKNOWN_FIELD"),
        ("negative_duplicate_agent_id.json", "REGISTRY_DUPLICATE_AGENT_ID"),
        (
            "negative_missing_contract_profile.json",
            "REGISTRY_UNKNOWN_EXECUTION_CONTRACT_PROFILE",
        ),
        ("negative_unknown_skill_profile.json", "REGISTRY_UNKNOWN_SKILL_PROFILE"),
        ("negative_unknown_provider_profile.json", "REGISTRY_UNKNOWN_PROVIDER_PROFILE"),
        (
            "negative_unknown_environment_profile.json",
            "REGISTRY_UNKNOWN_ENVIRONMENT_PROFILE",
        ),
        ("negative_unknown_mcp_profile.json", "REGISTRY_UNKNOWN_MCP_PROFILE"),
        ("negative_permission_escalation.json", "REGISTRY_PERMISSION_ESCALATION"),
        (
            "negative_contract_ceiling_escalation.json",
            "REGISTRY_PERMISSION_ESCALATION",
        ),
        ("negative_plaintext_secret.json", "REGISTRY_PLAINTEXT_SECRET"),
        ("negative_cyclic_dependency.json", "REGISTRY_CYCLIC_DEPENDENCY"),
        (
            "negative_partially_invalid_registry.json",
            "REGISTRY_UNKNOWN_SKILL_PROFILE",
        ),
    ],
)
def test_negative_fixtures_fail_closed(name: str, code: str) -> None:
    with pytest.raises(RegistryError) as exc:
        validate_registry(_load(name))
    assert exc.value.code == code


@pytest.mark.unit
def test_normalize_stable_agent_order() -> None:
    doc = _load("positive_multi_stable_order.json")
    normalized = normalize_registry(doc)
    ids = [agent["agent_id"] for agent in normalized["agents"]]
    assert ids == sorted(ids)
    assert registry_fingerprint(doc) == registry_fingerprint(deepcopy(doc))


@pytest.mark.unit
def test_identical_inputs_byteidentical_plans() -> None:
    doc = _load("positive_multi_stable_order.json")
    state = {"schema_id": "cdb.agent_registry.observed.v1", "agents": {}}
    plan_a = build_plan(doc, state, mode="plan")
    plan_b = build_plan(deepcopy(doc), deepcopy(state), mode="plan")
    assert dump_json(plan_a) == dump_json(plan_b)
    assert plan_a["plan_digest"] == plan_b["plan_digest"]
    assert [op["agent_id"] for op in plan_a["operations"]] == [
        "alpha",
        "mu",
        "zeta",
    ]
    assert {op["op"] for op in plan_a["operations"]} == {"create"}


@pytest.mark.unit
def test_aligned_state_is_noop() -> None:
    doc = _load("positive_aligned_noop_source.json")
    desired = normalize_registry(doc)["agents"][0]
    fingerprint = agent_desired_fingerprint(desired)
    state = {
        "schema_id": "cdb.agent_registry.observed.v1",
        "agents": {
            "alpha": {
                "agent_id": "alpha",
                "version": "1.0.0",
                "enabled": True,
                "fingerprint": fingerprint,
            }
        },
    }
    plan = build_plan(doc, state, mode="plan")
    assert plan["blocked"] is False
    assert len(plan["operations"]) == 1
    op = plan["operations"][0]
    assert op["op"] == "noop"
    assert op["agent_id"] == "alpha"
    assert op["reason"] == "already_aligned"
    assert op["desired"]["fingerprint"] == fingerprint
    assert op["observed"]["fingerprint"] == fingerprint
    assert plan["mutating_op_count"] == 0


@pytest.mark.unit
def test_disabled_agent_not_created_or_updated() -> None:
    doc = _load("positive_disabled_agent.json")
    state = {"schema_id": "cdb.agent_registry.observed.v1", "agents": {}}
    plan = build_plan(doc, state, mode="plan")
    by_id = {op["agent_id"]: op for op in plan["operations"]}
    assert by_id["alpha"]["op"] == "create"
    assert by_id["beta-disabled"]["op"] == "noop"
    assert by_id["beta-disabled"]["reason"] == "disabled_not_present"


@pytest.mark.unit
def test_disabled_present_agent_is_disabled() -> None:
    doc = _load("positive_disabled_agent.json")
    state = {
        "schema_id": "cdb.agent_registry.observed.v1",
        "agents": {
            "beta-disabled": {
                "agent_id": "beta-disabled",
                "version": "1.0.0",
                "enabled": True,
                "fingerprint": "sha256:deadbeef",
            }
        },
    }
    plan = build_plan(doc, state, mode="plan")
    by_id = {op["agent_id"]: op for op in plan["operations"]}
    assert by_id["beta-disabled"]["op"] == "disable"


@pytest.mark.unit
def test_invalid_registry_blocks_entire_plan_no_partial_ops() -> None:
    doc = _load("negative_partially_invalid_registry.json")
    state = {"schema_id": "cdb.agent_registry.observed.v1", "agents": {}}
    plan = build_plan(doc, state, mode="plan")
    assert plan["blocked"] is True
    assert plan["mutation_intended"] is False
    assert len(plan["operations"]) == 1
    assert plan["operations"][0]["op"] == "block"
    assert plan["operations"][0]["agent_id"] == "*"


@pytest.mark.unit
def test_dry_run_causes_no_mutation() -> None:
    doc = _load("positive_enabled_valid.json")
    backend = MockBackend({"schema_id": "cdb.agent_registry.observed.v1", "agents": {}})
    before = backend.observe()
    result = reconcile(doc, backend, dry_run=True)
    after = backend.observe()
    assert result["dry_run"] is True
    assert result["applied"] is False
    assert before == after
    assert backend.mutations == []
    assert result["plan"]["operations"][0]["op"] == "create"


@pytest.mark.unit
def test_mock_apply_is_idempotent_second_pass_noop() -> None:
    doc = _load("positive_enabled_valid.json")
    backend = MockBackend({"schema_id": "cdb.agent_registry.observed.v1", "agents": {}})
    first = reconcile(doc, backend, dry_run=False)
    assert first["applied"] is True
    second = reconcile(doc, backend, dry_run=False)
    assert second["plan"]["operations"][0]["op"] == "noop"
    assert second["plan"]["mutating_op_count"] == 0


@pytest.mark.unit
def test_registry_cannot_expand_contract_authority() -> None:
    doc = _load("positive_enabled_valid.json")
    doc["agents"][0]["permission_overrides"] = {"publish_cdb_local_ci": True}
    with pytest.raises(RegistryError) as exc:
        validate_registry(doc)
    assert exc.value.code == "REGISTRY_PERMISSION_ESCALATION"


@pytest.mark.unit
def test_nondeterministic_or_duplicate_state_rejected() -> None:
    doc = _load("positive_enabled_valid.json")
    state = {
        "schema_id": "cdb.agent_registry.observed.v1",
        "agents": [
            {
                "agent_id": "alpha",
                "enabled": True,
                "fingerprint": "sha256:a",
            },
            {
                "agent_id": "alpha",
                "enabled": True,
                "fingerprint": "sha256:b",
            },
        ],
    }
    plan = build_plan(doc, state, mode="plan")
    assert plan["blocked"] is True
    assert "REGISTRY_STATE_DUPLICATE_AGENT_ID" in plan["reason"]


@pytest.mark.unit
def test_cli_validate_and_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = EXAMPLES / "positive_multi_stable_order.json"
    state_path = tmp_path / "empty_state.json"
    state_path.write_text(
        json.dumps({"schema_id": "cdb.agent_registry.observed.v1", "agents": {}}),
        encoding="utf-8",
    )
    assert cli_main(["registry", "validate", "--config", str(config)]) == 0
    assert "VALID" in capsys.readouterr().out
    assert (
        cli_main(
            [
                "registry",
                "plan",
                "--config",
                str(config),
                "--state",
                str(state_path),
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["schema_id"] == "cdb.agent_registry.plan.v1"
    assert plan["blocked"] is False


@pytest.mark.unit
def test_cli_reconcile_dry_run_default(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = EXAMPLES / "positive_enabled_valid.json"
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"schema_id": "cdb.agent_registry.observed.v1", "agents": {}}),
        encoding="utf-8",
    )
    rc = cli_main(
        [
            "registry",
            "reconcile",
            "--config",
            str(config),
            "--state",
            str(state_path),
            "--dry-run",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["applied"] is False


@pytest.mark.unit
def test_cli_apply_without_mock_flag_blocked() -> None:
    config = EXAMPLES / "positive_enabled_valid.json"
    rc = cli_main(
        [
            "registry",
            "reconcile",
            "--config",
            str(config),
            "--apply",
        ]
    )
    assert rc == 1


@pytest.mark.unit
def test_directory_loader_matches_schema() -> None:
    document = load_registry_document(DEFAULT_CONFIG_ROOT)
    validate_registry(document)
    assert "acp-registry-reconciler" in {
        agent["agent_id"] for agent in document["agents"]
    }
