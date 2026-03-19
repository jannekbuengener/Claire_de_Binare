# Issue #1142 Handoff - Legacy Compose Phase 1 Guardrails

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- Der Repo-Canon ist klar und bereits mehrfach verankert:
  - `CURRENT_STATUS.md` setzt `BLUE+RED` als aktive Runtime und `base.yml + dev.yml` als CI-only Legacy-Pfad.
  - `infrastructure/compose/COMPOSE_LAYERS.md` markiert `base.yml`, `dev.yml`, `prod.yml` als deprecated und `stack_up.ps1` / `stack_down.ps1` als fail-fast Legacy-Helfer.
  - `infrastructure/compose/README.md` und `README.md` zeigen fuer den normalen Betrieb bereits auf `compose.blue.yml` + `compose.red.yml`.
- Harte Guards existieren schon an den offensichtlichen Legacy-Entrypoints:
  - `infrastructure/scripts/stack_up.ps1` blockiert ohne `CDB_LEGACY_COMPOSE_OK=1`.
  - `infrastructure/scripts/stack_down.ps1` blockiert ohne `CDB_LEGACY_COMPOSE_OK=1`.
  - `Makefile` blockiert `docker-up-prod` bereits hart.
- Bewusste CI-only Legacy-Compose-Consumer sind im nicht-archivierten Repo weiterhin vorhanden:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/shadow-soak-evidence.yml`
  - `.github/workflows/e2e-tests.yml`
- Keine aktive Workflow-Stelle verwendet `stack_up.ps1`, `stack_down.ps1` oder `CDB_LEGACY_COMPOSE_OK`; das Legacy-Skript-Bypass-Thema ist damit kein CI-Pflichtpfad.
- Die eigentlichen accidental-runtime-Risiken liegen in lokalen Helfern und Folgehinweisen:
  - `infrastructure/scripts/bootstrap_local.ps1` delegiert trotz Canon direkt an `stack_up.ps1`.
  - `infrastructure/scripts/validate-environment.sh` validiert `dev.yml` als Compose-Einstieg und empfiehlt direkt `docker compose -f infrastructure/compose/dev.yml up -d`.
  - `infrastructure/scripts/run_e2e.ps1` startet lokal weiterhin ueber `stack_up.ps1` und nutzt fuer Tear-down die nicht vorhandene `infrastructure/compose/monitoring.yml`.
  - `tools/secrets/Rotate-Secrets.ps1` und `tools/secrets/README.md` schicken den Nutzer nach `apply` / `export` weiter auf `stack_up.ps1`.
- Guard-/Migrationslage ist inkonsistent:
  - `bootstrap_local.sh` ist bereits auf BLUE+RED umgestellt, `bootstrap_local.ps1` aber nicht.
  - `stack_down.ps1` ist zwar guardiert, der Legacy-Bypass referenziert intern aber weiterhin `docker-compose.base.yml`, das laut Canon entfernt ist.
  - `prod.yml` hat im aktiven Repo keinen belastbaren Consumer-Fund; es ist eher Restbestand als aktiver Pfad.

## Minimaler Zielzustand fuer #1142 Phase 1

- Normale lokale Operator-/Developer-Einstiege fuehren nicht mehr direkt oder indirekt auf Legacy-Compose-Runtime.
- Bestehende CI-Workflows mit `base.yml` / `dev.yml` bleiben unveraendert funktionsfaehig.
- Legacy-Skripte bleiben als deprecated/fail-fast Restpfade erkennbar; Phase 1 macht sie nicht wieder "benutzbar".
- Nach Secret-Rotation, Bootstrap oder lokaler Environment-Validierung wird nur noch auf den kanonischen BLUE+RED-Startpfad verwiesen.
- `run_e2e.ps1` bekommt keinen versteckten Legacy-Stack-Lifecycle mehr. Wenn dort ein minimaler Fix noetig ist, dann guard-first und nicht als neuer halbkanonischer Runtime-Manager.

## Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `infrastructure/scripts/bootstrap_local.ps1`
  - `infrastructure/scripts/validate-environment.sh`
  - `infrastructure/scripts/run_e2e.ps1`
  - `tools/secrets/Rotate-Secrets.ps1`
  - `tools/secrets/README.md`
- Optional fuer kleine Konsistenztexte, aber nicht primaer:
  - `docs/env/index.md`
  - `infrastructure/compose/COMPOSE_LAYERS.md`
- Fuer #1142 Phase 1 standardmaessig nicht anfassen:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/shadow-soak-evidence.yml`
  - `.github/workflows/e2e-tests.yml`
  - `infrastructure/compose/base.yml`
  - `infrastructure/compose/dev.yml`
  - `infrastructure/compose/prod.yml`
  - `infrastructure/scripts/stack_up.ps1`
  - `infrastructure/scripts/stack_down.ps1`
  - `infrastructure/scripts/dr_backup.ps1`
  - `infrastructure/scripts/dr_restore.ps1`
  - `infrastructure/scripts/dr_drill.ps1`
  - `infrastructure/scripts/stack_rollback.ps1`
  - `infrastructure/scripts/stack_clean.ps1`
  - `infrastructure/scripts/activate_live_data.ps1`
  - `tools/stack_boot.ps1`

