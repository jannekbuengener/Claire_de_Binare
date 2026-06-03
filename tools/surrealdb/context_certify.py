"""Read-only operator certification proof pack for Context/Memory/MCP/CLI.

Aggregates static registry/bridge/guard evidence and optional live doctor checks
without productive DB writes, apply modes, or context-smoke-db.

Issue: #2776
Parent: #1976

Usage:
    python -m tools.surrealdb.context_certify
    python -m tools.surrealdb.context_certify --format json
    python -m tools.surrealdb.context_certify --format markdown --output report.md
    make context-certify

Exit codes:
    0 - certified (static gates pass; no blocking failures)
    1 - blocking failure (registry/guard inconsistency)
    2 - CLI or output validation error
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from core.utils.clock import utcnow
from tools.mcp.context_bridge import create_bridge
from tools.mcp.permission_guard import (
    FORBIDDEN_SQL_KEYWORDS,
    INPUT_SCAN_EXEMPT_TOOLS,
    INPUT_SCAN_TOOLS,
)
from tools.mcp.registry import ContextToolRegistry
from tools.surrealdb import context_onboarding_doctor as doctor

GateStatus = Literal["pass", "fail", "skipped", "blocked"]
FinalVerdict = Literal["certified", "fail"]

FORBIDDEN_OUTPUT_SUBSTRINGS = doctor.FORBIDDEN_OUTPUT_SUBSTRINGS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_metadata(repo_root: Path) -> dict[str, Any]:
    def _run(*args: str) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=repo_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, ""
        if proc.returncode != 0:
            return False, (proc.stdout or proc.stderr).strip()
        return True, (proc.stdout or "").strip()

    sha_ok, sha = _run("rev-parse", "HEAD")
    branch_ok, branch = _run("rev-parse", "--abbrev-ref", "HEAD")
    clean_ok, porcelain = _run("status", "--porcelain")
    worktree_clean = clean_ok and porcelain == ""
    return {
        "git_sha": sha if sha_ok else "unknown",
        "branch": branch if branch_ok else "unknown",
        "worktree_clean": worktree_clean if clean_ok else False,
        "git_available": sha_ok and branch_ok,
    }


@dataclass
class GateEntry:
    check_id: str
    status: GateStatus
    blocking: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "blocking": self.blocking,
            "detail": self.detail,
        }


@dataclass
class CertifyReport:
    timestamp: str
    git_sha: str
    branch: str
    worktree_clean: bool
    tool_count: int
    doctor_status: dict[str, Any]
    bridge_status: dict[str, Any]
    mcp_readonly_summary: dict[str, Any]
    permission_guard_summary: dict[str, Any]
    test_results: dict[str, Any]
    gate_matrix: list[GateEntry] = field(default_factory=list)
    skipped_checks_with_reason: list[dict[str, str]] = field(default_factory=list)
    blocked_checks_with_reason: list[dict[str, str]] = field(default_factory=list)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    lr_note: str = "NO-GO"
    final_verdict: FinalVerdict = "certified"
    issue_ref: str = "#2776"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "git_sha": self.git_sha,
            "branch": self.branch,
            "worktree_clean": self.worktree_clean,
            "tool_count": self.tool_count,
            "doctor_status": self.doctor_status,
            "bridge_status": self.bridge_status,
            "mcp_readonly_summary": self.mcp_readonly_summary,
            "permission_guard_summary": self.permission_guard_summary,
            "test_results": self.test_results,
            "gate_matrix": [entry.to_dict() for entry in self.gate_matrix],
            "skipped_checks_with_reason": list(self.skipped_checks_with_reason),
            "blocked_checks_with_reason": list(self.blocked_checks_with_reason),
            "safety_flags": dict(self.safety_flags),
            "lr_note": self.lr_note,
            "final_verdict": self.final_verdict,
            "issue_ref": self.issue_ref,
        }


def _collect_static_gates() -> tuple[list[GateEntry], dict[str, Any], dict[str, Any]]:
    gates: list[GateEntry] = []
    bridge = create_bridge()
    bridge_status = bridge.get_read_only_status()
    tools = ContextToolRegistry.list_tools()
    non_read_only = [tool.name for tool in tools if not tool.read_only]

    registry_ok = not non_read_only
    gates.append(
        GateEntry(
            check_id="registry_all_read_only",
            status="pass" if registry_ok else "fail",
            blocking=True,
            detail=(
                f"{len(tools)} tools registered; all read_only=True"
                if registry_ok
                else f"non-read-only tools: {non_read_only}"
            ),
        )
    )

    try:
        ContextToolRegistry.assert_read_only_consistency()
        consistency_detail = "assert_read_only_consistency OK"
        consistency_status: GateStatus = "pass"
    except ValueError as exc:
        consistency_detail = str(exc)
        consistency_status = "fail"

    gates.append(
        GateEntry(
            check_id="permission_guard_registry_consistency",
            status=consistency_status,
            blocking=True,
            detail=consistency_detail,
        )
    )

    tool_count = len(tools)
    expected_read_only = len(bridge_status.get("read_only_tools", []))
    count_ok = tool_count == expected_read_only == bridge_status.get("tools_count")
    gates.append(
        GateEntry(
            check_id="bridge_tool_inventory",
            status="pass" if count_ok else "fail",
            blocking=True,
            detail=(
                f"bridge tools_count={bridge_status.get('tools_count')}, "
                f"read_only_tools={expected_read_only}, registry={tool_count}"
            ),
        )
    )

    mcp_summary = {
        "enforced": bridge_status.get("enforced"),
        "tools_count": tool_count,
        "read_only_tools_count": expected_read_only,
        "non_read_only_tools": non_read_only,
    }
    permission_summary = {
        "registry_gate": (
            "pass" if registry_ok and consistency_status == "pass" else "fail"
        ),
        "input_scan_tools_count": len(INPUT_SCAN_TOOLS),
        "input_scan_exempt_tools_count": len(INPUT_SCAN_EXEMPT_TOOLS),
        "forbidden_sql_keywords_count": len(FORBIDDEN_SQL_KEYWORDS),
    }
    return gates, mcp_summary, permission_summary


def _collect_root_inventory_gates(repo_root: Path) -> list[GateEntry]:
    from tools.mcp.cross_repo_root_inventory import build_inventory

    try:
        inv = build_inventory(repo_root, check_github=False)
    except (FileNotFoundError, ValueError) as exc:
        return [
            GateEntry(
                check_id="cross_repo_root_inventory",
                status="fail",
                blocking=True,
                detail=f"inventory build failed: {exc}",
            )
        ]

    missing_optional = [
        row.key for row in inv.rows if row.local_status == "MISSING" and not row.required
    ]
    if inv.roots_verdict == "fail":
        status: GateStatus = "fail"
        detail = "; ".join(inv.fail_reasons) or "required local root missing"
        blocking = True
    elif missing_optional:
        status = "pass"
        detail = (
            f"roots_verdict={inv.roots_verdict}; optional missing: "
            f"{', '.join(missing_optional)}"
        )
        blocking = False
    else:
        status = "pass"
        detail = f"roots_verdict={inv.roots_verdict}; all configured roots present"
        blocking = False

    return [
        GateEntry(
            check_id="cross_repo_root_inventory",
            status=status,
            blocking=blocking,
            detail=detail,
        )
    ]


def _default_skipped_checks() -> list[dict[str, str]]:
    return [
        {
            "check": "context-smoke-db",
            "reason": "not run by certification (hard DB-backed smoke is operator-only)",
        },
        {
            "check": "context-smoke-full-pipeline",
            "reason": "make context-smoke not invoked by context-certify",
        },
        {
            "check": "context-import-apply",
            "reason": "no --apply or productive import in certification default",
        },
        {
            "check": "live_mcp_http_port",
            "reason": "skipped unless --include-live-checks",
        },
        {
            "check": "live_surrealdb_schema",
            "reason": "skipped unless --include-live-checks (requires local stack + secrets)",
        },
    ]


def _run_doctor(
    repo_root: Path,
    *,
    include_live: bool,
) -> tuple[dict[str, Any], list[GateEntry]]:
    gates: list[GateEntry] = []
    report = doctor.build_report(
        repo_root,
        skip_mcp=not include_live,
        skip_schema=not include_live,
    )
    doctor_dict = report.to_dict()
    doctor_dict["mode"] = "live" if include_live else "inventory_only"
    doctor_dict["exit_code_if_onboarding"] = doctor.compute_exit_code(report)

    if include_live:
        code = doctor.compute_exit_code(report)
        gates.append(
            GateEntry(
                check_id="context_doctor_live",
                status="pass" if code == 0 else "fail",
                blocking=False,
                detail=report.next_action,
            )
        )
    else:
        gates.append(
            GateEntry(
                check_id="context_doctor_live",
                status="skipped",
                blocking=False,
                detail="inventory-only; pass --include-live-checks for TCP/MCP/schema",
            )
        )

    doctor_status = {
        "summary": doctor_dict,
        "reachable": report.surrealdb_status,
        "mcp_server": report.mcp_server_status,
        "next_action": report.next_action,
    }
    return doctor_status, gates


def _run_unit_tests(repo_root: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/surrealdb/test_context_certify.py",
        "-q",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ran": True,
            "passed": False,
            "command": " ".join(cmd),
            "detail": str(exc),
        }
    output = (proc.stdout or "") + (proc.stderr or "")
    return {
        "ran": True,
        "passed": proc.returncode == 0,
        "exit_code": proc.returncode,
        "command": " ".join(cmd),
        "tail": output.strip()[-500:] if output else "",
    }


def build_report(
    repo_root: Path | None = None,
    *,
    include_live_checks: bool = False,
    run_unit_tests: bool = False,
) -> CertifyReport:
    root = _repo_root() if repo_root is None else repo_root
    git_info = _git_metadata(root)
    static_gates, mcp_summary, permission_summary = _collect_static_gates()
    doctor_status, doctor_gates = _run_doctor(root, include_live=include_live_checks)
    root_gates = _collect_root_inventory_gates(root)

    gates = static_gates + doctor_gates + root_gates
    skipped = _default_skipped_checks()
    blocked: list[dict[str, str]] = []

    for gate in gates:
        if gate.status == "fail" and gate.blocking:
            blocked.append(
                {"check": gate.check_id, "reason": gate.detail},
            )

    test_suggestions = [
        "pytest tests/unit/surrealdb/test_context_onboarding_doctor.py -q",
        "pytest tests/unit/tools/mcp/test_context_bridge.py -q",
        "pytest tests/unit/tools/mcp/test_permission_guard.py -q",
        "pytest tests/unit/surrealdb/test_context_certify.py -q",
    ]
    test_results: dict[str, Any] = {
        "ran_in_certify": False,
        "test_command_suggestions": test_suggestions,
    }
    if run_unit_tests:
        test_results["certify_unit"] = _run_unit_tests(root)
        test_results["ran_in_certify"] = True
        gates.append(
            GateEntry(
                check_id="certify_unit_tests",
                status="pass" if test_results["certify_unit"]["passed"] else "fail",
                blocking=False,
                detail=test_results["certify_unit"]["command"],
            )
        )

    safety_flags = {
        "PERSIST_ALLOWED": False,
        "MUTATION_ALLOWED": False,
        "includes_db_smoke": False,
        "includes_apply": False,
        "includes_context_smoke_db": False,
        "read_only_by_default": True,
    }

    blocking_fail = any(gate.status == "fail" and gate.blocking for gate in gates)
    final_verdict: FinalVerdict = "fail" if blocking_fail else "certified"

    return CertifyReport(
        timestamp=utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        git_sha=git_info["git_sha"],
        branch=git_info["branch"],
        worktree_clean=git_info["worktree_clean"],
        tool_count=mcp_summary["tools_count"],
        doctor_status=doctor_status,
        bridge_status=create_bridge().get_read_only_status(),
        mcp_readonly_summary=mcp_summary,
        permission_guard_summary=permission_summary,
        test_results=test_results,
        gate_matrix=gates,
        skipped_checks_with_reason=skipped,
        blocked_checks_with_reason=blocked,
        safety_flags=safety_flags,
        final_verdict=final_verdict,
    )


def compute_exit_code(report: CertifyReport) -> int:
    if report.final_verdict == "fail":
        return 1
    return 0


def format_report_markdown(report: CertifyReport) -> str:
    lines = [
        "# Context Operator Certification Proof Pack",
        "",
        f"- **timestamp:** {report.timestamp}",
        f"- **git_sha:** {report.git_sha}",
        f"- **branch:** {report.branch}",
        f"- **worktree_clean:** {report.worktree_clean}",
        f"- **tool_count:** {report.tool_count}",
        f"- **final_verdict:** {report.final_verdict}",
        f"- **lr_note:** {report.lr_note}",
        "",
        "## Safety flags",
    ]
    for key, value in sorted(report.safety_flags.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Gate matrix"])
    for gate in report.gate_matrix:
        lines.append(
            f"- `{gate.check_id}`: **{gate.status}** "
            f"(blocking={gate.blocking}) — {gate.detail}"
        )
    if report.skipped_checks_with_reason:
        lines.extend(["", "## Skipped checks"])
        for item in report.skipped_checks_with_reason:
            lines.append(f"- **{item['check']}:** {item['reason']}")
    if report.blocked_checks_with_reason:
        lines.extend(["", "## Blocked checks"])
        for item in report.blocked_checks_with_reason:
            lines.append(f"- **{item['check']}:** {item['reason']}")
    lines.extend(["", "## Test commands"])
    for cmd in report.test_results.get("test_command_suggestions", []):
        lines.append(f"- `{cmd}`")
    return "\n".join(lines)


def format_report(report: CertifyReport, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if fmt == "markdown":
        return format_report_markdown(report)
    if fmt == "text":
        return format_report_markdown(report)
    raise ValueError(f"unsupported format: {fmt!r}")


def _validate_output_safe(text: str) -> None:
    for forbidden in FORBIDDEN_OUTPUT_SUBSTRINGS:
        if forbidden in text:
            raise ValueError(f"output contains forbidden substring: {forbidden}")


_HELP_EPILOG = """\
Examples:
  python -m tools.surrealdb.context_certify
  python -m tools.surrealdb.context_certify --format json
  python -m tools.surrealdb.context_certify --format markdown --output certify.md
  make context-certify

Notes:
  - Read-only by default; does not run context-smoke-db or --apply.
  - Live MCP/SurrealDB checks require --include-live-checks (non-blocking).
  - LR remains NO-GO; no Phase-2 activation.

Exit codes:
  0  certified (static gates pass)
  1  blocking registry/guard failure
  2  CLI or output validation error
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Context/Memory/MCP operator certification proof pack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_HELP_EPILOG,
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write report to file (optional)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )
    parser.add_argument(
        "--include-live-checks",
        action="store_true",
        help="Run context-doctor live MCP/SurrealDB probes (non-blocking)",
    )
    parser.add_argument(
        "--run-unit-tests",
        action="store_true",
        help="Run certify unit tests as part of the proof pack (non-blocking)",
    )
    args = parser.parse_args(argv)

    report = build_report(
        args.repo_root,
        include_live_checks=args.include_live_checks,
        run_unit_tests=args.run_unit_tests,
    )
    output = format_report(report, args.format)
    _validate_output_safe(output)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return compute_exit_code(report)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
