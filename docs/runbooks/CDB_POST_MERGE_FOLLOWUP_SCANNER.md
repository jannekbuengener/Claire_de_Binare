# CDB Post-Merge Follow-up Scanner

Zweck: kleiner fail-closed V1-Scanner fuer repo-backed Nachzugarbeit nach gemergten PRs.

## Scope

- Workflow: `.github/workflows/cdb-post-merge-followup-scanner.yml`
- Script: `.github/scripts/post_merge_followup_scanner.py`
- nutzt den bestehenden Prompt `.github/prompts/cdb-control-followup.prompt.yml`
- scannt nur gemergte PR-Diffs oder bewusst gesetzte `workflow_dispatch`-Revalidierungen
- mutiert niemals Repo-Dateien

## V1-Regeln

1. `architecture_service_catalog_drift`
   - service-/runtime-nahe Aenderungen ohne Nachzug in:
     - `knowledge/ARCHITECTURE_MAP.md`
     - `knowledge/governance/SERVICE_CATALOG.md`
   - **Suppression:** unterdrueckt, wenn alle betroffenen service-/runtime-nahen Dateien ausschliesslich einen `@sha256`-Digest-Bump enthalten und der semantische Image-Tag unveraendert bleibt (digest-only image-pin, z.B. `postgres:15.17-alpine@sha256:old` → `postgres:15.17-alpine@sha256:new`); gilt fuer `image:`-Zeilen in Compose-Dateien und `FROM`-Zeilen in Dockerfiles — implementiert in PR #1729 (#1726)
2. `runbook_evidence_followup_drift`
   - workflow-/control-nahe Aenderungen ohne Runbook-/Evidence-Begleitung in:
     - `docs/runbooks/`
     - `docs/operations/`
     - `docs/ci/`
     - `CURRENT_STATUS.md`
     - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
3. `discovery_surface_drift`
   - operator-/front-door-nahe Aenderungen ohne Nachzug in:
     - `mcp_navpack_working_repo/ENTRYPOINTS.yaml`
     - `mcp_navpack_working_repo/CHEATSHEET.md`
4. `canon_terminology_drift`
   - offensichtliche Re-Introduktion bekannter Canon-Verstoesse in aktiven Diffs

## Klassifikation und Ausgabe

- jede repo-backed V1-Feststellung wird ueber den bestehenden Control-Follow-up-Prompt klassifiziert:
  - `report_only`
  - `follow_up_issue`
  - `unclear`
- `follow_up_issue`
  - erzeugt ein enges dedupe-sicheres GitHub-Issue
- `report_only` oder `unclear`
  - werden dedupe-sicher als Kommentar unter `#1445` festgehalten
- kein Befund
  - nur Step Summary + Artefakt, kein Kommentar, kein Issue

## Dedupe

- Folge-Issues tragen einen versteckten Marker pro PR + Regel + Triggerdateien
- der Kommentarpfad unter `#1445` hat einen versteckten Marker pro PR
- Re-Runs derselben PR aktualisieren den bestehenden Kommentar oder referenzieren das bestehende Issue statt Doppelungen zu erzeugen

## Ausfuehrung

1. GitHub Actions -> `CDB Post-Merge Follow-up Scanner`
2. fuer Revalidierung:
   - `pr_number` setzen
   - `publish_mode` waehlen:
     - `dry_run`
     - `publish`
3. der automatische Pfad auf `pull_request.closed` laeuft nur fuer wirklich gemergte PRs und publiziert immer im `publish`-Modus
4. lokales `dry_run` mit Models-Token ist moeglich; der echte Kommentar-/Issue-Pfad braucht Schreibrechte und wird deshalb bevorzugt im GitHub-Workflow validiert

## Guardrails

- fail-closed, wenn die PR nicht gemergt ist
- fail-closed, wenn der Prompt kein valides JSON liefert
- kein Auto-Issue fuer unklare oder schwache Evidenz
- kein Auto-Issue-Duplikat fuer denselben repo-backed Befund
