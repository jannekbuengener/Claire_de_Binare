"""Shared Cursor normalization, redaction, and route guards (#4254)."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import (
    PROVIDER_STATUSES,
    ProviderResult,
    sanitize_provider_result,
)

CURSOR_STATUS_MAP = {
    "CREATING": "QUEUED",
    "QUEUED": "QUEUED",
    "RUNNING": "RUNNING",
    "FINISHED": "SUCCEEDED",
    "ERROR": "FAILED",
    "CANCELLED": "CANCELLED",
    "CANCELED": "CANCELLED",
    "EXPIRED": "FAILED",
}

ROUTER_OPTIMIZE_FOR = frozenset({"cost", "balanced", "intelligence"})
ROUTER_MODEL_ID = "auto-smart"

_AUTH_KEY = re.compile(
    r"(?i)^(authorization|cookie|x-api-key|api[-_]?key|token|secret|password)$"
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+\S+")
_CRSR = re.compile(r"\bcrsr_[A-Za-z0-9_\-]{8,}\b")
_PRESIGNED = re.compile(r"(?i)[?&](X-Amz-Signature|Signature|token)=|presigned")


def normalize_cursor_status(raw: str | None) -> tuple[str, str | None]:
    if raw is None:
        return "UNKNOWN", None
    key = str(raw).strip().upper()
    if key == "EXPIRED":
        return "FAILED", "PROVIDER_RUN_EXPIRED"
    mapped = CURSOR_STATUS_MAP.get(key)
    if mapped is None:
        return "UNKNOWN", "PROVIDER_STATUS_UNKNOWN"
    return mapped, None


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _AUTH_KEY.match(str(key)):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = redact_value(item)
        return out
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        text = value
        text = _BEARER.sub(lambda m: m.group(1) + " [REDACTED]", text)
        text = _CRSR.sub("[REDACTED_CRSR_TOKEN]", text)
        if _PRESIGNED.search(text):
            return "[REDACTED_PRESIGNED_URL]"
        return text
    return value


def ensure_no_secret_leak(payload: Any) -> None:
    redacted = redact_value(payload)
    # If redaction changed anything meaningful for secret-like patterns, reject.
    serialized = str(payload)
    if (
        _CRSR.search(serialized)
        or _BEARER.search(serialized)
        or _PRESIGNED.search(serialized)
    ):
        raise DispatchError(
            "HOLD_SECRET_BOUNDARY_NOT_PROVEN",
            "secret-like value leaked into provider payload",
        )
    _ = redacted


def normalize_usage(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    usage: dict[str, Any] = {
        "iterations": int(raw.get("iterations") or 0),
        "tool_calls": int(raw.get("tool_calls") or 0),
    }
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_tokens",
        "total_tokens",
    ):
        if key in raw and raw[key] is not None:
            usage[key] = int(raw[key])
    if "cost" in raw:
        usage["cost"] = raw["cost"]  # may be None
    return usage


def validate_artifact_path(path: str) -> str:
    text = path.replace("\\", "/").lstrip("/")
    if text.startswith("..") or "/../" in f"/{text}/" or text.startswith("/"):
        raise DispatchError(
            "PROVIDER_ARTIFACT_TRAVERSAL", f"invalid artifact path: {path!r}"
        )
    if not text.startswith("artifacts/"):
        raise DispatchError(
            "PROVIDER_ARTIFACT_PATH",
            "artifact path must be under artifacts/",
        )
    return text


def _pr_url_matches_target(pr_url: str, contract_target_pr: int) -> bool:
    """Match the complete pull-request path segment (avoid /12 matching /123)."""
    pattern = re.compile(rf"(?:^|/)pull/{int(contract_target_pr)}(?:/|$|[?#])")
    return pattern.search(pr_url) is not None


def guard_cloud_route_binding(
    *,
    auto_create_pr: bool,
    work_on_current_branch: bool,
    pr_url: str | None,
    contract_target_pr: int | None,
    contract_target_branch: str | None,
) -> None:
    if auto_create_pr:
        raise DispatchError(
            "PROVIDER_ROUTE_AUTOPR_FORBIDDEN",
            "autoCreatePR must remain false",
        )
    if work_on_current_branch:
        if not contract_target_pr or not contract_target_branch or not pr_url:
            raise DispatchError(
                "PROVIDER_ROUTE_BINDING_MISSING",
                "workOnCurrentBranch requires bound target PR/branch/prUrl",
            )
        # prUrl must reference the exact contract target PR number.
        if not _pr_url_matches_target(pr_url, int(contract_target_pr)):
            raise DispatchError(
                "PROVIDER_ROUTE_TARGET_CONFLICT",
                "prUrl does not match contract target_pr",
            )


def validate_router_selection(
    catalog: dict[str, Any],
    *,
    model_id: str,
    optimize_for: str,
) -> None:
    if model_id != ROUTER_MODEL_ID:
        raise DispatchError(
            "PROVIDER_ROUTER_MODEL",
            f"unsupported model_id {model_id!r}; expected {ROUTER_MODEL_ID}",
        )
    if optimize_for not in ROUTER_OPTIMIZE_FOR:
        raise DispatchError(
            "PROVIDER_ROUTER_MODE",
            f"unsupported optimize_for {optimize_for!r}",
        )
    models = set(catalog.get("model_ids") or [])
    params = set(catalog.get("optimize_for") or [])
    if ROUTER_MODEL_ID not in models or optimize_for not in params:
        raise DispatchError(
            "PROVIDER_ROUTER_CATALOG",
            "router mode not present in model catalog",
        )


def build_provider_result(
    *,
    provider_id: str,
    provider_run_id: str,
    raw_status: str | None,
    usage: dict[str, Any] | None = None,
    result_refs: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_category: str | None = None,
    delivery_receipt: dict[str, Any] | None = None,
    cancel_confirmed: bool | None = None,
) -> ProviderResult:
    status, mapped_error = normalize_cursor_status(raw_status)
    refs = redact_value(deepcopy(result_refs or {}))
    ensure_no_secret_leak(refs)
    result = ProviderResult(
        provider_id=provider_id,
        provider_run_id=provider_run_id,
        normalized_status=status if status in PROVIDER_STATUSES else "UNKNOWN",
        usage=normalize_usage(usage),
        result_refs=refs,
        error_category=error_category
        or ("provider" if status in {"FAILED", "UNKNOWN"} else None),
        error_code=error_code or mapped_error,
        delivery_receipt=deepcopy(delivery_receipt),
        cancel_confirmed=cancel_confirmed,
    )
    return sanitize_provider_result(result)


def host_is_api_cursor(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host.lower() == "api.cursor.com"
