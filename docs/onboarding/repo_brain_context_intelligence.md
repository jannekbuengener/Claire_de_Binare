# Repo Brain / Context Intelligence — Developer Onboarding

**Status:** Developer orientation
**Issue:** #3231
**Parent:** #3226
**Scope:** Docs / onboarding / Repo Brain / Context Intelligence

This page is the developer entry point for **Repo Brain / Context Intelligence** in
CDB. It explains what it is, what it is not, how to use it as read-only orientation,
and what safety boundaries apply.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO.

---

## What Is Repo Brain / Context Intelligence in CDB?

Repo Brain / Context Intelligence is the **read-only orientation and evidence layer**
for agents and developers working in this repo. It provides:

- **Orientierung** — Find canonical docs, governance, runbooks, and entrypoints
- **Bootloader/Read-Order resolution** — Follow the agent bootloader chain from
  `AGENTS.md` through `agents/AGENTS.md` and the full Read Order
- **Evidence collection** — Use Context MCP tools (`context.briefing`,
  `context.search`, `context.required_reads`, `context.readiness`) when available
  in the active agent surface
- **Stale-doc detection** — Compare repo-backed evidence against canonical sources
- **CDB Glossary** — A centralized terminology reference at [`cdb_glossary.md`](cdb_glossary.md) for all CDB-specific terms
- **Brain Evidence Block** — A structured gate output required before any plan
  when scope includes Strategy, Runtime, Module, Service, Contract, Context,
  SurrealDB, MCP tools, DB-backed Memory, or Evidence
- **Agent and PR context preparation** — Package context artifacts for agent
  handoff (`context.package`), generate briefings (`context.briefing`), assess
  readiness (`context.readiness`)

## What It Is Not

Repo Brain / Context Intelligence is **strictly read-only and gate-bound**. It is
not:

- **No live/trading authority** — Context output does not authorize trades, orders,
  risk changes, or any execution action
- **No LR-Go** — Live-Readiness remains `NO-GO` per
  `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **No Echtgeld-Go** — No real-money trading without explicit Human-GO
- **No replacement for GitHub live / Repo live** — GitHub issues, PRs, checks,
  branches are the live truth. Repo Brain/MCP results do not override GitHub state.
- **No secret source** — Context tooling does not expose secrets, credentials,
  API keys, or Tresor values
- **No productive Memory/DB write authorization** — `PERSIST_ALLOWED=False` and
  `MUTATION_ALLOWED=False` remain default on `main`

## Truth Order

When resolving context, use this priority (higher wins; fail-closed on conflict):

1. **GitHub live** — issues, PRs, checks, branches, comments
2. **Repo files** — governance, code, contracts, runbooks
3. **SurrealDB context package** — only with guarded adapter + record evidence
4. **Ledger / status snapshots** — e.g. `CURRENT_STATUS.md` (not live truth)
5. **Fallback** — explicit limitations; do not invent DB-backed claims

## Brain Evidence Block

When the scope includes **Strategy, Runtime, Module, Service, Contract, Context,
SurrealDB, MCP tools, DB-backed Memory, or Evidence**, the agent MUST output a
Brain Evidence Block **before any plan**.

### Field Values

| Field | Allowed values | Meaning |
|-------|---------------|---------|
| `brain_source` | `repo-only`, `in_memory`, `surrealdb-local`, `unavailable` | Where evidence came from |
| `brain_status` | `used`, `partial`, `not-used`, `blocked` | Whether brain evidence was usable |

### Source Logic

- `brain_source=repo-only`: Declare `brain_status=not-used`. No DB-backed claims.
  Use repo and GitHub live evidence as authority.
- `brain_source=in_memory`: Read-only helper/bundle context. No DB-backed claims.
- `brain_source=surrealdb-local`: Brain claims allowed **only** with
  Tool/Query/Record evidence. Caller-supplied `source`/`metadata.source` are not
  evidence (Issue #2638).
- `brain_source=unavailable`: Declare `blocked` or `repo-only fallback`.

### Examples

**Valid (repo-only fallback, no DB-backed claims):**

```
## Brain Evidence
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - Repo reads from bootloader Read Order
  - gh issue view for scope-related issues
