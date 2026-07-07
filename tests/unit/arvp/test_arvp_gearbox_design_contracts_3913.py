"""ARVP gearbox design contract tests (#3913).

Validates repo-backed gearbox design docs and JSON schemas. No runtime, no live
GitHub, no trade-approval claims.
"""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft7Validator

from tests.unit.arvp import _arvp_gearbox_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _load_json(path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.parametrize(
    ("contract_name", "schema_path", "example_path"),
    helpers.GEARBOX_SCHEMAS,
)
def test_gearbox_schema_example_validates(
    contract_name: str,
    schema_path,
    example_path,
) -> None:
    assert schema_path.is_file(), f"missing schema for {contract_name}"
    assert example_path.is_file(), f"missing example for {contract_name}"
    schema = _load_json(schema_path)
    example = _load_json(example_path)
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda e: e.message)
    assert not errors, [e.message for e in errors]


def test_design_doc_exists_and_references_all_five_contracts() -> None:
    text = helpers.DESIGN_DOC.read_text(encoding="utf-8")
    for contract_name, schema_path, _example_path in helpers.GEARBOX_SCHEMAS:
        assert contract_name in text
        rel = schema_path.relative_to(helpers.REPO_ROOT).as_posix()
        assert rel in text


def test_design_doc_declares_selector_not_trade_approval() -> None:
    text = helpers.DESIGN_DOC.read_text(encoding="utf-8").lower()
    assert "not trade approval" in text or "not** trade approval" in text
    assert "no_trade_approval" in text


def test_design_doc_declares_protective_idle_valid() -> None:
    text = helpers.DESIGN_DOC.read_text(encoding="utf-8")
    assert "Protective Idle" in text
    assert "not failure" in text.lower() or "not** failure" in text


def test_design_doc_separates_learning_and_trading_loops() -> None:
    text = helpers.DESIGN_DOC.read_text(encoding="utf-8")
    assert "Learning Loop" in text
    assert "Trading Loop" in text
    assert "never" in text.lower()


def test_design_doc_marks_lr_no_go_and_3912_not_ready() -> None:
    text = helpers.DESIGN_DOC.read_text(encoding="utf-8")
    assert "NO-GO" in text
    assert "#3912" in text
    assert "not ready" in text.lower()


def test_design_doc_classifies_3909_3911_as_prerequisites() -> None:
    text = helpers.DESIGN_DOC.read_text(encoding="utf-8")
    for issue in ("#3909", "#3910", "#3911"):
        assert issue in text
    assert "prerequisite" in text.lower() or "Technical prerequisite" in text


def test_selector_example_enforces_no_trade_approval() -> None:
    payload = _load_json(helpers.GEARBOX_SCHEMAS[1][2])
    assert payload["no_trade_approval"] is True


def test_protective_idle_example_is_valid_non_error_non_approval() -> None:
    payload = _load_json(helpers.GEARBOX_SCHEMAS[3][2])
    assert payload["is_valid_output"] is True
    assert payload["is_error"] is False
    assert payload["is_trade_approval"] is False


def test_gear_reason_codes_include_required_minimum_set() -> None:
    payload = _load_json(helpers.GEARBOX_SCHEMAS[2][2])
    codes = {entry["code"] for entry in payload["codes"]}
    assert helpers.REQUIRED_REASON_CODES.issubset(codes)


def test_loop_boundary_forbids_selector_as_order_approval() -> None:
    payload = _load_json(helpers.GEARBOX_SCHEMAS[4][2])
    assert payload["selector_output_is_not_order_approval"] is True
    assert "treat_selector_as_order_approval" in payload["trading_loop"]["must_not"]
