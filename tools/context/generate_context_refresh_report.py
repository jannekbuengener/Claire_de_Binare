"""Report-only CDB Context Refresh Report Generator.

Generates three artifacts from local repo + GitHub state:
  - context_delta.json       (machine-readable delta)
  - context_refresh_summary.md (human-readable summary)
  - validation_report.json    (validator result or honest not-generated)

Usage:
    python tools/context/generate_context_refresh_report.py \\
        --repo-path <path> --output-dir <dir> --base-ref <ref> --head-ref <ref> --repo <name>
    python tools/context/generate_context_refresh_report.py --help

Exit codes:
    0 - report generated (success or degraded)
    1 - fail-closed (core data missing)
    2 - unexpected error

No DB writes. No secrets. No runtime changes. LR remains NO-GO.
#3287
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "context_refresh_report.v1"
VALIDATION_SCHEMA_VERSION = "validation_report.v1"


def run_git(cmd: list[str], repo_path: str) -> str:
    result = subprocess.run(
        ["git"] + cmd,
        capture_output=True,
        text=True,
        cwd=repo_path,
        timeout=30,
    )
    if result.returncode != 0:
        return f"<error: {result.stderr.strip()}>"
    return result.stdout.strip()


def run_gh(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            ["gh"] + cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return f"<error: {result.stderr.strip()}>"
        return result.stdout.strip()
    except FileNotFoundError:
        return "<error: gh CLI not available>"


def collect_open_issues() -> list[dict[str, Any]]:
    raw = run_gh(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--json",
            "number,title,state,labels,updatedAt",
            "--limit",
            "50",
        ]
    )
    if raw.startswith("<error"):
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def collect_open_prs() -> list[dict[str, Any]]:
    raw = run_gh(
        [
            "pr",
            "list",
            "--state",
            "open",
            "--json",
            "number,title,state,headRefName,baseRefName",
            "--limit",
            "50",
        ]
    )
    if raw.startswith("<error"):
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def get_changed_canon_paths(repo_path: str, base_ref: str, head_ref: str) -> list[str]:
    canon_prefixes = [
        "AGENTS.md",
        "agents/",
        "knowledge/governance/",
        "knowledge/CDB_KNOWLEDGE_HUB.md",
        "docs/meta/",
        "CURRENT_STATUS.md",
        "docs/live-readiness/",
        "docs/runbooks/CONTROL_REGISTER.md",
    ]
    diff_output = run_git(
        ["diff", "--name-only", f"{base_ref}...{head_ref}"],
        repo_path,
    )
    if diff_output.startswith("<error"):
        return []
    changed = [line for line in diff_output.split("\n") if line.strip()]
    return [
        p for p in changed if any(p.startswith(prefix) for prefix in canon_prefixes)
    ]


def build_safety_boundaries() -> dict[str, Any]:
    return {
        "lr_status": "NO-GO",
        "board_stage_is_live_go": False,
        "real_money_go": False,
        "productive_db_writes_allowed": False,
        "secrets_in_outputs_allowed": False,
        "trading_state_ingestion_allowed": False,
    }


def build_context_delta(
    repo_path: str,
    base_ref: str,
    head_ref: str,
    repo_name: str,
    utc_now: str,
) -> dict[str, Any]:
    limitations: list[str] = []
    safety = build_safety_boundaries()

    head_commit = run_git(["rev-parse", head_ref], repo_path)
    base_commit = run_git(["rev-parse", base_ref], repo_path)

    if head_commit.startswith("<error") or base_commit.startswith("<error"):
        limitations.append("Git ref resolution failed — some fields may be incomplete.")
        head_commit = head_commit if not head_commit.startswith("<error") else ""
        base_commit = base_commit if not base_commit.startswith("<error") else ""

    open_issues = collect_open_issues()
    open_prs = collect_open_prs()
    if not open_issues and not open_prs:
        limitations.append(
            "GitHub CLI (gh) not available or API unreachable — issue/PR data is empty."
        )

    changed_canon = get_changed_canon_paths(repo_path, base_ref, head_ref)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now,
        "base_ref": base_ref,
        "head_ref": head_ref,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "repo": repo_name,
        "open_issues_summary": {
            "total_count": len(open_issues),
            "issues": [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "labels": [label["name"] for label in i.get("labels", [])],
                    "updated_at": i.get("updatedAt", ""),
                }
                for i in open_issues
            ],
        },
        "open_prs_summary": {
            "total_count": len(open_prs),
            "prs": [
                {
                    "number": p["number"],
                    "title": p["title"],
                    "state": p["state"],
                    "head_ref": p.get("headRefName", ""),
                    "base_ref": p.get("baseRefName", ""),
                }
                for p in open_prs
            ],
        },
        "changed_canon_paths_if_available": changed_canon,
        "limitations": limitations,
        "safety_boundaries": safety,
    }


def build_validation_report(
    delta: dict[str, Any],
    output_dir: str,
) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    warnings: list[str] = []

    if delta["head_commit"].startswith("<error"):
        blocked_reasons.append("Git HEAD resolution failed.")
    if delta["base_commit"].startswith("<error"):
        blocked_reasons.append("Git base ref resolution failed.")

    if (
        not delta["open_issues_summary"]["issues"]
        and not delta["open_prs_summary"]["prs"]
    ):
        warnings.append("No open issues or PRs found. gh CLI may not be available.")

    if len(delta["limitations"]) > 0:
        warnings.extend(delta["limitations"])

    status = (
        "PASS_WITH_LIMITATIONS"
        if (blocked_reasons or warnings) and not blocked_reasons
        else "PASS" if not blocked_reasons else "BLOCKED"
    )

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": status,
        "validator_used": "tools/context/generate_context_refresh_report.py",
        "validator_exit_code": 0 if not blocked_reasons else 1,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "artifact_paths": {
            "context_delta": f"{output_dir}/context_delta.json",
            "context_refresh_summary": f"{output_dir}/context_refresh_summary.md",
        },
        "limitations": [
            "Report-only: no DB writes, no brain apply, no runtime changes.",
            "LR remains NO-GO. No Live-Go. No Echtgeld-Go.",
            "Context delta is not a validated context package; no records field.",
            "Validation report is self-assessment, not context package validator output.",
        ],
    }


def build_summary_md(
    delta: dict[str, Any],
    validation: dict[str, Any],
    utc_now: str,
) -> str:
    lines: list[str] = []

    lines.append("# CDB Context Refresh Report")
    lines.append("")
    lines.append(f"- **Run timestamp (UTC):** {utc_now}")
    lines.append("- **Run timestamp (Europe/Berlin):** " + _utc_to_berlin_str(utc_now))
    lines.append(
        f"- **Schedule:** GitHub Actions cron runs in UTC. "
        f"Monday/Thursday 08:00 UTC = 10:00 Europe/Berlin (CEST, summer) "
        f"or 09:00 (CET, winter)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Source Summary")
    lines.append("")
    lines.append(f"- **Repo:** {delta['repo']}")
    lines.append(f"- **Base ref:** {delta['base_ref']} @ `{delta['base_commit'][:12]}`")
    lines.append(f"- **Head ref:** {delta['head_ref']} @ `{delta['head_commit'][:12]}`")
    lines.append(
        f"- **Changed canon paths:** {len(delta['changed_canon_paths_if_available'])}"
    )
    lines.append("")
    lines.append("## Open PRs / Issues")
    lines.append("")
    lines.append(f"- **Open issues:** {delta['open_issues_summary']['total_count']}")
    for issue in delta["open_issues_summary"]["issues"]:
        labels = ", ".join(issue["labels"]) if issue["labels"] else "none"
        lines.append(
            f"  - #{issue['number']} {issue['title']} ({issue['state']}, labels: {labels})"
        )
    lines.append(f"- **Open PRs:** {delta['open_prs_summary']['total_count']}")
    for pr in delta["open_prs_summary"]["prs"]:
        lines.append(
            f"  - #{pr['number']} {pr['title']} ({pr['state']}, {pr['head_ref']} → {pr['base_ref']})"
        )
    lines.append("")
    lines.append("## Validator Result")
    lines.append("")
    lines.append(f"- **Status:** {validation['status']}")
    lines.append(f"- **Blocked reasons:** {len(validation['blocked_reasons'])}")
    for reason in validation["blocked_reasons"]:
        lines.append(f"  - BLOCKED: {reason}")
    lines.append(f"- **Warnings:** {len(validation['warnings'])}")
    for warning in validation["warnings"]:
        lines.append(f"  - WARNING: {warning}")
    lines.append("")
    lines.append("## Safety Boundaries")
    lines.append("")
    for key, val in delta["safety_boundaries"].items():
        lines.append(f"- **{key}:** {val}")
    lines.append("")
    lines.append("## Known Limitations")
    lines.append("")
    lines.append(
        "- Report-only: no DB writes, no brain apply (#3289), no runtime changes."
    )
    lines.append("- LR remains NO-GO. No Live-Go. No Echtgeld-Go.")
    lines.append("- Issue/PR data is a point-in-time snapshot via `gh` CLI.")
    lines.append(
        "- Changed canon paths reflect diff from base to head at generation time."
    )
    if delta["limitations"]:
        lines.append("")
        lines.append("### Runtime Limitations")
        for lim in delta["limitations"]:
            lines.append(f"- {lim}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*This is a report-only artifact. "
        "No productive DB writes, no brain apply, no runtime changes. "
        "LR remains NO-GO.*"
    )

    return "\n".join(lines)


def _utc_to_berlin_str(utc_str: str) -> str:
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return f"{dt.hour + 2:02d}:{dt.minute:02d} (CEST) / {dt.hour + 1:02d}:{dt.minute:02d} (CET)"
    except (ValueError, TypeError):
        return "<could not convert>"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report-only CDB Context Refresh Report Generator (#3287)",
    )
    parser.add_argument(
        "--repo-path",
        required=True,
        help="Path to the local repo checkout.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for generated artifacts.",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Base git ref for diff (default: origin/main).",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git ref for diff (default: HEAD).",
    )
    parser.add_argument(
        "--repo",
        default="Claire_de_Binare",
        help="Repository name (default: Claire_de_Binare).",
    )
    args = parser.parse_args()

    utc_now = cdb_utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(repo_path):
        print(f"[FAIL] Repo path does not exist: {repo_path}", file=sys.stderr)
        return 2

    delta = build_context_delta(
        repo_path=repo_path,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        repo_name=args.repo,
        utc_now=utc_now,
    )

    validation = build_validation_report(delta, args.output_dir)

    summary_md = build_summary_md(delta, validation, utc_now)

    delta_path = output_dir / "context_delta.json"
    delta_path.write_text(
        json.dumps(delta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary_path = output_dir / "context_refresh_summary.md"
    summary_path.write_text(summary_md, encoding="utf-8")

    validation_path = output_dir / "validation_report.json"
    validation_path.write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"[PASS] Context refresh report generated:")
    print(f"  Delta:  {delta_path}")
    print(f"  Summary: {summary_path}")
    print(f"  Validation: {validation_path}")
    print(f"  Limitations: {len(delta['limitations'])}")
    print(f"  Validation status: {validation['status']}")
    print(f"  LR: NO-GO")

    return 0


if __name__ == "__main__":
    sys.exit(main())
