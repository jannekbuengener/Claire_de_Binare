# Control Board Automation Rollout Status (2026-02-26)

## Kontext
- PR #947 ist gemerged; Merge-Commit: `8905b749455af6875b71a5f4ccebd1a68a67de5e`.
- Die Workflows `control_board_auto_routing.yml` und `control_board_upsert.yml` sind aktiv.
- Die Repo-Variable `CDB_CONTROL_BOARD_AUTOMATION_ENABLED` ist nicht gesetzt; Toggle ist damit effektiv OFF.
- Tracking: #948 (Rollout Gate: Control Board Automation Smoke-Test (toggle-gated))

## Enthaltene Komponenten (High Level)
- Board-as-Code Upsert fuer Project-Felder und Views.
- Auto-Routing fuer Issues/PRs ins Project `CDB Control Board`.
- Hard toggle gating (`== 'true'`) vor mutierenden Project-API-Calls.
- Safeguards gegen unbeabsichtigte Ueberschreibungen und gegen Doppel-Events.
- Runbook-Abdeckung in `docs/runbooks/control_board_board_as_code.md` und `docs/runbooks/project_board_automation.md`.

## Betriebsmodus
### OFF (Default)
- Erwartetes Verhalten: Workflows duerfen triggern, loggen `automation disabled` und beenden vor jedem Project-Write (zero-write).

### ON (kontrolliert)
- Erwartetes Verhalten: Routing/Upsert greifen, Items werden ins Project aufgenommen und Felder nach Regeln gesetzt.

## Smoke-Test Runbook (kompakt)
### 1) OFF-Test (zero-write)
- Toggle bleibt OFF (`CDB_CONTROL_BOARD_AUTOMATION_ENABLED` nicht gesetzt oder `!= 'true'`).
- Test-Issue mit Stage-Label und `P`-Praefix oder `prio`-Label anlegen.
- Workflow-Run pruefen: `automation disabled` vor jedem Project-Write.
- Evidence: siehe #948 (Abschnitt "OFF-Test (zero-write)") — dort werden Workflow-Run-Links gepflegt.

### 2) ON-Test (kontrolliert)
- Toggle temporaer auf `true` setzen.
- Routing/Upsert per `workflow_dispatch` triggern.
- Neues Issue `P1 Smoke Test` mit genau einem Stage-Label anlegen.
- Im Project pruefen: Item vorhanden; Stage/Priority gesetzt; Status nur wenn leer; Milestone nur wenn leer oder automation-managed; Konflikte fuehren zu Warnung und keiner Mutation.
- Evidence: siehe #948 (Abschnitt "ON-Test (kontrolliert)") — dort werden Workflow-Run + Project-Item Links gepflegt.

### 3) Rollback
- Toggle wieder OFF setzen (unset oder `!= 'true'`).
- Folge-Events pruefen: erneut zero-write skip.
- Evidence: siehe #948 (Abschnitt "Rollback") — dort werden Workflow-Run-Links gepflegt.

## Risiken und Guardrails
- Default OFF minimiert Side Effects.
- `Status=Backlog` wird nur gesetzt, wenn Status leer ist.
- Milestone-Mapping ueberschreibt keine fremden Milestones (nur leer oder automation-managed).
- Konflikte bei Mehrfach-Stage/Priority fuehren zu Warnung und keiner Mutation; Concurrency reduziert Doppel-Event-Writes.

## Next Steps
- Smoke-Test gemaess Issue #948 in der Reihenfolge OFF -> ON -> Rollback ausfuehren.
- Evidence-Links aus allen drei Phasen in Issue #948 dokumentieren.
- Toggle-Policy verbindlich festlegen (Freigabe, Dauer, Ruecksetzen auf OFF).
- Kurzreview nach erstem ON-Lauf dokumentieren (Soll/Ist, Abweichungen, Follow-ups).
