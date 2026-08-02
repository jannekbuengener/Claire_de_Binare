"""Offline capability snapshots and drift classification (#4254)."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from tools.agent_execution_contract.jcs import canonicalize

DRIFT_CLASSES = (
    "MATCH",
    "ADDITIVE_COMPATIBLE",
    "BREAKING",
    "MISSING_REQUIRED_CAPABILITY",
    "UNAVAILABLE",
    "UNKNOWN",
    "PUBLIC_BETA_UNVERIFIED",
)

REQUIRED_OPS = ("dispatch", "watch", "cancel")
OPTIONAL_OPS = (
    "stream",
    "resume",
    "follow_up",
    "list_artifacts",
    "download_artifact",
    "get_usage",
    "archive",
    "unarchive",
)
FORBIDDEN_OPS = ("delete",)

_BASELINES: dict[str, dict[str, Any]] = {
    "cursor-sdk": {
        "provider_id": "cursor-sdk",
        "surface": "python-sdk",
        "stability": "public",
        "api_or_sdk_version": "cursor-sdk-public",
        "supported_operations": list(REQUIRED_OPS)
        + ["stream", "resume", "follow_up", "get_usage", "archive", "unarchive"],
        "unsupported_operations": ["delete", "download_artifact"],
        "observed_capabilities": {
            "runtimes": ["local", "cloud"],
            "router_modes": ["cost", "balanced", "intelligence"],
        },
        "limitations": [
            "Optional dependency; base CI must import without cursor-sdk installed.",
            "Billed cost may be delayed/None.",
            "Local artifact download not assumed.",
        ],
    },
    "cursor-cli": {
        "provider_id": "cursor-cli",
        "surface": "headless-cli",
        "stability": "public",
        "api_or_sdk_version": "cursor-agent-cli-public",
        "supported_operations": list(REQUIRED_OPS) + ["stream", "resume"],
        "unsupported_operations": [
            "delete",
            "list_artifacts",
            "download_artifact",
            "archive",
            "unarchive",
            "get_usage",
        ],
        "observed_capabilities": {
            "output_formats": ["text", "json", "stream-json"],
            "force_default": False,
        },
        "limitations": [
            "Write/force modes remain fail-closed; live dispatch never enabled "
            "by environment preflight alone (#4255).",
            "Prompt must travel via stdin, never argv.",
        ],
    },
    "cursor-cloud-api": {
        "provider_id": "cursor-cloud-api",
        "surface": "cloud-agents-api-v1",
        "stability": "public_beta",
        "api_or_sdk_version": "cloud-agents-api-v1-public-beta",
        "supported_operations": list(REQUIRED_OPS) + list(OPTIONAL_OPS),
        "unsupported_operations": ["delete"],
        "observed_capabilities": {
            "streaming": "sse",
            "resume": "Last-Event-ID",
            "stream_expired": "410->get-run",
        },
        "limitations": [
            "Public beta; additive response fields expected.",
            "GET /v1/repositories must not be polled.",
            "Permanent DELETE is never exposed.",
        ],
    },
}


def _digest(payload: dict[str, Any]) -> str:
    material = canonicalize(
        {
            k: v
            for k, v in payload.items()
            if k not in {"capability_digest", "drift_classification"}
        }
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def offline_capability_snapshot(provider_id: str) -> dict[str, Any]:
    if provider_id not in _BASELINES:
        raise KeyError(provider_id)
    base = deepcopy(_BASELINES[provider_id])
    base["drift_classification"] = (
        "PUBLIC_BETA_UNVERIFIED" if base["stability"] == "public_beta" else "MATCH"
    )
    base["capability_digest"] = _digest(base)
    return base


def classify_drift(
    baseline: dict[str, Any],
    observed: dict[str, Any] | None,
) -> str:
    if observed is None:
        return "UNAVAILABLE"
    missing = [
        op
        for op in REQUIRED_OPS
        if op not in set(observed.get("supported_operations") or [])
    ]
    if missing:
        return "MISSING_REQUIRED_CAPABILITY"
    if any(
        op in set(observed.get("supported_operations") or []) for op in FORBIDDEN_OPS
    ):
        return "BREAKING"
    base_ops = set(baseline.get("supported_operations") or [])
    obs_ops = set(observed.get("supported_operations") or [])
    if obs_ops == base_ops:
        return "MATCH"
    if base_ops.issubset(obs_ops):
        return "ADDITIVE_COMPATIBLE"
    if not base_ops.intersection(obs_ops):
        return "UNKNOWN"
    removed = base_ops - obs_ops
    if removed:
        return "BREAKING"
    return "ADDITIVE_COMPATIBLE"


def snapshot_blocks_dispatch(snapshot: dict[str, Any]) -> bool:
    return snapshot.get("drift_classification") in {
        "BREAKING",
        "MISSING_REQUIRED_CAPABILITY",
        "UNAVAILABLE",
        "UNKNOWN",
    }


def byte_identical_snapshots(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(
        b, sort_keys=True, separators=(",", ":")
    )
