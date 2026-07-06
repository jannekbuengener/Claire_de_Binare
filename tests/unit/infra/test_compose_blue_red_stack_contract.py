"""Compose layer and BLUE/RED stack contract tests (#3856).

Fixture-backed, static YAML contracts — no Docker runtime, no compose mutation.
Refs #3855, #1445, #2985.
"""

from __future__ import annotations

import pytest

from tests.unit.infra._compose_stack_contract_helpers import (
    BLUE_CANONICAL_SERVICES,
    CANONICAL_NETWORK,
    CANONICAL_RUNTIME_FILES,
    COMPOSE_DIR,
    COMPOSE_LAYER_FILES,
    LEGACY_CI_FILES,
    RED_CANONICAL_SERVICES,
    REPO_ROOT,
    TEST_NETWORK,
    container_name_mismatches,
    is_known_canonical_volume,
    load_compose_yaml,
    network_names,
    service_names,
    services_missing_healthcheck,
    volume_names,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize("filename,layer", list(COMPOSE_LAYER_FILES.items()))
def test_compose_layer_classification_is_fixture_backed(
    filename: str, layer: str
) -> None:
    compose = load_compose_yaml(filename)
    assert compose.get("services"), f"{filename} must declare services"
    assert layer in {
        "canonical_runtime",
        "legacy_ci",
        "legacy_overlay",
        "optional_overlay",
    }


def test_canonical_runtime_files_exist_and_are_not_legacy_ci() -> None:
    for filename in CANONICAL_RUNTIME_FILES:
        assert COMPOSE_LAYER_FILES[filename] == "canonical_runtime"
        load_compose_yaml(filename)


def test_legacy_ci_files_are_classified_separately_from_canonical_runtime() -> None:
    for filename in LEGACY_CI_FILES:
        assert COMPOSE_LAYER_FILES[filename] != "canonical_runtime"
        load_compose_yaml(filename)


def test_blue_red_canon_service_sets_do_not_overlap() -> None:
    overlap = BLUE_CANONICAL_SERVICES & RED_CANONICAL_SERVICES
    assert not overlap, f"BLUE/RED service overlap: {sorted(overlap)}"


def test_compose_blue_declares_full_blue_canon() -> None:
    blue = load_compose_yaml("compose.blue.yml")
    declared = set(service_names(blue))
    missing = BLUE_CANONICAL_SERVICES - declared
    assert not missing, f"compose.blue.yml missing BLUE services: {sorted(missing)}"
    assert declared.issubset(BLUE_CANONICAL_SERVICES)


def test_compose_red_declares_full_red_canon() -> None:
    red = load_compose_yaml("compose.red.yml")
    declared = set(service_names(red))
    missing = RED_CANONICAL_SERVICES - declared
    assert not missing, f"compose.red.yml missing RED services: {sorted(missing)}"
    assert declared.issubset(RED_CANONICAL_SERVICES)


def test_canonical_compose_uses_cdb_network() -> None:
    for filename in CANONICAL_RUNTIME_FILES:
        compose = load_compose_yaml(filename)
        nets = network_names(compose)
        assert CANONICAL_NETWORK in nets, f"{filename} must declare {CANONICAL_NETWORK}"


def test_test_overlay_uses_isolated_test_network() -> None:
    test_overlay = load_compose_yaml("test.yml")
    nets = network_names(test_overlay)
    assert TEST_NETWORK in nets, "test.yml must use isolated cdb_test_network"


def test_canonical_service_container_names_match_service_keys() -> None:
    for filename in CANONICAL_RUNTIME_FILES:
        compose = load_compose_yaml(filename)
        mismatches = container_name_mismatches(compose)
        assert not mismatches, f"{filename} container_name drift: {mismatches}"


def test_canonical_volumes_use_cdb_prefix_or_known_data_names() -> None:
    for filename in CANONICAL_RUNTIME_FILES:
        compose = load_compose_yaml(filename)
        for vol in volume_names(compose):
            assert is_known_canonical_volume(vol), (
                f"{filename} unexpected volume name: {vol}"
            )


def test_blue_stack_services_have_healthchecks() -> None:
    blue = load_compose_yaml("compose.blue.yml")
    missing = services_missing_healthcheck(blue)
    assert not missing, f"BLUE services without healthcheck: {missing}"


def test_red_stack_healthcheck_gaps_are_visible() -> None:
    """Document known RED gaps (e.g. cdb_cadvisor) without blocking canon drift."""
    red = load_compose_yaml("compose.red.yml")
    missing = services_missing_healthcheck(red)
    assert missing == ["cdb_cadvisor"], (
        "Update contract if RED healthcheck posture changed; "
        f"unexpected missing: {missing}"
    )


def test_compose_readme_distinguishes_canonical_from_legacy() -> None:
    readme = (COMPOSE_DIR / "README.md").read_text(encoding="utf-8")
    assert "compose.blue.yml" in readme
    assert "compose.red.yml" in readme
    assert "Legacy" in readme or "legacy" in readme
    assert "base.yml" in readme


def test_stack_lifecycle_doc_points_at_blue_red_canon() -> None:
    lifecycle = (REPO_ROOT / "knowledge" / "systems" / "STACK_LIFECYCLE.md").read_text(
        encoding="utf-8"
    )
    assert "compose.blue.yml" in lifecycle
    assert "compose.red.yml" in lifecycle
    assert "base.yml" in lifecycle
    assert "LEGACY" in lifecycle or "legacy" in lifecycle
