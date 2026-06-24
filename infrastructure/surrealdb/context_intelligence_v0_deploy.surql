-- =====================================================================
-- Context Intelligence v0 — SurrealKit-ready Deployable Schema
-- Issue: #3420  (Issue #2037 original, #3418 Meta, #3420 SurrealKit)
--
-- THIS IS A DEPLOYABLE WRAPPER.  The canonical schema draft remains
-- `context_intelligence_v0.surql`.  This file adds:
--   1. NS/DB context (idempotent)
--   2. IF NOT EXISTS on all DEFINE TABLE statements
--   3. Fail-closed PERMISSIONS (select/update/create/delete NONE)
--
-- Guardrails (hard):
-- - Schema wrapper only: no productive apply, no migration, no bootstrap
-- - No runtime, compose, service, or trading-system changes implied
-- - No secrets, no trading-state objects (no orders / positions / fills)
-- - `agent_memory` remains schema-only; no memory writes enabled
-- - Permissions are fail-closed NONE.  Productive permissions will be
--   defined by Issue #3426 (Permission Matrix + Readonly Agent User).
--
-- Conventions:
-- - Each DEFINE TABLE uses IF NOT EXISTS for idempotent loading
-- - Each table defines FOR select NONE, FOR create NONE, FOR update
--   NONE, FOR delete NONE as baseline
-- - Field / index definitions are identical to the canonical draft;
--   see `context_intelligence_v0.surql` for field-level docs
-- =====================================================================

-- ===== Namespace / Database Context =====
DEFINE NAMESPACE IF NOT EXISTS cdb;
USE NS cdb;
DEFINE DATABASE IF NOT EXISTS context_intel;
USE DB context_intel;

