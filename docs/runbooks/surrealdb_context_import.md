# SurrealDB Context Import - Local Runbook

**Status**: Draft
**Authority**: Issue #2077 / Wave 10 Parent #2067 / Epic #1976
**Scope**: Local/dev only. Document how to take Context Indexer JSONL artifacts through validate -> plan -> dry-run reconcile -> gated local-dev apply, with audit reports and tombstone-only delete semantics.

This runbook is **not** a production activation guide. It does not authorize live trading, does not change Live-Readiness, and does not enable a real SurrealDB write path.

---

## 1. Purpose and Scope

This runbook describes how to drive the Wave-10 Context Importer (`tools/surrealdb/context_importer.py`) end-to-end on a local/dev workstation:

- Take JSONL artifacts produced by the Context Indexer.
- Validate them as read-only input.
- Build a deterministic import plan.
- Reconcile the plan against an explicit local "existing records" snapshot in dry-run mode.
- Optionally execute a **gated, in-memory local-dev apply** with tombstone-only deletions.
- Inspect the audit report.

Out of scope for this runbook:

- Production SurrealDB activation.
- Default writes to any SurrealDB instance.
- Live-trading, risk, execution, governance, or runtime state.
- A real SurrealDB adapter (`real_surrealdb_adapter_available = false` in this slice).
- MCP bridge, Agent-Briefing engine, vector search, or query CLI (Wave 11+).

---

## 2. Non-Goals (Anti-Criteria)

This runbook explicitly does **not** establish or imply any of the following:

- No production default. The importer never reaches a real SurrealDB instance from this runbook.
- No default-write. `dry-run` is the default; `apply` is hard-gated.
- `apply` is local/dev only and requires multiple explicit flags.
- No trading-state, risk, execution, or governance tables are touched (forbidden-tables list is fail-closed).
- No Live-Readiness change. LR verdict remains **NO-GO** for live trading independent of this runbook.
- No Echtgeld-Go. Wave-10 completion does not authorize real capital.
- No real SurrealDB adapter is installed, registered, or selectable through CLI.
- No secrets, real tokens, or production URLs are used in any example.

If any of the steps below appear to require production credentials, a real SurrealDB endpoint, or a real network call, **stop**. The Wave-10 importer is intentionally local/dev only.

---

## 3. Prerequisites

Required:

