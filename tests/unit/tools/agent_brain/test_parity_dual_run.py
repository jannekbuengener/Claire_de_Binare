"""Dual-run parity harness against legacy + pinned Agent Brain (#18)."""

from __future__ import annotations

import importlib

import pytest

from tools.agent_brain.parity import (
    ParityClass,
    assert_parity_pass,
    load_accepted_delta_catalog,
    run_dual_suite,
)
from tools.agent_brain.parity_fixtures import representative_dual_run_cases
from tools.agent_brain.pin import PINNED_REQUIREMENT

pytestmark = pytest.mark.unit


def _require_pinned_agent_brain() -> None:
    try:
        importlib.import_module("agent_brain.protocol")
    except ImportError as exc:  # pragma: no cover
        pytest.skip(f"agent-brain not installed ({PINNED_REQUIREMENT}): {exc}")


def test_accepted_delta_catalog_loads() -> None:
    catalog = load_accepted_delta_catalog()
    assert catalog
    assert all(item.get("parity_class") != "UNACCEPTED_DELTA" for item in catalog)


def test_representative_dual_run_parity_pass() -> None:
    _require_pinned_agent_brain()
    report = run_dual_suite(representative_dual_run_cases())
    assert_parity_pass(report)
    counts = report.counts()
    assert counts[ParityClass.UNACCEPTED_DELTA.value] == 0
    assert counts[ParityClass.UNCOMPARABLE.value] == 0
    # Must have both exact matches and documented accepted changes.
    assert counts[ParityClass.EXACT_PARITY.value] > 0
    assert counts[ParityClass.ACCEPTED_CONTRACT_CHANGE.value] > 0


def test_scope_isolation_different_scopes_do_not_share_package_id() -> None:
    _require_pinned_agent_brain()
    cases = {
        case.case_id: case
        for case in representative_dual_run_cases()
        if case.case_id in {"ctx_scope_a", "ctx_scope_b"}
    }
    report = run_dual_suite([cases["ctx_scope_a"], cases["ctx_scope_b"]])
    assert_parity_pass(report)
    scope_a = report.results[0].comparable_fields["agent_brain"]["target_scope"]
    scope_b = report.results[1].comparable_fields["agent_brain"]["target_scope"]
    assert scope_a != scope_b


def test_source_priority_live_outranks_memory_on_both_paths() -> None:
    _require_pinned_agent_brain()
    case = next(
        c
        for c in representative_dual_run_cases()
        if c.case_id == "ctx_live_over_memory_marker"
    )
    report = run_dual_suite([case])
    assert_parity_pass(report)
    for side in ("legacy", "agent_brain"):
        priority = report.results[0].comparable_fields[side]["source_priority"]
        assert priority[0] == "github_live"
        assert priority.index("github_live") < priority.index("memory")
