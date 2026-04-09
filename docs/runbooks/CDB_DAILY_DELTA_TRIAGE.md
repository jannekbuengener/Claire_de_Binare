# CDB Daily Delta Triage

Zweck: leichte taegliche Fresh-Delta-Lane fuer den operativen Control-Thread `#1445`.

## Scope

- Workflow: `.github/workflows/cdb-daily-delta-triage.yml`
- Script: `.github/scripts/daily_delta_triage.py`
- Lane: daily fresh deltas (Di/Mi/Fr/So), nicht post-merge, nicht weekly hygiene
- Output:
  - dedupe-sicherer Tageskommentar unter `#1445`
  - optional enges Follow-up-Issue, hart gecappt auf `0..1` pro Run

## Abgrenzung

- Slice 1 bleibt Post-Merge-Scan:
  - `.github/workflows/cdb-post-merge-followup-scanner.yml`
- Slice 2 bleibt Weekly hygiene/reconciliation:
  - `.github/workflows/cdb-weekly-control-hygiene-classifier.yml`

Slice 3 bewertet nur neue Delta-Fingerprints seit dem letzten Daily-Marker.

## V1-Regelklassen

1. `register_missing_workflow_file`
   - Workflow steht in `CONTROL_REGISTER`, aber Datei fehlt in `.github/workflows/`
2. `recent_workflow_failure_delta`
   - neuer Failure-Delta im Lookback-Fenster (`30h`)
3. `new_open_pr_delta`
   - neue offene PRs im Lookback-Fenster (nur Kontrollsignal, kein Auto-Issue)

## Klassifikation und Guardrails

- Klassen bleiben strikt:
  - `report_only`
  - `follow_up_issue`
  - `unclear`
- harte Regeln:
  - keine automatische Repo-Mutation
  - kein Issue-Spam
  - Follow-up-Issues pro Lauf maximal `1`
  - dedupe ueber Fingerprint-Marker in Kommentar und Folge-Issue

## Trigger

- `schedule`:
  - Dienstag 06:20 UTC
  - Mittwoch 06:20 UTC
  - Freitag 06:20 UTC
  - Sonntag 06:20 UTC
- `workflow_dispatch`:
  - `publish_mode`: `dry_run` oder `publish`
  - `max_followup_issues`: `0..1`

## Ergebnis

- Step Summary + Artifact `cdb-daily-delta-triage`
- bei `publish`:
  - Tageskommentar unter `#1445` (upsert pro Kalendertag)
  - optional ein enges Follow-up-Issue nur bei klarem, kleinem Delta
