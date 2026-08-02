# Session 2026-08-01 — Issue #4252 Declarative Agent Registry + Reconciler

## Scope

Delivery-only slice for `#4252` (parent `#4249`) on Batch-PR `#4286`.
Precondition: Owner ratification of ACP `#4250` at `c691a8d0` documented in
prior commit on this branch.

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

`cdb_context` MCP serverStatus=error during discovery.

## Router

- Live `python -m tools.pr_routing route --issue 4252` → `CREATE_NEW_BATCH_PR`
  (`ISSUE_COMPATIBILITY_METADATA_INCOMPLETE`; label create 403).
- Operative continuation on existing Batch-PR `#4286` /
  `batch/agent-skills-issue-4250` (`OPERATIONAL_BATCH_CONTINUATION`) to preserve
  unmerged `#4250`/`#4251` evidence and avoid a competing PR.

## Delivered

- Schema `docs/contracts/cdb_agent_registry.v1.schema.json`
- Spec `docs/contracts/agent_registry/CDB_AGENT_REGISTRY_V1.md`
- Desired State `config/agent-control/`
- CLI `python -m tools.agent_control registry validate|plan|reconcile`
- Deterministic dry-run reconciler + MockBackend
- Fixtures under `docs/contracts/examples/agent_registry/`
- Unit tests `tests/unit/governance/test_agent_registry_v1.py`

## Validation

- `python -m tools.agent_control registry validate --config config/agent-control` → VALID
- `pytest` registry + execution-contract → 63 passed
- `pytest` pr_routing governance suite → 72 passed
- `python -m tools.validate_readme_links` → OK
- `python -m tools.validate_onboarding_docs` → OK
- `git diff --check` → clean
- `ruff check tools/agent_control tests/unit/governance/test_agent_registry_v1.py` → OK

## Non-goals / Boundaries

- No dispatcher (`#4253`), Cursor adapter (`#4254`), env provisioning, run
  evidence, approval agent
- No live provider mutation; reconcile dry-run default
- No merge, no `cdb-local-ci` publish, issues remain open, PR stays draft
- LR remains NO-GO
- ACP normative text at ratified `c691a8d0` not materially altered in this commit

## GitHub write limits

Issue comments / some PR body edits may 403; use PR comment + session log as
handoff if `gh` write fails.
