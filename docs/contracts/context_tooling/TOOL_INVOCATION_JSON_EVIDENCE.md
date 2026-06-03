# Tool invocation JSON evidence (#2850)

Machine-readable evidence for the context live invocation regression harness. Complements human-readable markdown/text output and embeds **db-record-evidence claims** from [#2851](../context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md).

| Artifact | Path |
|----------|------|
| Aggregate JSON Schema | [`docs/contracts/tool_invocation_evidence.v1.schema.json`](../tool_invocation_evidence.v1.schema.json) |
| Per-claim JSON Schema | [`docs/contracts/db_record_evidence_claim.v1.schema.json`](../db_record_evidence_claim.v1.schema.json) |
| Builder | [`tools/surrealdb/context_invocation_evidence_json.py`](../../../tools/surrealdb/context_invocation_evidence_json.py) |
| Harness | [`tools/surrealdb/context_live_invocation_harness.py`](../../../tools/surrealdb/context_live_invocation_harness.py) |

## Generate JSON evidence

```bash
# Minimal profile (expect final_verdict PASS_WITH_LIMITS, six accepted limitations)
python -m tools.surrealdb.context_live_invocation_harness --format json

# Full profile (expect final_verdict PASS, zero accepted limitations)
python -m tools.surrealdb.context_live_invocation_harness --profile full --format json

# Write to file (optional)
python -m tools.surrealdb.context_live_invocation_harness --format json \
  --output docs/evidence/context_tooling/latest_invocation_evidence.json
```

Makefile targets `context-live-invoke` and `context-live-invoke-full` remain unchanged (text/markdown default). Use `--format json` when you need the evidence bundle.

## Interpretation

- **`final_verdict`**: `PASS_WITH_LIMITS` when the minimal profile documents six fail-closed Wave-14 record paths; `PASS` when the full inline-record profile has no `PASS_WITH_LIMITS` rows.
- **`evidence_claims`**: One claim per `PASS_WITH_LIMITS` matrix row, `trust_classification=accepted_limitation`, aligned with `PASS_WITH_LIMITS_ERROR_CODES` / #2852 ratification.
- **`determinism_hash`**: Stable across runs with the same matrix and git SHA; excludes `started_at_or_observed_at` and the hash field itself.
- **No fake DB-backed claims**: Accepted-limitation claims use `in_memory` / empty record proof, not `surrealdb-local` with record IDs.

## Scope boundaries

- **#2853** (root inventory), **#2854** (negative controls), **#2855** (operator senses docs), **#2856** (trust thresholds) are out of scope for this slice.
- **LR remains NO-GO**; JSON evidence does not authorize live capital or productive DB writes.
