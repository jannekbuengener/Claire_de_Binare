"""Policy / prompt / adapter / protection-view drift audit (#4257)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.agent_control.approval.codes import DIGEST_PREFIX, DRIFT_STATUSES
from tools.agent_execution_contract.jcs import canonicalize_bytes

_REQUIRED_BASELINE_FIELDS = (
    "expected_policy_content_sha256",
    "expected_prompt_content_sha256",
    "expected_policy_version",
    "expected_prompt_version",
    "capability_fingerprint",
    "protection_view_fingerprint",
)


def load_baseline(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def protection_view_fingerprint(protection: dict[str, Any] | None) -> str:
    material = canonicalize_bytes(protection or {})
    return f"{DIGEST_PREFIX}{hashlib.sha256(material).hexdigest()}"


def audit_drift(
    *,
    policy: dict[str, Any],
    prompt: dict[str, Any],
    snapshot: dict[str, Any],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return drift status and individual sources. Missing/incomplete → UNKNOWN."""
    if baseline is None:
        return {
            "status": "UNKNOWN",
            "sources": ["UNKNOWN"],
            "details": ["baseline missing"],
        }

    missing_fields = [
        field
        for field in _REQUIRED_BASELINE_FIELDS
        if not isinstance(baseline.get(field), str)
        or not str(baseline.get(field)).strip()
    ]
    if missing_fields:
        return {
            "status": "UNKNOWN",
            "sources": ["UNKNOWN"],
            "details": [f"baseline incomplete: missing {', '.join(missing_fields)}"],
        }

    sources: list[str] = []
    details: list[str] = []

    if baseline["expected_policy_content_sha256"] != policy.get("content_sha256"):
        sources.append("POLICY")
        details.append("policy content_sha256 mismatch")
    if baseline["expected_policy_version"] != policy.get("version"):
        if "POLICY" not in sources:
            sources.append("POLICY")
        details.append("policy version mismatch")

    if baseline["expected_prompt_content_sha256"] != prompt.get("content_sha256"):
        sources.append("PROMPT")
        details.append("prompt content_sha256 mismatch")
    if baseline["expected_prompt_version"] != prompt.get("version"):
        if "PROMPT" not in sources:
            sources.append("PROMPT")
        details.append("prompt version mismatch")

    adapter = (
        snapshot.get("adapter") if isinstance(snapshot.get("adapter"), dict) else {}
    )
    if adapter.get("capability_fingerprint") != baseline["capability_fingerprint"]:
        sources.append("ADAPTER")
        details.append("adapter capability_fingerprint mismatch")

    protection = (
        snapshot.get("protection")
        if isinstance(snapshot.get("protection"), dict)
        else {}
    )
    observed_prot = protection_view_fingerprint(protection)
    if observed_prot != baseline["protection_view_fingerprint"]:
        sources.append("PROTECTION_VIEW")
        details.append("protection view fingerprint mismatch")

    if not sources:
        status = "NONE"
    else:
        status = sources[0]
        if status not in DRIFT_STATUSES:
            status = "UNKNOWN"

    return {"status": status, "sources": sources, "details": details}