## Risiken / Annahmen / offene Punkte

- Die CI-only Nutzung von `base.yml` / `dev.yml` ist real und darf in Phase 1 nicht collateral damage werden; die drei genannten Workflows sind dafuer die belastbaren Consumer.
- `run_e2e.ps1` ist fachlich nah an `#149`. Fuer `#1142` sollte dort nur accidental legacy runtime use unterbunden werden, nicht der gesamte offizielle E2E-Pfad neu designt werden.
- Mehrere DR-/Rollback-/Live-Helfer tragen weiterhin legacy/root-compose Annahmen in sich. Das ist repo-seitig unsauber, aber kein Grund, `#1142` in einen DR- oder Live-Ops-Rewrite zu drehen.
- `stack_down.ps1` ist intern bereits stale, obwohl der Guard vorne korrekt ist. Phase 1 muss diesen Legacy-Bypass nicht reparieren; wichtig ist nur, ihn nicht wieder als normalen Weg aufzuwerten.
- `prod.yml` ist ein Kandidat fuer spaetere Entfernung, aber nicht fuer Phase 1 auf Basis reiner Annahme.
- Falls nach den kleinen Guardrail-Aenderungen noch breite Doku-Drift sichtbar bleibt, ist das hoechstens ein klar benannter Folgeeffekt fuer spaetere Doku-Konsolidierung, nicht Teil dieses Deltas.

## Klare Nicht-Ziele

- Kein Reopen oder Reconciliation-Track fuer `#1138`; BLACK bleibt repo-seitig erledigt.
- Kein Nachziehen von `#1139` als verdecktes Runtime-/Doku-Unterprojekt.
- Kein Umbau der CI-Topologie, kein Wechsel der Legacy-Compose-Workflows auf BLUE+RED und kein Workflow-Consolidation-Projekt.
- Kein Entfernen von `base.yml`, `dev.yml` oder `prod.yml` in Phase 1.
- Kein DR-, Rollback-, Live-Data- oder Root-Compose-Modernisierungsprojekt.
- Keine Gesamt-Doku-Revision ueber README, Quick Start, Runbooks, Live-Readiness und Test-Harness gleichzeitig.
- Kein Vermischen mit `#659`, `#661`, `#785` oder groesseren Runtime-Rewrites.

## Claude-Code-Handoff

### Ziel

Die verbleibenden lokalen Helfer und Benutzerhinweise so haerten, dass versehentliche Runtime-Nutzung von Legacy Compose weiter unterbunden wird, waehrend die absichtliche CI-only Nutzung von `base.yml` / `dev.yml` unveraendert bleibt.

### Betroffene Dateien

