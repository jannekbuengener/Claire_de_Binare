"""Deterministic read-only Research Validation Pilot Spec invariants (#4272).

Companion to ``cdb.research_validation_pilot.v1``. No network, no DB, no pilot
execution, no provider fetches, no writes. Relational fail-closed rules that
JSON Schema cannot express alone.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

REQUIRED_CANDIDATE_KEYS: tuple[str, ...] = (
    "breakout",
    "liquidity_or_volume_filter",
    "on_chain_regime_filter",
)

REQUIRED_SOURCE_PAIRS: dict[str, frozenset[str]] = {
    "breakout": frozenset({"binance", "coinmarketcap"}),
    "liquidity_or_volume_filter": frozenset({"binance", "coinmarketcap"}),
    "on_chain_regime_filter": frozenset({"token_terminal", "bigdata_com"}),
}

REQUIRED_ARTIFACT_TYPES: frozenset[str] = frozenset(
    {
        "research_brief",
        "strategy_candidate",
        "validation_manifest",
        "research_security_gate",
        "hermes_orchestration_run",
        "candidate_evidence",
        "decision_record",
    }
)

ALLOWED_PRE_EXEC_STATUS: frozenset[str] = frozenset(
    {"PLANNED", "NOT_RUN", "PENDING_BINDING"}
)

FORBIDDEN_EXECUTED_CLAIM_STATUS: frozenset[str] = frozenset(
    {
        "PASS",
        "FAIL",
        "REJECT",
        "REVISE",
        "PARK",
        "PAPER_CANDIDATE",
        "EXECUTED",
        "COMPLETED",
    }
)

AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "research_apps_validation_authority",
    "hermes_live_authority",
    "hermes_validation_authority",
    "tickersage_validation_authority",
    "tickersage_decision_authority",
    "automatic_strategy_promotion",
    "paper_candidate_is_live_go",
    "paper_go",
    "live_go",
    "real_money_go",
    "capital_go",
    "risk_bypass",
    "productive_db_writes",
    "productive_agent_execution",
    "ml_rl_integration",
    "pilot_execution_claims_results",
)

ECONOMICS_REQUIRED: tuple[str, ...] = (
    "fees",
    "spread",
    "slippage",
    "fill_assumptions",
    "reject_assumptions",
    "latency_or_delay",
)


class PilotSpecContractError(ValueError):
    """Raised when Pilot Spec cross-contract invariants fail."""


def _as_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PilotSpecContractError(f"{label} must be an object")
    return value


def _as_sequence(value: Any, *, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise PilotSpecContractError(f"{label} must be an array")
    return value


def pilot_spec_grants_validation_authority(
    _pilot: Mapping[str, Any] | None = None,
) -> bool:
    """Pilot specification never grants validation authority."""
    return False


def pilot_spec_grants_live_authority(
    _pilot: Mapping[str, Any] | None = None,
) -> bool:
    """Pilot specification never grants live/capital authority."""
    return False


def validate_candidate_set(pilot: Mapping[str, Any]) -> list[str]:
    """Require exactly the three distinct candidate keys from #4272."""
    errors: list[str] = []
    specs = _as_sequence(pilot.get("candidate_specs"), label="candidate_specs")
    if len(specs) != 3:
        errors.append(f"candidate_specs must contain exactly 3 items, got {len(specs)}")
    keys: list[str] = []
    for idx, raw in enumerate(specs):
        spec = _as_mapping(raw, label=f"candidate_specs[{idx}]")
        key = spec.get("candidate_key")
        if not isinstance(key, str):
            errors.append(f"candidate_specs[{idx}].candidate_key required")
            continue
        keys.append(key)
    if len(keys) != len(set(keys)):
        errors.append("duplicate candidate_key is forbidden")
    missing = [key for key in REQUIRED_CANDIDATE_KEYS if key not in keys]
    extra = [key for key in keys if key not in REQUIRED_CANDIDATE_KEYS]
    if missing:
        errors.append(f"missing required candidate_key(s): {sorted(missing)}")
    if extra:
        errors.append(f"unknown candidate_key(s): {sorted(extra)}")
    return errors


