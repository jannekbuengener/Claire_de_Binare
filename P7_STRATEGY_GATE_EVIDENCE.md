# PHASE 7 – STRATEGY GATE VALIDATION (RC_010) + RC_004 CLASSIFICATION

**Date:** 2026-02-14 22:30 UTC
**Validator:** Claude Opus 4.5
**Stack Status:** 10/10 services healthy

---

## A) RC_010 Validation: pct_change_15m

### Source of Truth

Signal Engine uses **tick-buffer** for pct_change calculation, not candle deltas.

```
stream.signals sample:
  pct_change_15m: 0.010389567330975995 (1.04%)
  volume_15m: 0.00228247
```

### Threshold Check

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| pct_change_15m | 0.0104 (1.04%) | 0.03 (3.0%) | **BELOW** |
| volume_15m | 0.00228 | 0.165 | **BELOW** |

### Verdict

**RC_010 confirmed CORRECT**

Signal quality insufficient for trade execution. Market is quiet.

---

## B) RC_004 Classification: Data Silence

### Occurrence Pattern

```
Total decisions:  75
RC_004 blocks:    42 (56%)
RC_001 blocks:    30 (40%)
RC_010 blocks:    3  (4%)
```

### Root Cause

**Config Inconsistency:**

| Parameter | Value |
|-----------|-------|
| market_state update cadence | 60s (candle-close) |
| data_silence_s threshold | 30s |

This creates a **deterministic RC_004 window** of 30-60s after each candle close.

```
Timeline per minute:
  0-30s:  data_silence_s < 30  → RC_004 PASS
  30-60s: data_silence_s > 30  → RC_004 BLOCK
```

### Classification

**CONFIG INCONSISTENCY** – deterministic behavior under current cadence

Not a bug. Not a feature. A mismatch between update frequency and threshold.

**No fix in P7** – evidence-only phase.

---

## C) Decision Trace Snapshot

```json
{
  "contract_version": "decision_contract_v1",
  "decision_id": "dec-1771108400412",
  "timestamp_ms": 1771108400412,

  "signal_inputs": {
    "signal_id": "sig-ed54bae18fe052a28daa05be0ce7b89e",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "price": 69981.31,
    "pct_change_15m": 0.010389567330975995,
    "volume_15m": 0.00228247,
    "ts_ms": 1771108399000
  },

  "market_state_snapshot": {
    "symbol": "BTCUSDT",
    "regime_id": 1,
    "return_1m": 0.0005231274069007139,
    "return_5m": 0.0010687116810142653,
    "close_now": 69981.31,
    "last_tick_ts_ms": 1771108380232,
    "ts_ms": 1771108380682
  },

  "derived_values": {
    "staleness_s": 1.41,
    "data_silence_s": 20.18
  },

  "gate_evaluation": [
    {"gate": "RC_002", "value": 0.00052, "threshold": -2.0, "passed": true},
    {"gate": "RC_003", "value": 1.41, "threshold": 5.0, "passed": true},
    {"gate": "RC_004", "value": 20.18, "threshold": 30.0, "passed": true},
    {"gate": "RC_001", "value": 1, "allowed": [0,1], "passed": true},
    {"gate": "RC_010", "value": 0.0104, "threshold": 0.03, "passed": false}
  ],

  "final_decision": {
    "decision": "BLOCK",
    "reason_code": "RC_010",
    "first_failing_gate": "RC_010"
  }
}
```

---

## D) Known Issues

### D.1 risk_events Table Missing

```
ERROR: relation "risk_events" does not exist
```

**Impact:** Audit trail persistence broken.
**Severity:** MEDIUM – Forensics/audit capability degraded.
**Action:** Create table via migration before production.

### D.2 Positions State Mismatch

```
Positions table: EMPTY
Orders table: NET -0.60801014 BTC
```

**Impact:** Risk manager started with empty state.
**Severity:** LOW for paper trading.
**Action:** Run `reconcile_positions.py` before live.

---

## Summary

| Item | Status | Classification |
|------|--------|----------------|
| RC_010 | **CORRECT** | Market quiet, no trade |
| RC_004 | **CONFIG INCONSISTENCY** | 60s cadence vs 30s threshold |
| Decision Trace | **CONSISTENT** | RC_010 first-fail |
| risk_events | **MISSING** | DB migration needed |

### Stop Condition Met

**RC_010 confirmed correct → Market Condition: No Trade**

No code changes. No threshold tuning. Evidence-only validation complete.
