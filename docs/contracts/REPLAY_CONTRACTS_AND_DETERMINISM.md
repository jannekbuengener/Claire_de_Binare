# Replay Contracts & Determinism

Governance: Issue #1806 (LR-021 Replay Contracts & Determinism)

## Glossar

| Term | Definition |
|------|-----------|
| **Replay** | Deterministic re-execution of a historical event sequence from recorded envelope/market data |
| **Shadow Replay** | Reference/non-binding replay for diagnostic purposes (report_type: "shadow_replay") |
| **Deterministic Replay** | Canonical replay enforcing chain integrity and determinism rules (report_type: "deterministic_replay") |
| **Envelope** | Immutable record of a trading system event: DecisionEnvelopeV1 (risk decision), OrderEnvelopeV1 (order), FillEnvelopeV1 (execution) |
| **Event Chain** | Ordered sequence of envelopes forming a complete trade execution history |
| **Chain Hash** | Deterministic SHA256 hash of the ordered envelope sequence; used for integrity verification |
| **Report Hash** | Deterministic SHA256 hash of the complete replay report; immutable fingerprint of execution |
| **Determinism Rule** | Constraint ensuring identical inputs produce identical outputs (no wall-clock variation, no randomness) |
| **Canonical JSON** | Sorted-key, compact, float-sanitized JSON serialization (see `core/replay/canonical_json.py`) |

## Replay vs. Backtest

| Aspect | Backtest | Replay |
|--------|----------|--------|
| **Input** | Historical candle/OHLC data | Recorded envelope and market-state snapshots |
| **Execution** | One-pass strategy evaluation | Deterministic re-execution of recorded decision/order flow |
| **Report Schema** | `strategy_validation_report_v1.schema.json` | `replay_report.v1.schema.json` |
| **Focus** | Strategy performance & gating | Determinism verification & envelope chain integrity |
| **Binding** | Can pass/fail trading readiness gate | Diagnostic; feeds into determinism audits |

## Schema Versioning

### schema_version

Fixed field in reports: `schema_version = "replay_report.v1"` for all V1 replay reports.

- **Not** a semver (e.g., 1.0.0)
- String constant: `"replay_report.v1"`
- Changes to schema structure → new schema_version (e.g., `"replay_report.v2"`)
- Backwards incompatibility requires explicit version bump

### contract_version

Internal dataclass versioning (not exposed in reports):

- `ReplayRunSpec`, `ReplayExecutionResult`, etc. are tied to `replay_report.v1` implicitly
- Breaking changes to dataclasses → new schema_version
- Additive optional fields → same schema_version (backwards compatible)

## Determinism: Hash Computation

### Envelope Hash (event_hash)

Deterministic SHA256 hash of a single envelope:

```python
from core.replay.canonical_json import canonical_hash

envelope_dict = envelope.to_dict()  # None-valued fields omitted
event_hash = canonical_hash(envelope_dict)  # → 64-char hex
```

**Critical rules:**
- All required fields must be present and non-None
- Optional fields included only if set
- Floating-point values sanitized: NaN/Inf → None (omitted), normal floats rounded to 10 decimals, -0.0 → 0.0
- UTF-8 encoding

### Chain Hash (envelope_chain_hash)

Deterministic SHA256 hash of the ordered envelope sequence:

```python
envelope_hashes = [canonical_hash(e.to_dict()) for e in envelopes]
chain_hash = canonical_hash(envelope_hashes)
```

**Chain integrity requirements:**
- All envelopes must pass `validate_envelope_determinism()`
- Timestamps must be non-decreasing (ts_ms[i] ≤ ts_ms[i+1])
- event_ids must be unique (no duplicates)
- Order is deterministic and preserved

### Report Hash (report_hash)

Deterministic SHA256 hash of the full replay report:

```python
report_dict = replay_report_input.to_dict()  # None-valued fields omitted
report_hash = canonical_hash(report_dict)
```

Used as the immutable fingerprint of the entire replay execution.

## None Handling & Float Sanitization

### None Omission

Optional fields with None value are **omitted** from serialized dicts:

```python
# If metadata=None:
{"run_id": "...", "strategy_id": "..."}  # metadata NOT present

# If metadata={"key": "value"}:
{"run_id": "...", "strategy_id": "...", "metadata": {"key": "value"}}
```

