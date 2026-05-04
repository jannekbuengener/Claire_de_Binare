-- =====================================================================
-- Context Intelligence v0 — SurrealQL Schema Draft (read-only draft)
-- Issue: #2037  (Parent: #2034, Epic: #1976)
-- Core schema objects per #1981; gap-closed via schema-draft extension
--
-- Non-goals / Guardrails (hard):
-- - Schema draft only: no productive apply, no migration, no bootstrap (NS/DB)
-- - No runtime, compose, service, or trading-system changes implied
-- - No secrets, no trading-state objects (no orders / positions / fills)
-- - `agent_memory` is schema-only; this file does NOT enable memory writes
--
-- Conventions v0:
-- - Record identity:
--   - Surreal record id (e.g., repo_artifact:<id>) is canonical at storage level
--   - Each table also carries a stable `*_id` string field for deterministic IDs
--     and cross-system references (as required by dependency issues).
-- - Time fields:
--   - `created_at` (datetime) is required by v0 producer/validator contract
--     (this draft declares field shapes; it does not enforce mandatory presence
--     via ASSERT/DEFAULT to avoid any productive/runtime semantics)
--   - Domain-specific: `observed_at`, `collected_at`, `detected_at` where relevant
--   - Mandatory fields are tagged inline as `REQUIRED(v0-draft)`
-- - Provenance / evidence:
--   - Prefer `source_*` + `*_hash` + `confidence` for traceability
--   - Links between objects are represented as record refs or id strings
-- - COMMENT field:
--   - Each table includes a free-text `comment` field (string)
--
-- Notes:
-- - This draft intentionally avoids NS/DB statements (CREATE/USE) and PERMISSIONS.
-- - This draft also avoids enforcement constraints (ASSERT/DEFAULT/UNIQUE); those
--   are expected to be handled by producer/validator logic until later waves.
-- - Fields are minimal and designed to be extended in later waves.
-- =====================================================================

