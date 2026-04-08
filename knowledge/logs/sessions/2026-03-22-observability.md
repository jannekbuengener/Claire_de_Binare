# Observability Session — Dashboard Cleanup & Snapshot Pipeline

**Datum:** 2026-03-22
**Operator:** Claude Code (Sonnet 4.6)
**Status:** ERLEDIGT
**Issues:** #1251 (closed), #1255 (closed)

Historical note:
- This session log is a point-in-time record for 2026-03-22.
- Dashboard references below were later superseded by the 2026-04-08/09 consolidation work (`#1532`, `#1533`).
- The active dashboard canon is now the single file `infrastructure/monitoring/grafana/dashboards/cdb_operator_kpis_v1.json`.

---

## Ausgangslage

- 15 Dashboard-Dateien unter `infrastructure/monitoring/grafana/dashboards/`
- Davon 13 explizit als `ARCHIVED (legacy dashboard)` markiert, 1 reine Platzhalter-Hülle (`cdb_money_result_owner_v1.json` — alle KPI-Panels waren Markdown-Text "KPI missing")
- `cdb_trading_performance_v1.json` existierte nicht
- Publish-Kette `paper_runner → Redis → db_writer → PostgreSQL` unterbrochen: `paper_runner` published nie auf Redis-Channel `portfolio_snapshots`
- `portfolio_snapshots`-Tabelle enthielt ausschließlich den Schema-Seed-Eintrag (Timestamp: Schema-Init, PnL=0)
- `db_writer` hatte die vollständige Konsumseite (subscribed auf `portfolio_snapshots`, INSERT implementiert) — wartete auf einen Publisher, der nie kam

---

## Umgesetzte Änderungen

### #1251 — Dashboard-Footprint radikal reduzieren

**Gelöscht (14 Dateien):**

| Datei | Grund |
|---|---|
| `claire_dark_v1.json` | Explizit ARCHIVED |
| `claire_database_v1.json` | Explizit ARCHIVED |
| `claire_execution_v1.json` | Explizit ARCHIVED |
| `claire_hitl_control_v1.json` | Explizit ARCHIVED |
| `claire_minimal_observability_v1.json` | Explizit ARCHIVED |
| `claire_paper_trading_v1.json` | Explizit ARCHIVED (Phase N1) |
| `claire_risk_manager_v1.json` | Explizit ARCHIVED |
| `claire_signal_engine_v1.json` | Explizit ARCHIVED |
| `claire_soak_test_v1.json` | Explizit ARCHIVED |
| `claire_system_performance_v1.json` | Explizit ARCHIVED |
| `cdb_system_health_v1.json` | Explizit ARCHIVED |
| `risk_decision_accounting.json` | Explizit ARCHIVED |
| `signals_sprint1.json` | Explizit ARCHIVED (Sprint-1-Fossil) |
| `cdb_money_result_owner_v1.json` | Platzhalter-Hülle, keine echten Datenpanels |

**Hinzugefügt:**
- `cdb_trading_performance_v1.json` — minimales Trading-Performance-Dashboard

  | Panel | Typ | Datasource |
  |---|---|---|
  | SYSTEM HEALTH | stat | Prometheus (`min(up{job=~"cdb_.*"})`) |
  | CIRCUIT BREAKER | stat | Prometheus (`circuit_breaker_active`) |
  | KILL SWITCH | stat | Prometheus (`risk_kill_switch_active`) |
  | EQUITY (latest) | stat | PostgreSQL (`portfolio_snapshots.total_equity`) |
  | DAILY PnL | stat | PostgreSQL (`portfolio_snapshots.daily_pnl`) |
  | REALIZED PnL | stat | PostgreSQL (`portfolio_snapshots.total_realized_pnl`) |
  | EQUITY CURVE | timeseries | PostgreSQL (`portfolio_snapshots` Zeitreihe) |
  | ORDERS APPROVED | stat | Prometheus (`orders_approved_total`) |
  | ORDERS BLOCKED | stat | Prometheus (`orders_blocked_total`) |
  | FILLS | stat | Prometheus (`execution_orders_filled_total`) |
  | APPROVAL RATE | gauge | Prometheus (`orders_approved / signals_received * 100`) |

