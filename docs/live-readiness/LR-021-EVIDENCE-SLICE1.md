# LR-021 Evidence: Deterministic Replay Framework — Slice 1

**Issue:** #783
**Scope:** Offline replay of Decision/Order/Fill envelopes with stable canonical hashing.

## What Was Built

| File | Purpose |
|------|---------|
| `core/replay/__init__.py` | Package init |
| `core/replay/canonical_json.py` | Canonical JSON serialization (sorted keys, compact separators, None-omitted, float-sanitized, -0.0 normalized) |
| `core/replay/envelopes.py` | `DecisionEnvelopeV1`, `OrderEnvelopeV1`, `FillEnvelopeV1` dataclasses |
| `scripts/replay/lr021_replay.py` | Offline JSONL replay runner with `event_hash` + `chain_hash` |
| `tests/fixtures/replay/lr021_sample_envelopes.jsonl` | 5-event fixture (2 decisions, 2 orders, 1 fill) |
| `tests/fixtures/replay/lr021_expected_hashes.jsonl` | Golden file (frozen expected hashes) |
| `tests/unit/replay/test_canonical_json.py` | 30 tests: sanitization, None-omission, key-order independence, pinned bytes |
| `tests/unit/replay/test_envelopes.py` | 7 tests: envelope `to_dict()` contract |
| `tests/unit/replay/test_lr021_replay.py` | 15 tests: golden-file replay, validation, chain integrity, lenient mode |

## How to Run Replay

```bash
python scripts/replay/lr021_replay.py \
    --input tests/fixtures/replay/lr021_sample_envelopes.jsonl \
    --output artifacts/lr021_output.jsonl
```

## Why Deterministic

- `canonical_json_dumps()`: sorted keys + compact separators + None-omitted + floats rounded to 10 decimals + -0.0 normalized
- `event_hash`: SHA-256 of canonical JSON bytes per envelope
- `chain_hash`: `SHA-256(prev_chain_hash + ":" + event_hash)`, genesis = `"0" * 64`
- Golden-file tests assert both **canonical bytes** and **hash** per event

## Design Decisions

| Decision | Choice |
|----------|--------|
| Float sanitization | Local `_sanitize_float()` in `canonical_json.py`, decoupled from `uuid_gen.py` |
| Envelope design | Flat dataclasses, no base class |
| schema_version | `"envelope.v1"` |
| None-omission | Dict values omitted; list items preserved as null |
| Chain hash delimiter | `":"` between prev and current hash |

## What Is NOT in Slice 1

- Live replay / Redis wiring
- Market data replay
- Runtime integration (no changes to existing services)
- New thresholds or decision logic changes

## Next (Slice 2)

- Wire envelopes into risk/execution event emission (behind toggle, default OFF)
- Live replay from Redis streams using same canonical hashing
- Integration with LR-030 Shadow Mode (#784)
