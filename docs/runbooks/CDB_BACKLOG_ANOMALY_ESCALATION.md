# CDB Backlog Anomaly Escalation (Phase 1)

Zweck: separate, fail-closed Eskalationslane fuer starke typed Anomalien aus der
artifact-only Backlog-Curation (`cdb-backlog-curation.yml`), ohne die Phase-0-Curation
zu einer Auto-Issue-Kanone zu machen.

## Surfaces

- Workflow: `.github/workflows/cdb-backlog-anomaly-escalation.yml`
- Script: `.github/scripts/backlog_anomaly_escalation.py`
- Handoff-Artifact: `artifacts/backlog-curation/issue-<number>.json`

## Lane-Split

1. **Detector / Handoff Producer (Phase 0)**
   - `.github/scripts/backlog_curation.py`
   - erzeugt curation artifact + typed `anomalies` block
   - keine Issue-/Kommentar-Mutation
2. **Decision / Classifier / Issue-Emitter (Phase 1)**
   - `.github/scripts/backlog_anomaly_escalation.py`
   - klassifiziert je Anomalie in `report_only`, `follow_up_issue`, `unclear`
   - emittiert nur bei starken, erlaubten, dedupe-sicheren Befunden

## Typed anomaly contract (Handoff)

Jeder Befund in `anomalies.findings[]` liefert mindestens:

- `id` (Fingerprint)
- `type` (`broken_reference`, `missing_runbook`, `architecture_doc_drift`, `workflow_doc_drift`, `missing_expected_source`)
- `confidence` (0..1)
- `strength` (`strong|medium|weak`)
- `summary`
- `evidence[]`
- `affected_artifacts[]`
- `minimum_evidence_met`
- `escalation_hint`
- `public_issue_allowed`

## Confidence-/Threshold-Regeln

| Typ | Minimale Evidenz | Default-Confidence | Escalation-Threshold |
|---|---|---:|---:|
| `broken_reference` | explizit referenzierter Repo-Pfad fehlt im Checkout | 0.93 | 0.86 |
| `missing_expected_source` | kanonische `must_read`-Quelle fehlt im Repo | 0.96 | 0.90 |
| `missing_runbook` | Workflow-/Control-Kontext ohne konkrete Runbook-Referenz | 0.62 | 0.94 |
| `workflow_doc_drift` | Workflow + Workflow-Doku mit Drift-Signal im Issue-Text | 0.80 | 0.90 |
| `architecture_doc_drift` | Architektur-Surface + Drift-Signal im Issue-Text | 0.78 | 0.92 |

Regel: `follow_up_issue` nur bei `strength=strong`, `minimum_evidence_met=true`,
passendem `escalation_hint=follow_up_candidate` und Typ-spezifischem Threshold.

## Dedupe + Bounded emission

- Marker pro Anomalie: `<!-- cdb-backlog-anomaly-followup:<fingerprint> -->`
- Dedupe gegen offene Issues:
  - exakter Marker-Match
  - thematischer Match (`Backlog anomaly: <type>` + `Source issue: #<n>`)
- Hard cap: max `0..1` neu erzeugte Follow-up-Issues pro Run
- bei Budget-Erschoepfung: demote zu `report_only`

## Guardrails

- sensitive/private Kontext (`labels` oder Textsignale) blockiert public auto-issueing
- schwache/ambige Befunde werden nicht emittiert (`report_only` / `unclear`)
- kein Runtime-/Compose-/Deploy-Pfad
- keine Repo-Datei-Mutationen durch die Lane selbst