**Geändert:**
- `infrastructure/monitoring/grafana/provisioning/datasources/postgres.yml` — `uid: postgres` ergänzt (für deterministische Datasource-Referenzierung im Dashboard JSON)

**Commit:** `6bb4532`

---

### #1255 — paper_runner: Snapshot-Publish-Loop implementieren

**Betroffene Datei:** `tools/paper_trading/service.py`

**Neue Methoden in `PaperTradingRunner`:**

`_compute_portfolio_snapshot()`:
- Aggregiert aus `positions`-Tabelle: `SUM(unrealized_pnl)`, `SUM(realized_pnl)`, `COUNT(*) FILTER (WHERE closed_at IS NULL AND side != 'none')`, `SUM(size * current_price)` offener Positionen
- `total_equity = PAPER_STARTING_CAPITAL + realized + unrealized`
- Guard: `total_equity <= 0` → clamp auf 0.01 + Warning (DB-Constraint `total_equity > 0`)
- `daily_pnl`: Delta zum frühesten `portfolio_snapshots`-Eintrag des aktuellen Tages (Fallback 0.0)
- `max_drawdown_pct`: 0.0 (expliziter Platzhalter, kein laufender Peak-Tracker)

`snapshot_loop()`:
- Daemon-Thread, gestartet in `run()` neben `health_thread` und `report_thread`
- Interval: `PAPER_SNAPSHOT_INTERVAL_SECONDS` (Default 3600)
- Publisht JSON auf Redis-Channel `portfolio_snapshots`
- Exceptions werden geloggt, Loop läuft weiter (kein Absturz)

**ENV-Variablen (neu):**
- `PAPER_SNAPSHOT_INTERVAL_SECONDS` (Default: `3600`)
- `PAPER_STARTING_CAPITAL` (Default: `100000.0`)

**Commit:** `c26b08d`

---

### Weitere Commits dieser Session

| Commit | Inhalt |
|---|---|
| `1116275` | `CLAUDE.md` im Repo-Root angelegt (Build-/Test-Befehle, Architekturüberblick) |
| `33b81e2` | `CURRENT_STATUS.md` aktualisiert |

---

## Operative Wirkung

Die Kette ist jetzt geschlossen:

```
paper_runner (stündlich)
  → PUBLISH portfolio_snapshots (Redis)
    → db_writer (subscribed, persistiert)
      → PostgreSQL: portfolio_snapshots-Tabelle
        → Grafana: cdb_trading_performance_v1 (Equity/PnL-Panels)
```

Dashboard-Footprint: 15 → 2 Dateien.

---

## Validierung / Checks

- JSON-Syntax `cdb_trading_performance_v1.json`: OK
- Datasource-UIDs konsistent: `prometheus` (war vorhanden) + `postgres` (neu gesetzt)
- Provisioning-Pfad unverändert (`claire.yml` scannt Ordner) — kein manueller Import nötig
- Syntax-Check `tools/paper_trading/service.py` via `ast.parse`: OK
- 14 Validierungs-Checks (Channel-Name, Defaults, Exception-Handling, Payload-Felder, Guard): alle PASS

---

## Restunsicherheiten / offene Folgepunkte

| Punkt | Status |
|---|---|
| `max_drawdown_pct = 0.0` (Platzhalter) | Offen — kein laufender Peak-Tracker implementiert |
| `cdb_system_health_owner_v1.json` (43 Panels, viele Platzhalter) | Offen — kein Cleanup-Issue angelegt |
| `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md` (veraltet) | Offen — referenziert gelöschte Dashboards |
| Postgres-Reconnect bei Connection-Loss in `snapshot_loop` | Offen — außerhalb Scope |
| Portfolio-Panels leer solange `positions`-Tabelle leer (kein Trade) | Erwartetes Verhalten — konsistenter Snapshot mit Starting Capital wird trotzdem published |

---

## Referenzen

- Führende Statusquelle: `CURRENT_STATUS.md`
- Dashboard: `infrastructure/monitoring/grafana/dashboards/cdb_trading_performance_v1.json`
- Konsumseite (vollständig): `services/db_writer/db_writer.py:640-683`
- DB-Schema: `infrastructure/database/schema.sql:184-218`
- Publisher: `tools/paper_trading/service.py` — `_compute_portfolio_snapshot()`, `snapshot_loop()`
