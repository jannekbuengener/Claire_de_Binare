# Session 2026-05-29 — #2606 Parent-DoD follow-up roadmap (GitHub issues + ledger)

## Scope

Decompose Parent-DoD rest gaps from audit comment [#2606#issuecomment-4573207866](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606#issuecomment-4573207866) into deduplicated follow-up issues; record in repo ledger. No code, no DB/MCP/runtime mutation, no #2606 closure.

## Parent-DoD matrix (summary)

Gatekeeper verdict: **BLOCKED** — 10/11 criteria PARTIAL or OPEN; only fail-closed guard PASS.

| Criterion | Verdict | Follow-up |
|-----------|---------|-----------|
| Schema-validated memory records | PARTIAL | #2703 (write path), #2705 (closure audit) |
| DB-backed memory read | PARTIAL | #2705 |
| Gated write + auditable | PARTIAL | #2703, #2704 |
| Claims with evidence refs | PARTIAL | #2701, #2705 |
| Stale/expired visible | PARTIAL | #2702 |
| Rediscoverable via memory_id + scope | PARTIAL | #2703, #2705 |
| Agent output memory_id/source/trust/limitations | **OPEN** | **#2701** |
| Write without Human-GO fails | PARTIAL | #2703, #2704 |
| TTL → stale | PARTIAL | #2702 |
| Deterministic memory_id | PARTIAL | #2705 |
| No auto-memory / no prod write without gate | **PASS** | guard unchanged |

## Dedupe-Befund

**No open duplicates** for the five gaps before creation (2026-05-29).

Already closed / out of scope:

- #2694 — local-only write smoke (done)
- #2691, #2687 — DB read smoke blockers (done)
- #2009, #2571 — write policy design (done)
- #2153–#2160 — Wave-16 stale bundle-only (no DB)
- #2689 — Gordon decommission (separate epic, stays OPEN)

Related open epics (scope boundary, not duplicates): #1976, #2603, #2605, #2604.

## Follow-up issues created

| Prio | Issue | Scope |
|------|-------|-------|
| 1 | [#2701](https://github.com/jannekbuengener/Claire_de_Binare/issues/2701) | Agent output contract on memory MCP tools |
| 2 | [#2702](https://github.com/jannekbuengener/Claire_de_Binare/issues/2702) | DB-backed stale/expired scan vs `surrealdb-local` |
| 3 | [#2703](https://github.com/jannekbuengener/Claire_de_Binare/issues/2703) | Memory Write Path v1 + `audit_observation` |
| 4 | [#2704](https://github.com/jannekbuengener/Claire_de_Binare/issues/2704) | MCP write surface design (dry-run default) |
| 5 | [#2705](https://github.com/jannekbuengener/Claire_de_Binare/issues/2705) | Parent Closure Audit Slice |

Index comment on #2606: [#2606#issuecomment-4573401988](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606#issuecomment-4573401988)

## Recommended sequence

1. **#2701 + #2702** — parallel (read-side / evidence hardening)
2. **#2703** — write path v1 (after read-side)
3. **#2704** — MCP write design (design may start parallel to #2703; mutation after #2703)
4. **#2705** — closure audit last (formal DoD re-eval; does not close #2606)

## Non-goals (this session and follow-up tracker)

- Do **not** close #2606
- Do **not** close #2701–#2705 in this ledger session
- No code, DB write, MCP write, runtime mutation
- No memory write smoke, no productive memory write
- No auto-memory; `PERSIST_ALLOWED=False` unchanged
- No BLUE/RED stack change
- No LR-Go, no live capital, no Echtgeld authorization
- #2689 remains separate OPEN

## Actions

- Created follow-up issues #2701–#2705 (label `triage:offen`)
- Posted roadmap index on #2606
- Ledger: `CURRENT_STATUS.md` + this session log (docs PR)

## Verification

- `gh issue view 2606 2701–2705` — all OPEN (#2606 REOPENED)
- Dedupe search before #2701 — no pre-existing open duplicate
- `git diff --check` — clean (docs PR scope)
- LR remains **NO-GO** per `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`

## Rest

- Implementation of #2701–#2704 not started
- #2705 runs after A–D evidence or documented NON-BLOCKING gaps
- #1445 weekly focus stale (KW16); cockpit sequencing for memory work unconfirmed