records_or_results:
  - No SurrealDB-local record evidence
repo_crosscheck:
  - AGENTS.md -> agents/AGENTS.md
  - docs/runbooks/CONTROL_REGISTER.md
impact_on_plan:
  - Use repo/GitHub live evidence as authority
  - No DB-backed claims
limitations:
  - No productive DB or memory-write evidence
  - No Live-Go / Echtgeld-Go authority
```

**Invalid (ungrounded DB-backed claim):**

```
## Brain Evidence
brain_source: surrealdb-local
brain_status: used
records_or_results:
  - Agent memory shows X
  - Briefing said Y
```

↑ This is **invalid** because `records_or_results` does not cite a specific
Tool/Query/Record. `surrendb-local` caller-supplied metadata is not DB-backed
evidence.

## Developer First-Use Flow

When you start working with Repo Brain / Context Intelligence for the first time:

1. **Read the bootloader:**
   - `AGENTS.md` (root pointer)
   - `agents/AGENTS.md` (canonical agent registry + Read Order)
   - `agents/OPEN_CODE_AGENTS.md` (shared contract + Brain Evidence Gate)

2. **Assess local readiness:**

   ```bash
   # Read-only preflight: validates local context setup
   make context-doctor

   # Or directly:
   python -m tools.surrealdb.context_onboarding_doctor
   ```

   The doctor checks:
   - Secrets presence (not values)
   - Python and pip dependencies
   - Key file references
   - No live-key or LR violations

   It does **not** expose any secret values and does **not** require a running
   Docker stack.

3. **Read the SurrealDB/Context docs index:**
   - `docs/surrealdb/README.md` — Context-/MCP-Docs-Index

4. **Study the MCP access runbook:**
   - `docs/runbooks/surrealdb_context_mcp_access.md` — MCP capability resolution

5. **Work through the first-use example:**
   - `docs/onboarding/examples/repo_brain_first_use.md`

6. **Review agent MCP templates:**
   - `agents/templates/README.md` — Agent MCP config template index
   - `agents/templates/onboarding_mcp_setup.ps1` — MCP capability validation script

## Graph follow-up discoverability

The current Context Brain sensory canon is
[`CDB_CONTEXT_BRAIN_SENSORY_LAYER.md`](../../knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md).
For the #3484 graph follow-up, use that canon as the entry surface for these repo-only
discoverability anchors:

- `docs/surrealdb/context-relationship-vocabulary-v0.md`
- `infrastructure/surrealdb/traversal_query_fixtures.surql`

These files help agents discover graph vocabulary and traversal examples, but they do
not create DB-backed evidence, runtime authority, or any Live-/Echtgeld-Go.

## Vector pipeline discoverability

For the #3486 vector / embedding follow-up, start from
[`CDB_CONTEXT_BRAIN_SENSORY_LAYER.md`](../../knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md)
and then use these repo-only discoverability anchors:

- `docs/surrealdb/context-embedding-pipeline-v0.md`
- `infrastructure/surrealdb/hybrid_retrieval_fixtures.surql`
- `tools/surrealdb/graph_vector_proof_cli.py`

These anchors document the vector pipeline contract, fixtures, and proof boundaries.
They stay repo-only, non-authorizing, and do not create DB-backed truth, runtime
rebuild authority, or any Live-/Echtgeld-Go. #3487 remains a later follow-up.

## Hybrid retrieval discoverability

For the #3487 hybrid retrieval follow-up, start from the same sensory canon and keep
the foundations separate:

- #3484 provides the graph anchor
- #3486 provides the vector / embedding anchor
- #3487 connects BM25 + Vector + Graph only as contract / fixture / ranking semantics

Use these repo-only discoverability anchors:

- `docs/surrealdb/context-hybrid-retrieval-strategy-v1.md`
- `infrastructure/surrealdb/hybrid_retrieval_fixtures.surql`
- `tools/surrealdb/hybrid_retrieval_ranking.py`
- `context.search`

The hybrid follow-up remains non-authorizing. It does not create productive DB
execution, does not create DB-backed evidence without Tool/Query/Record proof, and
does not imply any Live-/Echtgeld-Go.

## Local Readiness Check

Start with the **developer onboarding doctor** for a general setup check:

```bash
# Cross-platform Python doctor
python -m tools.onboarding_doctor

