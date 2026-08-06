"""hh_hl analyzer profile — planning-only (#4374).

No 21/19 matrix assumption. Classifications are research-only (no promotion).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.hh_hl_campaign_grid import expand_hh_hl_variants

ANALYZER_PROFILE_ID = "hh_hl_analyzer_prep_v1"
ALLOWED_CLASSIFICATIONS = (
    "PROMISING",
    "INCONCLUSIVE",
    "REJECTED",
    "BLOCKED",
)

CLASSIFICATION_MEANING = {
    "PROMISING": "only research follow-up, no promotion",
    "INCONCLUSIVE": "no robust direction",
    "REJECTED": "candidate/grid yields no durable evidence in bound scope",
    "BLOCKED": "contracts, data, reproduction, or completeness failed",
}


class HhHlAnalyzerProfileError(ValueError):
    """Fail-closed analyzer profile violation."""


def build_hh_hl_analyzer_profile(
    *,
    expected_run_keys: Sequence[str],
    reproduction_pass_required: bool = True,
) -> dict[str, Any]:
    variants = expand_hh_hl_variants()
    if len(variants) == 21 or len(variants) == 19:
        # Guard against accidental #4153 matrix reuse in this profile.
        raise HhHlAnalyzerProfileError("ANALYZER_MUST_NOT_ASSUME_4153_MATRIX")

    keys = list(expected_run_keys)
    if len(keys) != len(set(keys)):
        raise HhHlAnalyzerProfileError("ANALYZER_DUPLICATE_EXPECTED_KEYS")

    body = {
        "analyzer_profile_id": ANALYZER_PROFILE_ID,
        "variant_count": len(variants),
        "expected_run_key_count": len(keys),
        "expected_run_keys": keys,
        "reproduction_pass_required": reproduction_pass_required,
        "allowed_classifications": list(ALLOWED_CLASSIFICATIONS),
        "classification_meaning": dict(CLASSIFICATION_MEANING),
        "auto_promotion": False,
        "pnl_only_ranking_forbidden": True,
        "required_reported_metrics": [
            "fees_total_quote",
            "max_drawdown_r",
            "expectancy_r",
            "closed_trades_total",
            "window_stability",
        ],
        "insufficient_evidence_default": "INCONCLUSIVE",
        "matrix_assumptions": {
            "slots_21": False,
            "physical_sets_19": False,
        },
    }
    return {
        **body,
        "analyzer_profile_fingerprint": canonical_hash(body),
        "status": "PLANNING_ONLY",
    }


def classify_fixture_completeness(
    *,
    expected_run_keys: Sequence[str],
    present_run_keys: Sequence[str],
    reproduction_pass: bool | None,
    foreign_run_keys: Sequence[str] = (),
) -> dict[str, Any]:
    expected = set(expected_run_keys)
    present = set(present_run_keys)
    foreign = set(foreign_run_keys) | (present - expected)
    missing = sorted(expected - present)
    if foreign or missing or reproduction_pass is not True:
        return {
            "classification": "BLOCKED",
            "missing_run_keys": missing,
            "foreign_run_keys": sorted(foreign),
            "reproduction_pass": reproduction_pass,
        }
    return {
        "classification": "INCONCLUSIVE",
        "missing_run_keys": [],
        "foreign_run_keys": [],
        "reproduction_pass": True,
        "note": "Fixture complete; no real campaign economics evaluated.",
    }


def assert_not_4153_matrix(payload: Mapping[str, Any]) -> None:
    if (
        payload.get("matrix_slots") == 21
        or payload.get("physical_parameter_sets") == 19
    ):
        raise HhHlAnalyzerProfileError("ANALYZER_4153_MATRIX_LEAK")