def validate_source_pairs(pilot: Mapping[str, Any]) -> list[str]:
    """Reject wrong or incomplete source pairs per candidate."""
    errors: list[str] = []
    specs = _as_sequence(pilot.get("candidate_specs"), label="candidate_specs")
    for idx, raw in enumerate(specs):
        spec = _as_mapping(raw, label=f"candidate_specs[{idx}]")
        key = spec.get("candidate_key")
        if key not in REQUIRED_SOURCE_PAIRS:
            continue
        sources = spec.get("required_sources")
        if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
            errors.append(f"{key}: required_sources must be an array")
            continue
        actual = frozenset(str(item) for item in sources)
        expected = REQUIRED_SOURCE_PAIRS[key]
        if actual != expected:
            errors.append(
                f"{key}: required_sources must be {sorted(expected)}, got {sorted(actual)}"
            )
        bindings = spec.get("source_bindings")
        if isinstance(bindings, Sequence) and not isinstance(bindings, (str, bytes)):
            bound = {
                str(item.get("source_type"))
                for item in bindings
                if isinstance(item, Mapping)
            }
            if not expected.issubset(bound):
                errors.append(f"{key}: source_bindings must cover {sorted(expected)}")
    return errors


def validate_shared_contract_and_gates(pilot: Mapping[str, Any]) -> list[str]:
    """All candidates must share one contract set and gate path."""
    errors: list[str] = []
    gates = _as_mapping(pilot.get("common_gate_bindings"), label="common_gate_bindings")
    if gates.get("same_contract_versions_for_all_candidates") is not True:
        errors.append("same_contract_versions_for_all_candidates must be true")
    if gates.get("same_validation_profile_for_all_candidates") is not True:
        errors.append("same_validation_profile_for_all_candidates must be true")
    if gates.get("same_security_and_integrity_gates") is not True:
        errors.append("same_security_and_integrity_gates must be true")
    if gates.get("source_specific_gate_bypass_allowed") is not False:
        errors.append("source-specific gate bypass is forbidden")
    if gates.get("source_adapters_have_no_validation_authority") is not True:
        errors.append("source adapters must have no validation authority")
    if gates.get("hermes_has_no_validation_authority") is not True:
        errors.append("hermes must have no validation authority")
    if pilot.get("validation_profile") != "validation-research-v1":
        errors.append("validation_profile must be validation-research-v1")
    contract_set = _as_mapping(pilot.get("contract_set"), label="contract_set")
    required = (
        "research_brief",
        "source_evidence",
        "strategy_candidate",
        "validation_manifest",
        "research_security_gate",
        "hermes_orchestration_run",
        "candidate_evidence",
        "decision_record",
        "execution_economics_gross_to_net",
    )
    for field in required:
        if field not in contract_set:
            errors.append(f"contract_set.{field} required")
    return errors


def validate_expected_artifacts(pilot: Mapping[str, Any]) -> list[str]:
    """Every candidate must reference the required planned/not-run artifacts."""
    errors: list[str] = []
    specs = _as_sequence(pilot.get("candidate_specs"), label="candidate_specs")
    top_level = _as_sequence(
        pilot.get("expected_artifacts"), label="expected_artifacts"
    )
    for idx, raw in enumerate(specs):
        spec = _as_mapping(raw, label=f"candidate_specs[{idx}]")
        key = spec.get("candidate_key")
        refs = spec.get("expected_artifact_refs")
        if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
            errors.append(f"{key}: expected_artifact_refs must be an array")
            continue
        types = {
            str(item.get("artifact_type")) for item in refs if isinstance(item, Mapping)
        }
        missing = sorted(REQUIRED_ARTIFACT_TYPES - types)
        if missing:
            errors.append(f"{key}: missing expected artifact types {missing}")
        for jdx, item in enumerate(refs):
            if not isinstance(item, Mapping):
                errors.append(f"{key}: expected_artifact_refs[{jdx}] must be object")
                continue
            status = item.get("status")
            if status in FORBIDDEN_EXECUTED_CLAIM_STATUS:
                errors.append(
                    f"{key}: expected_artifact_refs[{jdx}] status {status} claims execution"
                )
            if status not in ALLOWED_PRE_EXEC_STATUS:
                errors.append(
                    f"{key}: expected_artifact_refs[{jdx}] status must be PLANNED/NOT_RUN/PENDING_BINDING"
                )
            if item.get("candidate_key") != key:
                errors.append(
                    f"{key}: expected_artifact_refs[{jdx}].candidate_key mismatch"
                )
    # Top-level expected artifacts must also stay pre-execution.
    for idx, item in enumerate(top_level):
        if not isinstance(item, Mapping):
            errors.append(f"expected_artifacts[{idx}] must be object")
            continue
        status = item.get("status")
        if status in FORBIDDEN_EXECUTED_CLAIM_STATUS:
            errors.append(f"expected_artifacts[{idx}] status {status} claims execution")
        if status not in ALLOWED_PRE_EXEC_STATUS:
            errors.append(
                f"expected_artifacts[{idx}] status must be PLANNED/NOT_RUN/PENDING_BINDING"
            )
    return errors


