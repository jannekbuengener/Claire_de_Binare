# Issue #149 Handoff - Canonical Test-Harness Entrypoints and Official E2E Path

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- `#149` ist laut aktuellem Backlog-Audit weiter offen, aber nur mit reduziertem Scope als `canonical test-harness entrypoints + official E2E path`.
- Der Runtime-Canon ist bereits klar gezogen:
  - `CURRENT_STATUS.md` und `infrastructure/compose/COMPOSE_LAYERS.md` setzen `BLUE+RED` als normalen Runtime-Pfad.
  - `base.yml + dev.yml` bleiben nur fuer `CI/test`.
  - `stack_up.ps1` / `stack_down.ps1` sind deprecatet und per Guard abgesichert.
- Die Test-Harness-Doku driftet aber noch:
  - `knowledge/testing/TEST_HARNESS_V1.md` verweist fuer E2E weiter auf `test_paper_trading_p0.py`, auf `bootstrap_local.ps1` und auf `docker-compose -f infrastructure/compose/base.yml -f infrastructure/compose/dev.yml up -d`.
  - `tests/e2e/README.md` startet lokal weiter ueber `.\infrastructure\scripts\stack_up.ps1 -Logging` und nennt als Workflow noch `.github/workflows/e2e-tests.yml`, verweist spaeter bei CI-Problemen aber auf `.github/workflows/e2e.yml`.
- `infrastructure/scripts/run_e2e.ps1` ist der schwaechste, aber wichtigste Drift-Punkt:
  - Startet weiter ueber das deprecatete `stack_up.ps1`.
  - Tear-down nutzt `infrastructure/compose/monitoring.yml`, diese Datei existiert im aktuellen Repo nicht.
  - Default-Testziel ist bereits `tests/e2e/test_smoke_pipeline.py`; damit ist der Script-Intent schmaler als die alte Test-Harness-Doku.
- Bei den GitHub-Workflows gibt es drei konkurrierende E2E-nahe Pfade:
  - `.github/workflows/e2e.yml` ist repo-seitig der staerkste Kandidat fuer den offiziellen Pfad: aktiver Trigger-Mix, Secret-Preflight, Compose-Up/Down, Health-Wait, Diagnostics und `pytest tests/e2e/test_smoke_pipeline.py`.
  - `.github/workflows/e2e-tests.yml` ist ein aelterer Parallelpfad mit demselben Smoke-Test, aber aelteren Compose-Aufrufen und schwaecherer Kanon-Qualitaet.
  - `.github/workflows/e2e-happy-path.yaml` bringt keinen Docker-Stack hoch und ist damit kein belastbarer Source-of-Truth fuer den offiziellen Harness-Pfad, auch wenn der Name das suggeriert.
- Zusaetzlicher Mismatch:
  - `pytest.ini` beschreibt `@pytest.mark.e2e` als `mit echten Containern (NUR lokal)`.
  - Gleichzeitig laufen `e2e.yml` und `e2e-tests.yml` in GitHub Actions mit `-m e2e`.
  - `tests/e2e/test_smoke_pipeline.py` selbst ist deterministisch und benoetigt keinen externen Zustand, was die Begriffsdrift erklaert, aber nicht aufloest.

## Minimaler Zielzustand

- Genau ein offizieller lokaler Entry-Path wird benannt:
  1. Lokaler Runtime-/Harness-Start ueber den heute unterstuetzten Pfad
  2. offizieller lokaler Smoke-/E2E-Target = `tests/e2e/test_smoke_pipeline.py`
  3. `test_paper_trading_p0.py` bleibt historischer/breiterer Testpfad, aber nicht der kanonische Einstieg fuer `#149`
- Genau ein offizieller GitHub-E2E-Pfad wird benannt:
  - `.github/workflows/e2e.yml`
- `e2e-tests.yml` und `e2e-happy-path.yaml` werden nicht als offizieller Harness-Source-of-Truth dokumentiert.
- Der Unterschied zwischen Runtime-Canon und CI/Test-Compose wird explizit beschrieben:
  - `BLUE+RED` = normaler Runtime-/Operator-Pfad
  - `base.yml + dev.yml` = bestehender CI/Test-/Legacy-Kompatibilitaetspfad
- Fuer `#149` reicht reine Doku-Kanonisierung nicht ganz aus:
  - Wenn `run_e2e.ps1` offizieller lokaler Entry-Point bleiben soll, ist eine minimale technische Anpassung noetig, weil das Script heute auf einen blockierten Legacy-Startpfad und eine nicht vorhandene Compose-Datei zeigt.

## Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `knowledge/testing/TEST_HARNESS_V1.md`
  - `tests/e2e/README.md`
  - `infrastructure/scripts/run_e2e.ps1`
- Falls Konsistenztext noetig ist:
  - `pytest.ini`
- Nur falls der offizielle GitHub-Pfad im Repo selbst knapp markiert werden soll:
  - `.github/workflows/e2e.yml`
  - `.github/workflows/e2e-tests.yml`
  - `.github/workflows/e2e-happy-path.yaml`
- Fuer `#149` standardmaessig nicht anfassen:
  - `infrastructure/compose/compose.blue.yml`
  - `infrastructure/compose/compose.red.yml`
  - `infrastructure/compose/base.yml`
  - `infrastructure/compose/dev.yml`
  - `infrastructure/compose/test.yml`
  - `Makefile`
  - breite Legacy-Runbooks wie `knowledge/operations/DOCKER_STACK_RUNBOOK.md`

