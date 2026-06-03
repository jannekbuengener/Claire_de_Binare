"""Repeatable live-invocation regression harness for all Context MCP tools.

Invokes every registered tool via ContextBridge (same handler path as MCP server)
with benchmark-safe parameters. Produces a per-tool matrix for regression detection.

Issue: #2849, #2852 (profiles + ratification), #2850 (JSON evidence), #2853 (root inventory)
Parent: #2847

Usage:
    python -m tools.surrealdb.context_live_invocation_harness
    python -m tools.surrealdb.context_live_invocation_harness --profile full
    python -m tools.surrealdb.context_live_invocation_harness --format json
    python -m tools.surrealdb.context_live_invocation_harness --format json --output docs/evidence/context_tooling/latest_invocation_evidence.json
    make context-live-invoke
    make context-live-invoke-full

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
RATIFICATION_DOC = (
    "docs/evidence/context_tooling/CDB_PASS_WITH_LIMITS_RATIFICATION_2026-06-03.md"
)
InvocationProfile = Literal["minimal", "full"]

_BENCH_SCOPE = "bench-2852"
_BENCH_EVIDENCE: list[dict[str, Any]] = [
    {
        "evidence_id": "ev1",
        "evidence_type": "doc",
        "scope": _BENCH_SCOPE,
    }
]
_BENCH_CLAIM: list[dict[str, Any]] = [
    {
        "claim_id": "c1",
        "status": "open",
        "scope": _BENCH_SCOPE,
        "evidence_refs": ["ev1"],
    }
]
_BENCH_MEMORY: list[dict[str, Any]] = [
    {"memory_id": "m1", "scope": _BENCH_SCOPE, "summary": "bench inline record"}
]
_BENCH_DECISION_EVENTS: list[dict[str, Any]] = [
    {"decision_id": "d1", "scope": _BENCH_SCOPE, "status": "recorded"}
]
_BENCH_CONTRADICTION_RECORDS: dict[str, Any] = {
    "evidence_records": _BENCH_EVIDENCE,
    "claims": _BENCH_CLAIM,
}

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

# Inline-record overrides for --profile full (#2852 operational completeness check).
BENCHMARK_FULL_RECORD_OVERRIDES: dict[str, dict[str, Any]] = {
    "cdb_context_evidence_resolve": {
        "evidence_records": _BENCH_EVIDENCE,
        "mode": "by_artifact",
        "artifact": "AGENTS.md",
        "limit": 10,
    },
    "cdb_context_claim_resolve": {
        "claim_records": _BENCH_CLAIM,
        "mode": "by_claim_id",
        "claim_id": "c1",
    },
    "cdb_context_memory_get": {
        "memory_records": _BENCH_MEMORY,
        "mode": "by_scope",
        "scope": _BENCH_SCOPE,
    },
    "cdb_context_decision_history": {
        "decision_events": _BENCH_DECISION_EVENTS,
        "mode": "by_scope",
        "scope": _BENCH_SCOPE,
        "limit": 3,
    },
    "cdb_context_decision_replay": {
        "decision_events": _BENCH_DECISION_EVENTS,
        "mode": "replay_by_decision_id",
        "decision_id": "d1",
    },
    "cdb_context_contradictions": {
        "bundle": _BENCH_BUNDLE,
        "records": _BENCH_CONTRADICTION_RECORDS,
    },
}


def invocations_for_profile(profile: InvocationProfile) -> dict[str, dict[str, Any]]:
    """Return per-tool invocation payloads for minimal or full inline-record profile."""
    merged = {name: dict(params) for name, params in BENCHMARK_SAFE_INVOCATIONS.items()}
    if profile == "full":
        for tool_name, overrides in BENCHMARK_FULL_RECORD_OVERRIDES.items():
            call = dict(merged.get(tool_name, {}))
            call.update(overrides)
            merged[tool_name] = call
    return merged


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


def _expected_summary(tool_name: str, *, profile: InvocationProfile) -> str:
    if tool_name == "context.readiness":
        return "status=ok, readiness.status=ready_for_read_only"
    if tool_name == "cdb_context_memory_write_intent":
        return "status=refused (negative control; no persist)"
    if profile == "full" and tool_name in BENCHMARK_FULL_RECORD_OVERRIDES:
        return "status=ok with inline adapter records"
    if tool_name in BENCHMARK_FULL_RECORD_OVERRIDES:
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
        from tools.surrealdb.negative_controls import (
            classify_memory_write_intent_negative_control,
        )

        verdict = classify_memory_write_intent_negative_control(
            result, invocation_path="bridge"
        )
        if verdict == "PASS":
            return "PASS"
        if verdict == "BLOCKED_SAFETY":
            return "BLOCKED_SAFETY"
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
    profile: InvocationProfile = "minimal"
    ratification_doc: str = RATIFICATION_DOC
    manifest_tool_names: list[str] = field(default_factory=list)
    registry_tool_names: list[str] = field(default_factory=list)
    missing_from_manifest: list[str] = field(default_factory=list)
    extra_in_manifest: list[str] = field(default_factory=list)
    root_inventory: dict[str, Any] = field(default_factory=dict)

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
            "profile": self.profile,
            "ratification_doc": self.ratification_doc,
            "manifest_tool_names": self.manifest_tool_names,
            "registry_tool_names": self.registry_tool_names,
            "missing_from_manifest": self.missing_from_manifest,
            "extra_in_manifest": self.extra_in_manifest,
            "root_inventory": self.root_inventory,
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


def _attach_root_inventory(
    repo_root: Path,
    *,
    check_github: bool = True,
) -> dict[str, Any]:
    from tools.mcp.cross_repo_root_inventory import build_inventory

    report = build_inventory(repo_root, check_github=check_github)
    return report.to_dict()


def run_matrix(
    *,
    live: bool = True,
    profile: InvocationProfile = "minimal",
    fail_on_limits: bool = False,
    check_github_roots: bool = True,
) -> HarnessReport:
    """Build the invocation matrix. When live=False, only validate manifest/registry."""
    repo_root = _repo_root()
    root_inventory = _attach_root_inventory(repo_root, check_github=check_github_roots)
    git = _git_metadata(repo_root)
    bridge = create_bridge() if live else None
    invocations = invocations_for_profile(profile)
    registry_names = (
        _registry_tool_names(bridge) if bridge else sorted(invocations.keys())
    )
    manifest_names = sorted(invocations.keys())
    missing = sorted(set(registry_names) - set(manifest_names))
    extra = sorted(set(manifest_names) - set(registry_names))

    rows: list[MatrixRow] = []
    if live and bridge is not None:
        for tool_name in registry_names:
            params = invocations.get(tool_name)
            if params is None:
                rows.append(
                    MatrixRow(
                        tool_name=tool_name,
                        call={},
                        expected="callable via bridge",
                        actual="no manifest entry",
                        status="FAIL",
                        limitation=f"missing invocation entry for profile={profile}",
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
                    expected=_expected_summary(tool_name, profile=profile),
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
    if fail_on_limits and summary.get("PASS_WITH_LIMITS", 0) > 0:
        fail_reasons.append(
            f"{summary['PASS_WITH_LIMITS']} PASS_WITH_LIMITS row(s) not allowed"
        )
    if root_inventory.get("roots_verdict") == "fail":
        fail_reasons.append("cross-repo root inventory: required local root missing")
        for reason in root_inventory.get("fail_reasons") or []:
            if isinstance(reason, str):
                fail_reasons.append(f"root_inventory: {reason}")

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
        profile=profile,
        manifest_tool_names=manifest_names,
        registry_tool_names=registry_names,
        missing_from_manifest=missing,
        extra_in_manifest=extra,
        root_inventory=root_inventory,
    )


def compute_exit_code(report: HarnessReport, *, fail_on_limits: bool = False) -> int:
    if report.final_verdict == "fail":
        return 1
    if fail_on_limits and report.summary.get("PASS_WITH_LIMITS", 0) > 0:
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
        f"- **profile:** {report.profile}",
        f"- **ratification_doc:** {report.ratification_doc}",
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
    if report.root_inventory:
        inv = report.root_inventory
        lines.extend(
            [
                "",
                "## Cross-repo root inventory (#2853)",
                f"- **roots_verdict:** {inv.get('roots_verdict')}",
            ]
        )
        for row in inv.get("rows") or []:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- `{row.get('key')}`: local={row.get('local_status')} "
                f"github={row.get('github_target_status')} "
                f"path={row.get('local_path') or '—'}"
            )
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
        from tools.surrealdb.context_invocation_evidence_json import (
            serialize_invocation_evidence,
        )

        return serialize_invocation_evidence(report)
    if fmt in ("text", "markdown"):
        return format_report_markdown(report)
    raise ValueError(f"unsupported format: {fmt!r}")


_HELP_EPILOG = """\
Examples:
  python -m tools.surrealdb.context_live_invocation_harness
  python -m tools.surrealdb.context_live_invocation_harness --format json
  python -m tools.surrealdb.context_live_invocation_harness --format json --output docs/evidence/context_tooling/latest_invocation_evidence.json
  make context-live-invoke
  make context-live-invoke-full

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
        help=(
            "Output format (default: text). json emits #2850 machine-readable "
            "invocation evidence (compatible with db-record-evidence claims)."
        ),
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
    parser.add_argument(
        "--profile",
        choices=("minimal", "full"),
        default="minimal",
        help=(
            "minimal: fail-closed record paths (6 PASS_WITH_LIMITS expected). "
            "full: inline records for Wave-14 tools (27 PASS expected)."
        ),
    )
    parser.add_argument(
        "--fail-on-limits",
        action="store_true",
        help="Exit 1 when any PASS_WITH_LIMITS row is present",
    )
    args = parser.parse_args(argv)

    profile: InvocationProfile = args.profile
    fail_on_limits = args.fail_on_limits or profile == "full"
    report = run_matrix(
        live=not args.manifest_only,
        profile=profile,
        fail_on_limits=fail_on_limits,
    )
    output = format_report(report, args.format)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return compute_exit_code(report, fail_on_limits=fail_on_limits)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
