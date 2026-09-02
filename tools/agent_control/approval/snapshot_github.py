"""Build approval snapshots from live GitHub PR state (read-only, #4505)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from tools.agent_control.approval.acceptance_provenance import (
    resolve_final_head_provenance,
)
from tools.agent_control.approval.adapter_capabilities import (
    GITHUB_APPROVAL_SNAPSHOT_ADAPTER_ID,
    adapter_capability_fingerprint,
)
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.drift import (
    load_baseline,
    protection_view_fingerprint,
)
from tools.agent_control.approval.codes import (
    REASON_PROTECTION_INCOMPLETE,
    REASON_PROTECTION_READ_UNAVAILABLE,
)
from tools.agent_control.approval.gh_api import (
    gh_api_json,
    merge_check_runs_payload,
    merge_comment_pages,
)
from tools.agent_control.approval.protection_live_evidence import (
    parse_required_checks_from_protection_payload,
    probe_branch_protection_api,
    resolve_protection_live_attestation,
)
from tools.agent_control.approval.context import default_repo_paths
from tools.agent_control.paths import REPO_ROOT
from tools.pr_routing.engine import parse_batch_pr_metadata

DEFAULT_REPOSITORY = "jannekbuengener/Claire_de_Binare"


def _parse_steward_state(body: str) -> str | None:
    if "<!-- cdb-batch-pr:v1" not in body:
        return None
    try:
        return parse_batch_pr_metadata(body).steward_state
    except ValueError:
        return None


def _fetch_check_observations(
    owner: str, repo: str, head_sha: str
) -> list[dict[str, Any]]:
    payload = gh_api_json(
        [
            "api",
            f"repos/{owner}/{repo}/commits/{head_sha}/check-runs",
            "--paginate",
        ]
    )
    out: list[dict[str, Any]] = []
    for item in merge_check_runs_payload(payload):
        app = item.get("app") if isinstance(item.get("app"), dict) else {}
        out.append(
            {
                "name": item.get("name"),
                "mechanism": "check_run",
                "status": item.get("status") or "unknown",
                "conclusion": item.get("conclusion"),
                "app_id": app.get("id"),
                "source_sha": item.get("head_sha") or head_sha,
            }
        )
    return out


def _fetch_commit_statuses(
    owner: str, repo: str, head_sha: str
) -> list[dict[str, Any]]:
    payload = gh_api_json(["api", f"repos/{owner}/{repo}/commits/{head_sha}/status"])
    out: list[dict[str, Any]] = []
    for item in payload.get("statuses") or [] if isinstance(payload, dict) else []:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "name": item.get("context"),
                "mechanism": "commit_status",
                "status": item.get("state") or "unknown",
                "conclusion": None,
                "app_id": None,
                "source_sha": head_sha,
            }
        )
    return out


def _fetch_review_decision(owner: str, repo: str, pr_number: int) -> str | None:
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "reviewDecision",
            "-q",
            ".reviewDecision",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        return None
    value = (result.stdout or "").strip()
    if not value or value == "null":
        return "REVIEW_REQUIRED"
    return value


def _fetch_blocking_thread_count(
    owner: str, repo: str, pr_number: int
) -> tuple[int | None, bool]:
    """Return (count, retrieval_ok). count=None when retrieval failed."""
    query = """
    query($owner: String!, $name: String!, $number: Int!, $after: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes { isResolved isOutdated }
          }
        }
      }
    }
    """
    blocking = 0
    cursor: str | None = None
    pages = 0
    max_pages = 50
    while pages < max_pages:
        pages += 1
        args = [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={repo}",
            "-F",
            f"number={pr_number}",
        ]
        if cursor:
            args.extend(["-f", f"after={cursor}"])
        try:
            payload = gh_api_json(args)
        except RuntimeError:
            return None, False

        repo_node = (
            payload.get("data", {}).get("repository")
            if isinstance(payload, dict)
            else None
        )
        pr_node = repo_node.get("pullRequest") if isinstance(repo_node, dict) else None
        threads_block = (
            pr_node.get("reviewThreads")
            if isinstance(pr_node, dict)
            and isinstance(pr_node.get("reviewThreads"), dict)
            else None
        )
        if not isinstance(threads_block, dict):
            return None, False
        threads = threads_block.get("nodes")
        if not isinstance(threads, list):
            return None, False
        blocking += sum(
            1
            for thread in threads
            if isinstance(thread, dict)
            and thread.get("isResolved") is False
            and thread.get("isOutdated") is False
        )
        page_info = threads_block.get("pageInfo")
        if not isinstance(page_info, dict):
            return None, False
        if page_info.get("hasNextPage") is True:
            next_cursor = page_info.get("endCursor")
            if not isinstance(next_cursor, str) or not next_cursor:
                return None, False
            cursor = next_cursor
            continue
        return blocking, True

    return None, False


def _fetch_required_checks(
    owner: str, repo: str, base_branch: str
) -> tuple[list[dict[str, Any]], bool, dict[str, Any] | None]:
    """Read live branch protection required contexts; fail closed when unavailable."""
    payload, read_error = probe_branch_protection_api(owner, repo, base_branch)
    if payload is None:
        return [], False, read_error.to_dict() if read_error else None
    parsed = parse_required_checks_from_protection_payload(payload)
    if parsed is None:
        return (
            [],
            False,
            {
                "endpoint": f"repos/{owner}/{repo}/branches/{base_branch}/protection",
                "message": "protection payload missing required_status_checks",
            },
        )
    required_checks, _strict = parsed
    return required_checks, True, None


def _build_adapter_block(repo_root: Path) -> dict[str, Any]:
    paths = default_repo_paths(repo_root)
    baseline = load_baseline(paths.baseline_path)
    adapter_id = GITHUB_APPROVAL_SNAPSHOT_ADAPTER_ID
    if isinstance(baseline, dict):
        baseline_adapter = baseline.get("adapter_id")
        if isinstance(baseline_adapter, str) and baseline_adapter.strip():
            adapter_id = baseline_adapter
    return {
        "adapter_id": adapter_id,
        "capability_fingerprint": adapter_capability_fingerprint(),
    }


def build_github_approval_snapshot(
    *,
    pr_number: int,
    repository: str = DEFAULT_REPOSITORY,
    repo_root: Any = None,
) -> dict[str, Any]:
    """Read-only live snapshot with provenance-bound final_head block."""
    root = repo_root or REPO_ROOT
    owner, repo = repository.split("/", 1)
    pr = gh_api_json(["api", f"repos/{owner}/{repo}/pulls/{pr_number}"])
    if not isinstance(pr, dict):
        raise RuntimeError("invalid pull response")

    head_sha = ((pr.get("head") or {}).get("sha") or "").lower()
    base_sha = ((pr.get("base") or {}).get("sha") or "").lower()
    body = str(pr.get("body") or "")
    is_draft = bool(pr.get("draft"))

    comments_payload = gh_api_json(
        [
            "api",
            f"repos/{owner}/{repo}/issues/{pr_number}/comments",
            "--paginate",
        ]
    )
    comments: list[CommentRecord] = []
    for item in merge_comment_pages(comments_payload):
        comments.append(CommentRecord.from_github_issue_comment(item))

    steward_state = _parse_steward_state(body)
    provenance = resolve_final_head_provenance(
        comments=comments,
        pr_number=pr_number,
        repository=repository,
        live_head_sha=head_sha,
        live_base_sha=base_sha,
        steward_state=steward_state,
        repo_root=root,
    )
    final_head = provenance.to_snapshot_final_head()
    snapshot_reason_codes = list(provenance.reason_codes)

    checks = _fetch_check_observations(owner, repo, head_sha)
    checks.extend(_fetch_commit_statuses(owner, repo, head_sha))

    review_decision = _fetch_review_decision(owner, repo, pr_number)
    blocking_threads, threads_ok = _fetch_blocking_thread_count(owner, repo, pr_number)
    thread_state: str | None = None
    if not threads_ok:
        thread_state = "unknown"
        blocking_threads = None

    base_branch = (pr.get("base") or {}).get("ref") or "main"
    required_checks, protection_ok, protection_read_error = _fetch_required_checks(
        owner, repo, base_branch
    )
    protection_source: str | None = None
    protection_read: dict[str, Any] | None = None
    if protection_ok:
        protection = {"required_checks": required_checks}
        protection_source = "branch_protection_api"
    else:
        attestation = resolve_protection_live_attestation(
            comments=comments,
            repository=repository,
            live_base_sha=base_sha,
            live_base_ref=base_branch,
            repo_root=root,
        )
        if attestation is not None:
            # Fingerprint/drift uses required_checks only (same shape as API path).
            protection = {"required_checks": attestation.required_checks}
            protection_source = "trusted_attestation"
            protection_read = {
                "source": "trusted_attestation",
                "comment_id": attestation.comment_id,
                "envelope_digest": attestation.envelope_digest,
                "observed_at": attestation.observed_at,
                "strict": attestation.strict,
            }
        else:
            protection = {"required_checks": []}
            protection_read = protection_read_error or {
                "source": "branch_protection_api",
                "message": "protection unreadable and no trusted attestation",
            }
            if REASON_PROTECTION_READ_UNAVAILABLE not in snapshot_reason_codes:
                snapshot_reason_codes.append(REASON_PROTECTION_READ_UNAVAILABLE)
            if REASON_PROTECTION_INCOMPLETE not in snapshot_reason_codes:
                snapshot_reason_codes.append(REASON_PROTECTION_INCOMPLETE)

    snapshot: dict[str, Any] = {
        "pr": {
            "number": pr_number,
            "is_draft": is_draft,
            "head_sha": head_sha,
            "base_sha": base_sha,
            "review_decision": review_decision,
            "blocking_threads": blocking_threads,
        },
        "checks": checks,
        "protection": protection,
        "final_head": final_head,
        "final_head_reason_codes": snapshot_reason_codes,
        "adapter": _build_adapter_block(root),
        "protection_view_fingerprint": protection_view_fingerprint(protection),
    }
    if protection_source is not None:
        snapshot["protection_source"] = protection_source
    if protection_read is not None:
        snapshot["protection_read"] = protection_read
    if thread_state is not None:
        snapshot["review_thread_state"] = thread_state
    return snapshot
