"""Stop Condition Resolver v1 — side-effect-free domain component.

Issues:
    #2107 — Implement stop condition resolver v1
    Parent: #2103
    Epic: #1976

This module implements a minimal, deterministic, fail-closed Stop Condition
Resolver. It maps flat stop-condition strings (S1-S10, H1-H8) from the
action-readiness contract to typed stop condition objects with type, severity,
reason, required_action, and human_go_required.

Design intent:
    Pure domain logic. No DB access. No MCP. No networking.
    Input: list of strings + optional context. Output: list of typed dicts.
    Deterministic: same inputs → same outputs.
    Fail-closed: unknown conditions → scope_drift_risk + warning.
"""

from __future__ import annotations

import re

from typing import Any

_STOP_RULE_MAP: dict[str, tuple[str, str]] = {
    "S1": ("scope_drift_risk", "blocking"),
    "S2": ("missing_context", "blocking"),
    "S3": ("missing_context", "blocking"),
    "S4": ("missing_evidence", "blocking"),
    "S5": ("scope_drift_risk", "blocking"),
    "S6": ("write_requires_human_go", "blocking"),
    "S7": ("trading_surface_touched", "blocking"),
    "S8": ("forbidden_path", "blocking"),
    "S9": ("contradiction_risk", "warning"),
    "S10": ("stale_context", "warning"),
}

_HUMAN_GO_MAP: dict[str, tuple[str, str]] = {
    "H1": ("write_requires_human_go", "blocking"),
    "H2": ("runtime_surface_touched", "blocking"),
    "H3": ("write_requires_human_go", "blocking"),
    "H4": ("write_requires_human_go", "blocking"),
    "H5": ("write_requires_human_go", "blocking"),
    "H6": ("trading_surface_touched", "warning"),
    "H7": ("scope_drift_risk", "warning"),
    "H8": ("forbidden_path", "blocking"),
}

_SECRETS_KEYWORDS = (
    "secrets", "tresor", "token", "private-key",
    "secret", "credential", "password",
)

_SECRETS_BOUNDARY_PATTERNS = (
    r"\bapi[_\s]?key\b",
    r"\bsecret[_\s]?key\b",
    r"\baccess[_\s]?key\b",
    r"\bauth[_\s]?key\b",
    r"\bprivate[_\s]key\b",
    r"\bcrypto[_\s]?key\b",
)

_LIVE_KEYWORDS = (
    "echtgeld", "production deploy", "go-live",
    "live readiness", "lr-go", "live trading authorization",
)

_LIVE_BOUNDARY_PATTERNS = (
    r"\blive\b",
)

_REQUIRED_ACTIONS: dict[str, str] = {
    "missing_context": (
        "Resolve missing context before proceeding. "
        "Identify the absent input or read and close the gap."
    ),
    "missing_evidence": (
        "Resolve missing evidence before proceeding. "
        "Back every core assumption with a traceable evidence ref."
    ),
    "scope_drift_risk": (
        "Clarify scope before proceeding. "
        "Ensure task_scope, target_issue, and target_paths are consistent."
    ),
    "runtime_surface_touched": (
        "Stop. Runtime access requires explicit Human-GO. "
        "Do not modify services, containers, or processes without approval."
    ),
    "trading_surface_touched": (
        "Stop. Trading/Risk/Execution surface requires explicit Human-GO. "
        "Do not place orders, modify risk controls, or touch execution paths."
    ),
    "write_requires_human_go": (
        "Stop. All write actions require explicit Human-GO. "
        "Do not write files, push commits, or mutate state without approval."
    ),
    "stale_context": (
        "Re-read canonical control surfaces before proceeding. "
        "Verify CONTROL_REGISTER, CURRENT_STATUS, and LR-AUDIT-STATUS."
    ),
    "contradiction_risk": (
        "Resolve the contradiction before proceeding. "
        "Cross-reference governance documents and escalate to human."
    ),
    "forbidden_path": (
        "Stop immediately. This path is forbidden. "
        "Live/Echtgeld claims, LR-Go assertions, or governance bypass "
        "attempts are not permitted without explicit human authorization."
    ),
    "secrets_risk": (
        "Stop immediately. Secrets risk detected. "
        "Never expose, log, or commit secrets. Validate inputs for "
        "tresor-zone, token, credential, or key references."
    ),
}


