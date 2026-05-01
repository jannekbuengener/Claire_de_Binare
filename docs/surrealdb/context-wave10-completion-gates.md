# Context Intelligence - Wave 10 Completion Gates

**Status**: Draft
**Authority**: Issue #2078 / Wave 10 Parent #2067 / Epic #1976
**Scope**: Local/dev SurrealDB Context Importer (validate -> plan -> dry-run reconcile -> gated local-dev apply -> tombstones -> audit). No production SurrealDB activation, no runtime trading change, no Live-Readiness change.

This document defines the closure conditions for Wave 10 of the SurrealDB Context Intelligence roadmap. Wave-10 completion is not a live-trading, Live-Readiness, or Echtgeld authorization. It does not introduce a real SurrealDB write path.

---

## 1. Wave 10 Scope

Wave 10 delivers a deterministic, dry-run-first, locally-gated context import pipeline driving Context Indexer JSONL output through the importer to an in-memory adapter, with audit reports, tombstone-only deletions, and tests/fixtures.

In scope (delivered across the Wave-10 issue set below):

- A CLI scaffold for `tools/surrealdb/context_importer.py` with safe defaults.
- Local/dev configuration loading with fail-closed validation.
- Read-only JSONL artifact validation.
- Deterministic import plan generation.
- Dry-run reconcile against an explicit local existing-records snapshot.
- Gated local-dev apply with the in-memory mock adapter only.
- Tombstone-only deletion semantics with payload-field retention.
- Deterministic audit report (JSON + Markdown sibling).
- Unit tests, fixtures, and a local import runbook.

Out of scope (deferred to later waves):

- Real SurrealDB adapter / production write path.
- Production SurrealDB activation, default writes, or any runtime trading change.
- Query CLI / SurrealDB query layer (Wave 11+).
- Automated rollback-plan generation (stub only in Wave 10).
- MCP bridge, Agent-Briefing engine, vector search.

---

## 2. Wave 10 Issue Matrix

Each Wave-10 issue maps to a delivered slice. Status reflects merged-into-`main` evidence at the time this document is authored.

| Issue | Title | Status | Delivered slice |
|---|---|---|---|
| #2068 | Context importer CLI scaffold | merged | Argument parsing, help text, dry-run default, fail-closed `--apply` and `apply` (Exit `5`), output-path whitelist. |
| #2069 | Local SurrealDB context connection config | merged | Explicit YAML config loader (`context_import.local.example.yaml`); fail-closed `allow_apply_default=false`; allowed-/forbidden-tables enforcement; no secrets in YAML. |
| #2070 | JSONL artifact validation before import | merged | Read-only `validate-jsonl` with schema, `record_id` and per-table checks; secret-redaction in findings; Exit `0` clean / Exit `1` with blocking findings. |
| #2071 | Deterministic SurrealDB import plan | merged | `plan --input-dir` produces a stable candidate plan from validated artifacts; no DB calls. |
| #2072 | Dry-run reconcile against SurrealDB | merged | `dry-run --input-dir` reconciles plan against an explicit read-only existing-records JSON fixture or empty state; classifies create / update / skip / tombstone_candidate. |
| #2073 | Explicit local apply mode | merged | `apply` subcommand gated on `--apply` + `--apply-mode local-dev` + `--config` + `--input-dir` + `--run-id`; default in-memory adapter; no production SurrealDB and no real network. |
| #2074 | Tombstone handling | merged | Tombstone-only deletions with payload-field retention; `tombstoned_at` written by runtime `SystemClock`; injectable clock for tests; no hard-delete API. |
| #2075 | Context import audit report | merged | Audit schema `context-import-audit/v0` for plan/dry-run/apply; metadata-only counts; injectable `generated_at`/`duration_ms`/`git_commit`; JSON + Markdown sibling artifacts; audit clock isolated from apply payload timestamps. |
| #2076 | Tests and fixtures for importer | merged | `tests/unit/surrealdb/test_context_import_audit.py` + 11 minimal JSONL fixtures and an `existing_mixed.json`; full `tests/unit/surrealdb/` suite is green locally. |
| #2077 | Local import runbook | this PR | `docs/runbooks/surrealdb_context_import.md`. |
| #2078 | Wave-10 completion gates | this PR | this document. |

