# Session Log: Issue #1314 — alerts-Channel-Audit

**Datum:** 2026-03-29
**Branch:** fix/1311-dual-delivery-approved-cleanup
**Scope:** services/execution/config.py, knowledge/ARCHITECTURE_MAP.md

---

## Ausgangslage

Issue #1314 fragte nach dem realen Zustand des Redis Pub/Sub Channels `alerts`:
- Hat `cdb_execution` eine aktive publish()-Callsite für `TOPIC_ALERTS`?
- Hat `cdb_db_writer` einen Subscriber für `alerts`?
- Ist ein Subscriber überhaupt vorgesehen?

---

## Befunde (Evidenz-Audit)

- `services/risk/service.py:2011` — `cdb_risk` publiziert aktiv auf `alerts` via `send_alert()`
- `services/risk/service.py:2430` — Prometheus-Metrik `risk_alerts_generated_total` trackt Publizierungen
- `services/execution/config.py:53` — `TOPIC_ALERTS = "alerts"` war definiert
- `services/execution/service.py` — kein einziges Vorkommen von `TOPIC_ALERTS` (bestätigter Dead Code)
- `services/db_writer/db_writer.py:83` — channels-Liste ohne `alerts`
- Kein anderer Service subscribet `alerts` im gesamten Repo
- `knowledge/ARCHITECTURE_MAP.md:112` — Gap war bereits dokumentiert, aber die execution-Zeile war irreführend

---

## Durchgeführte Änderungen

- `services/execution/config.py` — `TOPIC_ALERTS = "alerts"` entfernt (Dead Code, nie referenziert)
- `knowledge/ARCHITECTURE_MAP.md:112` — alerts-Zeile auf aktuellen Zustand zurechtgeschnitten: Publisher `cdb_risk`, Subscriber-Spalte `kein Subscriber im Repo verifiziert`

---

## Validierung

- Grep auf `TOPIC_ALERTS` im gesamten Repo → 0 Treffer nach Entfernung
- ARCHITECTURE_MAP-Zeile 112 korrekt aktualisiert
- Keine Tests betroffen (TOPIC_ALERTS war nie in Tests referenziert)

---

## Restzustand

- `alerts` ist ein aktiver Publisher (cdb_risk), aber kein Subscriber existiert
- Alerts sind ephemer — kein Persistenzpfad
- Dies ist der dokumentierte Zustand; keine Designentscheidung für/gegen Subscriber getroffen
- Eine künftige Entscheidung (z. B. db_writer subscribet alerts) würde Issue #1314 als Folge-Task benötigen