- Python 3.12 (matches repo target; see `pyproject.toml`).
- Local repository checkout of `Claire_de_Binare` on a Wave-10 or later commit (Wave 10 anchor: #2067).
- A Context Indexer JSONL export under an approved repo-local directory (typically a `temp/` or `artifacts/` subtree). See `tools/surrealdb/context_indexer.py` and `docs/surrealdb/context-indexer-cli-contract.md`.
- The local-only example config: `infrastructure/config/surrealdb/context_import.local.example.yaml`.

Not required:

- Docker is **not** required for the dry-run / local-dev apply paths. The default adapter is in-memory and offline.
- A running SurrealDB instance is **not** required. The importer never opens a real network connection in this slice.
- No production secrets, no live API keys.

If you choose to run a local SurrealDB container later for Wave-11+ query work, that is **out of scope** here.

---

## 4. SurrealDB Local/Dev Posture

Even though no real SurrealDB is contacted, the importer parses URL/namespace/database arguments and validates them against config. Use only local/dev placeholders:

- `--surreal-url` and `surreal_url` in YAML must be a local/dev placeholder, e.g. `ws://127.0.0.1:8000/rpc`. Do not paste a production URL.
- Namespace must be the Context Intelligence namespace (the example config uses `cdb_ctx`).
- Database must be the Context Intelligence database (the example config uses `context`).
- Allowed tables are restricted to the Context-Intelligence record kinds (e.g. `code_symbol`, `config_reference`, `dependency_edge`, `doc_chunk`, `doc_code_link`, `doc_page`, `doc_section`, `import_reference`, `repo_artifact`, `test_case`).
- Forbidden tables (must never appear in `allowed_tables`) include trading-state and governance-mirror surfaces such as `balances`, `execution_state`, `fills`, `governance_decision`, `governance_event`, `governance_state`, `orders`, `pnl`, `positions`, `risk_state`.

If a config tries to widen `allowed_tables` into any forbidden table, the loader fails closed (Exit `5`).

Secrets must not be embedded in `infrastructure/config/surrealdb/context_import.local.example.yaml`. Real credentials, when ever needed (out of Wave-10 scope), come from the runtime environment / `SECRETS_PATH`, not from this YAML.

---

## 5. Step 1 - Produce a Context Indexer Export

Generate JSONL artifacts with the Context Indexer. This step is described in `docs/surrealdb/context-indexer-cli-contract.md`; the importer treats those JSONL files as read-only input.

Example (local/dev only):

```bash
# example, not production
python tools/surrealdb/context_indexer.py export-jsonl \
  --scope-config infrastructure/config/surrealdb/context_ingestion_scope.yaml \
  --output temp/context-index/run \
  --format json
```

Verify that `temp/context-index/run/` (or wherever you point the indexer) contains the per-table JSONL files (`doc_pages.jsonl`, `code_symbols.jsonl`, etc.).

---

## 6. Step 2 - Validate the JSONL Artifacts

Run the importer's read-only validation. No DB connection, no writes, no external calls.

Example:

```bash
# example, not production
python tools/surrealdb/context_importer.py validate-jsonl \
  --input-dir temp/context-index/run \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/import/validation.json
```

Notes:

- Exit `0` means "no blocking findings".
- Exit `1` means at least one blocking finding (e.g. malformed `record_id`, schema violation, secret-like content). Findings echo only the code and location, never the offending value.
- `--report-output` must resolve under `artifacts/` or `temp/`. Absolute paths and `..` traversal are rejected with Exit `5`.

---

## 7. Step 3 - Build a Deterministic Import Plan

Convert validated JSONL into a deterministic candidate plan. Still no DB calls.

Example:

```bash
# example, not production
python tools/surrealdb/context_importer.py plan \
  --input-dir temp/context-index/run \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/import/plan.json
```

The plan is determined by the input artifacts and is stable across runs with the same input.

---

## 8. Step 4 - Dry-Run Reconcile

Reconcile the plan against an explicit local "existing records" JSON fixture (or against an empty existing-state). This is dry-run only and never writes.

Existing-records fixture shape (read-only):

```json
{
  "records": [
    {
      "table": "doc_page",
      "record_id": "doc_page:page-id",
      "payload_hash": "lowercase-sha256-hex",
      "schema_version": "context-importer/v0"
    }
  ]
}
```

Example:

```bash
# example, not production
python tools/surrealdb/context_importer.py dry-run \
  --input-dir temp/context-index/run \
  --existing-records temp/context-index/existing.json \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/import/reconcile.json
```

The reconcile output classifies each candidate as `create`, `update`, `skip` (unchanged), or `tombstone_candidate` (present in existing snapshot, missing in new export).

---

## 9. Step 5 - Gated Local-Dev Apply (Optional)

Apply is **off by default** and requires four explicit flags simultaneously: `--apply`, `--apply-mode local-dev`, `--config`, plus `--input-dir` and `--run-id`. The default adapter is the **in-memory mock adapter**; no real SurrealDB instance is contacted, no real network is opened. Any missing gate yields Exit `5` (`WRITE_DENIED`).

Example:

```bash
# example, not production - in-memory adapter, no network
python tools/surrealdb/context_importer.py apply \
  --apply \
  --apply-mode local-dev \
  --config infrastructure/config/surrealdb/context_import.local.example.yaml \
  --input-dir temp/context-index/run \
  --existing-records temp/context-index/existing.json \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/apply/report.json \
  --audit-output artifacts/audit/apply.json
```

Important:

- `--apply-mode` accepts only `local-dev`. argparse rejects any other value.
- The importer reports `real_surrealdb_adapter_available: false` and `surrealdb_writes: in-memory-only` in the apply report.
- If the loaded config has `allow_apply_default: true`, the loader fails closed.
- Forbidden-table writes are blocked at config load time, not at apply time.

---

## 10. Step 6 - Tombstone Semantics

Wave-10 deletions are **tombstone-only**. There is no hard delete and no `delete`/`apply_delete` on the default adapter.

- A tombstone is recorded by writing the record's existing payload back with a tombstone metadata field (`tombstoned_at`, ISO8601 UTC) so all original payload fields are preserved.
- `tombstoned_at` is written by the runtime `SystemClock`. It is **not** affected by `--audit-generated-at`.
- The plan stage marks records as `tombstone_candidate`; the apply stage materializes them into adapter writes; the apply report exposes them as `op: tombstone`, `status: applied`, with the `tombstoned_at` timestamp.
- No record is physically removed by Wave 10. Recovery from a tombstone is therefore a metadata-level undo: the original payload remains addressable until a future curation step removes it. Wave-10 does not implement that curation step (see Section 12).

---

## 11. Step 7 - Inspect the Audit Report

`--audit-output` produces two artifacts in deterministic order:

- A JSON file at the given path (e.g. `artifacts/audit/apply.json`).
- A Markdown summary alongside (e.g. `artifacts/audit/apply.md`). When the JSON path already ends in `.md`, the Markdown sibling is written as `<path>.md` (e.g. `report.md` -> `report.md.md`) so the two artifacts never collide.

Audit fields to confirm:

- `schema_version: context-import-audit/v0`.
- `mode`: `plan`, `dry-run`, or `apply`.
- `run_id` matches the `--run-id` you passed.
- `counts`: metadata-only (`creates`, `updates`, `skips`, `tombstones`, etc.). No payload bodies are emitted.
- `generated_at`: deterministic when `--audit-generated-at` is passed; otherwise from `SystemClock`. This timestamp affects only the audit report and **never** apply payload timestamps such as `tombstoned_at`.
- `git_commit`: from `--git-commit` (test/CI injectable).
- `duration_ms`: non-negative; 0 if not provided.

Quick check (example):

```bash
# example, not production
python -c "import json; print(json.load(open('artifacts/audit/apply.json'))['mode'])"
```

---

## 12. Rollback / Recovery Notes

Wave 10 does **not** ship an automated rollback implementation. The `rollback-plan` subcommand is present as a stub (`scaffold-ack`, Exit `0`) and is explicitly out of scope for this wave.

Operational guidance for Wave-10 local/dev runs only:

- Keep the pre-apply existing-records snapshot file (`--existing-records ... .json`). Combined with the import plan and apply report, this is sufficient evidence to reason about what was tombstoned.
- Because deletions are tombstone-only, the original payload remains in the adapter state and can be re-affirmed by re-applying the prior export.
- Any production rollback / undo design is deferred to a separate Wave (`rollback-plan` generation, real SurrealDB adapter, durable backups). Do not invent or claim it here.

---

## 13. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Exit `1` on `validate-jsonl` / `plan` / `dry-run` | Blocking findings present (schema, malformed `record_id`, forbidden-table reference, secret-like content) | Inspect `--report-output` JSON; the `findings` list contains the codes and locations. Fix the indexer export or the existing-records fixture and re-run. |
| Exit `2` | argparse / CLI usage error | Re-check the subcommand and flags. Use `python tools/surrealdb/context_importer.py --help`. |
| Exit `3` | Input or config file not found | Verify the path passed to `--input-dir`, `--config`, `--existing-records`, or `--report-output` directory. |
| Exit `5` (`WRITE_DENIED`) on a non-`apply` subcommand | `--apply` was passed on a subcommand that is not `apply` | Drop `--apply` everywhere except the `apply` subcommand. |
| Exit `5` on `apply` | One of the required gates is missing: `--apply`, `--apply-mode local-dev`, `--config`, `--input-dir`, `--run-id` | Add the missing gate. All five must be present for apply to proceed. |
| Exit `5` with path-related code | `--report-output` or `--audit-output` is an absolute path, contains `..`, or resolves outside `artifacts/` and `temp/` | Use a path relative to the repo root under `artifacts/` or `temp/`. |
| Apply runs but writes seem to vanish | Default adapter is in-memory and process-local. There is no real SurrealDB persistence. | This is expected. Wave 10 ships an in-memory adapter only (`real_surrealdb_adapter_available: false`). |
| `run_id` missing | `--run-id` not passed where required | Provide a non-empty `--run-id`. The validator rejects missing/empty run ids on read-only validation when run-id consistency is checked. |
| `record_id` rejected as malformed | The JSONL artifact violates `table:id` shape or table prefix mismatch | Fix the indexer export. The importer does not silently coerce record IDs. |
| Config validation fails | `allow_apply_default: true`, missing `allowed_tables`, or a forbidden table is allow-listed | Use `infrastructure/config/surrealdb/context_import.local.example.yaml` as a template and keep `allow_apply_default: false`. |
| `--audit-output foo.md` produced unexpected files | Markdown sibling is appended (`foo.md.md`) so the JSON artifact at `foo.md` is not overwritten | Both files are intentional; the JSON artifact is at the requested path, the Markdown render is at `<path>.md`. |
| Hangs / network errors | Should not occur in this slice; default adapter is offline | Confirm you are on the local-dev path. There is no production SurrealDB code path in Wave 10. |

---

## 14. Example Command Bundle

All examples below are local/dev illustrations. None of them are production commands. None of them require Docker or a live SurrealDB instance.

```bash
# example, not production - validate
python tools/surrealdb/context_importer.py validate-jsonl \
  --input-dir temp/context-index/run \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/import/validation.json

# example, not production - plan
python tools/surrealdb/context_importer.py plan \
  --input-dir temp/context-index/run \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/import/plan.json

# example, not production - dry-run reconcile
python tools/surrealdb/context_importer.py dry-run \
  --input-dir temp/context-index/run \
  --existing-records temp/context-index/existing.json \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/import/reconcile.json \
  --audit-output artifacts/audit/dry-run.json

# example, not production - gated local-dev apply (in-memory adapter)
python tools/surrealdb/context_importer.py apply \
  --apply \
  --apply-mode local-dev \
  --config infrastructure/config/surrealdb/context_import.local.example.yaml \
  --input-dir temp/context-index/run \
  --existing-records temp/context-index/existing.json \
  --run-id wave10-local-dev-1 \
  --report-output artifacts/apply/report.json \
  --audit-output artifacts/audit/apply.json

# example, not production - audit emit (read-only mode)
python tools/surrealdb/context_importer.py audit \
  --input-dir temp/context-index/run \
  --audit-mode dry-run \
  --run-id wave10-local-dev-1 \
  --audit-output artifacts/audit/wave10-dry-run.json
```

---

## 15. Closing Reminder

- These commands are **examples**. Run them only against local/dev artifacts.
- The importer never opens a real network connection in Wave 10.
- Live-Readiness remains `NO-GO`. Wave-10 completion does not change Echtgeld posture.
- Real SurrealDB adapter, real persistence, automated rollback, and query CLI are all separate, future-wave work and must not be implied by Wave-10 evidence.
