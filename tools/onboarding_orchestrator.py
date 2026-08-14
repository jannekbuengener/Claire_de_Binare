"""CDB onboarding orchestrator - single smart read-only entrypoint.

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
    - The two-option setup confirmation prompt appears only in setup-confirmation state.

Read Order:
    agents/AGENTS.md § Read Order -> Context Brain Preflight -> Live Truth ->
    Bootloader check -> Scenario integrity -> Doctor readiness -> Verdict.

Output contract:
    CDB Onboarding
    Status: PASS | SETUP_WARN | BLOCKED
    ...
    No changes made.
    LR remains NO-GO.
    trade-capable is not Live-Go.

    Moechtest du das Onboarding-Setup jetzt ausfuehren?

    1. Ja
    2. Abbruch
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
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

SCENARIO_FILE = "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md"

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

SETUP_PROMPT_LINES: list[str] = [
    "Moechtest du das Onboarding-Setup jetzt ausfuehren?",
    "",
    "1. Ja",
    "2. Abbruch",
]

SETUP_APPROVED = "setup-approved"
SETUP_ABORTED = "setup-aborted"

STATUS_ONLY = "STATUS_ONLY"
SETUP_REQUIRED = "SETUP_REQUIRED"
SETUP_CONFIRMATION_PENDING = "SETUP_CONFIRMATION_PENDING"
DRY_RUN_COMPLETE = "DRY_RUN_COMPLETE"
BLOCKED_STATE = "BLOCKED"

ACTION_STATUS_ONLY = "status_only"
ACTION_APPROVE_SETUP = "approve_setup"
ACTION_REQUEST_SETUP_GO = "request_setup_go"
ACTION_ABORT = "abort"

SETUP_APPROVAL_INPUTS = {"1", "ja", "yes"}
SETUP_ABORT_INPUTS = {"2", "nein", "no", "abbruch", "cancel"}


def _run_cmd(
    cmd: str | list[str],
    timeout: float = 15.0,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[int, str, str]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "errors": "replace",
    }
    if isinstance(cmd, str):
        run_cmd: str | list[str]
        if os.name == "nt":
            run_cmd = cmd
            kwargs["shell"] = True
        else:
            run_cmd = shlex.split(cmd)
            kwargs["shell"] = False
    else:
        run_cmd = list(cmd)
        kwargs["shell"] = False
    try:
        if runner is not None:
            proc = runner(run_cmd, **kwargs)
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            return proc.returncode, out, err

        popen_kwargs = dict(kwargs)
        popen_kwargs.pop("timeout")
        popen_kwargs.pop("capture_output")
        popen_kwargs["stdout"] = subprocess.PIPE
        popen_kwargs["stderr"] = subprocess.PIPE
        if os.name == "nt":
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        else:
            popen_kwargs["start_new_session"] = True
        proc = subprocess.Popen(run_cmd, **popen_kwargs)
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process_tree(proc)
            out, err = proc.communicate(timeout=5)
            return (
                -1,
                "",
                f"command timed out after {timeout:g}s; process tree terminated",
            )
        return proc.returncode, (out or "").strip(), (err or "").strip()
    except (
        FileNotFoundError,
        OSError,
        subprocess.TimeoutExpired,
        UnicodeDecodeError,
    ) as exc:
        return -1, "", str(exc)


def _terminate_process_tree(proc: subprocess.Popen[str]) -> None:
    """Terminate a timed-out child and every descendant that can hold its pipes."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return
    os.killpg(os.getpgid(proc.pid), 15)


