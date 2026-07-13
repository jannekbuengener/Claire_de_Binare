"""Agent-facing ARVP test map contract tests (#3824)."""

from __future__ import annotations

import json

import pytest

from tests.unit.arvp import _arvp_test_map_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REQUIRED_ENTRY_FIELDS = frozenset(
    {"surface", "behavior", "service", "test", "fixtures", "issue_ref"}
)


def test_arvp_test_map_file_exists_and_is_partial_coverage() -> None:
    payload = json.loads(helpers.ARVP_TEST_MAP_JSON.read_text(encoding="utf-8"))
    assert payload["coverage"] == "partial"
    assert payload["catalog_scope"] == "agent-facing-arvp-test-map-p2"
    assert payload["limitations"]
    joined = " ".join(payload["limitations"]).lower()
    assert "complete" not in joined or "no coverage percentage" in joined


def test_committed_map_matches_builder_output() -> None:
    committed = json.loads(helpers.ARVP_TEST_MAP_JSON.read_text(encoding="utf-8"))
    built = helpers.build_arvp_test_map()
    assert committed == built


def test_required_surfaces_are_mapped() -> None:
    payload = helpers.build_arvp_test_map()
    assert set(payload["mapped_surfaces"]).issuperset(helpers.REQUIRED_SURFACES)
    assert payload["missing_required_surfaces"] == []


@pytest.mark.parametrize("surface", sorted(helpers.REQUIRED_SURFACES))
def test_each_required_surface_has_at_least_one_entry(surface: str) -> None:
    payload = helpers.build_arvp_test_map()
    surfaces = {entry["surface"] for entry in payload["entries"]}
    assert surface in surfaces


def test_map_entry_schema_and_test_paths_exist() -> None:
    payload = helpers.build_arvp_test_map()
    scan = helpers.scan_arvp_test_map_entries(helpers.CANONICAL_ARVP_TEST_ENTRIES)
    assert scan.missing_test_paths == ()
    assert scan.missing_fixture_paths == ()
    for entry in payload["entries"]:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        assert not missing, f"missing fields: {sorted(missing)}"
        assert (helpers.REPO_ROOT / entry["test"]).is_file()


def test_known_unmapped_arvp_surfaces_are_visible() -> None:
    payload = helpers.build_arvp_test_map()
    unmapped = payload["known_unmapped_arvp_surfaces"]
    surfaces = {item["surface"] for item in unmapped}
    assert "natural_paper_observation" in surfaces
    assert all(item.get("reason") for item in unmapped)


def test_p0_p1_issue_refs_are_present_on_entries() -> None:
    payload = helpers.build_arvp_test_map()
    issue_refs = {entry["issue_ref"] for entry in payload["entries"]}
    expected_minimum = {
        "#3821",
        "#3822",
        "#3823",
        "#3826",
        "#3827",
        "#3828",
        "#3829",
    }
    assert expected_minimum.issubset(issue_refs)


def test_parallel_ledger_isolation_guard_is_mapped() -> None:
    payload = helpers.build_arvp_test_map()
    matches = [
        entry
        for entry in payload["entries"]
        if entry["issue_ref"] == "#3911"
        and entry["surface"] == "parallel_ledger_isolation"
    ]
    assert len(matches) == 1
    assert (
        helpers.REPO_ROOT / matches[0]["test"]
    ).is_file()


def test_map_builder_is_deterministic() -> None:
    first = helpers.build_arvp_test_map()
    second = helpers.build_arvp_test_map()
    assert first == second
