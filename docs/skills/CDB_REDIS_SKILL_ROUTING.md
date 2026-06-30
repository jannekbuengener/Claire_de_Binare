# CDB Redis Skill Routing and Runtime Guardrails

| Field | Value |
| --- | --- |
| Status | **canonical** |
| Issue | GitHub issue #3596 |
| Scope | Agent skill routing and review guardrails only |
| LR | **NO-GO** (unchanged; this document does not authorize live trading) |

## Purpose

Redis is an **existing CDB runtime component** — cache, Pub/Sub, and Streams for
services such as risk, execution, signal, and paper runner. It is **not** a new
product surface and **not** a replacement for SurrealDB Context Intelligence.

This document defines which Redis-related skills agents may load, when, and what
is explicitly out of scope.

**Canonical runtime references (repo, not skills):**

- `core.utils.redis_client.create_redis_client` — shared pool-backed client
- `knowledge/governance/SERVICE_CATALOG.md` — `cdb_redis`, `cdb_redis_exporter`
- `knowledge/ARCHITECTURE_MAP.md` — Redis role in BLUE/RED stack
- `AGENTS.md` § Redis (message bus) — connection, key, and TTL rules

## Brain / Context posture

- **Primary CDB brain strategy:** SurrealDB Context Intelligence (read-only,
  conditional; see `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`).
- **Redis role:** runtime cache, messaging, and ephemeral state — **never** agent
  memory, evidence store, or decision brain.
- Agents touching Redis in Strategy/Runtime/Module/Service/Contract/Context scope
  must still emit the Brain Evidence block per `agents/AGENTS.md` § Brain Evidence
  Gate before planning.

## Session bootstrap (before Redis skills)

Always run CDB session skills first (fail-closed):

1. Bootloader: `AGENTS.md` → `agents/AGENTS.md` → `agents/OPEN_CODE_AGENTS.md`
2. `/cdb-session-start`
3. `/cdb-control-intake` (when control/board context applies)
4. `/cdb-issue-to-session-plan` (when issue-scoped)

Load Redis skills **only after** bootstrap — task-specific, not bulk-loaded.

## Official Redis core skill set (CDB)

These skills come from the **Cursor Redis plugin** (external to the repo). Invoke
via `/redis-<name>` or let the agent load them when editing Redis-related code.
Plugin rules apply automatically on matching code.

| Skill | When to load |
| --- | --- |
| `redis-development` | Umbrella entry; any Redis work in CDB services, clients, or docs review |
| `redis-core` | Data model, key naming, Hash vs JSON vs String, counters, sessions |
| `redis-connections` | Pooling, pipelining, timeouts, client-side caching |
| `redis-security` | Auth, ACLs, TLS, network exposure, production hardening review |
| `redis-observability` | Metrics, slow commands, debugging; pairs with `cdb_redis_exporter` review |

**Runtime guardrails (code review surface):**

- Use `create_redis_client`; no ad-hoc `redis.Redis()` in long-lived services.
- One pool-backed client per service where possible.
- Consistent prefixes (`cdb:` streams; dotted pub/sub channels).
- TTL on ephemeral cache keys.
- **No Redis secrets** in code, docs, issues, logs, or commits — env/secrets
  path only (`SECRETS_PATH` / operator secrets layout).

**Observability review surface:**

- Container: `cdb_redis_exporter` (see `SERVICE_CATALOG.md`)
- Validate scrape health, password handling, and metric-driven alerts during
  infra/ops reviews — not as part of this docs slice.

## Event / runtime add-on skills (CDB)

Load in addition to the core set when the task touches event flows, stack ops, or
shadow validation — not as replacements for the core set.

| Skill | Source | When to load |
| --- | --- | --- |
| `messaging-redis-streams` | External (Gemini domain-expert) | Streams vs Pub/Sub, consumer groups, `XADD`/`XREADGROUP`, event-flow design |
| `ctb-docker-stack` | CDB repo (`.cursor/skills/ctb-docker-stack/`) | BLUE/RED compose, `cdb_redis` container health, stack bring-up |
| `cdb-shadow-validation` | CDB repo (`.cursor/skills/cdb-shadow-validation/`) | Shadow runs reading `stream.order_results`, orders/signals evidence |

**Streams / PubSub rule:** When reviewing or designing event flows, explicitly
choose Streams (persistent, consumer groups) vs Pub/Sub (ephemeral fan-out). Do
not assume one pattern for all channels.

## Parking lot (explicit scope only — not default)

Do **not** load or recommend these unless a separate, explicit GO and issue scope
covers search, RAG, vector, or semantic-cache enablement:

| Item | Reason parked |
| --- | --- |
| `redis-search` | RQE / FT.* — not CDB default retrieval |
| `redis-semantic-cache` | LangCache / LLM response cache — not enabled |
| RedisVL | Vector client library — not in CDB runtime canon |
| LangCache | Managed semantic cache — not enabled |
| RQE as default | Query engine not default retrieval path |
| Vector Search as CDB brain | Violates Context Brain posture; SurrealDB remains primary |

Parked items may be referenced for future research issues only. They must not
appear in default agent bootstrap or routine service work.

## External Redis documentation

For vendor/plugin behavior beyond this routing doc, use the installed **Cursor
Redis plugin** skills and rules. Do not duplicate vendor docs in the repo. For
other third-party references, follow the same discipline as other external packs:
load only on explicit task need, defensively.

(`cdb-external-docs` is a session slash alias when configured in the operator
environment; it is not a repo-owned skill path.)

## Recommended invocation map

```text
Session start:
  /cdb-session-start → /cdb-control-intake → [optional] /cdb-issue-to-session-plan

Redis code / client / cache review:
  /redis-development → subset: redis-core, redis-connections, redis-security, redis-observability

Event / stack / shadow:
  + /messaging-redis-streams (streams design)
  + /ctb-docker-stack (compose / cdb_redis)
  + /cdb-shadow-validation (shadow evidence)

Subagents (parent-enforced GO):
  /cdb-docs-canon-maintainer, /cdb-governance-gatekeeper,
  /cdb-validation-evidence-analyst, /cdb-repository-auditor
```

## Non-goals (this document)

- No runtime, Docker Compose, or Redis config changes
- No enabling Redis Search, vector indexes, LangCache, or RQE-as-default
- No replacement of SurrealDB Context Intelligence
- No live trading, Echtgeld, or LR posture change (remains **NO-GO**)

## Related canon

| Document | Role |
| --- | --- |
| `agents/OPEN_CODE_AGENTS.md` | OpenCode skill routing (includes Redis pointer) |
| `AGENTS.md` | Root pointer, Redis runtime rules, skills table |
| `agents/AGENTS.md` | Brain Evidence Gate, read order |
| `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` | Brain vs repo-only default |
