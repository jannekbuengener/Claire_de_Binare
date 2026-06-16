"""Read-only guided onboarding tour for CDB.

Usage:
    python -m tools.onboarding_tour
    python -m tools.onboarding_tour --role developer
    .\\tools\\cdb.ps1 onboarding tour

Issue: #3249
Parent: #3246
"""

from __future__ import annotations

import argparse

try:
    from tools.onboarding_doctor import FORBIDDEN_OUTPUT_PATTERNS
except ModuleNotFoundError:  # direct script execution via tools/cdb.ps1
    from onboarding_doctor import FORBIDDEN_OUTPUT_PATTERNS


ROLE_ALIASES: dict[str, str] = {
    "developer": "developer",
    "dev": "developer",
    "agent": "agent",
    "docs": "docs",
    "docs maintainer": "docs",
    "docs-maintainer": "docs",
    "docs_maintainer": "docs",
    "validation": "validation",
    "validation/evidence": "validation",
    "validation-evidence": "validation",
    "evidence": "validation",
}

ROLE_LABELS: dict[str | None, str] = {
    None: "General",
    "developer": "Developer",
    "agent": "Agent",
    "docs": "Docs Maintainer",
    "validation": "Validation / Evidence",
}

PURPOSE = (
    "Claire de Binare is a deterministic, governance-first trading-system repo. "
    "The working repo is the active canon for code, docs, governance, and "
    "onboarding navigation."
)

SAFETY_LINES: list[str] = [
    "LR remains NO-GO.",
    "Board stage trade-capable is not Live-Go.",
    "No Echtgeld-Go.",
    "Docs/UI are orientation, not authority.",
    "This tour is read-only: no file writes, no Docker/runtime calls, and no DB or MCP mutation.",
]

DEFAULT_PATH: list[tuple[str, str]] = [
    ("README.md", "Repo landing page and safety boundary."),
    ("docs/index.md", "Shortest docs landing page for active surfaces."),
    (
        "docs/onboarding/DEVELOPER_VISUAL_START_HERE.md",
        "Visual onboarding map for developers and agents.",
    ),
    (
        "docs/onboarding/cdb_glossary.md",
        "Terminology anchor before you infer CDB-specific terms.",
    ),
    (
        "docs/onboarding/fresh_clone_rehearsal.md",
        "Read-only fresh-clone path to first safe confidence.",
    ),
]

ROLE_PATHS: dict[str, list[tuple[str, str]]] = {
    "developer": [
        ("README.md", "Repo landing page and safety boundary."),
        ("docs/index.md", "Fastest way into the active docs surfaces."),
        (
            "docs/onboarding/DEVELOPER_VISUAL_START_HERE.md",
            "Human-friendly visual start path.",
        ),
        (
            "docs/onboarding/fresh_clone_rehearsal.md",
            "Fresh-clone rehearsal before you touch implementation.",
        ),
        (
            "DEVELOPER_ONBOARDING.md",
            "Local setup, quick verification, and first PR workflow.",
        ),
    ],
    "agent": [
        ("AGENTS.md", "Resolve the repo root pointer first."),
        (
            "agents/AGENTS.md",
            "Read the canonical read order and status-surface rules.",
        ),
        (
            "agents/OPEN_CODE_AGENTS.md",
            "OpenCode shared contract, Brain Evidence rules, and gh-only GitHub writes.",
        ),
        (
            "docs/runbooks/CONTROL_REGISTER.md",
            "Board stage and current operating focus.",
        ),
        (
            "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
            "LR SSOT for Echtgeld Go/No-Go.",
        ),
    ],
    "docs": [
        ("README.md", "Repo landing page and onboarding boundary."),
        ("docs/index.md", "Primary docs navigation into onboarding surfaces."),
        (
            "docs/onboarding/DEVELOPER_VISUAL_START_HERE.md",
            "Visual pack and authority boundary wording.",
        ),
        (
            "docs/onboarding/cdb_glossary.md",
            "Terminology consistency surface.",
        ),
        (
            "tools/README.md",
            "Canonical tool discovery, including onboarding front doors.",
        ),
    ],
    "validation": [
        ("README.md", "Repo landing page and safety boundary."),
        (
            "docs/index.md",
            "Fast jump table into onboarding, evidence, tests, and runbooks.",
        ),
        (
            "docs/onboarding/fresh_clone_rehearsal.md",
            "Read-only baseline path for first safe validation steps.",
        ),
        (
            "tools/README.md",
            "Read-only onboarding doctor and docs guard entrypoints.",
        ),
        (
            "docs/onboarding/templates/evidence_doc_template.md",
            "Evidence template for scoped onboarding follow-ups.",
        ),
    ],
}

