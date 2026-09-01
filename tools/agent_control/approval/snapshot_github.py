"""Build approval snapshots from live GitHub PR state (read-only, #4505)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from tools.agent_control.approval.acceptance_provenance import resolve_final_head_provenance
from tools.agent_control.approval.comment_provenance import CommentRecord
from tools.agent_control.approval.drift import load_baseline, protection_view_fingerprint
from tools.agent_control.approval.gh_api import (
    gh_api_json,
    merge_check_runs_payload,
    merge_comment_pages,
)
from tools.agent_control.approval.context import default_repo_paths
from tools.agent_control.paths import REPO_ROOT
from tools.pr_routing.engine import parse_batch_pr_body

CDB_LOCAL_CI_APP_ID = 4410232
DEFAULT_REPOSITORY = "jannekbuengener/Claire_de_Binare"


def _parse_steward_state(body: str) -> str | None:
    if "<!-- cdb-batch-pr:v1" not in body:
        return None
    try:
        return parse_batch_pr_body(body).steward_state
    except ValueError:
        return None


def _fetch_check_observations(owner: str, repo: str, head_sha: str) -> list[dict[str, Any]]:
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


def _fetch_commit_statuses(owner: str, repo: str, head_sha: str) -> list[dict[str, Any]]:
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


def _fetch_blocking_thread_count(owner: str, repo: str, pr_number: int) -> tuple[int | None, bool]:
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

        repo_node = payload.get("data", {}).get("repository") if isinstance(payload, dict) else None
        pr_node = repo_node.get("pullRequest") if isinstance(repo_node, dict) else None
        threads_block = (
            pr_node.get("reviewThreads")
            if isinstance(pr_node, dict) and isinstance(pr_node.get("reviewThreads"), dict)
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
) -> tuple[list[dict[str, Any]], bool]:
    """Read live branch protection required contexts; fail closed when unavailable."""
    try:
        payload = gh_api_json(
            ["api", f"repos/{owner}/{repo}/branches/{base_branch}/protection"]
        )
    except RuntimeError:
        return [], False
    if not isinstance(payload, dict):
        return [], False
    rsc = payload.get("required_status_checks")
    contexts: list[str] = []
    if isinstance(rsc, dict):
        raw = rsc.get("contexts")
        if isinstance(raw, list):
            contexts = [str(item) for item in raw if isinstance(item, str) and item.strip()]
    if not contexts:
        return [], False
    out: list[dict[str, Any]] = []
    for name in contexts:
        entry: dict[str, Any] = {"name": name, "mechanism": "unknown"}
        if name == "cdb-local-ci":
            entry = {
                "name": "cdb-local-ci",
                "mechanism": "check_run",
                "app_id": CDB_LOCAL_CI_APP_ID,
            }
        out.append(entry)
    return out, True


def _build_adapter_block(repo_root: Path) -> dict[str, Any]:
    paths = default_repo_paths(repo_root)
    baseline = load_baseline(paths.baseline_path)
    adapter_id = "cursor-approval-dashboard"
    fingerprint = None
    if isinstance(baseline, dict):
        fingerprint = baseline.get("capability_fingerprint")
        baseline_adapter = baseline.get("adapter_id")
        if isinstance(baseline_adapter, str) and baseline_adapter.strip():
            adapter_id = baseline_adapter
    if not isinstance(fingerprint, str) or not fingerprint.startswith("sha256:"):
        raise RuntimeError("approval baseline capability_fingerprint missing")
    return {
        "adapter_id": adapter_id,
        "capability_fingerprint": fingerprint,
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

    base_branch = ((pr.get("base") or {}).get("ref") or "main")
    required_checks, protection_ok = _fetch_required_checks(owner, repo, base_branch)
    if not protection_ok:
        protection = {"required_checks": []}
        if "PROTECTION_INCOMPLETE" not in snapshot_reason_codes:
            snapshot_reason_codes.append("PROTECTION_INCOMPLETE")
    else:
        protection = {"required_checks": required_checks}

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
    if thread_state is not None:
        snapshot["review_thread_state"] = thread_state
    return snapshot
