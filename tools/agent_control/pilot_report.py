"""Deterministic cdb.agent_control_pilot_report.v1 envelope (#4258 foundation).

Orchestration-only: references existing digests; never a second evidence truth.
Does not authorize merge, publish, live agents, or issue closure.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.agent_control.errors import AgentControlError
from tools.agent_control.paths import REPO_ROOT
from tools.agent_execution_contract.jcs import canonicalize_bytes

REPORT_SCHEMA_ID = "cdb.agent_control_pilot_report.v1"
REPORT_SCHEMA_VERSION = "1.0.0"
REPORT_SCHEMA_RELPATH = "docs/contracts/cdb_agent_control_pilot_report.v1.schema.json"
DIGEST_PREFIX = "sha256:"

FINAL_STATUSES = frozenset({"PASS", "HOLD", "BLOCKED", "FAIL", "UNKNOWN"})

AUTHORITY_LIMITS = {
    "merge": False,
    "publish_cdb_local_ci": False,
    "modify_branch_protection": False,
    "modify_rulesets": False,
    "execute_live_agent": False,
    "live_go": False,
    "real_money_go": False,
    "close_issue": False,
}

_NON_DIGEST_KEYS = frozenset({"observed_at", "wall_clock", "generated_at"})


class PilotReportError(AgentControlError):
    """Pilot report validation / digest error."""


def load_report_schema(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    path = root / REPORT_SCHEMA_RELPATH
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_digest_fields(report: dict[str, Any]) -> dict[str, Any]:
    """Material for hashing: exclude digest fields and integrity envelope entirely.

    Integrity metadata is attached after hashing (same pattern as approval
    context: digest fields must not feed the digest).
    """
    payload = copy.deepcopy(report)
    payload.pop("report_digest", None)
    payload.pop("integrity", None)
    for key in _NON_DIGEST_KEYS:
        payload.pop(key, None)
    meta = payload.get("metadata")
    if isinstance(meta, dict):
        meta = {k: v for k, v in meta.items() if k not in _NON_DIGEST_KEYS}
        if meta:
            payload["metadata"] = meta
        else:
            payload.pop("metadata", None)
    return payload


def compute_report_digest(report: dict[str, Any]) -> str:
    material = canonicalize_bytes(_strip_digest_fields(report))
    return f"{DIGEST_PREFIX}{hashlib.sha256(material).hexdigest()}"


def attach_report_digest(report: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(report)
    digest = compute_report_digest(out)
    out["report_digest"] = digest
    integrity = dict(out.get("integrity") or {})
    integrity.update(
        {
            "canonicalization": "RFC8785",
            "digest": digest,
            "digest_algorithm": "sha256",
            "digest_encoding": "sha256:<lowercase-hex>",
        }
    )
    out["integrity"] = integrity
    return out


def validate_report(
    report: dict[str, Any], *, schema: dict[str, Any] | None = None
) -> None:
    if not isinstance(report, dict):
        raise PilotReportError("PILOT_REPORT_TYPE_INVALID", "report must be an object")
    sch = schema or load_report_schema()
    validator = Draft202012Validator(sch)
    errors = sorted(validator.iter_errors(report), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        path = ".".join(str(p) for p in err.path) or "$"
        raise PilotReportError("PILOT_REPORT_SCHEMA_INVALID", f"{path}: {err.message}")
    status = report.get("final_status")
    if status not in FINAL_STATUSES:
        raise PilotReportError(
            "PILOT_REPORT_STATUS_INVALID",
            f"final_status {status!r} not allowed",
        )
    if status == "PASS" and report.get("final_status") == "UNKNOWN":
        raise PilotReportError("PILOT_REPORT_UNKNOWN_PASS", "UNKNOWN cannot be PASS")
    limits = report.get("authority_limits") or {}
    for key, expected in AUTHORITY_LIMITS.items():
        if limits.get(key) is not expected:
            raise PilotReportError(
                "PILOT_REPORT_AUTHORITY_VIOLATION",
                f"authority_limits.{key} must be {expected}",
            )


def verify_report(
    report: dict[str, Any], *, schema: dict[str, Any] | None = None
) -> dict[str, Any]:
    validate_report(report, schema=schema)
    expected = compute_report_digest(report)
    actual = report.get("report_digest") or (report.get("integrity") or {}).get(
        "digest"
    )
    if actual != expected:
        raise PilotReportError(
            "PILOT_REPORT_DIGEST_MISMATCH",
            f"report_digest mismatch: got {actual!r} expected {expected!r}",
        )
    return {
        "ok": True,
        "report_digest": expected,
        "final_status": report["final_status"],
    }


def build_report(
    *,
    pilot_id: str,
    scenario_id: str,
    subject: dict[str, Any],
    contract_versions: dict[str, str],
    run_id: str | None,
    attempt: int | None,
    head_sha: str,
    input_digests: dict[str, Any],
    step_results: list[dict[str, Any]],
    provider_call_count: int,
    run_evidence_refs: list[dict[str, Any]],
    approval_context_digest: str | None,
    approval_recommendation: str | None,
    final_status: str,
    limitations: list[str],
) -> dict[str, Any]:
    if final_status == "UNKNOWN":
        # Fail-closed: UNKNOWN must never be remapped to PASS by callers.
        pass
    if final_status not in FINAL_STATUSES:
        raise PilotReportError(
            "PILOT_REPORT_STATUS_INVALID",
            f"final_status {final_status!r} not allowed",
        )
    if final_status == "PASS" and any(
        step.get("status") == "UNKNOWN" for step in step_results
    ):
        raise PilotReportError(
            "PILOT_REPORT_UNKNOWN_PASS",
            "cannot emit PASS when a step status is UNKNOWN",
        )
    report: dict[str, Any] = {
        "schema_id": REPORT_SCHEMA_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "pilot_id": pilot_id,
        "scenario_id": scenario_id,
        "subject": {
            "head_sha": head_sha,
            "base_sha": subject.get("base_sha"),
            "issue": subject.get("issue", 4258),
            "pr_number": subject.get("pr_number"),
        },
        "contract_versions": contract_versions,
        "run_id": run_id,
        "attempt": attempt,
        "head_sha": head_sha,
        "input_digests": input_digests,
        "step_results": step_results,
        "provider_call_count": provider_call_count,
        "run_evidence_refs": run_evidence_refs,
        "approval_context_digest": approval_context_digest,
        "approval_recommendation": approval_recommendation,
        "authority_limits": copy.deepcopy(AUTHORITY_LIMITS),
        "final_status": final_status,
        "limitations": list(limitations),
    }
    report = attach_report_digest(report)
    validate_report(report)
    return report
