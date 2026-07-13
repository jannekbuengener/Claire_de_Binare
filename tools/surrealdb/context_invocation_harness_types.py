"""Shared types for context live invocation harness and JSON evidence (#3939).

Extracted to break the CodeQL cyclic-import between
``context_live_invocation_harness`` and ``context_invocation_evidence_json``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MatrixStatus = Literal["PASS", "PASS_WITH_LIMITS", "FAIL", "BLOCKED_SAFETY"]
FinalVerdict = Literal["pass", "fail"]
InvocationProfile = Literal["minimal", "full"]

ISSUE_REF = "#2849"
RATIFICATION_DOC = (
    "docs/evidence/context_tooling/CDB_PASS_WITH_LIMITS_RATIFICATION_2026-06-03.md"
)


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
