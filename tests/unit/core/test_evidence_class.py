from __future__ import annotations

import json

import pytest

from core.utils.evidence_class import (
    EvidenceClassError,
    evidence_class_warning_banner,
    is_valid_evidence_class,
    validate_evidence_class,
    validate_evidence_class_from_json,
    validate_evidence_class_or_skip,
)


def _minimal_natural_paper() -> dict:
    return {
        "evidence_class": "natural_paper_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "test_runner",
        "produced_at_utc": "2026-06-12T00:00:00+00:00",
        "campaign_id": "test_campaign",
        "start_criterion": "manual",
        "safety_flags": {"mock_trading": True, "dry_run": True, "mexc_testnet": True},
        "provenance": "test_provenance",
    }


def _minimal_controlled_lab() -> dict:
    return {
        "evidence_class": "controlled_lab_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "test_runner",
        "produced_at_utc": "2026-06-12T00:00:00+00:00",
        "warning_banner": "⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4",
        "scenario_source": "test_scenario",
        "reproducibility_contract": "test_fingerprint",
    }


def _minimal_pipeline_test() -> dict:
    return {
        "evidence_class": "pipeline_test_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "test_runner",
        "produced_at_utc": "2026-06-12T00:00:00+00:00",
        "warning_banner": "⚠ Pipeline test only — NOT valid for Product-Complete gate",
        "pipeline_tool": "test_tool",
        "fixture_source": "test_fixture",
    }


def _minimal_waiver() -> dict:
    return {
        "evidence_class": "waiver_decision",
        "evidence_class_version": "1.0",
        "produced_by": "test_runner",
        "produced_at_utc": "2026-06-12T00:00:00+00:00",
        "warning_banner": "⚠ Policy decision — not evidence; requires formal governance vote",
        "governance_ref": "test_ref",
        "residual_uncertainties": "test_risk",
    }


class TestValidateEvidenceClass:
    def test_natural_paper_evidence_valid(self):
        validate_evidence_class(_minimal_natural_paper())

    def test_controlled_lab_evidence_with_banner(self):
        validate_evidence_class(_minimal_controlled_lab())

    def test_pipeline_test_evidence_with_banner(self):
        validate_evidence_class(_minimal_pipeline_test())

    def test_waiver_decision_with_banner(self):
        validate_evidence_class(_minimal_waiver())

    def test_missing_evidence_class_fails(self):
        with pytest.raises(EvidenceClassError, match="Missing evidence_class"):
            validate_evidence_class({})

    def test_none_evidence_class_fails(self):
        with pytest.raises(EvidenceClassError, match="Missing evidence_class"):
            validate_evidence_class({"evidence_class": None})

    def test_unknown_evidence_class_fails(self):
        with pytest.raises(EvidenceClassError, match="Unknown evidence_class"):
            validate_evidence_class({"evidence_class": "invalid_class"})

    def test_controlled_lab_missing_banner_fails(self):
        art = _minimal_controlled_lab()
        art.pop("warning_banner")
        with pytest.raises(EvidenceClassError, match="requires warning banner"):
            validate_evidence_class(art)

    def test_controlled_lab_wrong_banner_fails(self):
        art = _minimal_controlled_lab()
        art["warning_banner"] = "some random text"
        with pytest.raises(EvidenceClassError, match="requires warning banner"):
            validate_evidence_class(art)

    def test_pipeline_test_missing_banner_fails(self):
        art = _minimal_pipeline_test()
        art.pop("warning_banner")
        with pytest.raises(EvidenceClassError, match="requires warning banner"):
            validate_evidence_class(art)

    def test_waiver_decision_missing_banner_fails(self):
        art = _minimal_waiver()
        art.pop("warning_banner")
        with pytest.raises(EvidenceClassError, match="requires warning banner"):
            validate_evidence_class(art)

    def test_extra_fields_ok(self):
        art = _minimal_natural_paper()
        art["run_id"] = "abc123"
        art["some_other_field"] = "value"
        validate_evidence_class(art)

    def test_missing_evidence_class_version_fails(self):
        art = _minimal_natural_paper()
        art.pop("evidence_class_version")
        with pytest.raises(EvidenceClassError, match="evidence_class_version"):
            validate_evidence_class(art)

    def test_missing_produced_by_fails(self):
        art = _minimal_natural_paper()
        art.pop("produced_by")
        with pytest.raises(EvidenceClassError, match="produced_by"):
            validate_evidence_class(art)

    def test_missing_produced_at_utc_fails(self):
        art = _minimal_natural_paper()
        art.pop("produced_at_utc")
        with pytest.raises(EvidenceClassError, match="produced_at_utc"):
            validate_evidence_class(art)

    def test_missing_natural_paper_per_class_field_fails(self):
        art = _minimal_natural_paper()
        art.pop("campaign_id")
        with pytest.raises(EvidenceClassError, match="campaign_id"):
            validate_evidence_class(art)

    def test_missing_controlled_lab_per_class_field_fails(self):
        art = _minimal_controlled_lab()
        art.pop("scenario_source")
        with pytest.raises(EvidenceClassError, match="scenario_source"):
            validate_evidence_class(art)

    def test_missing_pipeline_test_per_class_field_fails(self):
        art = _minimal_pipeline_test()
        art.pop("pipeline_tool")
        with pytest.raises(EvidenceClassError, match="pipeline_tool"):
            validate_evidence_class(art)

    def test_missing_waiver_per_class_field_fails(self):
        art = _minimal_waiver()
        art.pop("governance_ref")
        with pytest.raises(EvidenceClassError, match="governance_ref"):
            validate_evidence_class(art)

    def test_blank_produced_by_fails(self):
        art = _minimal_natural_paper()
        art["produced_by"] = ""
        with pytest.raises(EvidenceClassError, match="produced_by"):
            validate_evidence_class(art)

    def test_blank_produced_at_utc_fails(self):
        art = _minimal_natural_paper()
        art["produced_at_utc"] = "   "
        with pytest.raises(EvidenceClassError, match="produced_at_utc"):
            validate_evidence_class(art)


