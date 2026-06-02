# Cross-Session Memory Rediscovery v1 (#2720)

**Status:** Campaign deliverable  
**Issue:** [#2720](https://github.com/jannekbuengener/Claire_de_Binare/issues/2720)  
**Epic:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (CLOSED 2026-05-31; design doc historical)  
**LR:** NO-GO (unchanged)

---

## Purpose

Prove that run-scoped ``agent_memory`` rows remain discoverable by ``memory_id`` and
``scope`` across process boundaries. Process A seeds DB rows and writes a
non-sensitive manifest; process B (fresh Python subprocess) reads only the
manifest and DB.

**Non-goals:** productive memory write; MCP mutation; MCP ``by_memory_id`` feature;
closing #2606.

---

## Flow

1. Seed run-scoped fixtures (same path as #2603 / #2719).
2. Write ``.cdb_memory_rediscovery/<run_id>/manifest.json`` (memory_id, scope, evidence_ids, run_id only).
3. Subprocess ``prove-phase`` loads manifest + SurrealDB adapter; SELECT by memory_id AND scope.
4. Stale scan + claim evidence at rest (#2719) on the same scope.
5. Cleanup DB rows and manifest directory.

---

## Operator path

```bash
make context-memory-rediscovery-proof
```

CLI:

```bash
python -m tools.surrealdb.memory_rediscovery_proof_cli run-proof --confirm
```

---

## CI boundary

| Layer | Proves |
|-------|--------|
| `tests/unit/surrealdb/test_memory_cross_session_rediscovery_contract.py` | Manifest + prove contracts (mocks) |
| `make context-memory-rediscovery-proof` | Local two-process proof |
| Required `ci.yml` | **No** live SurrealDB |

---

## Limits

- Proof is local operator / opt-in ``local_only`` only.
- Manifest handoff is file-based; not a production rediscovery API.
- Depends on #2719 claim evidence enforcement for linked claims in scope.

---

## References

- [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md)
- [`claim-evidence-at-rest-v1.md`](claim-evidence-at-rest-v1.md)
- Module: `tools/surrealdb/memory_cross_session_rediscovery.py`