# JSON output
python -m tools.onboarding_doctor --format json

# PowerShell v1 front door (Windows)
.\tools\cdb.ps1 onboarding doctor

# Make target (all platforms)
make onboarding-doctor
```

Then run the **context doctor** for Context Intelligence preflight:

```bash
# One-command preflight
make context-doctor

# Detailed JSON output
python -m tools.surrealdb.context_onboarding_doctor --format json
```

Both commands are **read-only**. They do not modify any files, do not start any
service, and do not require a running Docker stack. Together they validate:

- Git installed and branch state
- Python version (3.11+)
- Docker and Docker Compose presence (optional)
- gh CLI and authentication (optional)
- `.env` file presence
- SECRETS_PATH existence (not contents)
- All key onboarding files exist
- Python venv and dependencies
- Secret directory presence (not contents)
- Local MCP config accessibility
- Context Intelligence prerequisites

**Security:** Neither doctor ever outputs secret values. Do not modify either
doctor to display secret values.

## MCP / Agent Templates

Template files for agent MCP surfaces are in `agents/templates/`:

| File | Surface | Purpose |
|------|---------|---------|
| `onboarding_mcp_setup.ps1` | Any agent | Validates 5-level MCP capability (read-only) |
| `claude_mcp.json.template` | Claude / Cloud Code | MCP config template |
| `codex_mcp_config.md` | Codex | Reference only |
| `codex_config.example.toml` | Codex | Template config |

Run the validation from repo root:

```powershell
pwsh -File agents/templates/onboarding_mcp_setup.ps1
```

## Safety Boundaries

- **LR remains NO-GO** — SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Board-Stage `trade-capable` is not Live-Go**
- **No Echtgeld-Go without explicit Human-GO**
- **Docs/UI sind Orientierung, keine Autoritaet**
- **`CURRENT_STATUS.md` is a ledger, not live truth**
- **GitHub live and Repo live win over Brain/MCP claims**
- **`PERSIST_ALLOWED=False` and `MUTATION_ALLOWED=False` remain default**
- **Productive DB/Memory writes remain gate-bound**
- **MCP mutations remain gate-bound**
- **No secret values in logs, docs, issues, or PR comments**

## Related Docs

| Doc | Purpose |
|-----|---------|
| `knowledge/decisions/CDB_CONTEXT_BRAIN_SENSORY_LAYER.md` | Canonical sensory-layer principle and boundary contract |
| `docs/surrealdb/context-embedding-pipeline-v0.md` | Canonical #3486 vector / embedding pipeline contract |
| `docs/surrealdb/README.md` | Context-/MCP-Docs-Index |
| `docs/runbooks/surrealdb_context_mcp_access.md` | MCP capability resolution |
| `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md` | Local context runtime |
| `docs/onboarding/examples/repo_brain_first_use.md` | First-use example |
| `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md` | Visual developer start |
| `DEVELOPER_ONBOARDING.md` | Full developer setup guide |
| `docs/navigation/mcp-navpack/ENTRYPOINTS.yaml` | Machine-readable read order |
| `docs/navigation/mcp-navpack/CHEATSHEET.md` | Quick nav reference |
| `agents/templates/README.md` | Agent MCP template index |
| `tools/surrealdb/context_onboarding_doctor.py` | Read-only preflight script |
| `Makefile` (`make context-doctor`) | Preflight target |

---

**Document Version:** 1.0.0
**Last Updated:** 2026-06-16
**Issue:** #3231
