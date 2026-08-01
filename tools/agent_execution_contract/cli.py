"""CLI front door for cdb.agent_execution.v1 validation and handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.agent_execution_contract.attenuation import attenuate_contract
from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.handoff import build_contract_from_router_result
from tools.agent_execution_contract.hashing import attach_digest, compute_digest
from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_execution_contract.validate import (
    validate_contract,
    validate_contract_file,
)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        contract = validate_contract_file(Path(args.contract))
    except ContractValidationError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"INVALID CONTRACT_JSON: {exc}", file=sys.stderr)
        return 1
    print(
        f"VALID schema_id={contract['schema_id']} digest={contract['integrity']['digest']}"
    )
    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    payload = _load_json(Path(args.contract))
    if not isinstance(payload, dict):
        print("INVALID CONTRACT_TYPE_INVALID: root must be object", file=sys.stderr)
        return 1
    try:
        digest = compute_digest(payload)
    except ContractValidationError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    print(digest)
    return 0


def cmd_canonicalize(args: argparse.Namespace) -> int:
    payload = _load_json(Path(args.contract))
    try:
        sys.stdout.write(canonicalize(payload))
        if args.newline:
            sys.stdout.write("\n")
    except ContractValidationError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    return 0


def cmd_seal(args: argparse.Namespace) -> int:
    payload = _load_json(Path(args.contract))
    if not isinstance(payload, dict):
        print("INVALID CONTRACT_TYPE_INVALID: root must be object", file=sys.stderr)
        return 1
    try:
        sealed = attach_digest(payload)
        validate_contract(sealed)
    except ContractValidationError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(
            json.dumps(sealed, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        _print_json(sealed)
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    router_result = _load_json(Path(args.router_result))
    policy = _load_json(Path(args.policy))
    try:
        contract = build_contract_from_router_result(
            router_result,
            policy=policy,
            agent=args.agent,
            created_at=args.created_at,
            contract_id=args.contract_id,
        )
    except ContractValidationError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        _print_json(contract)
    return 0


def cmd_attenuate(args: argparse.Namespace) -> int:
    base = _load_json(Path(args.contract))
    override = _load_json(Path(args.override))
    try:
        validate_contract(base)
        reduced = attenuate_contract(base, override)
        validate_contract(reduced)
    except ContractValidationError as exc:
        print(f"INVALID {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(
            json.dumps(reduced, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        _print_json(reduced)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.agent_execution_contract",
        description="Validate and produce cdb.agent_execution.v1 contracts",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="Validate a contract file")
    p_val.add_argument("--contract", required=True, help="Path to contract JSON")
    p_val.set_defaults(func=cmd_validate)

    p_dig = sub.add_parser("digest", help="Compute digest excluding integrity.digest")
    p_dig.add_argument("--contract", required=True)
    p_dig.set_defaults(func=cmd_digest)

    p_can = sub.add_parser("canonicalize", help="Emit RFC8785 canonical JSON")
    p_can.add_argument("--contract", required=True)
    p_can.add_argument("--newline", action="store_true")
    p_can.set_defaults(func=cmd_canonicalize)

    p_seal = sub.add_parser("seal", help="Attach/recompute integrity.digest")
    p_seal.add_argument("--contract", required=True)
    p_seal.add_argument("--output")
    p_seal.set_defaults(func=cmd_seal)

    p_hand = sub.add_parser(
        "handoff",
        help="Build contract from router result + explicit policy",
    )
    p_hand.add_argument("--router-result", required=True)
    p_hand.add_argument("--policy", required=True)
    p_hand.add_argument("--agent", required=True)
    p_hand.add_argument("--created-at")
    p_hand.add_argument("--contract-id")
    p_hand.add_argument("--output")
    p_hand.set_defaults(func=cmd_handoff)

    p_att = sub.add_parser("attenuate", help="Apply provider attenuation override")
    p_att.add_argument("--contract", required=True)
    p_att.add_argument("--override", required=True)
    p_att.add_argument("--output")
    p_att.set_defaults(func=cmd_attenuate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
