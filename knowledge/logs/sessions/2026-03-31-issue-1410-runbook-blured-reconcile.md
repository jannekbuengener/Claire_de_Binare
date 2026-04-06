# Session Log — Issue #1410: Runbook BLUE/RED Reconcile

**Datum:** 2026-03-31
**Commits:** `0266dbd` (Hauptpatch), `d034ecc7` (Follow-up Resttreffer)
**Branch:** main

## Ziel

Aktive Operator-Docs von Legacy-Stack-Topologie (`stack_up.ps1`, `base.yml + dev.yml`, `-Profile dev`, `-Logging`-Flag) auf kanonischen BLUE/RED-Pfad bereinigen.

## Geänderte Dateien (19)

- `knowledge/playbooks/02_STACK_GOLDEN_PATH_WINDOWS.md` — vollständig auf BLUE+RED umgestellt, Stop-Reihenfolge RED→BLUE
- `knowledge/runbooks/02_STACK_GOLDEN_PATH_WINDOWS.md` — identisch wie Playbook-Variante
- `knowledge/playbooks/01_CANONICAL_GOLDEN_STATE.md` — Stack-Start auf BLUE+RED
- `knowledge/playbooks/03_DB_SCHEMA_INIT_AND_MIGRATIONS.md` — DB Reset auf RED down → BLUE down → volume rm → BLUE up → RED up
- `knowledge/playbooks/09_BRANCHING_RELEASE_ROLLBACK.md` — Rollback Stack-Restart auf BLUE+RED
- `knowledge/runbooks/03_DB_SCHEMA_INIT_AND_MIGRATIONS.md` — wie Playbook-Variante
- `knowledge/templates/PR_TEMPLATE.md` — Rollback-Block auf BLUE+RED
- `knowledge/OPERATIONS_RUNBOOK.md` — dev.yml-Hinweis entfernt, Logs-Legacy-Alternative entfernt, Service Rebuild kanonisch ergänzt, vollständiger Reset bereinigt
- `knowledge/operations/DOCKER_STACK_RUNBOOK.md` — breite Sanierung: alle `stack_up.ps1` und `docker-compose` Restart-Kommandos in aktiven Troubleshooting-Sections auf BLUE+RED; CI Workflow Steps als "(CI-intern)" annotiert
- `knowledge/operations/ALERTING_RUNBOOK.md` — Prerequisite von `stack_up.ps1 -Profile dev -Logging` auf BLUE+RED
- `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` — Legacy-Fallback-Kommentare und Legacy-Restart-Block entfernt
- `knowledge/operating_rules/ci_cd/CI_PIPELINE_GUIDE.md` — E2E Local Stack auf BLUE+RED
- `knowledge/operating_rules/ci_cd/TROUBLESHOOTING.md` — Local Stack Start auf BLUE+RED
- `infrastructure/compose/COMPOSE_LAYERS.md` — Feature Overlay "Enable with: stack_up.ps1 -Flag" durch direkte compose-Befehle ersetzt; "stack_up.ps1 Logging"-Section entfernt; Production-Section auf direkte Overlays; File Hierarchy stack_up.ps1 als Legacy markiert; Overlay Dev Guidelines stack_up.ps1 entfernt; Migration Path auf "abgeschlossen" gekürzt; Troubleshooting Hint auf BLUE+RED; "See Also: stack_up.ps1" entfernt
- `infrastructure/compose/logging.yml` — Header Usage-Kommentar auf direkten compose-Befehl
- `infrastructure/compose/tls.yml` — Header Usage-Kommentar auf direkten compose-Befehl
- `infrastructure/tls/TLS_SETUP.md` — stack_up.ps1 -TLS durch direkte compose + tls.yml Overlay-Kommandos ersetzt
- `infrastructure/scripts/bootstrap_local.sh` — base.yml+dev.yml auf BLUE+RED; Health-Loop und Status-Ausgabe ebenfalls auf BLUE+RED
- `README.md` — kommentierte base.yml+dev.yml Alternative direkt neben dem Start-Block entfernt

## Follow-up Resttreffer (Commit `d034ecc7`)

- `knowledge/OPERATIONS_RUNBOOK.md` Z.31–45 — gesamter "Legacy, CI/test only"-Block mit 4× `stack_up.ps1 -Profile dev` entfernt
- `knowledge/operations/ALERTING_RUNBOOK.md` Z.216 — `stack_up.ps1 -Profile dev -Logging` in Quick Commands → BLUE+RED
- `knowledge/operations/DOCKER_STACK_RUNBOOK.md` Z.332/334 — `docker-compose -f base.yml -f dev.yml` in DB-Section → BLUE+RED
- `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` Z.153–155 — kommentierter `base.yml + dev.yml`-Rollback-Fallback entfernt
- `knowledge/runbooks/01_CANONICAL_GOLDEN_STATE.md` Z.4–6 — `base.yml + dev.yml` → BLUE+RED

## Bewusst nicht angefasst

- `tools/test_pack/integrations/cdb-stack-adapter.ps1` → Test-Infrastruktur, gehört zu **#1411**
- `infrastructure/scripts/stack_clean.ps1` → Ops-Script-Cleanup, gehört zu **#1413**
- Archive / reviews / staging / context_build — explizit ausgeschlossen
- Secrets-Pfade (`.cdb_local/.secrets/` vs. tatsächlichem Pfad) — kein Secrets-Scope
- `knowledge/testing/TEST_HARNESS_V1.md` — `base.yml+dev.yml` bereits klar als "CI/Test-Compat" markiert, BLUE+RED als Runtime-Canon dokumentiert → kein Änderungsbedarf
- `infrastructure/compose/TEST_OVERLAY_README.md` — beschreibt 431B CI-Lab-Baseline korrekt → kein Änderungsbedarf
- `infrastructure/compose/network-prod.yml`, `healthchecks-strict.yml`, `healthchecks-mounts.yml` — Overlay-Headers ohne aktiven Operator-Workflow → kein Änderungsbedarf
