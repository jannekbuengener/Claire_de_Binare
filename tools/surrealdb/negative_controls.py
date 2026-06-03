"""Shared negative-control classification for Context/MCP/SurrealDB (#2854).

Read-only helpers: no DB access, no MCP mutations, no persistence.
LR remains NO-GO. Defaults: PERSIST_ALLOWED=False, MUTATION_ALLOWED=False.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal, Mapping

from tools.mcp.memory_write_intent_tools import MUTATION_ALLOWED
from tools.surrealdb.memory_write_gate import PERSIST_ALLOWED

NegativeControlVerdict = Literal["PASS", "BLOCKED_SAFETY", "FAIL"]
InvocationPath = Literal["bridge", "mcp"]

WRITE_INTENT_PASS_CODES = frozenset(
    {
        "agent_memory_write_not_activated",
        "productive_audit_not_activated",
        "local_audit_mcp_not_activated",
        "hg_p_required",
        "operation_mode_invalid",
        "mutation_blocked_by_default",
    }
)

MCP_BLOCKED_SAFETY_CODES = frozenset(
    {
        "blocked_safety",
        "smart_mode_blocked",
        "mcp_mutation_blocked",
        "policy_blocked",
    }
)

MCP_BLOCKED_SAFETY_MESSAGE_MARKERS = (
    "smart mode",
    "blocked_safety",
    "mutation not allowed",
    "write intent blocked",
)

SECRET_SUBSTRINGS_IN_OUTPUT = (
    "SURREAL_PASS",
    "SURREAL_USER",
    "Authorization:",
    "Bearer ",
    "password=",
    "api_key=",
    "secret=",
)

_HUMAN_GO_TOKEN_PATTERN = re.compile(r"GO-\d{4}-\d{2}-\d{2}(?:-[A-Za-z0-9._-]+)?")


def default_safety_flags() -> dict[str, bool]:
    """Module-level safety defaults for harness and regression matrix."""
    return {
        "PERSIST_ALLOWED": bool(PERSIST_ALLOWED),
        "MUTATION_ALLOWED": bool(MUTATION_ALLOWED),
    }


def assert_safety_defaults_off() -> list[str]:
    """Return violation messages when default-off gates are not enforced."""
    violations: list[str] = []
    flags = default_safety_flags()
    if flags["PERSIST_ALLOWED"]:
        violations.append("PERSIST_ALLOWED must remain False in CI/regression")
    if flags["MUTATION_ALLOWED"]:
        violations.append("MUTATION_ALLOWED must remain False in CI/regression")
    return violations


def _extract_code(result: Mapping[str, Any]) -> str | None:
    err = result.get("error")
    if isinstance(err, dict):
        code = err.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    code_top = result.get("code")
    if isinstance(code_top, str) and code_top.strip():
        return code_top.strip()
    return None


def _extract_message(result: Mapping[str, Any]) -> str:
    err = result.get("error")
    if isinstance(err, dict):
        msg = err.get("message")
        if isinstance(msg, str):
            return msg
    msg_top = result.get("message")
    return str(msg_top) if msg_top is not None else ""


def classify_memory_write_intent_negative_control(
    result: Mapping[str, Any],
    *,
    invocation_path: InvocationPath = "bridge",
) -> NegativeControlVerdict:
    """Classify write-intent negative-control outcomes (bridge vs MCP policy path)."""
    status = result.get("status")
    code = _extract_code(result)
    message = _extract_message(result).lower()

    if status == "ok":
        gate = result.get("result")
        if isinstance(gate, dict):
            gate_status = gate.get("gate_status")
            if gate_status == "approved_dry_run":
                return "PASS"
        return "FAIL"

    if invocation_path == "mcp":
        if code in MCP_BLOCKED_SAFETY_CODES:
            return "BLOCKED_SAFETY"
        if any(marker in message for marker in MCP_BLOCKED_SAFETY_MESSAGE_MARKERS):
            return "BLOCKED_SAFETY"
        if status == "error" and code not in WRITE_INTENT_PASS_CODES:
            return "BLOCKED_SAFETY"

    if status == "refused":
        if code in WRITE_INTENT_PASS_CODES or code is None:
            return "PASS"
        return "PASS"

    if code in WRITE_INTENT_PASS_CODES:
        return "PASS"

    if code == "mutation_blocked_by_default":
        return "PASS"

    if status in ("refused", "error") and code:
        return "PASS"

    return "FAIL"


def refusal_output_is_safe(payload: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Ensure refusal/error payloads do not leak secrets or raw GO tokens."""
    serialized = json.dumps(payload, default=str)
    issues: list[str] = []
    if '"human_go_token"' in serialized:
        issues.append("raw human_go_token field in output")
    for match in _HUMAN_GO_TOKEN_PATTERN.findall(serialized):
        if match.startswith("GO-"):
            issues.append("raw GO token pattern in output")
            break
    upper = serialized.upper()
    for marker in SECRET_SUBSTRINGS_IN_OUTPUT:
        if marker.upper() in upper:
            issues.append(f"forbidden substring {marker!r} in output")
    return (len(issues) == 0, issues)


def negative_control_matrix_summary() -> dict[str, Any]:
    """Machine-readable matrix index for harness evidence exports."""
    from tools.surrealdb.negative_controls_matrix import NEGATIVE_CONTROL_MATRIX

    rows = [
        {
            "case_id": case.case_id,
            "category": case.category,
            "expected_verdict": case.expected_verdict,
            "invocation_path": case.invocation_path,
            "issue_ref": "2854",
        }
        for case in NEGATIVE_CONTROL_MATRIX
    ]
    return {
        "schema": "negative-controls-matrix/v1",
        "issue_ref": "2854",
        "parent_issue_ref": "2847",
        "safety_flags": default_safety_flags(),
        "cases": rows,
    }
