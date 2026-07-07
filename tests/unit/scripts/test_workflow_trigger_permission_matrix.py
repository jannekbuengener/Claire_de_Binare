"""Workflow trigger and permission matrix contract tests (#3845)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "workflow_contract"


def _matrix_for_dir(workflows_dir: Path) -> list[helpers.WorkflowTriggerPermissionRow]:
    rows: list[helpers.WorkflowTriggerPermissionRow] = []
    for filename in helpers.list_workflow_yaml_files(workflows_dir):
        rows.append(helpers.build_trigger_permission_row(workflows_dir / filename))
    return rows


def test_no_workflow_declares_pull_request_target() -> None:
    offenders: list[str] = []
    for filename in helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR):
        forbidden = helpers.workflow_declares_forbidden_trigger(
            helpers.WORKFLOWS_DIR / filename
        )
        if forbidden:
            offenders.append(f"{filename}: {forbidden}")
    assert offenders == []


def test_trigger_matrix_is_deterministic_and_complete() -> None:
    first = _matrix_for_dir(helpers.WORKFLOWS_DIR)
    second = _matrix_for_dir(helpers.WORKFLOWS_DIR)
    assert first == second
    assert len(first) == len(helpers.list_workflow_yaml_files(helpers.WORKFLOWS_DIR))


@pytest.mark.parametrize(
    "filename,expected_triggers",
    [
        ("ci.yml", ("pull_request", "push")),
        ("ci.yaml", ("workflow_dispatch",)),
        ("policy-gate.yml", ("pull_request",)),
        ("gemini-invoke.yml", ("workflow_call",)),
        ("required-checks-audit.yml", ("workflow_dispatch",)),
    ],
)
def test_known_workflow_trigger_classification(
    filename: str,
    expected_triggers: tuple[str, ...],
) -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / filename)
    assert row.triggers == expected_triggers


@pytest.mark.parametrize(
    "filename,expected_write_permissions",
    [
        ("ci.yml", ()),
        ("policy-gate.yml", ()),
        ("stale.yml", ("issues:write", "pull-requests:write")),
        ("cdb-daily-delta-triage.yml", ("issues:write",)),
        (
            "gemini-invoke.yml",
            ("id-token:write", "issues:write", "pull-requests:write"),
        ),
    ],
)
def test_known_workflow_write_permission_classification(
    filename: str,
    expected_write_permissions: tuple[str, ...],
) -> None:
    row = helpers.build_trigger_permission_row(helpers.WORKFLOWS_DIR / filename)
    assert row.write_permissions == expected_write_permissions


def test_write_permissions_use_canonical_scope_tokens() -> None:
    for row in _matrix_for_dir(helpers.WORKFLOWS_DIR):
        for scope in row.write_permissions:
            assert scope in helpers.WRITE_PERMISSION_SCOPES, (
                f"{row.filename} has unexpected write scope {scope!r}"
            )


def test_fixture_flags_pull_request_target_as_forbidden() -> None:
    fixture_dir = FIXTURES_ROOT / "forbidden_trigger"
    row = helpers.build_trigger_permission_row(fixture_dir / "bad.yml")
    assert row.forbidden_triggers == ("pull_request_target",)


def test_fixture_surfaces_missing_permissions_block_as_finding() -> None:
    fixture_dir = FIXTURES_ROOT / "missing_permissions"
    row = helpers.build_trigger_permission_row(fixture_dir / "implicit.yml")
    assert row.has_explicit_permissions is False
    assert row.has_top_level_permissions is False
    assert row.has_job_level_permissions is False


def test_policy_gate_source_blocks_pull_request_target_pattern() -> None:
    content = (helpers.WORKFLOWS_DIR / "policy-gate.yml").read_text(encoding="utf-8")
    assert "pull_request_target" in content
    assert "contains pull_request_target" in content
