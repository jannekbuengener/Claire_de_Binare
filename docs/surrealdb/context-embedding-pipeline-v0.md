# Context Embedding Pipeline v0

**Status**: Contract Defined
**Issue**: #3486
**Parent**: #3479
**Builds on**: #3484
**Follow-up kept open**: #3487

This document defines the repo-only vector / embedding pipeline contract for CDB
Context Brain. It is a canon / contract surface, not a productive rebuild, not a
runtime authorization, and not a SurrealDB write instruction.

## Purpose

The purpose of #3486 is to make the embedding pipeline machine-readable before any
later runtime implementation:

- target records are **real CDB chunks**
- the vector field is `doc_chunk.embedding`
- the embedding source must be defined explicitly
- `model_id` is required metadata
- vector dimension is `1536`
- rebuild rules must be explicit before any future pipeline execution

## Non-Goals

- no productive DB writes
- no productive SurrealDB queries
- no runtime rebuild
- no LR-Go
- no Live-Go
- no Echtgeld-Go
- no secrets
- no delivery of #3487 hybrid retrieval follow-up

## Canonical contract

### Canon status

- This file is a contract / canon for #3486.
- It does not prove a populated database.
- It does not authorize MCP mutation or any productive workflow.
- No DB-backed claim is allowed without Tool/Query/Record evidence.

### Target object

| Field | Contract |
| --- | --- |
| logical object | `doc_chunk` |
| vector field | `doc_chunk.embedding` |
| chunk source | `real CDB chunks` |
| embedding dimension | `1536` |
| required metadata | `model_id` |
| optional metadata | chunk content hash, source hash, created_at, updated_at |

### Required metadata rules

The following metadata is required for any future compliant vector rebuild:

1. `model_id` must be present for every embedding batch.
2. `embedding source` must be declared as the canonical generator definition for the
   batch that produced `doc_chunk.embedding`.
3. `1536` is the required dimension for the current repo contract.
4. Any future runtime that cannot prove `model_id` and dimension consistency must
   treat the vector state as stale.

### Rebuild rules

The rebuild contract is defined even though this repo slice performs no rebuild.

Rebuild is required when one of the following changes:

- `model_id`
- embedding source implementation
- chunking contract that changes chunk boundaries
- source hash / content hash for the underlying documentation chunk
- vector dimension contract

### Stale / drift conditions

Vector state must be treated as stale or drifted when:

- `doc_chunk.embedding` is missing
- `model_id` is missing
- stored dimension is not `1536`
- chunk content changes without a matching embedding refresh
- rebuild rules changed but stored vectors were not regenerated

## Repo anchors for #3486

The repo-only discoverability surfaces for this contract are:

- `knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md`
- `docs/onboarding/repo_brain_context_intelligence.md`
- `infrastructure/surrealdb/context_intelligence_v0.surql`
- `infrastructure/surrealdb/hybrid_retrieval_fixtures.surql`
- `tools/surrealdb/graph_vector_proof_cli.py`

`infrastructure/surrealdb/hybrid_retrieval_fixtures.surql` remains a fixture surface.
It is not productive query evidence.

## Proof boundaries

`tools/surrealdb/graph_vector_proof_cli.py` may describe the vector pipeline contract
in machine-readable form, but repo output remains bounded:

- no DB-backed claim without Tool/Query/Record evidence
- no productive DB writes
- no productive embedding generation
- no runtime rebuild
- no LR-/Live-/Echtgeld-Freigabe

## Scope boundary

- #3479 remains open as the parent roadmap.
- #3484 remains the graph discoverability anchor this contract builds on.
- #3486 defines the vector / embedding pipeline contract only.
- #3487 remains out of scope as the later hybrid retrieval follow-up.
