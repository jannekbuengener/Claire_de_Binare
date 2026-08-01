"""Contract + registry preflight shared by dry-run and execute paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.agent_control.errors import DispatchError, RegistryError
from tools.agent_control.normalize import normalize_registry
from tools.agent_control.providers.factory import CURSOR_PROVIDER_IDS
from tools.agent_control.validate import validate_registry
from tools.agent_execution_contract.attenuation import PERMISSION_KEYS
from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.hashing import compute_digest
from tools.agent_execution_contract.validate import validate_contract
from tools.agent_execution_contract.work_order import verify_provider_work_order

HOLD_ROUTE_DECISIONS = frozenset({"HOLD_PR_LOCK_CONFLICT", "HOLD_NO_SAFE_ROUTE"})
SAFE_ROUTE_DECISIONS = frozenset(
    {
        "ROUTE_TO_EXISTING_BATCH_PR",
        "ROUTE_TO_EXISTING_DEDICATED_PR",
        "CREATE_NEW_BATCH_PR",
        "CREATE_DEDICATED_PR",
        "OPERATIONAL_BATCH_CONTINUATION",
    }
)
SLICE_FORBIDDEN_TRUE = frozenset(
    {
        "merge",
        "publish_cdb_local_ci",
        "close_issue",
        "runtime_mutation",
        "database_mutation",
        "mcp_live_mutation",
    }
)


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    terminal_state: str | None
    code: str | None
    message: str | None
    contract: dict[str, Any] | None
    contract_digest: str | None
    agent: dict[str, Any] | None
    provider_id: str | None
    route: dict[str, Any] | None
    budget: dict[str, Any] | None
    prompt_ref: str | None = None
    prompt_digest: str | None = None
    prompt_text: str | None = None
    provider_profile: dict[str, Any] | None = None

    def raise_if_blocked_for_execute(self) -> None:
        if self.ok:
            return
        raise DispatchError(
            self.code or "DISPATCH_PREFLIGHT_BLOCKED", self.message or ""
        )


def _fail(
    code: str,
    message: str,
    *,
    terminal_state: str = "BLOCKED",
) -> PreflightResult:
    # HOLD router decisions use HOLD; integrity/safety use BLOCKED.
    return PreflightResult(
        ok=False,
        terminal_state=terminal_state,
        code=code,
        message=message,
        contract=None,
        contract_digest=None,
        agent=None,
        provider_id=None,
        route=None,
        budget=None,
    )


def preflight(
    contract: dict[str, Any],
    registry_document: dict[str, Any],
    agent_id: str,
    *,
    execute: bool,
    repo_root: Path | None = None,
    allow_recorded_cursor: bool = False,
    prompt_text_override: str | None = None,
) -> PreflightResult:
    """Validate contract digest + registry binding. Shared by dry-run and execute."""
    try:
        validated = validate_contract(contract)
    except ContractValidationError as exc:
        return _fail(exc.code, exc.message, terminal_state="BLOCKED")

    digest = compute_digest(validated)
    sealed = (validated.get("integrity") or {}).get("digest")
    if sealed != digest:
        return _fail(
            "CONTRACT_HASH_MISMATCH",
            "contract digest mismatch before provider dispatch",
            terminal_state="BLOCKED",
        )

    route = validated.get("route") or {}
    decision = route.get("routing_decision")
    if decision in HOLD_ROUTE_DECISIONS:
        return _fail(
            decision,
            f"router decision {decision} must never dispatch",
            terminal_state="HOLD",
        )
    if decision not in SAFE_ROUTE_DECISIONS:
        return _fail(
            "DISPATCH_ROUTE_UNSUPPORTED",
            f"unsupported routing_decision: {decision!r}",
            terminal_state="BLOCKED",
        )

    # Existing/continuation routes require concrete target binding.
    needs_target = decision in {
        "ROUTE_TO_EXISTING_BATCH_PR",
        "ROUTE_TO_EXISTING_DEDICATED_PR",
        "OPERATIONAL_BATCH_CONTINUATION",
    }
    if needs_target:
        if not route.get("target_pr") or not route.get("target_branch"):
            return _fail(
                "DISPATCH_ROUTE_TARGET_MISSING",
                "safe existing/continuation route requires target_pr and target_branch",
                terminal_state="BLOCKED",
            )

    permissions = validated.get("permissions") or {}
    for key in SLICE_FORBIDDEN_TRUE:
        if permissions.get(key) is True:
            return _fail(
                "DISPATCH_FORBIDDEN_PERMISSION",
                f"permission {key}=true is forbidden for dispatcher slice #4253",
                terminal_state="BLOCKED",
            )

    budget = validated.get("budget") or {}
    if execute:
        for key in ("wall_time_seconds", "max_iterations", "max_tool_calls"):
            value = budget.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                return _fail(
                    "DISPATCH_ZERO_BUDGET",
                    f"execute blocked: budget.{key} must be > 0 (got {value!r})",
                    terminal_state="BLOCKED",
                )

    try:
        validate_registry(registry_document)
        normalized = normalize_registry(registry_document)
    except RegistryError as exc:
        return _fail(exc.code, exc.message, terminal_state="BLOCKED")

    agents = {agent["agent_id"]: agent for agent in normalized["agents"]}
    agent = agents.get(agent_id)
    if agent is None:
        return _fail(
            "DISPATCH_UNKNOWN_AGENT",
            f"agent_id {agent_id!r} not found in registry",
            terminal_state="BLOCKED",
        )
    if not agent["enabled"]:
        return _fail(
            "DISPATCH_AGENT_DISABLED",
            f"agent_id {agent_id!r} is disabled",
            terminal_state="BLOCKED",
        )

    # Profile resolvability already enforced by registry validate; re-check bind.
    profiles = normalized["profiles"]
    for kind, ref in (
        ("execution_contracts", agent["execution_contract_profile"]),
        ("providers", agent["provider_profile"]),
        ("environments", agent["environment_profile"]),
    ):
        if ref not in profiles[kind]:
            return _fail(
                "DISPATCH_PROFILE_UNRESOLVED",
                f"agent {agent_id!r}: unresolved {kind} profile {ref!r}",
                terminal_state="BLOCKED",
            )
    for skill_ref in agent["skills"]:
        if skill_ref not in profiles["skills"]:
            return _fail(
                "DISPATCH_PROFILE_UNRESOLVED",
                f"agent {agent_id!r}: unresolved skill profile {skill_ref!r}",
                terminal_state="BLOCKED",
            )
    for mcp_ref in agent["mcp_profiles"]:
        if mcp_ref not in profiles["mcp"]:
            return _fail(
                "DISPATCH_PROFILE_UNRESOLVED",
                f"agent {agent_id!r}: unresolved mcp profile {mcp_ref!r}",
                terminal_state="BLOCKED",
            )

    ceiling = agent["effective_permissions"]
    for key in PERMISSION_KEYS:
        if permissions.get(key) and not ceiling.get(key):
            return _fail(
                "DISPATCH_PERMISSION_CEILING",
                f"contract permission {key}=true exceeds registry ceiling",
                terminal_state="BLOCKED",
            )

    provider_profile = profiles["providers"][agent["provider_profile"]]
    provider_id = provider_profile.get("provider_id")
    contract_provider = (
        (validated.get("environment") or {}).get("provider_profile") or {}
    ).get("provider_id")
    if contract_provider and contract_provider != provider_id:
        return _fail(
            "DISPATCH_PROVIDER_MISMATCH",
            f"contract provider_id {contract_provider!r} != registry {provider_id!r}",
            terminal_state="BLOCKED",
        )

    # Routing selector conflicts (lane) → BLOCKED.
    selectors = agent.get("labels_or_routing_selectors") or {}
    lane_selector = selectors.get("lane")
    if lane_selector is not None and route.get("lane") not in {None, lane_selector}:
        return _fail(
            "DISPATCH_ROUTING_SELECTOR_CONFLICT",
            f"registry lane {lane_selector!r} conflicts with contract lane "
            f"{route.get('lane')!r}",
            terminal_state="BLOCKED",
        )

    live_dispatch = bool(provider_profile.get("live_dispatch", False))
    if execute and provider_id != "mock":
        if provider_id in CURSOR_PROVIDER_IDS:
            if live_dispatch and not allow_recorded_cursor:
                return _fail(
                    "CURSOR_ENVIRONMENT_PROFILE_NOT_READY",
                    "real Cursor write/live dispatch blocked until #4255",
                    terminal_state="BLOCKED",
                )
            if not allow_recorded_cursor and not live_dispatch:
                return _fail(
                    "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                    f"execute for {provider_id!r} requires recorded/fake transport "
                    "or later environment profile (#4255)",
                    terminal_state="BLOCKED",
                )
        else:
            return _fail(
                "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                f"execute forbidden for provider_id={provider_id!r}",
                terminal_state="BLOCKED",
            )

    prompt_ref = None
    prompt_digest = None
    prompt_text = None
    root = repo_root or Path(__file__).resolve().parents[2]
    try:
        prompt_ref, prompt_digest, prompt_text = verify_provider_work_order(
            validated,
            provider_id=str(provider_id),
            repo_root=root,
            require_for_live_provider=execute and provider_id in CURSOR_PROVIDER_IDS,
            prompt_text_override=prompt_text_override,
            verify_content=execute or prompt_text_override is not None,
        )
    except ContractValidationError as exc:
        return _fail(exc.code, exc.message, terminal_state="BLOCKED")

    return PreflightResult(
        ok=True,
        terminal_state=None,
        code=None,
        message=None,
        contract=validated,
        contract_digest=digest,
        agent=agent,
        provider_id=provider_id,
        route=route,
        budget=budget,
        prompt_ref=prompt_ref,
        prompt_digest=prompt_digest,
        prompt_text=prompt_text,
        provider_profile=provider_profile,
    )
