# Session: Batch-Head CI Repair (PR #4286 / #4254 context)

Date: 2026-08-02 (Europe/Berlin)
Branch: `batch/agent-skills-issue-4250`
PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/4286
Start head: `42c344f7781e5741a471f0cbc98ca077aac150b6`
Final head: `ff1dfb671d6ed4bb4f9d1cc6cfeb404c1b3f7e19`
Status: `DONE_BATCH_HEAD_CI_REPAIR_ADDED_TO_BATCH_PR`

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- context_tool_status: partial
- context_trust_level: none
- records_found: none
- repo_fallback_reason: insufficient_evidence

## Router

- `python -m tools.pr_routing route --issue 4254 --agent cursor`
- Machine decision: `CREATE_NEW_BATCH_PR` (ISSUE_COMPATIBILITY_METADATA_INCOMPLETE)
- Operational continuation on existing draft PR #4286 / `batch/agent-skills-issue-4250` (accepting_slices; no new PR)

## Reproduced failures (on 42c344f)

1. Black: `tests/unit/governance/test_agent_registry_v1.py`
2. Clock/UUID guard: `tools/agent_control/clock.py`, `dispatch.py`, `tools/agent_execution_contract/handoff.py`
3. Context smoke: two intentional `negative_plaintext_secret.json` fixtures
4. Root layout: unused `requirements-providers.txt`

## Repairs

- Black-format registry test
- Agent-control SystemClock + handoff via `core.utils.clock.utcnow` (tz-aware UTC preserved)
- `generate_runtime_id_hex` in `core/utils/uuid_gen.py`; dispatch `_new_run_id` uses it
- Smoke excludes for the two negative fixtures (documented)
- Removed unused root placeholder `requirements-providers.txt`
- Hosted follow-up: stage status flush + artifact upload; unshallow `origin/main` fetch for status-freshness; keep orchestrator invocation contract (`python ci/scripts/run.py --profile fast`)

## Commits

1. `1ab990aa` — `fix(agents): restore batch CI invariants (#4254)`
2. `9f00c1bc` — `fix(ci): surface fast-profile stage status and upload evidence`
3. `ff1dfb67` — `fix(ci): restore hosted fast-profile diagnostics without breaking contracts`

## Validation

- Local targeted: clock/smoke/root-layout, governance suite, uuid helper, registry validate, offline capabilities, cursor dry-run, ruff/black, readme/onboarding links, `git diff --check`
- Local Fast-CI (clean Py3.12): PASS
- Hosted: run `30744854292` on `ff1dfb67` — `ci (Unit/Integration + Lint gesammelt)` SUCCESS

## Boundaries

- issue_4255_implementation_started=false
- live_cursor_run_executed=false
- cursor_api_key_accessed=false
- provider_live_mutation=false
- not_agent_run_evidence_bundle_v1
- not_final_ci / not_cdb_local_ci / not_approval / not_merge_authority
- PR left draft; issues left open; no merge
