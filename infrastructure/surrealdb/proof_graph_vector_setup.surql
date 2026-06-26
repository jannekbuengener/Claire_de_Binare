-- =====================================================================
-- Graph + Vector Proof — Isolated Schema Setup
-- Isolated Namespace/Database: cdb_proof / graph_vector_proof
-- No existing ContextBrain / CDB data is touched.
-- LR: NO-GO. No live capital, no trading, no secrets.
-- =====================================================================

-- ===== Isolated Namespace / Database =====
DEFINE NAMESPACE IF NOT EXISTS cdb_proof;
USE NS cdb_proof;
DEFINE DATABASE IF NOT EXISTS graph_vector_proof;
USE DB graph_vector_proof;

-- ===== VectorGraph: code/doc full-text analyzer =====
DEFINE ANALYZER IF NOT EXISTS cdb_code_analyzer TOKENIZERS class, camel FILTERS lowercase, ascii;

-- ===== doc_page =====
DEFINE TABLE IF NOT EXISTS doc_page SCHEMAFULL
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD page_id ON TABLE doc_page TYPE string;
DEFINE FIELD source_path ON TABLE doc_page TYPE string;
DEFINE FIELD title ON TABLE doc_page TYPE string;
DEFINE FIELD doc_format ON TABLE doc_page TYPE string;
DEFINE FIELD confidence ON TABLE doc_page TYPE float;
DEFINE FIELD comment ON TABLE doc_page TYPE string;
DEFINE FIELD created_at ON TABLE doc_page TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_doc_page_page_id_unique ON TABLE doc_page FIELDS page_id UNIQUE;

-- ===== doc_chunk =====
DEFINE TABLE IF NOT EXISTS doc_chunk SCHEMAFULL
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD chunk_id ON TABLE doc_chunk TYPE string;
DEFINE FIELD page_ref ON TABLE doc_chunk TYPE record;
DEFINE FIELD chunk_index ON TABLE doc_chunk TYPE int;
DEFINE FIELD content ON TABLE doc_chunk TYPE string;
DEFINE FIELD content_hash ON TABLE doc_chunk TYPE string;
DEFINE FIELD confidence ON TABLE doc_chunk TYPE float;
DEFINE FIELD comment ON TABLE doc_chunk TYPE string;
DEFINE FIELD embedding ON TABLE doc_chunk TYPE array;
DEFINE FIELD created_at ON TABLE doc_chunk TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_doc_chunk_chunk_id_unique ON TABLE doc_chunk FIELDS chunk_id UNIQUE;
DEFINE INDEX IF NOT EXISTS idx_doc_chunk_embedding_hnsw ON TABLE doc_chunk FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;
DEFINE INDEX IF NOT EXISTS idx_doc_chunk_content_ft ON TABLE doc_chunk FIELDS content FULLTEXT ANALYZER cdb_code_analyzer BM25 HIGHLIGHTS;

-- ===== code_symbol =====
DEFINE TABLE IF NOT EXISTS code_symbol SCHEMAFULL
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD symbol_id ON TABLE code_symbol TYPE string;
DEFINE FIELD language ON TABLE code_symbol TYPE string;
DEFINE FIELD symbol_kind ON TABLE code_symbol TYPE string;
DEFINE FIELD qualified_name ON TABLE code_symbol TYPE string;
DEFINE FIELD name ON TABLE code_symbol TYPE string;
DEFINE FIELD file_path ON TABLE code_symbol TYPE string;
DEFINE FIELD confidence ON TABLE code_symbol TYPE float;
DEFINE FIELD comment ON TABLE code_symbol TYPE string;
DEFINE FIELD created_at ON TABLE code_symbol TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_code_symbol_symbol_id_unique ON TABLE code_symbol FIELDS symbol_id UNIQUE;

-- ===== claim =====
DEFINE TABLE IF NOT EXISTS claim SCHEMAFULL
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD claim_id ON TABLE claim TYPE string;
DEFINE FIELD title ON TABLE claim TYPE string;
DEFINE FIELD statement ON TABLE claim TYPE string;
DEFINE FIELD scope ON TABLE claim TYPE string;
DEFINE FIELD status ON TABLE claim TYPE string;
DEFINE FIELD confidence ON TABLE claim TYPE float;
DEFINE FIELD created_at ON TABLE claim TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_claim_claim_id_unique ON TABLE claim FIELDS claim_id UNIQUE;

-- ===== decision_event =====
DEFINE TABLE IF NOT EXISTS decision_event SCHEMAFULL
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD decision_id ON TABLE decision_event TYPE string;
DEFINE FIELD title ON TABLE decision_event TYPE string;
DEFINE FIELD question ON TABLE decision_event TYPE string;
DEFINE FIELD answer ON TABLE decision_event TYPE string;
DEFINE FIELD decision_type ON TABLE decision_event TYPE string;
DEFINE FIELD status ON TABLE decision_event TYPE string;
DEFINE FIELD scope ON TABLE decision_event TYPE string;
DEFINE FIELD confidence ON TABLE decision_event TYPE float;
DEFINE FIELD agent ON TABLE decision_event TYPE string;
DEFINE FIELD human_go ON TABLE decision_event TYPE bool;
DEFINE FIELD created_at ON TABLE decision_event TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_decision_event_decision_id_unique ON TABLE decision_event FIELDS decision_id UNIQUE;

-- ===== dependency_edge (generic graph) =====
DEFINE TABLE IF NOT EXISTS dependency_edge SCHEMAFULL
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD edge_id ON TABLE dependency_edge TYPE string;
DEFINE FIELD edge_type ON TABLE dependency_edge TYPE string;
DEFINE FIELD from_ref ON TABLE dependency_edge TYPE record;
DEFINE FIELD to_ref ON TABLE dependency_edge TYPE record;
DEFINE FIELD confidence ON TABLE dependency_edge TYPE float;
DEFINE FIELD created_at ON TABLE dependency_edge TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_dependency_edge_id_unique ON TABLE dependency_edge FIELDS edge_id UNIQUE;

-- ===== Graph Relations (TYPE RELATION) =====

-- artifact_cites_decision: cites vocabulary
DEFINE TABLE IF NOT EXISTS artifact_cites_decision TYPE RELATION
  FROM doc_page | doc_chunk
  TO decision_event
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD source ON TABLE artifact_cites_decision TYPE string;
DEFINE FIELD confidence ON TABLE artifact_cites_decision TYPE float;
DEFINE FIELD timestamp ON TABLE artifact_cites_decision TYPE datetime;
DEFINE FIELD hash ON TABLE artifact_cites_decision TYPE string;
DEFINE FIELD comment ON TABLE artifact_cites_decision TYPE string;
DEFINE FIELD created_at ON TABLE artifact_cites_decision TYPE datetime VALUE $value OR time::now();

-- chunk_mentions_symbol: mentions vocabulary
DEFINE TABLE IF NOT EXISTS chunk_mentions_symbol TYPE RELATION
  FROM doc_chunk
  TO code_symbol
  PERMISSIONS FOR select FULL, FOR create FULL, FOR update FULL, FOR delete FULL;
DEFINE FIELD source ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD confidence ON TABLE chunk_mentions_symbol TYPE float;
DEFINE FIELD timestamp ON TABLE chunk_mentions_symbol TYPE datetime;
DEFINE FIELD hash ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD mention_context ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD comment ON TABLE chunk_mentions_symbol TYPE string;
DEFINE FIELD created_at ON TABLE chunk_mentions_symbol TYPE datetime VALUE $value OR time::now();
