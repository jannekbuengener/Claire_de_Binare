# Session Log: #2604 CLI Chain Smoke Slice 2

**Date:** 2026-05-29  
**Issue:** #2604 (Epic — SurrealDB Context Intelligence CLI Tools)  
**Branch:** `feat/2604-cli-chain-smoke-slice2`  
**LR:** NO-GO (unchanged)  
**Board stage:** trade-capable (orthogonal; no live capital)

## Scope

Prove the CLI chain `indexer → JSONL export → importer validate/plan/dry-run/apply → query → explain-source`
end-to-end against the real local SurrealDB runtime from #2603. BLUE/RED read-only; no trading/live/MCP changes.
#2604 not closed. #2603 read as runtime prerequisite; #2605/#2606 context only.

## Runtime prerequisite (read-only proof of #2603)

| Step | Result |
|------|--------|
| `make context-env-check` | PASS (credentials redacted) |
| `make context-up` / `context-status` | `cdb_surrealdb` healthy, 127.0.0.1:8010 |
| `make context-schema-check` | PASS, exit 0 |
| BLUE/RED baseline | 27 containers (26 BLUE/RED + `cdb_surrealdb`) |

## Indexer (smoke scope)

- Scope: `infrastructure/config/surrealdb/context_ingestion_scope.smoke.yaml` (docs/knowledge/agents + README; no code).
- `run_id = context-indexer-8d9e14a17cbb30b4`, `state_hash = 8d9e14a1…` — **reproducible** across re-scan (same git commit → same hashes).
- Counts: included=734, skipped=62, forbidden=690; artifacts=734, pages=612, sections=8279, chunks=8295,
  **code_symbols=0** (expected — smoke scope excludes code), config_refs=3231, doc_code_links=5823, dependency_edges=5823.
- JSONL valid; `forbidden_files.jsonl` carries metadata only (path/reason/size/sensitivity), **no secret content**.
- No oversized/noise/archive paths ingested.

## Importer (fail-closed gating)

| Step | Result |
|------|--------|
| `validate-jsonl` | PASS |
| `plan` (run twice) | deterministic (identical plan) |
| `dry-run` reconcile | PASS, 0 blocking |
| `apply` WITHOUT `--apply --apply-mode local-dev` | **fail-closed (exit 5, WRITE_DENIED)** |

## Local apply (gated, real adapter)

- `make context-import-local` (after Makefile fix below) → **exit 0**, ~21 min (large smoke corpus; sequential HTTP upserts).
- Evidence: `status=applied`, `apply_executed=true`, `real_surrealdb_adapter_available=true`,
  `surrealdb_connection=local-http-api`, `surrealdb_writes=local-db-writes`,
  `reconcile_status=reconciled`, `actions=32797`, `blocking=0`, `failed=0`, `skipped=0`, `creates=26974`.
- `creates=26974` vs `actions=32797` delta = `dependency_edge=5823` reconciled as already-present no-ops from prior local-dev smoke runs (idempotent upsert). No productive DB writes.

## Query + provenance (real reads, `--adapter surrealdb-local --hard-mode`)

| Command | Result |
|---------|--------|
| `find-artifact --source-path README` | `source=surrealdb-local`, count=2; provenance: `source_path`, `normalized_sha256`, `source_commit`, `source_hash`, `raw_sha256`, `integrity_algo` |
| `find-doc --query SurrealDB` | `source=surrealdb-local`, count=3 |
| `find-symbol --name Manager` | `source=surrealdb-local`, count=0 (valid empty read — no code in smoke scope) |
| `trace --source-path … --direction up/down` | `source=surrealdb-local`, status=ok (read path proven) |
| `explain-source --artifact-id repo_artifact:…` | `source=surrealdb-local`, count=1; provenance includes `run_id`, `source_commit=67a3665d…` (matches indexer snapshot), `source_path`, `source_hash`, `chunk_id`, `edge_id`, `symbol_id` |

`source=surrealdb-local` appears only on real DB reads; provenance fields present per contract.

## Cross-CLI smoke

- `context-smoke-db` (Makefile L449–481) already wraps schema-check → scan(smoke) → apply(surrealdb-local) → `show-snapshot --min-count 1`.
- Its fail-closed acceptance gate executed standalone: **PASS** (exit 0, `source=surrealdb-local`, count=100, min-count=1 enforced).
- All wrapped stages independently proven this session ⇒ **no real gap; no new target/test added** (reuse-first per clarification).

## Fixes (in-scope, minimal)

1. **Makefile `context-import-local`** — resolve `--run-id` at recipe runtime from `$(CONTEXT_SNAP_DIR)/snapshot.json`
   (Windows `pwsh` + POSIX branch), mirroring the #2603 `context-smoke-db` fix. Prior parse-time `$(shell gen_run_id.py)`
   produced a timestamp run_id → `run_id_mismatch` blocking apply.
2. **Runbook `docs/runbooks/surrealdb_context_import.md`** — `--output-dir` → `--output` (indexer rejects `--output-dir`, would exit 2).
3. **Test `tests/unit/surrealdb/test_surrealdb_local_apply_adapter.py`** — Makefile-parser now skips `ifeq/else/endif`
   conditional directives so the `--adapter surrealdb-local` assertion survives the new Windows/POSIX branch structure.

## Findings (candidate follow-up)

- **Query statement normalizer uppercases string literals.** `find-artifact --file-type md` → `WHERE FILE_TYPE = "MD"` (0 hits vs lowercase-stored `md`);
  `find-symbol --name apply` → **false `WRITE_DENIED`** (search term `apply` upcased to `APPLY` collides with write-keyword denylist);
  `trace --source-path docs/` misses lowercase paths. Read path + classification guardrail work; the literal-casing is the defect.
  Scope-relevant to #2604 but a classifier change is non-trivial → dedup follow-up rather than in-slice fix.
- **Apply runtime** ~21 min for the 734-doc smoke corpus (32,797 sequential HTTP upserts) — known characteristic also noted in #2603.

## Teardown

| Step | Result |
|------|--------|
| `make context-down` | `cdb_surrealdb` stopped; 27 → 26 containers |
| BLUE/RED isolation | intact (postgres/redis/risk/execution/market + exporters untouched) |
| `pytest -q tests/unit/surrealdb` | green after test fix (1266 passed) |

## Verdict

CLI chain proven end-to-end against real local SurrealDB. LR stays **NO-GO**. #2604 remains open.
