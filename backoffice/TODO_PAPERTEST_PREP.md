# TODO: 7-Tage-Papertest Vorbereitung

**Datum erstellt**: 2025-11-23, 00:15 UTC
**Status**: PostgreSQL Persistence gehärtet (v1.3.1) - Bereit für nächste Phase
**Ziel**: System vollständig für 7-Tage-Papertest vorbereiten

---

## 📊 AKTUELLER STAND (Checkpoint)

### ✅ Abgeschlossen (2025-11-23)
- **PostgreSQL Persistence**: 100% stabil + gehärtet
  - 7 Bugs gefixt (Fix #1-7)
  - Migration 002 erfolgreich (orders.price nullable)
  - Rejected trades semantisch korrekt geskippt
  - Decimal-Typ für Financial Data implementiert
  - Hard Validation mit ValueError aktiv
  - E2E-Validierung: 18/18 Events + neue Test-Events bestanden
  - ADR-044 dokumentiert

- **Container-Status**: 9/9 healthy
  - cdb_redis, cdb_postgres, cdb_db_writer
  - cdb_ws, cdb_core, cdb_risk, cdb_execution
  - cdb_prometheus, cdb_grafana

- **Test-Suite**: 122 Tests (100% Pass Rate)
  - 90 Unit-Tests
  - 14 Integration-Tests
  - 18 E2E-Tests (mit Docker)
  - Risk-Engine: 100% Coverage

- **Branch**: `claude/fix-postgres-persistence-01FGrXqTxrSnnotHv7C3zHaq`
  - Alle Änderungen committed und gepusht
  - Bereit für Merge oder weitere Arbeit

---

## 🎯 SOFORT (Morgen starten, < 2h)

### 1. PostgreSQL Persistence - Edge-Case Tests erweitern
**Priorität**: HOCH
**Zeit**: 30 min
**Ziel**: Validieren dass Fix #6 und #7 robust sind

**Aufgaben**:
- [ ] **Market Order Edge-Cases testen**
  ```python
  # Test-Events publizieren:
  # 1. Market Order ohne price (NULL)
  # 2. Limit Order mit price
  # 3. Mixed Order-Types
  ```
  - Erwartung: Market Orders mit `price = NULL` in DB
  - Erwartung: Limit Orders mit `price = Decimal` in DB

- [ ] **Rejected/Cancelled Trade Edge-Cases**
  ```python
  # Test-Events publizieren:
  # 1. REJECTED status (verschiedene Varianten: REJECTED, rejected, Rejected)
  # 2. CANCELLED status
  # 3. Unknown status (sollte gewarnt und geskippt werden)
  ```
  - Erwartung: `⏭️  Skipping rejected/cancelled order_result` in Logs
  - Erwartung: Keine Einträge in `trades` Tabelle
  - Erwartung: Warning bei unknown status

- [ ] **PostgreSQL Query-Tests durchführen**
  ```sql
  -- Prüfen: Market vs. Limit Orders
  SELECT order_type, COUNT(*),
         COUNT(price) as with_price,
         COUNT(*) - COUNT(price) as null_price
  FROM orders
  GROUP BY order_type;

  -- Prüfen: Nur echte Trades in trades table
  SELECT status, COUNT(*)
  FROM trades
  GROUP BY status;
  -- Erwartung: Nur filled, partial, partially_filled

  -- Prüfen: Keine execution_price = 0
  SELECT COUNT(*) FROM trades WHERE execution_price <= 0;
  -- Erwartung: 0
  ```

**Deliverables**:
- `tests/test_postgres_edge_cases.py` (neues Test-File)
- Validierungs-Report als Markdown (z.B. `POSTGRES_EDGE_CASE_VALIDATION.md`)

---

### 2. Status-Update & Branch aufräumen
**Priorität**: MITTEL
**Zeit**: 15 min

**Aufgaben**:
- [ ] Pull Request erstellen (falls gewünscht)
  - Branch: `claude/fix-postgres-persistence-01FGrXqTxrSnnotHv7C3zHaq`
  - Target: `main`
  - Titel: "fix: PostgreSQL Persistence Hardening (Fix #6 & #7)"

- [ ] ODER: Branch in main mergen (lokal)
  ```bash
  git checkout main
  git merge claude/fix-postgres-persistence-01FGrXqTxrSnnotHv7C3zHaq
  git push origin main
  ```

- [ ] PROJECT_STATUS.md finalisieren
  - Container-Status-Tabelle aktualisieren (Datum + Uhrzeit)
  - Nächste Schritte für Papertest ergänzen

---

## 📈 HEUTE (Fortsetzung, 2-4h)

### 3. End-to-End Event-Flow Tests
**Priorität**: HOCH
**Zeit**: 1.5h
**Ziel**: Kompletten Event-Flow testen: market_data → signals → orders → order_results → PostgreSQL

**Aufgaben**:
- [ ] **E2E-Test implementieren**: `tests/e2e/test_full_event_pipeline.py`
  ```python
  def test_full_event_flow_market_data_to_db():
      """
      Test: Kompletter Event-Flow von market_data bis PostgreSQL

      1. Publish market_data event (Redis)
      2. Signal Engine generiert signal event
      3. Risk Manager validiert → order event
      4. Execution Service simuliert trade → order_result event
      5. DB Writer persistiert in PostgreSQL
      6. Validierung: Alle Tabellen enthalten erwartete Daten
      """
  ```

- [ ] **Monitoring während E2E-Test**
  - Logs von allen Services mitloggen
  - Timing messen (Latenz zwischen Events)
  - Resource-Usage tracken

- [ ] **Fehlerfälle testen**
  - Rejected Order → kein Trade in DB
  - Invalid Signal → kein Order
  - Stale Data → Circuit Breaker triggert

**Deliverables**:
- E2E-Test-Suite mit mindestens 5 Szenarien
- Performance-Metriken dokumentiert

---

### 4. Portfolio & State Manager implementieren
**Priorität**: KRITISCH (für Papertest)
**Zeit**: 2h
**Ziel**: Portfolio-State tracken und PnL berechnen

**Aufgaben**:
- [ ] **Portfolio Manager Service erstellen**
  - `services/cdb_portfolio/service.py`
  - Subscribed zu: `order_results`, `market_data`
  - Publishes: `portfolio_snapshots`

- [ ] **State Management**
  ```python
  # Funktionen:
  # - update_position(trade_event) → berechnet neue Position
  # - calculate_pnl(current_price, positions) → realized + unrealized PnL
  # - calculate_exposure() → total_exposure_pct
  # - calculate_drawdown() → max_drawdown_pct
  # - create_snapshot() → Portfolio-Snapshot Event
  ```

- [ ] **PostgreSQL Integration**
  - Snapshots automatisch persistieren (jede Minute oder nach Trade)
  - Query-Funktionen für Analytics

- [ ] **Tests schreiben**
  - Unit-Tests: PnL-Berechnung
  - Integration-Tests: Position-Updates
  - E2E-Test: Trade → Position → Snapshot → PostgreSQL

**Deliverables**:
- Portfolio Manager Service (funktional)
- 15+ Tests für Portfolio-Logik
- Docker-Integration (neuer Container `cdb_portfolio`)

---

## 🚀 DIESE WOCHE (vor Papertest)

### 5. Monitoring & Alerting Setup
**Priorität**: HOCH
**Zeit**: 1.5h

**Aufgaben**:
- [ ] **Grafana Dashboards konfigurieren**
  - Dashboard 1: Portfolio Overview (Equity, PnL, Drawdown)
  - Dashboard 2: Trading Activity (Signals, Orders, Trades)
  - Dashboard 3: System Health (Container Status, Latency, Errors)

- [ ] **Prometheus Metrics erweitern**
  ```python
  # In jedem Service:
  from prometheus_client import Counter, Histogram, Gauge

  signal_count = Counter('signals_generated_total', 'Total signals')
  order_latency = Histogram('order_processing_seconds', 'Order latency')
  portfolio_equity = Gauge('portfolio_equity_usd', 'Portfolio equity')
  ```

- [ ] **Alerting-Regeln definieren**
  - Alert bei Drawdown > 3%
  - Alert bei Container unhealthy
  - Alert bei Execution-Fehler

**Deliverables**:
- 3 Grafana Dashboards (exportiert als JSON)
- Prometheus Alert-Rules (YAML)
- Dokumentation: `MONITORING_SETUP.md`

---

### 6. Backup & Recovery Strategie
**Priorität**: MITTEL
**Zeit**: 1h

**Aufgaben**:
- [ ] **Backup-Script erstellen**
  ```powershell
  # backoffice/automation/backup_postgres.ps1
  # - Täglich 01:00 Uhr
  # - pg_dump → C:\Backups\cdb_postgres\YYYY-MM-DD\
  # - Cleanup: Older than 14 days
  ```

- [ ] **Recovery-Test durchführen**
  - Backup erstellen
  - Container stoppen
  - Daten löschen
  - Restore aus Backup
  - Validieren: Alle Daten vorhanden

- [ ] **Scheduled Task einrichten** (Windows Task Scheduler)

**Deliverables**:
- Backup-Script (PowerShell)
- Recovery-Runbook (`POSTGRES_RECOVERY.md`)
- Erster erfolgreicher Backup-Lauf dokumentiert

---

### 7. Performance & Stress Tests
**Priorität**: MITTEL
**Zeit**: 1h

**Aufgaben**:
- [ ] **Load-Test implementieren**
  ```python
  # tests/performance/test_high_volume.py
  # Simuliere: 100 Signals/minute für 10 Minuten
  # Erwartung: Alle Events verarbeitet, keine Fehler, Latenz < 100ms
  ```

- [ ] **Stress-Test mit Edge-Cases**
  - 1000 Events in 1 Sekunde
  - Gleichzeitige Rejected + Filled Trades
  - Invalid Data gemischt mit Valid Data

- [ ] **Resource-Monitoring**
  - CPU/RAM während Load-Test
  - PostgreSQL Connection Pool Status
  - Redis Queue Length

**Deliverables**:
- Performance-Test-Suite
- Stress-Test-Ergebnisse dokumentiert
- Bottlenecks identifiziert (falls vorhanden)

---

## 📋 7-TAGE-PAPERTEST CHECKLISTE

### Pre-Start Validierung
- [ ] **ENV-Validation ausführen**
  ```powershell
  backoffice/automation/check_env.ps1
  ```
  - Erwartung: Alle ENV-Variablen gesetzt und valide

- [ ] **Systemcheck durchführen**
  - Alle Container healthy
  - Health-Endpoints antworten
  - PostgreSQL erreichbar
  - Redis erreichbar
  - Grafana Dashboards laden

- [ ] **Backup vor Start**
  - PostgreSQL Voll-Backup
  - .env Backup
  - Docker Volumes Backup

### Während des Papertests
- [ ] **Tägliches Monitoring** (7 Tage)
  - Equity-Entwicklung tracken
  - Drawdown überwachen (Max: 5%)
  - Trade-Count & Win-Rate
  - System-Errors (sollte 0 sein)

- [ ] **Tägliche Backups**
  - Automatisch via Script
  - Manuell validieren

- [ ] **Log-Archivierung**
  - Container-Logs täglich exportieren
  - Struktur: `logs/papertest/day_1/`, `day_2/`, etc.

### Post-Test Analyse
- [ ] **Daten extrahieren**
  ```sql
  -- Alle Trades des Papertests
  SELECT * FROM trades
  WHERE timestamp BETWEEN '2025-11-23' AND '2025-11-30';

  -- Portfolio-Entwicklung
  SELECT * FROM portfolio_snapshots
  ORDER BY timestamp;

  -- Performance-Metriken
  SELECT
    COUNT(*) as total_trades,
    AVG(slippage_bps) as avg_slippage,
    SUM(fees) as total_fees
  FROM trades;
  ```

- [ ] **Report erstellen**
  - Equity-Chart
  - Drawdown-Chart
  - Trade-Statistiken
  - System-Performance
  - Lessons Learned

---

## 🔧 OPTIONAL (Nice-to-Have)

### 8. CLI-Tool für Papertest-Management
```bash
# Idee: claire papertest start/stop/status
python backoffice/cli/claire_papertest.py start --duration 7days
python backoffice/cli/claire_papertest.py status
python backoffice/cli/claire_papertest.py report
```

### 9. Telegram/Discord Alerts
- Notifications bei wichtigen Events
- Daily Summary Reports
- Critical Alerts (Drawdown, Errors)

### 10. Web-Dashboard (Live View)
- Real-time Equity
- Live Trade-Feed
- System-Status

---

## 📝 NOTIZEN & OFFENE FRAGEN

### Fragen für Jannek:
1. **Papertest-Startdatum**: Wann soll der 7-Tage-Test starten?
2. **Initial Capital**: Welches Startkapital? (Standard: 100.000 USDT)
3. **Risk-Limits**: Aktuell 5% Daily Drawdown, 10% Total Exposure - ok?
4. **Monitoring-Frequenz**: Wie oft manuell checken? (Vorschlag: 2x täglich)
5. **Stop-Kriterien**: Wann Test abbrechen? (z.B. bei >8% Drawdown)

### Technische TODOs (später):
- [ ] Rate-Limiting für MEXC-API-Calls
- [ ] Automatic Recovery bei Service-Crashes
- [ ] Circuit Breaker für Database-Connections
- [ ] Event-Store für Replay-Funktionalität

---

## 📞 NÄCHSTER SCHRITT (morgen)

**Start hier**:
1. Lies diese TODO-Datei
2. Beginne mit Abschnitt "SOFORT" (Edge-Case Tests)
3. Arbeite Abschnitt "HEUTE" ab (E2E + Portfolio Manager)
4. Update PROJECT_STATUS.md mit Fortschritt

**Command zum Starten**:
```bash
cd /home/user/Claire_de_Binare_Cleanroom
docker compose ps  # Prüfen: Alle Container healthy?
pytest -v -m "not e2e"  # CI-Tests durchlaufen?
# Dann: Edge-Case Tests implementieren
```

**Branch**:
- Aktuell: `claude/fix-postgres-persistence-01FGrXqTxrSnnotHv7C3zHaq`
- Option 1: Weiterarbeiten auf diesem Branch
- Option 2: Neuer Branch für Papertest-Prep: `claude/papertest-preparation`

---

**Erstellt von**: Claude Code
**Letzte Aktualisierung**: 2025-11-23, 00:15 UTC
**Status**: ✅ Ready to start
