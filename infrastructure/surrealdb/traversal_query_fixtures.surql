-- =====================================================================
-- Traversal Query Fixtures — static contract tests for Issue #3423
-- These are NOT executable against a live DB in CI (no runtime).
-- They define the expected SurrealQL traversal syntax contract.
--
-- Guardrails:
-- - No productive DB connection needed
-- - No migration, no runtime changes
-- - No embedding / hybrid retrieval scope
-- - No MCP evidence contract scope
-- - LR remains NO-GO
-- =====================================================================

-- Forward traversal: artifact → cited decision
SELECT ->artifact_cites_decision->decision_event.*
FROM ONLY $artifact_id;

-- Backward traversal: decision ← supported by memory
SELECT <-memory_supports_decision<-agent_memory.*
FROM ONLY $decision_id;

-- Multi-hop: chunk → mentioned symbol → repo_artifact
SELECT ->chunk_mentions_symbol->code_symbol->repo_artifact.*
FROM ONLY $chunk_id;

-- Recursive traversal (known depth 3): artifact → decision chain
SELECT @.{3}->artifact_cites_decision->decision_event.*
FROM ONLY $artifact_id;

-- Bi-directional evidence chain: chunk → symbol ← chunks that mention it
SELECT ->chunk_mentions_symbol->code_symbol<-chunk_mentions_symbol<-doc_chunk.*
FROM ONLY $chunk_id;

-- Decision with supporting memory chain (multi-hop backward)
SELECT <-memory_supports_decision<-agent_memory->memory_supports_decision->decision_event.*
FROM ONLY $decision_id;

-- All artifacts citing a decision (forward from decision via backward traversal)
SELECT <-artifact_cites_decision<-repo_artifact.*
FROM ONLY $decision_id;
