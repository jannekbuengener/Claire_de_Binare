# Issue #1139 Handoff - Runtime/Soak Docs Post-Migration Rewrite

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- Der operative Canon ist bereits klar und braucht keinen Runtime-Umbau:
  - `CURRENT_STATUS.md` setzt `BLUE+RED` als aktive Runtime, `base.yml + dev.yml` als deprecated/CI-only Legacy-Pfad und `BLACK` nur als historischen Begriff.
  - `docs/meta/WORKING_REPO_CANON.md`, `infrastructure/compose/README.md`, `infrastructure/compose/COMPOSE_LAYERS.md`, `docs/operations/SOAK_MONITOR_RUNBOOK.md` und `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` tragen dieses Bild konsistent.
- Der Drift sitzt in wenigen, aber operator-relevanten Dokumenten:
  - `README.md` startet korrekt mit `BLUE+RED` und `NO-GO`, fuehrt spaeter aber unvereinbare Aussagen wie `Live Readiness: erreicht`, `Systemstatus: stabil & einsetzbar` und `CI/CD: Gruen mit Concurrency` wieder ein.
  - `knowledge/CURRENT_STATUS.md` mischt aktuelle `BLUE+RED`-Rahmung mit alten Runtime-/Statusresten, inklusive `infrastructure/compose/dev.yml` als aktive Config und ueberholter Service-/Health-Aussagen.
  - `knowledge/systems/STACK_LIFECYCLE.md` nennt sich selbst `Single source of truth`, setzt aber `base.yml` als `ALWAYS required` und `dev.yml` als `DEFAULT`.
  - `knowledge/OPERATIONS_RUNBOOK.md` ist als `Kanonisch` markiert, nutzt aber `stack_up.ps1 -Profile dev` und `base.yml + dev.yml` als normalen Operatorpfad.
  - `knowledge/LIVE_TRADING_RUNBOOK.md` behandelt `dev.yml` als Live-Schaltdatei und deployed/rollt `cdb_execution` ueber `base.yml + dev.yml`.
  - `PROJECT_STATUS.md` beschreibt das Runtime-Modell weiter ueber `dev.yml/test.yml/prod.yml` und alte Compose-Pfade.
  - `knowledge/content/ONBOARDING_QUICK_START.md` und `knowledge/content/ONBOARDING_LINKS.md` schicken neue Nutzer weiterhin in `base.yml + dev.yml` und nennen diese Pfade implizit als Dokumentationszentrum.
  - `docs/env/index.md` zeigt bei `SECRETS_PATH` noch auf `stack_up.ps1`.
  - `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md` schickt den Nutzer noch auf `base.yml + dev.yml` und nennt `.env` als Passwortquelle fuer Grafana.
  - `infrastructure/compose/soak.yml` dokumentiert im Header weiter den Legacy-Start `base.yml + dev.yml + soak.yml`.
- Die kanonischen Runtime-/Soak-Dokumente sind inhaltlich weitgehend richtig, aber nicht immer copy/paste-sicher:
  - `infrastructure/docs/QUICK_START.md`, `infrastructure/docs/BLUE_RED_SPLIT.md` und `docs/operations/72H_SOAK_TEST_RUNBOOK.md` mischen Repo-Root-Pfade mit Snippets nach `cd infrastructure/compose`.
- Manual Soak und CI-only Shadow/Soak lassen sich im Repo bereits sauber trennen, aber diese Trennung muss explizit bleiben:
  - manueller 72h-Soak = `BLUE` Runtime-Core plus `RED` Observability accompaniment.
  - `.github/workflows/shadow-soak-evidence.yml` = CI-only Sonderpfad, der weiterhin Legacy-Compose-Fragmente nutzt.

## Minimaler Zielzustand fuer #1139

- Alle operator-facing Runtime- und Soak-Dokumente sagen dasselbe:
  - `BLUE+RED` ist der normale Runtime-Default.
  - `setup_blue_red.ps1` oder explizit `compose.blue.yml` + `compose.red.yml` sind der Standard-Startpfad.
- Dokumente, die sich selbst als Canon, `single source of truth` oder Onboarding-Default ausgeben, duerfen keinen Legacy-Compose-Default mehr behaupten.
- `base.yml + dev.yml` tauchen nur noch als CI/Test/Sonderfall-Legacy auf, nicht als normaler Operator-Start.
- Manueller 72h-Soak ist als Soak-spezifischer Gate-Fall dokumentiert, nicht als versteckter Alias fuer Legacy Compose.
- `BLACK` bleibt nur dort stehen, wo es explizit als Governance-/Risk-Label eingerahmt ist, nicht als Runtime-Topologie.
- `README.md` und Statusseiten widersprechen weder `NO-GO` noch der post-migration Runtime-Realitaet.

## Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `README.md`
  - `knowledge/CURRENT_STATUS.md`
  - `knowledge/systems/STACK_LIFECYCLE.md`
  - `knowledge/OPERATIONS_RUNBOOK.md`
  - `knowledge/LIVE_TRADING_RUNBOOK.md`
  - `PROJECT_STATUS.md`
  - `knowledge/content/ONBOARDING_QUICK_START.md`
  - `knowledge/content/ONBOARDING_LINKS.md`
  - `docs/env/index.md`
  - `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md`
  - `infrastructure/compose/soak.yml`
  - `infrastructure/docs/QUICK_START.md`
  - `infrastructure/docs/BLUE_RED_SPLIT.md`
  - `docs/operations/72H_SOAK_TEST_RUNBOOK.md`
- Optional fuer einen kleinen Text-Anker, aber nicht primaer:
  - `infrastructure/compose/COMPOSE_LAYERS.md`
- Fuer #1139 standardmaessig nicht anfassen:
  - `CURRENT_STATUS.md`
  - `docs/meta/WORKING_REPO_CANON.md`
  - `infrastructure/compose/README.md`
  - `docs/operations/SOAK_MONITOR_RUNBOOK.md`
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  - `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`
  - `.github/workflows/shadow-soak-evidence.yml`
  - `.github/workflows/e2e.yml`
  - `.github/workflows/e2e-tests.yml`
  - `infrastructure/compose/base.yml`
  - `infrastructure/compose/dev.yml`
  - `infrastructure/compose/prod.yml`

## Risiken / Annahmen / offene Punkte

- `knowledge/CURRENT_STATUS.md` kann schnell zu einer Vollsanierung eskalieren. Fuer `#1139` ist ein harter Redirect-/Bereinigungs-Schnitt genug; keine komplette historische Neuerzaehlung.
- `README.md` enthaelt viel weitere Alt-Status-Masse. Fuer `#1139` nur die Runtime-/Soak-/Readiness-Widersprueche entfernen oder klar historisieren, nicht die komplette Projektchronik aktualisieren.
- Die `knowledge/`-Dokumente mit `Kanonisch`-/`Single source of truth`-Anspruch sind der eigentliche High-Risk-Drift. Wenn sie nicht sauber auf `BLUE+RED` gezogen werden koennen, muss mindestens ihr Canon-/Default-Anspruch entfernt und auf die echten Canon-Dateien umgebogen werden.
- `soak.yml` ist als Overlay real, aber die manuelle 72h-Soak-Doku nutzt es derzeit nicht. Wenn es keine belastbare Repo-Evidenz fuer einen kanonischen manuellen `soak.yml`-Start gibt, nichts neu erfinden; nur den Legacy-Header entschraerfen.
- `QUICK_START.md`, `BLUE_RED_SPLIT.md` und `72H_SOAK_TEST_RUNBOOK.md` brauchen Pfadkonsistenz, keinen Architektur- oder Ablauf-Rewrite.
- Weitere Drift-Stellen existieren in Spezialdoku wie `knowledge/operations/DOCKER_STACK_RUNBOOK.md`, `knowledge/operations/MONTHLY_MAINTENANCE.md`, Alerting-, TLS-, DR- oder Test-Harness-Unterlagen. Das ist real, gehoert aber nicht in den Minimal-Scope von `#1139`, solange die selbsternannten Canon-/Onboarding-Dokumente zuerst bereinigt werden.
- `BLACK` darf in Governance-Dokumenten als klar markiertes Risk-Label weiter vorkommen. `#1139` ist kein Reopen von `#1138`.

## Klare Nicht-Ziele

- Kein technischer Runtime-Umbau.
- Keine CI-Neuverkabelung und kein Wechsel der Legacy-CI-Workflows auf `BLUE+RED`.
- Keine versteckte Fortsetzung von `#1142`.
- Kein Wiederaufrollen von `#1138`.
- Keine globale Bereinigung aller Spezial- und Alt-Dokumente jenseits der zentralen Canon-/Status-/Onboarding-Flaechen.
- Kein Rewrite von `CURRENT_STATUS.md`, `compose.blue.yml`, `compose.red.yml`, `base.yml`, `dev.yml` oder `prod.yml`.
- Kein generelles README- oder Knowledge-History-Refresh ueber den Runtime-/Soak-Kontext hinaus.

