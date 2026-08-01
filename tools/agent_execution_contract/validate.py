"""Schema + semantic validation for cdb.agent_execution.v1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from tools.agent_execution_contract.attenuation import PERMISSION_KEYS
from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.hashing import verify_digest
from tools.agent_execution_contract.paths import normalize_path_list

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "cdb_agent_execution.v1.schema.json"

_SECRET_VALUE_HINT = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|bearer)\b\s*[:=]\s*\S+"
)


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _schema_validate(contract: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda err: list(err.path))
    if not errors:
        return
    first = errors[0]
    path = ".".join(str(part) for part in first.path) or "<root>"
    msg = first.message
    code = "CONTRACT_SCHEMA_INVALID"
    if "Additional properties are not allowed" in msg:
        code = "CONTRACT_UNKNOWN_FIELD"
    raise ContractValidationError(code, f"{path}: {msg}")


def _reject_plaintext_secrets(node: Any, *, path: str = "$") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _reject_plaintext_secrets(value, path=f"{path}.{key}")
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            _reject_plaintext_secrets(value, path=f"{path}[{idx}]")
    elif isinstance(node, str):
        if _SECRET_VALUE_HINT.search(node):
            raise ContractValidationError(
                "CONTRACT_PLAINTEXT_SECRET",
                f"plaintext secret-like value rejected at {path}",
            )


def _semantic_validate(contract: dict[str, Any]) -> None:
    if contract.get("schema_id") != "cdb.agent_execution.v1":
        raise ContractValidationError(
            "CONTRACT_SCHEMA_VERSION",
            "schema_id must be cdb.agent_execution.v1",
        )
    schema_version = contract.get("schema_version")
    if schema_version not in {"1.0.0", "1.1.0"}:
        raise ContractValidationError(
            "CONTRACT_SCHEMA_VERSION",
            "schema_version must be 1.0.0 or 1.1.0",
        )

    work_order = contract.get("provider_work_order")
    if work_order is not None:
        if not isinstance(work_order, dict):
            raise ContractValidationError(
                "CONTRACT_PROVIDER_WORK_ORDER_INVALID",
                "provider_work_order must be an object",
            )
        for key in ("prompt_ref", "source_commit", "prompt_digest"):
            if not work_order.get(key):
                raise ContractValidationError(
                    "CONTRACT_PROVIDER_WORK_ORDER_INVALID",
                    f"provider_work_order.{key} is required when work order is present",
                )

    permissions = contract.get("permissions")
    if not isinstance(permissions, dict):
        raise ContractValidationError(
            "CONTRACT_PERMISSION_INVALID",
            "permissions must be an object",
        )
    for key in PERMISSION_KEYS:
        if key not in permissions:
            raise ContractValidationError(
                "CONTRACT_PERMISSION_MISSING",
                f"missing permission {key!r}; absent must never be interpreted as true",
            )
        if not isinstance(permissions[key], bool):
            raise ContractValidationError(
                "CONTRACT_PERMISSION_INVALID",
                f"permission {key!r} must be boolean",
            )

    # Delivery-safe defaults for merge/publish: required false unless a future
    # governance-authored contract explicitly sets them under a different role.
    # v1 rejects true for these on producer=pr_router_handoff.
    producer = contract.get("producer") or {}
    if producer.get("component") in {"pr_router_handoff", "explicit_policy"}:
        if permissions.get("merge") is True:
            raise ContractValidationError(
                "CONTRACT_MERGE_AUTHORITY",
                "merge=true is rejected without explicit governance merge authority",
            )
        if permissions.get("publish_cdb_local_ci") is True:
            raise ContractValidationError(
                "CONTRACT_MERGE_AUTHORITY",
                "publish_cdb_local_ci=true is rejected without governance authority",
            )

    merge_authority = (contract.get("validation_and_delivery") or {}).get(
        "merge_authority"
    )
    if (
        not isinstance(merge_authority, dict)
        or merge_authority.get("granted") is not False
    ):
        raise ContractValidationError(
            "CONTRACT_MERGE_AUTHORITY",
            "merge_authority.granted must be false for delivery contracts",
        )

    scope = contract.get("execution_scope") or {}
    allowed = list(scope.get("allowed_paths") or [])
    forbidden = list(scope.get("forbidden_paths") or [])
    normalize_path_list(allowed)
    normalize_path_list(forbidden)

    write_needed = any(
        permissions.get(key)
        for key in (
            "write_code",
            "write_docs",
            "commit",
            "push",
            "open_pr",
            "update_pr",
        )
    )
    if write_needed and not allowed:
        raise ContractValidationError(
            "CONTRACT_SCOPE_EMPTY_ALLOWLIST",
            "empty/missing allowed_paths means no write authority",
        )

    budget = contract.get("budget") or {}
    for key in ("wall_time_seconds", "max_iterations", "max_tool_calls"):
        value = budget.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ContractValidationError(
                "CONTRACT_BUDGET_INVALID",
                f"budget.{key} must be a finite non-negative integer",
            )

    network = budget.get("network_policy") or {}
    if network.get("mode") == "allowlist":
        domains = network.get("allowed_domains") or []
        classes = network.get("allowed_classes") or []
        if not domains and not classes:
            raise ContractValidationError(
                "CONTRACT_BUDGET_INVALID",
                "allowlist network_policy requires domains or classes",
            )

    _reject_plaintext_secrets(contract)
    verify_digest(contract)


def validate_contract(
    contract: dict[str, Any],
    *,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate schema + semantics + digest. Returns the contract on success."""
    if not isinstance(contract, dict):
        raise ContractValidationError(
            "CONTRACT_TYPE_INVALID",
            "contract must be a JSON object",
        )
    active_schema = schema if schema is not None else load_schema()
    try:
        _schema_validate(contract, active_schema)
    except ValidationError as exc:  # pragma: no cover - converted above
        raise ContractValidationError("CONTRACT_SCHEMA_INVALID", str(exc)) from exc
    _semantic_validate(contract)
    return contract


def validate_contract_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_contract(payload)
