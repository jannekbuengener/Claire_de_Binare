# Issue #661 Handoff - Operator Drill Real Evidence Pack

Status: analysis / handoff only
Date: 2026-03-13
Audience: Claude Code

## Ist-Analyse

- GitHub `#661` ist offen und im Tracker explizit von `#657` und `#656` abhaengig. `#656` ist bereits geschlossen; der verbleibende harte externe Blocker fuer `#661` ist damit `#657` als Quelle fuer den kanonischen Kill-Switch-Status bzw. die kanonische Verifikationsmethode.
- `tools/test_pack/tools/drills/trigger-operator-drill.ps1` ist aktuell nur ein Skeleton:
  - legt `EvidenceDir` und `screenshots/` an
  - schreibt Timeline-Stamps fuer `DRILL_START`, `ALERT_TRIGGERED_TODO`, `VERIFY_KILL_SWITCH_TODO`, `CAPTURE_STACK_LOGS`, `DRILL_END`
  - schreibt `trigger.todo.txt` und `verify.todo.txt`
  - schreibt `timeline.json`
  - versucht `stack.log` zu schreiben, sonst `stack_logs_error.txt`
  - enthaelt keinen realen Alert-Trigger, keine automatisierte Kill-Switch-Verifikation, keine automatisierte Verifikation von "order flow stopped" und keine echte Evidence-Capture ausser Timeline/Logs
- `tools/test_pack/runbooks/kill_switch_checklist.md` definiert die menschliche Drill-Erwartung bereits klar:
  - Alert quittieren
  - Kill-Switch aktivieren
  - "order flow stopped" verifizieren
  - Evidence sichern: `screenshot(s)`, `logs snapshot`, `timeline.json`
- `tools/test_pack/pack/manifest.yaml` erwartet fuer den Test-Pack generell Evidence-Pack-Artefakte wie `timeline.log or timeline.json` und `service_logs/*`. Der Operator-Drill liegt aktuell darunter, weil er Logs im Root (`stack.log`) statt unter `service_logs/` ablegt und keinerlei `reports/*` schreibt.
- `tools/test_pack/infrastructure/scripts/run-chaos-drill.ps1` ist der naechste kanonische Referenzpfad fuer Evidence-Pack-Struktur:
  - `service_logs/`
  - `reports/`
  - `README.md`
  - `run_config.json`
  - `sources_manifest.txt`
  - `timeline.log`
  Der Operator-Drill nutzt davon heute praktisch nichts ausser `EvidenceDir`.
- Screenshots werden im Repo fuer den Operator-Drill nicht automatisiert erzeugt. Die aktuelle Implementierung erstellt nur den Ordner `screenshots/`; ein echter Capture-Mechanismus oder auch nur ein Screenshot-Inventar fehlt.
- Fuer Kill-Switch und Stop-of-Order-Flow gibt es bereits belastbare Repo-Bausteine, die #661 nicht neu erfinden muss:
  - persistenter Kill-Switch-State in `core/safety/kill_switch.py`
  - lesbare Detail-API `get_kill_switch_details()`
  - fail-closed Risk-Gate in `services/risk/service.py`
  - fail-closed Execution-Gate, abgesichert durch `tests/unit/services/test_execution_shadow_gate.py`
  - repo-lokaler Drill `scripts/drills/lr003_kill_switch_limit_controls_runner.py`, der vorhandene Kill-Switch-Gates deterministisch prueft und Artefakte (`lr003_summary.json`, `lr003_report.md`) erzeugt
- Fuer den Alert-Trigger gibt es zwar Repo-Spuren Richtung Alertmanager/Webhook (`infrastructure/monitoring/alertmanager.yml`, `infrastructure/monitoring/prometheus.yml`, `infrastructure/compose/logging.yml`), aber `docs/operations/ALERTING_FIX_SUMMARY.md` markiert `infrastructure/monitoring/alertmanager.yml` gleichzeitig als `NOT used`. Deshalb darf #661 den Alertmanager-Pfad nicht blind als aktiven Runtime-Kanon annehmen.

## Minimaler Zielzustand