COMMON_SURFACES: list[tuple[str, str]] = [
    (
        "docs/onboarding/cdb_glossary.md",
        "Glossary for CDB-specific terms across all onboarding docs.",
    ),
    (
        "docs/onboarding/fresh_clone_rehearsal.md",
        "Fresh-clone rehearsal for first safe orientation.",
    ),
    (
        "python -m tools.onboarding_doctor | .\\tools\\cdb.ps1 onboarding doctor",
        "Read-only local onboarding doctor.",
    ),
    (
        "docs/onboarding/templates/",
        "Prompt, evidence, and PR-body templates.",
    ),
    (
        "#3251 planned next surface; use docs/onboarding/examples/first_issue_to_pr_flow.md until it lands.",
        "First-issue sandbox is not live yet, so the tour keeps it as a planned surface only.",
    ),
]

ROLE_HINTS: dict[str | None, str] = {
    None: "Use --role developer|agent|docs|validation|evidence for a narrower tour.",
    "developer": "Next safe command: python -m tools.onboarding_doctor",
    "agent": "If scope reaches module/service/contract/context/evidence surfaces, emit the Brain Evidence block before planning.",
    "docs": "After docs-only changes, run: python -m tools.validate_onboarding_docs",
    "validation": "For onboarding evidence slices, start from the evidence template and keep LR/Live claims out of scope.",
}


def _normalize_role(role: str | None) -> str | None:
    if role is None:
        return None

    normalized = ROLE_ALIASES.get(role.strip().lower())
    if normalized is None:
        allowed = "developer, agent, docs, validation, evidence"
        raise ValueError(f"unsupported role '{role}'. Allowed roles: {allowed}")
    return normalized


def _validate_output_safe(text: str) -> None:
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(text):
            raise ValueError("output contains forbidden pattern - potential secret leak")


def _format_steps(title: str, steps: list[tuple[str, str]]) -> list[str]:
    lines = [title]
    for index, (target, note) in enumerate(steps, start=1):
        lines.append(f"{index}. {target} - {note}")
    return lines


def render_tour(role: str | None = None) -> str:
    resolved_role = _normalize_role(role)
    path_steps = ROLE_PATHS.get(resolved_role, DEFAULT_PATH)

    lines: list[str] = [
        "=== CDB Onboarding Tour ===",
        "Mode: read-only orientation",
        f"Role: {ROLE_LABELS[resolved_role]}",
        "",
        "Purpose:",
        PURPOSE,
        "",
        "Safety boundaries:",
    ]
    lines.extend(f"- {line}" for line in SAFETY_LINES)
    lines.append("")
    lines.extend(_format_steps("First 5 active reads:", path_steps))
    lines.append("")
    lines.append("Active onboarding surfaces:")
    for target, note in COMMON_SURFACES:
        lines.append(f"- {target} - {note}")
    lines.append("")
    lines.append("Role hint:")
    lines.append(f"- {ROLE_HINTS[resolved_role]}")
    lines.append("- Guided tour command: python -m tools.onboarding_tour")
    lines.append("- PowerShell front door: .\\tools\\cdb.ps1 onboarding tour")
    return "\n".join(lines)


_HELP_EPILOG = """\
Examples:
  python -m tools.onboarding_tour
  python -m tools.onboarding_tour --role developer
  python -m tools.onboarding_tour --role agent
  .\\tools\\cdb.ps1 onboarding tour
  .\\tools\\cdb.ps1 onboarding tour --role docs
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only guided onboarding tour for CDB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_HELP_EPILOG,
    )
    parser.add_argument(
        "--role",
        help="Optional role path: developer, agent, docs, validation, evidence",
    )
    args = parser.parse_args(argv)

    try:
        output = render_tour(args.role)
    except ValueError as exc:
        parser.error(str(exc))

    _validate_output_safe(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
