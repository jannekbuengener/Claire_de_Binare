---
title: P1: Surface reject metadata for paper-trading E2E
status: open
priority: P1
---

# Summary
- TC-P0-001 and TC-P0-005 still only ever observe `REJECTED` results even after the order_results pipeline and risk service are stable.
- Without `reason_code`, `source_service`, `strategy_id`, `bot_id`, and `causing_event_id` the reject path cannot be diagnosed or trusted, so we cannot prove a FILLED path exists.
- We need instrumentation on the rejection path plus guard metadata so further E2E investigations can rely on deterministic signals instead of global resets.

# Context
- Benchmarks (#93) and the new E2E harness (#94/#113) are in place (see tests/e2e/test_paper_trading_p0.py) and circuit-breaker resets are deterministic.
- The existing E2E runs (with `E2E_RUN=1`, `E2E_DISABLE_CIRCUIT_BREAKER=1`, and `stream.bot_shutdown` reset) still report `status=REJECTED` for all orders and redis stream entries for `stream.bot_shutdown` only contain `{reason:'e2e circuit breaker', priority:'SAFETY'}`.
- We previously patched #224/#225 to get results into Redis/DB, so the gap is now purely observability: we can't trace rejects back to a real error or a fake fallback.

# Tasks for other agents
1. **Execution service** – ensure every publish to `TOPIC_ORDER_RESULTS`/`STREAM_ORDER_RESULTS` includes:
   - `source_service` (e.g. `execution` or `risk`)
   - `stage` (`risk`, `execution`, `db`, etc.) and `reason_code` for rejects
   - `causing_event_id` referencing the triggering signal/order
   - `strategy_id`/`bot_id`/`client_id`
2. **Risk service** – when sanitizing `OrderResult` before publishing, keep the reject reason and re-emit `bot_shutdown` entries that already include the metadata above so we can identify the guard producer.
3. **QA/Tests** – once metadata exists, extend the E2E smoke to assert at least one `FILLED` status under `E2E_DISABLE_CIRCUIT_BREAKER=1` and to match the new metadata fields.

# Technical Notes / Risks
- The goal is to diagnose rejects, not to artificially produce FILLED results; keep the DRY_RUN/paper logic unchanged.
- This issue blocks TC-P0-001/005 from proving a happy path, so keep it on the critical path until we can see a real FILLED entry (after both guard metadata and analysis).
