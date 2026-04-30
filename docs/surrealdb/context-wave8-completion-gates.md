# Context Intelligence - Wave 8 Completion Gates

**Status**: Draft
**Authority**: Issue #2054 / Parent #2044 / Epic #1976
**Scope**: Local-only context indexer implementation and validation (no SurrealDB runtime activation)

---

## 1. Purpose

This document defines completion gates for Wave 8 of the SurrealDB Context Intelligence roadmap.
Wave 8 delivers a deterministic, dry-run-first context indexer pipeline for repository context artifacts.

Wave-8 completion is not a live-trading, live-readiness, or production SurrealDB authorization.

---

## 2. Guardrails (Anti-Criteria)

Wave 8 is not complete if any of the following occur:

- SurrealDB production activation or production import path is introduced.
- Default SurrealDB writes are enabled.
- Runtime, trading, risk, or execution behavior is changed.
- Secrets or trading/runtime state are ingested or emitted in exports.
- Live-Readiness or Echtgeld GO is inferred from Wave-8 implementation status.

If any anti-criteria are violated, stop and split scope before merge.

---

## 3. Gate Checklist (MUST)

Wave 8 is complete when all Wave-8 implementation slices are present and validated:

- [ ] #2047 Discovery and classification produce deterministic included/skipped/forbidden output records.
- [ ] #2048 Deterministic hashing records stable `artifact_id`, `raw_sha256`, and `normalized_sha256` metadata.
- [ ] #2049 Markdown chunking produces deterministic `doc_page`, `doc_section`, and `doc_chunk` records with heading context and adjacency links.
- [ ] #2050 JSONL export writes the expected artifact files under approved repo-local output roots only.
- [ ] #2051 Snapshot output includes run metadata, counts, JSONL references, and validation summaries.
- [ ] #2052 Validation emits blocking/warning/info findings and returns non-zero on blocking findings.
- [ ] #2053 Unit tests and fixtures cover CLI contract behavior and core pipeline semantics without Docker or SurrealDB.
- [ ] #2233 output-path safety semantics remain present: `OutputPathOutsideAllowedRootsError`, `output_path_outside_allowed_roots`, approved-root symlink containment, child-path symlink escape blocking, and structured write-time filesystem errors.

---

## 4. Required Validation Commands

Minimum Wave-8 validation evidence:

- `pytest -q tests/unit/surrealdb/test_context_indexer.py`
- `ruff check tests/unit/surrealdb/test_context_indexer.py tools/surrealdb/context_indexer.py`
- `python tools/surrealdb/context_indexer.py --help`
- `python tools/surrealdb/context_indexer.py scan --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml --dry-run --format json`
- `python tools/surrealdb/context_indexer.py plan --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml --dry-run --format json`
- `python tools/surrealdb/context_indexer.py snapshot --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml --dry-run --format json`

Optional extended validation (recommended before PR ready):

- `python tools/surrealdb/context_indexer.py export-jsonl --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml --dry-run --format json`
- `python tools/surrealdb/context_indexer.py validate --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml --dry-run --format json`

---

## 5. Completion Evidence Requirements

Wave 8 closeout evidence should include:

- Final branch state against `origin/main`.
- List of touched Wave-8 files.
- Test and lint command outputs.
- Confirmation that outputs and write behavior remain constrained to approved roots.
- Explicit statement that Live-Readiness remains `NO-GO`.

Issue #2044 is the durable checkpoint ledger for this wave.

---

## 6. Handoff

After all Wave-8 gates pass, Wave 9+ work can build on the context indexer output surface for higher-order extraction and ingestion workflows.
Wave-8 completion does not authorize production activation or runtime integration by itself.
