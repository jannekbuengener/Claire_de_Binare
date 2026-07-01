# CDB Skills (`/docs/skills/`)

Status: kanonische Skill-Flaeche (siehe `SKILL_SURFACE_REGISTRY.md`).

`docs/skills/` ist die **Single Source of Truth** fuer CDB-Skills.
Alle anderen Surface-Pfade (`.opencode/`, `.cursor/`, `.codex/`,
`.claude/`) sind Mirror-Adapter und muessen gegen diese Dateien
synchron gehalten werden.

**Aenderungen an Skills starten hier.** Surface-Adapter werden daraus gespiegelt
(`Sync Status: mirrored-from-canon`, Last Verified 2026-07-01, Issue #3639).

## Kanonische Skill-Dateien (28 aktive CDB-Repo-Skills)

| Skill | Pfad | Surfaces |
|---|---|---|
| `onboarding` | [`onboarding/SKILL.md`](onboarding/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-onboarding` | [`cdb-onboarding/SKILL.md`](cdb-onboarding/SKILL.md) | codex (alias → onboarding) |
| `cdb-session-start` | [`cdb-session-start/SKILL.md`](cdb-session-start/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-session-close` | [`cdb-session-close/SKILL.md`](cdb-session-close/SKILL.md) | opencode, cursor, codex, claude — Post-Close Follow-up Intake (#3638) |
| `cdb-control-intake` | [`cdb-control-intake/SKILL.md`](cdb-control-intake/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-issue-to-session-plan` | [`cdb-issue-to-session-plan/SKILL.md`](cdb-issue-to-session-plan/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-operator` | [`cdb-operator/SKILL.md`](cdb-operator/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-test-first` | [`cdb-test-first/SKILL.md`](cdb-test-first/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-trading-core` | [`cdb-trading-core/SKILL.md`](cdb-trading-core/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-risk-governance` | [`cdb-risk-governance/SKILL.md`](cdb-risk-governance/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-exchange-adapters` | [`cdb-exchange-adapters/SKILL.md`](cdb-exchange-adapters/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-backtest-engine` | [`cdb-backtest-engine/SKILL.md`](cdb-backtest-engine/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-shadow-validation` | [`cdb-shadow-validation/SKILL.md`](cdb-shadow-validation/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-contract-evidence-gatekeeper` | [`cdb-contract-evidence-gatekeeper/SKILL.md`](cdb-contract-evidence-gatekeeper/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-drift-reconcile` | [`cdb-drift-reconcile/SKILL.md`](cdb-drift-reconcile/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-root-cause` | [`cdb-root-cause/SKILL.md`](cdb-root-cause/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-symptom-triage` | [`cdb-symptom-triage/SKILL.md`](cdb-symptom-triage/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-regression-gap` | [`cdb-regression-gap/SKILL.md`](cdb-regression-gap/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-docs-ops` | [`cdb-docs-ops/SKILL.md`](cdb-docs-ops/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-external-docs` | [`cdb-external-docs/SKILL.md`](cdb-external-docs/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-ci-cd-guard` | [`cdb-ci-cd-guard/SKILL.md`](cdb-ci-cd-guard/SKILL.md) | opencode, cursor, codex, claude |
| `ctb-docker-stack` | [`ctb-docker-stack/SKILL.md`](ctb-docker-stack/SKILL.md) | opencode, cursor, codex, claude |
| `gh-fix-ci` | [`gh-fix-ci/SKILL.md`](gh-fix-ci/SKILL.md) | opencode, cursor, codex, claude |
| `gh-address-comments` | [`gh-address-comments/SKILL.md`](gh-address-comments/SKILL.md) | opencode, cursor, codex, claude |
| `cdb-github-api-ops` | [`cdb-github-api-ops/SKILL.md`](cdb-github-api-ops/SKILL.md) | opencode, cursor, codex, claude |
| `surrealql` | [`surrealql/SKILL.md`](surrealql/SKILL.md) | opencode, cursor, codex, claude |
| `surrealdb-vector` | [`surrealdb-vector/SKILL.md`](surrealdb-vector/SKILL.md) | opencode, cursor, codex, claude |
| `surrealdb-python` | [`surrealdb-python/SKILL.md`](surrealdb-python/SKILL.md) | opencode, cursor, codex, claude |

## Routing / Index (kein SKILL.md-Mirror)

| Dokument | Pfad | Rolle |
|---|---|---|
| Redis Skill Routing (SSOT) | [`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md) | PR #3597 |
| Verfuegbare Skills (Index) | [`CDB.VERFUEGBARE.SKILLS_LISTE_2026-07-01.md`](CDB.VERFUEGBARE.SKILLS_LISTE_2026-07-01.md) | aktueller Index |
| Verfuegbare Skills (Vorgaenger) | [`CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md`](CDB.VERFUEGBARE.SKILLS_LISTE_2026-06-30.md) | PR #3598 |
| SurrealDB Skills Activation | [`CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md`](CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md) | #3482 |

## Nicht als aktive Skills

| Fläche | Grund |
|---|---|
| `skillforge/` | Meta-Tool, gitignored, Registry §5 |
| `mockexchange/` | Kein `SKILL.md` |
| `codex-primary-runtime` | Kein verifizierter Skill-Inhalt |
| `.cursor/rules/`, `.cursor/agents/` | Rules/Subagents |
| Redis Plugin Skills | Routing-only (extern) |
| `.claude/skills/*.skill` | Alias/Paketfläche, nicht primäre Quelle |
| `.gemini/skills/` | Eingeschraenkt (4 Skills), nicht Domain-Mirror |

## Redis Skills (extern — Routing only)

Redis-Plugin-Skills sind **nicht** repo-mirrored. Routing-SSOT:
[`CDB_REDIS_SKILL_ROUTING.md`](CDB_REDIS_SKILL_ROUTING.md).

## Registry

- [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md): verbindliche
  Definition der kanonischen Flaeche, Inventar, Drift-Matrix und Adapter-Regeln.

## Neue Skills

Bitte zuerst in `docs/skills/<skill-name>/SKILL.md` anlegen, dann auf
die Surfaces spiegeln. Workflow-Details siehe Registry, Abschnitt 9.

## Anti-Pattern

- Do NOT Skills direkt in `.opencode/`, `.cursor/`, `.codex/`,
  `.claude/` ohne kanonische Datei in `docs/skills/` anlegen.
- Do NOT Mirror-Kopien ohne Pflicht-Header aus Registry, Abschnitt 7.

## Related Surfaces

OpenCode: [`.opencode/skills/README.md`](../../.opencode/skills/README.md)
Cursor: [`.cursor/skills/README.md`](../../.cursor/skills/README.md)
Codex: [`.codex/cdb_skills/README.md`](../../.codex/cdb_skills/README.md)
Claude: [`.claude/skills/`](../../.claude/skills/)
Registry: [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md)
