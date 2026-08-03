# Session: #4258 Live Cursor Delivery and Approval Pilot v1

Date: 2026-08-03  
Branch: `dedicated/agent-skills-issue-4258`  
Base: `origin/main` @ `abf997d5` (PR #4301 foundation)  
Mode: Delivery (Plan-GO) — no merge, no `cdb-local-ci` publish

## Brain Evidence

- brain_source: repo-only / not-used (Context tools available, no enrichment records)
- repo_fallback_reason: insufficient_evidence

## Delivered

- Human-GO live gates on dispatch/preflight (`allow_live_cursor` + `human_go_live_cursor`)
- `CursorCloudApiDriver`: agentId idempotency, optional autoCreatePR under GO, live urllib transport, watch rehydrate
- Pilot/CLI: `--provider cursor-cloud-api --human-go-live-cursor --state --resume --auto-create-pr`
- Credential presence check (no secret values)
- GitHub delivery verify + scope allowlist
- Lifecycle pause at `AWAITING_APPROVAL` (no auto merge)
- Registry agent `acp-live-cursor-pilot` + env `cursor-live-pilot.v1`
- Runbook `docs/runbooks/agent_control_live_cursor_pilot.md`
- Offline unit tests (live pilot + mock regression + cursor providers)

## Controlled live attempt

- Human-GO: yes (Plan-GO)
- `CURSOR_API_KEY` present: **false**
- Result: `final_status=BLOCKED`, `provider_call_count=0`, no network
- Evidence: `artifacts/agent-control/pilot/live-20260803-precondition/` (local; redacted)

## Validation

- `pytest` live+mock+cursor provider suites: 47 passed (Windows pytest tmp cleanup noise ignored)
- `ruff check` on touched Python: pass
- `black --check` after format: pass
- `python -m tools.agent_control registry validate`: VALID

## Boundaries

- LR NO-GO unchanged
- Refs #4258 only (not Closes)
- No merge / no cdb-local-ci publish / no branch protection change
- Cursor Approval Agents: MANUAL_BOOTSTRAP_ONLY

## Follow-up for Issue closure

Operator must bootstrap `CURSOR_API_KEY`, re-run Human-GO live pilot once, capture provider_run_id + GitHub head + AWAITING_APPROVAL evidence, then allow `Closes #4258` in a later merge session.