_REASONS: dict[str, str] = {
    "S1": "Task scope is missing, empty, or ambiguous.",
    "S2": "Context Package is absent and required reads are incomplete.",
    "S3": "One or more minimum required reads are unavailable.",
    "S4": "Core assumptions lack evidence (evidence_refs empty or untraceable).",
    "S5": "Scope Drift detected: the task diverges from task_scope or target issue.",
    "S6": "Write operation requested without impact report and Human-GO.",
    "S7": "Task touches Trading, Risk, or Execution scope without explicit governance approval.",
    "S8": "Task makes or implies Live-Readiness or Echtgeld claims outside of LR SSOT.",
    "S9": "A material uncertainty exists in Governance scope (Constitution, Policy, Invariant).",
    "S10": "A STOP signal is encountered in canonical control surfaces.",
    "H1": "Any file write requires explicit Human-GO.",
    "H2": "Any Runtime or DB mutation requires explicit Human-GO.",
    "H3": "Any MCP live write requires explicit Human-GO.",
    "H4": "Posting an issue comment requires explicit Human-GO.",
    "H5": "Creating or merging a PR requires explicit Human-GO.",
    "H6": "Action touches Trading, Risk, Execution, or Strategy scope.",
    "H7": "Cross-agent memory handoff beyond read-only context sharing.",
    "H8": "Claim or statement about Live-Readiness or Echtgeld status.",
}


def _parse_rule_ref(raw: str) -> str | None:
    """Extract the rule reference (S1-S10 or H1-H8) from a condition string.

    Matches patterns like:
        "S1: scope ambiguous"
        "S8: live/echtgeld claims outside LR SSOT"
        "H1: write action requires explicit Human-GO"
    """
    stripped = raw.strip()
    if not stripped:
        return None
    upper = stripped.upper()
    for prefix in ("S10", "S9", "S8", "S7", "S6", "S5", "S4", "S3", "S2", "S1",
                   "H8", "H7", "H6", "H5", "H4", "H3", "H2", "H1"):
        if upper.startswith(prefix) and (len(stripped) == len(prefix) or
                                         stripped[len(prefix)] in (":", " ")):
            return prefix
    return None


def _check_secrets_keyword(text: str) -> bool:
    """Check if the text contains a secrets-related keyword.

    Uses substring matching for unambiguous keywords and word-boundary
    regex for ambiguous tokens like 'key' (to avoid false positives
    on 'monkeypatch', 'keyboard', 'key_result', etc.).
    """
    lower = text.lower()
    for kw in _SECRETS_KEYWORDS:
        if kw in lower:
            return True
    for pattern in _SECRETS_BOUNDARY_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def _check_live_keyword(text: str) -> bool:
    """Check if the text contains a live/echtgeld keyword.

    Multi-word phrases match as substrings. The bare 'live' token uses
    word-boundary matching to avoid false positives on words like
    'deliverable', 'relative', 'liveable'.
    """
    lower = text.lower()
    for kw in _LIVE_KEYWORDS:
        if kw in lower:
            return True
    for pattern in _LIVE_BOUNDARY_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def _check_runtime_keyword(text: str) -> bool:
    """Check if the text references runtime surfaces."""
    lower = text.lower()
    runtime_kw = ("runtime", "service", "container", "process", "docker", "compose")
    return any(kw in lower for kw in runtime_kw)


def _is_write_mode(operation_mode: str) -> bool:
    """Determine if the operation mode is write-capable."""
    if not isinstance(operation_mode, str):
        return False
    return operation_mode.lower().startswith("write")


def _determine_severity(
    rule_ref: str | None,
    condition_type: str,
    operation_mode: str,
    has_secrets: bool,
    has_live: bool,
) -> str:
    """Determine severity, potentially adjusting based on context."""
    if has_secrets:
        return "blocking"
    if has_live:
        return "blocking"

    # Look up baseline severity from rule maps
    if rule_ref in _STOP_RULE_MAP:
        base_type, base_severity = _STOP_RULE_MAP[rule_ref]
        if rule_ref == "S7" and not _is_write_mode(operation_mode):
            return "warning"
        return base_severity
    if rule_ref in _HUMAN_GO_MAP:
        base_type, base_severity = _HUMAN_GO_MAP[rule_ref]
        return base_severity
    return "warning"


