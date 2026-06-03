"""Machine-readable JSON evidence for context live invocation benchmarks (#2850).

Aggregates harness matrix output with db-record-evidence claims (#2851).
Read-only: no DB access, no MCP mutations, no writes except optional file export.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from tools.surrealdb import context_live_invocation_harness as harness
from tools.surrealdb.db_record_evidence_contract import (
    ACCEPTED_LIMITATION_CODES,
    SCHEMA_VERSION as CLAIM_SCHEMA_VERSION,
    build_example_claim,
    compute_determinism_hash,
    validate_db_record_evidence_claim,
)

SCHEMA_VERSION = "tool-invocation-evidence/v1"
ISSUE_REF = "2850"

HASH_EXCLUDED_TOP_LEVEL = frozenset(
    {
        "determinism_hash",
        "started_at_or_observed_at",
    }
)

GLOBAL_LIMITATIONS = (
    "bridge_only: MCP stdio path not exercised; handlers invoked via in-process bridge",
    "PERSIST_ALLOWED=false and MUTATION_ALLOWED=false for benchmark runs",
    "no productive SurrealDB writes in this harness slice",
    "LR remains NO-GO; benchmark evidence is not live-capital or LR-GO proof",
)


def _invocation_fingerprint(
    tool_name: str, call: Mapping[str, Any], profile: str
) -> str:
    payload = {"profile": profile, "tool": tool_name, "call": dict(call)}
    return canonical_hash(payload)[:16]


def _stable_run_id(profile: str, git_sha: str) -> str:
    sha = (git_sha or "unknown")[:12]
    return f"context-live-invoke-{profile}-{sha}"


def derive_evidence_final_verdict(report: harness.HarnessReport) -> str:
    """Map harness outcome to machine-readable final_verdict for JSON evidence."""
    if report.final_verdict == "fail":
        return "FAIL"
    limits_count = report.summary.get("PASS_WITH_LIMITS", 0)
    if limits_count > 0 and report.profile == "minimal":
        return "PASS_WITH_LIMITS"
    return "PASS"


def _build_accepted_limitation_claim(
    row: harness.MatrixRow,
    *,
    profile: str,
    git_sha: str,
) -> dict[str, Any]:
    code = row.error_code or "missing_records"
    if code not in ACCEPTED_LIMITATION_CODES:
        code = "missing_records"
    inv_hash = _invocation_fingerprint(row.tool_name, row.call, profile)
    claim = build_example_claim(
        claim_id=f"claim-{profile}-{row.tool_name}",
        claim_type="context_tooling_benchmark",
        claim_text_or_summary=(
            f"Harness {profile} profile: {row.tool_name} returned fail-closed "
            f"{code} without inline records."
        ),
        producer_tool=row.tool_name,
        tool_invocation_id_or_hash=f"inv-{profile}-{row.tool_name}-{inv_hash}",
        query_or_lookup_fingerprint=(
            f"bridge:{row.tool_name}:{profile}:no_inline_records"
        ),
        record_source="in_memory",
        record_ids=[],
        record_hashes_or_content_fingerprints=[],
        record_timestamps_or_freshness_signal="not_applicable",
        repo_crosscheck={
            "path": harness.RATIFICATION_DOC,
            "symbol": "PASS_WITH_LIMITS_ERROR_CODES",
            "commit": (git_sha or "unknown")[:8],
        },
        source_priority="repo_files",
        trust_classification="accepted_limitation",
        limitations=[
            f"status=error code={code} — ACCEPTED_LIMITATION per #2852 ratification",
        ],
        redaction_summary="no sensitive values present",
    )
    violations = validate_db_record_evidence_claim(claim)
    if violations:
        raise ValueError(
            f"accepted_limitation claim for {row.tool_name} invalid: {violations}"
        )
    return claim


def _tool_invocation_row(row: harness.MatrixRow, *, profile: str) -> dict[str, Any]:
    return {
        "tool_name": row.tool_name,
        "invocation_id": _invocation_fingerprint(row.tool_name, row.call, profile),
        "call": row.call,
        "matrix_status": row.status,
        "handler_status": row.handler_status,
        "error_code": row.error_code,
        "limitation_note": row.limitation,
        "invocation_path": row.invocation_path,
        "expected_summary": row.expected,
        "actual_summary": row.actual,
    }


def _accepted_limitations_list(
    rows: list[harness.MatrixRow],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.status != "PASS_WITH_LIMITS":
            continue
        code = row.error_code or "missing_records"
        out.append(
            {
                "tool_name": row.tool_name,
                "error_code": code,
                "matrix_status": row.status,
                "accepted": True,
                "rationale": "PASS_WITH_LIMITS_ERROR_CODES and #2852 ratification",
            }
        )
    return sorted(out, key=lambda item: item["tool_name"])


def _missing_evidence_codes(rows: list[harness.MatrixRow]) -> list[str]:
    codes: set[str] = set()
    for row in rows:
        if row.status == "PASS_WITH_LIMITS" and row.error_code:
            codes.add(row.error_code)
    return sorted(codes)


def _limits_block(report: harness.HarnessReport) -> list[dict[str, str]]:
    items = [
        {"code": "bridge_only", "description": GLOBAL_LIMITATIONS[0]},
        {"code": "safety_gates_default_off", "description": GLOBAL_LIMITATIONS[1]},
        {"code": "no_productive_db_writes", "description": GLOBAL_LIMITATIONS[2]},
        {"code": "lr_no_go", "description": GLOBAL_LIMITATIONS[3]},
    ]
    if report.profile == "minimal":
        items.append(
            {
                "code": "inline_records_absent",
                "description": (
                    "Six Wave-14 tools use minimal fail-closed payloads; "
                    "full profile supplies inline records (#2852)."
                ),
            }
        )
    return items


def hash_payload_for_determinism(document: Mapping[str, Any]) -> dict[str, Any]:
    """Stable subset for aggregate determinism_hash (wall-clock excluded)."""
    return {k: v for k, v in document.items() if k not in HASH_EXCLUDED_TOP_LEVEL}


def compute_aggregate_determinism_hash(document: Mapping[str, Any]) -> str:
    return canonical_hash(hash_payload_for_determinism(document))


def build_invocation_evidence(report: harness.HarnessReport) -> dict[str, Any]:
    """Build the #2850 machine-readable evidence document from a harness report."""
    limit_rows = [r for r in report.matrix if r.status == "PASS_WITH_LIMITS"]
    evidence_claims = [
        _build_accepted_limitation_claim(
            row, profile=report.profile, git_sha=report.git_sha
        )
        for row in sorted(limit_rows, key=lambda r: r.tool_name)
    ]
    tool_invocations = [
        _tool_invocation_row(row, profile=report.profile)
        for row in sorted(report.matrix, key=lambda r: r.tool_name)
    ]
    accepted = _accepted_limitations_list(report.matrix)
    missing_codes = _missing_evidence_codes(report.matrix)
    final_verdict = derive_evidence_final_verdict(report)

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id_or_invocation_id": _stable_run_id(report.profile, report.git_sha),
        "profile": report.profile,
        "final_verdict": final_verdict,
        "started_at_or_observed_at": report.timestamp,
        "tool_invocations": tool_invocations,
        "evidence_claims": evidence_claims,
        "limits": _limits_block(report),
        "accepted_limitations": accepted,
        "missing_evidence_codes": missing_codes,
        "summary_counts": dict(report.summary),
        "redaction_summary": "no sensitive values present; bridge benchmark payloads only",
        "limitations": list(GLOBAL_LIMITATIONS),
        "issue_ref": ISSUE_REF,
        "parent_issue_ref": harness.ISSUE_REF,
        "ratification_doc": report.ratification_doc,
        "claim_schema_version": CLAIM_SCHEMA_VERSION,
        "git_sha": report.git_sha,
        "branch": report.branch,
        "worktree_clean": report.worktree_clean,
        "lr_note": report.lr_note,
        "safety_flags": dict(report.safety_flags),
        "root_inventory": dict(report.root_inventory),
    }
    document["determinism_hash"] = compute_aggregate_determinism_hash(document)
    return document


def serialize_invocation_evidence(
    report: harness.HarnessReport,
    *,
    indent: int | None = 2,
) -> str:
    """Canonical JSON string for CLI and file export."""
    document = build_invocation_evidence(report)
    if indent is None:
        return canonical_json_dumps(document)
    return json.dumps(document, indent=indent, sort_keys=True, ensure_ascii=False)
