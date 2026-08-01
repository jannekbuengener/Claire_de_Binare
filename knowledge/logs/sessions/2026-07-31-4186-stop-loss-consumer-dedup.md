# Session 2026-07-31 — #4186 restart-safe stop-loss consumer with dedup state

## Scope

Issue #4186: implement a deterministic stop-loss consumer with a unique price
trigger and a restart-safe persistent dedup state, so one protection event
produces exactly one reduce-only exit intent despite restart, replay, or double
delivery. Missing, corrupt, unknown, or contradictory state must block
fail-closed.

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

`cdb_context_briefing` (briefing_id `f35c22fc72659e48`) returned
`operator_trust_level=LOW`, `readiness=blocked_missing_context`, and no
evidence/claim/decision/memory records; symbol hits came back as
`<mocked>/path/to/...`. Tool was available, so `insufficient_evidence` is the
correct classification — not `unavailable`. Repo and GitHub truth were the basis.

## Delivery

- Branch: `dedicated/runtime-risk-issue-4186`
- Code commit: `4b3c1b39313551fabd15b797d92a3f7177c7b387`
- Evidence commit: `27d87b7abdcce1b54cc35ea84b72232a9bb12d50`
- PR: #4233 (open, not merged)
- Router: `CREATE_DEDICATED_PR` / `DEDICATED_RULE_MATCH` / lane `runtime-risk`
- Follow-up: #4234 (real-stack persistence of the dedup ledger)

New surfaces: `core/safety/stop_loss/` (contracts, exit intent, dedup state,
consumer, shadow harness), `tools/safety/stop_loss_consumer_evidence.py`,
`docs/contracts/SAFETY_STOP_LOSS_CONSUMER_CONTRACT_V1.md`.

## Validation

- Full CI-equivalent suite: 8984 passed, 76 skipped
 (`pytest -q -k "not test_mcp_time_server_runtime"`)
- Targeted safety scope: 172 passed
- Executed scenarios D1–D11 all PASS via the evidence generator (real consumer
 runs, not test-name mirroring)
- Mock/shadow replay: 7-candle fixture, restart at step 4, exactly one unique
 exit intent, all post-restart steps `DUPLICATE_SUPPRESSED`
- `ruff check .` clean, `black --check` clean on changed scope,
 `git diff --check` clean, `gitleaks protect --staged` no leaks

## Decisions worth remembering

- The protection `event_id` deliberately excludes the observing tick but
 includes the position epoch: repeated ticks under the same armed stop collapse
 into one event, while a reopened position cannot be swallowed by an old record.
- A dedup record left `PREPARED` after a restart means "delivery unproven" and
 blocks permanently. It is never retried into a second intent.
- An absent state file is never read as an empty state; the store must be
 explicitly initialized.
- The evidence manifest is generated *after* the code commit and carries
 `worktree_dirty`, so `commit_sha` names the commit actually exercised. A guard
 test fails if the committed artifact drifts from current behaviour.
- An earlier draft cached position epochs in a module-global dict; replaced with
 a field on the event to avoid hidden cross-process state.

## Boundaries

- Protection status stays `UNAVAILABLE`; two gaps open
 (`real_stack_persistence_proven` → #4234,
 `productive_exit_path_proven` → #4184 / PR #4187, untouched)
- No merge, no issue close, no Full Fast-CI, no `cdb-local-ci` publish
- No productive exit/queue adapter, no MEXC call, no risk-limit change, no
 productive DB migration, no MCP mutation, no BLUE/RED change
- Hosted Actions red on every open PR (billing-lock, #4167) — infra, not a code
 failure from this slice
- LR `NO-GO` unchanged; board stage `trade-capable` is not a live go
