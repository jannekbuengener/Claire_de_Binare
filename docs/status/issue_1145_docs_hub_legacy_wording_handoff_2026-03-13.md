# Issue #1145 Handoff - Docs Hub Legacy Wording / Shim Trim

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- Der heutige Repo-Stand ist bereits enger als die alte Split-Repo-Lage:
  - `docs_hub_snapshot` ist lokal nur noch Read-only-Archiv, Provenienz und schmale Kompatibilitaetsflaeche.
  - Die meisten verbliebenen Docs-Hub-Nennungen sitzen in bewusst erhaltenen Closeout-, Archive- oder Shim-Dateien.
  - Das Issue-Body-Update von `#1145` passt dazu: keine Code-/Script-/Config-Verhaltensaenderung, keine Archive-Pruning-Arbeit.
- Der verbleibende aktive Drift ist klein und konkret:
  - `DOCS_MOVED_TO_DOCS_HUB.md` traegt noch die staerkste falsche Richtung im Dateinamen/Titel, obwohl der Inhalt nur noch ein lokaler Pointer ist.
  - `mcp_navpack_working_repo/DOCS_HUB.pointer.md` und `mcp_navpack_working_repo/DOCS_HUB.pointer.json` sind weiterhin aktive Pointer-Shims, formulieren aber teils noch zu breit ueber "compatibility recovery" und spaetere Konsolidierung.
  - `docs/governance/no_human_review_policy.md` verlangt fuer Invariant-Aenderungen noch einen "link to DocsHub change", obwohl der lokale Working-Repo-Canon massgeblich ist.
  - `docs/live-readiness/LR-007-STATUS.md` beschreibt PR #814 noch als Bruecke zu "DocsHub canonical SYSTEM_INVARIANTS.md" samt gepinntem DocsHub-Commit. Das ist in einer aktiven Statusseite stale.
- Load-bearing und bewusst zu erhalten:
  - `docs/meta/WORKING_REPO_CANON.md` ist die aktive Canon-/Redirect-Datei und kein Altlast-Fund.
  - `AGENTS.md`, `agents/AGENTS.md`, `knowledge/SYSTEM.CONTEXT.md` und `knowledge/CDB_KNOWLEDGE_HUB.md` erwaehnen das lokale Archiv bereits korrekt als nicht-default.
  - Behavior-bearing Kompatibilitaetsnamen bleiben real aktiv:
    - `DOCS_HUB_PATH` in `infrastructure/scripts/docs_hub_rag_adapter.py` und `infrastructure/scripts/discussion_pipeline/utils/config_loader.py`
    - `--docs-hub` in den Discussion-Pipeline-CLI-Surfaces
    - Workflow-/Check-Name `Docs Hub Guard` in `.github/workflows/docs-hub-guard.yml`
- Closeout- und Provenienz-Doku ist nicht das Problem, sondern Beleg:
  - `docs/meta/DOCS_HUB_RETIREMENT_HANDOFF.md`
  - `docs/meta/DOCS_HUB_REMOTE_RETIREMENT_STATUS.md`
  - `docs/meta/DOCS_HUB_DELETE_READINESS.md`
  - `docs/meta/DOCS_HUB_MIGRATION_MATRIX.md`
  - `docs/meta/DOCS_HUB_POST_DELETE_STATUS.md`

## Minimaler Zielzustand fuer #1145

- Aktive user-facing Docs lesen "Docs Hub" nicht mehr als aktuelle kanonische Zieladresse oder Pflicht-Change-Ort.
- Pointer- und Shim-Dateinamen duerfen bleiben, aber ihre Texte muessen eindeutig auf lokalen Canon plus lokales Archiv verweisen.
- Behavior-bearing Kompatibilitaetsinterfaces bleiben unveraendert:
  - keine Aenderung an `DOCS_HUB_PATH`
  - keine Aenderung an `--docs-hub`
  - keine Aenderung an Fallback-Logik
  - keine Aenderung an `Docs Hub Guard`
- Nach `#1145` bleiben in aktiven Flaechen nur noch absichtliche historische/archivische Nennungen oder bewusst unberuehrte behavior-bearing Kompatibilitaetsnamen uebrig.

## Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `DOCS_MOVED_TO_DOCS_HUB.md`
  - `mcp_navpack_working_repo/DOCS_HUB.pointer.md`
  - `mcp_navpack_working_repo/DOCS_HUB.pointer.json`
  - `docs/governance/no_human_review_policy.md`
  - `docs/live-readiness/LR-007-STATUS.md`
- Optional fuer kleinen Textabgleich, aber nicht primaer:
  - `docs/meta/WORKING_REPO_CANON.md`
  - `mcp_navpack_working_repo/REPO.map.json` nur wenn diese Navpack-Metadaten im Repo bewusst manuell gepflegt werden
- Fuer `#1145` standardmaessig nicht anfassen:
  - `docs/archive/docs_hub_snapshot/**`
  - `docs/meta/DOCS_HUB_RETIREMENT_HANDOFF.md`
  - `docs/meta/DOCS_HUB_REMOTE_RETIREMENT_STATUS.md`
  - `docs/meta/DOCS_HUB_DELETE_READINESS.md`
  - `docs/meta/DOCS_HUB_MIGRATION_MATRIX.md`
  - `docs/meta/DOCS_HUB_POST_DELETE_STATUS.md`
  - `AGENTS.md`
  - `agents/AGENTS.md`
  - `knowledge/CDB_KNOWLEDGE_HUB.md`
  - `knowledge/SYSTEM.CONTEXT.md`
  - `knowledge/governance/CONSTITUTION.md`
  - `knowledge/governance/REPOSITORY_POLICY.md`
  - `knowledge/governance/CONTRIBUTION_RULES.md`
  - `knowledge/roadmap/GOVERNANCE_AUDIT_ROADMAP.md`
  - `knowledge/roadmap/PLAN_AGENT_DOCS_ORCHESTRATION.md`
  - `infrastructure/scripts/docs_hub_rag_adapter.py`
  - `infrastructure/scripts/discussion_pipeline/utils/config_loader.py`
  - `infrastructure/scripts/discussion_pipeline/run_discussion.py`
  - `infrastructure/scripts/discussion_pipeline/create_github_issue.py`
  - `.github/workflows/docs-hub-guard.yml`

## Risiken / Annahmen / offene Punkte

- `DOCS_MOVED_TO_DOCS_HUB.md` ist als Dateiname selbst ein Kompatibilitaetshim. Nicht umbenennen oder loeschen, solange `docs/meta/WORKING_REPO_CANON.md` und der Navpack ihn noch als Pointer fuehren.
- `mcp_navpack_working_repo/DOCS_HUB.pointer.md` wird aktiv von Baseline-/Guard-Flaechen erwartet. Nur wording straffen, nicht Dateiname oder Rolle veraendern.
- `docs/live-readiness/LR-007-STATUS.md` ist nur an der Docs-Hub-Stelle zu korrigieren. Kein verstecktes Reopen von `#1139`, kein Runtime-/Soak-Rewrite.
- Falls `mcp_navpack_working_repo/REPO.map.json` generiert statt manuell gepflegt ist, dort nichts per Hand "sauberziehen".
- Die behavior-bearing Shims `DOCS_HUB_PATH` und `--docs-hub` haben aktive Doku-/Code-/Test-Kopplung. Ihre Zukunft ist eine getrennte Cleanup-Entscheidung, nicht dieses Delta.

## Klare Nicht-Ziele

- Kein Archive-Retention- oder Pruning-Redesign fuer `docs_hub_snapshot` (`#1146` bleibt getrennt).
- Kein Runtime-, Compose-, LR-, Operator- oder CI-Subprojekt.
- Kein verstecktes Fortsetzen von `#1139` oder `#1142`.
- Kein Entfernen oder Umbenennen von behavior-bearing Kompatibilitaetsnamen wie `DOCS_HUB_PATH`, `--docs-hub` oder `Docs Hub Guard`.
- Kein Rewrite der Closeout-/Migrationsevidenz unter `docs/meta/`.
- Keine breite README-/Knowledge-/Status-Reorganisation nur wegen historischer Restdateien.

## Claude-Code-Handoff

### Ziel

