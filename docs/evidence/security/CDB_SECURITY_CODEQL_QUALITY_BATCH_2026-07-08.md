# CodeQL Quality Batch — Issue #3924

**Date:** 2026-07-08 (UTC+2)  
**Scope:** CodeQL quality hygiene quick-wins (59 open quality alerts @ slice start)  
**Parent:** [#3924](https://github.com/jannekbuengener/Claire_de_Binare/issues/3924)  
**Related:** PR #3925 (4 HIGH clear-text fixes), meta [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**LR:** NO-GO (unchanged)

---

## Brain Evidence

| Feld | Wert |
|------|------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| repo_fallback_used | true |
| repo_fallback_reason | insufficient_evidence |
| tools_or_queries | `gh api code-scanning/alerts` (paginate), targeted pytest, ruff |
| records_or_results | Pre-slice: **63** open CodeQL (59 quality + 4 HIGH); post-merge recount pending Default Setup scan |
| impact_on_plan | GitHub API authoritative for alert inventory; HIGH alerts out of #3924 scope |

---

## CodeQL Inventory @ Slice Start

| Category | Count | Notes |
|----------|-------|-------|
| Total open | 63 | GitHub API |
| Quality | 59 | This slice |
| HIGH security | 4 | #4533, #4535, #4611, #4612 — addressed in #3925; closure awaits post-merge scan |

### Quality by rule

| Rule | Count | Action |
|------|-------|--------|
| `py/ineffectual-statement` | 16 | **Fixed** — Protocol `...` → `pass` |
| `py/unused-import` | 16 | **Fixed** — remove dead imports / `__all__` re-exports |
| `py/empty-except` | 10 | **Fixed** — best-effort comments (surrealdb + .codex imagegen) |
| `py/unused-global-variable` | 5 | **Fixed** — remove dead globals / `__all__` exports |
| `py/unused-local-variable` | 4 | **Fixed** — remove unused bindings |
| `py/import-and-import-from` | 2 | **Fixed** — single import style in tests |
| `py/implicit-string-concatenation-in-list` | 1 | **Fixed** — explicit concatenation in scanner |
| `py/uninitialized-local-variable` | 1 | **Deferred** — .codex plugin-creator (already has `= None` on main; scan lag) |
| cyclic-import | 2 | **Fixed** in #3939 — shared types extracted to `context_invocation_harness_types.py` |
| `py/file-not-closed` | 1 | **Deferred** — paper stimulus test fixture lifecycle |
| `py/polluting-import` | 1 | **Deferred** — local test helper import semantics |

---

## Delivered (Quick-Wins)

**tools/surrealdb/** — Protocol stubs, unused imports, empty-except comments, `audit_trail_t4_common.__all__`, trust-summary dead `_topic` removal in MCP tools.

**tests/** — unused imports/locals, import-style cleanup, fixture helper dead `_NOW` removal, wave14 `__all__` exports.

**.github/scripts/post_merge_followup_scanner.py** — explicit string concatenation in degraded-rate-limit block.

**.codex/cdb_skills/.system/imagegen/scripts/image_gen.py** — empty-except comments.

---

## Deferred Clusters (documented, no dismissals)

| Cluster | Alerts | Rationale | Follow-up |
|---------|--------|-----------|-----------|
| cyclic-import | 2 | `context_invocation_evidence_json` ↔ `context_live_invocation_harness` — fixed in #3939 via `context_invocation_harness_types.py` | #3939 (closed) |
| file-not-closed | 1 | `test_paper_runtime_stimulus_runner.py` — fixture lifecycle semantics | Document only |
| polluting-import | 1 | `memory_db_proof_helpers.py` — test-local import pattern | Document only |

No GitHub alert dismissals. No Trivy/image/Grafana/runtime changes.

---

## Validation

```bash
git diff --check
ruff check <touched files>  # passed
pytest -q tests/unit/surrealdb/ tests/unit/scripts/test_post_merge_followup_scanner.py \
  tests/unit/validation/test_paper_runtime_stimulus_runner.py \
  tests/unit/tools/mcp/test_wave14_query_contracts.py \
  tests/unit/surrealdb/test_knowledge_refresh_report.py \
  tests/unit/utils/test_redis_client.py \
  tests/unit/surrealdb/test_memory_write_path_productive.py \
  tests/unit/surrealdb/test_memory_write_path_t4.py \
  tests/unit/surrealdb/test_audit_trail_t4_proof_contract.py
# 1989 passed
```

Post-merge recount: `gh api repos/.../code-scanning/alerts?state=open` (Default Setup async).

---

## Safety Boundaries

- No alert dismissals
- #3755 Grafana HOLD untouched
- No BLUE/RED runtime / Docker / Trivy image changes
- No MCP/DB mutations
- LR remains NO-GO

---

## References

- Prior HIGH slice: `docs/evidence/security/CDB_SECURITY_CODEQL_DRIFT_2026-07-08.md`
- Meta tracker: #2513
- Issue: #3924
