from __future__ import annotations

import json
from typing import Any

_VALID_CLASSES: set[str] = {
    "natural_paper_evidence",
    "controlled_lab_evidence",
    "pipeline_test_evidence",
    "waiver_decision",
}

_WARNING_BANNERS: dict[str, str] = {
    "controlled_lab_evidence": (
        "⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4"
    ),
    "pipeline_test_evidence": (
        "⚠ Pipeline test only — NOT valid for Product-Complete gate"
    ),
    "waiver_decision": (
        "⚠ Policy decision — not evidence; requires formal governance vote"
    ),
}

SCHEMA_VERSION = "1.0"

_BASE_REQUIRED_FIELDS: set[str] = {
    "evidence_class_version",
    "produced_by",
    "produced_at_utc",
}

_CLASS_REQUIRED_FIELDS: dict[str, set[str]] = {
    "natural_paper_evidence": {
        "campaign_id",
        "start_criterion",
        "safety_flags",
        "provenance",
    },
    "controlled_lab_evidence": {
        "scenario_source",
        "reproducibility_contract",
    },
    "pipeline_test_evidence": {
        "pipeline_tool",
        "fixture_source",
    },
    "waiver_decision": {
        "governance_ref",
        "residual_uncertainties",
    },
}


class EvidenceClassError(ValueError):
    """Raised when evidence_class validation fails."""


def _check_required_fields(artifact: dict[str, Any], ec: str) -> None:
    """Check all required base and per-class fields are present and non-blank."""
    missing: list[str] = []
    for field in _BASE_REQUIRED_FIELDS:
        val = artifact.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    for field in _CLASS_REQUIRED_FIELDS.get(ec, set()):
        val = artifact.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    if missing:
        raise EvidenceClassError(
            f"evidence_class={ec!r} missing required field(s): "
            f"{', '.join(sorted(missing))}"
        )
    ec_version = artifact.get("evidence_class_version")
    if ec_version is not None and ec_version != SCHEMA_VERSION:
        raise EvidenceClassError(
            f"evidence_class_version must be {SCHEMA_VERSION!r}, "
            f"got {ec_version!r}"
        )


def validate_evidence_class(artifact: dict[str, Any]) -> None:
    """Validate evidence_class metadata on an ARVP evidence artifact.

    Args:
        artifact: Dict representing an ARVP evidence artifact.
            Must contain at minimum an ``evidence_class`` key.

    Raises:
        EvidenceClassError: If validation fails (missing, unknown,
            missing required warning banner, or missing required fields).
    """
    ec = artifact.get("evidence_class")

    if ec is None:
        raise EvidenceClassError(
            "Missing evidence_class — every ARVP evidence artifact "
            "must carry exactly one evidence_class"
        )

    if ec not in _VALID_CLASSES:
        raise EvidenceClassError(
            f"Unknown evidence_class={ec!r}. "
            f"Valid values: {', '.join(sorted(_VALID_CLASSES))}"
        )

    if ec in _WARNING_BANNERS:
        expected_banner = _WARNING_BANNERS[ec]
        actual_banner = artifact.get("warning_banner", "")

        if expected_banner not in actual_banner:
            raise EvidenceClassError(
                f"evidence_class={ec!r} requires warning banner "
                f"containing: {expected_banner!r}. "
                f"Got: {actual_banner!r}"
            )

    _check_required_fields(artifact, ec)


def validate_evidence_class_or_skip(artifact: dict[str, Any]) -> list[str]:
    """Non-raising variant that returns a list of error messages.

    Returns an empty list when validation passes.
    """
    errors: list[str] = []
    try:
        validate_evidence_class(artifact)
    except EvidenceClassError as exc:
        errors.append(str(exc))
    return errors


def evidence_class_warning_banner(evidence_class: str) -> str:
    """Return the required warning banner for the given evidence class.

    Returns an empty string for classes that do not require a banner.
    """
    return _WARNING_BANNERS.get(evidence_class, "")


def validate_evidence_class_from_json(json_str: str) -> None:
    """Parse a JSON string and validate evidence_class metadata."""
    try:
        artifact = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise EvidenceClassError(f"Invalid JSON: {exc}") from exc

    if not isinstance(artifact, dict):
        raise EvidenceClassError("JSON root must be a dict/object")

    validate_evidence_class(artifact)


def is_valid_evidence_class(value: str) -> bool:
    """Check if the given string is a valid evidence class value."""
    return value in _VALID_CLASSES
