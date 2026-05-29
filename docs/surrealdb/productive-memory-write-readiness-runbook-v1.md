# Productive Memory Write Readiness Runbook v1 (#2730)

**Issue:** [#2730](https://github.com/jannekbuengener/Claire_de_Binare/issues/2730)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
**Contract:** [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)  
**Status:** Readiness procedures — **no activation in this slice**  
**LR:** NO-GO (unchanged)

---

## 1. Purpose

Operator and maintainer checklist for **evaluating** future productive Memory
Write readiness. This runbook does **not** enable productive writes, MCP
mutation, or `PERSIST_ALLOWED` flips.

Use when:

- Preparing a future G1–G4 activation issue
- Re-auditing #2606 parent closure (criterion 6)
- Collecting evidence after local T2 proofs

---

## 2. Preflight read order

Read in order before any readiness assessment:

1. [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)
2. [`memory-write-gate-v1.md`](memory-write-gate-v1.md)
3. [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md)
4. [`audit-observation-model-v1.md`](audit-observation-model-v1.md)
5. [`mcp-memory-write-surface-v1.md`](mcp-memory-write-surface-v1.md)
6. [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
7. [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md) (ledger; live truth = GitHub/`main`)

---

## 3. Evidence pack template

Copy and fill for each readiness review session:

```text
## Productive Memory Write Readiness Evidence Pack

- Date/time (UTC):
- Assessor:
- Git commit SHA (main or review branch):
- GitHub issue ref:
- Human-GO tier claimed: HG-L | HG-P | HG-W (must match authorized scope)
- LR verdict cited: NO-GO (SSOT path)
- Board stage noted: trade-capable (orthogonal; not live-go)

### Tier under review
- [ ] T2 local only (audit_persist_local / write smoke)
- [ ] T3 productive audit trail (spec compliance only — not activated)
- [ ] T4 productive agent_memory write (must be NOT ACTIVATED unless separate GO issue)

### Gate / path evidence
- gate_status:
- path_status:
- observation_id (if local audit persist):
- memory_id (if applicable):
- Mode: dry_run | audit_persist_local | (future productive modes: NOT RUN)

### Test evidence (CI-safe baseline)
- pytest tests/unit/surrealdb/test_memory_write_gate.py — PASS/FAIL
- pytest tests/unit/surrealdb/test_memory_write_path_v1.py — PASS/FAIL
- pytest tests/unit/surrealdb/test_audit_observation_from_gate.py — PASS/FAIL
- pytest tests/unit/tools/mcp/test_memory_write_intent_tool.py — PASS/FAIL

### Safety assertions
- [ ] PERSIST_ALLOWED remains False in memory_write_gate.py (code read or grep)
- [ ] No raw human_go_token in logs, audit rows, or MCP output
- [ ] No agent_memory UPSERT via write path v1
- [ ] MCP mutation flags blocked (MUTATION_ALLOWED False)

### Explicit non-goals restated
- No LR upgrade implied
- No Echtgeld / live trading
- No BLUE/RED runtime change in this review
```

---

## 4. Operator checklist (readiness review)

| Step | Action | Pass criterion |
| --- | --- | --- |
| 1 | Confirm issue scope and Human-GO tier | Tier matches authorized work (HG-L for local only) |
| 2 | Read contract §8 abgrenzung | Reviewer can state local vs productive vs MCP |
| 3 | Verify `PERSIST_ALLOWED = False` on target SHA | Grep or file read; no flip without G3 issue |
| 4 | Run CI-safe unit tests (§3 template) | All listed tests PASS |
| 5 | If local T2 was run: confirm localhost + cleanup | `127.0.0.1:8010`; run-scoped DELETE documented |
| 6 | Record evidence pack in session log | Path under `knowledge/logs/sessions/` |
| 7 | State verdict | SPEC COMPLIANT / NOT READY / BLOCKED |

**Do not** run productive-tier persist commands in this runbook slice — placeholders only.

---

## 5. Safety and secret hygiene

| Rule | Detail |
| --- | --- |
| Token storage | `CDB_MEMORY_WRITE_HUMAN_GO_TOKEN` via env only |
| Logging | Never log raw token; audit rows use `human_go_token_present: bool` |
| Issues / PRs | No secrets in GitHub comments or PR bodies |
| Local cleanup | DELETE run-scoped `audit_observation` after local proofs |

---

## 6. Proof commands (placeholders — not activation)

**CI-safe (always allowed):**

```bash
pytest tests/unit/surrealdb/test_memory_write_gate.py \
  tests/unit/surrealdb/test_memory_write_path_v1.py \
  tests/unit/surrealdb/test_audit_observation_from_gate.py \
  tests/unit/tools/mcp/test_memory_write_intent_tool.py -q
```

**Local T2 (requires explicit HG-L operator GO — see [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md)):**

```bash
# Placeholder — do not run without maintainer GO
# export CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT=1
# export CDB_MEMORY_WRITE_HUMAN_GO_TOKEN=GO-YYYY-MM-DD-<suffix>
# python -m tools.surrealdb.memory_write_path_v1 ... audit_persist_local
```

**Productive T3/T4:** **NOT DEFINED** — blocked until G1–G4 implementation issues land.

---

## 7. #2606 parent re-audit hook

After #2730 spec merge, parent epic [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)
should be re-audited (read-only) with focus on:

| Criterion | Pre-#2730 | Post-#2730 spec |
| --- | --- | --- |
| 6 — Human-GO write path v1 auditable | PARTIAL (local audit only) | PARTIAL for runtime; **SPECIFIED** for productive audit (T3 not activated) |
| Productive audit trail gap | Undocumented BLOCKED | Documented in contract G0 |

Re-audit does **not** close #2606 unless all PARTIAL criteria become PASS.

Follow-up issue template: `#2606 Follow-up: parent closure re-audit after productive audit trail spec`.

---

## 8. Readiness verdict format

Use one of:

| Verdict | Meaning |
| --- | --- |
| **SPEC COMPLIANT (G0)** | Contract/runbook present; no activation attempted |
| **NOT READY (T3/T4)** | Implementation gates G1–G4 not met |
| **BLOCKED (SAFETY)** | Secret leak, unintended persist, or scope violation detected |

---

## Cross-references

- Contract: [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)
- Local operator path: [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md)
- Proof matrix: [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md) row 3
- Parent audit log: `knowledge/logs/sessions/2026-05-29-2606-parent-closure-audit.md`
