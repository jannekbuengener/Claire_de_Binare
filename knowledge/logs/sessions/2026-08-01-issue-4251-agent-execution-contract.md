# Session: Issue #4251 Agent Execution Contract v1

Date: 2026-08-01  
Agent: cursor-cloud  
Status: `DONE_SLICE_ADDED_TO_BATCH_PR` (delivery only)

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: blocked
context_trust_level: none
records_found: none
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: unavailable
```

`cdb_context` MCP server failed live tool discovery (tools unavailable).

## Router

- Live `python -m tools.pr_routing route --issue 4251` → `CREATE_NEW_BATCH_PR`
  (missing objective/contract/risk labels; `gh label create` → HTTP 403).
- Operational delivery: continue on PR `#4286` head
  `batch/agent-skills-issue-4250` (canon `#4250` present; draft restored;
  no competing PR). Decision code recorded as
  `OPERATIONAL_BATCH_CONTINUATION` in fixtures.

## Delivered

- Schema `cdb.agent_execution.v1` + Spec + RFC8785/SHA-256 tooling
- Validator/CLI `python -m tools.agent_execution_contract`
- Router handoff adapter + provider attenuation
- Positive/negative fixtures + golden vectors + unit tests

## Validation

- `pytest tests/unit/governance/test_agent_execution_contract_v1.py` → 31 passed
- `pytest tests/unit/governance/test_pr_routing_*.py` → 67 passed
- `ruff check` on touched Python → clean
- `black --check` after format → clean
- `git diff --check` → clean
- `python -m tools.validate_readme_links` → OK
- `python -m tools.validate_onboarding_docs` → OK

## GitHub write limitations (this session)

- `git push` to `batch/agent-skills-issue-4250` succeeded (head `653690f2`).
- PR `#4286` converted to draft via GraphQL succeeded earlier.
- `gh issue comment` / `gh pr edit` / REST issue+PR PATCH → HTTP 403
  (`Resource not accessible by integration`).
- ManagePullRequest body update blocked (description not agent-managed).
- ManagePullRequest PR comment with delivery evidence posted successfully.
- Issue `#4251` / parent `#4249` comments remain pending a token with
  `issues:write` (handoff contents are in the PR comment + this session log).

## Non-goals preserved

No dispatcher, registry, provider adapter, merge, or `cdb-local-ci` publish.
LR remains NO-GO.
