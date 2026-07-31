"""Contract tests for fail-closed Fast-CI slice selection (#4204).

Rules protected:
- Path/lane/profile map deterministically to documented test groups.
- Unknown paths, empty/broken policy, runtime/risk paths => full_fast fallback.
- Slice reports always carry merge_evidence=false.
- Full Fast-CI unit selector remains semantically unchanged.
- Changed-path order does not affect selection.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ci.lib.evidence import (
    EvidenceError,
    StageResult,
    assert_publishable,
    build_manifest,
)
from ci.lib.slice_selection import (
    FULL_FAST_GROUP,
    FULL_FAST_PYTEST_ARGS,
    SCHEMA_VERSION,
    build_unit_pytest_command,
    normalize_changed_paths,
    select_slice_test_groups,
)
from ci.stages.unit import (
    FULL_FAST_SELECTOR,
    build_unit_command,
    parse_pytest_durations,
)
from ci.stages._common import StageContext

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "ci" / "config" / "slice_validation_policy.v1.yaml"


def _load_policy() -> dict:
    with POLICY_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_docs_path_selects_documented_slice_groups_only():
    """Rule: known docs path selects only documented docs_guards groups."""
    result = select_slice_test_groups(
        changed_paths=["docs/runbooks/merge_policy_ci_gate.md"],
        routing_lane="docs",
        validation_profile="docs-v1",
        policy_path=POLICY_PATH,
    )
    assert result.merge_evidence is False
    assert result.fallback_reason is None
    assert result.used_full_fast is False
    assert result.selected_test_groups == ["docs_guards"]
    assert result.pytest_paths
    assert all(
        p.startswith("tests/unit/tools/") or p.startswith("tests/unit/tools/ci/")
        for p in result.pytest_paths
    )
    assert "tests/unit/ci/" not in result.pytest_paths


def test_ci_path_selects_ci_contract_groups():
    """Rule: known CI path selects ci_contracts (+ tooling) groups."""
    result = select_slice_test_groups(
        changed_paths=["ci/lib/slice_selection.py"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    assert result.merge_evidence is False
    assert result.fallback_reason is None
    assert "ci_contracts" in result.selected_test_groups
    assert "ci_tooling" in result.selected_test_groups
    assert any(p.startswith("tests/unit/ci/") for p in result.pytest_paths)


def test_runtime_risk_path_falls_back_to_full_profile():
    """Rule: runtime/risk path forces full Fast-CI selector."""
    result = select_slice_test_groups(
        changed_paths=["services/risk/service.py"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    assert result.used_full_fast is True
    assert result.selected_test_groups == [FULL_FAST_GROUP]
    assert result.fallback_reason == "runtime_or_risk_path"
    assert result.merge_evidence is False
    assert result.pytest_args == list(FULL_FAST_PYTEST_ARGS)


def test_unknown_path_forces_full_fallback():
    """Rule: unclassified path never silently greens a narrow slice."""
    result = select_slice_test_groups(
        changed_paths=["totally/unknown/widget.py"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    assert result.used_full_fast is True
    assert result.fallback_reason == "unclassified_paths"
    assert result.unclassified_paths == ["totally/unknown/widget.py"]
    assert result.merge_evidence is False


def test_empty_or_broken_policy_forces_full_fallback(tmp_path: Path):
    """Rule: empty/broken policy fails closed to full Fast-CI."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    empty_result = select_slice_test_groups(
        changed_paths=["docs/readme.md"],
        routing_lane="",
        validation_profile="",
        policy_path=empty,
    )
    assert empty_result.used_full_fast is True
    assert empty_result.fallback_reason in {
        "empty_policy",
        "policy_parse_error",
        "schema_error",
    }
    assert empty_result.merge_evidence is False

    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "schema_version: not-a-real-schema\npolicy_id: x\n", encoding="utf-8"
    )
    broken_result = select_slice_test_groups(
        changed_paths=["ci/lib/config.py"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=broken,
    )
    assert broken_result.used_full_fast is True
    assert broken_result.fallback_reason in {"schema_error", "policy_parse_error"}
    assert broken_result.merge_evidence is False


def test_unclassified_path_does_not_produce_silent_green_narrow_slice():
    """Rule: unclassified path cannot yield a narrow green selection."""
    result = select_slice_test_groups(
        changed_paths=["docs/x.md", "mystery/file.py"],
        routing_lane="docs",
        validation_profile="docs-v1",
        policy_path=POLICY_PATH,
    )
    assert result.used_full_fast is True
    assert "mystery/file.py" in result.unclassified_paths
    assert result.selected_test_groups == [FULL_FAST_GROUP]


def test_slice_report_merge_evidence_false():
    """Rule: slice selection report always sets merge_evidence=false."""
    result = select_slice_test_groups(
        changed_paths=["ci/config/stages.yaml"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    payload = result.to_dict()
    assert payload["merge_evidence"] is False
    assert "selected_test_groups" in payload
    assert "selection_reasons" in payload
    assert "unclassified_paths" in payload
    assert "fallback_reason" in payload


def test_full_fast_unit_selector_unchanged():
    """Rule: default unit stage keeps the Fast-CI SSOT selector."""
    ctx = StageContext(
        repo_root=REPO_ROOT,
        run_dir=REPO_ROOT / "ci" / "artifacts" / "_unused",
        run_id="run_test_selector",
        git=None,
        profile="fast",
        resources={},
        merge_evidence=True,
        unit_durations=0,
    )
    command = build_unit_command(ctx)
    assert "-k" in command
    assert command[command.index("-k") + 1] == FULL_FAST_SELECTOR
    assert FULL_FAST_SELECTOR == "not test_mcp_time_server_runtime"
    assert FULL_FAST_PYTEST_ARGS[-1] == FULL_FAST_SELECTOR


def test_changed_path_order_does_not_change_selection():
    """Rule: selection is deterministic regardless of path input order."""
    a = select_slice_test_groups(
        changed_paths=["ci/lib/config.py", "docs/index.md"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    b = select_slice_test_groups(
        changed_paths=["docs/index.md", "ci/lib/config.py"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    assert a.selected_test_groups == b.selected_test_groups
    assert a.selection_reasons == b.selection_reasons
    assert a.pytest_paths == b.pytest_paths
    assert normalize_changed_paths(["b", "a"]) == ("a", "b")


def test_slice_manifest_rejected_by_publisher_gate():
    """Rule: slice evidence cannot be published as cdb-local-ci merge proof."""
    stages = [
        StageResult(
            name="lint",
            status="PASS",
            exit_code=0,
            started_at_utc="2026-07-31T00:00:00Z",
            ended_at_utc="2026-07-31T00:00:01Z",
            duration_seconds=1.0,
            command_summary=["ruff"],
            log_path="logs/lint.log",
        ),
        StageResult(
            name="unit",
            status="PASS",
            exit_code=0,
            started_at_utc="2026-07-31T00:00:01Z",
            ended_at_utc="2026-07-31T00:00:02Z",
            duration_seconds=1.0,
            command_summary=["pytest"],
            log_path="logs/unit.log",
        ),
        StageResult(
            name="docs",
            status="PASS",
            exit_code=0,
            started_at_utc="2026-07-31T00:00:02Z",
            ended_at_utc="2026-07-31T00:00:03Z",
            duration_seconds=1.0,
            command_summary=["docs"],
            log_path="logs/docs.log",
        ),
        StageResult(
            name="governance",
            status="PASS",
            exit_code=0,
            started_at_utc="2026-07-31T00:00:03Z",
            ended_at_utc="2026-07-31T00:00:04Z",
            duration_seconds=1.0,
            command_summary=["gov"],
            log_path="logs/governance.log",
        ),
        StageResult(
            name="report",
            status="PASS",
            exit_code=0,
            started_at_utc="2026-07-31T00:00:04Z",
            ended_at_utc="2026-07-31T00:00:05Z",
            duration_seconds=1.0,
            command_summary=["report"],
            log_path="logs/report.log",
        ),
    ]
    manifest = build_manifest(
        run_id="run_slice4204",
        commit_sha="abc",
        branch="batch/ci-tooling-issue-4204",
        dirty_worktree=False,
        started_at_utc="2026-07-31T00:00:00Z",
        ended_at_utc="2026-07-31T00:01:00Z",
        host_platform="test",
        tool_versions={},
        docker_version="n/a",
        compose_version="n/a",
        profile="slice",
        stages=stages,
        skipped_checks=[],
        artifact_hashes={},
        repo_name="[REDACTED]",
        merge_evidence=False,
    )
    assert manifest["merge_evidence"] is False
    with pytest.raises(EvidenceError, match="merge_evidence=false|Slice profile"):
        assert_publishable(manifest)


def test_policy_schema_version_is_versioned():
    """Rule: slice policy is versioned and machine-readable."""
    policy = _load_policy()
    assert policy["schema_version"] == SCHEMA_VERSION
    assert policy["policy_id"] == "cdb-slice-validation-v1"
    assert "test_groups" in policy
    assert "path_rules" in policy


def test_build_unit_pytest_command_includes_durations():
    """Rule: timing evidence flag is appended without changing selector semantics."""
    result = select_slice_test_groups(
        changed_paths=["ci/lib/slice_selection.py"],
        routing_lane="ci-tooling",
        validation_profile="ci-tooling-v1",
        policy_path=POLICY_PATH,
    )
    cmd = build_unit_pytest_command(result, python_executable="python", durations=50)
    assert "--durations=50" in cmd
    assert any(p.startswith("tests/unit/ci/") for p in cmd)


def test_parse_pytest_durations_extracts_slowest():
    """Rule: duration lines are parsed into machine-readable slowest rows."""
    log = "\n".join(
        [
            "============================= slowest 50 durations =============================",
            "12.50s call     tests/unit/ci/test_local_ci_evidence_contract.py::test_pass",
            " 3.20s call     tests/unit/ci/test_black_timeout_contract.py::test_timeout",
            "0.01s setup    tests/unit/ci/test_local_ci_evidence_contract.py::test_pass",
        ]
    )
    rows = parse_pytest_durations(log, limit=2)
    assert len(rows) == 2
    assert rows[0]["duration_seconds"] == 12.5
    assert "test_pass" in str(rows[0]["nodeid"])
