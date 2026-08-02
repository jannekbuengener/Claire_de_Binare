"""Provider-neutral dispatcher orchestrator (#4253)."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils.uuid_gen import generate_runtime_id_hex
from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_control.clock import Clock, SystemClock
from tools.agent_control.errors import DispatchError
from tools.agent_control.lifecycle import TERMINAL_STATES, transition
from tools.agent_control.preflight import preflight
from tools.agent_control.provider import (
    MockProvider,
    Provider,
    ProviderRequest,
    get_provider,
)
from tools.agent_control.run_store import RunStore
from tools.agent_control.evidence.redact import sanitize_result_refs

ALLOWED_DELIVERY_STATUSES = frozenset(
    {
        "DONE_SLICE_ADDED_TO_BATCH_PR",
        "DONE_PR_OPEN",
        "DONE_PR_OPEN_MERGE_HANDOFF",
    }
)

CREATE_ROUTE_DECISIONS = frozenset(
    {
        "CREATE_NEW_BATCH_PR",
        "CREATE_DEDICATED_PR",
    }
)


def _persist_evidence_bindings(
    record: dict[str, Any],
    pf: Any,
    result: Any | None = None,
) -> None:
    """Additive #4256 bindings; never persists prompt_text or secrets."""
    env_profile = pf.environment_profile or {}
    agent = pf.agent or {}
    contract_env = (pf.contract or {}).get("environment") or {}
    record["environment_profile_id"] = (
        env_profile.get("profile_id")
        or agent.get("environment_profile")
        or contract_env.get("environment_profile")
    )
    record["environment_profile_version"] = env_profile.get("profile_version")
    record["environment_profile_digest"] = pf.environment_profile_digest
    record["provider_config_digest"] = pf.provider_environment_config_digest
    record["environment_preflight_verdict"] = pf.environment_preflight_verdict
    work_order = (pf.contract or {}).get("provider_work_order") or {}
    record["source_commit"] = work_order.get("source_commit")
    record["prompt_ref"] = pf.prompt_ref
    record["prompt_digest"] = pf.prompt_digest
    if result is not None:
        record["result_refs"] = sanitize_result_refs(
            getattr(result, "result_refs", None)
        )
        if getattr(result, "usage", None) is not None:
            record["usage"] = dict(result.usage)


def _iso(clock: Clock) -> str:
    value = clock.now()
    return value.isoformat().replace("+00:00", "Z")


def _event(
    seq: int,
    name: str,
    *,
    from_state: str | None,
    to_state: str | None,
    at: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "seq": seq,
        "name": name,
        "from_state": from_state,
        "to_state": to_state,
        "at": at,
        "detail": detail or {},
    }


def _append_event(record: dict[str, Any], event: dict[str, Any]) -> None:
    events = record.setdefault("lifecycle_events", [])
    if events and int(event["seq"]) <= int(events[-1]["seq"]):
        raise DispatchError(
            "DISPATCH_EVENT_SEQ_INVALID",
            "lifecycle event seq must be strictly monotonic",
        )
    events.append(event)


def _apply_state(
    record: dict[str, Any],
    nxt: str,
    *,
    event_name: str,
    clock: Clock,
    detail: dict[str, Any] | None = None,
) -> None:
    current = record["state"]
    transition(current, nxt)
    at = _iso(clock)
    seq = len(record.get("lifecycle_events") or []) + 1
    _append_event(
        record,
        _event(seq, event_name, from_state=current, to_state=nxt, at=at, detail=detail),
    )
    record["state"] = nxt
    record["updated_at"] = at
    if nxt in TERMINAL_STATES:
        record["terminal_reason"] = (detail or {}).get("reason") or event_name
        record["terminal_code"] = (detail or {}).get("code")


def _idempotency_key(contract_digest: str, agent_id: str, attempt: int) -> str:
    raw = f"{contract_digest}|{agent_id}|{attempt}"
    return "idem-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _new_run_id() -> str:
    return "adr-" + generate_runtime_id_hex(16)


