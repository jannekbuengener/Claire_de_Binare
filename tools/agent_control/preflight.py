"""Contract + registry + environment preflight shared by dry-run and execute."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.agent_control.environment.codes import (
    ENVIRONMENT_LIVE_DISPATCH_FORBIDDEN,
    PROVIDER_LIVE_DISPATCH_FORBIDDEN,
    VERDICT_READY_FOR_RECORDED_TEST,
    VERDICT_READY_OFFLINE_ONLY,
)
from tools.agent_control.environment.preflight import run_environment_preflight
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


def _normalized_branch(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _delivery_target_conflict_message(contract: dict[str, Any]) -> str | None:
    """Return conflict message when route and delivery_target disagree.

    Whitespace-only branches are absent (aligned with dispatch coalesce).
    """
    route = contract.get("route") or {}
    target = (contract.get("execution_scope") or {}).get("delivery_target") or {}
    conflicts: list[str] = []
    for field in ("target_pr", "target_branch"):
        route_val = route.get(field)
        target_val = target.get(field)
        if field == "target_branch":
            route_cmp = _normalized_branch(route_val)
            target_cmp = _normalized_branch(target_val)
            if route_cmp is None or target_cmp is None:
                continue
            if route_cmp != target_cmp:
                conflicts.append(field)
            continue
        route_present = route_val is not None
        target_present = target_val is not None
        if route_present and target_present and route_val != target_val:
            conflicts.append(field)
    if not conflicts:
        return None
    return "route and execution_scope.delivery_target conflict on: " + ", ".join(
        conflicts
    )


def _effective_budget_from_constraints(
    contract_budget: dict[str, Any],
    effective_constraints: dict[str, Any] | None,
) -> dict[str, Any]:
    """Restrictive merge of contract budget with attenuated environment ceilings."""
    budget = deepcopy(contract_budget or {})
    eff = effective_constraints or {}
    wall_e = eff.get("wall_time_seconds")
    if isinstance(wall_e, int) and not isinstance(wall_e, bool):
        wall_c = budget.get("wall_time_seconds")
        if isinstance(wall_c, int) and not isinstance(wall_c, bool):
            budget["wall_time_seconds"] = min(wall_c, wall_e)
        else:
            budget["wall_time_seconds"] = wall_e
    return budget


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
    environment_profile: dict[str, Any] | None = None
    environment_profile_digest: str | None = None
    provider_environment_config_ref: str | None = None
    provider_environment_config_digest: str | None = None
    environment_preflight_verdict: str | None = None
    effective_environment_constraints: dict[str, Any] | None = None
    environment_execute_ready: bool = False

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
    allow_live_cursor: bool = False,
    human_go_live_cursor: bool = False,
    prompt_text_override: str | None = None,
    environment_attestation_path: Path | None = None,
    config_root: Path | None = None,
) -> PreflightResult:
    """Validate contract digest + registry + environment. Shared by dry-run/execute."""
    live_ok = bool(allow_live_cursor and human_go_live_cursor)
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
        route_pr = route.get("target_pr")
        route_branch = _normalized_branch(route.get("target_branch"))
        pr_ok = (
            isinstance(route_pr, int)
            and not isinstance(route_pr, bool)
            and route_pr > 0
        )
        if not pr_ok or route_branch is None:
            return _fail(
                "DISPATCH_ROUTE_TARGET_MISSING",
                "safe existing/continuation route requires target_pr and target_branch",
                terminal_state="BLOCKED",
            )

    conflict_msg = _delivery_target_conflict_message(validated)
    if conflict_msg:
        return _fail(
            "DISPATCH_DELIVERY_TARGET_CONFLICT",
            conflict_msg,
            terminal_state="BLOCKED",
        )

    permissions = validated.get("permissions") or {}
    for key in SLICE_FORBIDDEN_TRUE:
        if permissions.get(key) is True:
            return _fail(
                "DISPATCH_FORBIDDEN_PERMISSION",
                f"permission {key}=true is forbidden for dispatcher slice",
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
    env_profile_id = agent["environment_profile"]
    env_profile = profiles["environments"][env_profile_id]
    source_commit = None
    work_order = validated.get("provider_work_order") or {}
    if isinstance(work_order, dict):
        source_commit = work_order.get("source_commit")

    root = repo_root or Path(__file__).resolve().parents[2]
    env_result = run_environment_preflight(
        profile_id=env_profile_id,
        provider_id=str(provider_id) if provider_id else None,
        contract=validated,
        source_commit=str(source_commit) if source_commit else None,
        attestation_path=environment_attestation_path,
        config=config_root or root / "config" / "agent-control",
        repo_root=root,
        execute=execute,
        allow_recorded=allow_recorded_cursor or live_ok,
        allow_live=live_ok,
    )

    if execute and provider_id != "mock":
        if provider_id in CURSOR_PROVIDER_IDS:
            # Durable gate: environment preflight never enables live dispatch.
            # Profile live_dispatch=true remains forbidden; Human-GO uses flags.
            if live_dispatch:
                return _fail(
                    ENVIRONMENT_LIVE_DISPATCH_FORBIDDEN,
                    "provider live_dispatch=true is forbidden; "
                    "use Human-GO allow_live_cursor flags instead of profile flip",
                    terminal_state="BLOCKED",
                )
            if not allow_recorded_cursor and not live_ok:
                return _fail(
                    PROVIDER_LIVE_DISPATCH_FORBIDDEN,
                    f"execute for {provider_id!r} requires recorded/fake transport "
                    "or Human-GO live cursor flags",
                    terminal_state="BLOCKED",
                )
            if allow_recorded_cursor and not live_ok:
                if env_result.verdict != VERDICT_READY_FOR_RECORDED_TEST:
                    return _fail(
                        (
                            env_result.reason_codes[0]
                            if env_result.reason_codes
                            else "ENVIRONMENT_EXECUTE_NOT_READY"
                        ),
                        f"environment preflight verdict {env_result.verdict} "
                        f"blocks recorded execute: {env_result.limitations}",
                        terminal_state="BLOCKED",
                    )
            elif live_ok:
                if env_result.verdict not in {
                    VERDICT_READY_FOR_RECORDED_TEST,
                    VERDICT_READY_OFFLINE_ONLY,
                }:
                    # Live path still needs a non-blocked environment surface.
                    from tools.agent_control.environment.codes import VERDICT_BLOCKED

                    if env_result.verdict == VERDICT_BLOCKED:
                        return _fail(
                            (
                                env_result.reason_codes[0]
                                if env_result.reason_codes
                                else "ENVIRONMENT_EXECUTE_NOT_READY"
                            ),
                            f"environment preflight verdict {env_result.verdict} "
                            f"blocks live execute: {env_result.limitations}",
                            terminal_state="BLOCKED",
                        )
        else:
            return _fail(
                PROVIDER_LIVE_DISPATCH_FORBIDDEN,
                f"execute forbidden for provider_id={provider_id!r}",
                terminal_state="BLOCKED",
            )

    # Dry-run: environment must not be schema-hard-broken for cloud profiles.
    if not execute and env_profile.get("runtime_class") == "cloud_agent":
        if env_result.verdict not in {
            VERDICT_READY_OFFLINE_ONLY,
            VERDICT_READY_FOR_RECORDED_TEST,
        }:
            return _fail(
                (
                    env_result.reason_codes[0]
                    if env_result.reason_codes
                    else "ENVIRONMENT_PREFLIGHT_BLOCKED"
                ),
                f"environment dry-run blocked: {env_result.verdict}",
                terminal_state="BLOCKED",
            )

    prompt_ref = None
    prompt_digest = None
    prompt_text = None
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

    # Effective run budget uses attenuated environment ceilings; contract stays intact.
    effective_budget = _effective_budget_from_constraints(
        budget, env_result.effective_constraints
    )

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
        budget=effective_budget,
        prompt_ref=prompt_ref,
        prompt_digest=prompt_digest,
        prompt_text=prompt_text,
        provider_profile=provider_profile,
        environment_profile=env_result.profile_snapshot or env_profile,
        environment_profile_digest=env_result.profile_digest,
        provider_environment_config_ref=env_result.provider_config_ref,
        provider_environment_config_digest=env_result.provider_config_digest,
        environment_preflight_verdict=env_result.verdict,
        effective_environment_constraints=env_result.effective_constraints,
        environment_execute_ready=env_result.execute_ready,
    )
