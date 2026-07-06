"""Test Pack docs and issue-pack drift contract tests (#3879).

Parent #3872. Read-only drift detection — no auto-fix, no issue autopilot.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.test_pack import _test_pack_contract_helpers as helpers
from tests.unit.test_pack._test_pack_contract_helpers import (
    CHAOS_DRILL_SCRIPT,
    FIXTURES_ROOT,
    ISSUE_PACK_PROMPT_REFS,
    ISSUE_PACK_README,
    ISSUE_PACK_ROOT,
    PLANNING_LINT_SCRIPT,
    PROMPT_IMPORT_TESTPACK,
    PROMPT_ISSUE_PACK,
    README_EXTENSION_TOOL_PATHS,
    README_FROZEN_STATUS_MARKERS,
    README_QUICKSTART_TOOL_PATHS,
    SCENARIO_CATALOG,
    TEST_PACK_README,
    TEST_PACK_ROOT,
    assert_drift_scanner_source_is_read_only,
    collect_stale_todo_hooks,
    load_scenario_catalog,
    resolve_repo_or_pack_path,
    scan_test_pack_docs_drift,
    score_docs_drift_fixture,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def test_readme_declares_frozen_pack_status() -> None:
    text = TEST_PACK_README.read_text(encoding="utf-8")
    for marker in README_FROZEN_STATUS_MARKERS:
        assert marker in text, f"README missing frozen marker: {marker!r}"


@pytest.mark.parametrize("rel_path", README_QUICKSTART_TOOL_PATHS)
def test_readme_quickstart_tool_paths_exist(rel_path: str) -> None:
    assert resolve_repo_or_pack_path(rel_path).is_file(), rel_path


@pytest.mark.parametrize("rel_path", README_EXTENSION_TOOL_PATHS)
def test_readme_extension_paths_exist(rel_path: str) -> None:
    target = resolve_repo_or_pack_path(rel_path)
    assert target.exists(), rel_path


@pytest.mark.parametrize("rel_path", ISSUE_PACK_PROMPT_REFS)
def test_issue_pack_readme_prompt_refs_exist(rel_path: str) -> None:
    assert resolve_repo_or_pack_path(rel_path).is_file(), rel_path


def test_issue_pack_readme_declares_frozen_local_pack() -> None:
    text = ISSUE_PACK_README.read_text(encoding="utf-8")
    assert "frozen" in text.lower() or "Local / frozen pack" in text
    assert "not the repo-wide default" in text.lower()


def test_issue_pack_issues_directory_is_populated() -> None:
    issues = list((ISSUE_PACK_ROOT / "issues").glob("*.md"))
    assert len(issues) >= 10


def test_prompts_reference_existing_test_pack_tools() -> None:
    for rel in (
        "tools/test_pack/tools/planning/planning_lint.py",
        "tools/test_pack/tools/chaos/generate_scenario.py",
        "tools/test_pack/README.md",
    ):
        assert resolve_repo_or_pack_path(rel).exists(), rel


def test_import_prompt_documents_no_todo_only_pr_rule() -> None:
    text = PROMPT_IMPORT_TESTPACK.read_text(encoding="utf-8")
    assert "No “TODO-only” PR" in text or 'No "TODO-only" PR' in text
    assert "tools/test_pack/" in text


def test_issue_pack_prompt_documents_manual_or_automated_paths() -> None:
    text = PROMPT_ISSUE_PACK.read_text(encoding="utf-8")
    assert "Create the following issues" in text
    assert "jannekbuengener/Claire_de_Binare" in text


def test_scenario_catalog_doc_paths_match_tools() -> None:
    catalog = load_scenario_catalog()
    missing = helpers.collect_missing_scenario_artifacts(catalog)
    assert missing == {}, missing


def test_scenario_template_docs_exist() -> None:
    catalog = load_scenario_catalog()
    evidence_paths = {
        scenario["evidence"]
        for scenario in catalog.get("scenarios", [])
        if scenario.get("evidence")
    }
    for rel in evidence_paths:
        assert resolve_repo_or_pack_path(rel).is_file(), rel


def test_stale_todo_hooks_are_visible_in_known_surfaces() -> None:
    scan = scan_test_pack_docs_drift()
    assert scan.stale_todo_hooks, "expected stale TODO hooks to be visible"
    joined = "\n".join(scan.stale_todo_hooks)
    assert "TODO hooks for ingestion" in joined
    assert "adapters/ADAPTERS" in joined or "ADAPTERS.md" in joined


def test_issue_005_stale_hook_is_visible() -> None:
    issue_text = (
        ISSUE_PACK_ROOT
        / "issues"
        / "005_p0_test_wire_test_pack_v2_ingestion_hook_metrics_snapshot_as.md"
    ).read_text(encoding="utf-8")
    hooks = collect_stale_todo_hooks(issue_text, label="issue_005")
    assert hooks


def test_fixture_detects_missing_tool_path_drift() -> None:
    fixture = _load_fixture("docs_drift_fixture_missing_path.json")
    result = score_docs_drift_fixture(fixture)
    assert result.has_missing_paths
    assert "tools/metrics/missing_snapshot.py" in result.missing_paths
    assert result.stale_todo_hooks


def test_fixture_canon_documents_drift_rules() -> None:
    canon = _load_fixture("docs_drift_canon_v1.json")
    assert canon["no_auto_fix_contract"]["mode"] == "detect_only"
    assert "automatic issue creation" in canon["no_auto_fix_contract"]["forbidden"]


def test_real_repo_docs_drift_scan_has_no_missing_active_paths() -> None:
    scan = scan_test_pack_docs_drift()
    assert scan.missing_paths == (), (
        "active canon paths must resolve; drift findings: "
        f"{[f.detail for f in scan.findings]}"
    )


def test_no_auto_fix_contract_helpers_are_read_only() -> None:
    source = Path(helpers.__file__).read_text(encoding="utf-8")
    violations = assert_drift_scanner_source_is_read_only(source)
    assert violations == [], violations


def test_drift_scan_does_not_mutate_readme_mtime() -> None:
    before = TEST_PACK_README.stat().st_mtime_ns
    scan_test_pack_docs_drift()
    after = TEST_PACK_README.stat().st_mtime_ns
    assert before == after


def test_readme_references_chaos_drill_script_in_quickstart() -> None:
    text = TEST_PACK_README.read_text(encoding="utf-8").replace("\\", "/")
    assert "infrastructure/scripts/run-chaos-drill.ps1" in text
    assert CHAOS_DRILL_SCRIPT.is_file()


def test_pack_supporting_scripts_exist_for_docs_references() -> None:
    assert CHAOS_DRILL_SCRIPT.is_file()
    assert PLANNING_LINT_SCRIPT.is_file()
    assert SCENARIO_CATALOG.is_file()
    assert TEST_PACK_ROOT.is_dir()
