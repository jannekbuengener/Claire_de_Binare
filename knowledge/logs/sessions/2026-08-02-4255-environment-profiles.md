# Session: #4255 Governed Execution Profiles + Environment Preflight

Date: 2026-08-02
Worktree: `cdb-wt-4250-acp-canon`
Branch: `batch/agent-skills-issue-4250`
Target PR: [#4286](https://github.com/jannekbuengener/Claire_de_Binare/pull/4286)
Issue: [#4255](https://github.com/jannekbuengener/Claire_de_Binare/issues/4255)
Parent: [#4249](https://github.com/jannekbuengener/Claire_de_Binare/issues/4249)

## Brain Evidence

- `brain_source: repo-only` / `brain_status: not-used`
- Context MCP tools absent in this Cursor surface (`insufficient_evidence`)

## Delivered

- Six governed profiles under `config/agent-control/profiles/environments/`
- `.cursor/environment.json` (official schema; `ci/Dockerfile` ref; `agentCanUpdateSnapshot: false`)
- Vendored `docs/contracts/cursor_environment.schema.json`
- `tools/agent_control/environment/` doctor + attenuation + cursor config validation
- CLI: `python -m tools.agent_control environment validate|doctor`
- Preflight/ProviderRequest wiring; durable live-dispatch gates
- `acp-cursor-sdk-adapter` bound to `cdb-agent-skills.v1`
- Unit tests + fixtures under `docs/contracts/examples/agent_environment/`

## Validation (targeted)

- `python -m tools.agent_control environment validate --config config/agent-control`
- Offline doctor for all six profiles → `READY_OFFLINE_ONLY`, `execute_ready=false`
- Cursor dry-run contract → `preflight_ok=true`
- `pytest` governance suite (registry/execution/dispatcher/cursor/environment): 131 passed
- `validate_root_layout` / `validate_readme_links` / `validate_onboarding_docs`: PASS
- `ruff` + `black --check` on changed Python: PASS

## Non-goals / negative claims

- `live_cursor_run_executed=false`
- `live_cursor_environment_setup_executed=false`
- `cursor_api_key_accessed=false`
- `live_cursor_dispatch_enabled=false`
- not `#4256` evidence bundle; not merge; not `cdb-local-ci`; not issue close

## Status

`DONE_SLICE_ADDED_TO_BATCH_PR`

**Final head:** `21b585e0535d45d657d0e0e58c114ad2ce2bc170`
**PR:** https://github.com/jannekbuengener/Claire_de_Binare/pull/4286 (draft, open)
