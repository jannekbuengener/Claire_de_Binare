# OpenCode Skills (`/.opencode/skills/`)

Repo-versionierte Session-Skills für OpenCode. Jeder Skill lebt in `<name>/SKILL.md`.

Spiegelt die Cursor-Skill-Oberfläche unter [`.cursor/skills/README.md`](../../.cursor/skills/README.md). Das entfernte `cdb_agent_sdk/`-Paket wurde durch repo-lokale Skill-Packs ersetzt (PR #2994).

## Onboarding (Pflicht fuer neue Agenten/Entwickler)

| Skill | Wann |
|---|---|
| [`onboarding`](onboarding/SKILL.md) | Erste Session, Bootloader, Context Brain Preflight, Tour, Doctor, First-Issue Sandbox |

## Session boundary (Pflicht)

| Skill | Wann |
|---|---|
| [`cdb-session-start`](cdb-session-start/SKILL.md) | Vor Repo-/GitHub-/Implementierungsarbeit |
| [`cdb-session-close`](cdb-session-close/SKILL.md) | Nach Implementierung/Validierung |

## Control / planning

| Skill | Zweck |
|---|---|
| [`cdb-control-intake`](cdb-control-intake/SKILL.md) | Control context |
| [`cdb-issue-to-session-plan`](cdb-issue-to-session-plan/SKILL.md) | Issue → Session-Plan |
| [`cdb-operator`](cdb-operator/SKILL.md) | Bootloader, GO gates |

## Domain

| Skill | Zweck |
|---|---|
| [`cdb-test-first`](cdb-test-first/SKILL.md) | Test-first planning, testarten, metadaten |
| [`cdb-trading-core`](cdb-trading-core/SKILL.md) | Trading core |
| [`cdb-risk-governance`](cdb-risk-governance/SKILL.md) | Risk governance |
| [`cdb-exchange-adapters`](cdb-exchange-adapters/SKILL.md) | Exchange adapters |
| [`cdb-backtest-engine`](cdb-backtest-engine/SKILL.md) | Backtest |
| [`cdb-shadow-validation`](cdb-shadow-validation/SKILL.md) | Shadow validation |
| [`cdb-contract-evidence-gatekeeper`](cdb-contract-evidence-gatekeeper/SKILL.md) | Contract evidence |
| [`cdb-drift-reconcile`](cdb-drift-reconcile/SKILL.md) | Drift reconcile |
| [`cdb-root-cause`](cdb-root-cause/SKILL.md) | Symptom to root-cause isolation, evidence, fix plan |
| [`cdb-symptom-triage`](cdb-symptom-triage/SKILL.md) | Frame and route a raw debug symptom |
| [`cdb-regression-gap`](cdb-regression-gap/SKILL.md) | Name the missing test/guard/evidence for a defect |
| [`cdb-debug-handoff`](cdb-debug-handoff/SKILL.md) | Package a resolved/parked debug record and route it onward |
| [`cdb-docs-ops`](cdb-docs-ops/SKILL.md) | Docs maintenance |
| [`ctb-docker-stack`](ctb-docker-stack/SKILL.md) | Docker BLUE+RED |
| [`cdb-ci-cd-guard`](cdb-ci-cd-guard/SKILL.md) | CI/CD guardrails |
| [`surrealql`](surrealql/SKILL.md) | CDB-curated official SurrealQL skill |
| [`surrealdb-vector`](surrealdb-vector/SKILL.md) | CDB-curated official vector skill |
| [`surrealdb-python`](surrealdb-python/SKILL.md) | CDB-curated official Python SDK skill |

## GitHub helpers

| Skill | Zweck |
|---|---|
| [`gh-fix-ci`](gh-fix-ci/SKILL.md) | CI failures |
| [`gh-address-comments`](gh-address-comments/SKILL.md) | PR review comments |
| [`cdb-github-api-ops`](cdb-github-api-ops/SKILL.md) | GitHub API-aware agent routing |

## Canonical skill source

- `docs/skills/` ist die kanonische Skill-Flaeche.
- Jede Surface-Kopie muss den Pflicht-Header aus Registry Abschnitt 7 tragen.
- Registry: [`docs/skills/SKILL_SURFACE_REGISTRY.md`](../../docs/skills/SKILL_SURFACE_REGISTRY.md).

## Related surfaces

- Cursor: [`.cursor/skills/README.md`](../../.cursor/skills/README.md)
- Codex: [`.codex/cdb_skills/README.md`](../../.codex/cdb_skills/README.md)
- Agent registry: [`agents/AGENTS.md`](../../agents/AGENTS.md)