## Risiken / Annahmen / offene Punkte

- Wenn ein identischer lokaler und CI-seitiger Compose-Pfad verlangt wird, waere das groesser als `#149`; der aktuelle Repo-Stand belegt nur eine saubere Kanonisierung, nicht die Vereinheitlichung aller Test-Stacks.
- `run_e2e.ps1` ist aktuell nicht nur textlich alt, sondern funktional drifted; dieser Punkt ist der wahrscheinlich einzige Ort, an dem eine minimale technische Anpassung fuer den Reduced Scope wirklich noetig ist.
- `e2e-happy-path.yaml` ist governance-/branch-protection-nah dokumentiert; groessere Trigger-, Naming- oder Status-Aenderungen koennen Folgedrift in Live-Readiness- oder CI-Doku ausloesen.
- Viele weitere Dateien referenzieren noch `stack_up.ps1` oder `base.yml + dev.yml`; `#149` sollte diese breite Historik nicht global bereinigen, sondern nur den offiziellen Einstieg klar ziehen.
- `pytest.ini` und die aktuelle Smoke-Test-Realitaet verwenden `e2e` nicht mehr ganz im selben Sinn; das sollte, wenn ueberhaupt, nur textlich und nicht als neue Test-Strategie aufgemacht werden.

## Klare Nicht-Ziele

- Kein Coverage-Gate- oder Required-Checks-Umbau aus `#414` oder `#659`.
- Kein Compose-/Runtime-Reconciliation-Track aus `#1138`, `#1139` oder `#1142`.
- Keine neue Testplattform und keine Umstellung des Repos auf einen voellig neuen Harness.
- Kein Nachziehen von breiteren Paper-Trading-, Replay-, Soak-, Chaos- oder Performance-Tracks.
- Kein Bulk-Cleanup aller historischen Test-/Ops-/Live-Readiness-Dokumente.
- Kein Vermischen mit `#145`, `#147`, `#169`, `#170`, `#151`, `#94`, `#189` oder groesseren Follow-up-Themen.

## Claude-Code-Handoff

### Ziel

Die heute repo-seitig vorhandenen Test-Harness-Einstiege auf genau einen offiziellen lokalen Pfad und genau einen offiziellen GitHub-E2E-Pfad reduzieren, ohne Runtime- oder CI-Plattform-Umbau.

### Betroffene Dateien

- `knowledge/testing/TEST_HARNESS_V1.md`
- `tests/e2e/README.md`
- `infrastructure/scripts/run_e2e.ps1`
- optional: `pytest.ini`
- optional: `.github/workflows/e2e.yml`
- optional: `.github/workflows/e2e-tests.yml`
- optional: `.github/workflows/e2e-happy-path.yaml`

### Minimale Aenderungen

- `knowledge/testing/TEST_HARNESS_V1.md` auf den heutigen Canon ziehen:
  - Runtime-Canon vs CI/Test-Legacy-Pfad sauber unterscheiden
  - offiziellen E2E-Einstieg auf `tests/e2e/test_smoke_pipeline.py` zuschneiden
  - tote oder unpassende Verweise wie `bootstrap_local.ps1` entfernen
- `tests/e2e/README.md` so anpassen, dass lokaler Start und CI-Referenz nicht mehr auf widerspruechliche Entrypoints zeigen.
- `run_e2e.ps1` minimal korrigieren:
  - keinen unguarded Call auf `stack_up.ps1`
  - kein Tear-down ueber `monitoring.yml`
  - Default-Testziel `tests/e2e/test_smoke_pipeline.py` beibehalten
  - Start/Stop logisch auf den wirklich unterstuetzten lokalen Pfad legen
- Nur falls fuer Repo-Klarheit noetig:
  - `e2e.yml` als offiziellen Workflow markieren
  - `e2e-tests.yml` und `e2e-happy-path.yaml` knapp als nicht-kanonische Nebenpfade markieren, ohne groesseren Workflow-Umbau
- Wenn die Textkonsistenz sonst nicht hergestellt werden kann, Marker-Beschreibung in `pytest.ini` knapp an die aktuelle Realitaet angleichen.

### Validierung

- Alle aktualisierten Texte muessen denselben offiziellen lokalen E2E-Einstieg nennen.
- Alle aktualisierten Texte muessen denselben offiziellen GitHub-E2E-Workflow nennen.
- `run_e2e.ps1` darf nach der Aenderung weder auf `stack_up.ps1` noch auf die fehlende `monitoring.yml` verweisen.
- Keine Doku darf behaupten, `e2e-tests.yml` oder `e2e-happy-path.yaml` seien der offizielle Source-of-Truth, wenn `e2e.yml` als Canon gesetzt wird.
- Keine Aussage darf Coverage-Gates, Required-Checks oder Compose-Reconciliation als Teil von `#149` aufmachen.

### Rollback / Sicherheitsgrenzen

- Rollback ist docs/script-only.
- Keine Service-, Compose-, Migration-, Runtime- oder Governance-Gate-Aenderungen.
- Keine Promotion/Demotion von Required Checks als Teil von `#149`.
- Wenn fuer einen glaubwuerdigen offiziellen Pfad groessere Workflow- oder Compose-Aenderungen noetig waeren, STOP und als Out-of-Scope fuer den aktuellen Reduced Scope markieren.
