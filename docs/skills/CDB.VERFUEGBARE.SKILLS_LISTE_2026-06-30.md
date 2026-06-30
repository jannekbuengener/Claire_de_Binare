# CDB Verfügbare Skills — Übersicht

| Field | Value |
| --- | --- |
| Status | **canonical** (available-skills index) |
| Date | 2026-06-30 |
| Issue | GitHub issue #3598 |
| Related | PR #3597, Issue #3596 |

## Zweck

Diese Liste fasst **verfügbare Agent-Skills** für CDB-Arbeit zusammen und verweist
auf die jeweiligen SSOT-Dokumente. Sie ersetzt keine Skill-Implementierungen und
erfindet keine neuen Slash-Befehle.

**Registry / Mirror-Modell:** [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md)

## Grenze: Brain vs Runtime

| Rolle | Technologie | SSOT |
| --- | --- | --- |
| **Brain / Context Intelligence** | SurrealDB Context Brain | [`CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md`](CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md), `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` |
| **Runtime / Cache / Messaging** | Redis (`cdb_redis`) | [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) |

SurrealDB bleibt primäre CDB-Brain-Strategie. Redis bleibt Runtime-/Cache-/
Messaging-Komponente — **kein** Agent-Brain, kein Evidence-/Memory-Ersatz.

## Session-Boundary (Pflicht, CDB repo skills)

| Skill | Surface | Zweck |
| --- | --- | --- |
| `cdb-session-start` | `.cursor/`, `.opencode/`, `.codex/` | Fail-closed Session-Start |
| `cdb-session-close` | `.cursor/`, `.opencode/`, `.codex/` | Session-Abschluss |
| `cdb-control-intake` | repo surfaces | Control/Board/LR-Kontext |
| `cdb-issue-to-session-plan` | repo surfaces | Issue → Session-Plan |

Bootloader vor Skills: `AGENTS.md` → `agents/AGENTS.md` → `agents/OPEN_CODE_AGENTS.md`.

## CDB Repo-Domain-Skills (mirrored surfaces)

Kanonische Quelle für repo-owned Skills: `docs/skills/<name>/SKILL.md` (wenn
vorhanden) bzw. Surface-Adapter unter `.cursor/skills/`, `.opencode/skills/`,
`.codex/cdb_skills/`.

| Skill | Zweck |
| --- | --- |
| `cdb-operator` | Bootloader, GO gates |
| `cdb-trading-core` | Trading core |
| `cdb-risk-governance` | Risk governance |
| `cdb-exchange-adapters` | Exchange adapters |
| `cdb-backtest-engine` | Backtest |
| `cdb-shadow-validation` | Shadow validation (Redis Streams evidence) |
| `cdb-contract-evidence-gatekeeper` | Contract evidence |
| `cdb-drift-reconcile` | Drift reconcile |
| `cdb-ci-cd-guard` | CI/CD guardrails |
| `cdb-docs-ops` | Docs maintenance |
| `ctb-docker-stack` | Docker BLUE+RED (`cdb_redis` health) |
| `cdb-github-api-ops` | GitHub API routing |
| `gh-fix-ci` | CI failures |
| `gh-address-comments` | PR review comments |
| `cdb-test-first` | Test-first planning (Cursor) |

Vollständige Cursor-Tabelle: [`AGENTS.md`](../../AGENTS.md) § Selected repo skills.

## SurrealDB Skills (official, curated — Brain-Scope)

SSOT: [`CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md`](CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md)

| Skill | Rolle |
| --- | --- |
| `surrealql` | SurrealQL / Context queries |
| `surrealdb-vector` | Vector in SurrealDB context (nicht Redis) |
| `surrealdb-python` | Python SDK |

## Redis Skills — Routing SSOT

**SSOT:** [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) (PR #3597)

Redis-Skills stammen vom **Cursor Redis Plugin** (extern, nicht repo-mirrored).
Laden nur nach Session-Bootstrap, task-spezifisch — keine Massenladung.

### Core Set (offiziell für CDB)

| Skill | Zweck |
| --- | --- |
| `redis-development` | Umbrella / Einstieg |
| `redis-core` | Datenmodell, Key-Naming, Hash vs JSON |
| `redis-connections` | Pooling, Pipelining, Timeouts |
| `redis-security` | Auth, ACLs, TLS, Netzwerk |
| `redis-observability` | Metriken, Debug; Review mit `cdb_redis_exporter` |

### Event / Runtime Zusatz (bei passendem Scope)

| Skill | Quelle | Zweck |
| --- | --- | --- |
| `messaging-redis-streams` | Extern (Gemini domain-expert) | Streams vs Pub/Sub, Consumer Groups |
| `ctb-docker-stack` | CDB repo skill | Compose, `cdb_redis` Container |
| `cdb-shadow-validation` | CDB repo skill | Shadow-Runs, `stream.order_results` |

### Parking-Lot (nicht Default — nur expliziter GO/Scope)

| Item | Status |
| --- | --- |
| `redis-search` | geparkt — kein CDB-Default |
| `redis-semantic-cache` | geparkt — kein Enablement |
| RedisVL | geparkt |
| LangCache | geparkt |
| RQE as default | geparkt |
| Vector Search as CDB Brain replacement | **verboten** — verletzt Brain-Posture |

**Keine** Redis-Search-/Vector-/LangCache-Empfehlung als Default in Routine-Arbeit.

## Routing-Kurzreferenz

```text
Session:  /cdb-session-start → /cdb-control-intake → [optional] /cdb-issue-to-session-plan
Redis:    /redis-development + subset (core set) — siehe CDB_REDIS_SKILL_ROUTING.md
Events:   + /messaging-redis-streams | /ctb-docker-stack | /cdb-shadow-validation
Brain:    SurrealDB skills — nicht durch Redis ersetzen
```

## Verwandte Dokumente

| Dokument | Rolle |
| --- | --- |
| [`README.md`](README.md) | `docs/skills/` Index |
| [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) | Mirror-SSOT, Drift-Regeln |
| [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) | Redis-Routing-SSOT |
| [`agents/OPEN_CODE_AGENTS.md`](../../agents/OPEN_CODE_AGENTS.md) | OpenCode Skill Routing |
| [`AGENTS.md`](../../AGENTS.md) | Root pointer, Redis runtime rules |

## Non-goals

- Keine Runtime-/Config-/Compose-Änderungen
- Keine neuen Skill-Implementierungen in diesem Dokument
- LR bleibt **NO-GO**
