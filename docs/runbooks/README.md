# Operative Runbooks (`docs/runbooks/`)

Index für operator- und agent-nahe Runbooks im Working Repo. **Kein** Live-Readiness-SSOT.

## Cockpit (zuerst lesen)

| Dokument | Zweck |
|---|---|
| [`CONTROL_REGISTER.md`](CONTROL_REGISTER.md) | Board-Stage, Workflow-Notizen, operativer Fokus |
| [`control-cockpit/CONTROL_COCKPIT_1445_REBASELINE_2026-05-13.md`](control-cockpit/CONTROL_COCKPIT_1445_REBASELINE_2026-05-13.md) | Cockpit #1445 Rebaseline |
| GitHub Issue **#1445** | Operatives Cockpit (Live-Wahrheit: neuester Kommentar) |
| [`../live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md) | Echtgeld Go/No-Go (**NO-GO**) |

Stage `trade-capable` autorisiert kein Live-Trading.

## Control / GitHub / CI

| Runbook | Thema |
|---|---|
| [`GITHUB_CONTROL_PLANE_RUNBOOK.md`](GITHUB_CONTROL_PLANE_RUNBOOK.md) | Control-plane Betrieb |
| [`GITHUB_CONTROL_PLANE_GRAPH.md`](GITHUB_CONTROL_PLANE_GRAPH.md) | Workflow-Graph |
| [`GITHUB_WORKFLOW_REGISTER.md`](GITHUB_WORKFLOW_REGISTER.md) | Workflow-Register |
| [`merge_policy_ci_gate.md`](merge_policy_ci_gate.md) | PR-Gates, required checks |
| [`merge_strategy_squash_vs_merge.md`](merge_strategy_squash_vs_merge.md) | Merge-Strategie |
| [`ci_hygiene_drift_checks.md`](ci_hygiene_drift_checks.md) | CI-Drift |
| [`resolve_review_threads_via_graphql.md`](resolve_review_threads_via_graphql.md) | Review-Threads |
| [`project_board_automation.md`](project_board_automation.md) | Project v2 / Board |
| [`control_board_board_as_code.md`](control_board_board_as_code.md) | Board-as-Code |

## CDB Automation (Issue #1445-Nachzug)

| Runbook | Thema |
|---|---|
| [`CDB_WEEKLY_CONTROL_HYGIENE_CLASSIFIER.md`](CDB_WEEKLY_CONTROL_HYGIENE_CLASSIFIER.md) | Weekly hygiene |
| [`CDB_DAILY_DELTA_TRIAGE.md`](CDB_DAILY_DELTA_TRIAGE.md) | Daily delta |
| [`CDB_POST_MERGE_FOLLOWUP_SCANNER.md`](CDB_POST_MERGE_FOLLOWUP_SCANNER.md) | Post-merge scan |
| [`CDB_BACKLOG_ANOMALY_ESCALATION.md`](CDB_BACKLOG_ANOMALY_ESCALATION.md) | Backlog escalation |
| [`CDB_CONTROL_FOLLOWUP_CLASSIFIER.md`](CDB_CONTROL_FOLLOWUP_CLASSIFIER.md) | HITL classifier |
| [`CDB_AGENT_SENSES_OPERATOR.md`](CDB_AGENT_SENSES_OPERATOR.md) | Context/MCP operator senses |

## Daten / Infra / Secrets

| Runbook | Thema |
|---|---|
| [`SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](SURREALDB_LOCAL_CONTEXT_RUNTIME.md) | Lokaler Context-Runtime |
| [`surrealdb_context_mcp_access.md`](surrealdb_context_mcp_access.md) | MCP capability matrix |
| [`surrealdb_context_import.md`](surrealdb_context_import.md) | Context import |
| [`surrealdb_context_query.md`](surrealdb_context_query.md) | Context query |
| [`surrealdb_append_only_enforcement.md`](surrealdb_append_only_enforcement.md) | Append-only |
| [`postgres_least_privilege_rls.md`](postgres_least_privilege_rls.md) | Postgres RLS |
| [`redis_aof_corruption_recovery.md`](redis_aof_corruption_recovery.md) | Redis AOF recovery |
| [`cdb_secrets_ssot.md`](cdb_secrets_ssot.md) | Secrets SSOT |
| [`BACKUP_AUTOMATION.md`](BACKUP_AUTOMATION.md) | Backup automation |
| [`local_ops_artifacts.md`](local_ops_artifacts.md) | Lokale Ops-Artefakte |
| [`mcp_worktree_hygiene.md`](mcp_worktree_hygiene.md) | Worktree hygiene |

## Evidence

- [`evidence/`](evidence/) — Run-scoped Evidence (z. B. SurrealDB restore drill); kein Status-SSOT.

## Related

- [`../index.md`](../index.md) — Docs-Hub
- [`../../knowledge/runbooks/`](../../knowledge/runbooks/) — Knowledge-Runbooks (operating rules)
- [`../../.github/README.md`](../../.github/README.md) — Control plane entry
