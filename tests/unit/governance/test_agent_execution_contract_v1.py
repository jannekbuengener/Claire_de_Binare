"""
test_id: tc_agent_execution_contract_v1_001
test_name: agent_execution_contract_v1_fail_closed
test_type: Bauteil-Test
cdb_area: governance
rule_ref: knowledge/governance/CDB_AGENT_CONTROL_PLANE.md
decision_ref: cdb.agent_execution.v1
issue_ref: 4251
pr_ref: 4286
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest

from tools.agent_execution_contract.attenuation import attenuate_contract
from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.handoff import build_contract_from_router_result
from tools.agent_execution_contract.hashing import attach_digest, compute_digest
from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_execution_contract.paths import normalize_repo_relative_path
from tools.agent_execution_contract.validate import validate_contract

REPO = Path(__file__).resolve().parents[3]
EXAMPLES = REPO / "docs" / "contracts" / "examples" / "agent_execution"
SCHEMA = REPO / "docs" / "contracts" / "cdb_agent_execution.v1.schema.json"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.unit
def test_schema_file_declares_draft_2020_12() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schema_id"]["const"] == "cdb.agent_execution.v1"


@pytest.mark.unit
@pytest.mark.parametrize(
    "name",
    [
        "positive_docs_only_batch_delivery.json",
        "positive_code_and_tests_delivery.json",
        "positive_provider_attenuated.json",
        "positive_handoff_deterministic.json",
    ],
)
def test_positive_fixtures_validate(name: str) -> None:
    validate_contract(_load(name))


@pytest.mark.unit
def test_golden_canonical_bytes_and_digest() -> None:
    contract = _load("positive_docs_only_batch_delivery.json")
    expected_canon = (EXAMPLES / "golden_docs_only_canonical.json.txt").read_text(
        encoding="utf-8"
    )
    expected_digest = (
        (EXAMPLES / "golden_docs_only_digest.txt").read_text(encoding="utf-8").strip()
    )
    assert canonicalize(contract) == expected_canon
    assert contract["integrity"]["digest"] == expected_digest
    assert compute_digest(contract) == expected_digest


@pytest.mark.unit
def test_hash_stable_under_key_order_and_whitespace() -> None:
    contract = _load("positive_docs_only_batch_delivery.json")
    # Re-parse with different key insertion order.
    reshuffled = json.loads(
        json.dumps(contract, sort_keys=False, indent=4, separators=(", ", " : "))
    )
    assert compute_digest(reshuffled) == compute_digest(contract)
    assert canonicalize(reshuffled) == canonicalize(contract)


@pytest.mark.unit
def test_authority_mutation_changes_digest() -> None:
    contract = _load("positive_docs_only_batch_delivery.json")
    mutated = deepcopy(contract)
    mutated["permissions"]["write_docs"] = False
    assert compute_digest(mutated) != contract["integrity"]["digest"]


@pytest.mark.unit
def test_manipulated_hash_rejected() -> None:
    payload = _load("negative_manipulated_hash.json")
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(payload)
    assert exc.value.code == "CONTRACT_HASH_MISMATCH"


@pytest.mark.unit
def test_wrong_schema_rejected() -> None:
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(_load("negative_wrong_schema.json"))
    assert exc.value.code in {"CONTRACT_SCHEMA_INVALID", "CONTRACT_SCHEMA_VERSION"}


@pytest.mark.unit
def test_unknown_field_rejected() -> None:
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(_load("negative_unknown_field.json"))
    assert exc.value.code == "CONTRACT_UNKNOWN_FIELD"


@pytest.mark.unit
def test_missing_permission_rejected() -> None:
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(_load("negative_missing_permission.json"))
    assert exc.value.code in {
        "CONTRACT_SCHEMA_INVALID",
        "CONTRACT_PERMISSION_MISSING",
    }


@pytest.mark.unit
def test_provider_permission_escalation_rejected() -> None:
    base = _load("positive_code_and_tests_delivery.json")
    override = _load("negative_provider_permission_escalation_override.json")
    with pytest.raises(ContractValidationError) as exc:
        attenuate_contract(base, override)
    assert exc.value.code == "CONTRACT_PERMISSION_ESCALATION"


@pytest.mark.unit
def test_provider_scope_expansion_rejected() -> None:
    base = _load("positive_code_and_tests_delivery.json")
    override = _load("negative_provider_scope_expansion_override.json")
    with pytest.raises(ContractValidationError) as exc:
        attenuate_contract(base, override)
    assert exc.value.code == "CONTRACT_SCOPE_EXPANSION"


@pytest.mark.unit
def test_merge_without_authority_rejected() -> None:
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(_load("negative_merge_without_authority.json"))
    assert exc.value.code == "CONTRACT_MERGE_AUTHORITY"


@pytest.mark.unit
def test_plaintext_secret_rejected() -> None:
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(_load("negative_plaintext_secret.json"))
    assert exc.value.code == "CONTRACT_PLAINTEXT_SECRET"


@pytest.mark.unit
def test_path_traversal_rejected() -> None:
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(_load("negative_path_traversal.json"))
    assert exc.value.code in {
        "CONTRACT_SCHEMA_INVALID",
        "CONTRACT_PATH_TRAVERSAL",
        "CONTRACT_PATH_INVALID",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    ["../etc/passwd", "foo/../../bar", "/abs", "a\\b", "a/./b", "a//b", "~/.secrets"],
)
def test_normalize_path_rejects_traversal(raw: str) -> None:
    with pytest.raises(ContractValidationError) as exc:
        normalize_repo_relative_path(raw)
    assert exc.value.code in {"CONTRACT_PATH_TRAVERSAL", "CONTRACT_PATH_INVALID"}


@pytest.mark.unit
def test_nan_and_infinity_rejected_by_jcs() -> None:
    with pytest.raises(ContractValidationError) as exc:
        canonicalize({"wall_time_seconds": math.nan})
    assert exc.value.code == "CONTRACT_NONDETERMINISTIC_NUMBER"
    with pytest.raises(ContractValidationError) as exc2:
        canonicalize({"wall_time_seconds": math.inf})
    assert exc2.value.code == "CONTRACT_NONDETERMINISTIC_NUMBER"
    # Text fixture is intentionally non-JSON for consumers that parse strictly.
    raw = (EXAMPLES / "negative_nan_number.json.txt").read_text(encoding="utf-8")
    assert "NaN" in raw


@pytest.mark.unit
def test_permission_attenuation_is_transitive() -> None:
    base = _load("positive_code_and_tests_delivery.json")
    mid = attenuate_contract(
        base,
        {
            "permissions": {
                **base["permissions"],
                "push": False,
            }
        },
    )
    final = attenuate_contract(
        mid,
        {
            "permissions": {
                **mid["permissions"],
                "commit": False,
            }
        },
    )
    assert mid["permissions"]["push"] is False
    assert final["permissions"]["push"] is False
    assert final["permissions"]["commit"] is False
    validate_contract(final)
    # Escalation from attenuated contract still rejected.
    with pytest.raises(ContractValidationError) as exc:
        attenuate_contract(
            final,
            {"permissions": {**final["permissions"], "push": True}},
        )
    assert exc.value.code == "CONTRACT_PERMISSION_ESCALATION"


@pytest.mark.unit
def test_router_handoff_byte_identical() -> None:
    router = _load("handoff_router_result.json")
    policy = _load("handoff_policy.json")
    first = build_contract_from_router_result(
        router,
        policy=policy,
        agent="cursor-cloud",
        created_at="2026-08-01T20:00:00Z",
        contract_id="aec-issue-4251-handoff",
    )
    second = build_contract_from_router_result(
        router,
        policy=policy,
        agent="cursor-cloud",
        created_at="2026-08-01T20:00:00Z",
        contract_id="aec-issue-4251-handoff",
    )
    assert canonicalize(first) == canonicalize(second)
    assert first == _load("positive_handoff_deterministic.json")


@pytest.mark.unit
def test_handoff_rejects_hold_decision() -> None:
    router = _load("handoff_router_result.json")
    policy = _load("handoff_policy.json")
    router["routing_decision"] = "HOLD_NO_SAFE_ROUTE"
    with pytest.raises(ContractValidationError) as exc:
        build_contract_from_router_result(
            router,
            policy=policy,
            agent="cursor-cloud",
            created_at="2026-08-01T20:00:00Z",
        )
    assert exc.value.code == "CONTRACT_HANDOFF_ROUTE_HOLD"


@pytest.mark.unit
def test_handoff_does_not_grant_merge_from_policy() -> None:
    router = _load("handoff_router_result.json")
    policy = _load("handoff_policy.json")
    policy["permissions"] = {**policy.get("permissions", {}), "merge": True}
    with pytest.raises(ContractValidationError) as exc:
        build_contract_from_router_result(
            router,
            policy=policy,
            agent="cursor-cloud",
            created_at="2026-08-01T20:00:00Z",
        )
    assert exc.value.code == "CONTRACT_PERMISSION_ESCALATION"


@pytest.mark.unit
def test_seal_roundtrip() -> None:
    contract = _load("positive_docs_only_batch_delivery.json")
    unsigned = deepcopy(contract)
    unsigned["integrity"].pop("digest", None)
    sealed = attach_digest(unsigned)
    validate_contract(sealed)
    assert sealed["integrity"]["digest"] == contract["integrity"]["digest"]


@pytest.mark.unit
def test_empty_allowlist_blocks_writes() -> None:
    contract = _load("positive_docs_only_batch_delivery.json")
    contract["execution_scope"]["allowed_paths"] = []
    contract = attach_digest(contract)
    with pytest.raises(ContractValidationError) as exc:
        validate_contract(contract)
    assert exc.value.code == "CONTRACT_SCOPE_EMPTY_ALLOWLIST"
