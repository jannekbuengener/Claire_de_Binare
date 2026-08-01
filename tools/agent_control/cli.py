"""CLI front door for agent registry + governed dispatcher.

Examples:
  python -m tools.agent_control registry validate --config <PATH>
  python -m tools.agent_control dispatch --contract <PATH> --registry <PATH> \\
      --agent-id <ID> --state <PATH> --dry-run
  python -m tools.agent_control watch --run-id <ID> --state <PATH>
  python -m tools.agent_control cancel --run-id <ID> --state <PATH> --reason <TEXT>
  python -m tools.agent_control retry --previous-run-id <ID> --contract <PATH> --reason <TEXT>
  python -m tools.agent_control evidence --run-id <ID> --state <PATH>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.agent_control.dispatch import (
    cancel_run,
    dispatch_run,
    evidence_snapshot,
    retry_run,
    watch_run,
)
from tools.agent_control.errors import AgentControlError, DispatchError, RegistryError
from tools.agent_control.load import (
    dump_json,
    load_observed_state,
    load_registry_document,
)
from tools.agent_control.normalize import normalize_registry, registry_fingerprint
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT
from tools.agent_control.reconcile import backend_from_state, build_plan, reconcile
from tools.agent_control.run_store import JsonFileRunStore
from tools.agent_control.validate import validate_registry


def _print_json(payload: Any) -> None:
    sys.stdout.write(dump_json(payload))


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cmd_registry_validate(args: argparse.Namespace) -> int:
    try:
        document = load_registry_document(Path(args.config))
        validate_registry(document)
        fingerprint = registry_fingerprint(document)
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    print(f"VALID schema_id=cdb.agent_registry.v1 fingerprint={fingerprint}")
    return 0


def cmd_registry_normalize(args: argparse.Namespace) -> int:
    try:
        document = load_registry_document(Path(args.config))
        normalized = normalize_registry(document)
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(normalized), encoding="utf-8")
    else:
        _print_json(normalized)
    return 0


def cmd_registry_plan(args: argparse.Namespace) -> int:
    try:
        document = load_registry_document(Path(args.config))
        state = load_observed_state(Path(args.state))
        plan = build_plan(document, state, mode="plan")
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(plan), encoding="utf-8")
    else:
        _print_json(plan)
    return 1 if plan.get("blocked") else 0


def cmd_registry_reconcile(args: argparse.Namespace) -> int:
    dry_run = not args.apply
    if args.apply and not args.allow_mock_apply:
        print(
            "INVALID REGISTRY_LIVE_MUTATION_FORBIDDEN: "
            "reconcile defaults to dry-run; pass --apply --allow-mock-apply "
            "only against a mock state file (no live provider)",
            file=sys.stderr,
        )
        return 1
    try:
        document = load_registry_document(Path(args.config))
        if args.state:
            state = load_observed_state(Path(args.state))
        else:
            state = {
                "schema_id": "cdb.agent_registry.observed.v1",
                "agents": {},
            }
        backend_name = "mock" if args.apply else "file"
        backend = backend_from_state(state, backend_name=backend_name)
        result = reconcile(document, backend, dry_run=dry_run)
    except RegistryError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(result), encoding="utf-8")
    else:
        _print_json(result)
    plan = result["plan"]
    if plan.get("blocked"):
        return 1
    return 0


def cmd_dispatch(args: argparse.Namespace) -> int:
    dry_run = not args.execute
    try:
        contract = _load_json(Path(args.contract))
        registry = load_registry_document(Path(args.registry))
        if dry_run:
            result = dispatch_run(
                contract,
                registry,
                args.agent_id,
                store=None,
                dry_run=True,
                scenario=args.scenario,
            )
        else:
            if not args.state:
                raise DispatchError(
                    "DISPATCH_STATE_REQUIRED",
                    "execute requires --state <PATH>",
                )
            if not args.allow_mock_dispatch:
                raise DispatchError(
                    "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                    "execute requires --allow-mock-dispatch",
                )
            store = JsonFileRunStore(Path(args.state))
            result = dispatch_run(
                contract,
                registry,
                args.agent_id,
                store,
                dry_run=False,
                allow_mock_dispatch=True,
                scenario=args.scenario,
            )
    except (AgentControlError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "DISPATCH_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(dump_json(result), encoding="utf-8")
    else:
        _print_json(result)
    if result.get("dry_run"):
        return 0 if result["plan"].get("preflight_ok") else 1
    run = result.get("run") or {}
    return 0 if run.get("state") not in {"HOLD", "BLOCKED", "FAILED"} else 1


def cmd_watch(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = watch_run(args.run_id, store)
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(record)
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        record = cancel_run(args.run_id, store, args.reason)
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(record)
    return 0


def cmd_retry(args: argparse.Namespace) -> int:
    dry_run = not args.execute
    try:
        contract = _load_json(Path(args.contract))
        registry = load_registry_document(Path(args.registry))
        if not args.state:
            raise DispatchError("DISPATCH_STATE_REQUIRED", "retry requires --state")
        store = JsonFileRunStore(Path(args.state))
        result = retry_run(
            args.previous_run_id,
            contract,
            registry,
            store,
            args.reason,
            agent_id=args.agent_id,
            dry_run=dry_run,
            allow_mock_dispatch=bool(args.execute and args.allow_mock_dispatch),
            scenario=args.scenario,
        )
    except (AgentControlError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "DISPATCH_ERROR")
        message = getattr(exc, "message", str(exc))
        print(f"INVALID {code}: {message}", file=sys.stderr)
        return 1
    _print_json(result)
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    try:
        store = JsonFileRunStore(Path(args.state))
        snapshot = evidence_snapshot(args.run_id, store)
    except DispatchError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    _print_json(snapshot)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.agent_control",
        description="CDB Agent Control Plane CLI (registry + governed dispatcher)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    registry = sub.add_parser("registry", help="Declarative agent registry commands")
    reg_sub = registry.add_subparsers(dest="registry_command", required=True)

    p_val = reg_sub.add_parser("validate", help="Validate registry desired state")
    p_val.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_ROOT),
        help="Registry file or config/agent-control root",
    )
    p_val.set_defaults(func=cmd_registry_validate)

    p_norm = reg_sub.add_parser("normalize", help="Emit normalized registry JSON")
    p_norm.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_norm.add_argument("--output")
    p_norm.set_defaults(func=cmd_registry_normalize)

    p_plan = reg_sub.add_parser(
        "plan",
        help="Build deterministic reconcile plan (desired vs observed)",
    )
    p_plan.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_plan.add_argument("--state", required=True, help="Observed state JSON/YAML")
    p_plan.add_argument("--output")
    p_plan.set_defaults(func=cmd_registry_plan)

    p_rec = reg_sub.add_parser(
        "reconcile",
        help="Reconcile desired vs observed (dry-run default; no live mutation)",
    )
    p_rec.add_argument("--config", default=str(DEFAULT_CONFIG_ROOT))
    p_rec.add_argument(
        "--state",
        help="Observed state JSON/YAML (default: empty observed set)",
    )
    p_rec.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Plan only (default)",
    )
    p_rec.add_argument(
        "--apply",
        action="store_true",
        help="Simulate apply via MockBackend only (requires --allow-mock-apply)",
    )
    p_rec.add_argument(
        "--allow-mock-apply",
        action="store_true",
        help="Acknowledge mock-only apply (still no live provider calls)",
    )
    p_rec.add_argument("--output")
    p_rec.set_defaults(func=cmd_registry_reconcile)

    p_dispatch = sub.add_parser(
        "dispatch",
        help="Governed dispatch (dry-run default; mock execute opt-in)",
    )
    p_dispatch.add_argument("--contract", required=True)
    p_dispatch.add_argument(
        "--registry",
        default=str(DEFAULT_CONFIG_ROOT),
        help="Registry file or config/agent-control root",
    )
    p_dispatch.add_argument("--agent-id", required=True)
    p_dispatch.add_argument(
        "--state",
        help="JSON run-store path (required for --execute)",
    )
    p_dispatch.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preflight + plan only (default)",
    )
    p_dispatch.add_argument(
        "--execute",
        action="store_true",
        help="Execute mock dispatch (requires --allow-mock-dispatch)",
    )
    p_dispatch.add_argument(
        "--allow-mock-dispatch",
        action="store_true",
        help="Acknowledge mock-only provider execution",
    )
    p_dispatch.add_argument(
        "--scenario",
        default="success",
        help="MockProvider scenario (tests/CLI)",
    )
    p_dispatch.add_argument("--output")
    p_dispatch.set_defaults(func=cmd_dispatch)

    p_watch = sub.add_parser("watch", help="Watch/advance a mock run")
    p_watch.add_argument("--run-id", required=True)
    p_watch.add_argument("--state", required=True)
    p_watch.set_defaults(func=cmd_watch)

    p_cancel = sub.add_parser("cancel", help="Cancel a non-terminal mock run")
    p_cancel.add_argument("--run-id", required=True)
    p_cancel.add_argument("--state", required=True)
    p_cancel.add_argument("--reason", required=True)
    p_cancel.set_defaults(func=cmd_cancel)

    p_retry = sub.add_parser("retry", help="Explicit retry as a new attempt")
    p_retry.add_argument("--previous-run-id", required=True)
    p_retry.add_argument("--contract", required=True)
    p_retry.add_argument("--reason", required=True)
    p_retry.add_argument("--registry", default=str(DEFAULT_CONFIG_ROOT))
    p_retry.add_argument("--agent-id")
    p_retry.add_argument("--state", required=True)
    p_retry.add_argument("--dry-run", action="store_true", default=True)
    p_retry.add_argument("--execute", action="store_true")
    p_retry.add_argument("--allow-mock-dispatch", action="store_true")
    p_retry.add_argument("--scenario", default="success")
    p_retry.set_defaults(func=cmd_retry)

    p_evidence = sub.add_parser(
        "evidence",
        help="Read-only dispatcher lifecycle snapshot (not #4256 evidence bundle)",
    )
    p_evidence.add_argument("--run-id", required=True)
    p_evidence.add_argument("--state", required=True)
    p_evidence.set_defaults(func=cmd_evidence)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
