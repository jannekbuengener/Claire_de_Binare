"""Fixture-based ARVP window qualification contract tests (#3827).

Dataset cadence, warmup/live split, regime segments, and paper-reference availability.
No live DB, runtime capture, or silent promotion.
"""

from __future__ import annotations

import pytest

from tests.unit.arvp._arvp_window_qualification_helpers import (
    load_window_qualification_cases,
    qualify_arvp_window_case,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


@pytest.mark.parametrize("case", load_window_qualification_cases(), ids=lambda c: c["case_id"])
def test_window_qualification_fixture_verdict(case: dict, tmp_path) -> None:
    result = qualify_arvp_window_case(case, tmp_path)
    assert result.verdict == case["expected_verdict"]


def test_gap_cadence_violation_is_blocked_not_promoted(tmp_path) -> None:
    case = next(c for c in load_window_qualification_cases() if c["case_id"] == "cadence_gap_blocked")
    result = qualify_arvp_window_case(case, tmp_path)
    assert result.verdict == "BLOCKED"
    assert result.promotes is False
    assert result.cadence_ok is False


def test_missing_regime_surfaces_limitation_without_pass(tmp_path) -> None:
    case = next(c for c in load_window_qualification_cases() if c["case_id"] == "missing_regime_warn")
    result = qualify_arvp_window_case(case, tmp_path)
    assert result.verdict == "WARN"
    assert result.regime_available is False
    assert result.promotes is False
    assert any("regime" in note.lower() for note in result.limitations)


def test_missing_paper_reference_surfaces_limitation(tmp_path) -> None:
    case = next(
        c for c in load_window_qualification_cases() if c["case_id"] == "paper_reference_missing_warn"
    )
    result = qualify_arvp_window_case(case, tmp_path)
    assert result.verdict == "WARN"
    assert result.paper_reference_available is False
    assert result.promotes is False


def test_strict_pass_case_has_warmup_live_split(tmp_path) -> None:
    case = next(c for c in load_window_qualification_cases() if c["case_id"] == "strict_cadence_pass")
    result = qualify_arvp_window_case(case, tmp_path)
    assert result.verdict == "PASS"
    assert result.cadence_ok is True
    assert result.warmup_live_ok is True
    assert result.regime_available is True
    assert result.paper_reference_available is True


def test_all_warmup_no_live_is_blocked(tmp_path) -> None:
    case = next(c for c in load_window_qualification_cases() if c["case_id"] == "all_warmup_no_live_blocked")
    result = qualify_arvp_window_case(case, tmp_path)
    assert result.verdict == "BLOCKED"
    assert result.warmup_live_ok is False
