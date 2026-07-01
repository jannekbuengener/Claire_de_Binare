# Cursor Skills (`/.cursor/skills/`)

Repo-versionierte Session-Skills für Cursor Agents. Jeder Skill lebt in `<name>/SKILL.md`.

## Session boundary (Pflicht)

| Skill | Wann |
|---|---|
| [`cdb-session-start`](cdb-session-start/SKILL.md) | Vor Repo-/GitHub-/Implementierungsarbeit |
| [`cdb-session-close`](cdb-session-close/SKILL.md) | Nach Implementierung/Validierung, vor Abschluss |

## Control / planning

| Skill | Zweck |
|---|---|
| [`cdb-control-intake`](cdb-control-intake/SKILL.md) | Control context (Register, LR, status) |
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
| [`cdb-docs-ops`](cdb-docs-ops/SKILL.md) | Docs maintenance |
| [`ctb-docker-stack`](ctb-docker-stack/SKILL.md) | Docker BLUE+RED |
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

- Codex: [`.codex/cdb_skills/README.md`](../../.codex/cdb_skills/README.md)
- OpenCode: [`.opencode/skills/README.md`](../../.opencode/skills/README.md)
- Subagents (delegation only): [`.cursor/agents/README_CDB_CURSOR_SUBAGENTS.md`](../agents/README_CDB_CURSOR_SUBAGENTS.md)
- Registry: [`agents/AGENTS.md`](../../agents/AGENTS.md)

## Rule

Skills strukturieren Arbeit; sie ersetzen keine Human-GO, LR-SSOT oder Write-Gates in `knowledge/governance/CDB_AGENT_POLICY.md`.
