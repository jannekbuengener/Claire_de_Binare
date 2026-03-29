# LR-002: Stack Snapshot (Pre-Flight Context)

**Date:** 2026-02-04
**Baseline:** main@81955684 (post PR #790)
**Purpose:** Stack context for Contract Tests implementation

---

## Stack Map (Services + Responsibilities)

| Service | Responsibility | Entry Point |
|---------|---------------|-------------|
| **allocation** | Trade allocation decisions | `services/allocation/service.py` |
| **candles** | Aggregates market_data → 1m candles stream | `services/candles/service.py` |
| **db_writer** | Persists events/trades to Postgres | `services/db_writer/db_writer.py` |
| **execution** | Executes trades (paper/live) | `services/execution/service.py` |
| **market** | Market data ingestion | `services/market/service.py` |
| **regime** | Market regime detection | `services/regime/service.py` |
| **reports** | Generates reports | `services/reports/` |
| **risk** | **Risk gating + Decision Contract 0/1** | `services/risk/service.py` |
| **signal** | Signal generation | `services/signal/service.py` |
| **validation** | 72h validation gate logic (library/CLI, not compose-wired) | `services/validation/runner.py` |
| **ws** | WebSocket data ingestion | `services/ws/service.py` |

**Total:** 11 compose-wired services + 1 library/CLI component (validation)

---

## Where Contracts Live

### 1. Decision Contract 0/1 v1
**Location:** `services/risk/service.py:152-277`

**Function:** `decide_trade(signal, market_state, account_state, market_health, now_ms) -> (decision, reason_code, evidence)`

**Outputs:**
- `decision`: "ALLOW" or "BLOCK"
- `reason_code`: RC_001 - RC_022 (8 codes defined inline)
- `evidence`: dict with contract_version, thresholds, inputs

**Reason Codes (inline, not centralized):**
- RC_001: Circuit Breaker active
- RC_002: Panic Mode (returns/price_change thresholds)
- RC_003: Stale Data (>5s)
- RC_004: Data Silence (>30s no ticks)
- RC_010: Signal quality insufficient
- RC_020: Daily Drawdown Limit
- RC_021: Total Exposure Limit
- RC_022: Slippage too high

**Version:** `DECISION_CONTRACT_VERSION = "decision_contract_v1"` (line 91)

### 2. Message Contracts (JSON Schemas)
**Location:** `docs/contracts/`

**Files:**
- `market_data.schema.json` - Market data message schema
- `signal.schema.json` - Signal message schema

**Validation:** `.github/workflows/contracts.yml` (pytest + JSON validation)

### 3. Contract Tests
**Current Location:** `tests/unit/risk/test_decision_contract.py` (16 tests)
**Empty Directory:** `tests/contract/` (exists but unused)

**Test Coverage:**
- All 8 Reason Codes (RC_001 - RC_022) ✅
- ALLOW case ✅
- Determinism test ✅
- Marker: `@pytest.mark.unit`

---

## Dataflow Hints (Streams/Topics/Redis Keys)

### Redis Streams (XADD/XREAD)
**Pattern Found:** Services use Redis Streams for event-driven communication

**Confirmed Streams:**
- `stream.candles_1m` - Candles service output (candles/config.py:30)
- `stream.signals` - Signal service output (inferred from tests)
- `stream.allocation_decisions` - Allocation service output (inferred)
- `stream.regime_signals` - Regime service output (inferred)

**Message Flow:**
```
WS → market_data (pubsub) → Candles → stream.candles_1m → Regime/Signal
Signal → stream.signals → Allocation
Allocation → stream.allocation_decisions → Risk → Execution
```

**Key Insight:** Risk service receives pre-aggregated data from upstream services. Decision Contract validates inputs before execution.

### Contracts at Boundaries
1. **WS → Candles:** market_data pubsub (schema: market_data.schema.json)
2. **Signal → Allocation:** stream.signals (schema: signal.schema.json)
3. **Allocation → Risk:** Validated in `decide_trade` function (Decision Contract)
4. **Risk → Execution:** decision + reason_code gates execution

---

## Where CI Enforces What

### 1. `.github/workflows/contracts.yml`
**Job:** `validate-contracts`

**Triggers:**
- Push/PR to main
- Changes in `docs/contracts/**` or `tests/unit/contracts/**`

**Enforcement:**
- Runs `pytest tests/unit/contracts/test_contracts.py -v`
- Validates JSON schema syntax for market_data.schema.json, signal.schema.json
- Reports: "19 tests" (per workflow summary)

**Status:** ✅ Active (validated in contracts.yml:36-38)

### 2. `.github/workflows/ci.yaml`
**Jobs:** `Tests (Python 3.11/3.12)`

**Triggers:** All pushes/PRs to main

**Enforcement:**
- Runs `pytest -v -m "not e2e and not local_only"` (ci.yaml:221)
- **Includes:** `tests/unit/risk/test_decision_contract.py` (via unit marker)
- **E2E Job:** Runs `pytest -q tests/e2e/test_smoke_pipeline.py`

**Status:** ✅ Active (contracts are tested in unit suite)

### 3. Required Checks (Ruleset 11617228)
**From GATE 0 Evidence:**
- `ci (Unit/Integration + Lint gesammelt)` ✅ Includes decision_contract tests
- `E2E Happy Path` ✅ May exercise contracts end-to-end

**Gap:** No explicit "Contract Tests" job (contracts hidden in unit tests)

---

## Risks/Unknowns

1. **Reason Codes Not Centralized**
   - RC_001 - RC_022 defined inline in services/risk/service.py:230-275
   - No enum, no constants file, no documentation
   - Risk: Code duplication if other services need same codes

2. **Contract Tests Misplaced**
   - Contract tests in `tests/unit/risk/` instead of `tests/contract/`
   - Empty `tests/contract/` directory suggests intent but not implemented
   - Risk: Contracts not discoverable as first-class test category

3. **No Contract Tests Job in CI**
   - Contracts tested as "unit tests" in main CI job
   - No explicit pytest marker `@pytest.mark.contract`
   - Risk: Cannot enforce/track contract coverage independently

4. **Schema Validation Decoupled from Implementation**
   - JSON schemas in `docs/contracts/` validated separately
   - Risk service `decide_trade` function has no direct link to schemas
   - Risk: Schema drift from actual message formats

5. **Limited Contract Surface Documentation**
   - No centralized "Contract Catalog" or registry
   - Decision Contract thresholds hardcoded in DECISION_THRESHOLDS dict
   - Risk: Contracts change without version bumps or changelog

---

## Recommendation for LR-002

**Goal:** Make Contract Tests explicit, enforceable, and auditable in CI.

**Actions:**
1. Centralize Reason Codes → `services/risk/reason_codes.py`
2. Move tests → `tests/contract/test_decision_contract.py`
3. Add pytest marker → `@pytest.mark.contract`
4. Create CI job → "Contract Tests" (explicit, runs `pytest -m contract`)
5. Document → `LR-002-EVIDENCE.md` with CI proof

**DoD:** CI shows "Contract Tests: PASS" as separate check, not buried in unit tests.

---

**Snapshot Complete:** 2026-02-04 13:00 UTC
