# Session 2026-08-04 — #4153 Sensitivity Campaign BLOCKED

## Status

`BLOCKED_CAMPAIGN_PROVENANCE_RESIDUALS`

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

## Live Truth

- `origin/main` @ `10ddcc099a978be3435dd0da376c1196a0aaa452`
- Preflight: `READY_FOR_REPLAY_SENSITIVITY` (7/7)
- #4153 OPEN; #4148/#4149/#4150/#4151 CLOSED
- #4335/#4336 OPEN
- PR #4333/#4334 MERGED
- Router: `CREATE_NEW_BATCH_PR` / lane `validation-research`

## Blocker

R8 fail: `strategy_replay_runner._load_dataset_result` drops
`request_fingerprint`/`content_fingerprint` on `file` and `binance_window`
(39 Stage-A path). Residual #4335. No campaign runs. No scope into #4335/#4336.

## Issue comments

- https://github.com/jannekbuengener/Claire_de_Binare/issues/4153#issuecomment-5172790233
- https://github.com/jannekbuengener/Claire_de_Binare/issues/4147#issuecomment-5172790212
- https://github.com/jannekbuengener/Claire_de_Binare/issues/4335#issuecomment-5172790347

## Boundaries

LR=NO-GO. No paper/live/echtgeld. No holdout. No gate changes.