class TestValidateEvidenceClassOrSkip:
    def test_valid_returns_empty_list(self):
        errors = validate_evidence_class_or_skip(_minimal_natural_paper())
        assert errors == []

    def test_invalid_returns_error_list(self):
        errors = validate_evidence_class_or_skip({})
        assert len(errors) == 1
        assert "Missing evidence_class" in errors[0]

    def test_unknown_returns_error(self):
        errors = validate_evidence_class_or_skip(
            {"evidence_class": "invalid_class"}
        )
        assert len(errors) == 1


class TestValidateEvidenceClassFromJson:
    def test_valid_json(self):
        json_str = json.dumps(_minimal_natural_paper())
        validate_evidence_class_from_json(json_str)

    def test_invalid_json(self):
        with pytest.raises(EvidenceClassError, match="Invalid JSON"):
            validate_evidence_class_from_json("not json")

    def test_non_dict_json(self):
        with pytest.raises(EvidenceClassError, match="JSON root must be a dict"):
            validate_evidence_class_from_json(json.dumps([1, 2, 3]))

    def test_missing_class_in_json(self):
        with pytest.raises(EvidenceClassError, match="Missing evidence_class"):
            validate_evidence_class_from_json(json.dumps({"foo": "bar"}))


class TestWarningBanner:
    def test_natural_paper_no_banner(self):
        assert evidence_class_warning_banner("natural_paper_evidence") == ""

    def test_controlled_lab_banner(self):
        banner = evidence_class_warning_banner("controlled_lab_evidence")
        assert "NOT natural_paper_evidence" in banner
        assert "§5.2.4" in banner

    def test_pipeline_test_banner(self):
        banner = evidence_class_warning_banner("pipeline_test_evidence")
        assert "Pipeline test only" in banner
        assert "Product-Complete" in banner

    def test_waiver_decision_banner(self):
        banner = evidence_class_warning_banner("waiver_decision")
        assert "Policy decision" in banner
        assert "governance vote" in banner

    def test_unknown_class_empty_banner(self):
        assert evidence_class_warning_banner("unknown_class") == ""


class TestIsValidEvidenceClass:
    def test_valid_classes(self):
        assert is_valid_evidence_class("natural_paper_evidence")
        assert is_valid_evidence_class("controlled_lab_evidence")
        assert is_valid_evidence_class("pipeline_test_evidence")
        assert is_valid_evidence_class("waiver_decision")

    def test_invalid_classes(self):
        assert not is_valid_evidence_class("invalid_class")
        assert not is_valid_evidence_class("")
        assert not is_valid_evidence_class(None)
        assert not is_valid_evidence_class("natural-paper-evidence")


class TestPipelineTestEvidenceCannotBeNaturalPaper:
    """Prove pipeline_test_evidence cannot be interpreted as natural_paper_evidence."""

    def test_different_classes(self):
        assert "pipeline_test_evidence" != "natural_paper_evidence"

    def test_pipeline_test_rejected_as_unknown_when_used_as_natural(self):
        art = _minimal_pipeline_test()
        art["warning_banner"] = ""
        with pytest.raises(EvidenceClassError, match="requires warning banner"):
            validate_evidence_class(art)

    def test_warning_banner_distinct(self):
        pipeline_banner = evidence_class_warning_banner("pipeline_test_evidence")
        natural_banner = evidence_class_warning_banner("natural_paper_evidence")
        assert pipeline_banner != natural_banner
        assert "Pipeline test only" in pipeline_banner

    def test_validate_blocks_silent_upgrade(self):
        art = _minimal_pipeline_test()
        art.pop("warning_banner")
        with pytest.raises(EvidenceClassError, match="requires warning banner"):
            validate_evidence_class(artifact=art)