## Claude-Code-Handoff

### Ziel

Die operator-facing Runtime-/Soak-Doku so konsolidieren, dass sie den heutigen Post-Migration-Stand ohne Widerspruch abbildet: `BLUE+RED` als Runtime-Default, manuelle Soak-Faelle klar vom CI-only Legacy-Pfad getrennt, keine alten Compose-Default-Hinweise mehr in zentralen Einstiegsdokumenten.

### Betroffene Dateien

- `README.md`
- `knowledge/CURRENT_STATUS.md`
- `knowledge/systems/STACK_LIFECYCLE.md`
- `knowledge/OPERATIONS_RUNBOOK.md`
- `knowledge/LIVE_TRADING_RUNBOOK.md`
- `PROJECT_STATUS.md`
- `knowledge/content/ONBOARDING_QUICK_START.md`
- `knowledge/content/ONBOARDING_LINKS.md`
- `docs/env/index.md`
- `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md`
- `infrastructure/compose/soak.yml`
- `infrastructure/docs/QUICK_START.md`
- `infrastructure/docs/BLUE_RED_SPLIT.md`
- `docs/operations/72H_SOAK_TEST_RUNBOOK.md`
- optional text-only: `infrastructure/compose/COMPOSE_LAYERS.md`

### Minimale Aenderungen

- `README.md`
  - Den korrekten Opening-Block behalten.
  - Die spaeteren Widersprueche zu `NO-GO` und Post-Migration-Realitaet entfernen, umschreiben oder klar historisieren.
  - Keine Vollaktualisierung aller Projektmetriken.
- `knowledge/CURRENT_STATUS.md`
  - Nicht komplett neu schreiben.
  - Die Datei klar von der operativen SSOT trennen und die expliziten Runtime-Default-/Status-Widersprueche entschraerfen, insbesondere `dev.yml` als aktive Config und ueberholte OPERATIONAL-/Service-Inventar-Aussagen.
- `knowledge/systems/STACK_LIFECYCLE.md`
  - Den `Single source of truth`-/`DEFAULT`-Anspruch nicht mit Legacy Compose stehen lassen.
  - Entweder sauber auf `BLUE+RED` umstellen oder den SSOT-/Default-Anspruch entfernen und auf `COMPOSE_LAYERS.md` / `QUICK_START.md` redirecten.
- `knowledge/OPERATIONS_RUNBOOK.md`
  - `stack_up.ps1 -Profile dev` und `base.yml + dev.yml` nicht mehr als kanonischen Operatorpfad fuehren.
  - Entweder auf `BLUE+RED` umschreiben oder klar als historische/legacy Kompatibilitaetsnotiz markieren.
- `knowledge/LIVE_TRADING_RUNBOOK.md`
  - Kein Live-Switch oder Rollback ueber `dev.yml` als Normalmodell.
  - Die Datei darf `NOT READY FOR LIVE` bleiben, muss aber die aktuelle Runtime-/Readiness-Realitaet referenzieren statt alte Compose-Defaults.
- `PROJECT_STATUS.md`
  - Nicht als aktuelles Runtime-Modell ueber `dev.yml/test.yml/prod.yml` stehen lassen.
  - Entweder klar als historischer Service-Audit einrahmen oder die Runtime-Referenzen auf heutigen Stand ziehen.
- `knowledge/content/ONBOARDING_QUICK_START.md`
  - Neulinge nicht ueber `base.yml + dev.yml` in den Repo-Default schicken.
  - Auf `README.md`, `CURRENT_STATUS.md`, `COMPOSE_LAYERS.md` und `QUICK_START.md` als aktuelle Einstiegskette umbiegen.
- `knowledge/content/ONBOARDING_LINKS.md`
  - Keine Infrastructure-Sektion mehr mit `base.yml` / `dev.yml` als Compose-Zentrum.
  - Dokumentations-Hub auf die heutigen Canon-Pointer umstellen.
- `docs/env/index.md`
  - `SECRETS_PATH` nicht mehr primaer auf `stack_up.ps1` zeigen lassen.
  - Auf den kanonischen BLUE+RED-/Secret-Init-Pfad umbiegen.
- `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md`
  - Kein normaler Start ueber `base.yml + dev.yml`.
  - Keine `.env`-Zentrierung fuer das Grafana-Passwort, wenn die aktuelle Secret-Realitaet ausserhalb von Git liegt.
  - Falls Legacy erwaehnt wird, dann nur als CI/debug/special-case.
