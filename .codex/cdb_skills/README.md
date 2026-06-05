# Codex Skills (`/.codex/cdb_skills/`)

Repo-versionierte Session-Skills für Codex. Jeder Skill lebt in `<name>/SKILL.md`.

Spiegelt die Cursor-Skill-Oberfläche unter [`.cursor/skills/README.md`](../../.cursor/skills/README.md). Das entfernte `cdb_agent_sdk/`-Paket wurde durch repo-lokale Skill-Packs ersetzt (PR #2994).

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
| [`cdb-trading-core`](cdb-trading-core/SKILL.md) | Trading core |
| [`cdb-risk-governance`](cdb-risk-governance/SKILL.md) | Risk governance |
| [`cdb-exchange-adapters`](cdb-exchange-adapters/SKILL.md) | Exchange adapters |
| [`cdb-backtest-engine`](cdb-backtest-engine/SKILL.md) | Backtest |
| [`cdb-shadow-validation`](cdb-shadow-validation/SKILL.md) | Shadow validation |
| [`cdb-contract-evidence-gatekeeper`](cdb-contract-evidence-gatekeeper/SKILL.md) | Contract evidence |
| [`cdb-drift-reconcile`](cdb-drift-reconcile/SKILL.md) | Drift reconcile |
| [`cdb-docs-ops`](cdb-docs-ops/SKILL.md) | Docs maintenance |
| [`ctb-docker-stack`](ctb-docker-stack/SKILL.md) | Docker BLUE+RED |
| [`cdb-ci-cd-guard`](cdb-ci-cd-guard/SKILL.md) | CI/CD guardrails |

## GitHub helpers

| Skill | Zweck |
|---|---|
| [`gh-fix-ci`](gh-fix-ci/SKILL.md) | CI failures |
| [`gh-address-comments`](gh-address-comments/SKILL.md) | PR review comments |

## Related surfaces

- Cursor: [`.cursor/skills/README.md`](../../.cursor/skills/README.md)
- OpenCode: [`.opencode/skills/README.md`](../../.opencode/skills/README.md)
- Agent registry: [`agents/AGENTS.md`](../../agents/AGENTS.md)
