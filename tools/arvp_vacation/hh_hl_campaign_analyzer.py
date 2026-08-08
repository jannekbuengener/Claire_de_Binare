"""hh_hl analyzer profile + durable classifier (#4374).

No 21/19 matrix assumption. Classifications are research-only (no promotion).
window_stability is descriptive evidence; economic REJECTED/PROMISING requires
an Owner-ratified threshold policy.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.hh_hl_campaign_grid import expand_hh_hl_variants
from tools.arvp_vacation.hh_hl_window_stability import (
    SCHEMA_VERSION as WINDOW_STABILITY_SCHEMA,
    validate_window_stability_artifact,
)

ANALYZER_PROFILE_ID = "hh_hl_analyzer_prep_v1"
CLASSIFIER_CODE_VERSION = "hh_hl_durable_classifier.v1"
CLASSIFICATION_SCHEMA_VERSION = "cdb.hh_hl_analyzer_classification.v1"
THRESHOLD_POLICY_SCHEMA_VERSION = "cdb.hh_hl_classifier_threshold_policy.v1"

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

FORBIDDEN_STATEMENTS = (
    "promoted",
    "paper ready",
    "live ready",
    "pnl_only_ranking",
    "production ready",
    "4153_21_19_matrix",
)

REASON_BLOCKED_REPRODUCTION = "ANALYZER_BLOCKED_REPRODUCTION_NOT_PASS"
REASON_BLOCKED_COMPLETENESS = "ANALYZER_BLOCKED_FIXTURE_INCOMPLETE"
REASON_INCONCLUSIVE_STABILITY_ABSENT = "ANALYZER_INCONCLUSIVE_WINDOW_STABILITY_ABSENT"
REASON_INCONCLUSIVE_THRESHOLD_POLICY_ABSENT = (
    "ANALYZER_INCONCLUSIVE_THRESHOLD_POLICY_ABSENT"
)
REASON_INCONCLUSIVE_POLICY_NOT_RATIFIED = (
    "ANALYZER_INCONCLUSIVE_THRESHOLD_POLICY_NOT_RATIFIED"
)
REASON_INCONCLUSIVE_INSUFFICIENT_SIGNAL = "ANALYZER_INCONCLUSIVE_INSUFFICIENT_SIGNAL"
REASON_REJECTED_UNIFORM_NEGATIVE_SIGN = "ANALYZER_REJECTED_UNIFORM_NEGATIVE_SIGN"

UNIFORM_NEGATIVE_SIGN_REJECT_RULE_ID = "uniform_negative_sign_reject_v1"


class HhHlAnalyzerProfileError(ValueError):
    """Fail-closed analyzer profile violation."""


class HhHlClassifierError(ValueError):
    """Fail-closed durable classifier violation."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


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
            "reason_code": REASON_BLOCKED_COMPLETENESS,
            "missing_run_keys": missing,
            "foreign_run_keys": sorted(foreign),
            "reproduction_pass": reproduction_pass,
        }
    return {
        "classification": "INCONCLUSIVE",
        "reason_code": "ANALYZER_FIXTURE_COMPLETE_NO_ECONOMICS",
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


def fingerprint_threshold_policy(policy: Mapping[str, Any]) -> str:
    body = {k: v for k, v in policy.items() if k != "policy_fingerprint"}
    return canonical_hash(body)


def build_threshold_policy(
    *,
    policy_id: str,
    policy_status: str,
    issue: int,
    rejected_rules: Sequence[Mapping[str, Any]],
    promising_rules: Sequence[Mapping[str, Any]] = (),
    owner_ratified_at_utc: str | None = None,
    owner_github_login: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    if policy_status not in {"DRAFT", "OWNER_RATIFIED"}:
        raise HhHlClassifierError("CLASSIFIER_POLICY_STATUS_INVALID", policy_status)
    if policy_status == "OWNER_RATIFIED":
        if not owner_ratified_at_utc or not owner_github_login:
            raise HhHlClassifierError("CLASSIFIER_POLICY_RATIFICATION_INCOMPLETE")
    body: dict[str, Any] = {
        "schema_version": THRESHOLD_POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "policy_status": policy_status,
        "issue": int(issue),
        "auto_promotion": False,
        "pnl_only_ranking_forbidden": True,
        "promising_means": CLASSIFICATION_MEANING["PROMISING"],
        "rejected_rules": [dict(rule) for rule in rejected_rules],
        "promising_rules": [dict(rule) for rule in promising_rules],
        "owner_ratified_at_utc": owner_ratified_at_utc,
        "owner_github_login": owner_github_login,
    }
    if notes:
        body["notes"] = notes
    return {**body, "policy_fingerprint": fingerprint_threshold_policy(body)}


def build_uniform_negative_sign_reject_policy_draft(
    *, issue: int = 4374
) -> dict[str, Any]:
    """Draft Owner-ratifiable policy: sign-consistency REJECTED only; PROMISING empty."""
    return build_threshold_policy(
        policy_id=UNIFORM_NEGATIVE_SIGN_REJECT_RULE_ID,
        policy_status="DRAFT",
        issue=issue,
        rejected_rules=[
            {
                "rule_id": UNIFORM_NEGATIVE_SIGN_REJECT_RULE_ID,
                "reason_code": REASON_REJECTED_UNIFORM_NEGATIVE_SIGN,
                "requires": {
                    "n_traded_equals_n_total": True,
                    "n_total_gt_zero": True,
                    "negative_share_net_pnl_quote": 1.0,
                    "negative_share_expectancy_r": 1.0,
                    "all_gates_not_ranking_ready": True,
                },
            }
        ],
        promising_rules=[],
        notes=(
            "DRAFT only. Not active until policy_status=OWNER_RATIFIED. "
            "PROMISING rules intentionally empty."
        ),
    )


def _uniform_negative_sign_reject_fires(stability: Mapping[str, Any]) -> bool:
    metrics = stability.get("metrics")
    if not isinstance(metrics, Mapping):
        return False
    n_total = int(metrics.get("n_total") or 0)
    n_traded = int(metrics.get("n_traded") or 0)
    if not (n_total > 0 and n_traded == n_total):
        return False
    sign = metrics.get("sign_shares")
    if not isinstance(sign, Mapping):
        return False
    net = (
        sign.get("net_pnl_quote")
        if isinstance(sign.get("net_pnl_quote"), Mapping)
        else {}
    )
    exp = (
        sign.get("expectancy_r")
        if isinstance(sign.get("expectancy_r"), Mapping)
        else {}
    )
    if net.get("negative_share") != 1.0 or exp.get("negative_share") != 1.0:
        return False
    hist = metrics.get("gate_status_histogram")
    if not isinstance(hist, Mapping) or not hist:
        return False
    return (
        set(hist.keys()) == {"NOT_RANKING_READY"}
        and sum(int(v) for v in hist.values()) == n_total
    )


def _apply_rejected_rules(
    policy: Mapping[str, Any],
    *,
    stability: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    for rule in policy.get("rejected_rules") or []:
        if not isinstance(rule, Mapping):
            continue
        rule_id = str(rule.get("rule_id") or "")
        if rule_id == UNIFORM_NEGATIVE_SIGN_REJECT_RULE_ID:
            if _uniform_negative_sign_reject_fires(stability):
                return rule_id, str(
                    rule.get("reason_code") or REASON_REJECTED_UNIFORM_NEGATIVE_SIGN
                )
    return None, None


def _apply_promising_rules(
    policy: Mapping[str, Any],
    *,
    stability: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    del stability  # no v1 PROMISING rule may fire without explicit Owner criteria
    for rule in policy.get("promising_rules") or []:
        if not isinstance(rule, Mapping):
            continue
        # Intentionally no built-in PROMISING evaluators in v1.
        # Owner-defined future rules must be added as explicit code paths.
        _ = rule
    return None, None


def _finalize_classification(body: dict[str, Any]) -> dict[str, Any]:
    fingerprint_body = {
        k: v for k, v in body.items() if k != "classification_fingerprint"
    }
    return {
        **body,
        "classification_fingerprint": canonical_hash(fingerprint_body),
    }


def classify_hh_hl_campaign(
    *,
    analyzer_profile: Mapping[str, Any],
    reproduction_pass: bool | None,
    window_stability: Mapping[str, Any] | None,
    threshold_policy: Mapping[str, Any] | None = None,
    campaign_summary_fingerprint: str | None = None,
    reproduction_summary_fingerprint: str | None = None,
    expected_run_keys: Sequence[str] | None = None,
    present_run_keys: Sequence[str] | None = None,
    foreign_run_keys: Sequence[str] = (),
) -> dict[str, Any]:
    """Durable classifier: binds stability + optional Owner-ratified policy."""
    assert_not_4153_matrix(analyzer_profile)
    if analyzer_profile.get("analyzer_profile_id") != ANALYZER_PROFILE_ID:
        raise HhHlClassifierError("CLASSIFIER_PROFILE_ID_MISMATCH")

    profile_fp = str(analyzer_profile.get("analyzer_profile_fingerprint") or "")
    if not profile_fp:
        # Recompute if caller passed profile body without fingerprint.
        rebuilt = build_hh_hl_analyzer_profile(
            expected_run_keys=list(
                analyzer_profile.get("expected_run_keys") or expected_run_keys or []
            ),
            reproduction_pass_required=bool(
                analyzer_profile.get("reproduction_pass_required", True)
            ),
        )
        profile_fp = str(rebuilt["analyzer_profile_fingerprint"])

    base = {
        "schema_version": CLASSIFICATION_SCHEMA_VERSION,
        "classifier_code_version": CLASSIFIER_CODE_VERSION,
        "analyzer_profile_id": ANALYZER_PROFILE_ID,
        "analyzer_profile_fingerprint": profile_fp,
        "policy_id": None,
        "policy_version": None,
        "policy_fingerprint": None,
        "policy_status": None,
        "auto_promotion": False,
        "pnl_only_ranking_forbidden": True,
        "promising_means": CLASSIFICATION_MEANING["PROMISING"],
        "forbidden_statements": list(FORBIDDEN_STATEMENTS),
        "window_stability_present": False,
        "input_fingerprints": {
            "campaign_summary_fingerprint": campaign_summary_fingerprint,
            "reproduction_summary_fingerprint": reproduction_summary_fingerprint,
            "window_stability_fingerprint": None,
            "threshold_policy_fingerprint": None,
            "analyzer_profile_fingerprint": profile_fp,
        },
    }

    if expected_run_keys is not None and present_run_keys is not None:
        completeness = classify_fixture_completeness(
            expected_run_keys=expected_run_keys,
            present_run_keys=present_run_keys,
            reproduction_pass=reproduction_pass,
            foreign_run_keys=foreign_run_keys,
        )
        if completeness["classification"] == "BLOCKED":
            return _finalize_classification(
                {
                    **base,
                    "classification": "BLOCKED",
                    "reason_code": REASON_BLOCKED_COMPLETENESS,
                    "fired_rules": ["fixture_completeness"],
                    "reproduction_pass": bool(reproduction_pass),
                    "note": "Fixture incomplete or reproduction not PASS.",
                }
            )

    if reproduction_pass is not True:
        return _finalize_classification(
            {
                **base,
                "classification": "BLOCKED",
                "reason_code": REASON_BLOCKED_REPRODUCTION,
                "fired_rules": ["reproduction_pass_required"],
                "reproduction_pass": False,
                "note": "Reproduction PASS required before economic classification.",
            }
        )

    if window_stability is None:
        return _finalize_classification(
            {
                **base,
                "classification": "INCONCLUSIVE",
                "reason_code": REASON_INCONCLUSIVE_STABILITY_ABSENT,
                "fired_rules": ["window_stability_absent_cap"],
                "reproduction_pass": True,
                "window_stability_present": False,
                "note": (
                    "Reproduction PASS proven; required window_stability absent "
                    "— max INCONCLUSIVE under hh_hl_analyzer_prep_v1."
                ),
            }
        )

    try:
        validated_stability = validate_window_stability_artifact(window_stability)
    except Exception as exc:  # noqa: BLE001 — map to inconclusive absent/invalid
        return _finalize_classification(
            {
                **base,
                "classification": "INCONCLUSIVE",
                "reason_code": REASON_INCONCLUSIVE_STABILITY_ABSENT,
                "fired_rules": ["window_stability_invalid"],
                "reproduction_pass": True,
                "window_stability_present": False,
                "note": f"window_stability invalid: {exc}",
            }
        )

    if validated_stability.get("schema_version") != WINDOW_STABILITY_SCHEMA:
        return _finalize_classification(
            {
                **base,
                "classification": "INCONCLUSIVE",
                "reason_code": REASON_INCONCLUSIVE_STABILITY_ABSENT,
                "fired_rules": ["window_stability_schema_mismatch"],
                "reproduction_pass": True,
                "window_stability_present": False,
                "note": "window_stability schema mismatch.",
            }
        )

    stability_fp = str(validated_stability["evidence_fingerprint"])
    base["window_stability_present"] = True
    base["input_fingerprints"]["window_stability_fingerprint"] = stability_fp

    if threshold_policy is None:
        return _finalize_classification(
            {
                **base,
                "classification": "INCONCLUSIVE",
                "reason_code": REASON_INCONCLUSIVE_THRESHOLD_POLICY_ABSENT,
                "fired_rules": ["threshold_policy_absent"],
                "reproduction_pass": True,
                "note": (
                    "window_stability present; threshold policy absent — "
                    "descriptive evidence only, no PROMISING/REJECTED."
                ),
            }
        )

    policy = dict(threshold_policy)
    if policy.get("schema_version") != THRESHOLD_POLICY_SCHEMA_VERSION:
        raise HhHlClassifierError("CLASSIFIER_POLICY_SCHEMA_MISMATCH")
    policy_fp = fingerprint_threshold_policy(policy)
    if str(policy.get("policy_fingerprint") or "") != policy_fp:
        raise HhHlClassifierError("CLASSIFIER_POLICY_FINGERPRINT_MISMATCH")

    base["policy_id"] = str(policy.get("policy_id"))
    base["policy_version"] = str(policy.get("policy_id"))
    base["policy_fingerprint"] = policy_fp
    base["policy_status"] = str(policy.get("policy_status"))
    base["input_fingerprints"]["threshold_policy_fingerprint"] = policy_fp

    if policy.get("policy_status") != "OWNER_RATIFIED":
        return _finalize_classification(
            {
                **base,
                "classification": "INCONCLUSIVE",
                "reason_code": REASON_INCONCLUSIVE_POLICY_NOT_RATIFIED,
                "fired_rules": ["threshold_policy_not_ratified"],
                "reproduction_pass": True,
                "note": "Threshold policy present but not OWNER_RATIFIED.",
            }
        )

    if policy.get("auto_promotion") is not False:
        raise HhHlClassifierError("CLASSIFIER_AUTO_PROMOTION_FORBIDDEN")
    if policy.get("pnl_only_ranking_forbidden") is not True:
        raise HhHlClassifierError("CLASSIFIER_PNL_ONLY_RANKING_FORBIDDEN")

    fired: list[str] = []
    rejected_rule, rejected_reason = _apply_rejected_rules(
        policy, stability=validated_stability
    )
    if rejected_rule:
        fired.append(rejected_rule)
        return _finalize_classification(
            {
                **base,
                "classification": "REJECTED",
                "reason_code": rejected_reason or REASON_REJECTED_UNIFORM_NEGATIVE_SIGN,
                "fired_rules": fired,
                "reproduction_pass": True,
                "note": "Owner-ratified REJECTED rule fired on descriptive stability.",
            }
        )

    promising_rule, promising_reason = _apply_promising_rules(
        policy, stability=validated_stability
    )
    if promising_rule:
        fired.append(promising_rule)
        return _finalize_classification(
            {
                **base,
                "classification": "PROMISING",
                "reason_code": promising_reason
                or "ANALYZER_PROMISING_RESEARCH_FOLLOWUP",
                "fired_rules": fired,
                "reproduction_pass": True,
                "note": "PROMISING means research follow-up only; no promotion.",
            }
        )

    return _finalize_classification(
        {
            **base,
            "classification": "INCONCLUSIVE",
            "reason_code": REASON_INCONCLUSIVE_INSUFFICIENT_SIGNAL,
            "fired_rules": ["insufficient_signal"],
            "reproduction_pass": True,
            "note": "Stability and ratified policy present; no REJECTED/PROMISING rule fired.",
        }
    )
