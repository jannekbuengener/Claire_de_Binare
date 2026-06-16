# Example: Repo Brain First Use

Status: Orientation
Issue: #3238

This example shows how a new developer or agent uses Repo Brain / Context
Intelligence as read-only orientation. It does not authorize writes, merges,
runtime actions, trading actions, Live-Go, or Echtgeld-Go.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO.

## Scenario

You receive a task that mentions Context Intelligence, Repo Brain, MCP tools,
Evidence, SurrealDB, or memory. You need orientation, but you must not invent
DB-backed claims.

## Step 1: Resolve The Bootloader

Read:

1. `AGENTS.md`
2. `agents/AGENTS.md`
3. the full Read Order from `agents/AGENTS.md`
4. `agents/OPEN_CODE_AGENTS.md`

The Brain Evidence Gate applies before any plan when Context, SurrealDB, MCP,
DB-backed memory, or evidence is in scope.

## Step 2: Ask What Evidence You Actually Have

Use read-only Context tooling only when it is available in the active agent
surface and returns a real handler response.

Valid examples of orientation tooling:

```text
context.required_reads
context.briefing
context.search
context.readiness
```

If the tool returns synthetic, mocked, empty, or repo-only results, say so. Do
not claim `surrealdb-local` or DB-backed evidence without adapter/query/record
evidence.

## Step 3: Use Repo-Backed Context Paths

Repo-backed references for Context onboarding are:

- [`../../surrealdb/README.md`](../../surrealdb/README.md)
- [`../../runbooks/surrealdb_context_mcp_access.md`](../../runbooks/surrealdb_context_mcp_access.md)
- `make context-doctor` as the read-only local Context onboarding preflight
- `python -m tools.surrealdb.context_onboarding_doctor --format json`

The context-doctor path is read-only orientation. It may report missing local
config or unavailable local services; that is evidence, not permission to start
runtime or write productive memory.

## Step 4: Fill The Brain Evidence Block Honestly

Example fallback when no verified DB records are available:

```text
## Brain Evidence
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - context.required_reads for the task scope
  - context.briefing for the task scope
  - repo reads from the bootloader Read Order
records_or_results:
  - No SurrealDB-local record evidence returned
  - Context briefing used as orientation only
repo_crosscheck:
  - AGENTS.md -> agents/AGENTS.md
  - docs/runbooks/surrealdb_context_mcp_access.md
impact_on_plan:
  - Use repo and GitHub live evidence as authority
  - Do not make DB-backed Brain claims
limitations:
  - No productive DB or memory-write evidence
  - No Live-Go / Echtgeld-Go authority
```

## Step 5: Cross-Check Against Authority

Use this priority order:

1. GitHub live issue and PR state
2. Repo files and canonical docs
3. Verified SurrealDB context package with record evidence, if actually present
4. Ledger/status snapshots such as `CURRENT_STATUS.md`
5. Explicit fallback with limitations

Repo Brain helps with evidence and orientation, but it is not a live, trading,
merge, or LR authority. Context/MCP output does not override GitHub live state,
repo canon, Human-GO, `PERSIST_ALLOWED=False`, or `MUTATION_ALLOWED=False`.