- Der Operator-Drill bleibt schmal: realen Alert ausloesen, menschliche Runbook-Aktion ermoeglichen, danach den vorhandenen kanonischen Stop-Zustand automatisiert verifizieren und Evidence deterministisch ablegen.
- `#661` implementiert genau einen realen Alert-Pfad, aber baut kein neues Alerting-System. Der gewaehlte Pfad muss bereits im aktuellen Stack/Setup existieren. Wenn der aktive Pfad lokal nicht belastbar identifizierbar ist, STOP statt neuer Trigger-Architektur.
- `#661` implementiert keine neue Kill-Switch-Semantik. Es bindet genau die kanonische Verifikationsquelle an, die durch `#657` definiert oder geliefert wird. Wenn `#657` diese Quelle noch nicht belastbar bereitstellt, bleibt `#661` blockiert.
- Die minimale Evidence fuer einen erfolgreichen Operator-Drill sollte danach mindestens enthalten:
  - `timeline.json` mit echten Stamps fuer Alert-Ausloesung, Verifikationsstart, Kill-Switch aktiv bestaetigt, Order-Flow-Stopp bestaetigt, Logs gesichert, Drill-Ende
  - rohes Alert-Artefakt im Evidence-Pfad, also Payload/Message und wenn verfuegbar Response/Ack
  - mindestens ein maschinenlesbares Verifikationsartefakt unter `reports/`, z. B. fuer Kill-Switch-Status und Order-Flow-Stopp
  - `service_logs/stack.log` oder `service_logs/stack_logs_error.txt`
  - `screenshots/` als deterministischer Ablageort fuer manuelle Operator-Screenshots
- Wenn die Anpassung ohne grossen Zusatzaufwand moeglich ist, sollte der Operator-Drill ausserdem an die bestehende Evidence-Pack-Form angenaehert werden:
  - `README.md` aus Template kopieren
  - `run_config.json` schreiben
  - `sources_manifest.txt` schreiben
  Das ist Alignment, aber kein Vorwand fuer einen Harness-Refactor.

## Konkrete Dateiliste fuer Claude Code

- Sollte angefasst werden:
  - `tools/test_pack/tools/drills/trigger-operator-drill.ps1`
  - `tools/test_pack/runbooks/kill_switch_checklist.md`
- Wahrscheinlich sinnvoll, aber nur falls fuer die minimale Evidence-Pack-Topologie noetig:
  - `tools/test_pack/templates/evidence_pack_README.md`
  - `tools/test_pack/README.md`
- Nur falls Artefaktpfade oder Erwartungen sonst unstimmig bleiben:
  - `tools/test_pack/pack/manifest.yaml`
- Als vorhandene Referenz- und Validierungsanker lesen, aber standardmaessig nicht umbauen:
  - `core/safety/kill_switch.py`
  - `services/risk/service.py`
  - `scripts/drills/lr003_kill_switch_limit_controls_runner.py`
  - `tests/unit/services/test_execution_shadow_gate.py`
  - `tests/unit/risk/test_contract_enforcement.py`
  - `infrastructure/monitoring/alertmanager.yml`
  - `docs/operations/ALERTING_FIX_SUMMARY.md`

## Risiken / Annahmen / offene Punkte

- `#661` ist im GitHub-Tracker an `#657` gekoppelt. Wenn `#657` keinen stabilen Status-Endpoint, keine stabile Metric und keinen klaren kanonischen Log-Marker liefert, darf `#661` das nicht "mal eben" neu definieren.
- Das Repo zeigt Alertmanager-/Webhook-Konfig, aber die aktuelle Ops-Doku nennt denselben Alertmanager-Pfad `NOT used`. Claude Code darf deshalb nicht auf Verdacht Alertmanager als Live-Kanon verdrahten.
- "Order flow stopped" ist groesser als "Kill-Switch-Flag wurde gesetzt". Wenn dafuer in `#657` keine eindeutige kanonische Quelle existiert, darf #661 keine neue Runtime- oder Monitoring-Semantik aufmachen.
- Screenshot-Capture ist heute manuell. Wenn es keinen bereits eingefuehrten lokalen Capture-Mechanismus gibt, soll #661 keinen GUI-Automations-Track starten. Ordner + klare Erwartung + Evidence-Inventar reicht.
- Der vorhandene LR-003-Drill ist ein guter repo-lokaler Nachweis fuer fail-closed Gates, aber kein Ersatz fuer eine echte kanonische Runtime-Verifikation im Operator-Drill. Er ist Validierungsanker, nicht der primaere Scope von #661.
- Keine Scope-Verschiebung in:
  - `#785` Shadow Metrics
  - `#659` CI Required Checks
  - Runtime-/Compose-Themen `#1138`, `#1139`, `#1142`

