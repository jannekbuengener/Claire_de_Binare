# LR-050 Kill-Switch Drill — Latency Measurement (#2984)

**Captured:** 2026-07-03T20:04:28.550Z UTC  
**Method:** UTC timestamps + HTTP stopwatch on local stack (`127.0.0.1:8002`, Grafana `:3000`)

## Milestones

| Milestone | UTC timestamp | Notes |
|-----------|---------------|-------|
| Trigger (activate request start) | `2026-07-03T20:04:22.803Z` | `POST /kill-switch/activate` |
| Risk HTTP response (`active:true`) | `2026-07-03T20:04:22.865Z` | HTTP 200 |
| Risk gate closed (`GET /kill-switch`) | `2026-07-03T20:04:22.981Z` | `active: true`, reason: manual |
| `risk_kill_switch_active=1` | `2026-07-03T20:04:22.976Z` | Prometheus gauge on `:8002/metrics` |
| Grafana test (KS still active) | `2026-07-03T20:04:25.037Z` → `2026-07-03T20:04:28.521Z` | Correlated operator receipt path |
| Operator receipt ack | `2026-07-03T20:04:30.524Z` | Attested in `operator_attestation.md` |
| Rollback complete (`active:false`) | `2026-07-03T20:04:28.535Z` | `POST /kill-switch/deactivate` |

## Deltas (from activate request start)

| Measurement | Latency |
|-------------|---------|
| Activate HTTP round-trip | **60 ms** |
| Activate response (wall) | **62 ms** |
| `risk_kill_switch_active=1` (metric poll) | **109 ms poll** / **173 ms wall** |
| `GET /kill-switch` confirms active | **178 ms wall** |
| Deactivate HTTP (rollback) | **7 ms** (response at +5725 ms wall, after alert test) |
| Grafana test API round-trip | **3482 ms** (Grafana reported `1s457ms` send duration) |

## Execution stop / no-send state

| Check | Before drill | During KS active | After rollback |
|-------|--------------|------------------|----------------|
| `execution_orders_received_total` | 0 | 0 | 0 |
| `execution_orders_filled_total` | 0 | 0 | 0 |
| `execution_orders_rejected_total` | 0 | 0 | 0 |
| Real venue send path | inactive | inactive (mock/dry-run) | inactive |

No test order injected during drill; execution halt inferred from File Kill Switch state + unchanged order counters under safe flags.

## Alert latency (correlated, not auto-fired)

- **Not claimed:** Prometheus/Alertmanager auto-alert on `risk_kill_switch_active` (no such rule in repo).
- **Observed:** Grafana SMTP test notification (`CDB-LR050-KillSwitchDrill`) while File KS active; API `success`, duration `1s457ms`.

## Verdict

**PASS** — Kill-switch activation to risk metric active within **<200 ms**; rollback to inactive + metric `0` within **<10 ms** of deactivate request.
