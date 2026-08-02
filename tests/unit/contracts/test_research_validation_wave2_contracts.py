"""
Wave-2 Research Validation contracts (#4267/#4268/#4269).

test_id: tc_research_validation_wave2_001
test_name: research_validation_wave2_contract_surfaces
test_type: Wissens-Test / Schutz-Test
cdb_area: contracts
rule_ref: source-evidence-non-authority; compiler-no-invention; registry-immutable; pmr-01..04
decision_ref: research-validation-wave2
issue_ref: #4267 #4268 #4269 #4283
pr_ref: pending
evidence_ref: docs/contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from tools.research_validation.wave2_cross_contract import (
    SAFE_ALLOWED_NEXT_ACTIONS,
    canonical_content_hash,
    validate_candidate_lineage,
    validate_brief_provenance,
    validate_compiler_input_completeness,
    validate_decision_allowed_actions,
    validate_paper_candidate_transition,
    validate_registry_entry_status_bindings,
    validate_source_evidence_non_authority,
    validate_source_evidence_refs_sorted,
    validate_transition_status_bindings,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = PROJECT_ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"

SOURCE_TYPES = (
    "binance",
    "coinmarketcap",
    "token_terminal",
    "bigdata_com",
    "gainium",
    "hugging_face",
)

WAVE2_SCHEMA_EXAMPLES = (
    (
        "cdb.source_evidence.v1",
        "cdb_source_evidence.v1.schema.json",
        "cdb_source_evidence_binance_valid.json",
    ),
    (
        "cdb.compiler_report.v1",
        "cdb_compiler_report.v1.schema.json",
        "cdb_compiler_report_valid.json",
    ),
    (
        "cdb.candidate_registry_entry.v1",
        "cdb_candidate_registry_entry.v1.schema.json",
        "cdb_candidate_registry_entry_valid.json",
    ),
    (
        "cdb.candidate_transition.v1",
        "cdb_candidate_transition.v1.schema.json",
        "cdb_candidate_transition_paper_valid.json",
    ),
    (
        "cdb.candidate_evidence.v1",
        "cdb_candidate_evidence.v1.schema.json",
        "cdb_candidate_evidence_pass_valid.json",
    ),
    (
        "cdb.decision_record.v1",
        "cdb_decision_record.v1.schema.json",
        "cdb_decision_record_paper_valid.json",
    ),
)


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _errors(schema_name: str, payload: dict) -> list:
    schema = _load(CONTRACTS / schema_name)
    return list(Draft7Validator(schema).iter_errors(payload))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("schema_version", "schema_name", "example_name"),
    WAVE2_SCHEMA_EXAMPLES,
)
def test_wave2_schema_and_example_validate(
    schema_version: str, schema_name: str, example_name: str
) -> None:
    schema = _load(CONTRACTS / schema_name)
    example = _load(EXAMPLES / example_name)
    Draft7Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert example["schema_version"] == schema_version
    assert _errors(schema_name, example) == []


@pytest.mark.unit
@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_all_six_sources_produce_valid_source_evidence(source_type: str) -> None:
    payload = _load(EXAMPLES / f"cdb_source_evidence_{source_type}_valid.json")
    assert payload["source_type"] == source_type
    assert _errors("cdb_source_evidence.v1.schema.json", payload) == []
    assert validate_source_evidence_non_authority(payload) == []


@pytest.mark.unit
def test_source_evidence_rejects_pass_fail_claim_type() -> None:
    payload = _load(EXAMPLES / "cdb_source_evidence_binance_valid.json")
    payload["claim_type"] = "PASS"
    assert _errors("cdb_source_evidence.v1.schema.json", payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    (
        "validation_authority",
        "decision_authority",
        "contains_secrets",
        "contains_account_data",
    ),
)
def test_source_evidence_rejects_authority_or_secret_flags(field: str) -> None:
    payload = _load(EXAMPLES / "cdb_source_evidence_binance_valid.json")
    payload[field] = True
    assert _errors("cdb_source_evidence.v1.schema.json", payload)
    assert validate_source_evidence_non_authority(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_key",
    ("retrieved_at", "claim", "uncertainty", "provenance", "content_hash"),
)
def test_source_evidence_rejects_missing_required_fields(missing_key: str) -> None:
    payload = _load(EXAMPLES / "cdb_source_evidence_binance_valid.json")
    del payload[missing_key]
    assert _errors("cdb_source_evidence.v1.schema.json", payload)


@pytest.mark.unit
def test_conflict_state_cannot_be_omitted_as_safe_claim() -> None:
    payload = _load(EXAMPLES / "cdb_source_evidence_bigdata_com_valid.json")
    payload["conflict_state"] = "UNRESOLVED"
    payload["claim"] = "Resolved consensus that strategy is safe to promote"
    assert _errors("cdb_source_evidence.v1.schema.json", payload) == []
    # Conflict remains marked; docs forbid inventing resolution — claim_type stays NARRATIVE.
    assert payload["conflict_state"] == "UNRESOLVED"
    assert payload["trust_classification"] == "UNTRUSTED_INPUT"


@pytest.mark.unit
def test_compiler_full_input_ready_status() -> None:
    report = _load(EXAMPLES / "cdb_compiler_report_valid.json")
    assert report["status"] == "READY"
    assert _errors("cdb_compiler_report.v1.schema.json", report) == []
    brief = _load(EXAMPLES / "cdb_research_brief_valid.json")
    sources = [
        _load(EXAMPLES / "cdb_source_evidence_binance_valid.json"),
        _load(EXAMPLES / "cdb_source_evidence_coinmarketcap_valid.json"),
    ]
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    status, reasons = validate_compiler_input_completeness(
        research_brief=brief,
        source_evidence_refs=sources,
        candidate_draft=candidate,
    )
    assert status == "READY"
    assert reasons == []


@pytest.mark.unit
def test_identical_canonical_input_same_hash() -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    h1 = canonical_content_hash(candidate)
    h2 = canonical_content_hash(deepcopy(candidate))
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


@pytest.mark.unit
def test_changed_falsifiable_content_requires_new_version_with_parent() -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    mutated = deepcopy(candidate)
    mutated["candidate_version"] = "v2"
    mutated["parent_version"] = "v1"
    mutated["parameters"] = {**candidate["parameters"], "breakout_buffer": 0.001}
    assert _errors("cdb_strategy_candidate.v1.schema.json", mutated) == []
    assert validate_candidate_lineage(mutated) == []
    assert canonical_content_hash(mutated) != canonical_content_hash(candidate)


@pytest.mark.unit
def test_compiler_rejects_invented_missing_rules() -> None:
    brief = _load(EXAMPLES / "cdb_research_brief_valid.json")
    sources = [_load(EXAMPLES / "cdb_source_evidence_binance_valid.json")]
    draft = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    draft["entry_rules"] = []
    draft["exit_rules"] = []
    status, reasons = validate_compiler_input_completeness(
        research_brief=brief,
        source_evidence_refs=sources,
        candidate_draft=draft,
    )
    assert status == "NEEDS_RESEARCH"
    assert any("entry_rules" in r for r in reasons)
    assert any("exit_rules" in r for r in reasons)


@pytest.mark.unit
def test_non_falsifiable_candidate_not_ready() -> None:
    brief = _load(EXAMPLES / "cdb_research_brief_valid.json")
    sources = [_load(EXAMPLES / "cdb_source_evidence_binance_valid.json")]
    draft = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    draft["falsifiable_hypothesis"] = "   "
    status, reasons = validate_compiler_input_completeness(
        research_brief=brief,
        source_evidence_refs=sources,
        candidate_draft=draft,
    )
    assert status == "BLOCKED"
    assert any("non-falsifiable" in r for r in reasons)


@pytest.mark.unit
def test_missing_research_brief_version_or_hash_rejected() -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    broken = deepcopy(candidate)
    del broken["provenance"]["research_brief_version"]
    assert _errors("cdb_strategy_candidate.v1.schema.json", broken)
    broken2 = deepcopy(candidate)
    del broken2["provenance"]["research_brief_content_hash"]
    assert _errors("cdb_strategy_candidate.v1.schema.json", broken2)
    assert validate_brief_provenance(broken)
    assert validate_brief_provenance(broken2)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("version", "parent", "expect_error_substr"),
    (
        ("v2", None, "requires parent_version"),
        ("v2", "v2", "must not equal"),
        ("v2", "v3", "future"),
        ("v3", "v1", "exact previous"),
    ),
)
def test_candidate_lineage_rejects_invalid_parents(
    version: str, parent: str | None, expect_error_substr: str
) -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    candidate["candidate_version"] = version
    candidate["parent_version"] = parent
    # Schema may still accept pattern-valid parents; lineage validator must reject.
    errors = validate_candidate_lineage(candidate)
    assert errors
    assert any(expect_error_substr in err for err in errors)


@pytest.mark.unit
def test_candidate_version_not_silently_overwritten_contract() -> None:
    """Immutability: content change must mint new version, not mutate in place."""
    v1 = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    pretend_overwrite = deepcopy(v1)
    pretend_overwrite["parameters"] = {**v1["parameters"], "breakout_buffer": 0.009}
    # Same version + different falsifiable content is a lineage/process failure.
    assert pretend_overwrite["candidate_version"] == v1["candidate_version"]
    assert canonical_content_hash(pretend_overwrite) != canonical_content_hash(v1)
    fixed = deepcopy(pretend_overwrite)
    fixed["candidate_version"] = "v2"
    fixed["parent_version"] = "v1"
    assert validate_candidate_lineage(fixed) == []


@pytest.mark.unit
def test_registry_identities_not_mixed() -> None:
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    assert isinstance(entry["issue_id"], int)
    assert entry["candidate_id"].startswith("sc-")
    assert entry["run_id"].startswith("run-")
    assert entry["candidate_id"] != entry["run_id"]
    assert transition["identity_separation"]["issue_id_is_not_candidate_id"] is True
    assert transition["identity_separation"]["candidate_id_is_not_run_id"] is True
    broken = deepcopy(transition)
    broken["identity_separation"]["candidate_id_is_not_run_id"] = False
    assert _errors("cdb_candidate_transition.v1.schema.json", broken)


@pytest.mark.unit
def test_status_change_without_decision_record_rejected() -> None:
    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    del transition["decision_id"]
    assert _errors("cdb_candidate_transition.v1.schema.json", transition)


@pytest.mark.unit
def test_valid_registry_transition_auditable() -> None:
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", entry) == []
    assert _errors("cdb_candidate_transition.v1.schema.json", transition) == []
    assert transition["decision_id"]
    assert transition["decision_record_hash"].startswith("sha256:")


@pytest.mark.unit
def test_paper_candidate_with_pass_evidence_accepted() -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    evidence = _load(EXAMPLES / "cdb_candidate_evidence_pass_valid.json")
    decision = _load(EXAMPLES / "cdb_decision_record_paper_valid.json")
    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    assert evidence["overall_verdict"] == "PASS"
    assert _errors("cdb_candidate_evidence.v1.schema.json", evidence) == []
    assert _errors("cdb_decision_record.v1.schema.json", decision) == []
    errors = validate_paper_candidate_transition(
        candidate=candidate,
        evidence=evidence,
        decision=decision,
        transition=transition,
    )
    assert errors == []


@pytest.mark.unit
def test_paper_candidate_without_evidence_rejected() -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    decision = _load(EXAMPLES / "cdb_decision_record_paper_valid.json")
    errors = validate_paper_candidate_transition(
        candidate=candidate,
        evidence=None,
        decision=decision,
    )
    assert errors
    assert any("requires CandidateEvidence" in e for e in errors)


@pytest.mark.unit
@pytest.mark.parametrize("bad_verdict", ["FAIL", "BLOCKED", "INSUFFICIENT_DATA"])
def test_paper_candidate_rejects_non_pass_evidence(bad_verdict: str) -> None:
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    evidence = _load(EXAMPLES / "cdb_candidate_evidence_valid.json")
    evidence["overall_verdict"] = bad_verdict
    decision = _load(EXAMPLES / "cdb_decision_record_paper_valid.json")
    decision["evidence_id"] = evidence["evidence_id"]
    decision["run_id"] = evidence["run_id"]
    errors = validate_paper_candidate_transition(
        candidate=candidate,
        evidence=evidence,
        decision=decision,
    )
    assert errors
    assert any(bad_verdict in e or "PASS" in e for e in errors)


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_action",
    (
        "live_trading",
        "live_capital_allocation",
        "bypass_risk_layer",
        "automatic_strategy_promotion",
        "real_money_go",
        "promote_to_live",
    ),
)
def test_allowed_next_actions_rejects_unsafe_vocabulary(bad_action: str) -> None:
    decision = _load(EXAMPLES / "cdb_decision_record_valid.json")
    decision["allowed_next_actions"] = [bad_action]
    assert bad_action not in SAFE_ALLOWED_NEXT_ACTIONS
    assert _errors("cdb_decision_record.v1.schema.json", decision)
    assert validate_decision_allowed_actions(decision)


@pytest.mark.unit
def test_wiring_source_to_compiler_to_candidate_to_registry() -> None:
    source = _load(EXAMPLES / "cdb_source_evidence_binance_valid.json")
    report = _load(EXAMPLES / "cdb_compiler_report_valid.json")
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    evidence = _load(EXAMPLES / "cdb_candidate_evidence_pass_valid.json")
    decision = _load(EXAMPLES / "cdb_decision_record_paper_valid.json")

    assert any(
        ref["evidence_id"] == source["evidence_id"]
        for ref in report["source_evidence_refs"]
    )
    assert report["candidate_id"] == candidate["candidate_id"]
    assert entry["candidate_id"] == candidate["candidate_id"]
    assert entry["candidate_version"] == candidate["candidate_version"]
    assert transition["to_status"] == "PAPER_CANDIDATE"
    assert transition["evidence_id"] == evidence["evidence_id"]
    assert transition["decision_id"] == decision["decision_id"]
    assert (
        validate_paper_candidate_transition(
            candidate=candidate,
            evidence=evidence,
            decision=decision,
            transition=transition,
        )
        == []
    )


@pytest.mark.unit
def test_profitability_and_arvp_lineage_untouched() -> None:
    assert (CONTRACTS / "profitability_candidate_contract.v1.schema.json").is_file()
    assert (CONTRACTS / "profitability_evidence_packet.v1.schema.json").is_file()
    candidate = _load(EXAMPLES / "cdb_strategy_candidate_valid.json")
    assert (
        candidate["lineage_refs"]["profitability_candidate_contract"]
        == "profitability_candidate_contract.v1"
    )


@pytest.mark.unit
def test_wave2_docs_exist() -> None:
    research = PROJECT_ROOT / "docs" / "research"
    for name in (
        "CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md",
        "CDB_STRATEGY_CANDIDATE_COMPILER_V1.md",
        "CDB_GITHUB_CANDIDATE_REGISTRY_V1.md",
        "CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md",
    ):
        assert (research / name).is_file()
    overview = (CONTRACTS / "CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md").read_text(
        encoding="utf-8"
    )
    assert "PMR-01" in overview
    assert "cdb.source_evidence.v1" in overview


# --- Post-merge residuals G-01..G-04 (#4283) ---


@pytest.mark.unit
def test_g01_validating_rejects_null_validation_manifest() -> None:
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    entry["status"] = "VALIDATING"
    entry["validation_manifest_id"] = None
    entry["run_id"] = None
    entry["evidence_id"] = None
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", entry)
    assert validate_registry_entry_status_bindings(entry)

    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    transition["to_status"] = "VALIDATING"
    transition["validation_manifest_id"] = None
    transition["run_id"] = None
    transition["evidence_id"] = None
    transition["evidence_hash"] = None
    assert _errors("cdb_candidate_transition.v1.schema.json", transition)
    assert validate_transition_status_bindings(transition)


@pytest.mark.unit
def test_g02_evidence_ready_rejects_null_run_evidence_fields() -> None:
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    entry["status"] = "EVIDENCE_READY"
    entry["run_id"] = None
    entry["evidence_id"] = None
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", entry)
    assert validate_registry_entry_status_bindings(entry)

    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    transition["to_status"] = "EVIDENCE_READY"
    transition["run_id"] = None
    transition["evidence_id"] = None
    transition["evidence_hash"] = None
    assert _errors("cdb_candidate_transition.v1.schema.json", transition)
    assert validate_transition_status_bindings(transition)


@pytest.mark.unit
def test_g03_unsorted_source_evidence_refs_rejected() -> None:
    report = _load(EXAMPLES / "cdb_compiler_report_valid.json")
    assert validate_source_evidence_refs_sorted(report["source_evidence_refs"]) == []
    reversed_refs = list(reversed(report["source_evidence_refs"]))
    assert [r["evidence_id"] for r in reversed_refs] != sorted(
        r["evidence_id"] for r in reversed_refs
    )
    errors = validate_source_evidence_refs_sorted(reversed_refs)
    assert errors
    assert any("sorted by evidence_id" in e for e in errors)
    # Hash differs when order differs — determinism requires sort enforcement.
    assert canonical_content_hash({"refs": report["source_evidence_refs"]}) != (
        canonical_content_hash({"refs": reversed_refs})
    )


@pytest.mark.unit
def test_g04_paper_candidate_entry_rejects_null_evidence_run() -> None:
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    entry["status"] = "PAPER_CANDIDATE"
    entry["run_id"] = None
    entry["evidence_id"] = None
    # decision_id may remain; run/evidence null must still fail.
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", entry)
    companion = validate_registry_entry_status_bindings(entry)
    assert companion
    assert any("PAPER_CANDIDATE" in e for e in companion)


@pytest.mark.unit
def test_g01_g02_g04_valid_status_bindings_still_pass() -> None:
    entry = _load(EXAMPLES / "cdb_candidate_registry_entry_valid.json")
    assert entry["status"] == "EVIDENCE_READY"
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", entry) == []
    assert validate_registry_entry_status_bindings(entry) == []

    paper_entry = deepcopy(entry)
    paper_entry["status"] = "PAPER_CANDIDATE"
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", paper_entry) == []
    assert validate_registry_entry_status_bindings(paper_entry) == []

    validating = deepcopy(entry)
    validating["status"] = "VALIDATING"
    validating["run_id"] = None
    validating["evidence_id"] = None
    validating["decision_id"] = None
    assert validating["validation_manifest_id"]
    assert _errors("cdb_candidate_registry_entry.v1.schema.json", validating) == []
    assert validate_registry_entry_status_bindings(validating) == []

    transition = _load(EXAMPLES / "cdb_candidate_transition_paper_valid.json")
    assert _errors("cdb_candidate_transition.v1.schema.json", transition) == []
    assert validate_transition_status_bindings(transition) == []
