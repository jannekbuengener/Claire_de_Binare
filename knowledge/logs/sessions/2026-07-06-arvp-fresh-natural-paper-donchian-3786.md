# Session Log — #3786 Donchian Fresh Natural-Paper (Preflight Abort)

**Date:** 2026-07-06
**Scope:** RUNTIME-GO #3786 — bounded natural-paper observation `HYP-NP-DONCHIAN-01`
**Status:** DONE_MERGED — verdict `HOLD_RUNTIME_ABORT`

## Goal

Execute single 8h-bounded fresh natural-paper observation for `donchian_breakout_v1` / regime_segments gate.

## Delivered

- RUNTIME-GO documented on #3786 before preflight
- Campaign manifest: `manifests/campaign_3786_donchian_np_01.yaml`
- Evidence: `docs/evidence/arvp_fresh_natural_paper_donchian_3786.md`
- PR [#3787](https://github.com/jannekbuengener/Claire_de_Binare/pull/3787) squash-merged @ `0c19b047`

## Verdict

**`HOLD_RUNTIME_ABORT`** — `donchian_breakout_v1` has no runtime signal path; observation not started (strategy drift stop rule).

## Validation

- Safety flags on live stack: PASS
- Kill-switch: inactive
- cdb_readonly: 34256 correlation_ledger rows
- PR checks: ci + policy-gate green
- No 8h window executed

## GitHub

| Item | State |
|------|-------|
| #3786 | CLOSED (preflight abort delivered) |
| #3742 | OPEN — commented §5.2.4 disposition |
| #1900 | OPEN — commented North-Star impact |

## Boundaries

- LR NO-GO unchanged
- No Live-Go / Echtgeld-Go / natural_paper_evidence claim

## Follow-up (not created — blocked)

Runtime Donchian signal adapter in `services/signal` per #3748 §7.2 before re-attempt.
