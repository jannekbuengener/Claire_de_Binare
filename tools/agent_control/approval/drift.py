"""Policy / prompt / adapter / protection-view drift audit (#4257)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.agent_control.approval.codes import DIGEST_PREFIX, DRIFT_STATUSES
from tools.agent_execution_contract.jcs import canonicalize_bytes


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
    """Return drift status and individual sources. Missing baseline → UNKNOWN."""
    if baseline is None:
        return {
            "status": "UNKNOWN",
            "sources": ["UNKNOWN"],
            "details": ["baseline missing"],
        }

    sources: list[str] = []
    details: list[str] = []

    expected_policy_hash = baseline.get("expected_policy_content_sha256")
    if isinstance(expected_policy_hash, str) and expected_policy_hash:
        if expected_policy_hash != policy.get("content_sha256"):
            sources.append("POLICY")
            details.append("policy content_sha256 mismatch")
    expected_policy_version = baseline.get("expected_policy_version")
    if isinstance(expected_policy_version, str) and expected_policy_version:
        if expected_policy_version != policy.get("version"):
            if "POLICY" not in sources:
                sources.append("POLICY")
            details.append("policy version mismatch")

    expected_prompt_hash = baseline.get("expected_prompt_content_sha256")
    if isinstance(expected_prompt_hash, str) and expected_prompt_hash:
        if expected_prompt_hash != prompt.get("content_sha256"):
            sources.append("PROMPT")
            details.append("prompt content_sha256 mismatch")
    expected_prompt_version = baseline.get("expected_prompt_version")
    if isinstance(expected_prompt_version, str) and expected_prompt_version:
        if expected_prompt_version != prompt.get("version"):
            if "PROMPT" not in sources:
                sources.append("PROMPT")
            details.append("prompt version mismatch")

    adapter = (
        snapshot.get("adapter") if isinstance(snapshot.get("adapter"), dict) else {}
    )
    expected_fp = baseline.get("capability_fingerprint")
    observed_fp = adapter.get("capability_fingerprint")
    if isinstance(expected_fp, str) and expected_fp:
        if observed_fp != expected_fp:
            sources.append("ADAPTER")
            details.append("adapter capability_fingerprint mismatch")

    expected_prot = baseline.get("protection_view_fingerprint")
    if isinstance(expected_prot, str) and expected_prot:
        protection = (
            snapshot.get("protection")
            if isinstance(snapshot.get("protection"), dict)
            else {}
        )
        observed_prot = protection_view_fingerprint(protection)
        if observed_prot != expected_prot:
            sources.append("PROTECTION_VIEW")
            details.append("protection view fingerprint mismatch")

    if not sources:
        status = "NONE"
    else:
        # Prefer first concrete source; never collapse UNKNOWN into NONE.
        status = sources[0]
        if status not in DRIFT_STATUSES:
            status = "UNKNOWN"

    return {"status": status, "sources": sources, "details": details}
