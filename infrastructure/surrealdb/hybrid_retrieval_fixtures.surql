-- =====================================================================
-- Hybrid Retrieval Query Fixtures — static contract tests for Issue #3424
-- These are NOT executable against a live DB in CI (no runtime).
-- They define the expected SurrealQL retrieval syntax contract.
--
-- Sources:
--   SurrealDB Search functions (docs/reference/query-language/functions/database-functions/search)
--   SurrealDB Vector indexes (docs/learn/data-models/vector-search/vector-indexes)
--   SurrealDB Hybrid search (docs/learn/data-models/vector-search/hybrid-search)
--
-- Schema dependencies (Issue #3422):
--   idx_doc_chunk_embedding_hnsw — HNSW DIMENSION 1536 DIST COSINE
--   idx_doc_chunk_content_ft — FULLTEXT ANALYZER cdb_code_analyzer BM25 HIGHLIGHTS
--
-- Guardrails:
--   - No productive DB connection needed
--   - No embedding generation (embedding vectors are query parameters only)
--   - No migration, no runtime changes
--   - No MCP evidence contract scope
--   - Does NOT replace the existing Python hybrid ranking
--   - LR remains NO-GO
-- =====================================================================

-- -----------------------------------------------------------------------
-- BM25 Full-text Search Query
-- Searches doc_chunk.content using the FULLTEXT BM25 index.
-- SurrealQL syntax: @N@ matches operator + search::score(N)
-- -----------------------------------------------------------------------
-- Reference: search::score() — returns BM25 relevance score
--   SELECT id, search::score(1) as score FROM doc_chunk
--   WHERE content @1@ 'keyword' ORDER BY score DESC LIMIT $limit;

LET $bm25_keyword = 'policy_hash';
LET $bm25_limit = 10;

SELECT
    id,
    chunk_id,
    content,
    content_hash,
    page_ref,
    search::score(1) AS bm25_score
FROM doc_chunk
WHERE content @1@ $bm25_keyword
ORDER BY bm25_score DESC
LIMIT $bm25_limit;

-- -----------------------------------------------------------------------
-- Vector Similarity Search Query
-- Searches doc_chunk.embedding using HNSW approximate KNN.
-- SurrealQL syntax: embedding <|K, EF|> $vector
--   WHERE embedding <|$k, $ef|> $query_vector
--   vector::distance::knn() returns the computed distance
-- -----------------------------------------------------------------------
-- Reference: Vector indexes — HNSW KNN operator
--   SELECT id, vector::distance::knn() AS dist FROM doc_chunk
--   WHERE embedding <|10, 40|> $qvec

LET $query_vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
    0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20];
LET $k = 10;
LET $ef = 40;

SELECT
    id,
    chunk_id,
    content,
    content_hash,
    vector::distance::knn() AS vector_distance
FROM doc_chunk
WHERE embedding <|$k, $ef|> $query_vector
ORDER BY vector_distance ASC;

SELECT
    id,
    chunk_id,
    content,
    content_hash,
    1.0 - vector::distance::knn() AS vector_score
FROM doc_chunk
WHERE embedding <|$k, $ef|> $query_vector
ORDER BY vector_score DESC;

-- -----------------------------------------------------------------------
-- Hybrid Retrieval Contract: RRF (Reciprocal Rank Fusion)
-- Fuses BM25 full-text results with vector similarity results.
-- SurrealQL syntax: search::rrf([$list1, $list2], $limit, $k)
--
-- RRF formula: rrf_score = Sum 1 / (k + rank_in_list)
-- k = 60 (standard default per Cormack et al. 2009)
-- Tie-breaker: rrf_score DESC, then id ASC
--
-- Result contract fields: id, rrf_score (fuse_score),
--   plus source fields from the first non-null source per list order
-- -----------------------------------------------------------------------
-- Reference: Hybrid search — search::rrf()
--   search::rrf([$vs, $ft], 2, 60);

LET $hybrid_limit = 10;
LET $rrf_k = 60;

LET $vs = SELECT
    id,
    chunk_id,
    content_hash
FROM doc_chunk
WHERE embedding <|$hybrid_limit, $ef|> $query_vector;

LET $ft = SELECT
    id,
    chunk_id,
    content_hash,
    search::score(1) AS bm25_score
FROM doc_chunk
WHERE content @1@ $bm25_keyword
ORDER BY bm25_score DESC
LIMIT $hybrid_limit;

SELECT * FROM search::rrf([$vs, $ft], $hybrid_limit, $rrf_k);

-- -----------------------------------------------------------------------
-- Hybrid Retrieval Contract: Linear Fusion (alternative)
-- Weighted linear fusion with minmax normalization.
-- SurrealQL syntax: search::linear([$list1, $list2], [w1, w2], limit, 'minmax')
-- -----------------------------------------------------------------------
SELECT * FROM search::linear([$vs, $ft], [1, 1], $hybrid_limit, 'minmax');

-- -----------------------------------------------------------------------
-- Result Contract
--
-- Each hybrid retrieval result contains:
--   id:            record id (SurrealDB native)
--   rrf_score:     fused score from RRF (fuse_score in output)
--   chunk_id:      deterministic chunk identifier
--   content_hash:  SHA256 of chunk content
--   bm25_score:    BM25 relevance score (if from full-text list)
--   vector_distance / vector_score: vector similarity (if from vector list)
--   source fields: first non-null from list order
--
-- Note: Embedding vectors are query parameters only.
-- No embedding generation, storage, or runtime is defined here.
-- The existing Python hybrid ranking (hybrid_retrieval_ranking.py) is
-- a parallel reference and is NOT replaced by this contract.
-- =======================================================================
