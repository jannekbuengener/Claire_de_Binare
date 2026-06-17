"""Generate an Agent Briefing Seed from Context Refresh artifacts.

Reads the three artifacts produced by the report-only Context Refresh workflow:
  - context_delta.json
  - context_refresh_summary.md
  - validation_report.json

Produces:
  - agent_briefing_seed.json (machine-readable)
  - agent_briefing_seed.md (human-readable)

Usage:
    python tools/context/generate_agent_briefing_seed.py \\
        --delta <path> --summary <path> --validation <path> [--output-dir <dir>]
    python tools/context/generate_agent_briefing_seed.py --help

Exit codes:
    0 - briefing seed generated (success or degraded)
    1 - fail-closed (core input missing)
    2 - unexpected error

No DB writes. No secrets. No runtime changes. LR remains NO-GO.
No Brain Apply (#3289). No Drift Radar (#3291). No Onboarding (#3292).
#3290
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "agent_briefing_seed.v1"

CANON_READ_ORDER: list[str] = [
    "AGENTS.md",
    "agents/AGENTS.md",
    "agents/roles/CODEX.md",
    "docs/meta/WORKING_REPO_CANON.md",
    "knowledge/governance/CDB_CONSTITUTION.md",
    "knowledge/governance/CDB_GOVERNANCE.md",
    "knowledge/governance/CDB_AGENT_POLICY.md",
    "knowledge/CDB_KNOWLEDGE_HUB.md",
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "knowledge/runbooks/CDB_CONTROL_BOARD_RUNBOOK.md",
    "PROJECT_STATUS.md",
    "agents/OPEN_CODE_AGENTS.md",
]

EVIDENCE_PATH_PREFIXES: list[str] = [
    "docs/evidence/",
    "reports/",
    "docs/live-readiness/",
]

STOP_CONDITIONS_BASE: list[str] = [
    "LR remains NO-GO. Briefing seed does not authorize live trading.",
    "No Echtgeld-Go. No real-money trading authorized.",
    "Board stage 'trade-capable' is orthogonal to LR system; no live implication.",
    "No productive DB writes. No SurrealDB mutations.",
    "No Brain Apply (#3289) — briefing seed is context, not execution.",
    "No Drift Radar (#3291) — separate follow-up slice.",
    "No Onboarding (#3292) — separate follow-up slice.",
    "No secrets ingestion or exposure.",
    "No orders, fills, positions, or live risk state ingestion.",
    "No runtime, Docker, compose, or BLUE/RED stack changes.",
    "No MCP mutations.",
    "No agent authorization decisions from this briefing alone.",
    "No auto-issue creation.",
]

SAFETY_BOUNDARIES: dict[str, Any] = {
    "lr_status": "NO-GO",
    "board_stage_is_live_go": False,
    "real_money_go": False,
    "productive_db_writes_allowed": False,
    "secrets_in_outputs_allowed": False,
    "trading_state_ingestion_allowed": False,
    "brain_apply_allowed": False,
    "drift_radar_allowed": False,
    "onboarding_allowed": False,
    "auto_issue_creation_allowed": False,
    "agent_authorization_allowed": False,
}


def read_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(path: str | Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def extract_recent_merges_from_gh(limit: int = 5) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--json",
                "number,title,mergedAt,mergeCommit,baseRefName,headRefName,url",
                "--limit",
                str(limit),
                "--base",
                "main",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return []


def extract_evidence_paths(changed_paths: list[str]) -> list[str]:
    return [
        p
        for p in changed_paths
        if any(p.startswith(prefix) for prefix in EVIDENCE_PATH_PREFIXES)
    ]


def extract_stale_claims(
    delta: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    stale: list[dict[str, Any]] = []
    for lim in delta.get("limitations", []):
        stale.append(
            {
                "claim": lim,
                "source": "context_delta.limitations",
                "confidence": "low",
                "marked_as": "stale_or_unknown",
            }
        )
    for warning in validation.get("warnings", []):
        stale.append(
            {
                "claim": warning,
                "source": "validation_report.warnings",
                "confidence": "medium",
                "marked_as": "stale_or_unknown",
            }
        )
    for reason in validation.get("blocked_reasons", []):
        stale.append(
            {
                "claim": reason,
                "source": "validation_report.blocked_reasons",
                "confidence": "medium",
                "marked_as": "blocking",
            }
        )
    return stale


def extract_delta_source_commit(delta: dict[str, Any]) -> str:
    head = delta.get("head_commit", "")
    if head and not head.startswith("<error"):
        return head
    base = delta.get("base_commit", "")
    if base and not base.startswith("<error"):
        return base
    return ""


def build_brain_evidence_status(
    delta: dict[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    if not delta or not source_commit:
        return {
            "brain_source": "repo-only",
            "brain_status": "not-used",
            "tools_or_queries": ["file_read"],
            "records_or_results": ["context refresh artifacts (file-based)"],
            "repo_crosscheck": [],
            "impact_on_plan": ["Briefing seed is generated from file inputs only"],
            "limitations": [
                "No DB-backed evidence",
                "No MCP tool queries",
                "No SurrealDB records",
                "Brain status is repo-only; no productive DB or memory layer consulted",
            ],
        }
    gh_used = bool(delta.get("open_issues_summary", {}).get("issues"))
    tools = ["file_read"]
    if gh_used:
        tools.append("gh_cli")
    return {
        "brain_source": "repo-only",
        "brain_status": "partial" if gh_used else "not-used",
        "tools_or_queries": tools,
        "records_or_results": [
            f"context_delta.json (schema: {delta.get('schema_version', 'unknown')})",
            f"validation_report.json (status: {delta.get('status', 'unknown')})",
        ],
        "repo_crosscheck": [
            f"source_commit: {source_commit[:12] if source_commit else 'unknown'}",
        ],
        "impact_on_plan": [
            "Briefing seed is compiled from context refresh artifacts",
            "Claims are sourced from input files, not live DB",
        ],
        "limitations": [
            "No DB-backed evidence; all claims are file-based",
            "No verified MCP tool queries were executed",
            "Context delta reflects a point-in-time snapshot",
            "Stale/unknown claims are based on input limitations, not live scan",
        ],
    }


def build_recommended_read_order(
    delta: dict[str, Any],
) -> list[dict[str, Any]]:
    changed = delta.get("changed_canon_paths_if_available", [])
    changed_set = set(changed)
    order: list[dict[str, Any]] = []
    for path in CANON_READ_ORDER:
        reason = "changed" if path in changed_set else "canonical reference"
        order.append({"path": path, "reason": reason})
    extra_changed = [p for p in changed if p not in CANON_READ_ORDER]
    for path in extra_changed:
        order.append(
            {"path": path, "reason": "changed (outside default canon read order)"}
        )
    return order


def build_stop_conditions(
    limitations: list[str],
) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for sc in STOP_CONDITIONS_BASE:
        conditions.append({"condition": sc, "source": "built-in safety boundaries"})
    for lim in limitations:
        conditions.append({"condition": lim, "source": "context refresh limitation"})
    return conditions


def build_briefing_seed(
    delta: dict[str, Any],
    summary_text: str,
    validation: dict[str, Any],
    recent_merges: list[dict[str, Any]],
    repo_path: str,
    source_commit: str,
    utc_now: str,
    degraded: bool,
) -> dict[str, Any]:
    brain = build_brain_evidence_status(delta, source_commit)
    changed_canon = delta.get("changed_canon_paths_if_available", [])
    evidence_files = extract_evidence_paths(changed_canon)
    stale = extract_stale_claims(delta, validation)
    limitations: list[str] = list(delta.get("limitations", []))
    limitations.extend(validation.get("limitations", []))
    if recent_merges is None:
        limitations.append("Recent merges not available — gh CLI not reachable")
    if degraded:
        limitations.insert(
            0, "DEGRADED: One or more input artifacts were missing or unreadable"
        )
    stop_conditions = build_stop_conditions(limitations)

    open_issues_raw = delta.get("open_issues_summary", {}).get("issues", [])
    open_prs_raw = delta.get("open_prs_summary", {}).get("prs", [])

    context_issues = [
        {
            "number": i["number"],
            "title": i["title"],
            "state": i.get("state", "OPEN"),
            "labels": i.get("labels", []),
            "updated_at": i.get("updated_at", ""),
        }
        for i in open_issues_raw
    ]
    context_prs = [
        {
            "number": p["number"],
            "title": p["title"],
            "state": p.get("state", "OPEN"),
            "head_ref": p.get("head_ref", ""),
            "base_ref": p.get("base_ref", ""),
        }
        for p in open_prs_raw
    ]

    new_merges = [
        {
            "number": m["number"],
            "title": m["title"],
            "merged_at": m.get("mergedAt", ""),
            "merge_commit": (
                m.get("mergeCommit", {}).get("oid", "")
                if isinstance(m.get("mergeCommit"), dict)
                else ""
            ),
            "url": m.get("url", ""),
        }
        for m in recent_merges
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now,
        "source_artifacts": {
            "context_delta": delta.get("schema_version", ""),
            "validation_report": validation.get("schema_version", ""),
            "context_refresh_summary": "markdown",
        },
        "source_commit": source_commit or "",
        "brain_evidence_status": brain,
        "recommended_read_order": build_recommended_read_order(delta),
        "new_merges": new_merges,
        "open_context_prs": context_prs,
        "open_context_issues": context_issues,
        "changed_canon_files": changed_canon,
        "new_evidence_files": evidence_files,
        "stale_claims": stale,
        "stop_conditions": stop_conditions,
        "safety_boundaries": dict(SAFETY_BOUNDARIES),
        "limitations": limitations,
        "degraded": degraded,
        "validation_summary": {
            "status": validation.get("status", "unknown"),
            "blocked_reasons": validation.get("blocked_reasons", []),
            "warnings": validation.get("warnings", []),
        },
    }


def build_briefing_md(briefing: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append("# Agent Briefing Seed")
    lines.append("")
    lines.append(f"- **Generated at (UTC):** {briefing['generated_at_utc']}")
    lines.append(f"- **Schema version:** {briefing['schema_version']}")
    lines.append(
        f"- **Source commit:** `{briefing['source_commit'][:12] if briefing['source_commit'] else 'unknown'}`"
    )
    if briefing["degraded"]:
        lines.append(
            "- **Status: DEGRADED** — one or more input artifacts were missing or unreadable"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Source Artifacts")
    lines.append("")
    arts = briefing["source_artifacts"]
    lines.append(f"- **context_delta.json:** {arts.get('context_delta', 'unknown')}")
    lines.append(
        f"- **validation_report.json:** {arts.get('validation_report', 'unknown')}"
    )
    lines.append(f"- **context_refresh_summary.md:** markdown")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Brain Evidence Status")
    lines.append("")
    brain = briefing["brain_evidence_status"]
    lines.append(f"- **brain_source:** {brain.get('brain_source', 'unknown')}")
    lines.append(f"- **brain_status:** {brain.get('brain_status', 'unknown')}")
    lines.append("- **tools_or_queries:**")
    for t in brain.get("tools_or_queries", []):
        lines.append(f"  - {t}")
    lines.append("- **limitations:**")
    for lim in brain.get("limitations", []):
        lines.append(f"  - {lim}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Recommended Read Order")
    lines.append("")
    for item in briefing["recommended_read_order"]:
        icon = "[changed]" if item["reason"] == "changed" else "[canon]"
        lines.append(f"- {icon} {item['path']} ({item['reason']})")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Context-Relevant Changes")
    lines.append("")
    canon_files = briefing["changed_canon_files"]
    lines.append(f"- **Changed canon files ({len(canon_files)}):**")
    if canon_files:
        for p in canon_files:
            lines.append(f"  - {p}")
    else:
        lines.append("  - (none detected)")
    evidence_files = briefing["new_evidence_files"]
    lines.append(f"- **New evidence files ({len(evidence_files)}):**")
    if evidence_files:
        for p in evidence_files:
            lines.append(f"  - {p}")
    else:
        lines.append("  - (none detected)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Open PRs / Issues")
    lines.append("")
    lines.append(f"- **Open context issues:** {len(briefing['open_context_issues'])}")
    for issue in briefing["open_context_issues"]:
        labels = ", ".join(issue["labels"]) if issue["labels"] else "none"
        lines.append(f"  - #{issue['number']} {issue['title']} (labels: {labels})")
    lines.append(f"- **Open context PRs:** {len(briefing['open_context_prs'])}")
    for pr in briefing["open_context_prs"]:
        lines.append(
            f"  - #{pr['number']} {pr['title']} ({pr['head_ref']} -> {pr['base_ref']})"
        )
    lines.append("")
    lines.append("### Recent Merges")
    merges = briefing["new_merges"]
    if merges:
        for m in merges:
            sha = f"`{m['merge_commit'][:12]}`" if m["merge_commit"] else ""
            lines.append(
                f"- #{m['number']} {m['title']} — merged at {m['merged_at']} ({sha})"
            )
    else:
        lines.append("- (none detected or gh CLI not available)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Stale or Unknown Claims")
    lines.append("")
    stale = briefing["stale_claims"]
    if stale:
        for s in stale:
            lines.append(
                f"- [{s['marked_as']}] {s['claim']} (confidence: {s['confidence']}, source: {s['source']})"
            )
    else:
        lines.append("- (none detected)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Stop Conditions")
    lines.append("")
    for sc in briefing["stop_conditions"]:
        lines.append(f"- {sc['condition']} (source: {sc['source']})")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Safety Boundaries")
    lines.append("")
    for key, val in briefing["safety_boundaries"].items():
        lines.append(f"- **{key}:** {val}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for lim in briefing["limitations"]:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append(
        "*This is a context artifact. "
        "It does not authorize live trading, runtime changes, DB writes, "
        "or any Echtgeld activity. LR remains NO-GO. "
        "Brain Apply (#3289), Drift Radar (#3291), and Onboarding (#3292) "
        "are separate follow-up slices.*"
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Agent Briefing Seed from Context Refresh artifacts (#3290)",
    )
    parser.add_argument(
        "--delta",
        required=True,
        help="Path to context_delta.json",
    )
    parser.add_argument(
        "--summary",
        required=True,
        help="Path to context_refresh_summary.md",
    )
    parser.add_argument(
        "--validation",
        required=True,
        help="Path to validation_report.json",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for generated briefing seed files (default: current dir)",
    )
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to repo root (default: current dir)",
    )
    parser.add_argument(
        "--source-commit",
        default="",
        help="Override source commit (default: auto-detect from delta or HEAD)",
    )
    parser.add_argument(
        "--no-gh",
        action="store_true",
        help="Skip gh CLI calls — use only file inputs",
    )
    args = parser.parse_args()

    utc_now = cdb_utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_path = os.path.abspath(args.repo_path)

    degraded = False
    delta: dict[str, Any] = {}
    summary_text = ""
    validation: dict[str, Any] = {}

    try:
        delta = read_json(args.delta)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not read context_delta.json: {e}", file=sys.stderr)
        degraded = True
        delta = {
            "schema_version": "absent",
            "open_issues_summary": {"issues": [], "total_count": 0},
            "open_prs_summary": {"prs": [], "total_count": 0},
            "changed_canon_paths_if_available": [],
            "limitations": [f"context_delta.json not available: {e}"],
            "safety_boundaries": {},
            "head_commit": "",
            "base_commit": "",
            "status": "absent",
        }

    try:
        summary_text = read_text(args.summary)
    except (FileNotFoundError, OSError) as e:
        print(f"[WARN] Could not read context_refresh_summary.md: {e}", file=sys.stderr)
        degraded = True
        summary_text = f"<summary not available: {e}>"

    try:
        validation = read_json(args.validation)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Could not read validation_report.json: {e}", file=sys.stderr)
        degraded = True
        validation = {
            "schema_version": "absent",
            "status": "absent",
            "blocked_reasons": [f"validation_report.json not available: {e}"],
            "warnings": [],
            "limitations": ["validation_report.json not available"],
        }

    source_commit = args.source_commit or extract_delta_source_commit(delta)
    if not source_commit:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=repo_path,
            )
            if result.returncode == 0:
                source_commit = result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    recent_merges: list[dict[str, Any]] = []
    if not args.no_gh:
        recent_merges = extract_recent_merges_from_gh()

    briefing = build_briefing_seed(
        delta=delta,
        summary_text=summary_text,
        validation=validation,
        recent_merges=recent_merges,
        repo_path=repo_path,
        source_commit=source_commit,
        utc_now=utc_now,
        degraded=degraded,
    )

    json_path = output_dir / "agent_briefing_seed.json"
    json_path.write_text(
        json.dumps(briefing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md_path = output_dir / "agent_briefing_seed.md"
    md_path.write_text(build_briefing_md(briefing), encoding="utf-8")

    exit_code = 0 if not degraded else 1
    print(f"[{'DEGRADED' if degraded else 'PASS'}] Agent briefing seed generated:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")
    print(f"  Degraded: {degraded}")
    print(f"  Source commit: {source_commit[:12] if source_commit else 'unknown'}")
    print(f"  Stale claims: {len(briefing['stale_claims'])}")
    print(f"  Stop conditions: {len(briefing['stop_conditions'])}")
    print(f"  Limitations: {len(briefing['limitations'])}")
    print(f"  LR: NO-GO")
    print(f"  Exit code: {exit_code} (0=PASS, 1=DEGRADED)")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
