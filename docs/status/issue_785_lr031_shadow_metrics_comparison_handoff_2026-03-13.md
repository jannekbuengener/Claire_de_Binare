# Issue #785 Handoff - LR-031 Shadow Metrics Comparison

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- Der Repo-Kanon markiert `LR-031` weiter als nicht abgeschlossen:
  - `docs/evidence/LR-031.md` steht auf `PARTIAL`.
  - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` fuehrt `LR-031` in P3 weiter als offen mit DoD `baseline vs shadow metrics report with acceptance thresholds`.
- Der GitHub-Tracker steht davor:
  - `#785` ist aktuell `CLOSED`.
  - Repo-seitig ist aber nur die Shadow-Evidence-Kette belastbar verankert, nicht der komplette comparison layer.
- Bereits vorhanden ist eine belastbare, testgestuetzte Single-run Shadow-Evidence-Kette:
  - `.github/workflows/shadow-soak-evidence.yml`
  - `infrastructure/scripts/generate_evidence_index.py`
  - `infrastructure/scripts/soak_gate_eval.py`
  - `infrastructure/scripts/build_shadow_evidence_package.py`
  - `tests/test_generate_evidence_index.py`
  - `tests/unit/scripts/test_soak_gate_eval.py`
  - `tests/unit/scripts/test_build_shadow_evidence_package.py`
- Diese Kette erzeugt bzw. verarbeitet heute:
  - `run_summary.json`
  - `endpoints/execution_metrics.txt`
  - `endpoints/risk_metrics.txt`
  - `endpoints/execution_status.json`
  - `endpoints/risk_status.json`
  - `shadow_block_probe.json`
  - `evidence_index.json`
  - `soak_gate_eval.json`
  - `package_manifest.json` plus `packages/<package_id>/manifest.json`
- Bereits repo-committete Snapshot-Verzeichnisse (`evidence-run/`, `evidence-full-run/`, `evidence-full-run-30m/`) liefern Shadow-nahe Rohdaten, aber gerade nicht den kanonischen LR-031-Abschluss:
  - vorhanden: `run_summary.*`, `endpoints/*`, Logs
  - fehlend: `shadow_block_probe.json`, `evidence_index.json`, `soak_gate_eval.json`, `package_manifest.json`
- Der fehlende Rest sitzt nicht in weiterer Shadow-Infrastruktur, sondern exakt hier:
  - Es gibt kein Script, das ein explizites Baseline-Artefakt plus Shadow-Run zusammenfuehrt.
  - Es gibt keine repo-kodierte Acceptance-Threshold-Tabelle fuer LR-031.
  - Es gibt kein `shadow comparison`-Artefakt in JSON/Markdown mit Delta-, Threshold- und Verdict-Feldern.
  - Das kanonische Evidence-Package modelliert heute keinen LR-031-Comparison-Report.
- Weitere Repo-Spuren deuten den Zielzustand an, setzen ihn aber nicht um:
  - `docs/evidence/LR-042.md` nennt `lr042_<scenario>_shadow_comparison.json|.md` und `t0 baseline snapshot`.
  - Shadow-Logs enthalten bereits `policy_hash` und `decision_context.thresholds`; das ist ein brauchbarer Vergleichsanker, aber kein LR-031-Report.
  - Historische Shadow-Reports unter `reports/shadow_mode/` enthalten Baseline-/Mismatch-Sprache, sind aber kein kanonischer LR-031-Input.

## Minimaler Zielzustand fuer #785

- Ein kleiner, separater Comparison-Layer wird auf die bestehende Shadow-Evidence-Kette gesetzt.
- Der Layer konsumiert genau zwei Dinge:
  - ein explizites, versioniertes, machine-readable LR-031-Baseline/Threshold-Artefakt
  - ein Shadow-Run-Artefakt auf Basis des bestehenden `evidence_index.json` plus noetiger Status-/Log-Anker
- Der Layer erzeugt deterministisch:
  - `shadow_metrics_comparison.json`
  - `shadow_metrics_comparison.md`
- Das JSON benoetigt mindestens:
  - Baseline-Metadaten und Provenienz
  - die verglichenen Metriken
  - Ist-/Baseline-Werte
  - Delta bzw. Ratio
  - Acceptance Threshold pro Metrik
  - per-metric PASS/FAIL
  - Gesamtverdict