## Klare Nicht-Ziele

- Kein Incident-Management-System bauen.
- Kein Monitoring-Rewrite bauen.
- Keine neue Kill-Switch-Semantik oder neue HALT-State-Maschine definieren.
- Kein Runtime-/Compose-Umbau.
- Kein Alerting-Subprojekt starten.
- Keine Desktop-/GUI-Screenshot-Automation neu einfuehren.
- Keine anderen Drill-Tracks, Shadow-Metrics oder CI-Gates mitziehen.

## Claude-Code-Handoff

### Ziel

Den bestehenden Operator-Drill so weit vervollstaendigen, dass ein reproduzierbarer, evidenzfaehiger Kill-Switch-Drill moeglich ist: realer Alert-Trigger, automatisierte Verifikation ueber genau eine vorhandene kanonische Quelle, geordnete Evidence-Ablage. Keine neue Alerting-, Monitoring- oder Incident-Architektur.

### Betroffene Dateien

- `tools/test_pack/tools/drills/trigger-operator-drill.ps1`
- `tools/test_pack/runbooks/kill_switch_checklist.md`
- optional: `tools/test_pack/templates/evidence_pack_README.md`
- optional: `tools/test_pack/README.md`
- optional: `tools/test_pack/pack/manifest.yaml`

### Minimale Aenderungen

- `trigger-operator-drill.ps1`
  - TODO-Text fuer Alert-Trigger durch genau einen realen, bereits vorhandenen Trigger-Pfad ersetzen
  - rohes Trigger-Artefakt in den Evidence-Pfad schreiben
  - TODO-Text fuer Verifikation durch automatisierte Calls auf genau eine kanonische Quelle ersetzen
  - Timeline mit echten Drill-Stamps fuellen
  - Logs unter `service_logs/` ablegen statt lose im Root
  - `reports/` fuer maschinenlesbare Verifikationsartefakte verwenden
  - `screenshots/` behalten, aber keinen neuen GUI-Automations-Track starten
- `kill_switch_checklist.md`
  - Runbook auf den tatsaechlichen Drill-Pfad und die tatsaechlichen Evidence-Dateinamen ziehen
  - den menschlichen Teil klar lassen: Alert sehen, Kill-Switch ausloesen, Screenshots ablegen
  - keine neue Incident-Prozedur erfinden
- Optional nur wenn trivial:
  - `README.md` Template in den Operator-Drill uebernehmen
  - `run_config.json` und `sources_manifest.txt` analog zum Chaos-Drill schreiben
- Harte Scope-Grenze:
  - Wenn fuer die Verifikation zunaechst `#657` erweitert oder stabilisiert werden muss, STOP und Blocker explizit dokumentieren statt #661 aufzublaehen

### Validierung

- Script-Dry-Run mit temporaerem `EvidenceDir`:
  - Evidence-Ordner entsteht deterministisch
  - `timeline.json` enthaelt echte Stamps statt TODO-Events
  - Alert-Artefakt ist vorhanden
  - Verifikationsartefakt(e) unter `reports/` sind vorhanden
  - `service_logs/stack.log` oder sauberer Fehlerpfad liegt unter `service_logs/`
  - `screenshots/` existiert
- Bestehende Kill-Switch-Gates gegen Regression absichern:
  - `tests/unit/services/test_execution_shadow_gate.py`
  - `tests/unit/risk/test_contract_enforcement.py`
- Falls ein kleiner repo-lokaler Nachweis fuer bestehende Gate-Semantik gebraucht wird:
  - `scripts/drills/lr003_kill_switch_limit_controls_runner.py`
- Dokumentarisch pruefen:
  - Runbook, Script und ggf. Test-Pack-README nennen dieselben Evidence-Dateien und denselben Ablauf

### Rollback / Sicherheitsgrenzen

- Rollback bleibt auf Drill-Script, Runbook und ggf. kleine Evidence-Pack-Doku begrenzt.
- Keine Aenderungen an Runtime-/Compose-Topologie.
- Keine Aenderungen an Safety-Kernlogik in `core/` oder `services/` als Primaerscope von `#661`.
- Keine neuen externen Abhaengigkeiten nur fuer diesen Drill.
- Wenn der reale Trigger-Pfad oder die kanonische Verifikationsquelle nicht belastbar vorhanden sind: nicht improvisieren, sondern `#661` als durch `#657` bzw. aktiven Alerting-Kanon blockiert dokumentieren.