Implemented by `to_dict()` methods and `core/replay/canonical_json._omit_none()`.

**Exception:** Lists preserve None items (removing would change indices and break determinism):

```python
[null, "value", null]  # None items are null in lists, not omitted
```

### Float Sanitization

All floating-point values undergo sanitization before serialization:

- **NaN, +Inf, -Inf** → None (then omitted from dicts by None-omission rule)
- **Normal floats** → rounded to 10 decimal places
- **-0.0 normalization** → 0.0 (JSON doesn't distinguish -0.0 from 0.0)

Implemented by `core/replay/canonical_json._sanitize_float()`.

**Rationale:** Deterministic hashing requires bit-identical JSON strings. Floating-point quirks (signed zero, rounding) must be normalized.

## Determinism Validation

### validate_envelope_determinism(envelope)

Validates a single envelope for determinism-safety:

- `schema_version == "envelope.v1"`
- `event_type` in ("DECISION", "ORDER", "FILL")
- `event_id` non-empty string
- `ts_ms` non-negative int
- `payload` is dict

Raises `ReplayDeterminismError` if any check fails.

### verify_envelope_chain_integrity(envelopes, expected_chain_hash=None)

Validates ordered envelope sequence:

- All envelopes pass individual validation
- Timestamps non-decreasing
- event_ids unique
- Computes and optionally verifies chain hash

Raises `ReplayDeterminismError` if any check fails.

### verify_replay_integrity_result(integrity)

Validates a `ReplayIntegrity` result:

- `run_id`, `envelope_count`, hashes are well-formed
- `failed_checks` non-empty ⟺ `integrity_ok == False`

Raises `ReplayDeterminismError` on inconsistency.

### compute_replay_report_hash(report_input)

Computes deterministic hash of full report. Used as report fingerprint.

## Event Loop State Snapshotting

During replay, capture periodic snapshots of execution state:

```python
ReplayEventLoopState(
    event_index=i,
    ts_ms=envelope.ts_ms,
    event_hash=compute_envelope_hash(envelope),
    state_hash=cumulative_state_hash,
    decision_made=decision_emitted,
    order_submitted=order_placed,
    metadata={"regime": "UPTREND", ...}
)
```

State snapshots allow verification that:
- Event processing order is preserved
- Cumulative state hash matches envelope chain hash
- Decision/order flow aligns with envelope emissions

Hash of all state snapshots: `event_loop_states_hash`.

## Versioning Strategy (V1 Minimal)

### Breaking vs. Non-breaking

**Non-breaking (same schema_version):**
- Add optional fields to dataclasses
- Add optional top-level sections to report (e.g., new optional metrics)
- Expand enum values for `report_type`, `run_mode` (backwards compatible)

**Breaking (new schema_version):**
- Remove or rename required fields
- Change field types (e.g., string → int)
- Change const values (e.g., strategy_id const)
- Remove optional fields that become required

### Future Versions

When backwards incompatibility is necessary:

1. Increment schema_version: `"replay_report.v2"`
2. Update `ReplayReportInput` dataclass if needed
3. Update JSON-Schema file
4. Keep old schema for archive/migration purposes
5. Update validation logic to handle both versions

## File Locations

| Artifact | Location | Purpose |
|----------|----------|---------|
| Replay contracts (Python) | `core/replay/replay_contracts.py` | Dataclass definitions |
| Determinism helpers | `core/replay/determinism.py` | Validation & hashing utilities |
| Canonical JSON serialization | `core/replay/canonical_json.py` | Deterministic JSON rendering |
| Replay report schema | `docs/contracts/replay_report.v1.schema.json` | Machine-readable contract |
| Envelope definitions | `core/replay/envelopes.py` | Event envelope types |
| This documentation | `docs/contracts/REPLAY_CONTRACTS_AND_DETERMINISM.md` | Operational guidance |

## Fail-Closed Posture

Replay contracts enforce strict validation:

- Unknown fields in payloads → rejected (additionalProperties: false in schema)
- Missing required fields → rejected
- Type mismatches → rejected
- Determinism violations (hash mismatch, non-monotonic timestamps, etc.) → exception raised
- Malformed hashes (wrong length, non-hex) → rejected

Design principle: **Better to fail loudly and preserve integrity than silently accept invalid data.**
