"""CLI for the trusted local CI status publisher."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from ci.lib.evidence import DEFAULT_FRESHNESS_HOURS, utc_now
from ci.lib.gitinfo import EXPECTED_REPOSITORY, collect_git_info
from ci.publisher import DEFAULT_STATUS_CONTEXT, PREVIEW_STATUS_CONTEXT
from ci.publisher.app_auth import credential_summary
from ci.publisher.backends import (
    ALLOWED_BACKENDS,
    CheckRunBackend,
    build_publisher_backend,
    parse_positive_int,
    resolve_app_installation_token,
    resolve_expected_app_id,
    resolve_expected_installation_id,
)
from ci.publisher.evidence import (
    build_check_run_payload,
    validate_evidence_for_publish,
)
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
    find_exact_publication,
    load_ledger,
)
from ci.publisher.models import (
    CHECK_RUN_NAME,
    SHADOW_CHECK_RUN_NAME,
    CheckRunPayload,
    build_check_run_external_id,
)
from ci.publisher.redaction import redact_mapping, redact_text
from tools.ci.policy_gate_local import evaluate_policy_gate

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


def _latest_context_status(
    statuses: object, *, context: str
) -> dict[str, object] | None:
    if not isinstance(statuses, list):
        return None
    matching = [
        status
        for status in statuses
        if isinstance(status, dict) and status.get("context") == context
    ]
    if not matching or any(
        not (status.get("updated_at") or status.get("created_at"))
        for status in matching
    ):
        return None
    return max(
        matching,
        key=lambda status: str(
            status.get("updated_at") or status.get("created_at") or ""
        ),
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
        help=(
            "PR number; required (>0) when --status-context is "
            f"{DEFAULT_STATUS_CONTEXT}; optional for preview"
        ),
    )
    parser.add_argument(
        "--target-url",
        default="",
        help="Optional target URL attached to the status / details_url",
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
    parser.add_argument(
        "--publisher-backend",
        default="check-run",
        choices=sorted(ALLOWED_BACKENDS),
        help=(
            "Publish surface: check-run (default, App-bound required path after "
            "#4170 Phase D) or commit-status (legacy; does not satisfy BP)"
        ),
    )
    parser.add_argument(
        "--expected-app-id",
        type=int,
        default=0,
        help="Expected GitHub App ID (required for check-run; positive int)",
    )
    parser.add_argument(
        "--expected-installation-id",
        type=int,
        default=0,
        help="Expected GitHub App installation ID (required for check-run)",
    )
    parser.add_argument(
        "--check-run-name",
        default=CHECK_RUN_NAME,
        help=(
            f"Check Run name (default {CHECK_RUN_NAME}; shadow "
            f"{SHADOW_CHECK_RUN_NAME} for non-required smoke only)"
        ),
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


def _require_pr_for_required_context(args: argparse.Namespace) -> None:
    """Fail closed when publishing the required-path context without a PR."""
    if args.status_context == DEFAULT_STATUS_CONTEXT and int(args.pr_number or 0) <= 0:
        raise PublisherError(
            f"--pr-number > 0 is required when --status-context is "
            f"{DEFAULT_STATUS_CONTEXT} (local policy-gate mirror at publish time)"
        )


def _backend_name(args: argparse.Namespace) -> str:
    backend = str(getattr(args, "publisher_backend", "check-run") or "check-run")
    if backend not in ALLOWED_BACKENDS:
        raise PublisherError(
            f"Unknown publisher backend {backend!r}; "
            f"allowed: {sorted(ALLOWED_BACKENDS)}"
        )
    return backend


def _cli_app_ids(args: argparse.Namespace) -> tuple[int | None, int | None]:
    app_id = int(getattr(args, "expected_app_id", 0) or 0)
    installation_id = int(getattr(args, "expected_installation_id", 0) or 0)
    return (
        app_id if app_id > 0 else None,
        installation_id if installation_id > 0 else None,
    )


def _pr_labels(pr: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for entry in pr.get("labels") or []:
        if isinstance(entry, dict) and entry.get("name"):
            labels.append(str(entry["name"]))
        elif isinstance(entry, str):
            labels.append(entry)
    return labels


def _is_workflow_path(path: str) -> bool:
    return path.startswith(".github/workflows/") and (
        path.endswith(".yml") or path.endswith(".yaml")
    )


def enforce_policy_gate_for_pr(
    client: GitHubStatusClient,
    *,
    pr_number: int,
    commit_sha: str,
) -> dict[str, Any]:
    """Verify PR head SHA and run the local policy-gate mirror. Fail closed."""
    pr = client.get_pull_request(pr_number)
    head = (pr.get("head") or {}).get("sha")
    if not head:
        raise PublisherError(f"PR #{pr_number} head SHA missing from GitHub response")
    if str(head).lower() != commit_sha.lower():
        raise PublisherError(
            f"PR #{pr_number} head SHA {head} does not match commit_sha {commit_sha}"
        )

    files = client.list_pull_request_files(pr_number)
    workflow_contents: dict[str, str] = {}
    for entry in files:
        filename = str(entry.get("filename") or "")
        status = str(entry.get("status") or "modified")
        if _is_workflow_path(filename) and status != "removed":
            workflow_contents[filename] = client.get_repo_file_content(
                filename, commit_sha
            )

    policy = evaluate_policy_gate(
        title=str(pr.get("title") or ""),
        labels=_pr_labels(pr),
        files=files,
        workflow_contents=workflow_contents,
    )
    if not policy.ok:
        raise PublisherError(
            "policy-gate local mirror failed: " + " | ".join(policy.failures)
        )
    return {
        "category": policy.category,
        "category_source": policy.category_source,
        "passes": list(policy.passes),
        "failures": list(policy.failures),
        "ok": True,
    }


def _assert_clean_live_worktree(repo_root: Path) -> None:
    info = collect_git_info(repo_root)
    if info.dirty_worktree:
        raise PublisherError(
            "Live worktree is dirty; refusing publish of commit status"
        )


def _build_check_run_from_validation(result: Any, args: argparse.Namespace) -> Any:
    started = str(result.started_at_utc or "")
    ended = str(result.ended_at_utc or "")
    if not started or not ended:
        raise PublisherError(
            "Check Run mode requires started_at_utc and ended_at_utc in evidence"
        )
    return build_check_run_payload(
        commit_sha=result.commit_sha,
        run_id=result.run_id,
        ok=True,
        started_at_utc=started,
        ended_at_utc=ended,
        target_url=args.target_url or None,
        optional_skipped=result.optional_skipped,
        name=str(getattr(args, "check_run_name", None) or CHECK_RUN_NAME),
    )


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
                started_at_utc=result.started_at_utc,
                ended_at_utc=result.ended_at_utc,
            )
    out: dict[str, Any] = {"command": "validate", **result.to_dict()}
    if result.ok and _backend_name(args) == "check-run":
        try:
            check_payload = _build_check_run_from_validation(result, args)
            out["intended_check_run_payload"] = check_payload.to_api_body()
        except PublisherError as exc:
            out["ok"] = False
            out["reason"] = str(exc)
            _print_json(out)
            print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
            return FAILURE_EXIT
    _print_json(out)
    if not result.ok:
        print(
            f"REJECT: {redact_text(result.reason or 'validation failed')}",
            file=sys.stderr,
        )
        return FAILURE_EXIT
    return SUCCESS_EXIT


def cmd_dry_run(args: argparse.Namespace) -> int:
    try:
        _require_pr_for_required_context(args)
        backend = _backend_name(args)
    except PublisherError as exc:
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
    policy_result: dict[str, Any] | None = None
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
        if int(args.pr_number or 0) > 0:
            try:
                token = resolve_token()
                owner, repo = result.repository.split("/", 1)
                client = GitHubStatusClient(token=token, owner=owner, repo=repo)
                policy_result = enforce_policy_gate_for_pr(
                    client, pr_number=int(args.pr_number), commit_sha=commit_sha
                )
            except (
                AuthenticationError,
                GitHubApiError,
                LedgerError,
                PublisherError,
            ) as exc:
                print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
                _print_json(
                    {
                        "command": "dry-run",
                        "ok": False,
                        "reason": redact_text(str(exc)),
                        "write_attempted": False,
                        "policy_gate": None,
                    }
                )
                return FAILURE_EXIT
        try:
            owner, repo = result.repository.split("/", 1)
            app_id, installation_id = _cli_app_ids(args)
            if backend == "check-run":
                # Dry-run must not require a live App token; inject a placeholder
                # for payload shaping only — never used for network writes.
                check_payload = _build_check_run_from_validation(result, args)
                publisher = build_publisher_backend(
                    backend=backend,
                    app_token="dry-run-app-installation-token",
                    expected_app_id=resolve_expected_app_id(
                        cli_value=app_id, require=True
                    ),
                    expected_installation_id=resolve_expected_installation_id(
                        cli_value=installation_id, require=True
                    ),
                    owner=owner,
                    repo=repo,
                )
                publish_result = publisher.publish(
                    check_run_payload=check_payload, dry_run=True
                )
                github_body = {
                    "dry_run": True,
                    "publisher_backend": backend,
                    "body": publish_result.payload_body,
                    "expected_app_id": publish_result.github_app_id,
                    "expected_installation_id": publish_result.github_installation_id,
                }
                write_attempted = any(
                    not c.get("dry_run") for c in getattr(publisher, "write_calls", [])
                )
            else:
                client = GitHubStatusClient(token="dry-run-token")
                publisher = build_publisher_backend(
                    backend=backend, status_client=client, owner=owner, repo=repo
                )
                publish_result = publisher.publish(
                    status_payload=result.intended_payload, dry_run=True
                )
                github_body = {
                    "dry_run": True,
                    "publisher_backend": backend,
                    "sha": result.intended_payload.sha,
                    "body": publish_result.payload_body,
                }
                write_attempted = any(not c.get("dry_run") for c in client.write_calls)
        except (AuthenticationError, GitHubApiError, PublisherError) as exc:
            print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
            _print_json(
                {
                    "command": "dry-run",
                    "ok": False,
                    "reason": redact_text(str(exc)),
                    "write_attempted": False,
                    "publisher_backend": backend,
                }
            )
            return FAILURE_EXIT
    payload: dict[str, Any] = {
        "command": "dry-run",
        "ok": result.ok,
        "reason": result.reason,
        "validation": result.to_dict(),
        "github_payload": github_body,
        "write_attempted": write_attempted,
        "network_write": False,
        "publisher_backend": backend,
    }
    if policy_result is not None:
        payload["policy_gate"] = policy_result
    _print_json(payload)
    if not result.ok:
        print(
            f"REJECT: {redact_text(result.reason or 'validation failed')}",
            file=sys.stderr,
        )
        return FAILURE_EXIT
    return SUCCESS_EXIT


def cmd_publish(args: argparse.Namespace) -> int:
    try:
        _require_pr_for_required_context(args)
        backend = _backend_name(args)
    except PublisherError as exc:
        print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
        _print_json({"command": "publish", "ok": False, "reason": str(exc)})
        return FAILURE_EXIT

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
        owner, repo = result.repository.split("/", 1)
        # Reads (commit exists, PR head, policy gate) stay on the interim token path.
        read_token = resolve_token()
        read_client = GitHubStatusClient(token=read_token, owner=owner, repo=repo)
        read_client.assert_commit_exists(commit_sha)
        policy_result: dict[str, Any] | None = None
        if int(args.pr_number or 0) > 0:
            policy_result = enforce_policy_gate_for_pr(
                read_client, pr_number=int(args.pr_number), commit_sha=commit_sha
            )
        ledger = load_ledger(ledger_path)
        assert_run_id_not_reused(
            ledger, run_id=result.run_id, commit_sha=result.commit_sha
        )
        _assert_clean_live_worktree(repo_root)
        read_client.assert_commit_exists(commit_sha)
        if int(args.pr_number or 0) > 0:
            head = read_client.get_pull_request_head_sha(int(args.pr_number))
            if head.lower() != commit_sha.lower():
                raise PublisherError(
                    f"PR #{args.pr_number} head SHA {head} does not match "
                    f"commit_sha {commit_sha}"
                )

        app_id, installation_id = _cli_app_ids(args)
        if backend == "check-run":
            check_payload = _build_check_run_from_validation(result, args)
            publisher = build_publisher_backend(
                backend=backend,
                app_token=resolve_app_installation_token(),
                expected_app_id=resolve_expected_app_id(cli_value=app_id, require=True),
                expected_installation_id=resolve_expected_installation_id(
                    cli_value=installation_id, require=True
                ),
                owner=owner,
                repo=repo,
            )
            publish_result = publisher.publish(
                check_run_payload=check_payload, dry_run=False
            )
            if not publish_result.idempotent_noop:
                append_entry(
                    ledger_path,
                    LedgerEntry(
                        run_id=result.run_id,
                        commit_sha=result.commit_sha,
                        repository=result.repository,
                        status_context=args.status_context,
                        manifest_sha256=result.manifest_sha256,
                        published_at_utc=utc_now(),
                        state=check_payload.conclusion,
                        publisher_backend="check-run",
                        github_object_type="check_run",
                        github_check_run_id=publish_result.remote_id,
                        github_app_id=publish_result.github_app_id,
                        github_installation_id=publish_result.github_installation_id,
                        check_run_name=publish_result.check_run_name,
                        head_sha=publish_result.head_sha,
                        external_id=publish_result.external_id,
                        remote_verification_status=(
                            publish_result.remote_verification_status
                        ),
                    ),
                )
            api_result = {
                "id": publish_result.remote_id,
                "conclusion": check_payload.conclusion,
                "name": check_payload.name,
                "head_sha": commit_sha,
                "external_id": check_payload.external_id,
                "idempotent_noop": publish_result.idempotent_noop,
                "remote_verification_status": (
                    publish_result.remote_verification_status
                ),
                "app_id": publish_result.github_app_id,
            }
        else:
            prior = find_exact_publication(
                ledger,
                run_id=result.run_id,
                commit_sha=result.commit_sha,
                repository=result.repository,
                status_context=args.status_context,
                manifest_sha256=result.manifest_sha256,
                state=result.intended_payload.state,
            )
            idempotent_noop = False
            api_result: dict[str, Any]
            if prior is not None:
                live = read_client.get_commit_status(commit_sha)
                latest = _latest_context_status(
                    live.get("statuses"), context=args.status_context
                )
                expected_body = result.intended_payload.to_api_body()
                expected_status_id = prior.get("github_status_id")
                if latest is not None and all(
                    (
                        latest.get("state") == expected_body["state"],
                        latest.get("description") == expected_body["description"],
                        latest.get("target_url") == expected_body.get("target_url"),
                        expected_status_id is not None,
                        str(latest.get("id")) == str(expected_status_id),
                    )
                ):
                    api_result = {
                        "id": prior.get("github_status_id"),
                        "state": result.intended_payload.state,
                        "context": args.status_context,
                        "sha": commit_sha,
                        "idempotent_noop": True,
                    }
                    idempotent_noop = True
            if not idempotent_noop:
                publisher = build_publisher_backend(
                    backend=backend,
                    status_client=read_client,
                    owner=owner,
                    repo=repo,
                )
                publish_result = publisher.publish(
                    status_payload=result.intended_payload, dry_run=False
                )
                api_result = {
                    "id": publish_result.remote_id,
                    "state": result.intended_payload.state,
                    "context": args.status_context,
                    "sha": commit_sha,
                    "idempotent_noop": False,
                }
                append_entry(
                    ledger_path,
                    LedgerEntry(
                        run_id=result.run_id,
                        commit_sha=result.commit_sha,
                        repository=result.repository,
                        status_context=args.status_context,
                        manifest_sha256=result.manifest_sha256,
                        published_at_utc=utc_now(),
                        github_status_id=publish_result.remote_id,
                        state=result.intended_payload.state,
                        publisher_backend="commit-status",
                        github_object_type="commit_status",
                        head_sha=commit_sha,
                        remote_verification_status=(
                            publish_result.remote_verification_status
                        ),
                    ),
                )
    except (AuthenticationError, GitHubApiError, LedgerError, PublisherError) as exc:
        print(f"REJECT: {redact_text(str(exc))}", file=sys.stderr)
        _print_json(
            {
                "command": "publish",
                "ok": False,
                "reason": redact_text(str(exc)),
                "publisher_backend": backend,
            }
        )
        return FAILURE_EXIT

    out: dict[str, Any] = {
        "command": "publish",
        "ok": True,
        "sha": commit_sha,
        "context": args.status_context,
        "state": result.intended_payload.state,
        "run_id": result.run_id,
        "publisher_backend": backend,
        "github": redact_mapping(api_result),
        "optional_skipped": result.optional_skipped,
    }
    if policy_result is not None:
        out["policy_gate"] = policy_result
    _print_json(out)
    return SUCCESS_EXIT


def cmd_inspect(args: argparse.Namespace) -> int:
    repo_root, _evidence_dir, _ledger = _resolve_paths(args)
    commit_sha = _resolve_commit_sha(args, repo_root)
    backend = _backend_name(args)
    try:
        owner, repo = (args.repository or EXPECTED_REPOSITORY).split("/", 1)
        if backend == "check-run":
            app_id, installation_id = _cli_app_ids(args)
            expected_app_id = resolve_expected_app_id(cli_value=app_id, require=True)
            expected_installation_id = resolve_expected_installation_id(
                cli_value=installation_id, require=True
            )
            assert expected_app_id is not None
            assert expected_installation_id is not None
            check_client = CheckRunBackend(
                token=resolve_app_installation_token(),
                expected_app_id=expected_app_id,
                expected_installation_id=expected_installation_id,
                owner=owner,
                repo=repo,
            )
            name = str(getattr(args, "check_run_name", None) or CHECK_RUN_NAME)
            runs = check_client.list_check_runs_for_sha(commit_sha, check_name=name)
            filtered = []
            for entry in runs:
                app = entry.get("app") if isinstance(entry.get("app"), dict) else {}
                remote_app_id = app.get("id")
                if remote_app_id is not None:
                    try:
                        if (
                            parse_positive_int(
                                remote_app_id, field_name="remote app.id"
                            )
                            != expected_app_id
                        ):
                            continue
                    except PublisherError:
                        continue
                filtered.append(
                    {
                        "id": entry.get("id"),
                        "name": entry.get("name"),
                        "head_sha": entry.get("head_sha"),
                        "status": entry.get("status"),
                        "conclusion": entry.get("conclusion"),
                        "external_id": entry.get("external_id"),
                        "app_id": remote_app_id,
                        "html_url": entry.get("html_url"),
                    }
                )
            _print_json(
                {
                    "command": "inspect",
                    "publisher_backend": backend,
                    "sha": commit_sha,
                    "check_run_name": name,
                    "expected_app_id": expected_app_id,
                    "check_runs": filtered,
                    "total_count": len(filtered),
                }
            )
            return SUCCESS_EXIT

        token = resolve_token()
        client = GitHubStatusClient(token=token, owner=owner, repo=repo)
        status = client.get_commit_status(commit_sha)
    except (AuthenticationError, GitHubApiError, PublisherError) as exc:
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
    filtered_statuses = [
        c
        for c in contexts
        if not args.status_context or c.get("context") == args.status_context
    ]
    _print_json(
        {
            "command": "inspect",
            "publisher_backend": backend,
            "sha": commit_sha,
            "state": status.get("state"),
            "statuses": filtered_statuses if args.status_context else contexts,
            "total_count": status.get("total_count"),
        }
    )
    return SUCCESS_EXIT


def cmd_app_auth_probe(args: argparse.Namespace) -> int:
    """Mint App installation token and write SHADOW Check Run only (#4170 Phase C).

    Refuses required name ``cdb-local-ci`` and any Commit Status write. Intended
    for disposable probe SHAs — bypasses full evidence gates by design.
    """
    commit_sha = (args.commit_sha or "").strip().lower()
    if not commit_sha or len(commit_sha) != 40:
        print(
            "REJECT: --commit-sha must be the exact 40-char probe SHA",
            file=sys.stderr,
        )
        _print_json(
            {
                "command": "app-auth-probe",
                "ok": False,
                "reason": "exact 40-char commit SHA required",
            }
        )
        return USAGE_EXIT

    check_name = str(getattr(args, "check_run_name", None) or SHADOW_CHECK_RUN_NAME)
    if check_name != SHADOW_CHECK_RUN_NAME:
        print(
            f"REJECT: app-auth-probe only allows check-run name "
            f"{SHADOW_CHECK_RUN_NAME!r} (refused {check_name!r})",
            file=sys.stderr,
        )
        _print_json(
            {
                "command": "app-auth-probe",
                "ok": False,
                "reason": f"refused non-shadow check-run name {check_name!r}",
                "allowed_name": SHADOW_CHECK_RUN_NAME,
            }
        )
        return FAILURE_EXIT
    if check_name == CHECK_RUN_NAME:
        print(
            f"REJECT: app-auth-probe refuses required name {CHECK_RUN_NAME!r}",
            file=sys.stderr,
        )
        return FAILURE_EXIT

    repository = str(args.repository or EXPECTED_REPOSITORY)
    if repository != EXPECTED_REPOSITORY:
        print(
            f"REJECT: repository must be {EXPECTED_REPOSITORY}",
            file=sys.stderr,
        )
        return FAILURE_EXIT

    try:
        owner, repo = repository.split("/", 1)
        app_id, installation_id = _cli_app_ids(args)
        expected_app_id = resolve_expected_app_id(cli_value=app_id, require=True)
        expected_installation_id = resolve_expected_installation_id(
            cli_value=installation_id, require=True
        )
        assert expected_app_id is not None and expected_installation_id is not None
        token = resolve_app_installation_token()
        backend = CheckRunBackend(
            token=token,
            expected_app_id=expected_app_id,
            expected_installation_id=expected_installation_id,
            owner=owner,
            repo=repo,
        )
        now = utc_now()
        run_id = f"app-auth-probe-{commit_sha[:12]}"
        payload = CheckRunPayload(
            name=SHADOW_CHECK_RUN_NAME,
            head_sha=commit_sha,
            conclusion="success",
            started_at=now,
            completed_at=now,
            external_id=build_check_run_external_id(
                run_id=run_id, commit_sha=commit_sha
            ),
            output_title="cdb-local-ci App auth probe (shadow)",
            output_summary=(
                "Phase-C shadow probe: GitHub App JWT auto-mint + Check Run write. "
                "Not the required cdb-local-ci context."
            ),
        )
        if args.dry_run:
            result = backend.publish(check_run_payload=payload, dry_run=True)
            _print_json(
                {
                    "command": "app-auth-probe",
                    "ok": True,
                    "dry_run": True,
                    "sha": commit_sha,
                    "check_run_name": SHADOW_CHECK_RUN_NAME,
                    "expected_app_id": expected_app_id,
                    "expected_installation_id": expected_installation_id,
                    "credentials": credential_summary(),
                    "remote_verification_status": result.remote_verification_status,
                }
            )
            return SUCCESS_EXIT

        result = backend.publish(check_run_payload=payload, dry_run=False)
        _print_json(
            {
                "command": "app-auth-probe",
                "ok": True,
                "dry_run": False,
                "sha": commit_sha,
                "check_run_name": result.check_run_name,
                "github_check_run_id": result.remote_id,
                "app_id": result.github_app_id,
                "installation_id": result.github_installation_id,
                "external_id": result.external_id,
                "remote_verification_status": result.remote_verification_status,
                "idempotent_noop": result.idempotent_noop,
                "credentials": credential_summary(),
            }
        )
        return SUCCESS_EXIT
    except AuthenticationError as exc:
        message = redact_text(str(exc))
        blocked = (
            "insufficient app permission" in message.lower()
            or "checks" in message.lower()
        )
        status = "BLOCKED_APP_PERMISSION" if blocked else "AUTH_FAILED"
        print(f"REJECT: {message}", file=sys.stderr)
        _print_json(
            {
                "command": "app-auth-probe",
                "ok": False,
                "status": status,
                "reason": message,
                "credentials": credential_summary(),
            }
        )
        return FAILURE_EXIT
    except (GitHubApiError, PublisherError) as exc:
        message = redact_text(str(exc))
        print(f"REJECT: {message}", file=sys.stderr)
        _print_json(
            {
                "command": "app-auth-probe",
                "ok": False,
                "reason": message,
                "credentials": credential_summary(),
            }
        )
        return FAILURE_EXIT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ci.publisher",
        description=(
            "Validate local Docker CI evidence and publish a commit-bound "
            "GitHub Commit Status (default) or an explicit App-bound Check Run "
            "(--publisher-backend check-run). Check Run mode auto-mints an "
            "installation token when App ID/Installation ID/PEM are set. "
            "Branch Protection is not changed by this tool."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate evidence only")
    _add_common_args(validate)
    validate.set_defaults(func=cmd_validate)

    dry = sub.add_parser("dry-run", help="Validate and print payload without write")
    _add_common_args(dry)
    dry.set_defaults(func=cmd_dry_run)

    publish = sub.add_parser(
        "publish",
        help="Validate and publish Commit Status or App Check Run",
    )
    _add_common_args(publish)
    publish.set_defaults(func=cmd_publish)

    inspect = sub.add_parser(
        "inspect",
        help="Inspect GitHub statuses or App Check Runs for a SHA",
    )
    _add_common_args(inspect)
    # evidence-dir not strictly required for inspect — allow dummy.
    for action in inspect._actions:
        if action.dest == "evidence_dir":
            action.required = False
            action.default = "."
    inspect.set_defaults(func=cmd_inspect)

    probe = sub.add_parser(
        "app-auth-probe",
        help=(
            f"Mint App installation token and write shadow Check Run "
            f"{SHADOW_CHECK_RUN_NAME} only (no evidence gates; refuses "
            f"{CHECK_RUN_NAME})"
        ),
    )
    probe.add_argument(
        "--commit-sha",
        required=True,
        help="Exact 40-char probe commit SHA (not main)",
    )
    probe.add_argument(
        "--repository",
        default=EXPECTED_REPOSITORY,
        help="owner/name (must be jannekbuengener/Claire_de_Binare)",
    )
    probe.add_argument(
        "--expected-app-id",
        type=int,
        default=0,
        help="Expected GitHub App ID (or CDB_GH_APP_ID / alias)",
    )
    probe.add_argument(
        "--expected-installation-id",
        type=int,
        default=0,
        help="Expected installation ID (or CDB_GH_APP_INSTALLATION_ID / alias)",
    )
    probe.add_argument(
        "--check-run-name",
        default=SHADOW_CHECK_RUN_NAME,
        help=f"Must be {SHADOW_CHECK_RUN_NAME} (default)",
    )
    probe.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve credentials path and build payload without GitHub write",
    )
    probe.set_defaults(func=cmd_app_auth_probe)

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
