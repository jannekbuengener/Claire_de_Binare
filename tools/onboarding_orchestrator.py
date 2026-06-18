"""CDB onboarding orchestrator — single smart read-only entrypoint.

Usage:
    python -m tools.onboarding_orchestrator
    python -m tools.onboarding_orchestrator --mode check-only
    python -m tools.onboarding_orchestrator --format json
    .\\tools\\cdb.ps1 onboarding

Exit codes:
    0 - status PASS or SETUP_WARN (onboarding usable)
    1 - status BLOCKED (onboarding not usable)
    2 - CLI usage error

This tool is read-only by default:
    - No file writes, no report, no setup mutation, no Docker, no secrets.
    - Status card ends with numbered next-option hints (no open yes/no question).

Read Order:
    agents/AGENTS.md § Read Order -> Context Brain Preflight -> Live Truth ->
    Bootloader check -> Scenario integrity -> Doctor readiness -> Verdict.

Output contract:
    CDB Onboarding
    Status: PASS | SETUP_WARN | BLOCKED
    ...
    Keine Änderungen vorgenommen.
    LR remains NO-GO.
    trade-capable ist kein Live-Go.
    Nächste Optionen:
    1. Setup-Plan anzeigen
    2. Setup vorbereiten
    3. Onboarding-Report schreiben
    4. Ersten sicheren Issue-Workflow simulieren
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent

CANONICAL_BOOTLOADER_FILES: list[str] = [
    "AGENTS.md",
    "agents/AGENTS.md",
]

SCENARIO_FILE = (
    "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md"
)

REQUIRED_SCENARIO_TERMS: list[str] = [
    "onboarding-scenario-001",
    "fresh agent safe-work drill",
    "jannek-ops-go",
    "infra-mutation-gate",
    "repo_fallback_reason",
    "insufficient_evidence",
    "lr remains no-go",
    "/onboarding",
]

FORBIDDEN_OUTPUT_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)\b(token|secret|password|passwd|api[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)SURREAL_(?:PASS|USER)\s*=\s*\S+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"https?://[^\s\"']+"),
]

NEXT_OPTIONS: list[str] = [
    "1. Setup-Plan anzeigen",
    "2. Setup vorbereiten",
    "3. Onboarding-Report schreiben",
    "4. Ersten sicheren Issue-Workflow simulieren",
]


def _run_cmd(
    cmd: str,
    timeout: float = 15.0,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[int, str, str]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["shell"] = True
    else:
        kwargs["shell"] = False
    try:
        if runner is not None:
            proc = runner(cmd, **kwargs)
        else:
            proc = subprocess.run(cmd, **kwargs)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode, out, err
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        return -1, "", str(exc)


@dataclass
class OrchestratorOutput:
    status: str = "BLOCKED"
    bootloader_ok: str = "FAIL"
    scenario_ok: str = "FAIL"
    lr_ok: str = "FAIL"
    doctor_reachable: str = "SKIP"
    env_file: str = "FAIL"
    context_doctor: str = "SKIP"
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "bootloader": self.bootloader_ok,
            "scenario": self.scenario_ok,
            "lr_note": self.lr_ok,
            "doctor_reachable": self.doctor_reachable,
            "env_file": self.env_file,
            "context_doctor": self.context_doctor,
            "warnings": self.warnings,
            "blockers": self.blockers,
            "details": self.details,
        }


def _check_bootloader_files(root: Path) -> tuple[str, list[str]]:
    missing: list[str] = []
    for rel_path in CANONICAL_BOOTLOADER_FILES:
        if not (root / rel_path).is_file():
            missing.append(rel_path)
    if missing:
        return "FAIL", missing
    return "PASS", []


def _check_scenario_file(root: Path) -> tuple[str, list[str]]:
    full_path = root / SCENARIO_FILE
    if not full_path.is_file():
        return "FAIL", [f"Scenario file not found: {SCENARIO_FILE}"]
    try:
        text = full_path.read_text(encoding="utf-8", errors="replace").lower()
        missing = [t for t in REQUIRED_SCENARIO_TERMS if t not in text]
        if missing:
            return "WARN", [f"Scenario missing terms: {missing}"]
        return "PASS", []
    except (OSError, UnicodeDecodeError) as exc:
        return "FAIL", [f"Cannot read scenario file: {exc}"]


def _check_lr_doc(root: Path) -> tuple[str, str]:
    lr_path = root / "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"
    if not lr_path.is_file():
        return "FAIL", "LR doc not found"
    text = lr_path.read_text(encoding="utf-8", errors="replace")
    if "NO-GO" in text:
        return "PASS", "NO-GO confirmed"
    no_go_variants = [v for v in ["No-Go", "no-go", "no go", "No Go"] if v in text]
    if no_go_variants:
        return "PASS", f"NO-GO variant found: {no_go_variants[0]}"
    return "FAIL", "NO-GO not found in LR doc"


def _check_env_file(root: Path) -> tuple[str, str]:
    env_path = root / ".env"
    if env_path.is_file():
        return "WARN", ".env exists (setup may be partially complete)"
    example = root / ".env.example"
    if example.is_file():
        return "SETUP_WARN", ".env fehlt (setup warn, kein blocker)"
    return "SETUP_WARN", ".env fehlt und kein .env.example"


def _check_doctor_reachable(
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[str, str]:
    cmd = "python -m tools.onboarding_doctor --format json"
    rc, out, _ = _run_cmd(cmd, timeout=15.0, runner=runner)
    if rc == 0:
        return "PASS", "onboarding_doctor reachable"
    return "SETUP_WARN", "Context Doctor nicht initialisiert (setup warn, kein blocker)"


def _check_context_doctor(
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[str, str]:
    cmd = "python -m tools.surrealdb.context_onboarding_doctor --skip-mcp --skip-schema 2>&1"
    rc, _, _ = _run_cmd(cmd, timeout=15.0, runner=runner)
    if rc == 0:
        return "PASS", "context_doctor reachable"
    return "SETUP_WARN", "Context Doctor nicht initialisiert (setup warn, kein blocker)"


def _validate_output_safe(text: str) -> None:
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(text):
            raise ValueError("output contains forbidden pattern — potential secret leak")


def build_verdict(
    root: Path | None = None,
    *,
    doctor_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    context_doctor_runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> OrchestratorOutput:
    r = root or REPO_ROOT
    output = OrchestratorOutput()

    # 1. Bootloader files
    bl_status, bl_missing = _check_bootloader_files(r)
    output.bootloader_ok = bl_status
    if bl_status == "FAIL":
        output.blockers.append(
            f"Fehlender Bootloader: {', '.join(bl_missing)}"
        )

    # 2. Scenario file
    sc_status, sc_issues = _check_scenario_file(r)
    output.scenario_ok = sc_status
    if sc_status == "FAIL":
        output.blockers.append(f"Fehlendes Szenario-Dokument: {SCENARIO_FILE}")
    elif sc_status == "WARN":
        output.warnings.extend(sc_issues)

    # 3. LR doc
    lr_status, lr_detail = _check_lr_doc(r)
    output.lr_ok = lr_status
    output.details["lr"] = lr_detail

    # 4. Env file (setup warn only)
    env_status, env_detail = _check_env_file(r)
    output.env_file = env_status
    if env_status == "SETUP_WARN":
        output.warnings.append(env_detail)

    # 5. Doctor reachability
    doc_status, doc_detail = _check_doctor_reachable(runner=doctor_runner)
    output.doctor_reachable = doc_status
    if doc_status == "SETUP_WARN":
        output.warnings.append(doc_detail)

    # 6. Context doctor
    ctx_status, ctx_detail = _check_context_doctor(runner=context_doctor_runner)
    output.context_doctor = ctx_status
    if ctx_status == "SETUP_WARN":
        output.warnings.append(ctx_detail)

    # Final status
    if output.blockers:
        output.status = "BLOCKED"
    elif output.warnings:
        output.status = "SETUP_WARN"
    else:
        output.status = "PASS"

    return output


def _safe_summary(text: str, max_len: int = 100) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def format_output(report: OrchestratorOutput, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)

    lines: list[str] = [
        "=== CDB Onboarding ===",
        f"Status: {report.status}",
        "",
    ]

    lines.append("Prüfungen:")
    lines.append(f"  Bootloader: [{report.bootloader_ok}]")
    lines.append(f"  Szenario-Dokument: [{report.scenario_ok}]")
    lines.append(f"  LR-Status: [{report.lr_ok}] — {report.details.get('lr', '')}")
    lines.append(f"  .env: [{report.env_file}]")
    lines.append(f"  onboarding_doctor: [{report.doctor_reachable}]")
    lines.append(f"  context_doctor: [{report.context_doctor}]")
    lines.append("")

    if report.blockers:
        lines.append("BLOCKER:")
        for b in report.blockers:
            lines.append(f"  ! {_safe_summary(b, 120)}")
        lines.append("")

    if report.warnings:
        lines.append("WARNINGS:")
        for w in report.warnings:
            lines.append(f"  * {_safe_summary(w, 120)}")
        lines.append("")

    lines.append("Keine Änderungen vorgenommen.")
    lines.append("LR remains NO-GO.")
    lines.append("trade-capable ist kein Live-Go.")
    lines.append("")

    lines.append("Nächste Optionen:")
    for opt in NEXT_OPTIONS:
        lines.append(f"  {opt}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CDB onboarding orchestrator — single smart read-only entrypoint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m tools.onboarding_orchestrator
  python -m tools.onboarding_orchestrator --format json
  .\\tools\\cdb.ps1 onboarding

Exit codes:
  0  status PASS or SETUP_WARN
  1  status BLOCKED
  2  CLI usage error
""",
    )
    parser.add_argument(
        "--mode",
        choices=("default", "check-only"),
        default="default",
        help="Operation mode (default: default, read-only)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    report = build_verdict()

    try:
        output = format_output(report, args.format)
        _validate_output_safe(output)
        print(output)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 1 if report.status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
