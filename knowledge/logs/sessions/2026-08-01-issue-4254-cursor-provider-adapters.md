# Session: Issue #4254 Cursor Provider Adapters

Date: 2026-08-01 (Europe/Berlin)
Status: `DONE_SLICE_ADDED_TO_BATCH_PR`
PR: #4286 (`batch/agent-skills-issue-4250`)
Final head: `4c1465e7265c648c64f226973879366eb05a418a`
Routing: `OPERATIONAL_BATCH_CONTINUATION` (router returned `CREATE_NEW_BATCH_PR` only for `ISSUE_COMPATIBILITY_METADATA_INCOMPLETE`)
GitHub writes: PR body marker/ledger updated; comments on PR #4286, Issues #4254 and #4249

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: partial
context_trust_level: none
records_found: none
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
```

## Delivered

- Additive `provider_work_order` on `cdb.agent_execution.v1` (`schema_version` 1.0.0|1.1.0)
- Cursor drivers: `cursor-sdk`, `cursor-cli`, `cursor-cloud-api` behind existing Provider protocol
- Offline capability snapshots, CLI `provider` surface, registry profiles + `acp-cursor-sdk-adapter`
- Fake/recorded tests; live Cursor dispatch fail-closed (`CURSOR_ENVIRONMENT_PROFILE_NOT_READY`)

## Validation

- `pytest -q` cursor + dispatcher + registry + execution contract + pr-routing: PASS
- `python -m tools.agent_control provider capabilities --provider cursor-{sdk,cli,cloud-api} --offline`
- Cursor dry-run contract: `preflight_ok=true`, zero provider calls
- `registry validate`, `ruff check`, `black --check`, `git diff --check`
- `validate_readme_links`, `validate_onboarding_docs`

## Negative claims

- `live_cursor_run_executed=false`
- `cursor_api_key_accessed=false`
- `provider_live_mutation=false`
- `not_agent_run_evidence_bundle_v1`
- `not_final_ci` / `not_cdb_local_ci` / `not_approval` / `not_merge_authority`

## Residuals

- #4255 Environment profiles
- #4256 Agent Run Evidence Bundle
- #4257 Approval Agent / Policy