def validate_no_executed_claims(pilot: Mapping[str, Any]) -> list[str]:
    """SPECIFICATION_ONLY must not claim executed evidence or decision verdicts."""
    errors: list[str] = []
    if pilot.get("execution_status") != "SPECIFICATION_ONLY":
        errors.append("execution_status must be SPECIFICATION_ONLY")
    if pilot.get("spec_status") != "PLANNED":
        errors.append("spec_status must be PLANNED for specification-only pilots")
    safety = _as_mapping(pilot.get("safety_boundaries"), label="safety_boundaries")
    if safety.get("pilot_execution") is not False:
        errors.append("safety_boundaries.pilot_execution must be false")
    summary = _as_mapping(
        pilot.get("comparative_summary_spec"), label="comparative_summary_spec"
    )
    cell = summary.get("pre_execution_cell_status")
    if cell not in {"PLANNED", "NOT_RUN"}:
        errors.append(
            "comparative_summary_spec.pre_execution_cell_status must be PLANNED or NOT_RUN"
        )
    if summary.get("status") in FORBIDDEN_EXECUTED_CLAIM_STATUS:
        errors.append("comparative_summary_spec.status must not claim execution")
    # Reject invented decision verdict fields if a caller injects them.
    for forbidden_key in (
        "decision_verdict",
        "final_verdict",
        "executed_verdict",
        "paper_candidate_verdict",
    ):
        if forbidden_key in pilot:
            errors.append(f"{forbidden_key} is forbidden on specification-only pilot")
    return errors


def validate_economics_and_scenarios(pilot: Mapping[str, Any]) -> list[str]:
    """Fees/spread/slippage and pessimistic delay must be complete."""
    errors: list[str] = []
    policy = _as_mapping(
        pilot.get("execution_economics_policy"), label="execution_economics_policy"
    )
    components = policy.get("required_components")
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        errors.append("execution_economics_policy.required_components must be array")
    else:
        present = {str(item) for item in components}
        for field in ("fees", "spread", "slippage", "latency_or_delay"):
            if field not in present:
                errors.append(
                    f"execution_economics_policy.required_components missing {field}"
                )
    if policy.get("reuse_ssot") != "execution_economics_gross_to_net.v1":
        errors.append("execution economics SSOT must be reused")
    if policy.get("no_invented_results") is not True:
        errors.append("no_invented_results must be true")

    specs = _as_sequence(pilot.get("candidate_specs"), label="candidate_specs")
    for idx, raw in enumerate(specs):
        spec = _as_mapping(raw, label=f"candidate_specs[{idx}]")
        key = spec.get("candidate_key")
        economics = spec.get("economics_components")
        if not isinstance(economics, Mapping):
            errors.append(f"{key}: economics_components required")
            continue
        for field in ECONOMICS_REQUIRED:
            value = economics.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{key}: economics_components.{field} required")

    scenarios = _as_sequence(pilot.get("scenario_specs"), label="scenario_specs")
    keys = {
        str(item.get("scenario_key")) for item in scenarios if isinstance(item, Mapping)
    }
    if "baseline" not in keys:
        errors.append("scenario_specs must include baseline")
    if "pessimistic_liquidity_and_delay" not in keys:
        errors.append("scenario_specs must include pessimistic_liquidity_and_delay")
    for idx, raw in enumerate(scenarios):
        scenario = _as_mapping(raw, label=f"scenario_specs[{idx}]")
        if scenario.get("scenario_key") != "pessimistic_liquidity_and_delay":
            continue
        if scenario.get("additional_execution_delay_required") is not True:
            errors.append("pessimistic scenario requires additional_execution_delay")
        if scenario.get("higher_spread_required") is not True:
            errors.append("pessimistic scenario requires higher_spread")
        if scenario.get("higher_slippage_required") is not True:
            errors.append("pessimistic scenario requires higher_slippage")
        if scenario.get("stricter_fill_or_liquidity_required") is not True:
            errors.append("pessimistic scenario requires stricter fill/liquidity")
        if scenario.get("positive_price_improvement_allowed") is not False:
            errors.append("pessimistic scenario forbids positive price improvement")
        if scenario.get("adverse_relative_to_baseline") is not True:
            errors.append("pessimistic scenario must be adverse_relative_to_baseline")
    return errors


