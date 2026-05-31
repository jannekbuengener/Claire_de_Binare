# Memory Write Path T4 Runbook v1 (#2758 / #2759 closeout)

**Issue:** [#2758](https://github.com/jannekbuengener/Claire_de_Binare/issues/2758) closeout; HG-W evidence anchor [#2759](https://github.com/jannekbuengener/Claire_de_Binare/issues/2759)
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
**Contract:** [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)  
**Status:** Repo-backed HG-W proof path on `main`; default fail-closed (`PERSIST_ALLOWED=False`, env-gated operator proof only)
**LR:** NO-GO (unchanged)

---

## 1. Purpose

Operator reference for the **repo-backed T4 agent_memory proof path** delivered
across #2758 / #2759. Documents fail-closed behavior, mandatory
`audit_observation` ordering, proof CLI usage, and rollback boundaries after the
2026-05-31 HG-W proof. It does **not** authorize permanent-on productive
`agent_memory` UPSERT, code-level `PERSIST_ALLOWED` flips, or MCP mutation.

---

## 2. Preflight read order

1. [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)
2. [`memory-write-gate-v1.md`](memory-write-gate-v1.md)
3. [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md)
4. [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
5. [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md)

---

## 3. Code surfaces

| Surface | Path | Role |
| --- | --- | --- |
| T4 orchestrator | `tools/surrealdb/memory_write_path_t4.py` | HG-W gate chain; mock sink only |
| T4 proof CLI | `tools/surrealdb/audit_trail_t4_proof.py` | Read-only matrix by default; HG-W write/rollback when env gates pass |
| T4 write helper | `tools/surrealdb/audit_trail_t4_write.py` | Governed endpoint write + rollback helper for the scoped HG-W proof |
| Gate (unchanged) | `tools/surrealdb/memory_write_gate.py` | `PERSIST_ALLOWED=False`; `approved_for_persist()` |

### Modes

| Mode | Behavior |
| --- | --- |
| `dry_run` (default) | Gate evaluation only; `path_status=evaluated_only` |
| `agent_memory_persist_productive` | HG-W + env-gated proof path; audit first; memory via `approved_for_persist()` only |

### Env gates

- `CDB_PERSIST_PRODUCTIVE_AGENT_MEMORY=1` — required to enter the operator proof path
- `CDB_PERSIST_ALLOWED=1` — operator env gate for `approved_for_persist()`
- `CDB_T4_HGW_HUMAN_GO_TOKEN` — required for the governed HG-W proof write
- `CDB_T4_HGW_AUTHORIZED_BY` — optional operator attribution override
- Module constant `PERSIST_ALLOWED` remains **`False`** on `main` (unchanged through closeout)

### Proof scope

- Exactly one scoped proof record: `g4-hgw-proof-2759`
- Authorization `target_issue` must reference `#2759`
- Authorization `scope` must be `memory_write_path_t4:g4-hgw-proof-2759`

### Human-GO tier

- **HG-W required** for `agent_memory_persist_productive`
- HG-P and HG-L are refused with `code=hg_w_required`
- HG-P remains valid for T3 productive audit path only (#2747)

---

## 4. Mandatory persist order

When productive mode is invoked (mock scaffold):

1. `evaluate_memory_write_gate()` → `approved_dry_run`
2. `materialize_audit_observation_from_gate()`
3. `audit_observation_row_is_redacted()` check
4. Mock `upsert_audit_observation`
5. **Only if** `approved_for_persist()` returns true (HG-W + `CDB_PERSIST_ALLOWED=1` + #2759 + proof scope): mock `upsert_agent_memory`

By default on `main`, step 5 does not run; response includes
`agent_memory_written=false` and `path_status=mock_persisted_audit_only`.
The 2026-05-31 HG-W proof executed step 5 exactly once on the governed endpoint
and rolled both rows back afterward.

---

## 5. Proof CLI

```bash
# Env structure only (no network)
python -m tools.surrealdb.audit_trail_t4_proof --check-env-only

# Read-only endpoint matrix (requires governed T3/T4 endpoint env)
python -m tools.surrealdb.audit_trail_t4_proof

# Write one scoped proof row on the governed endpoint (authorized window only)
python -m tools.surrealdb.audit_trail_t4_proof --write-proof-row --rollback-after
```

Without the HG-W env gates, `--write-proof-row` returns
`write_proof_row_status=refused` and
`write_proof_row_blocked_code=hgw_proof_not_authorized`.

Redacted proof evidence is recorded in
`knowledge/logs/sessions/2026-05-31-2759-hgw-proof.md`.

---

## 6. CI validation

```bash
pytest tests/unit/surrealdb/test_memory_write_path_t4.py \
  tests/unit/surrealdb/test_audit_trail_t4_proof_contract.py \
  tests/unit/surrealdb/test_memory_write_gate.py \
  tests/unit/surrealdb/test_memory_write_path_v1.py \
  tests/unit/surrealdb/test_memory_write_path_productive.py \
  tests/unit/surrealdb/test_audit_observation_from_gate.py \
  tests/unit/tools/mcp/test_memory_write_intent_tool.py -q

ruff check tools/surrealdb/memory_write_path_t4.py \
  tools/surrealdb/audit_trail_t4_common.py \
  tools/surrealdb/audit_trail_t4_proof.py \
  tests/unit/surrealdb/test_memory_write_path_t4.py \
  tests/unit/surrealdb/test_audit_trail_t4_proof_contract.py
```

---

## 7. Rollback

| Layer | Procedure |
| --- | --- |
| Code | Revert #2758 PR — constants remain fail-closed |
| Mock proof rows | N/A in scaffold (no real DB writes) |
| HG-W proof rows | DELETE by `observation_id` + `memory_id` + proof scope tag; document in session log |

---

## 8. Non-goals (closeout state)

- No code-level `PERSIST_ALLOWED=True` on `main`
- No permanent-on productive `agent_memory` UPSERT on governed endpoint
- No MCP mutation enablement
- No #2606 epic close
- No LR upgrade

Criterion #6 on #2606 is satisfied by the scoped HG-W proof plus repo-backed
orchestration. The epic still remains open because other closure axes are out of
scope for this runbook.
