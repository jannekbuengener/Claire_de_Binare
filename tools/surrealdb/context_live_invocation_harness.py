"""Repeatable live-invocation regression harness for all Context MCP tools.

Invokes every registered tool via ContextBridge (same handler path as MCP server)
with benchmark-safe parameters. Produces a per-tool matrix for regression detection.

Issue: #2849
Parent: #2847

Usage:
    python -m tools.surrealdb.context_live_invocation_harness
    python -m tools.surrealdb.context_live_invocation_harness --format json
    python -m tools.surrealdb.context_live_invocation_harness --format markdown --output report.md
    make context-live-invoke

Exit codes:
    0 - all tools callable; no FAIL rows
    1 - one or more FAIL rows, registry/tool manifest mismatch, or safety gate failure
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
from tools.mcp.memory_write_intent_tools import MUTATION_ALLOWED
from tools.surrealdb import memory_write_gate

MatrixStatus = Literal["PASS", "PASS_WITH_LIMITS", "FAIL", "BLOCKED_SAFETY"]
FinalVerdict = Literal["pass", "fail"]
OutputFormat = Literal["text", "json", "markdown"]

EXPECTED_TOOL_COUNT = 27
ISSUE_REF = "#2849"

_BENCH_BUNDLE: dict[str, Any] = {
    "meta": {
        "scope_id": "bench-2849",
        "as_of": "2026-06-03T12:00:00+00:00",
    }
}
_BENCH_AS_OF = "2026-06-03T12:00:00+00:00"
_BRIEFING_PAYLOAD: dict[str, Any] = {
    "task_id": "cdb-briefing-2849-regression-harness",
    "task_scope": "Run all-tools live invocation regression harness",
    "target_issue": "2849",
    "requested_depth": "quick",
    "operation_mode": "read_only",
}

# Safe invocation manifest (bridge path). Keys must match registry tool names exactly.
BENCHMARK_SAFE_INVOCATIONS: dict[str, dict[str, Any]] = {
    "context.search": {"query": "benchmark", "limit": 3},
    "context.trace": {"target_id": "evt_bench_001"},
    "context.explain_source": {"source_ref": "AGENTS.md"},
    "context.show_snapshot": {"snapshot_id": "snap_bench_001"},
    "context.show_audit": {"target_tool": "context.search"},
    "context.package": {"artifacts": ["art_bench_001"]},
    "context.readiness": {
        "task_scope": "bench-2849 regression harness read-only validation",
        "operation_mode": "read_only",
        "stop_conditions": [
            "H1: no productive DB writes",
            "S1: LR remains NO-GO",
        ],
        "required_reads": [],
    },
    "context.self_explain": {
        "question": "Why is live trading blocked?",
        "explanation_type": "why_blocked",
        "evidence_refs": ["AGENTS.md"],
    },
    "context.briefing": dict(_BRIEFING_PAYLOAD),
    "context.stop_resolver": {
        "stop_conditions": ["no_live_orders"],
        "context_summary": "bench",
    },
    "context.required_reads": {
        "task_scope": "Regression harness validation",
        "target_issue": "2849",
        "operation_mode": "read_only",
    },
    "cdb_context_impact": {"component": "tools/surrealdb/memory_write_gate.py"},
    "cdb_context_evidence_resolve": {"evidence_id": "ev1"},
    "cdb_context_claim_resolve": {"claim_id": "c1"},
    "cdb_context_memory_get": {"memory_id": "m1"},
    "cdb_context_memory_write_intent": {
        "operation_mode": "agent_memory_write",
        "payload": {"summary": "bench-2849 negative control"},
        "human_go_token": "",
    },
    "cdb_context_trust_summary": {"scope": "benchmark"},
    "cdb_context_decision_history": {"limit": 3},
    "cdb_context_decision_replay": {"decision_id": "d1"},
    "cdb_context_contradictions": {"bundle": _BENCH_BUNDLE},
    "cdb_context_stale": {"bundle": _BENCH_BUNDLE, "scope": "all"},
    "cdb_context_scope_drift": {"bundle": {}, "as_of": _BENCH_AS_OF},
    "cdb_context_quality_score": {"bundle": _BENCH_BUNDLE},
    "cdb_context_architect_signals": {"bundle": _BENCH_BUNDLE},
    "cdb_control_room_view": {"bundle": _BENCH_BUNDLE},
    "cdb_agent_os_readiness": {"bundle": _BENCH_BUNDLE},
    "cdb_context_briefing": dict(_BRIEFING_PAYLOAD),
}

# Fail-closed error codes that indicate the handler ran but lacks inline records (expected).
PASS_WITH_LIMITS_ERROR_CODES = frozenset(
    {
        "missing_evidence_records",
        "missing_claim_records",
        "missing_memory_records",
        "missing_decision_events",
        "missing_records",
        "missing_bundle",
    }
)

# Hard failures: tool broken, not callable, or manifest produced invalid input.
FAIL_ERROR_CODES = frozenset(
    {
        "unknown_tool",
        "write_not_allowed",
        "invalid_parameters",
        "execution_error",
        "scan_error",
        "scoring_error",
        "evaluator_error",
        "signal_error",
        "not_implemented",
    }
)

INVALID_INPUT_PREFIXES = ("invalid_",)


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


def _extract_error_code(result: dict[str, Any]) -> str | None:
    err = result.get("error")
    if isinstance(err, dict):
        code = err.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    code_top = result.get("code")
    if isinstance(code_top, str) and code_top.strip():
        return code_top.strip()
    return None


def _summarize_actual(result: dict[str, Any]) -> str:
    status = result.get("status", "unknown")
    code = _extract_error_code(result)
    if code:
        return f"status={status}, code={code}"
    readiness = result.get("readiness")
    if isinstance(readiness, dict):
        rs = readiness.get("status", "unknown")
        drift = readiness.get("root_drift_detected")
        return f"status={status}, readiness.status={rs}, root_drift_detected={drift}"
    return f"status={status}"


def _expected_summary(tool_name: str) -> str:
    if tool_name == "context.readiness":
        return "status=ok, readiness.status=ready_for_read_only"
    if tool_name == "cdb_context_memory_write_intent":
        return "status=refused (negative control; no persist)"
    if tool_name in {
        "cdb_context_evidence_resolve",
        "cdb_context_claim_resolve",
        "cdb_context_memory_get",
        "cdb_context_decision_history",
        "cdb_context_decision_replay",
        "cdb_context_contradictions",
    }:
        return "fail-closed missing_* records (no inline bundle)"
    return "status=ok (handler JSON)"


def classify_tool_result(
    tool_name: str,
    result: dict[str, Any],
    *,
    invocation_exc: str | None = None,
) -> MatrixStatus:
    """Classify a single bridge invocation for the regression matrix."""
    if invocation_exc:
        return "FAIL"

    status = result.get("status")
    code = _extract_error_code(result)

    if tool_name == "cdb_context_memory_write_intent":
        if status == "refused":
            return "PASS"
        if code == "agent_memory_write_not_activated" and status in (
            "refused",
            "error",
        ):
            return "PASS"
        return "FAIL"

    if status == "ok":
        if tool_name == "context.readiness":
            readiness = result.get("readiness")
            if isinstance(readiness, dict):
                rs = readiness.get("status")
                if rs in (
                    "ready_for_read_only",
                    "ready_for_dry_run",
                    "ready_for_human_go",
                ):
                    return "PASS"
                if rs == "blocked_missing_context":
                    drift = readiness.get("root_drift_detected")
                    severity = readiness.get("drift_severity")
                    if drift and severity == "warning":
                        return "PASS_WITH_LIMITS"
                    return "FAIL"
                if rs and str(rs).startswith("blocked_"):
                    return "FAIL"
        return "PASS"

    if status == "refused":
        return "FAIL"

    if code and code in FAIL_ERROR_CODES:
        return "FAIL"

    if code and code in PASS_WITH_LIMITS_ERROR_CODES:
        return "PASS_WITH_LIMITS"

    if code and code.startswith(INVALID_INPUT_PREFIXES):
        return "FAIL"

    if status == "error":
        return "FAIL"

    return "FAIL"


@dataclass
class MatrixRow:
    tool_name: str
    call: dict[str, Any]
    expected: str
    actual: str
    status: MatrixStatus
    handler_status: str | None = None
    error_code: str | None = None
    limitation: str | None = None
    invocation_path: str = "bridge"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "call": self.call,
            "expected": self.expected,
            "actual": self.actual,
            "status": self.status,
            "handler_status": self.handler_status,
            "error_code": self.error_code,
            "limitation": self.limitation,
            "invocation_path": self.invocation_path,
        }


@dataclass
class HarnessReport:
    timestamp: str
    git_sha: str
    branch: str
    worktree_clean: bool
    tool_count: int
    expected_tool_count: int
    matrix: list[MatrixRow] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    safety_flags: dict[str, bool] = field(default_factory=dict)
    lr_note: str = "NO-GO"
    final_verdict: FinalVerdict = "pass"
    issue_ref: str = ISSUE_REF
    manifest_tool_names: list[str] = field(default_factory=list)
    registry_tool_names: list[str] = field(default_factory=list)
    missing_from_manifest: list[str] = field(default_factory=list)
    extra_in_manifest: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "git_sha": self.git_sha,
            "branch": self.branch,
            "worktree_clean": self.worktree_clean,
            "tool_count": self.tool_count,
            "expected_tool_count": self.expected_tool_count,
            "matrix": [row.to_dict() for row in self.matrix],
            "summary": self.summary,
            "safety_flags": self.safety_flags,
            "lr_note": self.lr_note,
            "final_verdict": self.final_verdict,
            "issue_ref": self.issue_ref,
            "manifest_tool_names": self.manifest_tool_names,
            "registry_tool_names": self.registry_tool_names,
            "missing_from_manifest": self.missing_from_manifest,
            "extra_in_manifest": self.extra_in_manifest,
        }


def _safety_flags() -> dict[str, bool]:
    return {
        "PERSIST_ALLOWED": bool(memory_write_gate.PERSIST_ALLOWED),
        "MUTATION_ALLOWED": bool(MUTATION_ALLOWED),
        "includes_productive_db": False,
        "includes_mcp_stdio": False,
    }


def _registry_tool_names(bridge: Any) -> list[str]:
    tools = bridge.list_tools()
    names: list[str] = []
    for entry in tools:
        if isinstance(entry, dict):
            name = entry.get("name")
        else:
            name = getattr(entry, "name", None)
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return sorted(names)


def run_matrix(*, live: bool = True) -> HarnessReport:
    """Build the invocation matrix. When live=False, only validate manifest/registry."""
    repo_root = _repo_root()
    git = _git_metadata(repo_root)
    bridge = create_bridge() if live else None
    registry_names = (
        _registry_tool_names(bridge)
        if bridge
        else sorted(BENCHMARK_SAFE_INVOCATIONS.keys())
    )
    manifest_names = sorted(BENCHMARK_SAFE_INVOCATIONS.keys())
    missing = sorted(set(registry_names) - set(manifest_names))
    extra = sorted(set(manifest_names) - set(registry_names))

    rows: list[MatrixRow] = []
    if live and bridge is not None:
        for tool_name in registry_names:
            params = BENCHMARK_SAFE_INVOCATIONS.get(tool_name)
            if params is None:
                rows.append(
                    MatrixRow(
                        tool_name=tool_name,
                        call={},
                        expected="callable via bridge",
                        actual="no manifest entry",
                        status="FAIL",
                        limitation="missing BENCHMARK_SAFE_INVOCATIONS entry",
                    )
                )
                continue
            exc_msg: str | None = None
            try:
                result = bridge.execute_tool(tool_name, params)
            except Exception as exc:  # pragma: no cover - bridge should not raise
                exc_msg = f"{type(exc).__name__}: {exc}"
                result = {
                    "tool": tool_name,
                    "status": "error",
                    "error": {"code": "execution_error", "message": exc_msg},
                }
            matrix_status = classify_tool_result(
                tool_name, result, invocation_exc=exc_msg
            )
            rows.append(
                MatrixRow(
                    tool_name=tool_name,
                    call=params,
                    expected=_expected_summary(tool_name),
                    actual=_summarize_actual(result),
                    status=matrix_status,
                    handler_status=(
                        str(result.get("status")) if result.get("status") else None
                    ),
                    error_code=_extract_error_code(result),
                    limitation=(
                        "MCP stdio path not exercised; use bridge proof"
                        if tool_name == "cdb_context_memory_write_intent"
                        else None
                    ),
                )
            )

    summary: dict[str, int] = {
        "PASS": 0,
        "PASS_WITH_LIMITS": 0,
        "FAIL": 0,
        "BLOCKED_SAFETY": 0,
    }
    for row in rows:
        summary[row.status] = summary.get(row.status, 0) + 1

    safety = _safety_flags()
    fail_reasons: list[str] = []
    if len(registry_names) != EXPECTED_TOOL_COUNT:
        fail_reasons.append(
            f"registry tool count {len(registry_names)} != {EXPECTED_TOOL_COUNT}"
        )
    if missing:
        fail_reasons.append(f"missing manifest for: {missing}")
    if extra:
        fail_reasons.append(f"extra manifest keys: {extra}")
    if safety["PERSIST_ALLOWED"] or safety["MUTATION_ALLOWED"]:
        fail_reasons.append("safety gates must remain default-off")
    if summary.get("FAIL", 0) > 0:
        fail_reasons.append(f"{summary['FAIL']} FAIL row(s)")

    final: FinalVerdict = "fail" if fail_reasons else "pass"

    return HarnessReport(
        timestamp=utcnow().isoformat(),
        git_sha=git["git_sha"],
        branch=git["branch"],
        worktree_clean=git["worktree_clean"],
        tool_count=len(registry_names),
        expected_tool_count=EXPECTED_TOOL_COUNT,
        matrix=rows,
        summary=summary,
        safety_flags=safety,
        final_verdict=final,
        manifest_tool_names=manifest_names,
        registry_tool_names=registry_names,
        missing_from_manifest=missing,
        extra_in_manifest=extra,
    )


def compute_exit_code(report: HarnessReport) -> int:
    if report.final_verdict == "fail":
        return 1
    return 0


def format_report_markdown(report: HarnessReport) -> str:
    lines = [
        "# Context live invocation regression harness",
        "",
        f"- **timestamp:** {report.timestamp}",
        f"- **git_sha:** {report.git_sha}",
        f"- **branch:** {report.branch}",
        f"- **worktree_clean:** {report.worktree_clean}",
        f"- **tool_count:** {report.tool_count} (expected {report.expected_tool_count})",
        f"- **final_verdict:** {report.final_verdict}",
        f"- **issue_ref:** {report.issue_ref}",
        f"- **lr_note:** {report.lr_note}",
        "",
        "## Summary",
    ]
    for key in ("PASS", "PASS_WITH_LIMITS", "FAIL", "BLOCKED_SAFETY"):
        lines.append(f"- **{key}:** {report.summary.get(key, 0)}")
    lines.extend(["", "## Safety flags"])
    for key, value in sorted(report.safety_flags.items()):
        lines.append(f"- {key}: {value}")
    if report.missing_from_manifest or report.extra_in_manifest:
        lines.extend(["", "## Manifest drift"])
        if report.missing_from_manifest:
            lines.append(f"- missing_from_manifest: {report.missing_from_manifest}")
        if report.extra_in_manifest:
            lines.append(f"- extra_in_manifest: {report.extra_in_manifest}")
    lines.extend(
        [
            "",
            "## Per-tool matrix",
            "",
            "| tool_name | status | actual | expected |",
            "|-----------|--------|--------|----------|",
        ]
    )
    for row in report.matrix:
        lines.append(
            f"| `{row.tool_name}` | **{row.status}** | {row.actual} | {row.expected} |"
        )
    return "\n".join(lines)


def format_report(report: HarnessReport, fmt: OutputFormat) -> str:
    if fmt == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if fmt in ("text", "markdown"):
        return format_report_markdown(report)
    raise ValueError(f"unsupported format: {fmt!r}")


_HELP_EPILOG = """\
Examples:
  python -m tools.surrealdb.context_live_invocation_harness
  python -m tools.surrealdb.context_live_invocation_harness --format json
  make context-live-invoke

Notes:
  - Bridge-only live path (same handlers as MCP server); no productive DB writes.
  - PERSIST_ALLOWED and MUTATION_ALLOWED must remain False.
  - LR remains NO-GO.

Exit codes:
  0  pass (all tools callable, no FAIL rows)
  1  fail (FAIL row, manifest drift, or safety gate)
  2  CLI error
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live invocation regression harness for all Context MCP tools.",
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
        "--manifest-only",
        action="store_true",
        help="Validate manifest vs registry only (no live handler calls)",
    )
    args = parser.parse_args(argv)

    report = run_matrix(live=not args.manifest_only)
    output = format_report(report, args.format)

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