- Der Workflow fuehrt diesen Vergleich nach `generate_evidence_index.py` und vor dem kanonischen Package-Build aus.
- Das kanonische Evidence-Package traegt den Comparison-Report mit; fuer einen repo-seitig belastbaren LR-031-PASS darf nicht nur das Shadow-Gate, sondern auch der Comparison-Verdict `PASS` sein.
- `docs/evidence/LR-031.md` dokumentiert danach klar:
  - Shadow capture/gate war bereits vorhanden
  - neu ist der baseline-vs-shadow comparison layer mit Acceptance Thresholds
  - kein Shadow-/Runtime-Rewrite war Teil des Deltas

## Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `.github/workflows/shadow-soak-evidence.yml`
  - `infrastructure/scripts/build_shadow_evidence_package.py`
  - `docs/evidence/LR-031.md`
- Sollte neu hinzukommen:
  - `infrastructure/scripts/shadow_metrics_compare.py`
  - `tests/unit/scripts/test_shadow_metrics_compare.py`
  - ein explizites machine-readable Baseline/Threshold-Artefakt, vorzugsweise repo-klar und reviewbar, z. B. `docs/evidence/lr031_baseline_thresholds.json`
- Wahrscheinlich anpassen:
  - `tests/unit/scripts/test_build_shadow_evidence_package.py`
- Optional, nur wenn Artefaktpfade oder Canon-Listen veraendert werden:
  - `docs/evidence/SHADOW_SOAK_RUN_INDEX.md`
  - `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`
- Fuer #785 standardmaessig nicht anfassen:
  - `infrastructure/scripts/soak_gate_eval.py`
  - `infrastructure/scripts/generate_evidence_index.py`
  - Runtime-/Service-Code unter `services/`
  - Shadow-/Soak-Compose-Topologien
  - bestehende LR-030-Shadow-Gate-Implementierung

## Risiken / Annahmen / offene Punkte

- Es gibt heute keinen kanonischen LR-031-Baseline-Pfad im Repo. Claude Code darf hier keine Werte aus historischen Reports, Issue-Text oder Bauchgefuehl erraten.
- Wenn kein defensibles Baseline-Artefakt aus existierender Repo-Evidence ableitbar ist, muss Claude Code das offen dokumentieren und darf keinen kuenstlichen `PASS` bauen.
- `execution_shadow_blocked_total` ist ein LR-030-/Probe-/Gate-Signal, kein offensichtlicher LR-031-Drift-KPI. Den bestehenden Shadow-Gate-Disput nicht neu aufrollen.
- Die committeten `evidence-*` Verzeichnisse sind Convenience-Snapshots, keine kanonischen PASS-Pakete. Nichts rueckwirkend rekonstruieren.
- Falls der Comparison-Layer `policy_hash` oder `decision_context.thresholds` als Guardrail nutzt, dann nur lesend als bestehender Anker. Kein neues Runtime-Wiring aus #748 ableiten.
- Das Issue selbst ist aktuell `CLOSED`, waehrend der Repo-Kanon `PARTIAL` sagt. Diese Notiz dokumentiert den Repo-Befund; sie ist kein Reopen-Auftrag.

## Klare Nicht-Ziele

- Kein Shadow- oder Soak-Stack-Neuaufbau.
- Kein Reopen oder Umbau von `#784`.
- Kein Abrutschen in `#661` oder `#659`.
- Kein Wiederaufrollen von `#1138`, `#1139` oder `#1142`.
- Kein Grafana-/Dashboard-/Alerting-Programm als Primaerscope.
- Keine Aenderung an Trading-Logik, Decision Thresholds oder Runtime-Verhalten.
- Kein Rueckbau oder Redesign des bestehenden LR-030/LR-031 Shadow-Gate-Pfads.
- Kein Nachpflegen historischer Shadow-Runs oder manueller Reports als scheinbar kanonische Evidence.

## Claude-Code-Handoff

### Ziel

Den fehlenden LR-031-Comparison-Layer schmal und auditierbar auf die bestehende Shadow-Evidence-Kette setzen: explizites Baseline/Threshold-Artefakt einlesen, Shadow-Run dagegen vergleichen, deterministisches Comparison-JSON/MD erzeugen, Ergebnis in Workflow und kanonisches Evidence-Package einhaengen, `docs/evidence/LR-031.md` auf den echten neuen Stand ziehen.

### Betroffene Dateien

