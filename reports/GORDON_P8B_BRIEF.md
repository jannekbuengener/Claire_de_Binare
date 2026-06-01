# Gordon Brief: Phase 8B - Deterministic risk_events Persistence

> **Orphaned / historisch** — Gordon/Docker-AI/MCP_DOCKER als Review-Gate ist
> **dekommissioniert** (#2689). Inhalt unten ist Archiv-Evidence; keine aktive
> Freigabe oder Blocker-Warteschlange. Entscheidungen: Jannek Human-GO +
> GitHub-live-before-ledger.

**Date:** 2026-02-15  
**Requester:** Claude Opus 4.5  
**Status:** ORPHANED (historisch: AWAITING GORDON REVIEW)

---

## Context

Phase 8B requires deterministic, idempotent persistence of risk_events. Current implementation writes directly to Postgres without idempotency guarantees. Replays can create duplicate rows.

**Current State:**
- `services/risk/service.py:388-416` - Direct INSERT, no ON CONFLICT
- `infrastructure/database/migrations/004_add_risk_events_table.sql` - SERIAL PK, no UNIQUE
- `decision_id` generated via counter-based UUID (not replay-deterministic)

---

## Questions for Gordon

### Q1: Write-Path Architecture

**Option A (Direct INSERT):**
- Risk service writes directly to Postgres
- `INSERT ... ON CONFLICT (decision_pk) DO NOTHING`
- Timeout ≤250ms, max 3 retries with backoff (50ms, 100ms)
- Existing pattern in codebase

**Option B (Redis Stream → db_writer):**
- Risk publishes to Redis stream
- db_writer consumer inserts idempotently
- Additional infrastructure, backpressure concerns

**My Recommendation:** Option A
- Matches existing risk_events persistence pattern
- db_writer currently does NOT consume risk_events (only signals/orders/trades via Pub/Sub)
- Simpler, fewer moving parts

**Gordon's Input Requested:** Confirm Option A or recommend Option B with justification.

---

### Q2: Idempotency Key

**Proposed:** Deterministic UUIDv5 as `decision_pk` column

```
decision_pk = uuid5(namespace, f"{symbol}:{ts_ms}:{input_snapshot_hash}")
```

Where `input_snapshot_hash` = SHA256 of sorted JSON containing:
- symbol, timestamp_ms, regime_id
- return_1m, return_5m, price_change_5m
- pct_change_15m, volume_15m
- daily_drawdown_pct, total_exposure_pct, slippage_pct
- staleness_s, data_silence_s
- thresholds dict

**Excluded (mutable):** decision_id, trace_id, service_version, git_sha

**Existing `decision_id`** stays as correlation ID (not PK).

**Gordon's Input Requested:** Confirm hash inputs or suggest alternatives.

---

### Q3: Retry Strategy

**Proposed:**
- Timeout: 250ms per attempt
- Retries: 3 total
- Backoff: 50ms after 1st fail, 100ms after 2nd fail
- Logging: 1 warning per retry, 1 final error if all fail
- Metric: `risk_events_persist_ok` (bool flag per decision)

**Failure Handling:**
- Decision logic remains independent (fail-closed on risk side)
- Persist failure = evidence debt (tracked via metric, not silent)

**Gordon's Input Requested:** Confirm retry params or adjust.

---

## Pitfalls I'm Aware Of

1. **Connection pool exhaustion** - Using existing `autocommit=True` pattern
2. **Statement timeout propagation** - Will SET per-query, not session-wide
3. **Hash collisions** - UUIDv5 is deterministic, collisions extremely unlikely
4. **Schema drift** - Will run drift guard check post-migration

---

## Expected Response Format

```
Q1: [A/B] + rationale
Q2: [APPROVED/MODIFY] + changes if needed
Q3: [APPROVED/MODIFY] + changes if needed
Pitfalls: [any additional concerns]
```

---

**Historisch:** Review wurde extern simuliert; kein aktiver Gordon-Gate mehr.

---

## Gordon Response (via MCP_DOCKER) — historisch, nicht operativ

**Consultation Date:** 2026-02-15
**Method:** Docker infrastructure inspection

### Infrastructure Findings

**Docker Version:** 29.2.0

**Stack Status:** `claire_de_binare` - restarting(1), running(12)
- Config: base.yml + compose.blue.yml + dev.yml

**Critical Services:**
| Service | Status | Image | Network |
|---------|--------|-------|---------|
| cdb_risk | running (healthy) | claire_de_binare-cdb_risk | cdb_network |
| cdb_db_writer | running (healthy) | claire_de_binare-cdb_db_writer | cdb_network |
| cdb_postgres | running (healthy) | postgres:15-alpine | cdb_network |

**Database State:**
- Database: `claire_de_binare`
- User: `claire_user`
- Applied migrations: 1.0.1, 1.0.2
- **CRITICAL: `risk_events` table does NOT exist** (Migration 004 not applied)

**Risk Service Logs:**
```
❌ Failed to persist risk_event: relation "risk_events" does not exist
```

### Gordon's Decisions

**Q1: Write-Path** → **OPTION A CONFIRMED**
- Risk service already writes directly to Postgres (existing pattern)
- db_writer does NOT consume risk_events (only signals/orders/trades)
- cdb_risk and cdb_postgres share cdb_network (direct connectivity confirmed)
- No additional Redis stream infrastructure needed

**Q2: Idempotency Key** → **APPROVED**
- `decision_pk` as deterministic UUIDv5 is correct approach
- Hash inputs confirmed: symbol, ts_ms, evidence fields
- Exclude mutable fields: trace_id, service_version, git_sha

**Q3: Retry Strategy** → **APPROVED WITH NOTE**
- 250ms timeout, 3 retries with 50ms/100ms backoff confirmed
- Note: Current state shows table doesn't exist - migration MUST be applied first
- Metric `risk_events_persist_ok` required for evidence debt tracking

### Additional Concerns (Gordon)

1. **Migration Gap:** Migration 004 exists in codebase but NOT applied to running DB
   - Schema version shows only 1.0.1, 1.0.2
   - Must apply migration 004 before implementing Phase 8B changes

2. **cdb_execution Restarting:** Service is in restart loop - unrelated but noted

3. **Env Consistency:** Both cdb_risk and cdb_db_writer use same POSTGRES_HOST/USER - good

### Gordon's Verdict

✅ **PROCEED WITH OPTION A**
- Apply migration 004 first (create risk_events table)
- Then apply migration 005 (add idempotency columns)
- Direct INSERT pattern confirmed as correct architecture

---

**Status (historisch):** GORDON APPROVED — Archiv only; Implementation-GO nur via Jannek + Live-Evidence