Die wenigen verbleibenden aktiven Docs-Hub-Wording-Stellen so straffen, dass sie nur noch lokalen Canon plus lokales Archiv ausdruecken, ohne behavior-bearing Kompatibilitaetsinterfaces anzufassen.

### Betroffene Dateien

- `DOCS_MOVED_TO_DOCS_HUB.md`
- `mcp_navpack_working_repo/DOCS_HUB.pointer.md`
- `mcp_navpack_working_repo/DOCS_HUB.pointer.json`
- `docs/governance/no_human_review_policy.md`
- `docs/live-readiness/LR-007-STATUS.md`
- optional text-only: `docs/meta/WORKING_REPO_CANON.md`
- optional metadata sync only: `mcp_navpack_working_repo/REPO.map.json`

### Minimale Aenderungen

- `DOCS_MOVED_TO_DOCS_HUB.md`
  - Dateinamen behalten.
  - Heading/Body so umformulieren, dass die Datei erkennbar nur ein Legacy-Dateiname mit lokalem Redirect ist.
  - Kein Text, der "Docs Hub" wie ein aktuelles Ziel oder eine aktive Heimat klingen laesst.
- `mcp_navpack_working_repo/DOCS_HUB.pointer.md` und `.json`
  - Namen/Keys behalten.
  - Nur noch als lokaler Archivpointer formulieren.
  - Keine Formulierungen mehr, die "orphaned docs recovery", aktive Pruning-Arbeit oder eine zweite Docs-Heimat implizieren.
- `docs/governance/no_human_review_policy.md`
  - "link to DocsHub change" auf lokalen Canon/Governance-Change umstellen.
  - Rest der Policy unveraendert lassen.
- `docs/live-readiness/LR-007-STATUS.md`
  - Die PR-#814-Passage von DocsHub-Canon/DocsHub-Commit auf die heutige lokale Governance-Realitaet ziehen oder klar historisieren.
  - Sonst nichts an LR-007 neu designen.
- `docs/meta/WORKING_REPO_CANON.md`
  - Nur wenn fuer Konsistenz noetig den Archiv-Use-Satz straffen.
  - Die Datei bleibt die kanonische Redirect-/Archiv-Policy.
- `mcp_navpack_working_repo/REPO.map.json`
  - Nur anfassen, wenn die Repo-Konvention dort manuelle Beschreibungssynchronisierung erwartet.

### Validierung

- `rg -n "DocsHub canonical|DocsHub change|Docs Hub" DOCS_MOVED_TO_DOCS_HUB.md docs/governance/no_human_review_policy.md docs/live-readiness/LR-007-STATUS.md mcp_navpack_working_repo/DOCS_HUB.pointer.md`
  - Verbleibende Treffer in angefassten Dateien duerfen nur noch historisch oder archive-only lesbar sein.
- `rg -n "DOCS_HUB_PATH|--docs-hub|Docs Hub Guard|docs-hub-guard" infrastructure/scripts infrastructure/docs .github/workflows`
  - Muss als Guardrail unveraendert bleiben; `#1145` aendert diese behavior-bearing Flaechen nicht.
- `rg -n "docs/archive/docs_hub_snapshot|local archive|read-only archive|working repo" DOCS_MOVED_TO_DOCS_HUB.md docs/meta/WORKING_REPO_CANON.md mcp_navpack_working_repo/DOCS_HUB.pointer.md mcp_navpack_working_repo/DOCS_HUB.pointer.json`
  - Archiv- und Canon-Sprache sollte nach dem Delta konsistent sein.
- Falls `.json` geaendert wird:
  - JSON parsebar halten.

### Rollback / Sicherheitsgrenzen

- Rollback bleibt auf kleine Text-/JSON-Aenderungen beschraenkt.
- Keine Dateiumbenennungen, keine neuen Pointer-Dateien, kein Entfernen alter Dateinamen.
- Keine Code-, Script-, Env-, CLI- oder Workflow-Verhaltensaenderung.
- Wenn eine geplante Aenderung Tests, Branch-Protection-Checks oder Fallback-Logik beruehrt, STOP und als Folgeentscheidung ausserhalb von `#1145` ausweisen.
