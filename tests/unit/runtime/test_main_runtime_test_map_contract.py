"""Agent-facing main runtime test map contract tests (#3841)."""

from __future__ import annotations

import json

import pytest

from tests.unit.runtime import _main_runtime_test_map_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REQUIRED_ENTRY_FIELDS = frozenset(
    {"surface", "behavior", "service", "test", "fixtures", "issue_ref"}
)


def test_main_runtime_test_map_file_exists_and_is_partial_coverage() -> None:
    payload = json.loads(helpers.MAIN_RUNTIME_TEST_MAP_JSON.read_text(encoding="utf-8"))
    assert payload["coverage"] == "partial"
    assert payload["catalog_scope"] == "agent-facing-main-runtime-test-map-p2"
    assert payload["limitations"]
    joined = " ".join(payload["limitations"]).lower()
    assert "complete" not in joined or "no coverage percentage" in joined
    assert "partial" in joined or "not all runtime" in joined


def test_committed_map_matches_builder_output() -> None:
    committed = json.loads(helpers.MAIN_RUNTIME_TEST_MAP_JSON.read_text(encoding="utf-8"))
    built = helpers.build_main_runtime_test_map()
    assert committed == built


def test_required_surfaces_are_mapped() -> None:
    payload = helpers.build_main_runtime_test_map()
    assert set(payload["mapped_surfaces"]).issuperset(helpers.REQUIRED_SURFACES)
    assert payload["missing_required_surfaces"] == []


@pytest.mark.parametrize(
    "surface",
    sorted(helpers.REQUIRED_SURFACES),
)
def test_each_required_surface_has_at_least_one_entry(surface: str) -> None:
    payload = helpers.build_main_runtime_test_map()
    surfaces = {entry["surface"] for entry in payload["entries"]}
    assert surface in surfaces


def test_map_entry_schema_and_test_paths_exist() -> None:
    payload = helpers.build_main_runtime_test_map()
    scan = helpers.scan_runtime_test_map_entries(
        tuple(helpers.CANONICAL_RUNTIME_TEST_ENTRIES)
        + tuple(helpers.SUPPLEMENTAL_RUNTIME_TEST_ENTRIES)
    )
    assert scan.missing_test_paths == ()
    assert scan.missing_fixture_paths == ()
    for entry in payload["entries"]:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        assert not missing, f"missing fields: {sorted(missing)}"
        assert (helpers.REPO_ROOT / entry["test"]).is_file()


def test_known_unmapped_runtime_surfaces_are_visible() -> None:
    payload = helpers.build_main_runtime_test_map()
    unmapped = payload["known_unmapped_runtime_surfaces"]
    services = {item["service"] for item in unmapped}
    assert "cdb_candles" in services
    assert "cdb_allocation" in services
    assert all(item.get("reason") for item in unmapped)


def test_runtime_flow_fixtures_are_mapped() -> None:
    payload = helpers.build_main_runtime_test_map()
    flow_entries = [
        entry for entry in payload["entries"] if entry["surface"] == "runtime_flow"
    ]
    assert flow_entries
    fixtures = flow_entries[0]["fixtures"]
    assert "tests/fixtures/runtime_flow/market_tick_happy.json" in fixtures
    for rel in fixtures:
        assert (helpers.REPO_ROOT / rel).is_file()


def test_map_builder_is_deterministic() -> None:
    first = helpers.build_main_runtime_test_map()
    second = helpers.build_main_runtime_test_map()
    assert first == second