@dataclass
class OrchestratorOutput:
    mode: str = "default"
    status: str = "BLOCKED"
    state: str = BLOCKED_STATE
    check_scope: str = "onboarding_status_default"
    skipped_checks: list[str] = field(default_factory=list)
    bootloader_ok: str = "FAIL"
    scenario_ok: str = "FAIL"
    lr_ok: str = "FAIL"
    doctor_reachable: str = "SKIP"
    env_file: str = "FAIL"
    context_doctor: str = "SKIP"
    blocking: bool = True
    requires_explicit_setup_go: bool = False
    setup_prompt_visible: bool = False
    allowed_next_actions: list[str] = field(default_factory=list)
    warning_semantics: str = (
        "WARN means onboarding remains read-only usable, but setup or follow-up is still required."
    )
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "status": self.status,
            "state": self.state,
            "check_scope": self.check_scope,
            "skipped_checks": self.skipped_checks,
            "bootloader": self.bootloader_ok,
            "scenario": self.scenario_ok,
            "lr_note": self.lr_ok,
            "doctor_reachable": self.doctor_reachable,
            "env_file": self.env_file,
            "context_doctor": self.context_doctor,
            "blocking": self.blocking,
            "requires_explicit_setup_go": self.requires_explicit_setup_go,
            "setup_prompt_visible": self.setup_prompt_visible,
            "allowed_next_actions": self.allowed_next_actions,
            "warning_semantics": self.warning_semantics,
            "warnings": self.warnings,
            "blockers": self.blockers,
            "details": self.details,
        }


def get_setup_prompt_text() -> str:
    return "\n".join(SETUP_PROMPT_LINES)


def normalize_setup_prompt_input(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in SETUP_APPROVAL_INPUTS:
        return SETUP_APPROVED
    if normalized in SETUP_ABORT_INPUTS:
        return SETUP_ABORTED
    return None


def prompt_for_setup_confirmation(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] | None = None,
) -> str:
    prompt_text = get_setup_prompt_text()
    while True:
        if output_fn is not None:
            output_fn(prompt_text)
            raw_value = input_fn("")
        else:
            raw_value = input_fn(f"{prompt_text}\n")
        decision = normalize_setup_prompt_input(raw_value)
        if decision is not None:
            return decision


def _module_cmd(module: str, *args: str) -> list[str]:
    return [sys.executable, "-m", module, *args]


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
        return "PASS", ".env found"
    example = root / ".env.example"
    if example.is_file():
        return "WARN", ".env missing (setup required, non-blocking)"
    return "WARN", ".env missing and no .env.example found"


