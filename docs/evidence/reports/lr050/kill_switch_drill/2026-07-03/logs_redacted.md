# LR-050 Kill-Switch Drill — Logs (Redacted) (#2984)

**Window:** 2026-07-03T20:04:22Z — 2026-07-03T20:04:29Z UTC  
**Source:** `docker logs cdb_risk --since 5m` (filtered)

## cdb_risk — kill-switch activate

```text
2026-07-03 20:04:22,849 [WARNING] core.safety.kill_switch: KILL-SWITCH ACTIVATED - ALL TRADING STOPPED
2026-07-03 20:04:22,850 [WARNING] core.safety.kill_switch: Reason: manual
2026-07-03 20:04:22,862 [WARNING] core.safety.kill_switch: Message: LR-050 kill-switch drill #2984 (operator: lr050-drill-operator)
2026-07-03 20:04:22,862 [WARNING] core.safety.kill_switch: Activated at: 2026-07-03T20:04:22.836477
2026-07-03 20:04:22,864 [INFO] werkzeug: POST /kill-switch/activate HTTP/1.1" 200
2026-07-03 20:04:22,981 [INFO] werkzeug: GET /kill-switch HTTP/1.1" 200
```

## cdb_risk — kill-switch deactivate (rollback)

```text
2026-07-03 20:04:28,532 [INFO] core.safety.kill_switch: Kill-switch state updated: inactive (reason: none)
2026-07-03 20:04:28,532 [WARNING] core.safety.kill_switch: KILL-SWITCH DEACTIVATED - TRADING RESUMED
2026-07-03 20:04:28,532 [WARNING] core.safety.kill_switch: Operator: lr050-drill-operator
2026-07-03 20:04:28,532 [WARNING] core.safety.kill_switch: Justification: LR-050 drill rollback complete #2984
2026-07-03 20:04:28,533 [INFO] werkzeug: POST /kill-switch/deactivate HTTP/1.1" 200
2026-07-03 20:04:28,537 [INFO] werkzeug: GET /kill-switch HTTP/1.1" 200
```

## cdb_execution — drill window

No kill-switch-related log lines in the 5-minute window; no order processing events. Order counters remained at zero.

## Redaction

- No secret values, DSNs, passwords, tokens, or API keys
- No email addresses or account identifiers
- No real order IDs