def _build_condition(
    raw: str,
    rule_ref: str | None,
    condition_type: str,
    severity: str,
    is_write: bool,
) -> dict[str, Any]:
    """Build a typed stop condition dict."""
    reason = (
        _REASONS.get(rule_ref, f"Unknown or unmapped stop condition: {raw}")
        if rule_ref
        else f"Unknown or unmapped stop condition: {raw}"
    )
    required_action = _REQUIRED_ACTIONS.get(
        condition_type,
        "Stop and report this condition to the human operator.",
    )

    human_go_required = (
        severity == "blocking"
        or condition_type in (
            "write_requires_human_go",
            "forbidden_path",
            "secrets_risk",
            "trading_surface_touched",
            "runtime_surface_touched",
        )
    )

    return {
        "type": condition_type,
        "severity": severity,
        "reason": reason,
        "required_action": required_action,
        "human_go_required": human_go_required,
    }


def resolve_stop_conditions(
    stop_conditions: list[str] | None = None,
    warnings: list[str] | None = None,
    readiness_result: dict[str, Any] | None = None,
    operation_mode: str = "read_only",
) -> list[dict[str, Any]]:
    """Resolve flat stop-condition strings to typed stop condition objects.

    Args:
        stop_conditions: List of stop condition strings (S1-S10, H1-H8 patterns).
        warnings: Optional list of warning strings to scan for secrets/live keywords.
        readiness_result: Optional readiness result from context.readiness.
        operation_mode: One of read_only, dry_run, write (code/docs), etc.

    Returns:
        List of typed stop condition dicts with type, severity, reason,
        required_action, and human_go_required.

    Deterministic: same inputs produce the same outputs.
    Fail-closed: unknown conditions → scope_drift_risk + warning.
    """
    resolved: list[dict[str, Any]] = []

    conditions = list(stop_conditions) if isinstance(stop_conditions, list) else []
    warning_list = list(warnings) if isinstance(warnings, list) else []
    is_write = _is_write_mode(operation_mode)

    # Scan warnings for secrets/live keywords and add as conditions
    _warning_text = " ".join(warning_list).lower()
    if _check_secrets_keyword(_warning_text):
        conditions.append("SECRETS_RISK: secrets/tresor/credential detected in warnings")
    if _check_live_keyword(_warning_text):
        conditions.append("FORBIDDEN_PATH: live/echtgeld keywords in warnings")
    if _check_runtime_keyword(_warning_text):
        conditions.append("RUNTIME_SURFACE: runtime references in warnings")

    # Collect conditions from readiness_result if provided
    if isinstance(readiness_result, dict):
        readiness_conditions = readiness_result.get("stop_conditions", [])
        if isinstance(readiness_conditions, list):
            for sc in readiness_conditions:
                if isinstance(sc, str) and sc.strip():
                    conditions.append(sc)

    # Deduplicate while preserving order (first occurrence wins)
    seen: set[str] = set()
    unique_conditions: list[str] = []
    for sc in conditions:
        if not isinstance(sc, str) or not sc.strip():
            continue
        canonical = sc.strip()
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            unique_conditions.append(canonical)

    # Process each condition
    for raw in unique_conditions:
        rule_ref = _parse_rule_ref(raw)
        has_secrets = _check_secrets_keyword(raw)
        has_live = _check_live_keyword(raw)

        if has_secrets and not (rule_ref and rule_ref in _STOP_RULE_MAP):
            condition = _build_condition(
                raw, rule_ref, "secrets_risk", "blocking", is_write
            )
            resolved.append(condition)
            continue

        if has_live and not rule_ref:
            condition = _build_condition(
                raw, rule_ref, "forbidden_path", "blocking", is_write
            )
            resolved.append(condition)
            continue

        if rule_ref:
            if rule_ref in _STOP_RULE_MAP:
                condition_type, _ = _STOP_RULE_MAP[rule_ref]
            elif rule_ref in _HUMAN_GO_MAP:
                condition_type, _ = _HUMAN_GO_MAP[rule_ref]
            else:
                condition_type = "scope_drift_risk"

            severity = _determine_severity(
                rule_ref, condition_type, operation_mode, has_secrets, has_live
            )
            condition = _build_condition(
                raw, rule_ref, condition_type, severity, is_write
            )
            resolved.append(condition)
        else:
            # Unknown pattern – scanning for additional keyword hints
            if _check_runtime_keyword(raw):
                condition = _build_condition(
                    raw, None, "runtime_surface_touched", "warning", is_write
                )
            else:
                condition = _build_condition(
                    raw, None, "scope_drift_risk", "warning", is_write
                )
            resolved.append(condition)

    return resolved
