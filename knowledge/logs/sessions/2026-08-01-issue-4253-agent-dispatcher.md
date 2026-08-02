# Session 2026-08-01 — Issue #4253 Governed Dispatcher + Run State Machine

## Scope

Delivery-only slice for `#4253` (parent `#4249`) on Batch-PR `#4286`.
No merge, no `cdb-local-ci`, no Cursor adapter, no `#4256` evidence bundle.

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: unavailable
context_trust_level: none
records_found: none
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: unavailable
```

## Dependency Integrity

- ACP Owner Ratification Record present for `c691a8d0` (commit `5274e351`)
- `python -m tools.agent_execution_contract --help` OK
- `python -m tools.agent_control registry validate --config config/agent-control` VALID
- Existing contract + registry pytest green on head `795e6777` before changes

## Router

- Live `route --issue 4253` → `CREATE_NEW_BATCH_PR` (incomplete labels)
- Operative `OPERATIONAL_BATCH_CONTINUATION` on `#4286` /
  `batch/agent-skills-issue-4250` (schema-supported; prior ACP batch evidence;
  steward_state accepting_slices; no competing #4253 PR)

## Delivered

- Lifecycle pure transitions (`tools/agent_control/lifecycle.py`)
- Preflight binding contract digest + registry ceilings
- MockProvider + RunStore (InMemory/JsonFile CAS)
- Dispatcher orchestrator + CLI verbs:
  `dispatch|watch|cancel|retry|evidence`
- Schema `cdb.agent_dispatch_run.v1` + docs
- Registry agent `acp-mock-dispatcher`
- Tests `tests/unit/governance/test_agent_dispatcher_v1.py`

## Canon / Issue mapping

- `VALIDATED` → `validation_success` event → `CONTRACTED`
- `EVIDENCE_COLLECTED` → snapshot event only
- `HANDED_OFF` → handoff event after PASS

## Validation

- dispatcher pytest: 34 passed
- contract+registry+pr_routing targeted: 169 passed (with dispatcher)
- validate_readme_links / validate_onboarding_docs OK
- ruff + black --check on touched Python OK
- git diff --check clean
- CLI dry-run + mock execute/watch → PASS smoke

## Boundaries

- No live provider / Cursor adapter
- No `#4254`–`#4260` implementation
- evidence ≠ Agent Run Evidence Bundle v1
- LR NO-GO
