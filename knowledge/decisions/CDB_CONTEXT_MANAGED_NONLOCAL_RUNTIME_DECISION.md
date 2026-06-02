# Context Managed / Non-Local Runtime Decision

| Field | Value |
| --- | --- |
| Status | **accepted** / **active** (decision record only) |
| Date | 2026-06-02 |
| Issue | GitHub issue #2803 |
| Parent | GitHub issue #2778 (Phase-2 epic) |
| Grandparent | GitHub issue #1976 |
| `recommended_posture` | **`local_only`** |
| Runtime activation | **NOT ACTIVATED** |
| Decision label | `LOCAL_ONLY_UNTIL_GATES` |

## Scope

This decision governs **whether and how** CDB may adopt a **managed** or **non-local**
runtime for **Context Intelligence** (SurrealDB read path, Context MCP Bridge, agent
Brain Evidence). It is a **governance and documentation** artifact only.

**In scope:**

- Option matrix, Gate 0 prerequisites, hard rejection criteria
- Security boundaries, evidence requirements, operator gate sequence
- Rollback / fail-closed posture, open questions, follow-up issue candidates
- Cross-links to Phase-2 read-only deliverables (#2797–#2802)

**Out of scope (unchanged by this document):**

- Enabling managed SurrealDB, remote MCP, tunnels, or vendor endpoints
- Runtime, Docker, BLUE/RED, compose, or MCP config changes
- Productive SurrealDB writes or memory persistence
- Live-readiness upgrade, Echtgeld authorization, or trading actions
- Implementation of controlled write strategy v2 (GitHub issue #2804)
- Closing epic #2778 or grandparent #1976

**Related but separate lineage:** productive **T3 audit trail** endpoint design
([`docs/surrealdb/productive-memory-audit-trail-endpoint-design-v1.md`](../../docs/surrealdb/productive-memory-audit-trail-endpoint-design-v1.md),
issue #2735 / G1 ladder). That path targets **governed non-localhost write** for
`audit_observation` only under HG-P. This decision covers **Context/MCP read** posture
and future **managed read-only** candidates — do not merge scopes or infer T3
activation from Slice #2803.

## Decision summary

**`LOCAL_ONLY_UNTIL_GATES`**

Until all Gate 0 preconditions pass and a **separate scoped issue** receives explicit
Jannek-GO per option:

1. **Current production posture:** `local_only` — `NoopQueryAdapter` (in-memory) or
   `SurrealDBLocalQueryAdapter` (localhost HTTP only) via explicit `adapter_config_path`.
2. **Managed read-only** and **non-local read-only MCP** remain **deferred** design
   candidates only.
3. **Managed write-capable** runtime remains **explicit NO-GO** for this slice and for
   Phase-2 read adoption; write strategy is issue #2804 + LR/HG ladders.

Default agent reporting remains per
[`CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md):
`brain_source=repo-only`, `brain_status=not-used`, until guarded adapter evidence exists.

## Option matrix

| Option ID | Description | Slice #2803 verdict | Activation |
| --- | --- | --- | --- |
| `local_only` | Context/SurrealDB/MCP stays fully local read-only; `surrealdb-local` or in-memory Noop; MCP stdio from repo root | **RECOMMENDED (current)** | **Active** (read-only; not LR-Go) |
| `managed_readonly` | Future vendor- or operator-hosted SurrealDB used **only** for read-only context queries | **DEFERRED** | **NOT ACTIVATED** — separate issue + Jannek-GO |
| `nonlocal_readonly_mcp` | Future non-local read-only MCP/Context access (tunnel, remote bridge, or hosted MCP) | **DEFERRED** | **NOT ACTIVATED** — tunnel/security review GO |
| `managed_write_capable` | Write-capable managed runtime (persist, mutation, productive memory) | **REJECTED / OUT OF SCOPE** | **NO-GO** — #2804 + `PERSIST_ALLOWED`/`MUTATION_ALLOWED` gates |

### Comparison notes

| Dimension | `local_only` (now) | `managed_readonly` (future) | `nonlocal_readonly_mcp` (future) |
| --- | --- | --- | --- |
| Network | `127.0.0.1` / localhost only | Private or vendor endpoint (non-localhost) | Remote transport to read-only bridge |
| Adapter | `SurrealDBLocalQueryAdapter` | Future productive-read adapter (design TBD) | Future MCP transport + same read guards |
| MCP source labels | `in_memory`, `surrealdb-local`, `surrealdb-local-unavailable` | New label only after contract + tests | New surface; no raw external MCP default |
| Writes | Blocked at statement class + factory | Read-only only; no UPSERT path | Read-only only |
| Secrets | Local `SECRETS_PATH` / context secrets dir | Requires **managed secret policy** (follow-up) | Requires tunnel/auth model (follow-up) |
| LR implication | None | None without LR-SSOT review | None without LR-SSOT review |

**Code reality on `main`:** `build_adapter_from_params()` returns only
`NoopQueryAdapter` or `SurrealDBLocalQueryAdapter`; `load_config` and the local adapter
**reject non-local URLs**. Allowed MCP `metadata.source` values exclude managed/non-local
labels until a future contract extends the factory with inverse allowlist guards.

## Gate 0 — prerequisites (all required before any managed/non-local activation)

| # | Prerequisite | Evidence type |
| --- | --- | --- |
| G0-1 | Phase-2 read-only slices **#2797–#2802** landed on `main` with PR SHAs | GitHub merge evidence |
| G0-2 | Default brain posture **#2775** remains active; no contradiction | This repo + `CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` |
| G0-3 | MCP capability **L3–L5** verified per agent surface or documented WARN | [`docs/runbooks/surrealdb_context_mcp_access.md`](../../docs/runbooks/surrealdb_context_mcp_access.md) §1.5.1 |
| G0-4 | **Managed secret-handling policy** accepted (no secrets in repo/PRs/logs) | Dedicated issue + decision doc |
| G0-5 | Security/deployment review (TLS, tenant isolation, egress, audit logging) | Design issue + operator sign-off |
| G0-6 | Adapter contract extension (**read-only**, non-local allowlist, localhost denylist for productive-read path) | Implementation PR + unit tests |
| G0-7 | Operator proof pack: read queries succeed; write/admin SQL fail-closed | Session log + redacted proof |
| G0-8 | LR-SSOT review: managed path docs do not imply LR-Go or Echtgeld | Human review vs `LR-AUDIT-STATUS` |
| G0-9 | **Gordon gate** before any Docker/BLUE/RED/compose change | Explicit Gordon-GO (forbidden in #2803) |

Gate 0 is **documentation and evidence** in this slice. Satisfying G0-4 through G0-9
requires **follow-up issues**; none are activated here.

## Hard rejection criteria

Stop work and fail-closed (do not enable managed/non-local) when any of the following
is true or requested without explicit scope:

1. **Implicit activation** — enabling endpoints, tunnels, or remote adapters under
   #2803 or without Jannek-GO + scoped issue.
2. **Default write gates flipped** — `PERSIST_ALLOWED=True` or `MUTATION_ALLOWED=True`
   on `main` as a side effect of managed adoption.
3. **Trading or secret data in SurrealDB** — orders, fills, positions, risk state,
   balances, API keys, or vault material in context tables.
4. **Raw SurrealQL agent surface** — unconstrained query strings from agents.
5. **Brain output authorizes action** — Context Brain, MCP read results, or control-room
   signals used to auto-merge, auto-close issues, or mutate runtime without human GO.
6. **Board stage misread** — `trade-capable` treated as LR-Go or strategy validation.
7. **Infra mutation in decision slice** — Docker, compose, BLUE/RED, MCP JSON, tunnel
   config, or stack verify changes bundled with this decision PR.
8. **Caller-forged brain evidence** — `brain_source` / `metadata.source` set by caller
   without adapter/tool/record proof (issue #2638 guardrail).
9. **Managed write-capable** — any productive write, memory persist, or T3/T4 ladder
   step conflated with read-only managed adoption.

## Security boundaries

### Current (`local_only`)

- **Localhost-only HTTP** for DB-backed reads (`127.0.0.1` / `localhost`; non-local
  URLs rejected at config load and adapter construction).
- **Read-only statement classification** in `SurrealDBLocalQueryAdapter` independent of
  factory defaults.
- **MCP stdio** from repository root; do not substitute raw/external SurrealDB MCP
  servers when `cdb_context` capability checks fail.
- **`PERSIST_ALLOWED=False`** and **`MUTATION_ALLOWED=False`** remain defaults on `main`.
- **LR NO-GO** — no live capital, no Grafana gate for strategy validation, no Echtgeld.

### Future managed / non-local (deferred)

- Requires **inverse allowlist**: non-localhost URLs allowed only on a dedicated
  read-only adapter type; localhost must remain denied on that path when productive
  mode is requested (mirror of G1 T3 endpoint design, but scoped to **read** context).
- **No split-brain** — agents must not use both unguarded remote MCP and CDB-native
  bridge without capability resolution protocol (§1.5 runbook).
- **No secrets in git** — credentials only via operator-controlled stores; redact proof
  packs before GitHub comments.
- **Tenant / namespace isolation** documented before provisioning (design follow-up).

## Evidence requirements

Before claiming `brain_source=surrealdb-local` for managed or non-local paths (future):

1. Scoped issue with Jannek-GO and non-goals listed in PR body.
2. `adapter_config_path` or equivalent **explicit opt-in** in tool request.
3. Real adapter instantiation with `adapter.status` matching guarded label.
4. Tool/query/record IDs in Brain Evidence block (not caller-supplied fields).
5. Repo crosscheck (paths, symbols, commit SHA).
6. Live GitHub wins over ledger/memory if contradictory.

For this decision slice (#2803), evidence is **repo-only**:

- File: `tools/mcp/surrealdb_adapter_factory.py` (localhost-only module docstring and guards).
- File: `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`.
- Phase-2 docs: context package v2, hybrid retrieval, decision replay v2, control-room
  signals (read-only modules on `main`).

## Operator gate sequence

| Gate | Name | Owner | Delivers |
| --- | --- | --- | --- |
| **0** | Preconditions | Engineering + operator | This decision record; G0 table satisfied or tracked |
| **1** | Design-only follow-ups | Engineering | Pilot design, secret policy, tunnel model (separate issues) |
| **2** | Implementation | Engineering | Adapter/MCP contract code + tests; no activation flag |
| **3** | Operator proof | Operator | Redacted session log; read PASS; write/admin FAIL |
| **4** | Jannek-GO | Human | Per-option enablement (`managed_readonly` vs `nonlocal_readonly_mcp`) |
| **5** | LR-SSOT review | Human | If docs touch live-readiness narrative |
| **Gordon** | Infra/runtime | Human | **Only** for Docker/BLUE/RED/compose — **forbidden in #2803** |

Certification (`make context-certify`, #2801) supports readiness evaluation but
**does not** authorize managed/non-local activation alone.

## Rollback and fail-closed posture

If a future managed/non-local experiment fails or drifts:

1. **Revert to `local_only`** — remove or disable non-local `adapter_config_path` configs.
2. **MCP** — continue stdio `cdb_context` from repo; no fallback to unguarded remote MCP.
3. **Reporting** — `brain_status=blocked` or `repo-only` + `not-used` with explicit
   limitations; never claim DB-backed truth without records.
4. **Writes** — keep `PERSIST_ALLOWED=False` / `MUTATION_ALLOWED=False`; roll back env
   gates if any local audit persist was used in tests.
5. **Document** — session log + issue comment with SHA; do not close #1976/#2778 on rollback alone.

## Open questions

| ID | Question | Blocks |
| --- | --- | --- |
| OQ-1 | Vendor-hosted SurrealDB vs dedicated VM vs private sidecar for read-only context? | G0-5, managed_readonly pilot |
| OQ-2 | MCP transport: remain stdio-local vs remote MCP server vs SSE bridge? | nonlocal_readonly_mcp |
| OQ-3 | Secret rotation and multi-agent access for managed endpoints? | G0-4 |
| OQ-4 | Cost, SLA, and backup model for managed read replicas? | G0-5 |
| OQ-5 | Relationship to T3 audit endpoint (G1) — shared infra vs isolated read replica? | Architecture follow-up |
| OQ-6 | CI proof for non-local read without exposing credentials in Actions? | G0-7 |

## Follow-up issue candidates

Search open issues before creating. No duplicate found for **managed secret policy**
at decision time (2026-06-02); consider filing if implementation slice starts.

| Candidate | Purpose | Suggested title fragment |
| --- | --- | --- |
| FU-1 | Managed-read-only pilot design (network + adapter allowlist) | `[PHASE-2] managed read-only context pilot design` |
| FU-2 | Secret policy for managed/non-local postures | `[PHASE-2] context managed runtime secret policy` |
| FU-3 | Non-local MCP/tunnel verification harness | `[PHASE-2] non-local read-only MCP verification` |
| FU-4 | Runtime activation / compose (Gordon-GO) | `[PHASE-2] context runtime activation` (infra explicit) |

Issue #2804 remains the **write-strategy design** slice; do not expand #2803 into write
implementation.

## Phase-2 cross-links (read-only foundation on `main`)

| Slice | Issue | Artifact (non-exhaustive) |
| --- | --- | --- |
| Brain adoption | #2797 | Read-only agent brain adoption |
| Context package v2 | #2798 | [`docs/surrealdb/context-package-model-v2.md`](../../docs/surrealdb/context-package-model-v2.md) |
| Hybrid retrieval | #2799 | [`docs/surrealdb/context-hybrid-retrieval-strategy-v1.md`](../../docs/surrealdb/context-hybrid-retrieval-strategy-v1.md) |
| Decision replay v2 | #2800 | [`docs/surrealdb/decision_replay_query_contract.md`](../../docs/surrealdb/decision_replay_query_contract.md) |
| Operator certification | #2801 | Runbook §1.5.2 certification flow |
| Control room signals | #2802 | [`docs/surrealdb/control-room-readonly-signal-layer-v1.md`](../../docs/surrealdb/control-room-readonly-signal-layer-v1.md) |
| Write strategy (design) | #2804 | Separate slice — not activated here |

## What requires Jannek-GO and LR-SSOT impact review

| Action | Jannek-GO | LR-SSOT review |
| --- | --- | --- |
| Land this decision record (#2803) | Covered by Phase-2 planning GO | No |
| Enable `managed_readonly` | **Yes** — per follow-up issue | **Yes** if docs imply operational readiness |
| Enable `nonlocal_readonly_mcp` | **Yes** — per follow-up issue | **Yes** if exposure changes trust model |
| Flip persist/mutation defaults | **Yes** — explicit; out of #2803 | **Yes** |
| Docker/BLUE/RED changes | **Gordon-GO** | No unless LR narrative changes |
| Live/Echtgeld trading | **Yes** + LR human gate | **Required** |

## Safety and LR boundaries

- **Live-readiness:** NO-GO per
  [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
  unless changed only via LR SSOT.
- **Board stage:** `trade-capable` is orthogonal; not live authorization.
- **`PERSIST_ALLOWED=False`** and **`MUTATION_ALLOWED=False`** remain defaults; this
  decision does not flip them.
- **No** trading state in SurrealDB for context brain paths.
- **Context Brain output does not authorize** code changes, merges, issues, or runtime
  actions without parent agent and human GO.

## References

- [`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md) — #2775
- [`agents/AGENTS.md`](../../agents/AGENTS.md) — Brain Evidence Gate
- [`docs/runbooks/surrealdb_context_mcp_access.md`](../../docs/runbooks/surrealdb_context_mcp_access.md)
- [`tools/mcp/surrealdb_adapter_factory.py`](../../tools/mcp/surrealdb_adapter_factory.py)
- [`docs/surrealdb/productive-memory-audit-trail-endpoint-design-v1.md`](../../docs/surrealdb/productive-memory-audit-trail-endpoint-design-v1.md) — G1 T3 (separate)
- GitHub issue #2803 (this decision), #2778 (parent), #1976 (grandparent), #2804 (write design)
