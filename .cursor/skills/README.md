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
| [`cdb-trading-core`](cdb-trading-core/SKILL.md) | Trading core |
| [`cdb-risk-governance`](cdb-risk-governance/SKILL.md) | Risk governance |
| [`cdb-exchange-adapters`](cdb-exchange-adapters/SKILL.md) | Exchange adapters |
| [`cdb-backtest-engine`](cdb-backtest-engine/SKILL.md) | Backtest |
| [`cdb-shadow-validation`](cdb-shadow-validation/SKILL.md) | Shadow validation |
| [`cdb-contract-evidence-gatekeeper`](cdb-contract-evidence-gatekeeper/SKILL.md) | Contract evidence |
| [`cdb-drift-reconcile`](cdb-drift-reconcile/SKILL.md) | Drift reconcile |
| [`cdb-docs-ops`](cdb-docs-ops/SKILL.md) | Docs maintenance |
| [`ctb-docker-stack`](ctb-docker-stack/SKILL.md) | Docker BLUE+RED |

## GitHub helpers

| Skill | Zweck |
|---|---|
| [`gh-fix-ci`](gh-fix-ci/SKILL.md) | CI failures |
| [`gh-address-comments`](gh-address-comments/SKILL.md) | PR review comments |

## Related surfaces

- Codex: `.codex/cdb_skills/` (gleiche Skill-Namen, wo migriert)
- OpenCode: `.opencode/skills/`
- Subagents (delegation only): `.cursor/agents/README_CDB_CURSOR_SUBAGENTS.md`
- Registry: `agents/AGENTS.md`

## Rule

Skills strukturieren Arbeit; sie ersetzen keine Human-GO, LR-SSOT oder Write-Gates in `knowledge/governance/CDB_AGENT_POLICY.md`.
