# SYSTEM_INVARIANTS - Must-Never-Break Rules

**Version:** 1.0
**Erstellt:** 2025-12-28
**Status:** Kanonisch
**Pruefintervall:** Bei jedem Session-Start

---

## Zweck

Diese Datei definiert **unverletzliche Systeminvarianten**.
Ein Verstoss gegen diese Regeln bedeutet **Systembruch**.

---

## 1. Trading Invariants

### INV-010: Paper Trading Default
**Regel:** System startet IMMER im Paper Trading Mode.
**Implementierung:** `MOCK_TRADING=true` als Default in allen Services.
**Pruefung:** Kein Order darf ohne explizites Gate an eine echte Exchange gehen.

### INV-011: Risk-before-Execution
**Regel:** Jede Order MUSS durch Risk Service gehen.
**Datenfluss:** signal -> risk -> execution (nie signal -> execution direkt).
**Pruefung:** Execution Service akzeptiert nur Messages vom orders-Channel.

### INV-012: Circuit Breaker Authority
**Regel:** Risk Service kann jederzeit alle Orders blockieren.
**Implementierung:** circuit_breaker_active Flag in Risk Service.
**Pruefung:** Bei circuit_breaker_active=true werden keine neuen Orders weitergeleitet.

---

## 2. Security Invariants

### INV-020: Secrets Never in Git
**Regel:** Keine Secrets duerfen jemals in Git committet werden.
**Speicherort:** `~/.secrets/.cdb/` (ausserhalb Repo).
**Pruefung:** gitleaks in CI, pre-commit hooks.

### INV-021: Localhost Binding
**Regel:** Alle Ports auf 127.0.0.1 gebunden.
**Ausnahme:** Keine - auch nicht fuer "Debugging".
**Pruefung:** docker ps zeigt nur 127.0.0.1:PORT.

### INV-022: TLS Optional aber Prepared
**Regel:** TLS fuer Redis + PostgreSQL muss aktivierbar sein.
**Implementierung:** `-TLS` Flag in stack_up.ps1.
**Pruefung:** tls.yml existiert und ist syntaktisch korrekt.

---

## 3. Data Invariants

### INV-030: Event Sourcing
**Regel:** Alle State-Aenderungen ueber Events (Replay-faehig).
**Implementierung:** PostgreSQL speichert alle Events.
**Pruefung:** Event Replay muss deterministisches Ergebnis liefern.

### INV-031: Deterministic UUIDs
**Regel:** Event-IDs sind deterministisch generiert.
**Implementierung:** `core/utils/uuid_gen.py` mit Seed.
**Pruefung:** Gleicher Seed = gleiche UUID-Sequenz.

### INV-032: Centralized Clock
**Regel:** Alle Services nutzen zentralen Clock.
**Implementierung:** `core/utils/clock.py`.
**Pruefung:** Replay mit historischen Timestamps muss funktionieren.

---

## 4. Deployment Invariants

### INV-040: Delivery Gate
**Regel:** Kein Live-Deployment ohne explizites Gate.
**Datei:** `governance/DELIVERY_APPROVED.yaml`.
**Pruefung:** CI-Workflow `delivery-gate.yml`.

### INV-041: Container Naming
**Regel:** Alle Container mit `cdb_` Prefix.
**Format:** `cdb_<service>` (z.B. cdb_redis, cdb_signal).
**Pruefung:** docker ps --filter "name=cdb_".

### INV-042: Health Endpoints
**Regel:** Jeder Application Service hat /health Endpoint.
**Response:** HTTP 200 bei gesund, HTTP 503 bei Problem.
**Pruefung:** docker-compose healthchecks.

---

## 5. Governance Invariants

### INV-050: User Authority
**Regel:** User (Jannek) ist oberste Autoritaet.
**Umsetzung:** Kein Agent darf gegen explizite User-Anweisung handeln.
**Pruefung:** Bei Konflikt: STOP und User fragen.

### INV-051: Canon Location
**Regel:** Canon liegt nur im Docs Repo.
**Pfad:** `Claire_de_Binare_Docs/knowledge/`, `/governance/`, `/agents/`.
**Pruefung:** Keine Governance-Dateien im Working Repo erstellen.

### INV-052: Session Hygiene
**Regel:** Keine Session ohne Issue-Pflege.
**Umsetzung:** Am Session-Ende mindestens ein GitHub Issue.
**Pruefung:** CURRENT_STATUS.md referenziert aktive Issues.

---

## Verletzungsprotokoll

Bei Invariant-Verletzung:
1. **SOFORT STOPPEN** - keine weiteren Aktionen
2. **Verletzung dokumentieren** - Issue mit Label `invariant-violation`
3. **User informieren** - Jannek entscheidet ueber Vorgehensweise
4. **Keine autonome Reparatur** - erst nach User-Freigabe

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Core Build Sprint | Claude (Orchestrator) |
