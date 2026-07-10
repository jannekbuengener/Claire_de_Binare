# Session: ARVP diagnostic telemetry execute terminal (#3967)

**Date:** 2026-07-10  
**Issue:** #3967  
**Verdict:** FAIL_FALSE_ZERO_EVENT_REPRODUCED  
**Terminal:** 2026-07-10T13:32:07Z

## Summary

2h diagnostic run completed. Donchian emitted 10 signals; supervisor/ledger counts 0 (false zero) due to signal_id/event_pk collision with 2026-02-15 ledger rows. PB1 idle (true zero). campaign_id propagation unproven. Baseline restored.

## Evidence

- `docs/evidence/arvp_diag_telemetry_verification_run.md`
- Local: `artifacts/campaigns/arvp_diag_p15_*`
