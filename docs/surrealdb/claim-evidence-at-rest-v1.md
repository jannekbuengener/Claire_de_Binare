# Claim Evidence at Rest v1 (#2719)

**Status:** Campaign deliverable  
**Issue:** [#2719](https://github.com/jannekbuengener/Claire_de_Binare/issues/2719)  
**Epic:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (CLOSED 2026-05-31; design doc historical)  
**LR:** NO-GO (unchanged)

---

## Purpose

Fail-closed DB-layer enforcement that `claim` rows with status `supported` or
`weakly_supported` reference persisted `evidence_ref` records. Caller-supplied
metadata cannot substitute for at-rest evidence.

**Non-goals:** productive memory write; MCP mutation; live DB ASSERT in required CI;
closing #2606.

---

## Contract

Envelope schema: `claim-evidence-at-rest/v1`

| Function | Role |
|----------|------|
| `validate_claim_record_structure` | Hard-fail claim shape; evidence_refs required for supported statuses |
| `validate_evidence_refs_resolve` | Each ref must exist in evidence index |
| `reject_caller_metadata_as_evidence` | Block metadata keys posing as evidence without DB rows |
| `prove_claim_evidence_at_rest_db_v1` | SELECT claims + evidence_ref; enforce per row |

Module: `tools/surrealdb/claim_evidence_at_rest.py`

---

## Operator path (local only)

Prerequisites: same as `make context-memory-db-proof` (#2603).

```bash
make context-claim-evidence-proof
```

CLI:

```bash
python -m tools.surrealdb.claim_evidence_proof_cli preflight --confirm
python -m tools.surrealdb.claim_evidence_proof_cli run-proof --confirm
```

Run-scoped fixtures include `claims.jsonl` under
`tests/fixtures/surrealdb/memory_db_proof/` (seeded via `context_importer`
`local-dev` mode, then cleaned up).

---

## CI boundary

| Layer | Proves |
|-------|--------|
| `tests/unit/surrealdb/test_claim_evidence_at_rest.py` | Contracts, mocks, fail-closed |
| `make context-claim-evidence-proof` | Local SurrealDB read proof |
| Required `ci.yml` | **No** live SurrealDB |

---

## Limits (PASS WITH EXPLICIT LIMITS)

- Enforcement is Python contract v1 on SELECT results, not a SurrealDB DB ASSERT.
- No guarantee on production or non-local adapters without operator proof.
- `claim_resolver.py` in-memory path still warning-only; DB proof is stricter.

---

## References

- Proof path matrix: [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md)
- Runbook: [`docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md)
- Runtime: `tools/surrealdb/claim_evidence_proof_runtime.py`
