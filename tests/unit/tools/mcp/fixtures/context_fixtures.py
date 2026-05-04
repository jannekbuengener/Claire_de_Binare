"""
Shared test fixtures for Context MCP tool tests.

Reusable deterministic inputs for handler tests.
#2100
"""

MINIMUM_REQUIRED_READS = [
    "AGENTS.md",
    "agents/AGENTS.md",
    "agents/OPEN_CODE_AGENTS.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
]

SAMPLE_QUERY = "risk decisions"
SAMPLE_TARGET_ID = "evt_abc123"
SAMPLE_SOURCE_REF = "src_test_001"
SAMPLE_ARTIFACTS = ["art_001", "art_002", "art_003"]
SAMPLE_TASK_SCOPE = "review documentation"
SAMPLE_TASK_ID = "task_unit_test_001"

VALID_OPERATION_MODES = [
    "read_only",
    "dry_run",
    "write (code/docs)",
    "write (config/infra)",
    "write (DB/migration)",
    "write (MCP live)",
]

VALID_EXPLANATION_TYPES = [
    "why_blocked",
    "why_risky",
    "why_stale",
    "why_decision_current",
    "why_decision_superseded",
    "why_scope_blocked",
    "why_evidence_weak",
    "why_agent_needs_go",
    "why_doc_untrusted",
]

VALID_DEPTH_VALUES = ["quick", "standard", "deep"]
VALID_PACKAGE_FORMATS = ["json", "markdown"]