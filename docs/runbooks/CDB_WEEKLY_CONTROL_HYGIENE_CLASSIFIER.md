# CDB Weekly Control Hygiene Classifier

Zweck: kleiner weekly hygiene/reconciliation Layer fuer den operativen Control-Thread `#1445`.

## Scope

- Workflow: `.github/workflows/cdb-weekly-control-hygiene-classifier.yml`
- Script: `.github/scripts/weekly_control_hygiene_classifier.py`
- Lane: weekly hygiene/reconciliation (Mo/Do/Fr), nicht post-merge, nicht daily delta
- Output:
  - ein dedupe-sicherer Wochenkommentar unter `#1445`
  - optional enge Follow-up-Issues, hart gecappt auf `0..2` pro Run

## Abgrenzung

- Slice 1 bleibt der unmittelbare Post-Merge-Scanner:
  - `.github/workflows/cdb-post-merge-followup-scanner.yml`
- Slice 3 bleibt die taegliche Fresh-Delta-Lane:
  - `#1567`
- Slice 2 soll nur weekly hygiene/reconciliation aggregieren.

## V1-Regelklassen

1. `parked_active_drift`
   - `status:parked` plus aktive Delivery-Labels (`prio:*`, `stage:*`, `milestone:*`)
2. `old_open_issues_without_leverage`
   - offene, nicht geparkte Issues aelter als 60 Tage (report-first Snapshot)
3. `workflow_register_drift`
   - Drift zwischen `docs/runbooks/CONTROL_REGISTER.md` Trigger-Note und realen Workflow-Triggers
4. `workflow_noise`
   - wiederholte Failure-Muster auf aktiven Workflows im 21-Tage-Fenster

## Klassifikation und Guardrails

- Klassifikationen bleiben strikt:
  - `report_only`
  - `follow_up_issue`
  - `unclear`
- harte Regeln:
  - kein Auto-Repo-Change
  - kein Issue-Flood
  - Follow-up-Issues pro Run max `2`
  - dedupe ueber stabile Marker im Kommentar und im Folge-Issue

## Trigger

- `schedule`:
  - Montag 07:30 UTC
  - Donnerstag 07:30 UTC
  - Freitag 07:30 UTC
- `workflow_dispatch`:
  - `publish_mode`: `dry_run` oder `publish`
  - `max_followup_issues`: `0..2`

## Ergebnis

- Step Summary + Artifact `cdb-weekly-control-hygiene`
- bei `publish`:
  - Wochenkommentar unter `#1445` wird erstellt/aktualisiert
  - Follow-up-Issues nur fuer klare, kleine Pakete und nur innerhalb des Caps