-- ===== VectorGraph: code/doc full-text analyzer (Issue #3422) =====
DEFINE ANALYZER IF NOT EXISTS cdb_code_analyzer TOKENIZERS class, camel FILTERS lowercase, ascii;

-- ===== repo_artifact =====
DEFINE TABLE IF NOT EXISTS repo_artifact SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD artifact_id ON TABLE repo_artifact TYPE string;
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
DEFINE FIELD created_at ON TABLE repo_artifact TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_repo_artifact_artifact_id_unique ON TABLE repo_artifact FIELDS artifact_id UNIQUE;
DEFINE INDEX idx_repo_artifact_source_path ON TABLE repo_artifact FIELDS source_path;
DEFINE INDEX idx_repo_artifact_source_hash ON TABLE repo_artifact FIELDS source_hash;
DEFINE INDEX idx_repo_artifact_created_at ON TABLE repo_artifact FIELDS created_at;

-- ===== code_symbol =====
DEFINE TABLE IF NOT EXISTS code_symbol SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD symbol_id ON TABLE code_symbol TYPE string;
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
DEFINE FIELD created_at ON TABLE code_symbol TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_code_symbol_symbol_id_unique ON TABLE code_symbol FIELDS symbol_id UNIQUE;
DEFINE INDEX idx_code_symbol_qualified_name ON TABLE code_symbol FIELDS qualified_name;
DEFINE INDEX idx_code_symbol_file_path ON TABLE code_symbol FIELDS file_path;
DEFINE INDEX idx_code_symbol_created_at ON TABLE code_symbol FIELDS created_at;

-- ===== doc_page =====
DEFINE TABLE IF NOT EXISTS doc_page SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD page_id ON TABLE doc_page TYPE string;
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
DEFINE FIELD created_at ON TABLE doc_page TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_doc_page_page_id_unique ON TABLE doc_page FIELDS page_id UNIQUE;
DEFINE INDEX idx_doc_page_source_path ON TABLE doc_page FIELDS source_path;
DEFINE INDEX idx_doc_page_source_hash ON TABLE doc_page FIELDS source_hash;
DEFINE INDEX idx_doc_page_created_at ON TABLE doc_page FIELDS created_at;

-- ===== doc_section =====
DEFINE TABLE IF NOT EXISTS doc_section SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD section_id ON TABLE doc_section TYPE string;
DEFINE FIELD page_ref ON TABLE doc_section TYPE record;
DEFINE FIELD heading ON TABLE doc_section TYPE string;
DEFINE FIELD heading_path ON TABLE doc_section TYPE array;
DEFINE FIELD section_index ON TABLE doc_section TYPE int;
DEFINE FIELD span_start_line ON TABLE doc_section TYPE int;
DEFINE FIELD span_end_line ON TABLE doc_section TYPE int;
DEFINE FIELD source_hash ON TABLE doc_section TYPE string;
DEFINE FIELD confidence ON TABLE doc_section TYPE float;
DEFINE FIELD comment ON TABLE doc_section TYPE string;
DEFINE FIELD created_at ON TABLE doc_section TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_doc_section_section_id_unique ON TABLE doc_section FIELDS section_id UNIQUE;
DEFINE INDEX idx_doc_section_page_ref ON TABLE doc_section FIELDS page_ref;
DEFINE INDEX idx_doc_section_created_at ON TABLE doc_section FIELDS created_at;

-- ===== doc_chunk =====
DEFINE TABLE IF NOT EXISTS doc_chunk SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD chunk_id ON TABLE doc_chunk TYPE string;
DEFINE FIELD page_ref ON TABLE doc_chunk TYPE record;
DEFINE FIELD section_ref ON TABLE doc_chunk TYPE record;
DEFINE FIELD chunk_index ON TABLE doc_chunk TYPE int;
DEFINE FIELD content ON TABLE doc_chunk TYPE string;
DEFINE FIELD content_hash ON TABLE doc_chunk TYPE string;
DEFINE FIELD tokens_estimate ON TABLE doc_chunk TYPE int;
DEFINE FIELD source_hash ON TABLE doc_chunk TYPE string;
DEFINE FIELD confidence ON TABLE doc_chunk TYPE float;
DEFINE FIELD comment ON TABLE doc_chunk TYPE string;
DEFINE FIELD embedding ON TABLE doc_chunk TYPE array;
DEFINE FIELD created_at ON TABLE doc_chunk TYPE datetime VALUE $value OR time::now();
DEFINE INDEX IF NOT EXISTS idx_doc_chunk_embedding_hnsw ON TABLE doc_chunk FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;
DEFINE INDEX IF NOT EXISTS idx_doc_chunk_content_ft ON TABLE doc_chunk FIELDS content FULLTEXT ANALYZER cdb_code_analyzer BM25 HIGHLIGHTS;
DEFINE INDEX idx_doc_chunk_chunk_id_unique ON TABLE doc_chunk FIELDS chunk_id UNIQUE;
DEFINE INDEX idx_doc_chunk_page_ref ON TABLE doc_chunk FIELDS page_ref;
DEFINE INDEX idx_doc_chunk_section_ref ON TABLE doc_chunk FIELDS section_ref;
DEFINE INDEX idx_doc_chunk_content_hash ON TABLE doc_chunk FIELDS content_hash;
DEFINE INDEX idx_doc_chunk_created_at ON TABLE doc_chunk FIELDS created_at;

-- ===== concept =====
DEFINE TABLE IF NOT EXISTS concept SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD concept_id ON TABLE concept TYPE string;
DEFINE FIELD name ON TABLE concept TYPE string;
DEFINE FIELD description ON TABLE concept TYPE string;
DEFINE FIELD tags ON TABLE concept TYPE array;
DEFINE FIELD source_refs ON TABLE concept TYPE array;
DEFINE FIELD evidence_refs ON TABLE concept TYPE array;
DEFINE FIELD freshness ON TABLE concept TYPE string;
DEFINE FIELD confidence ON TABLE concept TYPE float;
DEFINE FIELD comment ON TABLE concept TYPE string;
DEFINE FIELD created_at ON TABLE concept TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_concept_concept_id_unique ON TABLE concept FIELDS concept_id UNIQUE;
DEFINE INDEX idx_concept_name ON TABLE concept FIELDS name;
DEFINE INDEX idx_concept_created_at ON TABLE concept FIELDS created_at;

-- ===== dependency_edge =====
DEFINE TABLE IF NOT EXISTS dependency_edge SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD edge_id ON TABLE dependency_edge TYPE string;
DEFINE FIELD edge_type ON TABLE dependency_edge TYPE string;
DEFINE FIELD from_ref ON TABLE dependency_edge TYPE record;
DEFINE FIELD to_ref ON TABLE dependency_edge TYPE record;
DEFINE FIELD source_ref ON TABLE dependency_edge TYPE string;
DEFINE FIELD confidence ON TABLE dependency_edge TYPE float;
DEFINE FIELD evidence_level ON TABLE dependency_edge TYPE string;
DEFINE FIELD inferred ON TABLE dependency_edge TYPE bool;
DEFINE FIELD comment ON TABLE dependency_edge TYPE string;
DEFINE FIELD created_at ON TABLE dependency_edge TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_dependency_edge_id_unique ON TABLE dependency_edge FIELDS edge_id UNIQUE;
DEFINE INDEX idx_dependency_edge_type ON TABLE dependency_edge FIELDS edge_type;
DEFINE INDEX idx_dependency_edge_from_ref ON TABLE dependency_edge FIELDS from_ref;
DEFINE INDEX idx_dependency_edge_to_ref ON TABLE dependency_edge FIELDS to_ref;
DEFINE INDEX idx_dependency_edge_created_at ON TABLE dependency_edge FIELDS created_at;

-- ===== evidence_ref =====
DEFINE TABLE IF NOT EXISTS evidence_ref SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD evidence_id ON TABLE evidence_ref TYPE string;
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
DEFINE FIELD created_at ON TABLE evidence_ref TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_evidence_ref_evidence_id_unique ON TABLE evidence_ref FIELDS evidence_id UNIQUE;
DEFINE INDEX idx_evidence_ref_source_path ON TABLE evidence_ref FIELDS source_path;
DEFINE INDEX idx_evidence_ref_source_hash ON TABLE evidence_ref FIELDS source_hash;
DEFINE INDEX idx_evidence_ref_collected_at ON TABLE evidence_ref FIELDS collected_at;
DEFINE INDEX idx_evidence_ref_created_at ON TABLE evidence_ref FIELDS created_at;

-- ===== claim =====
DEFINE TABLE IF NOT EXISTS claim SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD claim_id ON TABLE claim TYPE string;
DEFINE FIELD title ON TABLE claim TYPE string;
DEFINE FIELD statement ON TABLE claim TYPE string;
DEFINE FIELD scope ON TABLE claim TYPE string;
DEFINE FIELD status ON TABLE claim TYPE string;
DEFINE FIELD evidence_refs ON TABLE claim TYPE array;
DEFINE FIELD source_refs ON TABLE claim TYPE array;
DEFINE FIELD confidence ON TABLE claim TYPE float;
DEFINE FIELD comment ON TABLE claim TYPE string;
DEFINE FIELD created_at ON TABLE claim TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_claim_claim_id_unique ON TABLE claim FIELDS claim_id UNIQUE;
DEFINE INDEX idx_claim_status ON TABLE claim FIELDS status;
DEFINE INDEX idx_claim_created_at ON TABLE claim FIELDS created_at;

-- ===== decision_event =====
DEFINE TABLE IF NOT EXISTS decision_event SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD decision_id ON TABLE decision_event TYPE string;
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
DEFINE FIELD created_at ON TABLE decision_event TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_decision_event_decision_id_unique ON TABLE decision_event FIELDS decision_id UNIQUE;
DEFINE INDEX idx_decision_event_status ON TABLE decision_event FIELDS status;
DEFINE INDEX idx_decision_event_created_at ON TABLE decision_event FIELDS created_at;

-- ===== agent_memory (schema only) =====
DEFINE TABLE IF NOT EXISTS agent_memory SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD memory_id ON TABLE agent_memory TYPE string;
DEFINE FIELD scope ON TABLE agent_memory TYPE string;
DEFINE FIELD namespace ON TABLE agent_memory TYPE string;
DEFINE FIELD memory_type ON TABLE agent_memory TYPE string;
DEFINE FIELD content ON TABLE agent_memory TYPE string;
DEFINE FIELD source_refs ON TABLE agent_memory TYPE array;
DEFINE FIELD evidence_refs ON TABLE agent_memory TYPE array;
DEFINE FIELD confidence ON TABLE agent_memory TYPE float;
DEFINE FIELD ttl ON TABLE agent_memory TYPE int;
DEFINE FIELD expires_at ON TABLE agent_memory TYPE datetime;
DEFINE FIELD stale_after ON TABLE agent_memory TYPE option<int>;
DEFINE FIELD superseded_by ON TABLE agent_memory TYPE option<string>;
DEFINE FIELD created_by ON TABLE agent_memory TYPE string;
DEFINE FIELD comment ON TABLE agent_memory TYPE string;
DEFINE FIELD created_at ON TABLE agent_memory TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_agent_memory_memory_id_unique ON TABLE agent_memory FIELDS memory_id UNIQUE;
DEFINE INDEX idx_agent_memory_scope ON TABLE agent_memory FIELDS scope;
DEFINE INDEX idx_agent_memory_namespace ON TABLE agent_memory FIELDS namespace;
DEFINE INDEX idx_agent_memory_created_at ON TABLE agent_memory FIELDS created_at;

-- ===== context_query =====
DEFINE TABLE IF NOT EXISTS context_query SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD query_id ON TABLE context_query TYPE string;
DEFINE FIELD query_type ON TABLE context_query TYPE string;
DEFINE FIELD query_text ON TABLE context_query TYPE string;
DEFINE FIELD context_refs ON TABLE context_query TYPE array;
DEFINE FIELD confidence ON TABLE context_query TYPE float;
DEFINE FIELD comment ON TABLE context_query TYPE string;
DEFINE FIELD created_at ON TABLE context_query TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_context_query_query_id_unique ON TABLE context_query FIELDS query_id UNIQUE;
DEFINE INDEX idx_context_query_query_type ON TABLE context_query FIELDS query_type;
DEFINE INDEX idx_context_query_created_at ON TABLE context_query FIELDS created_at;

-- ===== audit_observation =====
DEFINE TABLE IF NOT EXISTS audit_observation SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD observation_id ON TABLE audit_observation TYPE string;
DEFINE FIELD observation_type ON TABLE audit_observation TYPE string;
DEFINE FIELD subject_ref ON TABLE audit_observation TYPE record;
DEFINE FIELD message ON TABLE audit_observation TYPE string;
DEFINE FIELD evidence_refs ON TABLE audit_observation TYPE array;
DEFINE FIELD confidence ON TABLE audit_observation TYPE float;
DEFINE FIELD observed_by ON TABLE audit_observation TYPE string;
DEFINE FIELD observed_at ON TABLE audit_observation TYPE datetime;
DEFINE FIELD comment ON TABLE audit_observation TYPE string;
DEFINE FIELD severity ON TABLE audit_observation TYPE string;
DEFINE FIELD related_claims ON TABLE audit_observation TYPE array;
DEFINE FIELD related_decisions ON TABLE audit_observation TYPE array;
DEFINE FIELD related_memory ON TABLE audit_observation TYPE array;
DEFINE FIELD status ON TABLE audit_observation TYPE string;
DEFINE FIELD created_at ON TABLE audit_observation TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_audit_observation_observation_id_unique ON TABLE audit_observation FIELDS observation_id UNIQUE;
DEFINE INDEX idx_audit_observation_type ON TABLE audit_observation FIELDS observation_type;
DEFINE INDEX idx_audit_observation_observed_at ON TABLE audit_observation FIELDS observed_at;
DEFINE INDEX idx_audit_observation_created_at ON TABLE audit_observation FIELDS created_at;
DEFINE INDEX idx_audit_observation_severity ON TABLE audit_observation FIELDS severity;
DEFINE INDEX idx_audit_observation_status ON TABLE audit_observation FIELDS status;

-- ===== contradiction =====
DEFINE TABLE IF NOT EXISTS contradiction SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD contradiction_id ON TABLE contradiction TYPE string;
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
DEFINE FIELD created_at ON TABLE contradiction TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_contradiction_id_unique ON TABLE contradiction FIELDS contradiction_id UNIQUE;
DEFINE INDEX idx_contradiction_status ON TABLE contradiction FIELDS status;
DEFINE INDEX idx_contradiction_detected_at ON TABLE contradiction FIELDS detected_at;
DEFINE INDEX idx_contradiction_created_at ON TABLE contradiction FIELDS created_at;

-- ===== stale_context =====
DEFINE TABLE IF NOT EXISTS stale_context SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD stale_id ON TABLE stale_context TYPE string;
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
DEFINE FIELD created_at ON TABLE stale_context TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_stale_context_stale_id_unique ON TABLE stale_context FIELDS stale_id UNIQUE;
DEFINE INDEX idx_stale_context_status ON TABLE stale_context FIELDS status;
DEFINE INDEX idx_stale_context_detected_at ON TABLE stale_context FIELDS detected_at;
DEFINE INDEX idx_stale_context_created_at ON TABLE stale_context FIELDS created_at;

-- ===== scope_drift_event =====
DEFINE TABLE IF NOT EXISTS scope_drift_event SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD drift_id ON TABLE scope_drift_event TYPE string;
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
DEFINE FIELD created_at ON TABLE scope_drift_event TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_scope_drift_id_unique ON TABLE scope_drift_event FIELDS drift_id UNIQUE;
DEFINE INDEX idx_scope_drift_event_type ON TABLE scope_drift_event FIELDS event_type;
DEFINE INDEX idx_scope_drift_status ON TABLE scope_drift_event FIELDS status;
DEFINE INDEX idx_scope_drift_created_at ON TABLE scope_drift_event FIELDS created_at;

-- ===== knowledge_quality_score =====
DEFINE TABLE IF NOT EXISTS knowledge_quality_score SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD score_id ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD subject_ref ON TABLE knowledge_quality_score TYPE record;
DEFINE FIELD scoring_model ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD score ON TABLE knowledge_quality_score TYPE float;
DEFINE FIELD dimensions ON TABLE knowledge_quality_score TYPE record;
DEFINE FIELD confidence ON TABLE knowledge_quality_score TYPE float;
DEFINE FIELD computed_by ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD computed_at ON TABLE knowledge_quality_score TYPE datetime;
DEFINE FIELD comment ON TABLE knowledge_quality_score TYPE string;
DEFINE FIELD created_at ON TABLE knowledge_quality_score TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_knowledge_quality_score_id_unique ON TABLE knowledge_quality_score FIELDS score_id UNIQUE;
DEFINE INDEX idx_knowledge_quality_subject_ref ON TABLE knowledge_quality_score FIELDS subject_ref;
DEFINE INDEX idx_knowledge_quality_computed_at ON TABLE knowledge_quality_score FIELDS computed_at;
DEFINE INDEX idx_knowledge_quality_created_at ON TABLE knowledge_quality_score FIELDS created_at;

-- ===== visual_control_view =====
DEFINE TABLE IF NOT EXISTS visual_control_view SCHEMAFULL
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD view_id ON TABLE visual_control_view TYPE string;
DEFINE FIELD view_type ON TABLE visual_control_view TYPE string;
DEFINE FIELD view_label ON TABLE visual_control_view TYPE string;
DEFINE FIELD target_scope ON TABLE visual_control_view TYPE string;
DEFINE FIELD data_sources ON TABLE visual_control_view TYPE array;
DEFINE FIELD filters ON TABLE visual_control_view TYPE record;
DEFINE FIELD required_queries ON TABLE visual_control_view TYPE array;
DEFINE FIELD display_entities ON TABLE visual_control_view TYPE array;
DEFINE FIELD display_edges ON TABLE visual_control_view TYPE array;
DEFINE FIELD warnings ON TABLE visual_control_view TYPE array;
DEFINE FIELD generated_at ON TABLE visual_control_view TYPE datetime;
DEFINE FIELD generated_by ON TABLE visual_control_view TYPE string;
DEFINE FIELD export_formats ON TABLE visual_control_view TYPE array;
DEFINE FIELD guardrails ON TABLE visual_control_view TYPE array;
DEFINE FIELD created_at ON TABLE visual_control_view TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_visual_control_view_id_unique ON TABLE visual_control_view FIELDS view_id UNIQUE;
DEFINE INDEX idx_visual_control_view_type ON TABLE visual_control_view FIELDS view_type;
DEFINE INDEX idx_visual_control_view_scope ON TABLE visual_control_view FIELDS target_scope;
DEFINE INDEX idx_visual_control_view_generated_at ON TABLE visual_control_view FIELDS generated_at;
DEFINE INDEX idx_visual_control_view_created_at ON TABLE visual_control_view FIELDS created_at;

-- ===== Graph Relations v0 (Issue #3423) =====

-- ===== artifact_cites_decision =====
DEFINE TABLE IF NOT EXISTS artifact_cites_decision TYPE RELATION
  FROM repo_artifact | doc_page | doc_chunk
  TO decision_event
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD source ON TABLE artifact_cites_decision TYPE string;
DEFINE FIELD confidence ON TABLE artifact_cites_decision TYPE float;
DEFINE FIELD timestamp ON TABLE artifact_cites_decision TYPE datetime;
DEFINE FIELD hash ON TABLE artifact_cites_decision TYPE string;
DEFINE FIELD comment ON TABLE artifact_cites_decision TYPE string;
DEFINE FIELD created_at ON TABLE artifact_cites_decision TYPE datetime VALUE $value OR time::now();

-- ===== memory_supports_decision =====
DEFINE TABLE IF NOT EXISTS memory_supports_decision TYPE RELATION
  FROM agent_memory
  TO decision_event
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD source ON TABLE memory_supports_decision TYPE string;
DEFINE FIELD confidence ON TABLE memory_supports_decision TYPE float;
DEFINE FIELD timestamp ON TABLE memory_supports_decision TYPE datetime;
DEFINE FIELD hash ON TABLE memory_supports_decision TYPE string;
DEFINE FIELD comment ON TABLE memory_supports_decision TYPE string;
DEFINE FIELD created_at ON TABLE memory_supports_decision TYPE datetime VALUE $value OR time::now();

-- ===== chunk_mentions_symbol =====
DEFINE TABLE IF NOT EXISTS chunk_mentions_symbol TYPE RELATION
  FROM doc_chunk
  TO code_symbol
  PERMISSIONS FOR select NONE, FOR create NONE, FOR update NONE, FOR delete NONE;
DEFINE FIELD source ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD confidence ON TABLE chunk_mentions_symbol TYPE float;
DEFINE FIELD timestamp ON TABLE chunk_mentions_symbol TYPE datetime;
DEFINE FIELD hash ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD mention_context ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD comment ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD created_at ON TABLE chunk_mentions_symbol TYPE datetime VALUE $value OR time::now();
