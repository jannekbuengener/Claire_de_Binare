# CDB Verfügbare Skills — Übersicht

| Field | Value |
| --- | --- |
| Status | **canonical** (available-skills index) |
| Date | 2026-07-01 |
| Supersedes | [`CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md`](CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md) |
| Related | PR skills-canon-sync, Issue #3598 (Vorgänger-Index) |

## Zweck

Diese Liste fasst **verfügbare Agent-Skills** für CDB-Arbeit zusammen und verweist
auf die jeweiligen SSOT-Dokumente. Sie ersetzt keine Skill-Implementierungen und
erfindet keine neuen Slash-Befehle.

**Registry / Mirror-Modell:** [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md)

**Canon-Update 2026-07-01:** Alle 25 aktiven CDB-Repo-Skills haben
`docs/skills/<name>/SKILL.md` als Single Source of Truth. Surface-Adapter
(`.opencode/`, `.cursor/`, `.codex/`, `.claude/`) sind auf Canon gespiegelt
(Issue #3639; Header `mirrored-from-canon`, Body-Parity verifiziert).

## Grenze: Brain vs Runtime

| Rolle | Technologie | SSOT |
| --- | --- | --- |
| **Brain / Context Intelligence** | SurrealDB Context Brain | [`CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md`](CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md), `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md` |
| **Runtime / Cache / Messaging** | Redis (`cdb_redis`) | [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) |

## Session-Boundary (Pflicht, CDB repo skills)

| Skill | Canon | Surface-Adapter |
| --- | --- | --- |
| `cdb-session-start` | [`cdb-session-start/SKILL.md`](cdb-session-start/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-session-close` | [`cdb-session-close/SKILL.md`](cdb-session-close/SKILL.md) | opencode, cursor, codex, claude — includes Post-Close Follow-up Intake (Issue #3638) |
| `cdb-control-intake` | [`cdb-control-intake/SKILL.md`](cdb-control-intake/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-issue-to-session-plan` | [`cdb-issue-to-session-plan/SKILL.md`](cdb-issue-to-session-plan/SKILL.md) | opencode, cursor, codex, claude |
| `onboarding` | [`onboarding/SKILL.md`](onboarding/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-onboarding` | [`cdb-onboarding/SKILL.md`](cdb-onboarding/SKILL.md) | codex alias → onboarding |

Bootloader vor Skills: `AGENTS.md` → `agents/AGENTS.md` → `agents/OPEN_CODE_AGENTS.md`.

## CDB Repo-Domain-Skills (kanonisch unter docs/skills/)

| Skill | Canon | Zweck |
| --- | --- | --- |
| `cdb-operator` | [`cdb-operator/SKILL.md`](cdb-operator/SKILL.md) | Bootloader, GO gates |
| `cdb-trading-core` | [`cdb-trading-core/SKILL.md`](cdb-trading-core/SKILL.md) | Trading core |
| `cdb-risk-governance` | [`cdb-risk-governance/SKILL.md`](cdb-risk-governance/SKILL.md) | Risk governance |
| `cdb-exchange-adapters` | [`cdb-exchange-adapters/SKILL.md`](cdb-exchange-adapters/SKILL.md) | Exchange adapters |
| `cdb-backtest-engine` | [`cdb-backtest-engine/SKILL.md`](cdb-backtest-engine/SKILL.md) | Backtest |
| `cdb-shadow-validation` | [`cdb-shadow-validation/SKILL.md`](cdb-shadow-validation/SKILL.md) | Shadow validation |
| `cdb-contract-evidence-gatekeeper` | [`cdb-contract-evidence-gatekeeper/SKILL.md`](cdb-contract-evidence-gatekeeper/SKILL.md) | Contract evidence |
| `cdb-drift-reconcile` | [`cdb-drift-reconcile/SKILL.md`](cdb-drift-reconcile/SKILL.md) | Drift reconcile |
| `cdb-ci-cd-guard` | [`cdb-ci-cd-guard/SKILL.md`](cdb-ci-cd-guard/SKILL.md) | CI/CD guardrails |
| `cdb-docs-ops` | [`cdb-docs-ops/SKILL.md`](cdb-docs-ops/SKILL.md) | Docs maintenance |
| `cdb-external-docs` | [`cdb-external-docs/SKILL.md`](cdb-external-docs/SKILL.md) | External docs index |
| `ctb-docker-stack` | [`ctb-docker-stack/SKILL.md`](ctb-docker-stack/SKILL.md) | Docker BLUE+RED |
| `cdb-github-api-ops` | [`cdb-github-api-ops/SKILL.md`](cdb-github-api-ops/SKILL.md) | GitHub API routing |
| `gh-fix-ci` | [`gh-fix-ci/SKILL.md`](gh-fix-ci/SKILL.md) | CI failures |
| `gh-address-comments` | [`gh-address-comments/SKILL.md`](gh-address-comments/SKILL.md) | PR review comments |
| `cdb-test-first` | [`cdb-test-first/SKILL.md`](cdb-test-first/SKILL.md) | Test-first planning |

Vollständige Tabelle: [`README.md`](README.md). Cursor-Pointer: [`AGENTS.md`](../../AGENTS.md).

## SurrealDB Skills (official, curated — Brain-Scope)

| Skill | Canon | Rolle |
| --- | --- | --- |
| `surrealql` | [`surrealql/SKILL.md`](surrealql/SKILL.md) | SurrealQL / Context queries |
| `surrealdb-vector` | [`surrealdb-vector/SKILL.md`](surrealdb-vector/SKILL.md) | Vector in SurrealDB context |
| `surrealdb-python` | [`surrealdb-python/SKILL.md`](surrealdb-python/SKILL.md) | Python SDK |

SSOT Activation: [`CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md`](CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md)

## Redis Skills — Routing SSOT (extern, nicht mirrored)

**SSOT:** [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md)

## Nicht als aktive Skills

- `skillforge/` — Meta-Tool, gitignored
- `mockexchange/` — kein SKILL.md
- `codex-primary-runtime` — kein verifizierter SKILL.md
- Redis Plugin Skills — routing-only
- `.gemini/skills/` — eingeschränkt (4 Skills), kein Domain-Mirror

## Verwandte Dokumente

| Dokument | Rolle |
| --- | --- |
| [`README.md`](README.md) | `docs/skills/` Index (25 Skills) |
| [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) | Mirror-SSOT, Drift-Matrix §16 |
| [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) | Redis-Routing-SSOT |
| [`agents/OPEN_CODE_AGENTS.md`](../../agents/OPEN_CODE_AGENTS.md) | OpenCode Skill Routing |
| [`AGENTS.md`](../../AGENTS.md) | Root pointer |

## Non-goals

- Keine Runtime-/Config-/Compose-Änderungen
- Keine fachliche Erweiterung der Skill-Inhalte in diesem Slice
- Surface-Mirror abgeschlossen (#3639); `cdb-session-close` Follow-up Intake (#3638)
- LR bleibt **NO-GO**
