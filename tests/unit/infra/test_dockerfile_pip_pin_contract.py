"""pip pin security contract for productive service images (#4095).

Guards the remediation of CVE-2026-8643 (pip < 26.1.2): every productive image
that installs pip must pin a version at or above the advisory floor, all images
must agree on one version, and the finding must not be silenced via
`.trivyignore`.

Static Dockerfile parsing only — no image build, no registry access, no runtime.
"""

from __future__ import annotations

import pytest

from tests.unit.infra import _dockerfile_pip_pin_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_every_productive_image_pins_pip() -> None:
    missing = [
        dockerfile
        for dockerfile in helpers.PRODUCTIVE_IMAGE_DOCKERFILES
        if not helpers.collect_pip_pins(dockerfile)
    ]
    assert missing == [], f"productive images without an explicit pip pin: {missing}"


@pytest.mark.parametrize("cve, floor", sorted(helpers.PIP_ADVISORY_FLOORS.items()))
def test_productive_pip_pins_meet_every_known_advisory_floor(
    cve: str, floor: str
) -> None:
    floor_version = helpers.parse_version(floor)
    violations = [
        (pin.dockerfile, pin.line_number, pin.version)
        for pin in helpers.collect_all_productive_pins()
        if helpers.parse_version(pin.version) < floor_version
    ]
    assert violations == [], f"pip pins below the {cve} floor {floor}: {violations}"


def test_productive_pip_pins_use_one_agreed_version() -> None:
    versions = {pin.version for pin in helpers.collect_all_productive_pins()}
    assert versions == {
        helpers.SAFE_PIP_VERSION
    }, f"productive images must share pip=={helpers.SAFE_PIP_VERSION}, found {sorted(versions)}"


def test_execution_pins_both_build_venv_and_runtime_pip() -> None:
    pins = helpers.collect_pip_pins(helpers.EXECUTION_DOCKERFILE)
    assert len(pins) == helpers.EXPECTED_EXECUTION_PIN_COUNT, (
        "the execution image copies its build venv into the runtime stage, so the "
        f"venv pip and the global pip must both be pinned; found {pins}"
    )


def test_productive_images_do_not_float_pip_unpinned() -> None:
    floating = [
        dockerfile
        for dockerfile in helpers.PRODUCTIVE_IMAGE_DOCKERFILES
        if helpers.has_unpinned_pip_upgrade(dockerfile)
    ]
    assert floating == [], f"productive images with an unpinned pip upgrade: {floating}"


def test_dockerfile_inventory_has_no_unclassified_surface() -> None:
    known = set(helpers.PRODUCTIVE_IMAGE_DOCKERFILES) | set(
        helpers.NON_PRODUCTIVE_DOCKERFILES
    )
    unclassified = sorted(set(helpers.discover_dockerfiles()) - known)
    assert unclassified == [], (
        "new Dockerfile surface must be classified as productive or non-productive "
        f"before it can ship pip: {unclassified}"
    )


def test_pip_cve_is_not_silenced_by_trivyignore() -> None:
    entries = helpers.trivyignore_entries()
    silenced = sorted(set(entries) & set(helpers.PIP_ADVISORY_FLOORS))
    assert silenced == [], f"pip advisories must be fixed, not ignored: {silenced}"
