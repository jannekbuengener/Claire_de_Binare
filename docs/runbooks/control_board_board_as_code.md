# Control Board – Board as Code

**Stand:** 2026-07-16

## Aktive Pfade

| Aufgabe | Workflow |
|---|---|
| Periodischer Board-Upsert | `control_board_upsert.yml` |
| Tägliche Reconciliation | `project_reconcile_daily.yml` |
| Neue Issues zum Projekt hinzufügen | `add_to_project.yml` |
| Status → Label | `project_status_label_map.yml` |
| Label → Status | `project_status_sync.yml` |
| Milestone → Stage-Label | `milestone_stage_label_sync.yml` |

Der frühere separate Per-Event-Router und sein Label-Dispatch wurden entfernt.
Board-Konsistenz wird ausschließlich durch die oben dokumentierten aktiven
Pfade hergestellt.

## Feature Toggle und Authentifizierung

Vor mutierenden Board-Läufen müssen Repository-Variablen und Token-Scope
explizit geprüft werden. Fehlende Project-v2-Berechtigungen sind ein harter
Fehler; ein Run darf daraus keinen erfolgreichen Reconcile ableiten.

## Betriebsablauf

1. `control_board_upsert.yml` oder `project_reconcile_daily.yml` ausführen.
2. Run-Summary und Project-v2-API-Ergebnis prüfen.
3. Stichprobe aus Issue-Status, Labels und Board-Spalte vergleichen.
4. Abweichungen dedupliziert als enges Follow-up erfassen.
5. Kein LR- oder Trading-Signal aus Board-Konsistenz ableiten.

## Änderungspflicht

Änderungen an Board-Workflows müssen zusammen mit
`GITHUB_WORKFLOW_REGISTER.md`, `GITHUB_CONTROL_PLANE_GRAPH.md` und den
zugehörigen Contract-Tests landen.
