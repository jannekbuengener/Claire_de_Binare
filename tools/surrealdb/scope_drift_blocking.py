"""Blocking Scope Drift Output Helper — Wave 17-D.

Issues:
    #2166 — [SURREALDB][CONTEXT][SCOPE-BLOCKING] Blocking Scope Drift Output
    Parent: #2162 (Wave-17 anchor)
    Depends on: #2163 (scope_drift_firewall, merged via PR #2376)
    Epic: #1976

Scope:
    Standardised blocking-output helper for Scope Drift findings.
    Produces the full #2166 output schema so that Operator and Agent
    can clearly see:
        - why execution is being stopped
        - which artefacts are affected
        - which guardrails apply
        - which next reads are recommended
        - which operator action is expected
        - that no auto-fixes or auto-writes are permitted

    This module is read-only, side-effect-free, and purely in-memory.
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No auto-fix. No auto-write. No live-go. No Echtgeld-Go.

Output schema (produced by ``build_blocking_output``):
    status                  str — scan status from ScopeDriftScanResult
    blocking                bool — True iff blocking_count > 0
    blocking_count          int — number of blocking findings
    summary                 str — human-readable summary line
    operator_action         str — one of: stop, review, split_scope, request_human_go
    affected_artifacts      list[str] — sorted, deduplicated
    recommended_next_reads  list[str] — stable-order, deduplicated
    guardrails              list[str] — all guardrails from the scan result
    findings                list[dict] — blocking findings only (to_dict())
    anti_actions            list[str] — explicit prohibitions (always present)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from tools.surrealdb.scope_drift_firewall import ScopeDriftFinding, ScopeDriftScanResult

# ── Constants ─────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "scope-drift-blocking/v1"

# Explicit prohibitions — always present in blocking output regardless of findings.
ANTI_ACTIONS: tuple[str, ...] = (
    "no_auto_fix",
    "no_auto_write",
    "no_auto_merge",
    "no_auto_close",
    "no_live_go",
    "no_lr_go",
    "no_echtgeld_go",
    "no_runtime_enable",
)

# Operator-action priority — lower value = higher priority (stop wins).
# Maps internal required_action values to canonical output operator_action labels.
_ACTION_LABEL: dict[str, str] = {
    "stop": "stop",
    "request_go": "request_human_go",
    "split_scope": "split_scope",
    "review": "review",
}

_ACTION_PRIORITY: dict[str, int] = {
    "stop": 0,
    "request_go": 1,
    "split_scope": 2,
    "review": 3,
}

# Sentinel returned when there are no blocking findings.
_DEFAULT_OPERATOR_ACTION = "review"

# ── Helpers ───────────────────────────────────────────────────────────────────


def _blocking_findings(
    scan_result: "ScopeDriftScanResult",
) -> list["ScopeDriftFinding"]:
    """Return only the blocking findings from a scan result."""
    return [f for f in scan_result.findings if f.human_go_required]


def _derive_operator_action(findings: Sequence["ScopeDriftFinding"]) -> str:
    """Derive the highest-priority operator action from a set of findings.

    Findings with ``required_action="stop"`` have highest priority.
    Returns ``_DEFAULT_OPERATOR_ACTION`` when *findings* is empty.
    """
    if not findings:
        return _DEFAULT_OPERATOR_ACTION
    best_priority = len(_ACTION_PRIORITY)  # start above worst
    best_action = _DEFAULT_OPERATOR_ACTION
    for f in findings:
        priority = _ACTION_PRIORITY.get(f.required_action, len(_ACTION_PRIORITY))
        if priority < best_priority:
            best_priority = priority
            best_action = f.required_action
    return _ACTION_LABEL.get(best_action, best_action)


def _collect_affected_artifacts(findings: Sequence["ScopeDriftFinding"]) -> list[str]:
    """Return a sorted, deduplicated list of affected artifact paths/IDs.

    Sourced exclusively from ``ScopeDriftFinding.affected_artifacts``.
    Sorting ensures deterministic output regardless of finding order.
    """
    seen: set[str] = set()
    artifacts: list[str] = []
    for f in findings:
        for artifact in f.affected_artifacts:
            artifact = artifact.strip()
            if artifact and artifact not in seen:
                seen.add(artifact)
                artifacts.append(artifact)
    return sorted(artifacts)


def _collect_recommended_next_reads(findings: Sequence["ScopeDriftFinding"]) -> list[str]:
    """Return a stable-order, deduplicated list of recommended next reads.

    Preserves first-seen order across blocking findings.  Stable order is
    important so that operator tooling produces repeatable output.
    """
    seen: set[str] = set()
    reads: list[str] = []
    for f in findings:
        for read in f.recommended_next_reads:
            read = read.strip()
            if read and read not in seen:
                seen.add(read)
                reads.append(read)
    return reads


def _build_summary_str(blocking_count: int, operator_action: str) -> str:
    """Build a human-readable summary line for blocking output."""
    if blocking_count == 0:
        return "No blocking scope drift findings detected."
    noun = "finding" if blocking_count == 1 else "findings"
    return (
        f"{blocking_count} blocking scope drift {noun} detected. "
        f"Operator action required: {operator_action}. "
        "No auto-fix. No auto-write. Human-GO required for any write."
    )


# ── Public API ────────────────────────────────────────────────────────────────


def build_blocking_output(scan_result: "ScopeDriftScanResult") -> dict[str, Any]:
    """Build the standardised blocking-output dict from a scan result.

    Always safe to call — returns a stable schema regardless of whether any
    blocking findings are present.  When ``blocking_count == 0`` the result
    has ``blocking=False`` and an empty ``findings`` list.

    Output keys:
        status                  str
        blocking                bool
        blocking_count          int
        summary                 str
        operator_action         str
        affected_artifacts      list[str]  — sorted, deduplicated
        recommended_next_reads  list[str]  — stable-order, deduplicated
        guardrails              list[str]
        findings                list[dict] — blocking findings only
        anti_actions            list[str]
    """
    bf = _blocking_findings(scan_result)
    operator_action = _derive_operator_action(bf)
    return {
        "status": scan_result.status,
        "blocking": scan_result.blocking_count > 0,
        "blocking_count": scan_result.blocking_count,
        "summary": _build_summary_str(scan_result.blocking_count, operator_action),
        "operator_action": operator_action,
        "affected_artifacts": _collect_affected_artifacts(bf),
        "recommended_next_reads": _collect_recommended_next_reads(bf),
        "guardrails": list(scan_result.guardrails),
        "findings": [f.to_dict() for f in bf],
        "anti_actions": list(ANTI_ACTIONS),
    }


def render_blocking_markdown(blocking_output: dict[str, Any]) -> str:
    """Render a blocking-output dict as a Markdown section.

    Suitable for embedding in a larger CLI Markdown report.
    Contains: Summary, Operator Action, Affected Artefacts, Anti-Actions,
    Recommended Next Reads, Guardrails, and the Blocking Findings table.
    """
    lines: list[str] = ["## Blocking Output", ""]

    status = blocking_output.get("status", "unknown")
    blocking = blocking_output.get("blocking", False)
    blocking_count = blocking_output.get("blocking_count", 0)
    summary = blocking_output.get("summary", "")
    operator_action = blocking_output.get("operator_action", "review")

    lines += [
        f"- **status**: `{status}`",
        f"- **blocking**: {blocking}",
        f"- **blocking_count**: {blocking_count}",
        "",
        f"**Summary:** {summary}",
        "",
        f"**Operator Action:** `{operator_action}`",
        "",
    ]

    # Affected Artefacts
    artifacts = blocking_output.get("affected_artifacts", [])
    if artifacts:
        lines += ["### Affected Artefacts", ""]
        for a in artifacts:
            lines.append(f"- `{a}`")
        lines.append("")

    # Anti-Actions — always shown
    anti_actions = blocking_output.get("anti_actions", list(ANTI_ACTIONS))
    lines += ["### Anti-Actions (Prohibited)", ""]
    for aa in anti_actions:
        lines.append(f"- `{aa}`")
    lines.append("")

    # Recommended Next Reads
    next_reads = blocking_output.get("recommended_next_reads", [])
    if next_reads:
        lines += ["### Recommended Next Reads", ""]
        for r in next_reads:
            lines.append(f"- `{r}`")
        lines.append("")

    # Guardrails
    guardrails = blocking_output.get("guardrails", [])
    if guardrails:
        lines += ["### Guardrails", ""]
        for g in guardrails:
            lines.append(f"- {g}")
        lines.append("")

    # Blocking Findings table
    findings = blocking_output.get("findings", [])
    if findings:
        lines += ["### Blocking Findings", ""]
        lines.append("| ID | Type | Action | Stop Condition |")
        lines.append("|---|---|---|---|")
        for f in findings:
            stop = f.get("stop_conditions", [])
            stop_str = stop[0] if stop else ""
            lines.append(
                f"| `{f['drift_id']}` "
                f"| `{f['drift_type']}` "
                f"| {f['required_action']} "
                f"| {stop_str} |"
            )
        lines.append("")

    return "\n".join(lines)
