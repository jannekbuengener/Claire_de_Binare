"""CLI front door for declarative agent registry + dry-run reconciler.

Examples:
  python -m tools.agent_control registry validate --config <PATH>
  python -m tools.agent_control registry plan --config <PATH> --state <PATH>
  python -m tools.agent_control registry reconcile --config <PATH> --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.agent_control.errors import RegistryError
from tools.agent_control.load import dump_json, load_observed_state, load_registry_document
from tools.agent_control.normalize import normalize_registry, registry_fingerprint
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT
from tools.agent_control.reconcile import backend_from_state, build_plan, reconcile
from tools.agent_control.validate import validate_registry


def _print_json(payload: Any) -> None:
    sys.stdout.write(dump_json(payload))


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
        # build_plan already converts validation errors into blocked plans;
        # this catches load/parse errors before planning.
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.agent_control",
        description="CDB Agent Control Plane CLI (registry + dry-run reconciler)",
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