def build_dry_run_plan(
    contract: dict[str, Any],
    registry_document: dict[str, Any],
    agent_id: str,
    *,
    scenario: str = "success",
) -> dict[str, Any]:
    """Deterministic dry-run plan. No provider calls, no store writes."""
    result = preflight(contract, registry_document, agent_id, execute=False)
    plan: dict[str, Any] = {
        "schema_id": "cdb.agent_dispatch_plan.v1",
        "mode": "dry-run",
        "agent_id": agent_id,
        "scenario": scenario,
        "preflight_ok": result.ok,
        "preflight_code": result.code,
        "preflight_message": result.message,
        "terminal_state_if_execute_blocked": result.terminal_state,
        "contract_id": (
            contract.get("contract_id") if isinstance(contract, dict) else None
        ),
        "contract_digest": result.contract_digest,
        "provider_id": result.provider_id,
        "route": result.route,
        "planned_transitions": [],
        "provider_calls_intended": 0,
        "state_writes_intended": 0,
    }
    if result.ok:
        plan["planned_transitions"] = [
            "PLANNED",
            "ROUTED",
            "CONTRACTED",
            "DISPATCHED",
            "RUNNING",
            "DELIVERED",
            "PASS",
        ]
        plan["provider_calls_intended"] = 0
        plan["state_writes_intended"] = 0
        plan["note"] = "dry-run only; execute requires --execute --allow-mock-dispatch"
    digest = hashlib.sha256(canonicalize(plan).encode("utf-8")).hexdigest()
    plan["plan_digest"] = f"sha256:{digest}"
    return plan


def _normalized_branch(value: Any) -> str | None:
    """Return stripped branch name, or None for missing/whitespace-only."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _field_present(value: Any, *, field: str) -> bool:
    if value is None:
        return False
    if field == "target_branch":
        return _normalized_branch(value) is not None
    return True


def assert_delivery_target_consistent(contract: dict[str, Any]) -> None:
    """Fail-closed when route and delivery_target disagree on the same field.

    Identical duplicates remain allowed. Create routes may leave targets empty
    until a validated provider receipt supplies them. Whitespace-only branches
    are treated as absent (same semantics as coalesce in `_delivery_target`).
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
        if not (
            _field_present(route_val, field=field)
            and _field_present(target_val, field=field)
        ):
            continue
        if route_val != target_val:
            conflicts.append(field)
    if conflicts:
        raise DispatchError(
            "DISPATCH_DELIVERY_TARGET_CONFLICT",
            "route and execution_scope.delivery_target conflict on: "
            + ", ".join(conflicts),
        )


def _delivery_target(contract: dict[str, Any]) -> dict[str, Any]:
    assert_delivery_target_consistent(contract)
    scope = contract.get("execution_scope") or {}
    target = scope.get("delivery_target") or {}
    route = contract.get("route") or {}
    # Whitespace-only branches must not win over a real route branch via
    # truthy `or` (R1 / #4293 acceptance residual).
    delivery_branch = _normalized_branch(target.get("target_branch"))
    route_branch = _normalized_branch(route.get("target_branch"))
    return {
        "target_pr": target.get("target_pr") or route.get("target_pr"),
        "target_branch": delivery_branch or route_branch,
        "expected_status": target.get("expected_status")
        or "DONE_SLICE_ADDED_TO_BATCH_PR",
        "routing_decision": route.get("routing_decision"),
    }


