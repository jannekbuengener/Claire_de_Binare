# GAP-006 Evidence: Tamper-Evident Audit Export

**Issue:** #463
**Scope:** Offline verification tool that validates LR-021 envelope hash chains and produces a tamper-evident evidence pack.

## What Was Built

| File | Purpose |
|------|---------|
| `scripts/audit/gap006_audit_export.py` | CLI tool: verify chain_hash + produce evidence pack |
| `tests/unit/audit/test_gap006_audit_export.py` | 20 tests: positive (PASS), negative (tamper detection), helpers |

## Guardrails Satisfied

| Guardrail | How |
|-----------|-----|
| No SIGNAL / threshold / decision-logic changes | Purely additive: new files only, 0 existing files modified |
| Offline only | Standalone CLI script; no service / trading impact |
| No schema changes | Reads existing envelope.v1 + event_hash + chain_hash fields |
| Deterministic | `json.dumps(sort_keys=True)` for manifest; no timestamps or non-deterministic metadata in outputs — all values derived from input; same input -> byte-identical output |
| No hash duplication | `compute_event_hash` / `compute_chain_hash` imported from `lr021_replay.py` |
| Backward compatible | No new required fields; no payload changes |

## How to Use

### Verify and export evidence pack:

```bash
python scripts/audit/gap006_audit_export.py \
    --input artifacts/replayed.jsonl \
    --out-dir artifacts/audit_export
```

Exit code: `0` = PASS, `1` = FAIL.

### Typical pipeline:

```bash
# 1. Replay raw envelopes (adds event_hash + chain_hash)
python scripts/replay/lr021_replay.py \
    --input raw_envelopes.jsonl \
    --output replayed.jsonl

# 2. Audit-verify the replay output
python scripts/audit/gap006_audit_export.py \
    --input replayed.jsonl \
    --out-dir audit_export/
```

## Output Files

| File | Content |
|------|---------|
| `manifest.json` | Schema `gap006.audit_manifest.v1`: counts, first/last hashes, input SHA-256, chain_verified bool |
| `sha256sum.txt` | `sha256sum`-compatible checksum line for the input file |
| `verification.md` | Human-readable PASS/FAIL report with hash chain details |

## Verification Logic

1. For each JSONL line: strip `event_hash` + `chain_hash` from the dict
2. Recompute `event_hash` = `SHA-256(canonical_json_dumps(envelope))` via `lr021_replay.compute_event_hash`
3. Recompute `chain_hash` = `SHA-256(prev_chain_hash + ":" + event_hash)` via `lr021_replay.compute_chain_hash`
4. Compare stored vs. computed — any mismatch -> FAIL
5. Genesis: `prev_chain_hash = "0" * 64`

## Tamper Detection Coverage

| Mutation | Detected by |
|----------|-------------|
| Payload field changed | event_hash mismatch |
| event_hash flipped | event_hash mismatch |
| chain_hash flipped | chain_hash mismatch |
| Line deleted | chain_hash mismatch (from deleted line onward) |
| Line reordered | chain_hash mismatch |
| Line inserted | chain_hash mismatch |

## Test Evidence

- **20/20 tests passed**
- Positive: golden fixture (`lr021_expected_hashes.jsonl`) -> PASS
- Negative: mutated event_hash, chain_hash, payload, deleted line -> FAIL
- CLI exit codes: 0 (PASS), 1 (FAIL)
- Deterministic: 3 runs -> byte-identical manifest
