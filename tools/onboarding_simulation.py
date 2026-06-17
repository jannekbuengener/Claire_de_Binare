"""Deterministic read-only onboarding simulation runner for CDB.

Makes the /onboarding slash-skill thin and testable. Emits a reproducible
simulation of the full CDB onboarding flow without any file writes, GitHub
mutations, branch creation, PR creation, runtime/Docker/DB/MCP actions, or
secret exposure.

Usage:
    python -m tools.onboarding_simulation
    python -m tools.onboarding_simulation --role agent --mode first-issue-dry-run
    python -m tools.onboarding_simulation --role developer --format json
    .\\tools\\cdb.ps1 onboarding simulate

Output contract:
    ONBOARDING_START -> Bootloader Plan -> Live Truth Plan -> Tour Path ->
    Doctor / Validator Plan -> First-Issue Dry Run -> PR / LOCK Simulation ->
    HOLD Conditions -> Final Verdict

Final verdict enum:
    READY_FOR_REAL_FIRST_ISSUE | HOLD_ONBOARDING_GAP |
    BLOCKED_BOOTLOADER | BLOCKED_LIVE_TRUTH | BLOCKED_GOVERNANCE

Issue: #3273
Parent: #3271
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

ROLE_ALIASES: dict[str, str] = {
    "developer": "developer",
    "dev": "developer",
    "agent": "agent",
    "docs": "docs",
    "docs-maintainer": "docs",
    "validation": "validation",
    "evidence": "validation",
}

ROLE_LABELS: dict[str, str] = {
    "developer": "Developer",
    "agent": "Agent",
    "docs": "Docs Maintainer",
    "validation": "Validation / Evidence",
}

VERDICT_ENUM: tuple[str, ...] = (
    "READY_FOR_REAL_FIRST_ISSUE",
    "HOLD_ONBOARDING_GAP",
    "BLOCKED_BOOTLOADER",
    "BLOCKED_LIVE_TRUTH",
    "BLOCKED_GOVERNANCE",
)

FORBIDDEN_OUTPUT_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)\b(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)SURREAL_(?:PASS|USER)\s*=\s*\S+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"https?://[^\s\"']+"),
    re.compile(r"(?i)(?:api|private|secret)_key[=:]\s*\S+"),
]


@dataclass
class SimulationOutput:
    role: str
    mode: str
    verdict: str
    sections: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": ROLE_LABELS.get(self.role, self.role),
            "mode": self.mode,
            "verdict": self.verdict,
            "sections": self.sections,
        }


def _normalize_role(role: str) -> str:
    normalized = ROLE_ALIASES.get(role.strip().lower())
    if normalized is None:
        allowed = "developer, agent, docs, validation, evidence"
        raise ValueError(f"unsupported role '{role}'. Allowed roles: {allowed}")
    return normalized


def _normalize_mode(mode: str) -> str:
    allowed = ("first-issue-dry-run", "check-only")
    if mode not in allowed:
        raise ValueError(
            f"unsupported mode '{mode}'. Allowed modes: {', '.join(allowed)}"
        )
    return mode


def _build_bootloader_plan(role: str) -> list[str]:
    lines: list[str] = [
        "Bootloader Plan:",
        "  1. Read AGENTS.md (repo root pointer).",
        "  2. Read agents/AGENTS.md (canonical registry, Read Order, Brain Evidence Gate).",
        "  3. Read agents/OPEN_CODE_AGENTS.md (shared contract, skill routing).",
        "  4. Run Context Brain Preflight (context_brain_attempted=true).",
        "  5. If MCP tools unavailable: fallback to repo with repo_fallback_reason=tool_blocked.",
    ]
    if role == "agent":
        lines.extend(
            [
                "  6. Read agents/roles/CODEX.md for role-specific contract.",
                "  7. Verify Brain Evidence block fields before planning.",
            ]
        )
    return lines


def _build_live_truth_plan() -> list[str]:
    return [
        "Live Truth Plan:",
        "  1. GitHub live: issue state, PRs, checks via 'gh'.",
        "  2. Repo live: git fetch, status, diff.",
        "  3. Ledger: CURRENT_STATUS.md (context only, not live truth).",
        "  4. LR SSOT: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md (NO-GO).",
        "  5. Control: docs/runbooks/CONTROL_REGISTER.md (stage:trade-capable).",
    ]


def _build_tour_path(role: str) -> list[str]:
    lines: list[str] = [
        "Tour Path:",
        "  1. README.md - repo landing page and safety boundary.",
        "  2. docs/index.md - shortest active docs landing page.",
        "  3. docs/onboarding/DEVELOPER_VISUAL_START_HERE.md - visual onboarding map.",
        "  4. docs/onboarding/cdb_glossary.md - terminology anchor.",
        "  5. docs/onboarding/fresh_clone_rehearsal.md - read-only fresh-clone path.",
    ]
    if role == "agent":
        lines.append(
            "  6. docs/onboarding/repo_brain_context_intelligence.md - Repo Brain first use.",
        )
    elif role == "developer":
        lines.append(
            "  6. DEVELOPER_ONBOARDING.md - local setup and first PR workflow.",
        )
    return lines


def _build_doctor_validator_plan() -> list[str]:
    return [
        "Doctor / Validator Plan:",
        "  1. python -m tools.onboarding_doctor - read-only local check.",
        "  2. python -m tools.validate_onboarding_docs - active surface validation.",
        "  3. make context-doctor - Context Intelligence preflight.",
        "  All three are read-only; no stack, Docker, DB, or MCP mutation.",
    ]


def _build_first_issue_dry_run() -> list[str]:
    return [
        "First-Issue Dry Run:",
        "  Scope: docs-only change (e.g. add term to cdb_glossary.md).",
        "  1. Branch from origin/main: docs/<issue>-<slug>.",
        "  2. Edit a single safe file under docs/onboarding/.",
        "  3. Run: python -m tools.validate_onboarding_docs.",
        "  4. Run: ruff check .",
        "  5. Commit with conventional commit message.",
        "  6. Push branch.",
    ]


def _build_pr_lock_simulation() -> list[str]:
    return [
        "PR / LOCK Simulation:",
        "  1. PR body MUST contain: Delivered, Validation, Non-Goals, Safety, Restunsicherheiten.",
        "  2. Post LOCK: comment on the PR before any further mutation.",
        "  3. Required checks: ci (Unit/Integration + Lint).",
        "  4. Required checks: policy-gate.",
        "  5. Wait for CI green before merge.",
        "  6. Squash-merge after green + approved.",
    ]


def _build_hold_conditions() -> list[str]:
    return [
        "HOLD Conditions:",
        "  ONBOARDING_HOLD if:",
        "  - git fetch / gh issue view fail.",
        "  - Worktree dirty with unknown changes.",
        "  - Local main behind origin/main.",
        "  - Target issue not readable via gh.",
        "  - Context Brain Preflight fails without valid fallback reason.",
        "  - Bootloader files missing or unreadable.",
        "  - Required checks red and not scope-fixable.",
        "  - Diff shows scope growth beyond allowed surfaces.",
        "  - Secrets or LR/Live boundaries touched.",
    ]


def _build_final_verdict(role: str, mode: str) -> str:
    if mode == "check-only":
        return "HOLD_ONBOARDING_GAP"
    return "READY_FOR_REAL_FIRST_ISSUE"


def _build_safety_lines() -> list[str]:
    return [
        "LR remains NO-GO.",
        "Board stage trade-capable is not Live-Go.",
        "No Echtgeld-Go.",
        "This simulation is read-only: no file writes, no GitHub writes, no Docker/runtime/DB/MCP mutation.",
    ]


def _build_context_brain_note() -> list[str]:
    return [
        "Context Brain Note:",
        "  context_brain_attempted=true (required by bootloader).",
        "  If MCP tools unavailable: repo_fallback_used=true, repo_fallback_reason=tool_blocked.",
        "  If Context Brain MCP tools respond: use records, not caller metadata.",
        "  No DB-backed claims without tool/query/record evidence.",
    ]


def _validate_output_safe(text: str) -> None:
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(text):
            raise ValueError("output contains forbidden pattern - potential secret leak")


def render_simulation(role: str = "agent", mode: str = "first-issue-dry-run") -> str:
    resolved_role = _normalize_role(role)
    resolved_mode = _normalize_mode(mode)
    verdict = _build_final_verdict(resolved_role, resolved_mode)
    role_label = ROLE_LABELS[resolved_role]

    sections: dict[str, list[str]] = {
        "context_brain": _build_context_brain_note(),
        "bootloader": _build_bootloader_plan(resolved_role),
        "live_truth": _build_live_truth_plan(),
        "tour": _build_tour_path(resolved_role),
        "doctor_validator": _build_doctor_validator_plan(),
        "first_issue": _build_first_issue_dry_run(),
        "pr_lock": _build_pr_lock_simulation(),
        "hold_conditions": _build_hold_conditions(),
    }

    lines: list[str] = [
        "ONBOARDING_START",
        f"mode: {resolved_mode}",
        f"role: {role_label}",
        "writes: disabled",
        "github_writes: disabled",
        "lr: NO-GO",
        "",
    ]

    for section_name, section_lines in sections.items():
        lines.extend(section_lines)
        lines.append("")

    lines.append(f"Final Verdict: {verdict}")
    lines.append("")

    lines.append("Safety boundaries:")
    for sl in _build_safety_lines():
        lines.append(f"  - {sl}")

    return "\n".join(lines)


def render_simulation_json(role: str = "agent", mode: str = "first-issue-dry-run") -> str:
    resolved_role = _normalize_role(role)
    resolved_mode = _normalize_mode(mode)
    verdict = _build_final_verdict(resolved_role, resolved_mode)

    output = SimulationOutput(role=resolved_role, mode=resolved_mode, verdict=verdict)
    output.sections = {
        "context_brain": _build_context_brain_note(),
        "bootloader": _build_bootloader_plan(resolved_role),
        "live_truth": _build_live_truth_plan(),
        "tour": _build_tour_path(resolved_role),
        "doctor_validator": _build_doctor_validator_plan(),
        "first_issue": _build_first_issue_dry_run(),
        "pr_lock": _build_pr_lock_simulation(),
        "hold_conditions": _build_hold_conditions(),
    }
    return json.dumps(output.to_dict(), indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic read-only onboarding simulation runner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m tools.onboarding_simulation
  python -m tools.onboarding_simulation --role agent --mode first-issue-dry-run
  python -m tools.onboarding_simulation --role developer --format json
  .\\tools\\cdb.ps1 onboarding simulate
""",
    )
    parser.add_argument(
        "--role",
        default="agent",
        help="Role path: developer, agent, docs, validation, evidence (default: agent)",
    )
    parser.add_argument(
        "--mode",
        choices=("first-issue-dry-run", "check-only"),
        default="first-issue-dry-run",
        help="Simulation mode (default: first-issue-dry-run)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    try:
        role = args.role
        mode = args.mode
        if args.format == "json":
            output = render_simulation_json(role, mode)
        else:
            output = render_simulation(role, mode)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    _validate_output_safe(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
