"""Central negative-control matrix for write-intent and mutation blockades (#2854).

Read-only catalog for regression tests and harness evidence. No live DB/MCP mutations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

NegativeControlCategory = Literal[
    "safety_defaults",
    "write_intent",
    "mutation_gate",
    "productive_persist",
    "fake_db_evidence",
    "scope_drift",
    "harness_classification",
]

InvocationPath = Literal["bridge", "mcp", "n/a"]
ExpectedVerdict = Literal["PASS", "BLOCKED_SAFETY", "FAIL", "blocked"]


@dataclass(frozen=True)
class NegativeControlCase:
    case_id: str
    category: NegativeControlCategory
    description: str
    expected_verdict: ExpectedVerdict
    invocation_path: InvocationPath = "bridge"
    parameters: dict[str, Any] | None = None
    operation_mode: str | None = None
    mutation_flag: str | None = None
    mcp_simulated_code: str | None = None
    include_authorization: bool = True


NEGATIVE_CONTROL_MATRIX: tuple[NegativeControlCase, ...] = (
    NegativeControlCase(
        case_id="defaults_persist_allowed_false",
        category="safety_defaults",
        description="PERSIST_ALLOWED module constant remains False",
        expected_verdict="PASS",
        invocation_path="n/a",
    ),
    NegativeControlCase(
        case_id="defaults_mutation_allowed_false",
        category="safety_defaults",
        description="MUTATION_ALLOWED module constant remains False",
        expected_verdict="PASS",
        invocation_path="n/a",
    ),
    NegativeControlCase(
        case_id="write_intent_dry_run_allowed",
        category="write_intent",
        description="dry_run gate evaluation returns approved_dry_run",
        expected_verdict="PASS",
        invocation_path="bridge",
        operation_mode="dry_run",
        include_authorization=True,
    ),
    NegativeControlCase(
        case_id="write_intent_agent_memory_refused",
        category="write_intent",
        description="agent_memory_write operation_mode refused on bridge",
        expected_verdict="PASS",
        invocation_path="bridge",
        operation_mode="agent_memory_write",
        include_authorization=True,
    ),
    NegativeControlCase(
        case_id="write_intent_productive_audit_refused",
        category="write_intent",
        description="audit_persist_productive refused without G3b activation",
        expected_verdict="PASS",
        invocation_path="bridge",
        operation_mode="audit_persist_productive",
        include_authorization=True,
    ),
    NegativeControlCase(
        case_id="write_intent_local_audit_refused",
        category="write_intent",
        description="audit_persist_local refused on MCP surface",
        expected_verdict="PASS",
        invocation_path="bridge",
        operation_mode="audit_persist_local",
        include_authorization=True,
    ),
    NegativeControlCase(
        case_id="mutation_flag_persist_blocked",
        category="mutation_gate",
        description="persist=true blocked with mutation_blocked_by_default",
        expected_verdict="PASS",
        invocation_path="bridge",
        mutation_flag="persist",
    ),
    NegativeControlCase(
        case_id="mutation_flag_execute_write_blocked",
        category="mutation_gate",
        description="execute_write=true blocked with mutation_blocked_by_default",
        expected_verdict="PASS",
        invocation_path="bridge",
        mutation_flag="execute_write",
    ),
    NegativeControlCase(
        case_id="productive_persist_without_env",
        category="productive_persist",
        description="approved_for_persist false without CDB_PERSIST_ALLOWED=1",
        expected_verdict="PASS",
        invocation_path="n/a",
    ),
    NegativeControlCase(
        case_id="write_intent_no_authorization",
        category="write_intent",
        description="missing authorization yields blocked_no_authorization",
        expected_verdict="PASS",
        invocation_path="bridge",
        operation_mode="dry_run",
        include_authorization=False,
    ),
    NegativeControlCase(
        case_id="unsafe_sql_injection_blocked",
        category="mutation_gate",
        description="query field with INSERT blocked as unsafe_input",
        expected_verdict="PASS",
        invocation_path="bridge",
        parameters={"query": "INSERT INTO agent_memory SET x=1"},
    ),
    NegativeControlCase(
        case_id="mcp_smart_mode_blocked_safety",
        category="harness_classification",
        description="MCP Smart Mode policy block is BLOCKED_SAFETY not FAIL",
        expected_verdict="BLOCKED_SAFETY",
        invocation_path="mcp",
        mcp_simulated_code="blocked_safety",
    ),
    NegativeControlCase(
        case_id="mcp_bridge_refused_still_pass",
        category="harness_classification",
        description="bridge refused write-intent remains PASS regression row",
        expected_verdict="PASS",
        invocation_path="bridge",
        operation_mode="agent_memory_write",
        include_authorization=True,
    ),
    NegativeControlCase(
        case_id="fake_brain_source_not_db_evidence",
        category="fake_db_evidence",
        description="caller brain_source without records is invalid_fake_db",
        expected_verdict="PASS",
        invocation_path="n/a",
    ),
    NegativeControlCase(
        case_id="scope_drift_write_without_go",
        category="scope_drift",
        description="scope drift firewall blocks write-intent without human_go_token",
        expected_verdict="blocked",
        invocation_path="n/a",
    ),
)


def matrix_case_ids() -> list[str]:
    return [c.case_id for c in NEGATIVE_CONTROL_MATRIX]


def case_by_id(case_id: str) -> NegativeControlCase:
    for case in NEGATIVE_CONTROL_MATRIX:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