-- ---------------------------
-- repo_artifact (Issue #1981)
-- ---------------------------
DEFINE TABLE repo_artifact SCHEMAFULL;
DEFINE FIELD artifact_id ON TABLE repo_artifact TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD artifact_type ON TABLE repo_artifact TYPE string;
DEFINE FIELD source_path ON TABLE repo_artifact TYPE string;
DEFINE FIELD source_url ON TABLE repo_artifact TYPE string;
DEFINE FIELD source_commit ON TABLE repo_artifact TYPE string;
DEFINE FIELD source_hash ON TABLE repo_artifact TYPE string;
DEFINE FIELD integrity_algo ON TABLE repo_artifact TYPE string;
DEFINE FIELD size_bytes ON TABLE repo_artifact TYPE int;
DEFINE FIELD mime_type ON TABLE repo_artifact TYPE string;
DEFINE FIELD observed_at ON TABLE repo_artifact TYPE datetime;
DEFINE FIELD freshness ON TABLE repo_artifact TYPE string;
DEFINE FIELD confidence ON TABLE repo_artifact TYPE float;
DEFINE FIELD comment ON TABLE repo_artifact TYPE string;
DEFINE FIELD created_at ON TABLE repo_artifact TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_repo_artifact_artifact_id_unique ON TABLE repo_artifact FIELDS artifact_id UNIQUE;
DEFINE INDEX idx_repo_artifact_source_path ON TABLE repo_artifact FIELDS source_path;
DEFINE INDEX idx_repo_artifact_source_hash ON TABLE repo_artifact FIELDS source_hash;
DEFINE INDEX idx_repo_artifact_created_at ON TABLE repo_artifact FIELDS created_at;

-- --------------------------
-- code_symbol (Issue #1981)
-- --------------------------
DEFINE TABLE code_symbol SCHEMAFULL;
DEFINE FIELD symbol_id ON TABLE code_symbol TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD language ON TABLE code_symbol TYPE string;
DEFINE FIELD symbol_kind ON TABLE code_symbol TYPE string;
DEFINE FIELD qualified_name ON TABLE code_symbol TYPE string;
DEFINE FIELD name ON TABLE code_symbol TYPE string;
DEFINE FIELD file_path ON TABLE code_symbol TYPE string;
DEFINE FIELD span_start_line ON TABLE code_symbol TYPE int;
DEFINE FIELD span_end_line ON TABLE code_symbol TYPE int;
DEFINE FIELD source_hash ON TABLE code_symbol TYPE string;
DEFINE FIELD source_commit ON TABLE code_symbol TYPE string;
DEFINE FIELD confidence ON TABLE code_symbol TYPE float;
DEFINE FIELD comment ON TABLE code_symbol TYPE string;
DEFINE FIELD created_at ON TABLE code_symbol TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_code_symbol_symbol_id_unique ON TABLE code_symbol FIELDS symbol_id UNIQUE;
DEFINE INDEX idx_code_symbol_qualified_name ON TABLE code_symbol FIELDS qualified_name;
DEFINE INDEX idx_code_symbol_file_path ON TABLE code_symbol FIELDS file_path;
DEFINE INDEX idx_code_symbol_created_at ON TABLE code_symbol FIELDS created_at;

-- ------------------------
-- doc_page (Issue #1981)
-- ------------------------
DEFINE TABLE doc_page SCHEMAFULL;
DEFINE FIELD page_id ON TABLE doc_page TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD source_path ON TABLE doc_page TYPE string;
DEFINE FIELD source_url ON TABLE doc_page TYPE string;
DEFINE FIELD source_commit ON TABLE doc_page TYPE string;
DEFINE FIELD source_hash ON TABLE doc_page TYPE string;
DEFINE FIELD title ON TABLE doc_page TYPE string;
DEFINE FIELD doc_format ON TABLE doc_page TYPE string;
DEFINE FIELD observed_at ON TABLE doc_page TYPE datetime;
DEFINE FIELD freshness ON TABLE doc_page TYPE string;
DEFINE FIELD confidence ON TABLE doc_page TYPE float;
DEFINE FIELD comment ON TABLE doc_page TYPE string;
DEFINE FIELD created_at ON TABLE doc_page TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_doc_page_page_id_unique ON TABLE doc_page FIELDS page_id UNIQUE;
DEFINE INDEX idx_doc_page_source_path ON TABLE doc_page FIELDS source_path;
DEFINE INDEX idx_doc_page_source_hash ON TABLE doc_page FIELDS source_hash;
DEFINE INDEX idx_doc_page_created_at ON TABLE doc_page FIELDS created_at;

-- ---------------------------
-- doc_section (Issue #1981)
-- ---------------------------
DEFINE TABLE doc_section SCHEMAFULL;
DEFINE FIELD section_id ON TABLE doc_section TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD page_ref ON TABLE doc_section TYPE record;
DEFINE FIELD heading ON TABLE doc_section TYPE string;
DEFINE FIELD heading_path ON TABLE doc_section TYPE array;
DEFINE FIELD section_index ON TABLE doc_section TYPE int;
DEFINE FIELD span_start_line ON TABLE doc_section TYPE int;
DEFINE FIELD span_end_line ON TABLE doc_section TYPE int;
DEFINE FIELD source_hash ON TABLE doc_section TYPE string;
DEFINE FIELD confidence ON TABLE doc_section TYPE float;
DEFINE FIELD comment ON TABLE doc_section TYPE string;
DEFINE FIELD created_at ON TABLE doc_section TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_doc_section_section_id_unique ON TABLE doc_section FIELDS section_id UNIQUE;
DEFINE INDEX idx_doc_section_page_ref ON TABLE doc_section FIELDS page_ref;
DEFINE INDEX idx_doc_section_created_at ON TABLE doc_section FIELDS created_at;

-- -------------------------
-- doc_chunk (Issue #1981)
-- -------------------------
DEFINE TABLE doc_chunk SCHEMAFULL;
DEFINE FIELD chunk_id ON TABLE doc_chunk TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD page_ref ON TABLE doc_chunk TYPE record;
DEFINE FIELD section_ref ON TABLE doc_chunk TYPE record;
DEFINE FIELD chunk_index ON TABLE doc_chunk TYPE int;
DEFINE FIELD content ON TABLE doc_chunk TYPE string;
DEFINE FIELD content_hash ON TABLE doc_chunk TYPE string;
DEFINE FIELD tokens_estimate ON TABLE doc_chunk TYPE int;
DEFINE FIELD source_hash ON TABLE doc_chunk TYPE string;
DEFINE FIELD confidence ON TABLE doc_chunk TYPE float;
DEFINE FIELD comment ON TABLE doc_chunk TYPE string;
DEFINE FIELD created_at ON TABLE doc_chunk TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_doc_chunk_chunk_id_unique ON TABLE doc_chunk FIELDS chunk_id UNIQUE;
DEFINE INDEX idx_doc_chunk_page_ref ON TABLE doc_chunk FIELDS page_ref;
DEFINE INDEX idx_doc_chunk_section_ref ON TABLE doc_chunk FIELDS section_ref;
DEFINE INDEX idx_doc_chunk_content_hash ON TABLE doc_chunk FIELDS content_hash;
DEFINE INDEX idx_doc_chunk_created_at ON TABLE doc_chunk FIELDS created_at;

-- -----------------------
-- concept (Issue #1981)
-- -----------------------
DEFINE TABLE concept SCHEMAFULL;
DEFINE FIELD concept_id ON TABLE concept TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD name ON TABLE concept TYPE string;
DEFINE FIELD description ON TABLE concept TYPE string;
DEFINE FIELD tags ON TABLE concept TYPE array;
DEFINE FIELD source_refs ON TABLE concept TYPE array;
DEFINE FIELD evidence_refs ON TABLE concept TYPE array;
DEFINE FIELD freshness ON TABLE concept TYPE string;
DEFINE FIELD confidence ON TABLE concept TYPE float;
DEFINE FIELD comment ON TABLE concept TYPE string;
DEFINE FIELD created_at ON TABLE concept TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_concept_concept_id_unique ON TABLE concept FIELDS concept_id UNIQUE;
DEFINE INDEX idx_concept_name ON TABLE concept FIELDS name;
DEFINE INDEX idx_concept_created_at ON TABLE concept FIELDS created_at;

-- ------------------------------------------
-- dependency_edge (Issue #2000)
-- ------------------------------------------
DEFINE TABLE dependency_edge SCHEMAFULL;
DEFINE FIELD edge_id ON TABLE dependency_edge TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD edge_type ON TABLE dependency_edge TYPE string;
DEFINE FIELD from_ref ON TABLE dependency_edge TYPE record;
DEFINE FIELD to_ref ON TABLE dependency_edge TYPE record;
DEFINE FIELD source_ref ON TABLE dependency_edge TYPE string;
DEFINE FIELD confidence ON TABLE dependency_edge TYPE float;
DEFINE FIELD evidence_level ON TABLE dependency_edge TYPE string;
DEFINE FIELD inferred ON TABLE dependency_edge TYPE bool;
DEFINE FIELD comment ON TABLE dependency_edge TYPE string;
DEFINE FIELD created_at ON TABLE dependency_edge TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_dependency_edge_id_unique ON TABLE dependency_edge FIELDS edge_id UNIQUE;
DEFINE INDEX idx_dependency_edge_type ON TABLE dependency_edge FIELDS edge_type;
DEFINE INDEX idx_dependency_edge_from_ref ON TABLE dependency_edge FIELDS from_ref;
DEFINE INDEX idx_dependency_edge_to_ref ON TABLE dependency_edge FIELDS to_ref;
DEFINE INDEX idx_dependency_edge_created_at ON TABLE dependency_edge FIELDS created_at;

-- ------------------------------------------
-- evidence_ref (Issue #2005)
-- ------------------------------------------
DEFINE TABLE evidence_ref SCHEMAFULL;
DEFINE FIELD evidence_id ON TABLE evidence_ref TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD evidence_type ON TABLE evidence_ref TYPE string;
DEFINE FIELD source_path ON TABLE evidence_ref TYPE string;
DEFINE FIELD source_url ON TABLE evidence_ref TYPE string;
DEFINE FIELD source_hash ON TABLE evidence_ref TYPE string;
DEFINE FIELD source_commit ON TABLE evidence_ref TYPE string;
DEFINE FIELD collected_at ON TABLE evidence_ref TYPE datetime;
DEFINE FIELD observed_by ON TABLE evidence_ref TYPE string;
DEFINE FIELD freshness ON TABLE evidence_ref TYPE string;
DEFINE FIELD confidence ON TABLE evidence_ref TYPE float;
DEFINE FIELD validates ON TABLE evidence_ref TYPE array;
DEFINE FIELD invalidates ON TABLE evidence_ref TYPE array;
DEFINE FIELD related_artifacts ON TABLE evidence_ref TYPE array;
DEFINE FIELD related_decisions ON TABLE evidence_ref TYPE array;
DEFINE FIELD comment ON TABLE evidence_ref TYPE string;
DEFINE FIELD created_at ON TABLE evidence_ref TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_evidence_ref_evidence_id_unique ON TABLE evidence_ref FIELDS evidence_id UNIQUE;
DEFINE INDEX idx_evidence_ref_source_path ON TABLE evidence_ref FIELDS source_path;
DEFINE INDEX idx_evidence_ref_source_hash ON TABLE evidence_ref FIELDS source_hash;
DEFINE INDEX idx_evidence_ref_collected_at ON TABLE evidence_ref FIELDS collected_at;
DEFINE INDEX idx_evidence_ref_created_at ON TABLE evidence_ref FIELDS created_at;

-- -------------------------
-- claim (v0; linked by #2005/#2007)
-- -------------------------
DEFINE TABLE claim SCHEMAFULL;
DEFINE FIELD claim_id ON TABLE claim TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD title ON TABLE claim TYPE string;
DEFINE FIELD statement ON TABLE claim TYPE string;
DEFINE FIELD scope ON TABLE claim TYPE string;
DEFINE FIELD status ON TABLE claim TYPE string;
DEFINE FIELD evidence_refs ON TABLE claim TYPE array;
DEFINE FIELD source_refs ON TABLE claim TYPE array;
DEFINE FIELD confidence ON TABLE claim TYPE float;
DEFINE FIELD comment ON TABLE claim TYPE string;
DEFINE FIELD created_at ON TABLE claim TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_claim_claim_id_unique ON TABLE claim FIELDS claim_id UNIQUE;
DEFINE INDEX idx_claim_status ON TABLE claim FIELDS status;
DEFINE INDEX idx_claim_created_at ON TABLE claim FIELDS created_at;

-- ------------------------------------------
-- decision_event (Issue #2007)
-- ------------------------------------------
DEFINE TABLE decision_event SCHEMAFULL;
DEFINE FIELD decision_id ON TABLE decision_event TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD title ON TABLE decision_event TYPE string;
DEFINE FIELD question ON TABLE decision_event TYPE string;
DEFINE FIELD answer ON TABLE decision_event TYPE string;
DEFINE FIELD decision_type ON TABLE decision_event TYPE string;
DEFINE FIELD status ON TABLE decision_event TYPE string;
DEFINE FIELD scope ON TABLE decision_event TYPE string;
DEFINE FIELD evidence_refs ON TABLE decision_event TYPE array;
DEFINE FIELD claim_refs ON TABLE decision_event TYPE array;
DEFINE FIELD affected_artifacts ON TABLE decision_event TYPE array;
DEFINE FIELD agent ON TABLE decision_event TYPE string;
DEFINE FIELD human_go ON TABLE decision_event TYPE bool;
DEFINE FIELD confidence ON TABLE decision_event TYPE float;
DEFINE FIELD superseded_by ON TABLE decision_event TYPE string;
DEFINE FIELD invalidated_by ON TABLE decision_event TYPE string;
DEFINE FIELD uncertainty ON TABLE decision_event TYPE string;
DEFINE FIELD comment ON TABLE decision_event TYPE string;
DEFINE FIELD created_at ON TABLE decision_event TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_decision_event_decision_id_unique ON TABLE decision_event FIELDS decision_id UNIQUE;
DEFINE INDEX idx_decision_event_status ON TABLE decision_event FIELDS status;
DEFINE INDEX idx_decision_event_created_at ON TABLE decision_event FIELDS created_at;

-- ------------------------------------------
-- agent_memory (Issue #2009) — schema only
-- ------------------------------------------
DEFINE TABLE agent_memory SCHEMAFULL;
DEFINE FIELD memory_id ON TABLE agent_memory TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD scope ON TABLE agent_memory TYPE string;
DEFINE FIELD namespace ON TABLE agent_memory TYPE string;
DEFINE FIELD memory_type ON TABLE agent_memory TYPE string;
DEFINE FIELD content ON TABLE agent_memory TYPE string;
DEFINE FIELD source_refs ON TABLE agent_memory TYPE array;
DEFINE FIELD evidence_refs ON TABLE agent_memory TYPE array;
DEFINE FIELD confidence ON TABLE agent_memory TYPE float;
DEFINE FIELD ttl ON TABLE agent_memory TYPE int;
DEFINE FIELD expires_at ON TABLE agent_memory TYPE datetime;
DEFINE FIELD stale_after ON TABLE agent_memory TYPE int;
DEFINE FIELD superseded_by ON TABLE agent_memory TYPE string;
DEFINE FIELD created_by ON TABLE agent_memory TYPE string;
DEFINE FIELD comment ON TABLE agent_memory TYPE string;
DEFINE FIELD created_at ON TABLE agent_memory TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_agent_memory_memory_id_unique ON TABLE agent_memory FIELDS memory_id UNIQUE;
DEFINE INDEX idx_agent_memory_scope ON TABLE agent_memory FIELDS scope;
DEFINE INDEX idx_agent_memory_namespace ON TABLE agent_memory FIELDS namespace;
DEFINE INDEX idx_agent_memory_created_at ON TABLE agent_memory FIELDS created_at;

-- -------------------------
-- context_query (Issue #1981)
-- -------------------------
DEFINE TABLE context_query SCHEMAFULL;
DEFINE FIELD query_id ON TABLE context_query TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD query_type ON TABLE context_query TYPE string;
DEFINE FIELD query_text ON TABLE context_query TYPE string;
DEFINE FIELD context_refs ON TABLE context_query TYPE array;
DEFINE FIELD confidence ON TABLE context_query TYPE float;
DEFINE FIELD comment ON TABLE context_query TYPE string;
DEFINE FIELD created_at ON TABLE context_query TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_context_query_query_id_unique ON TABLE context_query FIELDS query_id UNIQUE;
DEFINE INDEX idx_context_query_query_type ON TABLE context_query FIELDS query_type;
DEFINE INDEX idx_context_query_created_at ON TABLE context_query FIELDS created_at;

-- -------------------------
-- audit_observation (v0)
-- -------------------------
DEFINE TABLE audit_observation SCHEMAFULL;
DEFINE FIELD observation_id ON TABLE audit_observation TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD observation_type ON TABLE audit_observation TYPE string;
DEFINE FIELD subject_ref ON TABLE audit_observation TYPE record;
DEFINE FIELD message ON TABLE audit_observation TYPE string;
DEFINE FIELD evidence_refs ON TABLE audit_observation TYPE array;
DEFINE FIELD confidence ON TABLE audit_observation TYPE float;
DEFINE FIELD observed_by ON TABLE audit_observation TYPE string;
DEFINE FIELD observed_at ON TABLE audit_observation TYPE datetime;
DEFINE FIELD comment ON TABLE audit_observation TYPE string;
DEFINE FIELD created_at ON TABLE audit_observation TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_audit_observation_observation_id_unique ON TABLE audit_observation FIELDS observation_id UNIQUE;
DEFINE INDEX idx_audit_observation_type ON TABLE audit_observation FIELDS observation_type;
DEFINE INDEX idx_audit_observation_observed_at ON TABLE audit_observation FIELDS observed_at;
DEFINE INDEX idx_audit_observation_created_at ON TABLE audit_observation FIELDS created_at;

-- ------------------------------------------
-- contradiction (Issue #2025)
-- ------------------------------------------
DEFINE TABLE contradiction SCHEMAFULL;
DEFINE FIELD contradiction_id ON TABLE contradiction TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD contradiction_type ON TABLE contradiction TYPE string;
DEFINE FIELD source_a_ref ON TABLE contradiction TYPE record;
DEFINE FIELD source_b_ref ON TABLE contradiction TYPE record;
DEFINE FIELD claim_refs ON TABLE contradiction TYPE array;
DEFINE FIELD evidence_refs ON TABLE contradiction TYPE array;
DEFINE FIELD severity ON TABLE contradiction TYPE string;
DEFINE FIELD confidence ON TABLE contradiction TYPE float;
DEFINE FIELD detected_by ON TABLE contradiction TYPE string;
DEFINE FIELD detected_at ON TABLE contradiction TYPE datetime;
DEFINE FIELD status ON TABLE contradiction TYPE string;
DEFINE FIELD recommended_action ON TABLE contradiction TYPE string;
DEFINE FIELD comment ON TABLE contradiction TYPE string;
DEFINE FIELD created_at ON TABLE contradiction TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_contradiction_id_unique ON TABLE contradiction FIELDS contradiction_id UNIQUE;
DEFINE INDEX idx_contradiction_status ON TABLE contradiction FIELDS status;
DEFINE INDEX idx_contradiction_detected_at ON TABLE contradiction FIELDS detected_at;
DEFINE INDEX idx_contradiction_created_at ON TABLE contradiction FIELDS created_at;

-- -------------------------
-- stale_context (v0; aligns with later wave)
-- -------------------------
DEFINE TABLE stale_context SCHEMAFULL;
DEFINE FIELD stale_id ON TABLE stale_context TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD subject_ref ON TABLE stale_context TYPE record;
DEFINE FIELD reason ON TABLE stale_context TYPE string;
DEFINE FIELD source_refs ON TABLE stale_context TYPE array;
DEFINE FIELD evidence_refs ON TABLE stale_context TYPE array;
DEFINE FIELD severity ON TABLE stale_context TYPE string;
DEFINE FIELD confidence ON TABLE stale_context TYPE float;
DEFINE FIELD detected_by ON TABLE stale_context TYPE string;
DEFINE FIELD detected_at ON TABLE stale_context TYPE datetime;
DEFINE FIELD status ON TABLE stale_context TYPE string;
DEFINE FIELD comment ON TABLE stale_context TYPE string;
DEFINE FIELD created_at ON TABLE stale_context TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_stale_context_stale_id_unique ON TABLE stale_context FIELDS stale_id UNIQUE;
DEFINE INDEX idx_stale_context_status ON TABLE stale_context FIELDS status;
DEFINE INDEX idx_stale_context_detected_at ON TABLE stale_context FIELDS detected_at;
DEFINE INDEX idx_stale_context_created_at ON TABLE stale_context FIELDS created_at;

-- -------------------------
-- scope_drift_event (v0; aligns with later wave)
-- -------------------------
DEFINE TABLE scope_drift_event SCHEMAFULL;
DEFINE FIELD drift_id ON TABLE scope_drift_event TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD scope ON TABLE scope_drift_event TYPE string;
DEFINE FIELD event_type ON TABLE scope_drift_event TYPE string;
DEFINE FIELD subject_ref ON TABLE scope_drift_event TYPE record;
DEFINE FIELD message ON TABLE scope_drift_event TYPE string;
DEFINE FIELD evidence_refs ON TABLE scope_drift_event TYPE array;
DEFINE FIELD confidence ON TABLE scope_drift_event TYPE float;
DEFINE FIELD detected_by ON TABLE scope_drift_event TYPE string;
DEFINE FIELD detected_at ON TABLE scope_drift_event TYPE datetime;
DEFINE FIELD status ON TABLE scope_drift_event TYPE string;
DEFINE FIELD comment ON TABLE scope_drift_event TYPE string;
DEFINE FIELD created_at ON TABLE scope_drift_event TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_scope_drift_id_unique ON TABLE scope_drift_event FIELDS drift_id UNIQUE;
DEFINE INDEX idx_scope_drift_event_type ON TABLE scope_drift_event FIELDS event_type;
DEFINE INDEX idx_scope_drift_status ON TABLE scope_drift_event FIELDS status;
DEFINE INDEX idx_scope_drift_created_at ON TABLE scope_drift_event FIELDS created_at;

-- -------------------------
-- knowledge_quality_score (v0; aligns with later wave)
-- -------------------------
DEFINE TABLE knowledge_quality_score SCHEMAFULL;
DEFINE FIELD score_id ON TABLE knowledge_quality_score TYPE string; -- REQUIRED(v0-draft)
DEFINE FIELD subject_ref ON TABLE knowledge_quality_score TYPE record;
DEFINE FIELD scoring_model ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD score ON TABLE knowledge_quality_score TYPE float;
DEFINE FIELD dimensions ON TABLE knowledge_quality_score TYPE record;
DEFINE FIELD confidence ON TABLE knowledge_quality_score TYPE float;
DEFINE FIELD computed_by ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD computed_at ON TABLE knowledge_quality_score TYPE datetime;
DEFINE FIELD comment ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD created_at ON TABLE knowledge_quality_score TYPE datetime VALUE $value OR time::now(); -- REQUIRED(v0-draft)
DEFINE INDEX idx_knowledge_quality_score_id_unique ON TABLE knowledge_quality_score FIELDS score_id UNIQUE;
DEFINE INDEX idx_knowledge_quality_subject_ref ON TABLE knowledge_quality_score FIELDS subject_ref;
DEFINE INDEX idx_knowledge_quality_computed_at ON TABLE knowledge_quality_score FIELDS computed_at;
DEFINE INDEX idx_knowledge_quality_created_at ON TABLE knowledge_quality_score FIELDS created_at;