- `infrastructure/scripts/bootstrap_local.ps1`
- `infrastructure/scripts/validate-environment.sh`
- `infrastructure/scripts/run_e2e.ps1`
- `tools/secrets/Rotate-Secrets.ps1`
- `tools/secrets/README.md`
- optional text-only: `docs/env/index.md`
- optional text-only: `infrastructure/compose/COMPOSE_LAYERS.md`

### Minimale Aenderungen

- `bootstrap_local.ps1` nicht mehr an `stack_up.ps1` delegieren.
  - Entweder direkt auf `setup_blue_red.ps1` umstellen oder hart abbrechen und auf den kanonischen BLUE+RED-Startpfad verweisen.
  - Keine neue Legacy-Ausnahme einfuehren.
- `validate-environment.sh` auf den heutigen Runtime-Canon ziehen.
  - Nicht mehr `dev.yml` als den zu startenden Compose-Pfad validieren oder empfehlen.
  - Erfolgsausgabe und Hilfetext muessen auf BLUE+RED bzw. den kanonischen Startpfad zeigen.
- `run_e2e.ps1` nur guard-first minimal anfassen.
  - Keinen unguarded Start ueber `stack_up.ps1`.
  - Keine Tear-down-Kommandos ueber die nicht existente `monitoring.yml`.
  - Keine groessere Harness-Neudefinition; wenn noetig, Lifecycle-Management hart deaktivieren und den Nutzer auf einen bereits laufenden kanonischen Stack verweisen.
- `Rotate-Secrets.ps1` und `tools/secrets/README.md` bei den "next step"-Hinweisen auf BLUE+RED umstellen.
  - `.env.runtime`-Erzeugung bleibt unberuehrt.
  - Keine Secret-Logik oder Manifest-Semantik aendern.
- Nur wenn fuer Repo-Klarheit noetig:
  - `docs/env/index.md` so anpassen, dass `SECRETS_PATH` nicht mehr primaer auf `stack_up.ps1` zeigt.
  - `COMPOSE_LAYERS.md` knapp praezisieren, dass die Legacy-CI-Consumer `e2e.yml`, `shadow-soak-evidence.yml` und `e2e-tests.yml` sind.

### Validierung

- `rg -n "stack_up\\.ps1|monitoring\\.yml" infrastructure/scripts/run_e2e.ps1 infrastructure/scripts/bootstrap_local.ps1 tools/secrets/Rotate-Secrets.ps1 tools/secrets/README.md docs/env/index.md`
  - darf in den angefassten Normalpfaden keinen neuen aktiven Runtime-Hinweis auf Legacy Compose mehr zeigen.
- `rg -n "infrastructure/compose/dev\\.yml up -d|compose/dev\\.yml up -d" infrastructure/scripts/validate-environment.sh`
  - darf keinen normalen Startpfad ueber `dev.yml` mehr ausgeben.
- `rg -n "base\\.yml|dev\\.yml" .github/workflows/e2e.yml .github/workflows/shadow-soak-evidence.yml .github/workflows/e2e-tests.yml`
  - muss die bewussten CI-only Consumer weiterhin zeigen.
- Syntax-/Smoke-Validierung nur fuer die angefassten Helfer:
  - PowerShell-Skripte parsebar halten.
  - `validate-environment.sh` per Shell-Syntaxcheck pruefen.
- Keine Docker-/Compose-Verhaltensaenderung in CI als Teil dieser Phase pruefen oder umbauen.

### Rollback / Sicherheitsgrenzen

- Rollback bleibt auf kleine Script-/Textaenderungen begrenzt.
- Keine Aenderung an den CI-Workflows, solange nicht ein klarer CI-Bruch nachweisbar ist.
- Keine Aenderung an `compose.blue.yml`, `compose.red.yml`, `base.yml`, `dev.yml`, `prod.yml`.
- Keine Reparatur alter Legacy-Bypass-Pfade nur "der Vollstaendigkeit halber".
- Wenn sich fuer `run_e2e.ps1` ein sauberer Fix nur ueber groessere Harness- oder Workflow-Entscheidungen herstellen laesst, STOP und als out-of-scope nach `#149` verschieben.
