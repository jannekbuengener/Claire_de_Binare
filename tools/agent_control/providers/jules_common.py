"""Shared Jules REST v1alpha normalization and evidence shaping (#4461)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from tools.agent_control.provider import ProviderResult, sanitize_provider_result

JULES_STATUS_MAP = {
    "QUEUED": "QUEUED",
    "PLANNING": "RUNNING",
    "AWAITING_PLAN_APPROVAL": "RUNNING",
    "AWAITING_USER_FEEDBACK": "RUNNING",
    "IN_PROGRESS": "RUNNING",
    "PAUSED": "RUNNING",
    "FAILED": "FAILED",
    "COMPLETED": "SUCCEEDED",
    "STATE_UNSPECIFIED": "UNKNOWN",
}

_ACTIVITY_KEYS = (
    "agentMessaged",
    "userMessaged",
    "planGenerated",
    "planApproved",
    "progressUpdated",
    "sessionCompleted",
    "sessionFailed",
)


def normalize_jules_status(raw: str | None) -> tuple[str, str | None]:
    if raw is None:
        return "UNKNOWN", "PROVIDER_STATUS_UNKNOWN"
    key = str(raw).strip().upper()
    mapped = JULES_STATUS_MAP.get(key)
    if mapped is None:
        return "UNKNOWN", "PROVIDER_STATUS_UNKNOWN"
    if mapped == "FAILED":
        return mapped, "PROVIDER_RUN_FAILED"
    if mapped == "UNKNOWN":
        return mapped, "PROVIDER_STATUS_UNKNOWN"
    return mapped, None


def host_is_jules(url: str) -> bool:
    return (urlparse(url).hostname or "").lower() == "jules.googleapis.com"


def normalize_pull_requests(outputs: Any) -> list[dict[str, str | None]]:
    """Return safe PR handoff refs only; never provider-authored descriptions."""
    out: list[dict[str, str | None]] = []
    if not isinstance(outputs, list):
        return out
    for item in outputs:
        if not isinstance(item, dict):
            continue
        pr = item.get("pullRequest")
        if not isinstance(pr, dict):
            continue
        url = pr.get("url")
        if not isinstance(url, str) or not url.startswith("https://github.com/"):
            continue
        out.append(
            {
                "url": url,
                "title": str(pr.get("title")) if pr.get("title") is not None else None,
            }
        )
    return out


def normalize_activities(payload: Any) -> dict[str, Any]:
    """Reduce Jules activities to audit-safe metadata and plan identifiers.

    Agent/user message text, bash output, media and raw patches are deliberately
    excluded from durable provider refs. The execution/review path can fetch
    source-of-truth delivery data independently when required.
    """
    activities = payload.get("activities") if isinstance(payload, dict) else None
    if not isinstance(activities, list):
        activities = []
    compact: list[dict[str, Any]] = []
    latest_plan: dict[str, Any] | None = None
    for item in activities[:100]:
        if not isinstance(item, dict):
            continue
        kind = next((key for key in _ACTIVITY_KEYS if key in item), "unknown")
        row: dict[str, Any] = {
            "name": item.get("name"),
            "id": item.get("id"),
            "type": kind,
            "create_time": item.get("createTime"),
            "originator": item.get("originator"),
        }
        if kind == "planGenerated" and isinstance(item.get(kind), dict):
            plan = item[kind].get("plan")
            if isinstance(plan, dict):
                steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
                latest_plan = {
                    "id": plan.get("id"),
                    "create_time": plan.get("createTime"),
                    "steps": [
                        {
                            "id": step.get("id"),
                            "index": step.get("index"),
                            "title": step.get("title"),
                        }
                        for step in steps
                        if isinstance(step, dict)
                    ],
                }
                row["plan_id"] = plan.get("id")
        elif kind == "planApproved" and isinstance(item.get(kind), dict):
            row["plan_id"] = item[kind].get("planId")
        elif kind == "sessionFailed" and isinstance(item.get(kind), dict):
            # Do not persist free-form provider failure text; state/type is enough.
            row["failed"] = True
        compact.append(row)
    return {
        "items": compact,
        "count": len(compact),
        "latest_plan": latest_plan,
        "next_page_token_present": bool(
            isinstance(payload, dict) and payload.get("nextPageToken")
        ),
    }


def build_jules_provider_result(
    *,
    provider_run_id: str,
    raw_status: str | None,
    result_refs: dict[str, Any] | None = None,
    error_code: str | None = None,
    cancel_confirmed: bool | None = None,
) -> ProviderResult:
    status, mapped_error = normalize_jules_status(raw_status)
    refs = deepcopy(result_refs or {})
    result = ProviderResult(
        provider_id="jules-api",
        provider_run_id=provider_run_id,
        normalized_status=status,
        usage={"iterations": 0, "tool_calls": 0},
        result_refs=refs,
        error_category="provider" if status in {"FAILED", "UNKNOWN"} else None,
        error_code=error_code or mapped_error,
        cancel_confirmed=cancel_confirmed,
    )
    return sanitize_provider_result(result)
