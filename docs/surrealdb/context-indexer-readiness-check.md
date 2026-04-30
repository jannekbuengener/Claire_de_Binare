# Context Indexer Implementation Preconditions

**Status**: Draft precondition document
**Authority**: Issue #2044 / Issue #2045 / Epic #1976
**Target**: `tools/surrealdb/context_indexer.py` (future implementation slice #2045)
**Scope**: Docs-only readiness guidance; no implementation and no Wave 8 execution GO

---

## 1. Purpose

This document records the current preconditions and open gates for a future #2045 Context Indexer CLI scaffold.

It is only a readiness/precondition document. It does not implement #2045, authorize #2045 implementation, authorize #2046, authorize SurrealDB import/apply, or authorize Wave 8 execution. A separate human review and implementation GO remain required.

---

## 2. Canon Alignment

- #1976 remains the master anchor for the Context Intelligence issue tree and guardrails.
- GitHub live state and current `main` evidence win over stale issue prose or local notes.
- `docs/surrealdb/context-indexer-cli-contract.md` is the landed #1989 CLI contract.
- `docs/surrealdb/context-ingestion-scope.md` is the landed #1986 ingestion-scope canon.
- Live-Readiness remains `NO-GO`.
- Board stage `trade-capable` is not a Live-Readiness GO.

---

## 3. Gate Checklist (Pre-Implementation)

| # | Requirement | Validation method | Status |
|---|-------------|-------------------|--------|
| R1 | CLI contract (#1989) is landed | Review `docs/surrealdb/context-indexer-cli-contract.md` | CLOSED / COMPLETED |
| R2 | Agent handoff guide (#2040) is landed | Review `docs/surrealdb/context-agent-handoff.md` | CLOSED / COMPLETED |
| R3 | Machine-readable scope config (#2046) exists | Wait for `infrastructure/config/surrealdb/context_ingestion_scope.yaml` to land via #2046 | BLOCKING / PENDING #2046 |
| R4 | No DB runtime connection in scaffold | Code review gate for #2045 | PENDING #2045 |
| R5 | Read-only / dry-run-first default | Code review gate for #2045 | PENDING #2045 |

#2045 must not assume a landed machine-readable scope config until #2046 is closed with the tracked config file present on `main`.

---

## 4. Guardrails for Future #2045 Work

Any later #2045 implementation must satisfy these guardrails:

1. **No DB write**: no SurrealDB write, import, apply, or reconcile side effect is allowed in the #2045 scaffold.
2. **No SurrealDB runtime activation**: the scaffold must not connect to production SurrealDB or enable production ingestion.
3. **No secrets export**: the indexer must not export secret contents. Findings must fail closed or be represented as blocked/omitted according to the CLI contract.
4. **Deterministic scan identity**: hashing and artifact identity must follow the landed CLI contract, using repo-relative paths, normalized content, and stable contract/schema semantics. Timestamps must never be part of the identity/hash basis.
5. **Output path safety**: file writes are allowed only with explicit `--apply-writes` plus explicit `--output`.
6. **Approved output roots**: output paths must stay under `artifacts/` or `temp/`; `tmp/context-indexer/` is not an approved path in this readiness document.
7. **Path traversal protection**: absolute paths, drive-prefixed paths, UNC paths, and normalized paths escaping the approved output roots must stop with `5 write denied` as defined by the CLI contract.

---

## 5. Conditional Validation Plan for #2045

These checks are for a future #2045 implementation and are conditional on the relevant prerequisites being landed.

Before #2046 lands, #2045 may only reference the pending scope-config path as a dependency:

- `infrastructure/config/surrealdb/context_ingestion_scope.yaml` (pending #2046)

After #2046 lands and #2045 is separately approved for implementation, the scaffold should pass at least:

1. `python tools/surrealdb/context_indexer.py --help`
2. `python tools/surrealdb/context_indexer.py scan --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml --dry-run`
3. **Determinism test**: two scans on the same commit produce identical hashes/artifact identities.
4. **Security test**: scanning a file containing a fake secret does not export the secret content and fails closed or marks the finding as blocked/omitted.
5. **Path traversal test**: a write-capable command using `--apply-writes --output ../../etc/passwd` stops with `5 write denied`.

---

## 6. Explicit Non-Goals

- No #2045 implementation is included here.
- No #2046 implementation is included here.
- No machine-readable scope config is added here.
- No CLI scaffold is added here.
- No SurrealDB import/apply is authorized here.
- No runtime, trading, risk, execution, or Live-Readiness surface is changed here.
- No Wave 8 implementation GO is implied here.

---

## 7. Handoff

This readiness check preserves the #2045 precondition checklist and validation plan while keeping open gates explicit. It does not replace separate implementation approval, human review, or the repository write gates.
