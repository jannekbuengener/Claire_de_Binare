"""Read-only Research Validation Wave-2 helpers."""

from tools.research_validation.wave2_cross_contract import (
    SAFE_ALLOWED_NEXT_ACTIONS,
    Wave2ContractError,
    canonical_content_hash,
    parse_candidate_version,
    validate_brief_provenance,
    validate_candidate_lineage,
    validate_compiler_input_completeness,
    validate_decision_allowed_actions,
    validate_paper_candidate_transition,
    validate_source_evidence_non_authority,
)

__all__ = [
    "SAFE_ALLOWED_NEXT_ACTIONS",
    "Wave2ContractError",
    "canonical_content_hash",
    "parse_candidate_version",
    "validate_brief_provenance",
    "validate_candidate_lineage",
    "validate_compiler_input_completeness",
    "validate_decision_allowed_actions",
    "validate_paper_candidate_transition",
    "validate_source_evidence_non_authority",
]
