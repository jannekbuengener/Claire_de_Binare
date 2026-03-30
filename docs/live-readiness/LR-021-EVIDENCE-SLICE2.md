# LR-021 Evidence: Toggle-Gated Envelope Emission — Slice 2

**Issue:** #919 (tracks Slice 2), parent #783
**Prereq:** Slice 1 (PR #917, #918)
**Scope:** Wire DECISION/ORDER/FILL envelope emission into risk + execution services. Toggle `CDB_ENVELOPE_EMISSION` defaults OFF (legacy alias: `LR021_ENVELOPE_EMIT_ENABLED`).

## What Was Built

| File | Purpose |
|------|---------|
| `core/replay/emitter.py` | Toggle-gated emitter: `emit_decision_envelope`, `emit_order_envelope`, `emit_fill_envelope` |
| `services/risk/service.py` | DECISION hook (after `_phase9_enrich_evidence`) + ORDER hook (before `return order`) |
| `services/execution/service.py` | FILL hook (after correlation_ledger FILL, before stats update) |
| `tests/unit/replay/test_emitter.py` | 22 tests: toggle ON/OFF, all 3 envelope types, optional field omission, evidence_keys |

## Safety Guarantees

1. **Toggle OFF = zero side effects**: `CDB_ENVELOPE_EMISSION` / `LR021_ENVELOPE_EMIT_ENABLED` gate checked first; when `"0"` (default), no import in hotpath, no function call, no I/O
2. **Crashsafe toggle check**: even the `os.getenv` call is wrapped in `try/except` — if `os` is somehow unavailable, `_lr021_emit = False`
3. **Import + emit wrapped in `try/except Exception: pass`**: emitter bugs never break the trading or execution path
4. **Type coercion at hook site**: `str()`, `float()`, `int()` ensure type mismatches in upstream data don't propagate
5. **`order.price is None` → skip**: no sentinel values (e.g. `0.0`) emitted for missing prices
6. **No module-level cache**: `os.getenv` read per call, testable via `monkeypatch.setenv`

## Hook Locations

| Hook | File | Location | Guard |
|------|------|----------|-------|
| DECISION | `services/risk/service.py` | After `_phase9_enrich_evidence()` | `evidence.get("decision_id")` |
| ORDER | `services/risk/service.py` | Before `return order` | `getattr(order, "order_id", None)` + `order.price is not None` |
| FILL | `services/execution/service.py` | Before stats update | `status == "FILLED"` + `result.fill_id` |

## Emitter Design

- `envelope_emit_enabled()`: reads `CDB_ENVELOPE_EMISSION` (primary) or `LR021_ENVELOPE_EMIT_ENABLED` (legacy alias) per call; CDB_ takes precedence when set
- `_build_envelope()`: constructs envelope dict with `schema_version: "envelope.v1"`, omits None optionals
- `_compute_event_hash()`: canonical JSON → SHA-256 (reuses Slice 1 `canonical_json_dumps` + `sha256_hex`)
- `emit_envelope()`: computes `event_hash`, logs compact JSONL line to `lr021.emitter` logger
- `emit_decision_envelope()`: includes `evidence_keys` (sorted key names only, no values) for audit trail
- `emit_order_envelope()`: includes optional `signal_id`, `decision_id`
- `emit_fill_envelope()`: includes optional `price` (omitted when None)
- `emit_envelope()`: output serialized via `canonical_json_dumps()` (None omission, float sanitization, sorted keys)

## Schema Version Policy

- Envelope schema version is `"envelope.v1"`.
- The replay runner (`scripts/replay/lr021_replay.py`) validates `schema_version` and rejects envelopes with unknown, `None`, or empty versions.
- In strict mode (default): unknown `schema_version` raises `ValueError`.
- In lenient mode (`--lenient`): unknown `schema_version` skips the envelope and counts an error.
- New schema versions require coordinated updates to `VALID_SCHEMA_VERSIONS` in `lr021_replay.py` and `_build_envelope()` in `emitter.py`.

## What Is NOT in Slice 2

- Live replay from Redis streams
- Chain hash across emitted envelopes (single-envelope hashing only)
- New thresholds, decision logic, or risk/execution service changes
- Any changes to SIGNALS

## Verification

```bash
# All emitter tests
pytest tests/unit/replay/test_emitter.py -v

# Full replay suite (Slice 1 + Slice 2)
pytest tests/unit/replay/ -v

# Full unit suite (regression check)
pytest tests/unit/ -v
```