def _check_doctor_reachable(
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[str, str]:
    cmd = _module_cmd("tools.onboarding_doctor", "--format", "json")
    rc, out, _ = _run_cmd(cmd, timeout=15.0, runner=runner)
    if rc == 0:
        try:
            payload = json.loads(out) if out else {}
        except json.JSONDecodeError:
            payload = {}
        warnings = payload.get("warnings") if isinstance(payload, dict) else None
        if isinstance(warnings, list) and warnings:
            return "WARN", f"onboarding_doctor warning: {warnings[0]}"
        return "PASS", "onboarding_doctor reachable"
    return "WARN", "onboarding_doctor requires setup follow-up"


def _check_context_doctor(
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> tuple[str, str]:
    cmd = _module_cmd(
        "tools.surrealdb.context_onboarding_doctor",
        "--skip-mcp",
        "--skip-schema",
        "--format",
        "json",
    )
    rc, out, _ = _run_cmd(cmd, timeout=15.0, runner=runner)
    if rc == 0:
        try:
            payload = json.loads(out) if out else {}
        except json.JSONDecodeError:
            payload = {}
        warnings = payload.get("warnings") if isinstance(payload, dict) else None
        scope = payload.get("check_scope") if isinstance(payload, dict) else None
        skipped = payload.get("skipped_checks") if isinstance(payload, dict) else None
        if isinstance(warnings, list) and warnings:
            return "WARN", f"context_doctor warning: {warnings[0]}"
        if scope or skipped:
            skipped_text = (
                ", ".join(skipped) if isinstance(skipped, list) and skipped else "none"
            )
            return (
                "PASS",
                f"context_doctor {scope or 'partial check'} (skipped: {skipped_text})",
            )
        return "PASS", "context_doctor reachable"
    return "WARN", "context_doctor requires setup follow-up"


def _validate_output_safe(text: str) -> None:
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(text):
            raise ValueError(
                "output contains forbidden pattern — potential secret leak"
            )


def build_verdict(
    root: Path | None = None,
    *,
    mode: str = "default",
    doctor_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    context_doctor_runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> OrchestratorOutput:
    r = root or REPO_ROOT
    output = OrchestratorOutput(mode=mode)
    output.check_scope = (
        "onboarding_status_check_only"
        if mode == "check-only"
        else "onboarding_status_default"
    )

    # 1. Bootloader files
    bl_status, bl_missing = _check_bootloader_files(r)
    output.bootloader_ok = bl_status
    if bl_status == "FAIL":
        output.blockers.append(f"Fehlender Bootloader: {', '.join(bl_missing)}")

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
    output.details["env_file"] = env_detail
    if env_status == "WARN":
        output.warnings.append(env_detail)

    # 5. Doctor reachability
    doc_status, doc_detail = _check_doctor_reachable(runner=doctor_runner)
    output.doctor_reachable = doc_status
    output.details["doctor"] = doc_detail
    if doc_status == "WARN":
        output.warnings.append(doc_detail)

    # 6. Context doctor
    ctx_status, ctx_detail = _check_context_doctor(runner=context_doctor_runner)
    output.context_doctor = ctx_status
    output.details["context_doctor"] = ctx_detail
    if ctx_status == "WARN":
        output.warnings.append(ctx_detail)

    # Final status
    if output.blockers:
        output.status = "BLOCKED"
        output.state = BLOCKED_STATE
        output.blocking = True
        output.allowed_next_actions = [ACTION_ABORT]
    elif output.warnings:
        output.status = "SETUP_WARN"
        output.blocking = False
        if mode == "check-only":
            output.state = SETUP_REQUIRED
            output.allowed_next_actions = [ACTION_REQUEST_SETUP_GO, ACTION_ABORT]
            output.setup_prompt_visible = False
        else:
            output.state = SETUP_CONFIRMATION_PENDING
            output.allowed_next_actions = [ACTION_APPROVE_SETUP, ACTION_ABORT]
            output.setup_prompt_visible = True
        output.requires_explicit_setup_go = True
    else:
        output.status = "PASS"
        output.blocking = False
        output.state = DRY_RUN_COMPLETE if mode == "check-only" else STATUS_ONLY
        output.allowed_next_actions = [ACTION_STATUS_ONLY, ACTION_ABORT]

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
        f"State: {report.state}",
        f"check_scope: {report.check_scope}",
        f"requires_explicit_setup_go: {'yes' if report.requires_explicit_setup_go else 'no'}",
        f"allowed_next_actions: {', '.join(report.allowed_next_actions) if report.allowed_next_actions else 'none'}",
        f"skipped_checks: {', '.join(report.skipped_checks) if report.skipped_checks else 'none'}",
        "",
    ]

    lines.append("Checks:")
    lines.append(f"  Bootloader: [{report.bootloader_ok}]")
    lines.append(f"  Scenario document: [{report.scenario_ok}]")
    lines.append(f"  LR-Status: [{report.lr_ok}] - {report.details.get('lr', '')}")
    lines.append(f"  .env: [{report.env_file}] - {report.details.get('env_file', '')}")
    lines.append(
        f"  onboarding_doctor: [{report.doctor_reachable}] - {report.details.get('doctor', '')}"
    )
    lines.append(
        f"  context_doctor: [{report.context_doctor}] - {report.details.get('context_doctor', '')}"
    )
    lines.append("")

    if report.blockers:
        lines.append("BLOCKER:")
        for b in report.blockers:
            lines.append(f"  ! {_safe_summary(b, 120)}")
        lines.append("")

    if report.warnings:
        lines.append("Warnings:")
        for w in report.warnings:
            lines.append(f"  * {_safe_summary(w, 120)}")
        lines.append("")
        lines.append(f"Warning semantics: {report.warning_semantics}")
        lines.append("")

    if report.mode == "check-only":
        lines.append("check-only mode is dry-run only.")
        lines.append("No setup mutation is allowed from this run.")
    if report.requires_explicit_setup_go:
        lines.append("Would only run setup after explicit setup GO.")
    lines.append("No changes made.")
    lines.append("LR remains NO-GO.")
    lines.append("trade-capable is not Live-Go.")
    lines.append("")

    if report.setup_prompt_visible:
        lines.extend(SETUP_PROMPT_LINES)

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

    report = build_verdict(mode=args.mode)

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
