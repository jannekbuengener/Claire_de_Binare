# Session Log: donchian_breakout_v1 Runtime Signal Adapter (#3789)

**Date**: 2026-07-06  
**Issue**: #3789  
**PR**: #3790 → squash-merged @ `219ff460`  
**Status**: DONE_MERGED

## Scope

Runtime signal path for `donchian_breakout_v1` in `services/signal` per Pack-A frozen spec (#3748 §7.2). No Docker, no paper run, no RUNTIME-GO.

## Delivered

- `services/signal/service.py`: `_process_donchian_breakout_v1`, dispatch before momentum fallback
- `services/signal/config.py`: `SIGNAL_ENTRY_CHANNEL_BARS` / `SIGNAL_EXIT_CHANNEL_BARS` (defaults 20/10)
- Tests: `tests/unit/signal/test_donchian_breakout_v1_deterministic.py` (7 cases) + dispatch regression in `test_service.py`
- Docs: `SERVICE_CATALOG.md`, `services/signal/README.md`

## Validation

- Local: `pytest -q tests/unit/signal/` — 64 passed
- CI PR #3790: all required checks green (ci, policy-gate)

## Boundaries

- LR **NO-GO** unchanged
- No live/echtgeld path changes
- No natural_paper_evidence claim

## Follow-up

- New fresh-paper execute issue + explicit RUNTIME-GO before observation (do not silently retry #3786)
- #3742 tracker stays OPEN