- `infrastructure/compose/soak.yml`
  - Kommentar-only.
  - Den Header nicht mehr als Legacy-Runtime-Default formulieren.
  - Wenn noetig als Overlay/Sonderfall beschreiben, ohne einen neuen manuellen Startpfad zu erfinden.
- `infrastructure/docs/QUICK_START.md`
  - Einen konsistenten cwd-Stil waehlen.
  - Keine Mischung aus `cd infrastructure/compose` und anschliessenden Repo-Root-Pfaden.
- `infrastructure/docs/BLUE_RED_SPLIT.md`
  - Recovery-/Migration-Snippets auf denselben cwd-Stil ziehen.
  - Legacy Compose nur noch als alter Pfad, nicht als implizite Gegenwartsanweisung.
- `docs/operations/72H_SOAK_TEST_RUNBOOK.md`
  - Pfade nach `cd infrastructure/compose` bereinigen oder das `cd` entfernen.
  - Das bestehende Framing `BLUE` core + `RED` observability beibehalten.
  - Nur wenn noetig einen kurzen Satz ergaenzen, dass der CI-Workflow `shadow-soak-evidence.yml` nicht der normale manuelle Runtime-/Soak-Startpfad ist.
- `infrastructure/compose/COMPOSE_LAYERS.md`
  - Nur wenn als Text-Anker hilfreich:
  - explizit nennen, dass `shadow-soak-evidence.yml`, `e2e.yml` und `e2e-tests.yml` die aktiven CI-only Legacy-Consumer sind.

### Validierung

- `rg -n "Live Readiness: .*erreicht|Systemstatus: stabil|CI/CD: Gruen|stack_up\\.ps1|infrastructure/compose/dev\\.yml|Single source of truth|Kanonisch|DEFAULT" README.md PROJECT_STATUS.md knowledge/CURRENT_STATUS.md knowledge/systems/STACK_LIFECYCLE.md knowledge/OPERATIONS_RUNBOOK.md knowledge/LIVE_TRADING_RUNBOOK.md knowledge/content/ONBOARDING_QUICK_START.md knowledge/content/ONBOARDING_LINKS.md docs/env/index.md infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md`
  - In den angefassten Operator-Dokumenten duerfen diese Signale nicht mehr als aktueller Default stehen.
- `rg -n "base\\.yml|dev\\.yml" README.md PROJECT_STATUS.md knowledge/CURRENT_STATUS.md knowledge/systems/STACK_LIFECYCLE.md knowledge/OPERATIONS_RUNBOOK.md knowledge/LIVE_TRADING_RUNBOOK.md knowledge/content/ONBOARDING_QUICK_START.md knowledge/content/ONBOARDING_LINKS.md docs/env/index.md infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md infrastructure/compose/soak.yml infrastructure/docs/QUICK_START.md infrastructure/docs/BLUE_RED_SPLIT.md docs/operations/72H_SOAK_TEST_RUNBOOK.md`
  - Verbleibende Treffer muessen klar als historisch oder CI-only markiert sein.
- `rg -n "cd infrastructure[/\\\\]compose|compose\\.blue\\.yml|compose\\.red\\.yml|smoke_test\\.ps1|soak_monitor\\.sh" infrastructure/docs/QUICK_START.md infrastructure/docs/BLUE_RED_SPLIT.md docs/operations/72H_SOAK_TEST_RUNBOOK.md`
  - Alle Kommandos muessen aus ihrem dokumentierten cwd direkt kopierbar sein.
- `rg -n "base\\.yml|dev\\.yml" .github/workflows/e2e.yml .github/workflows/e2e-tests.yml .github/workflows/shadow-soak-evidence.yml`
  - Die bewussten CI-only Legacy-Consumer muessen unveraendert sichtbar bleiben.

### Rollback / Sicherheitsgrenzen

- Rollback bleibt auf kleine Text-/Kommentar-Aenderungen begrenzt.
- Keine Aenderung an Workflow-Logik, Compose-Verhalten oder Runtime-Skripten.
- Keine Aenderung an `compose.blue.yml`, `compose.red.yml`, `base.yml`, `dev.yml`, `prod.yml`.
- Wenn `knowledge/CURRENT_STATUS.md` oder `README.md` nur ueber groessere historische Umschreibungen sauber werden, STOP und auf Minimal-Redirect/Widerspruchsabbau begrenzen.
