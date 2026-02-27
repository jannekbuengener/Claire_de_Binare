# LR-021 Evidence: Redis Stream Export — Slice 3

**Issue:** #925
**Scope:** Offline, read-only tooling that exports Redis Stream events (DECISION / ORDER / FILL) as envelope.v1 JSONL for `lr021_replay` strict validation.

## What Was Built

| File | Purpose |
|------|---------|
| `scripts/replay/lr021_export_redis.py` | CLI tool: Redis Stream -> envelope.v1 JSONL exporter |
| `tests/unit/replay/test_lr021_export_redis.py` | 29 tests: parsing, streaming, determinism, replay roundtrip |

## Guardrails Satisfied

| Guardrail | How |
|-----------|-----|
| Read-only Redis | Uses `XRANGE` only. No writes, no consumer-group mutations, no `XACK`. |
| Toggle OFF = zero side effects | Tool is a standalone CLI script; no imports in service hotpaths. |
| No breaking changes | Purely additive: new files only, no existing files modified. |
| Backward compatible | `policy_*` fields only emitted when present (not None). |
| Deterministic output | Uses `canonical_json_dumps()` from `core/replay/canonical_json.py`. Same input -> byte-identical output. |
| No hash duplication | `compute_event_hash` / `compute_chain_hash` imported from `scripts/replay/lr021_replay.py` (single source of truth). |
| Streaming / no full-RAM collect | `iter_stream_entries()` is a generator — entries are read in batches and yielded immediately. |

## How to Use

### Basic export (raw envelopes, no hashes — recommended for replay):

```bash
python scripts/replay/lr021_export_redis.py \
    --redis-url redis://localhost:6379 \
    --stream lr021:events \
    --out artifacts/exported.jsonl
```

Then validate with `lr021_replay`:

```bash
python scripts/replay/lr021_replay.py \
    --input artifacts/exported.jsonl \
    --output artifacts/replayed.jsonl
```

### Filter by event type:

```bash
python scripts/replay/lr021_export_redis.py \
    --stream lr021:events \
    --type DECISION --type ORDER \
    --out artifacts/decisions_orders.jsonl
```

### With hashes (opt-in):

```bash
python scripts/replay/lr021_export_redis.py \
    --stream lr021:events \
    --include-hashes --compute-chain-hash \
    --out artifacts/with_chain.jsonl
```

### ID range + limit:

```bash
python scripts/replay/lr021_export_redis.py \
    --stream lr021:events \
    --start-id 1700000000000-0 \
    --end-id 1700000005000-0 \
    --limit 100 \
    --out artifacts/range.jsonl
```

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--stream` | (required) | Redis stream key to read from |
| `--redis-url` | `redis://localhost:6379` | Redis connection URL |
| `--out`, `-o` | stdout | Output JSONL file path |
| `--start-id` | `-` (beginning) | Start stream ID (inclusive) |
| `--end-id` | `+` (end) | End stream ID (inclusive) |
| `--limit` | None (all) | Maximum entries to read |
| `--type` | None (all) | Filter by event type (repeatable) |
| `--include-hashes` | off | Compute and include `event_hash` |
| `--compute-chain-hash` | off | Also compute `chain_hash` (implies `--include-hashes`) |
| `--batch-size` | 1000 | XRANGE batch size |

## Deterministic Guarantees

1. **Ordering**: Entries are read via `XRANGE` in Redis ID order (monotonic, server-assigned).
2. **Serialization**: Every output line uses `canonical_json_dumps()` — sorted keys, compact separators, None-omitted, float-sanitized.
3. **Hashing** (when opt-in): Uses the same `compute_event_hash` / `compute_chain_hash` as `lr021_replay.py`.
4. **Idempotent**: Same stream range -> byte-identical output file.

## Stream Entry Format

The exporter accepts three Redis Stream field layouts:

| Strategy | Field | Content |
|----------|-------|---------|
| (a) JSON blob | `envelope` | JSON-encoded envelope.v1 dict |
| (b) JSON blob | `data` | JSON-encoded envelope.v1 dict |
| (c) Flat fields | `schema_version`, `event_type`, `event_id`, `ts_ms`, `payload`, ... | Individual string fields |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Default output | Raw envelopes (no hashes) | Replay runner computes hashes; including them by default would pollute the hash input |
| Hash opt-in | `--include-hashes` flag | Useful for spot-checking; replay roundtrip verifies correctness |
| Streaming iterator | Generator pattern | Never collects full stream in RAM; safe for production-sized streams |
| Hash functions | Imported from `lr021_replay.py` | Single source of truth; no drift risk |
| Redis dependency | Lazy import | `redis` package only needed for CLI; unit tests use `FakeRedis` |
