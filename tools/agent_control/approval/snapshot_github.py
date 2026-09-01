"""Build approval snapshots from live GitHub PR state (read-only, #4505)."""

from __future__ import annotations

import json
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
_DEBUG_LOG = Path("debug-6088fb.log")


def _debug_log(*, hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    # #region agent log
    try:
        import time

        payload = {
            "sessionId": "6088fb",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass
    # #endregion


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
        _debug_log(
            hypothesis_id="H3",
            location="snapshot_github.py:_fetch_review_decision",
            message="review decision retrieval failed",
            data={"pr_number": pr_number, "stderr": (result.stderr or "")[:200]},
        )
        return None
    value = (result.stdout or "").strip()
    if not value or value == "null":
        return "REVIEW_REQUIRED"
    return value


def _fetch_blocking_thread_count(owner: str, repo: str, pr_number: int) -> tuple[int | None, bool]:
    """Return (count, retrieval_ok). count=None when retrieval failed."""
    query = """
    query($owner: String!, $name: String!, $number: Int!) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100) {
            nodes { isResolved isOutdated }
          }
        }
      }
    }
    """
    try:
        payload = gh_api_json(
            [
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
        )
    except RuntimeError as exc:
        _debug_log(
            hypothesis_id="H4",
            location="snapshot_github.py:_fetch_blocking_thread_count",
            message="graphql thread retrieval failed",
            data={"pr_number": pr_number, "error": str(exc)[:200]},
        )
        return None, False

    repo_node = payload.get("data", {}).get("repository") if isinstance(payload, dict) else None
    pr_node = repo_node.get("pullRequest") if isinstance(repo_node, dict) else None
    threads = (
        pr_node.get("reviewThreads", {}).get("nodes")
        if isinstance(pr_node, dict) and isinstance(pr_node.get("reviewThreads"), dict)
        else None
    )
    if not isinstance(threads, list):
        return None, False
    blocking = sum(
        1
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("isResolved") is False
        and thread.get("isOutdated") is False
    )
    _debug_log(
        hypothesis_id="H4",
        location="snapshot_github.py:_fetch_blocking_thread_count",
        message="blocking thread count computed",
        data={"pr_number": pr_number, "blocking": blocking, "total": len(threads)},
    )
    return blocking, True


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

    protection = {
        "required_checks": [
            {
                "name": "cdb-local-ci",
                "mechanism": "check_run",
                "app_id": CDB_LOCAL_CI_APP_ID,
            }
        ]
    }

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
