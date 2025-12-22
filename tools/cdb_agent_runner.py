#!/usr/bin/env python3
"""
Agent-only runner for deterministic checks and evidence collection.
Writes reports to logs/agent_runs/<run_id>/report.{md,json}.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MAX_EVIDENCE_LINES = 30
TOOL_VERSION = "0.1.0"
TEST_FILE = "tests/e2e/test_paper_trading_p0.py"
UNIT_TEST_CMD = ["pytest", "-m", "unit", "tests/unit/risk/test_guards.py"]
E2E_TEST_DRAW_CMD = [
    "pytest",
    "-m",
    "e2e",
    f"{TEST_FILE}::test_tc_p0_003_daily_drawdown_stop",
]
E2E_TEST_CB_CMD = [
    "pytest",
    "-m",
    "e2e",
    f"{TEST_FILE}::test_tc_p0_004_circuit_breaker_trigger",
]


@dataclass
class CommandResult:
    ok: bool
    returncode: Optional[int]
    stdout: str
    stderr: str
    error: Optional[str]


def run_cmd(
    cmd: List[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return CommandResult(
            ok=True,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            error=None,
        )
    except FileNotFoundError:
        return CommandResult(
            ok=False,
            returncode=None,
            stdout="",
            stderr="",
            error=f"command not found: {cmd[0]}",
        )
    except Exception as exc:
        return CommandResult(
            ok=False,
            returncode=None,
            stdout="",
            stderr="",
            error=str(exc),
        )


SECRET_KV_RE = re.compile(
    r"(?i)\b("
    r"password|passwd|pwd|secret|token|apikey|api_key|access_key|secret_key|"
    r"client_secret|private_key"
    r")\b\s*([:=])\s*([^\s,;]+)"
)
AUTH_RE = re.compile(r"(?i)\b(authorization|bearer)\b\s*([:=])\s*([^\s,;]+)")
URL_CREDS_RE = re.compile(r"(\w+://)([^:@/\s]+):([^@/\s]+)@")


def redact_line(line: str) -> str:
    line = URL_CREDS_RE.sub(r"\1REDACTED:REDACTED@", line)
    line = SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}REDACTED", line)
    line = AUTH_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}REDACTED", line)
    return line


def redact_text(text: str) -> str:
    return "\n".join(redact_line(line) for line in text.splitlines())


def trim_lines(text: str, max_lines: int = MAX_EVIDENCE_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    kept = lines[: max_lines - 1]
    omitted = len(lines) - (max_lines - 1)
    kept.append(f"... ({omitted} more lines truncated)")
    return "\n".join(kept)


def format_command_result(cmd: List[str], result: CommandResult) -> str:
    cmd_str = " ".join(cmd)
    lines = [f"$ {cmd_str}"]
    if not result.ok:
        lines.append(f"error: {result.error}")
        return "\n".join(lines)
    lines.append(f"exit_code: {result.returncode}")
    if result.stdout.strip():
        lines.append("stdout:")
        lines.extend(result.stdout.rstrip().splitlines())
    if result.stderr.strip():
        lines.append("stderr:")
        lines.extend(result.stderr.rstrip().splitlines())
    return "\n".join(lines)


def resolve_repo_root(cwd: Path) -> Tuple[Optional[Path], CommandResult]:
    result = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if result.ok and result.returncode == 0:
        root = result.stdout.strip()
        if root:
            return Path(root), result
    return None, result


def git_fact(cwd: Path, args: List[str]) -> Tuple[Optional[str], CommandResult]:
    result = run_cmd(["git"] + args, cwd=cwd)
    if result.ok and result.returncode == 0:
        value = result.stdout.strip()
        return value if value else None, result
    return None, result


def evaluate_git_tracking(
    ls_result: CommandResult, ignore_result: CommandResult
) -> Tuple[str, str]:
    if not ls_result.ok or not ignore_result.ok:
        reason = "git command unavailable"
        if ls_result.error:
            reason = ls_result.error
        elif ignore_result.error:
            reason = ignore_result.error
        return "UNKNOWN", reason
    if ls_result.returncode != 0:
        return "UNKNOWN", f"git ls-files exit {ls_result.returncode}"
    if ignore_result.returncode not in (0, 1):
        return "UNKNOWN", f"git check-ignore exit {ignore_result.returncode}"
    tracked = bool(ls_result.stdout.strip())
    ignored = ignore_result.returncode == 0
    if tracked:
        if ignored:
            return "FAIL", "tracked but ignored"
        return "PASS", "tracked and not ignored"
    if ignored:
        return "FAIL", "untracked and ignored"
    return "FAIL", "untracked and not ignored"


def evaluate_test_gate(result: Optional[CommandResult], reason: str) -> Tuple[str, str]:
    if result is None:
        return "UNKNOWN", reason
    if not result.ok:
        return "UNKNOWN", result.error or "command failed to execute"
    if result.returncode == 0:
        return "PASS", "pytest exit 0"
    return "FAIL", f"pytest exit {result.returncode}"


def format_env_snapshot(run_id: str, redis_host: str, postgres_host: str) -> Dict[str, str]:
    snapshot = {
        "E2E_RUN": "1",
        "E2E_RUN_ID": run_id,
        "REDIS_HOST": redis_host,
        "POSTGRES_HOST": postgres_host,
    }
    risk_namespace = os.getenv("RISK_NAMESPACE")
    if risk_namespace:
        snapshot["RISK_NAMESPACE"] = risk_namespace
    e2e_disable_cb = os.getenv("E2E_DISABLE_CIRCUIT_BREAKER")
    if e2e_disable_cb:
        snapshot["E2E_DISABLE_CIRCUIT_BREAKER"] = e2e_disable_cb
    return snapshot


def build_next_actions(gates: List[Dict[str, str]]) -> List[str]:
    actions: List[str] = []
    for gate in gates:
        status = gate.get("status", "")
        if status == "PASS":
            continue
        gate_name = gate["gate"]
        reason = str(gate.get("reason") or "")
        reason_lower = reason.lower()
        if gate_name == "git_tracking_tests_e2e_test_paper_trading_p0_py":
            if status == "UNKNOWN":
                if "not a git repo" in reason_lower or "rev-parse" in reason_lower:
                    action = (
                        "Open a PR to ensure the agent runner executes in a valid git checkout "
                        "and re-run the git tracking gate."
                    )
                elif "command not found" in reason_lower or "git not available" in reason_lower:
                    action = (
                        "Open a PR to ensure git is available in the agent environment for "
                        "tracking checks."
                    )
                else:
                    action = (
                        "Open a PR to restore git tracking inspection for "
                        "tests/e2e/test_paper_trading_p0.py."
                    )
            else:
                action = (
                    "Open a PR to add/track tests/e2e/test_paper_trading_p0.py and ensure it is "
                    "not ignored."
                )
            if action not in actions:
                actions.append(action)
        elif gate_name == "pytest_unit_tests_unit_risk_test_guards_py":
            if status == "UNKNOWN":
                action = (
                    "Open a PR to make pytest available in the agent environment for unit checks."
                    if "pytest not available" in reason_lower
                    else "Open a PR to investigate why the unit gate could not run."
                )
            else:
                action = (
                    "Open a PR to fix the failing unit test in "
                    "tests/unit/risk/test_guards.py."
                )
            if action not in actions:
                actions.append(action)
        elif gate_name == "pytest_e2e_tc_p0_003_daily_drawdown_stop":
            if status == "UNKNOWN":
                action = (
                    "Open a PR to make pytest available in the agent environment for E2E checks."
                    if "pytest not available" in reason_lower
                    else "Open a PR to investigate why the E2E drawdown gate could not run."
                )
            else:
                action = (
                    "Open a PR to fix the failing E2E test "
                    "test_tc_p0_003_daily_drawdown_stop."
                )
            if action not in actions:
                actions.append(action)
        elif gate_name == "pytest_e2e_tc_p0_004_circuit_breaker_trigger":
            if status == "UNKNOWN":
                action = (
                    "Open a PR to make pytest available in the agent environment for E2E checks."
                    if "pytest not available" in reason_lower
                    else "Open a PR to investigate why the E2E circuit breaker gate could not run."
                )
            else:
                action = (
                    "Open a PR to fix the failing E2E test "
                    "test_tc_p0_004_circuit_breaker_trigger."
                )
            if action not in actions:
                actions.append(action)
        if len(actions) >= 3:
            break
    return actions


def format_docker_result(cmd: List[str], result: Optional[CommandResult]) -> str:
    if result is None:
        return "docker not available"
    base = format_command_result(cmd, result)
    if not result.ok and result.error:
        return "\n".join([f"docker error: {result.error}", base])
    if result.returncode not in (0, None):
        error_line = ""
        if result.stderr.strip():
            error_line = result.stderr.strip().splitlines()[0]
        elif result.stdout.strip():
            error_line = result.stdout.strip().splitlines()[0]
        if error_line:
            return "\n".join([f"docker error: {error_line}", base])
    return base


def main() -> int:
    run_id = uuid.uuid4().hex
    cwd = Path.cwd()
    git_repo_root, git_root_result = resolve_repo_root(cwd)
    is_git_repo = (
        git_root_result.ok
        and git_root_result.returncode == 0
        and git_repo_root is not None
    )
    repo_root = git_repo_root if is_git_repo else cwd

    if is_git_repo:
        git_root = str(git_repo_root)
        git_branch, _ = git_fact(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
        git_sha, _ = git_fact(repo_root, ["rev-parse", "HEAD"])

        ls_result = run_cmd(["git", "ls-files", "--", TEST_FILE], cwd=repo_root)
        ignore_result = run_cmd(
            ["git", "check-ignore", "-v", "--", TEST_FILE], cwd=repo_root
        )
        status_result = run_cmd(
            ["git", "status", "--porcelain", "--", TEST_FILE], cwd=repo_root
        )

        git_tracking_status, git_tracking_reason = evaluate_git_tracking(
            ls_result, ignore_result
        )
    else:
        git_root = None
        git_branch = None
        git_sha = None
        ls_result = None
        ignore_result = None
        status_result = None
        if git_root_result.ok and git_root_result.returncode not in (0, None):
            candidates = (git_root_result.stderr or "", git_root_result.stdout or "")
            reason_line = ""
            for candidate in candidates:
                for line in candidate.splitlines():
                    if line.strip():
                        reason_line = line.strip()
                        break
                if reason_line:
                    break
            git_tracking_reason = reason_line or "git rev-parse failed"
        else:
            git_tracking_reason = git_root_result.error or "git not available"
        git_tracking_status = "UNKNOWN"

    redis_host = os.getenv("REDIS_HOST", "localhost")
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    test_env = os.environ.copy()
    test_env["E2E_RUN"] = "1"
    test_env["E2E_RUN_ID"] = run_id
    test_env["REDIS_HOST"] = redis_host
    test_env["POSTGRES_HOST"] = postgres_host

    pytest_available = shutil.which("pytest") is not None
    unit_result = None
    e2e_draw_result = None
    e2e_cb_result = None
    if pytest_available:
        unit_result = run_cmd(UNIT_TEST_CMD, cwd=repo_root, env=test_env)
        e2e_draw_result = run_cmd(E2E_TEST_DRAW_CMD, cwd=repo_root, env=test_env)
        e2e_cb_result = run_cmd(E2E_TEST_CB_CMD, cwd=repo_root, env=test_env)

    unit_status, unit_reason = evaluate_test_gate(
        unit_result, "pytest not available"
    )
    draw_status, draw_reason = evaluate_test_gate(
        e2e_draw_result, "pytest not available"
    )
    cb_status, cb_reason = evaluate_test_gate(
        e2e_cb_result, "pytest not available"
    )

    docker_available = shutil.which("docker") is not None
    docker_ps_result = None
    docker_risk_logs = None
    docker_exec_logs = None
    if docker_available:
        docker_ps_result = run_cmd(["docker", "compose", "ps"], cwd=repo_root)
        docker_risk_logs = run_cmd(
            ["docker", "logs", "--tail", "200", "cdb_risk"], cwd=repo_root
        )
        docker_exec_logs = run_cmd(
            ["docker", "logs", "--tail", "200", "cdb_execution"], cwd=repo_root
        )

    gates = [
        {
            "gate": "git_tracking_tests_e2e_test_paper_trading_p0_py",
            "status": git_tracking_status,
            "reason": git_tracking_reason,
        },
        {
            "gate": "pytest_unit_tests_unit_risk_test_guards_py",
            "status": unit_status,
            "reason": unit_reason,
        },
        {
            "gate": "pytest_e2e_tc_p0_003_daily_drawdown_stop",
            "status": draw_status,
            "reason": draw_reason,
        },
        {
            "gate": "pytest_e2e_tc_p0_004_circuit_breaker_trigger",
            "status": cb_status,
            "reason": cb_reason,
        },
    ]

    evidence_sections = {
        "git_facts": "\n".join(
            [
                f"git_root: {git_root or 'UNKNOWN'}",
                f"git_branch: {git_branch or 'UNKNOWN'}",
                f"git_sha: {git_sha or 'UNKNOWN'}",
            ]
        ),
        "git_tracking": "git tracking unavailable: " + git_tracking_reason
        if not is_git_repo
        else "\n".join(
            [
                format_command_result(["git", "ls-files", "--", TEST_FILE], ls_result),
                format_command_result(
                    ["git", "check-ignore", "-v", "--", TEST_FILE], ignore_result
                ),
                format_command_result(
                    ["git", "status", "--porcelain", "--", TEST_FILE], status_result
                ),
            ]
        ),
        "pytest_unit": "pytest not available"
        if unit_result is None
        else format_command_result(UNIT_TEST_CMD, unit_result),
        "pytest_e2e_drawdown": "pytest not available"
        if e2e_draw_result is None
        else format_command_result(E2E_TEST_DRAW_CMD, e2e_draw_result),
        "pytest_e2e_circuit_breaker": "pytest not available"
        if e2e_cb_result is None
        else format_command_result(E2E_TEST_CB_CMD, e2e_cb_result),
        "docker_compose_ps": format_docker_result(
            ["docker", "compose", "ps"], docker_ps_result
        ),
        "docker_logs_cdb_risk": format_docker_result(
            ["docker", "logs", "--tail", "200", "cdb_risk"], docker_risk_logs
        ),
        "docker_logs_cdb_execution": format_docker_result(
            ["docker", "logs", "--tail", "200", "cdb_execution"], docker_exec_logs
        ),
    }

    sanitized_evidence: Dict[str, str] = {}
    for key, text in evidence_sections.items():
        redacted = redact_text(text)
        sanitized_evidence[key] = trim_lines(redacted, MAX_EVIDENCE_LINES)

    next_actions = build_next_actions(gates)

    report = {
        "run_id": run_id,
        "tool_version": TOOL_VERSION,
        "exec_summary": gates,
        "evidence": sanitized_evidence,
        "next_actions": next_actions,
        "env_snapshot": format_env_snapshot(run_id, redis_host, postgres_host),
    }

    report_dir = repo_root / "logs" / "agent_runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_md = report_dir / "report.md"
    report_json = report_dir / "report.json"

    lines = []
    lines.append("# Agent Run Report")
    lines.append("")
    lines.append("## EXECUTIVE SUMMARY")
    for gate in gates:
        lines.append(f"- {gate['gate']}: {gate['status']} ({gate['reason']})")
    lines.append("")
    lines.append("## EVIDENCE")
    for key, text in sanitized_evidence.items():
        lines.append(f"### {key}")
        lines.append("```")
        lines.append(text if text else "(no output)")
        lines.append("```")
        lines.append("")
    if any(gate["status"] != "PASS" for gate in gates):
        lines.append("## NEXT ACTIONS")
        if next_actions:
            for action in next_actions:
                lines.append(f"- {action}")
        else:
            lines.append("- Investigate failing gate outputs and rerun checks.")
        lines.append("")
    lines.append("## ENV SNAPSHOT")
    for key, value in report["env_snapshot"].items():
        lines.append(f"- {key}={value}")
    lines.append("")

    report_md.write_text("\n".join(lines), encoding="utf-8")
    report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    any_fail = any(gate["status"] == "FAIL" for gate in gates)
    any_unknown = any(gate["status"] == "UNKNOWN" for gate in gates)
    if any_fail:
        overall = "FAIL"
        exit_code = 2
    elif any_unknown:
        overall = "UNKNOWN"
        exit_code = 3
    else:
        overall = "PASS"
        exit_code = 0

    print(f"Report written to: {report_md}")
    print(f"OVERALL={overall}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
