"""CLI for the trusted local CI status publisher."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ci.lib.evidence import DEFAULT_FRESHNESS_HOURS, utc_now
from ci.lib.gitinfo import EXPECTED_REPOSITORY, collect_git_info
from ci.publisher import DEFAULT_STATUS_CONTEXT, PREVIEW_STATUS_CONTEXT
from ci.publisher.evidence import validate_evidence_for_publish
from ci.publisher.exceptions import (
    AuthenticationError,
    GitHubApiError,
    LedgerError,
    PublisherError,
)
from ci.publisher.github_client import GitHubStatusClient, resolve_token
from ci.publisher.ledger import (
    LedgerEntry,
    append_entry,
    assert_run_id_not_reused,
    default_ledger_path,
    load_ledger,
)
from ci.publisher.redaction import redact_mapping, redact_text

SUCCESS_EXIT = 0
FAILURE_EXIT = 1
USAGE_EXIT = 2


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[2]


def _print_json(payload: object) -> None:
    print(
        json.dumps(
            redact_mapping(payload), sort_keys=True, indent=2, ensure_ascii=False
        )
    )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--evidence-dir",
        required=True,
        help="Path to ci/artifacts/<run_id> containing manifest.json",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="Exact commit SHA to publish for (default: HEAD)",
    )
    parser.add_argument(
        "--repository",
        default=EXPECTED_REPOSITORY,
        help="owner/name (must be jannekbuengener/Claire_de_Binare)",
    )
    parser.add_argument(
        "--status-context",
        default=DEFAULT_STATUS_CONTEXT,
        help=f"GitHub status context (default {DEFAULT_STATUS_CONTEXT}; "
        f"preview {PREVIEW_STATUS_CONTEXT})",
    )
    parser.add_argument(
        "--freshness-hours",
        type=float,
        default=DEFAULT_FRESHNESS_HOURS,
        help="Maximum age of evidence ended_at_utc",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        default=0,
        help="Optional PR number; head SHA must match commit SHA",
    )
    parser.add_argument(
        "--target-url",
        default="",
        help="Optional target URL attached to the status",
    )
    parser.add_argument(
        "--ledger",
        default="",
        help="Path to published-runs ledger (default ci/artifacts/published-runs.json)",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Repository root for git binding (default: detected)",
    )


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else _repo_root_from_here()
    )
    evidence_dir = Path(args.evidence_dir).resolve()
    if args.ledger:
        ledger_path = Path(args.ledger).resolve()
    else:
        ledger_path = default_ledger_path(repo_root / "ci" / "artifacts")
    return repo_root, evidence_dir, ledger_path


def _resolve_commit_sha(args: argparse.Namespace, repo_root: Path) -> str:
    if args.commit_sha:
        return args.commit_sha.strip()
    return collect_git_info(repo_root).commit_sha


def cmd_validate(args: argparse.Namespace) -> int:
    repo_root, evidence_dir, ledger_path = _resolve_paths(args)
    commit_sha = _resolve_commit_sha(args, repo_root)
    result = validate_evidence_for_publish(
        evidence_dir,
        commit_sha=commit_sha,
        repository=args.repository,
        repo_root=repo_root,
        status_context=args.status_context,
        freshness_hours=args.freshness_hours,
        target_url=args.target_url or None,
    )
    # Anti-replay check even for validate when ledger exists.
    if result.ok:
        try:
            ledger = load_ledger(ledger_path)
            assert_run_id_not_reused(
                ledger, run_id=result.run_id, commit_sha=result.commit_sha
            )
        except LedgerError as exc:
            result = type(result)(
                ok=False,
                run_id=result.run_id,
                commit_sha=result.commit_sha,
                repository=result.repository,
                overall_status=result.overall_status,
                manifest_sha256=result.manifest_sha256,
                optional_skipped=result.optional_skipped,
                reason=str(exc),
                intended_payload=None,
            )
    _print_json({"command": "validate", **result.to_dict()})
    if not result.ok:
        print(
            f"REJECT: {redact_text(result.reason or 'validation failed')}",
            file=sys.stderr,
        )
        return FAILURE_EXIT
    return SUCCESS_EXIT


def cmd_dry_run(args: argparse.Namespace) -> int:
    repo_root, evidence_dir, ledger_path = _resolve_paths(args)
    commit_sha = _resolve_commit_sha(args, repo_root)
    result = validate_evidence_for_publish(
        evidence_dir,
        commit_sha=commit_sha,
        repository=args.repository,
        repo_root=repo_root,
        status_context=args.status_context,
        freshness_hours=args.freshness_hours,
        target_url=args.target_url or None,
    )
    write_attempted = False
    github_body = None
    if result.ok:
        try:
            ledger = load_ledger(ledger_path)
            assert_run_id_not_reused(
                ledger, run_id=result.run_id, commit_sha=result.commit_sha
            )
        except LedgerError as exc:
            print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
            _print_json(
                {
                    "command": "dry-run",
                    "ok": False,
                    "reason": str(exc),
                    "write_attempted": False,
                }
            )
            return FAILURE_EXIT
        if result.intended_payload is None:
            print("REJECT: no intended payload", file=sys.stderr)
            return FAILURE_EXIT
        # Dry-run client never writes.
        client = GitHubStatusClient(token="dry-run-token")
        github_body = client.create_commit_status(result.intended_payload, dry_run=True)
        write_attempted = any(not c.get("dry_run") for c in client.write_calls)
    _print_json(
        {
            "command": "dry-run",
            "ok": result.ok,
            "reason": result.reason,
            "validation": result.to_dict(),
            "github_payload": github_body,
            "write_attempted": write_attempted,
            "network_write": False,
        }
    )
    if not result.ok:
        print(
            f"REJECT: {redact_text(result.reason or 'validation failed')}",
            file=sys.stderr,
        )
        return FAILURE_EXIT
    return SUCCESS_EXIT


def cmd_publish(args: argparse.Namespace) -> int:
    repo_root, evidence_dir, ledger_path = _resolve_paths(args)
    commit_sha = _resolve_commit_sha(args, repo_root)
    result = validate_evidence_for_publish(
        evidence_dir,
        commit_sha=commit_sha,
        repository=args.repository,
        repo_root=repo_root,
        status_context=args.status_context,
        freshness_hours=args.freshness_hours,
        target_url=args.target_url or None,
    )
    if not result.ok or result.intended_payload is None:
        print(
            f"REJECT: {redact_text(result.reason or 'validation failed')}",
            file=sys.stderr,
        )
        _print_json({"command": "publish", "ok": False, "reason": result.reason})
        return FAILURE_EXIT

    try:
        token = resolve_token()
        owner, repo = result.repository.split("/", 1)
        client = GitHubStatusClient(token=token, owner=owner, repo=repo)
        client.assert_commit_exists(commit_sha)
        if args.pr_number:
            head = client.get_pull_request_head_sha(args.pr_number)
            if head.lower() != commit_sha.lower():
                raise PublisherError(
                    f"PR #{args.pr_number} head SHA {head} does not match "
                    f"commit_sha {commit_sha}"
                )
        ledger = load_ledger(ledger_path)
        assert_run_id_not_reused(
            ledger, run_id=result.run_id, commit_sha=result.commit_sha
        )
        # Final verification immediately before write.
        client.assert_commit_exists(commit_sha)
        api_result = client.create_commit_status(result.intended_payload, dry_run=False)
        status_id = api_result.get("id")
        append_entry(
            ledger_path,
            LedgerEntry(
                run_id=result.run_id,
                commit_sha=result.commit_sha,
                repository=result.repository,
                status_context=args.status_context,
                manifest_sha256=result.manifest_sha256,
                published_at_utc=utc_now(),
                github_status_id=int(status_id) if status_id is not None else None,
                state=result.intended_payload.state,
            ),
        )
    except (AuthenticationError, GitHubApiError, LedgerError, PublisherError) as exc:
        print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
        _print_json(
            {
                "command": "publish",
                "ok": False,
                "reason": redact_text(str(exc)),
            }
        )
        return FAILURE_EXIT

    _print_json(
        {
            "command": "publish",
            "ok": True,
            "sha": commit_sha,
            "context": args.status_context,
            "state": result.intended_payload.state,
            "run_id": result.run_id,
            "github": redact_mapping(api_result),
            "optional_skipped": result.optional_skipped,
        }
    )
    return SUCCESS_EXIT


def cmd_inspect(args: argparse.Namespace) -> int:
    repo_root, _evidence_dir, _ledger = _resolve_paths(args)
    commit_sha = _resolve_commit_sha(args, repo_root)
    try:
        token = resolve_token()
        owner, repo = (args.repository or EXPECTED_REPOSITORY).split("/", 1)
        client = GitHubStatusClient(token=token, owner=owner, repo=repo)
        status = client.get_commit_status(commit_sha)
    except (AuthenticationError, GitHubApiError) as exc:
        print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
        return FAILURE_EXIT
    contexts = []
    for entry in status.get("statuses") or []:
        contexts.append(
            {
                "context": entry.get("context"),
                "state": entry.get("state"),
                "description": entry.get("description"),
                "updated_at": entry.get("updated_at"),
                "target_url": entry.get("target_url"),
            }
        )
    filtered = [
        c
        for c in contexts
        if not args.status_context or c.get("context") == args.status_context
    ]
    _print_json(
        {
            "command": "inspect",
            "sha": commit_sha,
            "state": status.get("state"),
            "statuses": filtered if args.status_context else contexts,
            "total_count": status.get("total_count"),
        }
    )
    return SUCCESS_EXIT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ci.publisher",
        description=(
            "Validate local Docker CI evidence and publish a commit-bound "
            "GitHub Commit Status (not a Required Check)."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate evidence only")
    _add_common_args(validate)
    validate.set_defaults(func=cmd_validate)

    dry = sub.add_parser("dry-run", help="Validate and print payload without write")
    _add_common_args(dry)
    dry.set_defaults(func=cmd_dry_run)

    publish = sub.add_parser("publish", help="Validate and publish Commit Status")
    _add_common_args(publish)
    publish.set_defaults(func=cmd_publish)

    inspect = sub.add_parser("inspect", help="Inspect GitHub statuses for a SHA")
    _add_common_args(inspect)
    # evidence-dir not strictly required for inspect — allow dummy.
    for action in inspect._actions:
        if action.dest == "evidence_dir":
            action.required = False
            action.default = "."
    inspect.set_defaults(func=cmd_inspect)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except PublisherError as exc:
        print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
        return FAILURE_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
