# LR-050 Runtime Dry-Run — Logs (Redacted)

**Captured:** 2026-07-03T19:47:47Z UTC  
**Sources:** `docker logs cdb_execution`, `docker logs cdb_risk` (trimmed, no secrets)

## Execution startup (non-send configuration)

```text
2026-07-01 00:50:25,052 - execution_service - INFO - Mode: MOCK
2026-07-01 00:50:25,052 - execution_service - INFO - Trading config: TRADING_MODE=(unset) DRY_RUN=True MOCK_TRADING=True
2026-07-01 00:50:25,228 - execution_service - INFO - Using execution adapter: mock_builtin (Paper Trading Mode)
2026-07-01 00:50:25,248 - execution_service - INFO - Database initialized
```

## Execution — absence of venue send signals

Searched full `cdb_execution` logs for: `place_market`, `place_limit`, `MEXC Client initialized`, `LIVE mode`, `contract.mexc`.

**Result:** No matches for venue order placement or live client initialization. Only startup config lines above match MEXC/LIVE-related patterns.

Recent tail (health/metrics only):

```text
2026-07-03 19:46:10,432 - werkzeug - INFO - 127.0.0.1 - - [03/Jul/2026 19:46:10] "GET /health HTTP/1.1" 200 -
2026-07-03 19:46:22,774 - werkzeug - INFO - 172.19.0.7 - - [03/Jul/2026 19:46:22] "GET /metrics HTTP/1.1" 200 -
```

## Risk — gating active (regime risk-off)

```text
2026-07-03 19:39:58,858 [INFO] risk_manager: Regime-Update: HIGH_VOL_CHAOTIC (risk_off=True)
2026-07-03 19:42:00,839 [INFO] risk_manager: Regime-Update: HIGH_VOL_CHAOTIC (risk_off=True)
2026-07-03 19:43:58,848 [INFO] risk_manager: Regime-Update: HIGH_VOL_CHAOTIC (risk_off=True)
2026-07-03 19:45:58,863 [INFO] risk_manager: Regime-Update: HIGH_VOL_CHAOTIC (risk_off=True)
```

Risk service healthy; regime classification driving `risk_off=True` — consistent with allocation gating.

## Kill-switch status log (via API, not drill)

```text
GET /kill-switch → active=false, message="Deactivated by d4-teardown: delta4 verify done"
```

## Redaction policy applied

Excluded from this file:

- Passwords, tokens, API keys, DSNs
- Private email addresses
- Account IDs
- Secret file contents

## What this does not claim

- No kill-switch activation drill (#2984)
- No injected end-to-end order through risk→execution on live stack
- No receiver/alert proof (covered separately by #2981)
