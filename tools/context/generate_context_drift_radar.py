"""Read-only CDB Context Drift Radar.

Scans context refresh artifacts for stale documentation, contradictions between
canon/ledger/GitHub signals, and high-risk drift that blocks Brain Apply (#3289).

Inputs (from context refresh pipeline):
  - context_delta.json          (#3287)
  - validation_report.json      (#3287)
  - agent_briefing_seed.json    (#3290, optional)

Outputs:
  - stale_claims.json  (machine-readable)
  - impact_radar.md    (human-readable)
  - impact_radar.json  (machine-readable, optional via --json)

Usage:
    python tools/context/generate_context_drift_radar.py \\
        --delta <path> --validation <path> [--briefing <path>] [--output-dir <dir>]
    python tools/context/generate_context_drift_radar.py --help

Exit codes:
    0 - radar generated (success or degraded)
    1 - blocked (high-risk drift detected, Brain Apply blocked)
    2 - unexpected error

No DB writes. No secrets. No runtime changes. LR remains NO-GO.
No Brain Apply (#3289). No Onboarding (#3292).
#3291
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "stale_claims.v1"
RADAR_SCHEMA_VERSION = "impact_radar.v1"

DRIFT_CATEGORIES = [
    "canon_pointer_drift",
    "ledger_vs_github_drift",
    "lr_status_ambiguity",
    "stale_architecture_docs",
    "stale_onboarding_docs",
    "stale_agent_bootloader_instructions",
    "workflow_check_drift",
    "unknown_high_risk_delta",
]

HIGH_SEVERITY_CATEGORIES: set[str] = {
    "lr_status_ambiguity",
    "unknown_high_risk_delta",
}

BRAIN_APPLY_BLOCKING_CLAIM_PATTERNS: list[str] = [
    "live readiness",
    "live-go",
    "echtgeld-go",
    "real money",
    "trade-capable",
    "orders",
    "fills",
    "positions",
    "live-risk-state",
    "api_key",
    "api_secret",
    "password",
    "token",
    "secret",
]

CANON_POINTER_PATHS: list[str] = [
    "docs/meta/WORKING_REPO_CANON.md",
    "AGENTS.md",
    "agents/AGENTS.md",
]

ONBOARDING_PATHS: list[str] = [
    "agents/roles/CODEX.md",
    "knowledge/SYSTEM.CONTEXT.md",
]

ARCHITECTURE_PATHS: list[str] = [
    "docs/architecture/",
    "knowledge/CDB_KNOWLEDGE_HUB.md",
]

BOOTLOADER_PATTERNS: list[str] = [
    "bootloader",
    "Read Order",
    "read order",
    "Context Brain Preflight",
    "Brain Evidence Gate",
    "session-start",
]


def read_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _severity_for_category(category: str) -> str:
    if category in HIGH_SEVERITY_CATEGORIES:
        return "high"
    return "medium"


def _blocks_brain_apply(severity: str, category: str, claim_text: str) -> bool:
    if severity == "high":
        return True
    if category in ("lr_status_ambiguity", "unknown_high_risk_delta"):
        return True
    lower = claim_text.lower()
    for pattern in BRAIN_APPLY_BLOCKING_CLAIM_PATTERNS:
        if pattern in lower:
            return True
    return False


def _find_secret_indicators(text: str) -> list[str]:
    found: list[str] = []
    indicators = [
        "api_key",
        "api_secret",
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "MEXC_API_KEY",
        "MEXC_API_SECRET",
        "SECRETS_PATH",
        "SMTP_PASSWORD",
        "GRAFANA_PASSWORD",
        "secret=",
        "password=",
        "token=",
    ]
    for ind in indicators:
        if ind in text:
            found.append(ind)
    return found


def _collect_source_artifacts(
    delta: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    if delta:
        artifacts["context_delta"] = delta.get("schema_version", "unknown")
    if validation:
        artifacts["validation_report"] = validation.get("schema_version", "unknown")
    if briefing:
        artifacts["agent_briefing_seed"] = briefing.get("schema_version", "unknown")
    return artifacts


def scan_canon_pointer_drift(
    delta: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    changed = set(delta.get("changed_canon_paths_if_available", []) if delta else [])
    for canon_path in CANON_POINTER_PATHS:
        if canon_path in changed:
            claims.append(
                {
                    "claim": f"Canon pointer file changed: {canon_path}",
                    "drift_category": "canon_pointer_drift",
                    "severity": "medium",
                    "source_ref": f"context_delta.changed_canon_paths_if_available",
                    "current_truth_ref": canon_path,
                    "status": "changed",
                    "recommended_action": f"Review {canon_path} for pointer consistency",
                    "blocks_brain_apply": False,
                }
            )
    return claims


def scan_ledger_vs_github_drift(
    delta: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if not delta:
        return claims

    issues = delta.get("open_issues_summary", {}).get("issues", [])
    for issue in issues:
        title = issue.get("title", "")
        if "CONTEXT" in title or "DRIFT" in title:
            claims.append(
                {
                    "claim": f"Open context/drift issue: #{issue['number']} {title}",
                    "drift_category": "ledger_vs_github_drift",
                    "severity": "medium",
                    "source_ref": f"context_delta.open_issues_summary.issues[#{issue['number']}]",
                    "current_truth_ref": f"https://github.com/jannekbuengener/Claire_de_Binare/issues/{issue['number']}",
                    "status": "open",
                    "recommended_action": f"Resolve #{issue['number']} before asserting ledger/GitHub alignment",
                    "blocks_brain_apply": False,
                }
            )

    return claims


def scan_lr_status_ambiguity(
    delta: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if not delta:
        return claims
    safety = delta.get("safety_boundaries", {})
    if safety.get("lr_status") != "NO-GO":
        claims.append(
            {
                "claim": f"LR status in context_delta is not NO-GO: {safety.get('lr_status')}",
                "drift_category": "lr_status_ambiguity",
                "severity": "high",
                "source_ref": "context_delta.safety_boundaries.lr_status",
                "current_truth_ref": "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                "status": "blocking",
                "recommended_action": "Revert lr_status to NO-GO; only LR-SSOT can change this.",
                "blocks_brain_apply": True,
            }
        )

    if briefing:
        briefing_safety = briefing.get("safety_boundaries", {})
        if briefing_safety.get("lr_status") != "NO-GO":
            claims.append(
                {
                    "claim": f"LR status in agent_briefing_seed is not NO-GO: {briefing_safety.get('lr_status')}",
                    "drift_category": "lr_status_ambiguity",
                    "severity": "high",
                    "source_ref": "agent_briefing_seed.safety_boundaries.lr_status",
                    "current_truth_ref": "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
                    "status": "blocking",
                    "recommended_action": "Revert briefing lr_status to NO-GO.",
                    "blocks_brain_apply": True,
                }
            )

    return claims


def scan_stale_architecture_docs(
    delta: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    changed = set(delta.get("changed_canon_paths_if_available", []) if delta else [])
    for arch_path in ARCHITECTURE_PATHS:
        if arch_path in changed:
            claims.append(
                {
                    "claim": f"Architecture or knowledge hub file changed: {arch_path}. Review for stale references.",
                    "drift_category": "stale_architecture_docs",
                    "severity": "medium",
                    "source_ref": f"context_delta.changed_canon_paths_if_available",
                    "current_truth_ref": arch_path,
                    "status": "needs_review",
                    "recommended_action": f"Audit {arch_path} for outdated architecture claims",
                    "blocks_brain_apply": False,
                }
            )
    return claims


def scan_stale_onboarding_docs(
    delta: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    changed = set(delta.get("changed_canon_paths_if_available", []) if delta else [])
    for ob_path in ONBOARDING_PATHS:
        if ob_path in changed:
            claims.append(
                {
                    "claim": f"Onboarding-related file changed: {ob_path}. Onboarding docs may be stale.",
                    "drift_category": "stale_onboarding_docs",
                    "severity": "medium",
                    "source_ref": f"context_delta.changed_canon_paths_if_available",
                    "current_truth_ref": ob_path,
                    "status": "needs_review",
                    "recommended_action": f"Review {ob_path} for onboarding accuracy",
                    "blocks_brain_apply": False,
                }
            )
    return claims


def scan_stale_agent_bootloader_instructions(
    delta: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    changed = set(delta.get("changed_canon_paths_if_available", []) if delta else [])

    for boot_path in set(changed):
        if any(
            boot_path.startswith(p)
            for p in ["AGENTS.md", "agents/", ".cursor/", ".opencode/", ".claude/"]
        ):
            claims.append(
                {
                    "claim": f"Agent or bootloader surface changed: {boot_path}. Bootloader instructions may be stale.",
                    "drift_category": "stale_agent_bootloader_instructions",
                    "severity": "medium",
                    "source_ref": f"context_delta.changed_canon_paths_if_available",
                    "current_truth_ref": boot_path,
                    "status": "needs_review",
                    "recommended_action": f"Audit {boot_path} for bootloader instruction drift",
                    "blocks_brain_apply": False,
                }
            )

    if briefing:
        stale = briefing.get("stale_claims", [])
        for s in stale:
            text = s.get("claim", "")
            for pattern in BOOTLOADER_PATTERNS:
                if pattern in text:
                    claims.append(
                        {
                            "claim": text,
                            "drift_category": "stale_agent_bootloader_instructions",
                            "severity": "medium",
                            "source_ref": "agent_briefing_seed.stale_claims",
                            "current_truth_ref": s.get("source", ""),
                            "status": "stale_or_unknown",
                            "recommended_action": "Resolve bootloader/read-order claim before Brain Apply",
                            "blocks_brain_apply": False,
                        }
                    )
                    break

    return claims


def scan_workflow_check_drift(
    validation: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if not validation:
        return claims

    status = validation.get("status", "unknown")
    blocked = validation.get("blocked_reasons", [])
    warnings = validation.get("warnings", [])

    if status == "BLOCKED":
        claims.append(
            {
                "claim": f"Validation report status is BLOCKED: {'; '.join(blocked)}",
                "drift_category": "workflow_check_drift",
                "severity": "high",
                "source_ref": "validation_report.status",
                "current_truth_ref": "validation_report.blocked_reasons",
                "status": "blocking",
                "recommended_action": "Resolve validation blockages before proceeding",
                "blocks_brain_apply": True,
            }
        )

    for warning in warnings:
        claims.append(
            {
                "claim": f"Validation warning: {warning}",
                "drift_category": "workflow_check_drift",
                "severity": "medium",
                "source_ref": "validation_report.warnings",
                "current_truth_ref": "",
                "status": "warning",
                "recommended_action": f"Review: {warning}",
                "blocks_brain_apply": False,
            }
        )

    return claims


def scan_unknown_high_risk_delta(
    delta: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if not delta:
        return claims

    limitations = delta.get("limitations", [])
    for lim in limitations:
        lower = lim.lower()
        for pattern in BRAIN_APPLY_BLOCKING_CLAIM_PATTERNS:
            if pattern in lower:
                claims.append(
                    {
                        "claim": f"High-risk limitation: {lim}",
                        "drift_category": "unknown_high_risk_delta",
                        "severity": "high",
                        "source_ref": "context_delta.limitations",
                        "current_truth_ref": "",
                        "status": "blocking",
                        "recommended_action": "Resolve limitation before proceeding with Brain Apply",
                        "blocks_brain_apply": True,
                    }
                )
                break

    return claims


def scan_all(
    delta: dict[str, Any] | None,
    validation: dict[str, Any] | None,
    briefing: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    all_claims: list[dict[str, Any]] = []
    all_claims.extend(scan_canon_pointer_drift(delta, briefing))
    all_claims.extend(scan_ledger_vs_github_drift(delta, briefing))
    all_claims.extend(scan_lr_status_ambiguity(delta, validation, briefing))
    all_claims.extend(scan_stale_architecture_docs(delta, briefing))
    all_claims.extend(scan_stale_onboarding_docs(delta, briefing))
    all_claims.extend(scan_stale_agent_bootloader_instructions(delta, briefing))
    all_claims.extend(scan_workflow_check_drift(validation))
    all_claims.extend(scan_unknown_high_risk_delta(delta, briefing))
    return all_claims


def build_stale_claims(
    claims: list[dict[str, Any]],
    source_artifacts: dict[str, Any],
    utc_now: str,
    degraded: bool,
    limitations: list[str],
) -> dict[str, Any]:
    blocks_brain = any(c.get("blocks_brain_apply", False) for c in claims)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now,
        "source_artifacts": source_artifacts,
        "claims": claims,
        "summary": {
            "total_claims": len(claims),
            "blocking_claims": sum(1 for c in claims if c.get("blocks_brain_apply")),
            "high_severity": sum(1 for c in claims if c.get("severity") == "high"),
            "medium_severity": sum(1 for c in claims if c.get("severity") == "medium"),
            "low_severity": sum(1 for c in claims if c.get("severity") == "low"),
            "blocks_brain_apply": blocks_brain,
        },
        "degraded": degraded,
        "limitations": limitations,
    }


def build_impact_radar(
    stale_claims: dict[str, Any],
    source_artifacts: dict[str, Any],
    utc_now: str,
    degraded: bool,
    limitations: list[str],
) -> dict[str, Any]:
    claims = stale_claims.get("claims", [])
    summary = stale_claims.get("summary", {})
    blocks_brain = summary.get("blocks_brain_apply", False)

    by_category: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        cat = c.get("drift_category", "unknown")
        by_category.setdefault(cat, []).append(c)

    blocking = [c for c in claims if c.get("blocks_brain_apply")]
    high_risk = [c for c in claims if c.get("severity") == "high"]

    follow_up_recommendations: list[dict[str, Any]] = []
    if blocks_brain:
        follow_up_recommendations.append(
            {
                "title": "Resolve Brain Apply blockers from drift radar",
                "reasoning": f"{summary.get('blocking_claims', 0)} claims block Brain Apply (#3289)",
                "priority": "high",
                "safety_boundary": "Brain Apply must not proceed while blocks_brain_apply claims exist",
                "dedupe_hint": "Check if #3289 already tracks these blockers",
            }
        )
    if high_risk:
        follow_up_recommendations.append(
            {
                "title": "Investigate high-risk drift signals",
                "reasoning": f"{len(high_risk)} high-severity claims detected",
                "priority": "high",
                "safety_boundary": "High-risk claims must be resolved before any live-adjacent work",
                "dedupe_hint": "Do not auto-create; use this report to triage",
            }
        )
    if any(c.get("drift_category") == "stale_architecture_docs" for c in claims):
        follow_up_recommendations.append(
            {
                "title": "Update stale architecture documentation",
                "reasoning": "Architecture or knowledge hub files changed",
                "priority": "medium",
                "safety_boundary": "Stale architecture docs may mislead agents",
                "dedupe_hint": "Verify no existing docs-maintenance issue is open",
            }
        )
    if any(c.get("drift_category") == "stale_onboarding_docs" for c in claims):
        follow_up_recommendations.append(
            {
                "title": "Refresh onboarding documentation",
                "reasoning": "Onboarding-related files changed",
                "priority": "medium",
                "safety_boundary": "Onboarding docs drift affects agent session quality",
                "dedupe_hint": "Onboarding scenario (#3292) is the planned slot for this",
            }
        )
    if any(
        c.get("drift_category") == "stale_agent_bootloader_instructions" for c in claims
    ):
        follow_up_recommendations.append(
            {
                "title": "Audit agent bootloader instructions for drift",
                "reasoning": "Bootloader surfaces changed since last refresh",
                "priority": "medium",
                "safety_boundary": "Bootloader drift can cause agent confusion",
                "dedupe_hint": "Check AGENTS.md and agent role files for consistency",
            }
        )
    if any(c.get("drift_category") == "workflow_check_drift" for c in claims):
        follow_up_recommendations.append(
            {
                "title": "Resolve workflow/check drift",
                "reasoning": "Validation report contains blockages or warnings",
                "priority": (
                    "high"
                    if any(
                        c.get("severity") == "high"
                        and c.get("drift_category") == "workflow_check_drift"
                        for c in claims
                    )
                    else "medium"
                ),
                "safety_boundary": "Workflow check drift may indicate CI/reporting failures",
                "dedupe_hint": "Check CI status before creating new issue",
            }
        )

    return {
        "schema_version": RADAR_SCHEMA_VERSION,
        "generated_at_utc": utc_now,
        "title": "CDB Context Drift / Impact Radar",
        "source_artifacts": source_artifacts,
        "high_risk_drift": high_risk,
        "brain_apply_blockers": blocking,
        "brain_apply_blocked": blocks_brain,
        "stale_claims": claims,
        "by_category": by_category,
        "canon_ledger_github_conflicts": {
            "ledger_vs_github": [
                c for c in claims if c.get("drift_category") == "ledger_vs_github_drift"
            ],
            "canon_pointer": [
                c for c in claims if c.get("drift_category") == "canon_pointer_drift"
            ],
            "lr_ambiguity": [
                c for c in claims if c.get("drift_category") == "lr_status_ambiguity"
            ],
        },
        "workflow_check_drift": [
            c for c in claims if c.get("drift_category") == "workflow_check_drift"
        ],
        "recommended_follow_up_issues": follow_up_recommendations,
        "safety_boundaries": {
            "lr_status": "NO-GO",
            "board_stage_is_live_go": False,
            "real_money_go": False,
            "productive_db_writes_allowed": False,
            "secrets_in_outputs_allowed": False,
            "trading_state_ingestion_allowed": False,
            "brain_apply_blocked": blocks_brain,
            "auto_issue_creation_allowed": False,
        },
        "degraded": degraded,
        "limitations": limitations,
    }


def build_impact_radar_md(radar: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# Context Drift / Impact Radar")
    lines.append("")
    lines.append(f"- **Generated at (UTC):** {radar['generated_at_utc']}")
    lines.append(f"- **Schema version:** {radar['schema_version']}")
    if radar["degraded"]:
        lines.append(
            "- **Status: DEGRADED** — one or more input artifacts were missing or unreadable"
        )
    if radar["brain_apply_blocked"]:
        lines.append("- **Brain Apply: BLOCKED** — high-risk drift prevents #3289")
    else:
        lines.append("- **Brain Apply: NOT BLOCKED** — no high-risk drift detected")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Source Artifacts")
    lines.append("")
    for name, version in radar["source_artifacts"].items():
        lines.append(f"- **{name}:** {version}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## High-Risk Drift")
    lines.append("")
    high = radar["high_risk_drift"]
    if high:
        for c in high:
            lines.append(
                f"- [{c['drift_category']}] {c['claim']} "
                f"(severity: {c['severity']}, blocks_brain_apply: {c['blocks_brain_apply']})"
            )
    else:
        lines.append("- (none detected)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Brain Apply Blockers")
    lines.append("")
    blockers = radar["brain_apply_blockers"]
    if blockers:
        for c in blockers:
            lines.append(
                f"- [{c['drift_category']}] {c['claim']} " f"(status: {c['status']})"
            )
        lines.append("")
        lines.append(
            "**Verdict:** Brain Apply (#3289) is BLOCKED until these claims are resolved."
        )
    else:
        lines.append("- (none detected)")
        lines.append("")
        lines.append("**Verdict:** Brain Apply (#3289) is NOT BLOCKED by drift radar.")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Stale Claims")
    lines.append("")
    stale = radar["stale_claims"]
    if stale:
        for c in stale:
            lines.append(
                f"- [{c['drift_category']}] {c['claim']} "
                f"(severity: {c['severity']}, recommended: {c.get('recommended_action', 'review')})"
            )
    else:
        lines.append("- (none detected)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Canon / Ledger / GitHub Conflicts")
    lines.append("")
    conflicts = radar["canon_ledger_github_conflicts"]
    ledger = conflicts["ledger_vs_github"]
    canon = conflicts["canon_pointer"]
    lr = conflicts["lr_ambiguity"]
    lines.append(f"- **Ledger vs GitHub:** {len(ledger)} claim(s)")
    for c in ledger:
        lines.append(f"  - {c['claim']}")
    lines.append(f"- **Canon pointer drift:** {len(canon)} claim(s)")
    for c in canon:
        lines.append(f"  - {c['claim']}")
    lines.append(f"- **LR status ambiguity:** {len(lr)} claim(s)")
    for c in lr:
        lines.append(f"  - {c['claim']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Workflow / Check Drift")
    lines.append("")
    wf = radar["workflow_check_drift"]
    if wf:
        for c in wf:
            lines.append(f"- [{c['status']}] {c['claim']}")
    else:
        lines.append("- (none detected)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Recommended Follow-up Issues")
    lines.append("")
    issues = radar["recommended_follow_up_issues"]
    if issues:
        for rec in issues:
            lines.append(f"- **{rec['title']}**")
            lines.append(f"  - Reasoning: {rec['reasoning']}")
            lines.append(f"  - Priority: {rec['priority']}")
            lines.append(f"  - Safety boundary: {rec['safety_boundary']}")
            lines.append(f"  - Dedupe hint: {rec['dedupe_hint']}")
    else:
        lines.append("- (none recommended)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Safety Boundaries")
    lines.append("")
    for key, val in radar["safety_boundaries"].items():
        lines.append(f"- **{key}:** {val}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for lim in radar["limitations"]:
        lines.append(f"- {lim}")
    if not radar["limitations"]:
        lines.append("- (none)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append(
        "*This is a read-only drift detection artifact. "
        "It does not authorize live trading, runtime changes, DB writes, "
        "or any Echtgeld activity. LR remains NO-GO. "
        "Brain Apply (#3289) and Onboarding (#3292) are separate follow-up slices. "
        "Follow-up issues are recommendations only — not auto-created.*"
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only CDB Context Drift Radar (#3291)",
    )
    parser.add_argument(
        "--delta",
        required=True,
        help="Path to context_delta.json",
    )
    parser.add_argument(
        "--validation",
        required=True,
        help="Path to validation_report.json",
    )
    parser.add_argument(
        "--briefing",
        default=None,
        help="Path to agent_briefing_seed.json (optional)",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for generated files (default: current dir)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Also emit impact_radar.json (machine-readable)",
    )
    args = parser.parse_args()

    utc_now = cdb_utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    degraded = False
    limitations: list[str] = []

    delta: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    briefing: dict[str, Any] | None = None

    try:
        delta = read_json(args.delta)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not read context_delta.json: {e}", file=sys.stderr)
        degraded = True
        limitations.append(f"context_delta.json not available: {e}")

    try:
        validation = read_json(args.validation)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not read validation_report.json: {e}", file=sys.stderr)
        degraded = True
        limitations.append(f"validation_report.json not available: {e}")

    if args.briefing:
        try:
            briefing = read_json(args.briefing)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(
                f"[WARN] Could not read agent_briefing_seed.json: {e}", file=sys.stderr
            )
            degraded = True
            limitations.append(f"agent_briefing_seed.json not available: {e}")

    source_artifacts = _collect_source_artifacts(delta, validation, briefing)

    if delta is None and validation is None:
        print(
            "[FAIL] Both context_delta.json and validation_report.json are required. Aborting.",
            file=sys.stderr,
        )
        return 2

    if delta is None:
        limitations.append("context_delta.json missing — some drift categories skipped")
    if validation is None:
        limitations.append(
            "validation_report.json missing — some drift categories skipped"
        )

    secret_warnings: list[str] = []
    for artifact_name, artifact in [
        ("context_delta", delta),
        ("validation_report", validation),
        ("agent_briefing_seed", briefing),
    ]:
        if artifact:
            text = json.dumps(artifact)
            found = _find_secret_indicators(text)
            if found:
                secret_warnings.append(
                    f"Secret indicators found in {artifact_name}: {found}"
                )

    if secret_warnings:
        for sw in secret_warnings:
            print(f"[SECRET WARNING] {sw}", file=sys.stderr)
            limitations.append(sw)

    claims = scan_all(delta, validation, briefing)
    stale_claims = build_stale_claims(
        claims=claims,
        source_artifacts=source_artifacts,
        utc_now=utc_now,
        degraded=degraded,
        limitations=list(limitations),
    )

    radar = build_impact_radar(
        stale_claims=stale_claims,
        source_artifacts=source_artifacts,
        utc_now=utc_now,
        degraded=degraded,
        limitations=list(limitations),
    )

    claims_path = output_dir / "stale_claims.json"
    claims_path.write_text(
        json.dumps(stale_claims, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md_path = output_dir / "impact_radar.md"
    md_path.write_text(build_impact_radar_md(radar), encoding="utf-8")

    json_path: Path | None = None
    if args.emit_json:
        json_path = output_dir / "impact_radar.json"
        json_path.write_text(
            json.dumps(radar, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    blocks_brain = stale_claims["summary"]["blocks_brain_apply"]
    exit_code = 1 if blocks_brain else (1 if degraded else 0)

    print(
        f"[{'BLOCKED' if blocks_brain else 'DEGRADED' if degraded else 'PASS'}] Drift radar generated:"
    )
    print(f"  Claims:  {claims_path}")
    print(f"  MD:      {md_path}")
    if json_path:
        print(f"  JSON:    {json_path}")
    print(f"  Degraded: {degraded}")
    print(f"  Total claims: {len(claims)}")
    print(f"  Blocking: {stale_claims['summary']['blocking_claims']}")
    print(f"  Brain Apply blocked: {blocks_brain}")
    print(f"  LR: NO-GO")
    print(f"  Exit code: {exit_code} (0=PASS, 1=BLOCKED/DEGRADED)")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