---

## 3. PR / Merge-Commit Matrix

| Issue(s) | PR | Merge commit |
|---|---|---|
| #2068 | #2239 | `6b9167bd012d705f0cb802e1bcd6ba7646972e11` |
| #2069 | #2242 | `240035f4b17fbce39c2a64eb7010a6d0f6e553e3` |
| #2070 | #2243 | `d69b62f76b4f282a1c253cd7032278b43949550d` |
| #2071 | #2244 | `4a83a0b4d2299761f75cb1b413072186f6aa631a` |
| #2072 | #2247 | `7b0bbd87fff67ab4301d9d4b8d8fc8659732cea7` |
| #2073, #2074 | #2248 | `4f4a72e71d094df813bdfc297237aa5e998b4baa` |
| #2075, #2076 | #2249 | `5e564c9b42dc9e044e72c0d9ab2b7b83540d53d5` |
| #2077, #2078 | this PR | (assigned at merge) |

---

## 4. Completion Checklist (MUST)

Wave 10 is complete when **all** of the following are true:

- [x] Context Importer CLI scaffold exists in `tools/surrealdb/context_importer.py` with safe defaults and fail-closed `--apply` / `apply` semantics. (#2068 / PR #2239)
- [x] Local/dev configuration exists at `infrastructure/config/surrealdb/context_import.local.example.yaml` and is loaded only with explicit `--config`. (#2069 / PR #2242)
- [x] JSONL validation works for the per-table artifacts produced by the Context Indexer; blocking findings yield Exit `1`; no secret values are echoed. (#2070 / PR #2243)
- [x] Deterministic import plan works: `plan --input-dir` returns a stable plan that depends only on the input artifacts. (#2071 / PR #2244)
- [x] Dry-run reconcile works: `dry-run --input-dir [--existing-records ...]` classifies create / update / skip / tombstone_candidate without DB calls. (#2072 / PR #2247)
- [x] Explicit apply mode works on the in-memory adapter only, requires all of `--apply` + `--apply-mode local-dev` + `--config` + `--input-dir` + `--run-id`, otherwise Exit `5`. (#2073 / PR #2248)
- [x] Tombstone handling works: deletions are tombstone-only with payload-field retention; `tombstoned_at` from runtime `SystemClock`; no hard-delete API. (#2074 / PR #2248)
- [x] Audit report exists: schema `context-import-audit/v0` for plan / dry-run / apply; deterministic JSON + Markdown sibling; audit clock cannot mutate apply payload timestamps. (#2075 / PR #2249)
- [x] Tests and fixtures exist under `tests/unit/surrealdb/` and `tests/fixtures/surrealdb/context_importer/`. (#2076 / PR #2249)
- [x] Local import runbook exists at `docs/runbooks/surrealdb_context_import.md`. (#2077 / this PR)
- [x] Wave-10 completion gates document exists at `docs/surrealdb/context-wave10-completion-gates.md`. (#2078 / this PR)

---

## 5. Anti-Criteria (Wave-10 closure must not violate any)

Wave 10 is **not** complete - and PRs claiming Wave-10 closure must be rejected - if any of the following appear:

- Default writes to any SurrealDB instance.
- Production SurrealDB activation or a registered real SurrealDB adapter on the CLI.
- Any runtime, trading, risk, execution, or governance behavior change.
- Trading-state or governance-mirror tables added to `allowed_tables`.
- Removal or weakening of the `allow_apply_default: false` invariant in the loaded config.
- A hard-delete code path on the apply boundary (only tombstones are allowed).
- Inference of Live-Readiness GO from Wave-10 implementation status.
- Inference of Echtgeld GO from Wave-10 implementation status.
- Introduction of an MCP bridge, Agent-Briefing engine, or vector search as part of Wave-10 closure.
- Docker as a hard requirement for Wave-10 unit-test validation.

These anti-criteria hold across all Wave-10 PRs and across this closeout PR.

---

## 6. Validation Evidence

Evidence is anchored to the merged Wave-10 PRs above; do not over-claim beyond what those PRs and the local repo state demonstrate.

Local validation observed for the most recent Wave-10 slice (PR #2249, audit/tests) on commit `5e564c9b`:

- `ruff check tools/surrealdb/context_importer.py tests/unit/surrealdb/test_context_import_audit.py` -> all checks passed.
- `python -m pytest -q tests/unit/surrealdb/` -> 266 passed, 0 failed.
- All required CI checks green on PR #2249 (capture-intent, docs conflict guard, ci unit/integration + lint, policy-gate, root-session-hygiene-warning, submit-pypi).

Repository-side Wave-10 evidence:

- `tools/surrealdb/context_importer.py` carries the CLI surface, config loader, validator, planner, reconciler, gated apply path, in-memory adapter boundary, tombstone semantics, and audit emitter.
- `docs/surrealdb/context-importer-cli-contract.md` documents the CLI contract, including exit codes, gate semantics, audit schema, tombstone semantics, and forbidden-tables list.
- `infrastructure/config/surrealdb/context_import.local.example.yaml` ships as the only sanctioned config template; it contains no secrets and no production URLs.
- `tests/unit/surrealdb/` covers config, JSONL validation, plan, reconcile, apply, tombstones, audit, indexer, drift, ledger importer, and symbol extraction; full local suite green.
- `tests/fixtures/surrealdb/context_importer/` ships minimal deterministic fixtures used by the audit / apply / tombstone tests.

Anything beyond this list (e.g. real SurrealDB persistence evidence, production rollback evidence, query-layer evidence) is **not** Wave-10 evidence and must not be cited as such.

---

## 7. Known Follow-ups (Out of Wave-10 Scope)

The following items are intentionally not delivered in Wave 10 and require their own scope and GO before any work begins:

- **Wave 11 - Query CLI / SurrealDB query layer.** Building a read query surface on top of imported context records. Tracked separately; do not start without explicit GO.
- **Real SurrealDB adapter.** Replacing the default in-memory adapter with a real, durable SurrealDB write boundary. Requires a separate design, separate guardrails, separate test posture, and separate authorization. Wave-10 reports `real_surrealdb_adapter_available: false`.
- **Automated rollback-plan generation.** The `rollback-plan` subcommand is a stub (`scaffold-ack`, Exit `0`) in Wave 10. Producing real, machine-actionable rollback plans is a separate slice.
- **Production SurrealDB activation, runtime ingestion, MCP bridge, Agent-Briefing engine, vector search.** None of these may be derived from Wave-10 closure. They each require their own canonical issue, design, and human GO.

No scope expansion is implied by Wave-10 closure.

---

## 8. Closure Recommendation

After this PR (the runbook + gates closeout PR) merges:

1. Close issue **#2077** with a closeout comment linking to the merge commit and the new `docs/runbooks/surrealdb_context_import.md`.
2. Close issue **#2078** with a closeout comment linking to the merge commit and to this document.
3. Close Wave-10 anchor **#2067** with a closeout comment that:
   - Summarises the Wave-10 scope.
   - Lists the merged Wave-10 PRs (#2239, #2242, #2243, #2244, #2247, #2248, #2249, plus this closeout PR).
   - Confirms each item in Section 4 above.
   - Confirms each anti-criterion in Section 5 above.
   - Explicitly restates: Wave-10 closure does **not** authorize live trading, does **not** change Live-Readiness, and does **not** change Echtgeld posture.
4. Do **not** close Epic **#1976** as part of Wave-10 closure. The epic remains open while later waves (Wave 11+) are still expected.
5. Do not start Wave-11 work as part of Wave-10 closeout. Wave 11 requires its own planning and GO.

---

## 9. Hand-off

After all Wave-10 gates pass and Wave 10 is closed:

- Wave 11+ can build a read-only query layer on top of the in-memory adapter or a future real SurrealDB adapter.
- Live-Readiness, runtime trading, and any production-write decision remain governed by the LR-Audit / Control-Register surfaces and are unaffected by Wave-10 closure.