def effective_dispatch_budget(
    contract_budget: dict[str, Any] | None,
    effective_constraints: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge contract budget with attenuated environment ceilings (restrictive).

    Does not mutate the signed/hashed contract input. Numeric ceilings take the
    more restrictive value when both sides are present.
    """
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


def _merge_observed_create_targets(
    record: dict[str, Any], receipt: dict[str, Any]
) -> None:
    """For CREATE routes, persist validated receipt targets onto the run route."""
    route = record.get("route") or {}
    routing = route.get("routing_decision")
    if routing not in CREATE_ROUTE_DECISIONS:
        return
    updated = False
    receipt_pr = receipt.get("target_pr")
    receipt_branch = receipt.get("target_branch")
    if isinstance(receipt_pr, int) and receipt_pr > 0:
        route["target_pr"] = receipt_pr
        updated = True
    if isinstance(receipt_branch, str) and receipt_branch.strip():
        route["target_branch"] = receipt_branch
        updated = True
    if updated:
        route["target_provenance"] = "route+validated_provider_receipt"
    record["route"] = route


def _expected_delivery_from_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Contract-sealed delivery expectations (not a fabricated receipt)."""
    return deepcopy(_delivery_target(contract))


def _validate_delivery_receipt(
    contract: dict[str, Any], receipt: dict[str, Any] | None
) -> None:
    if not isinstance(receipt, dict):
        raise DispatchError(
            "DISPATCH_DELIVERY_RECEIPT_MISSING",
            "DELIVERED requires a validated delivery receipt",
        )
    target = _delivery_target(contract)
    routing = target.get("routing_decision")
    contract_pr = target.get("target_pr")
    receipt_pr = receipt.get("target_pr")
    if routing in CREATE_ROUTE_DECISIONS and contract_pr is None:
        if not isinstance(receipt_pr, int) or int(receipt_pr) <= 0:
            raise DispatchError(
                "DISPATCH_DELIVERY_RECEIPT_MISMATCH",
                "create route requires observed positive target_pr on receipt",
            )
    elif receipt_pr != contract_pr:
        raise DispatchError(
            "DISPATCH_DELIVERY_RECEIPT_MISMATCH",
            "delivery receipt target_pr does not match contract",
        )
    contract_branch = target.get("target_branch")
    receipt_branch = receipt.get("target_branch")
    if routing in CREATE_ROUTE_DECISIONS and not contract_branch:
        if not isinstance(receipt_branch, str) or not receipt_branch.strip():
            raise DispatchError(
                "DISPATCH_DELIVERY_RECEIPT_MISMATCH",
                "create route requires observed target_branch on receipt",
            )
    elif receipt_branch != contract_branch:
        raise DispatchError(
            "DISPATCH_DELIVERY_RECEIPT_MISMATCH",
            "delivery receipt target_branch does not match contract",
        )
    status = receipt.get("delivery_status")
    if status not in ALLOWED_DELIVERY_STATUSES:
        raise DispatchError(
            "DISPATCH_DELIVERY_STATUS_INVALID",
            f"delivery_status {status!r} not allowed",
        )
    expected = target.get("expected_status")
    if expected and status != expected:
        raise DispatchError(
            "DISPATCH_DELIVERY_STATUS_MISMATCH",
            f"delivery_status {status!r} != expected {expected!r}",
        )
    commit = receipt.get("commit")
    if not isinstance(commit, str) or not commit or commit == ("0" * 40):
        raise DispatchError(
            "DISPATCH_DELIVERY_RECEIPT_INCOMPLETE",
            "delivery receipt requires a non-fabricated observed commit",
        )


def _budget_exceeded(budget: dict[str, Any], usage: dict[str, Any]) -> str | None:
    if int(usage.get("iterations", 0)) > int(budget.get("max_iterations", 0)):
        return "max_iterations"
    if int(usage.get("tool_calls", 0)) > int(budget.get("max_tool_calls", 0)):
        return "max_tool_calls"
    return None


def _wall_time_exceeded(
    record: dict[str, Any], budget: dict[str, Any], clock: Clock
) -> bool:
    created = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
    elapsed = (clock.now() - created).total_seconds()
    return elapsed > float(budget.get("wall_time_seconds", 0))


def dispatch_run(
    contract: dict[str, Any],
    registry_document: dict[str, Any],
    agent_id: str,
    store: RunStore | None = None,
    *,
    dry_run: bool = True,
    allow_mock_dispatch: bool = False,
    allow_recorded_cursor: bool = False,
    scenario: str = "success",
    clock: Clock | None = None,
    provider: Provider | None = None,
    previous_run_id: str | None = None,
    attempt: int | None = None,
    run_id: str | None = None,
    prompt_text_override: str | None = None,
    environment_attestation_path: Path | None = None,
) -> dict[str, Any]:
    clock = clock or SystemClock()
    if dry_run:
        return {
            "dry_run": True,
            "applied": False,
            "plan": build_dry_run_plan(
                contract, registry_document, agent_id, scenario=scenario
            ),
            "run": None,
        }
    if store is None:
        raise DispatchError(
            "DISPATCH_STATE_REQUIRED",
            "execute requires a RunStore",
        )

    if not allow_mock_dispatch and not allow_recorded_cursor:
        raise DispatchError(
            "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
            "execute requires --allow-mock-dispatch or recorded/fake Cursor transport",
        )

    pf = preflight(
        contract,
        registry_document,
        agent_id,
        execute=True,
        allow_recorded_cursor=allow_recorded_cursor,
        prompt_text_override=prompt_text_override,
        environment_attestation_path=environment_attestation_path,
    )
    if not pf.ok:
        # Persist a blocked/held terminal run only when execute was requested and
        # preflight fails after explicit mock allow — still no provider call.
        # Spec: dry-run writes nothing; execute may record blocked attempts.
        # To keep fail-closed and observable, create a terminal run record.
        at = _iso(clock)
        blocked_id = run_id or _new_run_id()
        terminal = pf.terminal_state or "BLOCKED"
        record = {
            "schema_id": "cdb.agent_dispatch_run.v1",
            "schema_version": "1.0.0",
            "run_id": blocked_id,
            "attempt": attempt or 1,
            "previous_run_id": previous_run_id,
            "revision": 0,
            "state": "PLANNED",
            "contract_id": contract.get("contract_id"),
            "contract_digest": None,
            "delivery_issue": (contract.get("issue") or {}).get("number"),
            "route": {
                "routing_decision": (contract.get("route") or {}).get(
                    "routing_decision"
                ),
                "target_pr": (contract.get("route") or {}).get("target_pr"),
                "target_branch": (contract.get("route") or {}).get("target_branch"),
                "lane": (contract.get("route") or {}).get("lane"),
            },
            "agent_id": agent_id,
            "provider_id": None,
            "provider_run_id": None,
            "budget": contract.get("budget") or {},
            "usage": {"iterations": 0, "tool_calls": 0},
            "lifecycle_events": [],
            "terminal_reason": pf.message,
            "terminal_code": pf.code,
            "idempotency_key": None,
            "created_at": at,
            "updated_at": at,
            "scenario": scenario,
        }
        _apply_state(
            record,
            terminal if terminal in {"HOLD", "BLOCKED", "CANCELLED"} else "BLOCKED",
            event_name="preflight_failed",
            clock=clock,
            detail={"code": pf.code, "reason": pf.message},
        )
        record["revision"] = 0
        store.create(record)
        return {"dry_run": False, "applied": True, "plan": None, "run": record}

    assert pf.contract is not None
    assert pf.contract_digest is not None
    assert pf.agent is not None
    assert pf.provider_id is not None

    attempt_n = attempt or 1
    idem = _idempotency_key(pf.contract_digest, agent_id, attempt_n)
    existing = store.find_by_idempotency(idem)
    if existing is not None:
        return {
            "dry_run": False,
            "applied": False,
            "idempotent_replay": True,
            "plan": None,
            "run": existing,
        }

    active_provider = provider or get_provider(pf.provider_id)
    if (
        not isinstance(active_provider, MockProvider)
        and pf.provider_id != "mock"
        and not allow_recorded_cursor
    ):
        raise DispatchError(
            "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
            "Cursor providers require recorded/fake transport in #4254",
        )

    at = _iso(clock)
    rid = run_id or _new_run_id()
    expected_delivery = _expected_delivery_from_contract(pf.contract)
    # Effective budget = contract ∩ attenuated environment ceilings.
    # Contract digest/input remain untouched; only the run/request budget shrinks.
    run_budget = effective_dispatch_budget(
        pf.budget, pf.effective_environment_constraints
    )
    record: dict[str, Any] = {
        "schema_id": "cdb.agent_dispatch_run.v1",
        "schema_version": "1.0.0",
        "run_id": rid,
        "attempt": attempt_n,
        "previous_run_id": previous_run_id,
        "revision": 0,
        "state": "PLANNED",
        "contract_id": pf.contract["contract_id"],
        "contract_digest": pf.contract_digest,
        "delivery_issue": (pf.contract.get("issue") or {}).get("number"),
        "route": {
            "routing_decision": pf.route.get("routing_decision") if pf.route else None,
            "target_pr": pf.route.get("target_pr") if pf.route else None,
            "target_branch": pf.route.get("target_branch") if pf.route else None,
            "lane": pf.route.get("lane") if pf.route else None,
            "batch_key": pf.route.get("batch_key") if pf.route else None,
        },
        "expected_delivery": expected_delivery,
        "agent_id": agent_id,
        "provider_id": pf.provider_id,
        "provider_run_id": None,
        "budget": run_budget,
        "usage": {"iterations": 0, "tool_calls": 0},
        "lifecycle_events": [],
        "terminal_reason": None,
        "terminal_code": None,
        "idempotency_key": idem,
        "created_at": at,
        "updated_at": at,
        "scenario": scenario,
        "delivery_receipt": None,
        "result_refs": {},
    }
    # Never persist prompt_text on the run record.
    _persist_evidence_bindings(record, pf)
    store.create(record)

    # PLANNED -> ROUTED -> CONTRACTED (validation_success maps VALIDATED)
    _apply_state(
        record,
        "ROUTED",
        event_name="route_bound",
        clock=clock,
        detail={"routing_decision": record["route"]["routing_decision"]},
    )
    record["revision"] = 1
    store.update_cas(rid, 0, record)

    _apply_state(
        record,
        "CONTRACTED",
        event_name="validation_success",
        clock=clock,
        detail={"mapped_from_issue_label": "VALIDATED"},
    )
    record["revision"] = 2
    store.update_cas(rid, 1, record)

    scope = pf.contract.get("execution_scope") or {}
    request = ProviderRequest(
        run_id=rid,
        contract_id=pf.contract["contract_id"],
        contract_digest=pf.contract_digest,
        agent_id=agent_id,
        scenario=scenario,
        delivery_receipt=None,
        delivery_expectations=deepcopy(expected_delivery),
        idempotency_key=idem,
        provider_id=pf.provider_id,
        provider_profile=deepcopy(pf.provider_profile or {}),
        route=deepcopy(pf.route or {}),
        effective_permissions=deepcopy(pf.agent.get("effective_permissions") or {}),
        allowed_paths=list(
            (pf.effective_environment_constraints or {}).get("allowed_paths")
            or scope.get("allowed_paths")
            or []
        ),
        allowed_command_classes=list(
            (pf.effective_environment_constraints or {}).get("allowed_command_classes")
            or scope.get("allowed_commands_or_command_classes")
            or []
        ),
        budget=deepcopy(run_budget),
        prompt_ref=pf.prompt_ref,
        prompt_digest=pf.prompt_digest,
        prompt_text=pf.prompt_text,
        secret_references=list(
            ((pf.contract.get("environment") or {}).get("secret_references") or [])
        ),
        environment_profile=deepcopy(pf.environment_profile or {}),
        environment_profile_digest=pf.environment_profile_digest,
        provider_environment_config_ref=pf.provider_environment_config_ref,
        provider_environment_config_digest=pf.provider_environment_config_digest,
        environment_preflight_verdict=pf.environment_preflight_verdict,
        effective_environment_constraints=deepcopy(
            pf.effective_environment_constraints or {}
        ),
    )
    # Never persist prompt_text on the run record.
    record["prompt_ref"] = pf.prompt_ref
    record["prompt_digest"] = pf.prompt_digest
    try:
        result = active_provider.dispatch(request)
    except DispatchError as exc:
        _apply_state(
            record,
            "BLOCKED",
            event_name="provider_dispatch_blocked",
            clock=clock,
            detail={"code": exc.code, "reason": exc.message},
        )
        record["revision"] = 3
        store.update_cas(rid, 2, record)
        return {"dry_run": False, "applied": True, "plan": None, "run": record}

    if result.normalized_status == "UNKNOWN":
        _persist_evidence_bindings(record, pf, result)
        _apply_state(
            record,
            "BLOCKED",
            event_name="provider_status_unknown",
            clock=clock,
            detail={
                "code": "DISPATCH_PROVIDER_STATUS_UNKNOWN",
                "reason": "unknown status",
            },
        )
        record["provider_run_id"] = result.provider_run_id
        record["revision"] = 3
        store.update_cas(rid, 2, record)
        return {"dry_run": False, "applied": True, "plan": None, "run": record}

    if result.normalized_status == "FAILED":
        _persist_evidence_bindings(record, pf, result)
        record["provider_run_id"] = result.provider_run_id
        _apply_state(
            record,
            "DISPATCHED",
            event_name="provider_dispatched",
            clock=clock,
            detail={"provider_run_id": result.provider_run_id},
        )
        record["revision"] = 3
        store.update_cas(rid, 2, record)
        _apply_state(
            record,
            "FAILED",
            event_name="provider_failed",
            clock=clock,
            detail={"code": result.error_code, "reason": result.error_category},
        )
        record["revision"] = 4
        store.update_cas(rid, 3, record)
        return {"dry_run": False, "applied": True, "plan": None, "run": record}

    record["provider_run_id"] = result.provider_run_id
    _persist_evidence_bindings(record, pf, result)
    _apply_state(
        record,
        "DISPATCHED",
        event_name="provider_dispatched",
        clock=clock,
        detail={"provider_run_id": result.provider_run_id},
    )
    record["revision"] = 3
    store.update_cas(rid, 2, record)
    return {"dry_run": False, "applied": True, "plan": None, "run": record}


def watch_run(
    run_id: str,
    store: RunStore,
    *,
    clock: Clock | None = None,
    provider: Provider | None = None,
    auto_advance_success: bool = True,
) -> dict[str, Any]:
    clock = clock or SystemClock()
    record = store.get(run_id)
    if record is None:
        raise DispatchError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
    if record["state"] in TERMINAL_STATES:
        return record

    if record["state"] not in {"DISPATCHED", "RUNNING"}:
        raise DispatchError(
            "DISPATCH_WATCH_INVALID_STATE",
            f"cannot watch run in state {record['state']!r}",
        )

    provider_run_id = record.get("provider_run_id")
    if not provider_run_id:
        raise DispatchError(
            "DISPATCH_PROVIDER_RUN_MISSING",
            "run has no provider_run_id",
        )
    if record.get("provider_id") != "mock" and provider is None:
        raise DispatchError(
            "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
            "watch for Cursor runs requires an injected provider instance",
        )

    active = provider or get_provider("mock")
    # Reuse same mock instance if caller did not inject — for JsonFile CLI,
    # MockProvider is ephemeral; store scenario on record and rebuild.
    if provider is None and isinstance(active, MockProvider):
        # Seed internal state from record for CLI watch without shared memory.
        if provider_run_id not in active._runs:  # noqa: SLF001 - test/CLI bridge
            seeded = ProviderRequest(
                run_id=run_id,
                contract_id=record["contract_id"],
                contract_digest=record["contract_digest"],
                agent_id=record["agent_id"],
                scenario=record.get("scenario") or "success",
                delivery_receipt=None,
                delivery_expectations=deepcopy(
                    record.get("expected_delivery")
                    or {
                        "target_pr": record["route"].get("target_pr"),
                        "target_branch": record["route"].get("target_branch"),
                        "expected_status": "DONE_SLICE_ADDED_TO_BATCH_PR",
                        "routing_decision": record["route"].get("routing_decision"),
                    }
                ),
                route=deepcopy(record.get("route") or {}),
            )
            active.dispatch(seeded)
            internal = active._runs[provider_run_id]  # noqa: SLF001
            # Restore progress so successive CLI processes can advance.
            ticks = int(record.get("provider_watch_ticks") or 0)
            internal.watch_ticks = ticks
            if record["state"] == "RUNNING":
                internal.status = "RUNNING"
            elif record["state"] == "DISPATCHED":
                internal.status = "QUEUED"

    if _wall_time_exceeded(record, record.get("budget") or {}, clock):
        return _handle_timeout(record, store, active, clock)

    result = active.watch(provider_run_id)
    rev = int(record["revision"])
    record = store.get(run_id)
    assert record is not None
    record["usage"] = dict(result.usage)
    if result.result_refs:
        record["result_refs"] = sanitize_result_refs(result.result_refs)
    if (
        isinstance(active, MockProvider) and provider_run_id in active._runs
    ):  # noqa: SLF001
        record["provider_watch_ticks"] = active._runs[
            provider_run_id
        ].watch_ticks  # noqa: SLF001

    exceeded = _budget_exceeded(record.get("budget") or {}, record["usage"])
    if exceeded:
        if record["state"] == "DISPATCHED":
            _apply_state(
                record,
                "RUNNING",
                event_name="provider_running",
                clock=clock,
            )
            record["revision"] = rev + 1
            store.update_cas(run_id, rev, record)
            rev = rev + 1
            record = store.get(run_id)
            assert record is not None
            record["usage"] = dict(result.usage)
        _apply_state(
            record,
            "BLOCKED",
            event_name="budget_exceeded",
            clock=clock,
            detail={"code": "DISPATCH_BUDGET_EXCEEDED", "reason": exceeded},
        )
        record["revision"] = rev + 1
        return store.update_cas(run_id, rev, record)

    if result.normalized_status == "UNKNOWN":
        if record["state"] == "DISPATCHED":
            _apply_state(
                record,
                "RUNNING",
                event_name="provider_running",
                clock=clock,
            )
            record["revision"] = rev + 1
            store.update_cas(run_id, rev, record)
            rev = rev + 1
            record = store.get(run_id)
            assert record is not None
        _apply_state(
            record,
            "BLOCKED",
            event_name="provider_status_unknown",
            clock=clock,
            detail={"code": "DISPATCH_PROVIDER_STATUS_UNKNOWN", "reason": "unknown"},
        )
        record["revision"] = rev + 1
        return store.update_cas(run_id, rev, record)

    if result.normalized_status == "FAILED":
        if record["state"] == "DISPATCHED":
            _apply_state(
                record,
                "FAILED",
                event_name="provider_failed",
                clock=clock,
                detail={"code": result.error_code, "reason": result.error_category},
            )
            record["revision"] = rev + 1
            return store.update_cas(run_id, rev, record)
        _apply_state(
            record,
            "FAILED",
            event_name="provider_failed",
            clock=clock,
            detail={"code": result.error_code, "reason": result.error_category},
        )
        record["revision"] = rev + 1
        return store.update_cas(run_id, rev, record)

    if result.normalized_status == "CANCELLED":
        _apply_state(
            record,
            "CANCELLED",
            event_name="provider_cancelled",
            clock=clock,
            detail={"code": "CANCELLED", "reason": "provider_cancelled"},
        )
        record["revision"] = rev + 1
        return store.update_cas(run_id, rev, record)

    if result.normalized_status in {"QUEUED", "RUNNING"}:
        if record["state"] == "DISPATCHED" and result.normalized_status == "RUNNING":
            _apply_state(
                record,
                "RUNNING",
                event_name="provider_running",
                clock=clock,
            )
            record["revision"] = rev + 1
            return store.update_cas(run_id, rev, record)
        record["updated_at"] = _iso(clock)
        record["revision"] = rev + 1
        return store.update_cas(run_id, rev, record)

    if result.normalized_status == "SUCCEEDED":
        if record["state"] == "DISPATCHED":
            _apply_state(
                record,
                "RUNNING",
                event_name="provider_running",
                clock=clock,
            )
            record["revision"] = rev + 1
            store.update_cas(run_id, rev, record)
            rev = rev + 1
            record = store.get(run_id)
            assert record is not None

        receipt = result.delivery_receipt or record.get("delivery_receipt")
        expected = record.get("expected_delivery") or {}
        # Reconstruct contract surface from sealed expectations — never from
        # the provider-reported delivery_status (avoids tautological checks).
        contract_surface = {
            "route": {
                **(record.get("route") or {}),
                "routing_decision": expected.get("routing_decision")
                or (record.get("route") or {}).get("routing_decision"),
                "target_pr": expected.get("target_pr"),
                "target_branch": expected.get("target_branch"),
            },
            "execution_scope": {
                "delivery_target": {
                    "target_pr": expected.get("target_pr"),
                    "target_branch": expected.get("target_branch"),
                    "expected_status": expected.get("expected_status")
                    or "DONE_SLICE_ADDED_TO_BATCH_PR",
                }
            },
        }
        try:
            _validate_delivery_receipt(contract_surface, receipt)
        except DispatchError as exc:
            _apply_state(
                record,
                "BLOCKED",
                event_name="delivery_receipt_invalid",
                clock=clock,
                detail={"code": exc.code, "reason": exc.message},
            )
            record["revision"] = rev + 1
            return store.update_cas(run_id, rev, record)

        record["delivery_receipt"] = deepcopy(receipt)
        _merge_observed_create_targets(record, receipt)
        if auto_advance_success:
            _apply_state(
                record,
                "DELIVERED",
                event_name="delivery_accepted",
                clock=clock,
                detail={"receipt_commit": receipt.get("commit")},
            )
            record["revision"] = rev + 1
            store.update_cas(run_id, rev, record)
            rev = rev + 1
            record = store.get(run_id)
            assert record is not None
            _apply_state(
                record,
                "PASS",
                event_name="delivery_pass",
                clock=clock,
                detail={
                    "code": "PASS",
                    "reason": "delivery_goals_met",
                    "not_final_ci": True,
                    "not_merge_authority": True,
                },
            )
            # Optional handoff event (not a lifecycle state).
            seq = len(record["lifecycle_events"]) + 1
            _append_event(
                record,
                _event(
                    seq,
                    "handed_off",
                    from_state="PASS",
                    to_state="PASS",
                    at=_iso(clock),
                    detail={"mapped_from_issue_label": "HANDED_OFF"},
                ),
            )
            record["revision"] = rev + 1
            return store.update_cas(run_id, rev, record)
        record["revision"] = rev + 1
        return store.update_cas(run_id, rev, record)

    raise DispatchError(
        "DISPATCH_PROVIDER_STATUS_UNKNOWN",
        f"unhandled provider status: {result.normalized_status!r}",
    )


def _handle_timeout(
    record: dict[str, Any],
    store: RunStore,
    provider: Provider,
    clock: Clock,
) -> dict[str, Any]:
    run_id = record["run_id"]
    rev = int(record["revision"])
    provider_run_id = record["provider_run_id"]
    result = provider.cancel(provider_run_id, "TIMEOUT")
    if result.cancel_confirmed is True or result.normalized_status == "CANCELLED":
        _apply_state(
            record,
            "CANCELLED",
            event_name="timeout_cancel_confirmed",
            clock=clock,
            detail={"code": "TIMEOUT", "reason": "TIMEOUT"},
        )
    else:
        _apply_state(
            record,
            "BLOCKED",
            event_name="timeout_cancel_unconfirmed",
            clock=clock,
            detail={
                "code": "PROVIDER_CANCEL_UNCONFIRMED",
                "reason": "timeout cancel not confirmed",
            },
        )
    record["revision"] = rev + 1
    return store.update_cas(run_id, rev, record)


def cancel_run(
    run_id: str,
    store: RunStore,
    reason: str,
    *,
    clock: Clock | None = None,
    provider: Provider | None = None,
) -> dict[str, Any]:
    clock = clock or SystemClock()
    record = store.get(run_id)
    if record is None:
        raise DispatchError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
    if record["state"] in TERMINAL_STATES:
        raise DispatchError(
            "DISPATCH_TERMINAL_TRANSITION",
            f"cannot cancel terminal run in state {record['state']!r}",
        )
    if record.get("provider_id") not in {None, "mock"} and provider is None:
        raise DispatchError(
            "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
            "cancel for Cursor runs requires an injected provider instance",
        )

    rev = int(record["revision"])
    if record.get("provider_run_id"):
        active = provider or get_provider("mock")
        if provider is None and isinstance(active, MockProvider):
            if record["provider_run_id"] not in active._runs:  # noqa: SLF001
                active.dispatch(
                    ProviderRequest(
                        run_id=run_id,
                        contract_id=record["contract_id"],
                        contract_digest=record["contract_digest"] or "",
                        agent_id=record["agent_id"],
                        scenario=record.get("scenario") or "success",
                    )
                )
        result = active.cancel(record["provider_run_id"], reason)
        if result.cancel_confirmed is False:
            _apply_state(
                record,
                "BLOCKED",
                event_name="cancel_unconfirmed",
                clock=clock,
                detail={
                    "code": "PROVIDER_CANCEL_UNCONFIRMED",
                    "reason": reason,
                },
            )
            record["revision"] = rev + 1
            return store.update_cas(run_id, rev, record)

    # Cancel from non-provider states or confirmed cancel.
    target = "CANCELLED"
    if record["state"] in {"PLANNED", "ROUTED", "CONTRACTED"}:
        pass
    _apply_state(
        record,
        target,
        event_name="cancel_requested",
        clock=clock,
        detail={"code": "CANCELLED", "reason": reason},
    )
    record["revision"] = rev + 1
    return store.update_cas(run_id, rev, record)


def retry_run(
    previous_run_id: str,
    contract: dict[str, Any],
    registry_document: dict[str, Any],
    store: RunStore,
    reason: str,
    *,
    agent_id: str | None = None,
    dry_run: bool = True,
    allow_mock_dispatch: bool = False,
    scenario: str = "success",
    clock: Clock | None = None,
    provider: Provider | None = None,
) -> dict[str, Any]:
    clock = clock or SystemClock()
    previous = store.get(previous_run_id)
    if previous is None:
        raise DispatchError(
            "DISPATCH_RUN_NOT_FOUND",
            f"unknown previous_run_id: {previous_run_id}",
        )
    if previous["state"] not in TERMINAL_STATES:
        raise DispatchError(
            "DISPATCH_RETRY_NOT_TERMINAL",
            "retry requires a terminal previous run",
        )

    # Governance/integrity blockers must not be blindly retried with same contract.
    blocked_codes = {
        "CONTRACT_HASH_MISMATCH",
        "CONTRACT_UNKNOWN_FIELD",
        "CONTRACT_SCHEMA_INVALID",
        "HOLD_PR_LOCK_CONFLICT",
        "HOLD_NO_SAFE_ROUTE",
        "DISPATCH_FORBIDDEN_PERMISSION",
        "DISPATCH_PERMISSION_CEILING",
    }
    if previous.get("terminal_code") in blocked_codes:
        # Re-run preflight; if still failing with same code, refuse.
        agent = agent_id or previous["agent_id"]
        pf = preflight(contract, registry_document, agent, execute=not dry_run)
        if not pf.ok and pf.code == previous.get("terminal_code"):
            raise DispatchError(
                "DISPATCH_RETRY_BLOCKER_UNCHANGED",
                f"refusing retry of unchanged blocker {pf.code}",
            )

    agent = agent_id or previous["agent_id"]
    # Snapshot previous so terminal record remains immutable.
    prev_snapshot = deepcopy(previous)
    result = dispatch_run(
        contract,
        registry_document,
        agent,
        None if dry_run else store,
        dry_run=dry_run,
        allow_mock_dispatch=allow_mock_dispatch,
        scenario=scenario,
        clock=clock,
        provider=provider,
        previous_run_id=previous_run_id,
        attempt=int(previous.get("attempt") or 1) + 1,
    )
    result["previous_run_unchanged"] = store.get(previous_run_id) == prev_snapshot
    result["retry_reason"] = reason
    return result


def evidence_snapshot(run_id: str, store: RunStore) -> dict[str, Any]:
    record = store.get(run_id)
    if record is None:
        raise DispatchError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
    # Read-only; emit snapshot event only in returned payload, not mutating store.
    events = deepcopy(record.get("lifecycle_events") or [])
    snapshot_event = {
        "seq": len(events) + 1,
        "name": "evidence_collected",
        "from_state": record["state"],
        "to_state": record["state"],
        "at": record.get("updated_at"),
        "detail": {"mapped_from_issue_label": "EVIDENCE_COLLECTED"},
    }
    return {
        "schema_id": "cdb.agent_dispatch_evidence_snapshot.v1",
        "output_type": "dispatcher_lifecycle_snapshot",
        "run_id": record["run_id"],
        "attempt": record.get("attempt"),
        "state": record["state"],
        "contract_id": record.get("contract_id"),
        "contract_digest": record.get("contract_digest"),
        "route_binding": deepcopy(record.get("route") or {}),
        "provider_id": record.get("provider_id"),
        "provider_run_id": record.get("provider_run_id"),
        "sanitized_event_sequence": events + [snapshot_event],
        "budget_usage_summary": {
            "budget": deepcopy(record.get("budget") or {}),
            "usage": deepcopy(record.get("usage") or {}),
        },
        "terminal_reason": record.get("terminal_reason"),
        "terminal_code": record.get("terminal_code"),
        "limitations": [
            "not_agent_run_evidence_bundle_v1",
            "not_final_ci",
            "not_cdb_local_ci",
            "not_completeness_review",
            "not_merge_authority",
        ],
        "explicit_negative_claims": [
            "not_agent_run_evidence_bundle_v1",
            "not_final_ci",
            "not_cdb_local_ci",
            "not_completeness_review",
            "not_merge_authority",
        ],
    }