- `.github/workflows/shadow-soak-evidence.yml`
- `infrastructure/scripts/shadow_metrics_compare.py`
- `infrastructure/scripts/build_shadow_evidence_package.py`
- `tests/unit/scripts/test_shadow_metrics_compare.py`
- `tests/unit/scripts/test_build_shadow_evidence_package.py`
- `docs/evidence/LR-031.md`
- neues Baseline/Threshold-Artefakt, z. B. `docs/evidence/lr031_baseline_thresholds.json`
- optional: `docs/evidence/SHADOW_SOAK_RUN_INDEX.md`
- optional: `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`

### Minimale Aenderungen

- `infrastructure/scripts/shadow_metrics_compare.py`
  - neues, kleines Script
  - Input: explizites Baseline/Threshold-Artefakt plus bestehendes Shadow-Evidence-Verzeichnis
  - Output: `shadow_metrics_comparison.json` und `shadow_metrics_comparison.md`
  - keine Runtime-Abhaengigkeit, kein Service-Code
- Baseline/Threshold-Artefakt
  - machine-readable und reviewbar im Repo
  - muss Baseline-Provenienz, Metrikliste und Acceptance Thresholds klar kodieren
  - keine implizite Ableitung aus historischen Markdown-Reports
- `.github/workflows/shadow-soak-evidence.yml`
  - Comparison-Script nach `generate_evidence_index.py` aufrufen
  - Comparison-Artefakte in `evidence/` ablegen
  - keine Shadow-/Stack-Architektur aendern
- `infrastructure/scripts/build_shadow_evidence_package.py`
  - Comparison-Artefakte ins kanonische Package aufnehmen
  - fuer einen kanonischen PASS-Package-Build nicht nur Shadow-Gate-PASS, sondern auch Comparison-PASS beruecksichtigen
  - Summary um Comparison-Verdict bzw. relevante Vergleichsfelder erweitern
- `tests/unit/scripts/test_shadow_metrics_compare.py`
  - PASS-Fall
  - FAIL-Fall bei Threshold-Ueberschreitung
  - FAIL-closed bei fehlendem/ungueltigem Baseline-Artefakt
  - stabile JSON/Markdown-Ausgabe
- `tests/unit/scripts/test_build_shadow_evidence_package.py`
  - neue Comparison-Dateien im Package
  - Package-Build blockiert bei fehlendem oder FAIL-Comparison-Report
- `docs/evidence/LR-031.md`
  - Status und Scope gegen den neuen Repo-Stand aktualisieren
  - klar benennen, dass der eigentliche Delta der baseline-vs-shadow comparison layer ist
  - keine neue Erzaehlung ueber Shadow-Infrastruktur
- Optional nur bei echter Pfad-/Artefakt-Aenderung:
  - `docs/evidence/SHADOW_SOAK_RUN_INDEX.md`
  - `docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`

### Validierung

- `pytest tests/unit/scripts/test_shadow_metrics_compare.py tests/unit/scripts/test_build_shadow_evidence_package.py`
- wenn noetig zusaetzlich:
  - `pytest tests/test_generate_evidence_index.py tests/unit/scripts/test_soak_gate_eval.py`
- Script-Dry-Run auf Fixture-/Temp-Evidence:
  - `python infrastructure/scripts/shadow_metrics_compare.py <baseline-artifact> <evidence-dir>`
- Repo-Checks:
  - `rg -n "shadow_metrics_comparison" .github/workflows/shadow-soak-evidence.yml infrastructure/scripts/build_shadow_evidence_package.py docs/evidence/LR-031.md docs/evidence/SHADOW_SOAK_RUN_INDEX.md docs/operations/P5_CANARY_EXECUTION_CHECKLIST.md`
  - `rg -n "baseline|threshold|verdict" infrastructure/scripts/shadow_metrics_compare.py tests/unit/scripts/test_shadow_metrics_compare.py`

### Rollback / Sicherheitsgrenzen

- Rollback bleibt auf das neue Comparison-Script, dessen Tests, Workflow-Einbindung, Package-Manifest-Delta und LR-031-Doku begrenzt.
- Keine Aenderung an Service-Code oder Compose-/Runtime-Topologie.
- `soak_gate_eval.py` und `generate_evidence_index.py` nur anfassen, wenn ein klar fehlendes Feld den Vergleich wirklich blockiert.
- Wenn Baseline-Provenienz nicht belastbar gemacht werden kann: STOP, offen dokumentieren, kein kuenstlicher LR-031-PASS.