def validate_time_and_provenance(pilot: Mapping[str, Any]) -> list[str]:
    """Time causality, as-of bounds, and fail-closed source rules."""
    errors: list[str] = []
    policy = _as_mapping(
        pilot.get("data_and_time_policy"), label="data_and_time_policy"
    )
    if policy.get("timezone") != "UTC":
        errors.append("data_and_time_policy.timezone must be UTC")
    if policy.get("forbid_as_of_after_decision_time") is not True:
        errors.append("as_of after decision_time must be forbidden")
    if policy.get("partial_or_missing_source_cannot_be_source_pass") is not True:
        errors.append("partial/missing source data cannot be Source-PASS")
    if policy.get("token_terminal_nonempty_errors_must_be_classified") is not True:
        errors.append("Token Terminal nonempty errors must be classified")
    if policy.get("bigdata_cannot_replace_numeric_validation_evidence") is not True:
        errors.append("Bigdata cannot replace numeric validation evidence")
    if policy.get("bigdata_outputs_are_untrusted_input") is not True:
        errors.append("Bigdata outputs must remain UNTRUSTED_INPUT")

    specs = _as_sequence(pilot.get("candidate_specs"), label="candidate_specs")
    for idx, raw in enumerate(specs):
        spec = _as_mapping(raw, label=f"candidate_specs[{idx}]")
        key = spec.get("candidate_key")
        causality = spec.get("time_causality")
        if not isinstance(causality, Mapping):
            errors.append(f"{key}: time_causality required")
            continue
        for field in (
            "research_cutoff",
            "data_cutoff",
            "decision_time",
            "earliest_execution_time",
            "signal_bar_time",
        ):
            value = causality.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{key}: time_causality.{field} required")
        if spec.get("as_of_rule") != (
            "No source or market datum with as_of after decision_time may be used."
        ):
            errors.append(f"{key}: as_of_rule missing or altered")
        dataset = spec.get("dataset_binding_policy")
        if not isinstance(dataset, Mapping):
            errors.append(f"{key}: dataset_binding_policy required")
        else:
            if dataset.get("status") != "PENDING_BINDING":
                errors.append(
                    f"{key}: dataset_binding_policy.status must be PENDING_BINDING"
                )
            if dataset.get("snapshot_hash") is not None:
                errors.append(
                    f"{key}: snapshot_hash must be null before real fetch (no invented hash)"
                )
        if key == "on_chain_regime_filter":
            policy_text = spec.get("token_terminal_partial_success_policy")
            if not isinstance(policy_text, str) or "errors" not in policy_text.lower():
                errors.append(
                    "on_chain_regime_filter must classify Token Terminal partial-success errors"
                )
            bindings = spec.get("source_bindings")
            if isinstance(bindings, Sequence):
                for jdx, binding in enumerate(bindings):
                    if not isinstance(binding, Mapping):
                        continue
                    if binding.get("source_type") == "bigdata_com":
                        if binding.get("content_classification") != "UNTRUSTED_INPUT":
                            errors.append(
                                "bigdata_com content_classification must be UNTRUSTED_INPUT"
                            )
                        surface = str(binding.get("surface", "")).lower()
                        if "search" not in surface:
                            errors.append(
                                "bigdata_com pilot surface must be REST Search (not invented SDK)"
                            )
    return errors


def validate_tickersage_and_authority(pilot: Mapping[str, Any]) -> list[str]:
    """TickerSage and all authority flags remain non-authoritative."""
    errors: list[str] = []
    viz = _as_mapping(pilot.get("visualization_policy"), label="visualization_policy")
    if viz.get("tickersage_role") != "visualization_only":
        errors.append("tickersage_role must be visualization_only")
    if viz.get("validation_authority") is not False:
        errors.append("TickerSage validation_authority must be false")
    if viz.get("decision_authority") is not False:
        errors.append("TickerSage decision_authority must be false")
    if viz.get("may_mutate_metrics") is not False:
        errors.append("TickerSage may_mutate_metrics must be false")
    if viz.get("may_write_lifecycle_transitions") is not False:
        errors.append("TickerSage may_write_lifecycle_transitions must be false")
    if viz.get("official_api_contract_present") is not False:
        errors.append("TickerSage official_api_contract_present must be false")

    authority = _as_mapping(
        pilot.get("authority_boundaries"), label="authority_boundaries"
    )
    for field in AUTHORITY_FALSE_FIELDS:
        if authority.get(field) is not False:
            errors.append(f"authority_boundaries.{field} must be false")
    return errors


def validate_research_validation_pilot(pilot: Mapping[str, Any]) -> list[str]:
    """Aggregate all Pilot Spec cross-contract invariants."""
    if not isinstance(pilot, Mapping):
        return ["pilot must be an object"]
    errors: list[str] = []
    errors.extend(validate_candidate_set(pilot))
    errors.extend(validate_source_pairs(pilot))
    errors.extend(validate_shared_contract_and_gates(pilot))
    errors.extend(validate_expected_artifacts(pilot))
    errors.extend(validate_no_executed_claims(pilot))
    errors.extend(validate_economics_and_scenarios(pilot))
    errors.extend(validate_time_and_provenance(pilot))
    errors.extend(validate_tickersage_and_authority(pilot))
    return errors
