"""Build approval snapshots from live GitHub PR state (read-only, #4505)."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from tools.agent_control.approval.acceptance_provenance import resolve_final_head_provenance
from tools.agent_control.paths import REPO_ROOT
from tools.pr_routing.engine import parse_batch_pr_body

CDB_LOCAL_CI_APP_ID = 4410232
DEFAULT_REPOSITORY = "jannekbuengener/Claire_de_Binare"


def _gh_json(argv: list[str], *, timeout: int = 60) -> Any:
    result = subprocess.run(
        ["gh", *argv],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"gh failed ({result.returncode}): {detail}")
    return json.loads(result.stdout or "null")


def _parse_steward_state(body: str) -> str | None:
    if "<!-- cdb-batch-pr:v1" not in body:
        return None
    try:
        return parse_batch_pr_body(body).steward_state
    except ValueError:
        return None


def _fetch_check_observations(owner: str, repo: str, head_sha: str) -> list[dict[str, Any]]:
    payload = _gh_json(
        [
            "api",
            f"repos/{owner}/{repo}/commits/{head_sha}/check-runs",
            "--paginate",
        ]
    )
    items = payload.get("check_runs") if isinstance(payload, dict) else []
    out: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
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
    payload = _gh_json(["api", f"repos/{owner}/{repo}/commits/{head_sha}/status"])
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


def build_github_approval_snapshot(
    *,
    pr_number: int,
    repository: str = DEFAULT_REPOSITORY,
    repo_root: Any = None,
) -> dict[str, Any]:
    """Read-only live snapshot with provenance-bound final_head block."""
    owner, repo = repository.split("/", 1)
    pr = _gh_json(
        [
            "api",
            f"repos/{owner}/{repo}/pulls/{pr_number}",
        ]
    )
    if not isinstance(pr, dict):
        raise RuntimeError("invalid pull response")

    head_sha = ((pr.get("head") or {}).get("sha") or "").lower()
    base_sha = ((pr.get("base") or {}).get("sha") or "").lower()
    body = str(pr.get("body") or "")
    is_draft = bool(pr.get("draft"))

    comments_payload = _gh_json(
        [
            "api",
            f"repos/{owner}/{repo}/issues/{pr_number}/comments",
            "--paginate",
        ]
    )
    comment_bodies: list[tuple[int | None, str]] = []
    if isinstance(comments_payload, list):
        for item in comments_payload:
            if isinstance(item, dict):
                comment_bodies.append((item.get("id"), str(item.get("body") or "")))

    steward_state = _parse_steward_state(body)
    provenance = resolve_final_head_provenance(
        comment_bodies=comment_bodies,
        pr_number=pr_number,
        repository=repository,
        live_head_sha=head_sha,
        steward_state=steward_state,
        repo_root=repo_root or REPO_ROOT,
    )
    final_head = provenance.to_snapshot_final_head()
    if provenance.reason_codes:
        snapshot_reason_codes = list(provenance.reason_codes)
    else:
        snapshot_reason_codes = []

    checks = _fetch_check_observations(owner, repo, head_sha)
    checks.extend(_fetch_commit_statuses(owner, repo, head_sha))

    review_threads = 0
    try:
        review_comments = _gh_json(
            [
                "api",
                f"repos/{owner}/{repo}/pulls/{pr_number}/comments",
                "--paginate",
            ]
        )
        if isinstance(review_comments, list):
            review_threads = sum(
                1 for c in review_comments if isinstance(c, dict) and not c.get("in_reply_to_id")
            )
    except RuntimeError:
        review_threads = 0

    return {
        "pr": {
            "number": pr_number,
            "is_draft": is_draft,
            "head_sha": head_sha,
            "base_sha": base_sha,
            "review_decision": None,
            "blocking_threads": review_threads,
        },
        "checks": checks,
        "protection": {
            "required_checks": [
                {
                    "name": "cdb-local-ci",
                    "mechanism": "check_run",
                    "app_id": CDB_LOCAL_CI_APP_ID,
                }
            ]
        },
        "final_head": final_head,
        "final_head_reason_codes": snapshot_reason_codes,
        "adapter": {
            "adapter_id": "cdb-approval-snapshot-github",
            "capability_fingerprint": "read-only",
        },
    }
