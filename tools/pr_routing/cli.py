"""Command-line interface for the read-only CDB PR router."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from core.utils.clock import utcnow
from tools.pr_routing.engine import (
    CandidatePullRequest,
    LockState,
    evaluate_merge_triggers,
    parse_batch_pr_body,
    route_issue,
)
from tools.pr_routing.github_cli import GhReadOnlyInventory, GitHubInventoryError
from tools.pr_routing.policy import load_policy

SUCCESS = 0
HOLD = 1
USAGE = 2


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object is not JSON serializable: {type(value).__name__}")


def _emit(payload: object) -> None:
    print(
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            default=_json_default,
        )
    )


def cmd_validate_policy(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    _emit(
        {
            "status": "PASS",
            "schema_version": policy.schema_version,
            "policy_id": policy.policy_id,
            "lanes": sorted(policy.lanes),
        }
    )
    return SUCCESS


def cmd_validate_pr_body(args: argparse.Namespace) -> int:
    metadata = parse_batch_pr_body(Path(args.body_file).read_text(encoding="utf-8"))
    _emit({"status": "PASS", "metadata": asdict(metadata)})
    return SUCCESS


def cmd_route(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    inventory = GhReadOnlyInventory(repository=args.repository)
    try:
        issue, issue_comments = inventory.issue(args.issue, current_agent=args.agent)
        candidates = inventory.candidates(
            policy=policy,
            issue_comments=issue_comments,
            current_agent=args.agent,
            issue_number=args.issue,
        )
    except GitHubInventoryError as exc:
        _emit(
            {
                "issue_number": args.issue,
                "routing_decision": "HOLD_NO_SAFE_ROUTE",
                "policy_id": policy.policy_id,
                "collection_errors": [str(exc)],
                "reason_codes": ["INCOMPLETE_GITHUB_INVENTORY"],
            }
        )
        return HOLD
    result = route_issue(policy, issue, candidates)
    payload = asdict(result)
    payload["observed_at"] = utcnow().replace(tzinfo=timezone.utc).isoformat()
    payload["evidence_sources"] = ["gh issue view", "gh pr list", "gh pr view"]
    payload["collection_errors"] = []
    _emit(payload)
    return HOLD if result.routing_decision.value.startswith("HOLD_") else SUCCESS


def _candidate_from_json(data: dict[str, Any]) -> CandidatePullRequest:
    contents = data.get("file_contents")
    paths = data.get("changed_file_paths")
    return CandidatePullRequest(
        number=int(data["number"]),
        title=str(data.get("title") or ""),
        head_branch=str(data.get("head_branch") or ""),
        base_branch=str(data.get("base_branch") or "main"),
        is_draft=bool(data.get("is_draft", True)),
        body=str(data["body"]),
        lock_state=LockState(str(data.get("lock_state") or "UNLOCKED")),
        created_at=datetime.fromisoformat(
            str(data["created_at"]).replace("Z", "+00:00")
        ),
        changed_files=int(data.get("changed_files") or 0),
        additions=int(data.get("additions") or 0),
        deletions=int(data.get("deletions") or 0),
        merge_mode=str(data.get("merge_mode") or "batch"),
        changed_file_paths=(
            tuple(str(item) for item in paths) if isinstance(paths, list) else None
        ),
        file_contents=(
            {str(key): str(value) for key, value in contents.items()}
            if isinstance(contents, dict)
            else None
        ),
        inventory_complete=bool(data.get("inventory_complete", True)),
        head_ref_oid=(str(data["head_ref_oid"]) if data.get("head_ref_oid") else None),
    )


def cmd_evaluate_trigger(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    data = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    candidate = _candidate_from_json(data)
    result = evaluate_merge_triggers(
        policy,
        candidate,
        observed_at=datetime.fromisoformat(args.observed_at.replace("Z", "+00:00")),
        explicit_operator_go=args.explicit_operator_go,
        dependency_blocker=args.dependency_blocker,
        security_or_safety=args.security_or_safety,
    )
    _emit(asdict(result))
    return SUCCESS


def cmd_merge_readiness(args: argparse.Namespace) -> int:
    metadata = parse_batch_pr_body(Path(args.body_file).read_text(encoding="utf-8"))
    ready = metadata.steward_state in {"merge_candidate", "frozen"} and all(
        row.status == "SLICE_DELIVERED" for row in metadata.ledger.values()
    )
    _emit(
        {
            "status": (
                "BATCH_PR_METADATA_READY_FOR_FINAL_VALIDATION"
                if ready
                else "HOLD_NOT_READY"
            ),
            "policy_id": metadata.policy_id,
            "steward_state": metadata.steward_state,
            "final_head_validation_required": True,
            "cdb_local_ci_exact_head_required": True,
        }
    )
    return SUCCESS if ready else HOLD


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.pr_routing")
    parser.add_argument("--policy", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    validate_policy = sub.add_parser("validate-policy")
    validate_policy.set_defaults(func=cmd_validate_policy)

    validate_body = sub.add_parser("validate-pr-body")
    validate_body.add_argument("--body-file", required=True)
    validate_body.set_defaults(func=cmd_validate_pr_body)

    route = sub.add_parser("route")
    route.add_argument("--issue", required=True, type=int)
    route.add_argument(
        "--repository",
        default="jannekbuengener/Claire_de_Binare",
    )
    route.add_argument("--agent", default="Codex")
    route.set_defaults(func=cmd_route)

    trigger = sub.add_parser("evaluate-trigger")
    trigger.add_argument("--snapshot", required=True)
    trigger.add_argument("--observed-at", required=True)
    trigger.add_argument("--explicit-operator-go", action="store_true")
    trigger.add_argument("--dependency-blocker", action="store_true")
    trigger.add_argument("--security-or-safety", action="store_true")
    trigger.set_defaults(func=cmd_evaluate_trigger)

    readiness = sub.add_parser("merge-readiness")
    readiness.add_argument("--body-file", required=True)
    readiness.set_defaults(func=cmd_merge_readiness)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _emit({"status": "HOLD_NO_SAFE_ROUTE", "error": str(exc)})
        return HOLD
