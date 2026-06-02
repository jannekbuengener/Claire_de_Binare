# Context Brain Default Posture (read-only, conditional)

| Field | Value |
| --- | --- |
| Status | **accepted** / **active** |
| Date | 2026-06-01 |
| Issue | GitHub issue #2775 |
| Parent | GitHub issue #1976 |
| Policy constant | `read_only_context_brain = conditional` |
| Decision label | `ALLOW_READONLY_CONDITIONAL` |

## Scope

This decision governs **agent and governance documentation only** for how CDB agents
report and use Context Brain / SurrealDB-backed context.

**In scope:** default `brain_source` / `brain_status`, source priority, opt-in
evidence path, caller-supplied guardrails, task-scope matrix, surface alignment.

**Out of scope (unchanged by this document):**

- Runtime, trading, or BLUE/RED stack changes
- Productive SurrealDB writes or memory persistence
- MCP tool implementation or registry changes
- Phase-2 activation (GitHub issue #2778)
- Live-readiness or Echtgeld authorization

## Decision

**`ALLOW_READONLY_CONDITIONAL`**

Agents may use the read-only Context Brain **only when** evidence proves a real
read path (repo files, in-memory fixtures, or localhost SurrealDB via guarded
adapter). There is **no** default-on productive brain, **no** automatic
SurrealDB activation for all agents, and **no** implicit DB-backed truth from
caller metadata.

## Default posture

Until an agent has **verified** Context-, DB-, or MCP-evidence from tools,
queries, or records:

| Field | Default |
| --- | --- |
| `brain_source` | `repo-only` |
| `brain_status` | `not-used` |

**Repo-first:** plan and triage from live GitHub, repo files, and required reads
before claiming SurrealDB-backed memory or evidence.

**Read-only:** Context/MCP tools and CLI paths remain read-only unless a
separate explicit human GO authorizes write/apply scope.

**DB-backed only with adapter evidence:** `brain_source=surrealdb-local` is
allowed in agent reports only when `metadata.source` (or equivalent guarded
label) was derived from a real `SurrealDBLocalQueryAdapter` with
`adapter.status == "surrealdb-local"`, plus tool/query/record evidence and
repo crosscheck.

## Source priority

When resolving what counts as authoritative context, use this order (higher wins):

1. **Live GitHub** — issues, PRs, checks, branches, live comments
2. **Repo files** — canon governance, code, contracts, runbooks
3. **SurrealDB context package** — only with guarded adapter + record evidence
4. **Ledger / status snapshots** — e.g. `CURRENT_STATUS.md` (not live truth)
5. **Fallback** — explicit limitations; fail-closed

GitHub and repo evidence override brain/CIS claims. Board stage `trade-capable`
does not imply live-readiness GO.

## Brain Evidence status rules

| `brain_status` | Meaning | When allowed |
| --- | --- | --- |
| `used` | Brain/context evidence actively used | With concrete `tools_or_queries` and `records_or_results`; valid pairings: `repo-only` + file/gh evidence, or `surrealdb-local` + adapter evidence |
| `partial` | Partial brain use or degraded DB | Adapter `surrealdb-local-unavailable`, or subset of queries succeeded; never from caller-forged fields |
| `not-used` | No brain/DB evidence used | **Default** for `repo-only` and `in_memory`; required for Noop/in-memory bundle paths |
| `blocked` | Brain access failed or not authorized | `unavailable` MCP, write scope without GO, LR/live scope; plan must stop or degrade |

**Consistency rules:**

1. `brain_status=used` requires populated `tools_or_queries` and
   `records_or_results` in the Brain Evidence block.
2. `brain_source=surrealdb-local` with `brain_status=not-used` is a
   **contradiction** — fail-closed.
3. `in_memory` / Noop must not report DB-backed claims; prefer
   `brain_status=not-used` unless only repo file evidence was used
   (`repo-only` + `used` is valid for pure repo/gh analysis).
4. Non-DB fallback must **never** report `brain_status=used` solely because
   MCP or briefing ran in in-memory mode.

## Allowed `brain_source` values

| `brain_source` | Semantics | DB-backed claims |
| --- | --- | --- |
| `repo-only` | Repo files, `gh`, required reads; brain not used or only as label | **No** — treat as `brain_status=not-used` unless file evidence justifies `used` with `repo-only` |
| `in_memory` | `NoopQueryAdapter`, fixtures, inline briefing records | **No** — `db_claims_allowed=false` |
| `surrealdb-local` | Localhost adapter reachable; guarded `metadata.source` | **Yes**, only with tool/query/record evidence |
| `unavailable` | MCP/adapter missing; fail-closed | **No** — use `blocked` or explicit repo-only fallback |

`repo-only` must **never** be described as SurrealDB-backed or “DB verified”.

## Caller-supplied source guardrail

The following are **not** evidence of a live SurrealDB read (GitHub issue #2638):

- caller-supplied `source`
- caller-supplied `brain_source`
- caller-supplied `brain_status`
- caller-supplied `metadata.source`

Implementation: `derive_guarded_source_label()` in
`tools/mcp/surrealdb_adapter_factory.py` ignores request fields and derives
`metadata.source` only from `adapter.status`.

Tests (non-exhaustive): `tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py`
(forged DB claim fields fail-closed).

## `in_memory` and `NoopQueryAdapter`

- `build_adapter_from_params()` without `adapter_config_path` returns
  `NoopQueryAdapter` (`source="in_memory"`, no network).
- Allowed for read-only helper evaluation, Wave-15–20 bundle tools, and MCP
  bridge smoke without a live DB.
- **`db_claims_allowed=false`** in briefing `session_context` when
  `brain_source` is `in_memory` or `repo-only`.
- Do not sell `in_memory` or `repo-only` as SurrealDB-backed.

## `surrealdb-local` opt-in evidence path

Opt-in is **conditional** on config, health, secrets, and adapter status.

```text
Agent / tool request
  └── adapter_config_path (e.g. infrastructure/config/surrealdb/context_query.local.yaml)
        └── build_adapter_from_params()  [tools/mcp/surrealdb_adapter_factory.py]
              ├── missing path → NoopQueryAdapter (in_memory, no DB claims)
              └── valid path → SurrealDBLocalQueryAdapter (localhost HTTP only)
                    ├── hard_mode=False → soft fail if DB offline
                    ├── credentials via secrets_path / CDB_CONTEXT_SECRETS_PATH
                    └── adapter.status → derive_guarded_source_label()
                          ├── "surrealdb-local" → DB-backed claims allowed (with records)
                          ├── "surrealdb-local-unavailable" → partial / in_memory fail-closed
                          └── other → in_memory fail-closed
```

**Operator prerequisites (read-only proof):**

1. Context onboarding doctor (GitHub issue #2651) /
   `make context-doctor` where applicable
2. `infrastructure/config/surrealdb/context_query.local.yaml` (init via
   `make context-query-config-init` if missing)
3. Local health/version checks and secrets presence (no secret contents in logs)
4. Optional Wave-14 proof:
   `CDB_RUN_REAL_SURREALDB_SMOKE=1` +
   `pytest tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py` (see
   `docs/runbooks/surrealdb_context_mcp_access.md` §7.7)

**Evidence chain for DB-backed agent claims:**

1. `adapter_config_path` present in request
2. Real `SurrealDBLocalQueryAdapter` instantiated
3. `adapter.status == "surrealdb-local"`
4. Tool response `metadata.source == "surrealdb-local"`
5. Concrete tools/queries/record IDs in Brain Evidence block
6. Repo crosscheck (paths, symbols, commits)

## Task-scope matrix

| Situation | Default `brain_source` | Default `brain_status` | `surrealdb-local` |
| --- | --- | --- | --- |
| Normal repo/issue triage | `repo-only` | `not-used` | Not required |
| Agent prompt / session handoff | `repo-only` | `not-used` | Only if `adapter_config_path` set |
| MCP/CLI closeout analysis | `repo-only` | `used` (with limitations) | Not required |
| SurrealDB/context planning | `repo-only` | `not-used` | After MCP capability L3+ and config path |
| DB-backed memory/evidence/claim claim | `in_memory` (fail-closed) | `not-used` | Only guarded `metadata.source=surrealdb-local` |
| Read-only context briefing | `repo-only` | `not-used` | Only with `adapter_config_path` |
| Local-only Wave-14 smoke | `surrealdb-local` | `used` | **Purpose** of smoke |
| Write/persist/memory-apply | `repo-only` | `blocked` | **Never** |
| Phase-2 brain adoption | `repo-only` | `not-used` | After #2775 + gates + Jannek GO (issue #2778) |
| Live/LR/trading scope | `unavailable` | `blocked` | **Never** |

## Stop conditions

Stop or fail-closed when:

- Caller tries to forge `brain_source`, `brain_status`, or `metadata.source`
- Agent claims DB-backed truth without adapter/tool/record evidence
- Write/persist/apply attempted without explicit GO (`PERSIST_ALLOWED=False`,
  `MUTATION_ALLOWED=False` on main)
- LR/live/echtgeld GO inferred from Context Brain or board stage
- Phase-2 work starts before issue #2778 entry gates (incl. G3)
- `repo-only` reported as SurrealDB-backed

## Surface alignment

| Surface | Alignment |
| --- | --- |
| **Cursor** | `.cursor/agents/_CDB_SUBAGENT_CONTRACT.md` — Brain Evidence Gate + § Context Brain adoption (#2775 / #2797); parent enforces this decision |
| **Codex** | `agents/CODEX.md` § MCP Capability Resolution |
| **OpenCode** | `agents/OPEN_CODE_AGENTS.md` — briefing + Wave-14 contracts |
| **Claude** | `agents/CLAUDE.md` / `agents/roles/CLAUDE.md` — context MCP capability |
| **All agents** | `agents/AGENTS.md` § Brain Evidence Gate + this document |

Surfaces must not contradict: default `repo-only` / `not-used`, guarded
`surrealdb-local`, caller fields not evidence.

## Safety and LR boundaries

- **Live-readiness:** NO-GO unless changed only via LR SSOT
  (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)
- **`PERSIST_ALLOWED=False`** and **`MUTATION_ALLOWED=False`** remain defaults;
  no productive SurrealDB writes from this policy
- **No** trading state in SurrealDB: orders, fills, positions, risk-state,
  secrets, balances
- **#2778** remains PARKED/BLOCKED until entry gates pass; this document
  satisfies G3 (read-only brain decision) only — not Phase-2 activation

## References

- [`agents/AGENTS.md`](../../agents/AGENTS.md) — Brain Evidence Gate
- [`agents/OPEN_CODE_AGENTS.md`](../../agents/OPEN_CODE_AGENTS.md)
- [`docs/runbooks/surrealdb_context_mcp_access.md`](../../docs/runbooks/surrealdb_context_mcp_access.md) — §1.5, §7.6–7.7
- [`tools/mcp/surrealdb_adapter_factory.py`](../../tools/mcp/surrealdb_adapter_factory.py)
- [`tools/mcp/context_bridge.py`](../../tools/mcp/context_bridge.py) — `db_claims_allowed`
- [`tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py`](../../tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py)
- Analysis: GitHub issue #2775 comment `4596329357`
