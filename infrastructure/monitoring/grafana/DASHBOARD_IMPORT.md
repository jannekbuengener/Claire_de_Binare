# Grafana Dashboard Import

## Aktuelles Setup

Grafana läuft unter: **http://localhost:3000**
- Username: `admin`
- Password: per secret init (see `SECRETS_PATH` / `bootstrap_local.sh`); not stored in `.env` in the repo

---

## Minimal Observability Dashboard (v1)

- Datei: `dashboards/claire_minimal_observability_v1.json`
- Datasource: `Prometheus`
- Targets: `cdb_signal:8005`, `cdb_execution:8003`, `cdb_db_writer:8010`, `cdb_candles:8007` (dev-only)
- Stack starten: kanonischer BLUE+RED Runtime via `compose.blue.yml` + `compose.red.yml`. `base.yml + dev.yml` nur fuer CI/test/debug.

---

## Quick Import - Freqtrade Dashboard

Das Dashboard `freqtrade_dashboard.json` ist ein Community-Dashboard (gnetId: 14632) für Trading-Bot-Monitoring.

### Import-Schritte:

1. **Grafana öffnen:**
   ```
   http://localhost:3000
   ```

2. **Dashboard importieren:**
   - Sidebar → `+` (Create) → `Import`
   - `Upload JSON file` → wähle `dashboards/freqtrade_dashboard.json`
   - Oder: Paste JSON content direkt

3. **Datasource konfigurieren:**
   - Bei "Prometheus" → wähle `Prometheus` (sollte auto-detected sein)
   - Port: 9090 (via `cdb_prometheus`)

4. **Dashboard laden:**
   - Click `Import`
   - Dashboard sollte erscheinen (evtl. "No data" - normal, da wir andere Metrik-Namen nutzen)

---

## Metric-Namen Mapping

**Freqtrade → Claire de Binare:**

Das Dashboard erwartet Freqtrade-Metriken, wir haben aber eigene:

| Freqtrade Metrik | Claire Equivalent | Service |
|------------------|-------------------|---------|
| `freqtrade_perf_realized_pct` | (noch nicht vorhanden) | Paper Runner |
| `freqtrade_trade_winning` | `signals_generated` (Teil) | Signal Engine |
| `freqtrade_crypto_balance` | `total_exposure` | Risk Manager |
| `freqtrade_state` | `signal_engine_status` | Signal Engine |
| `freqtrade_trade_open_current` | `open_positions` | Risk Manager |

### Aktuell verfügbare Metriken:

**Signal Engine** (`http://localhost:8001/metrics`):
```
signals_generated_total
signal_engine_status
```

**Risk Manager** (`http://localhost:8002/metrics`):
```
signals_received_total
signals_approved_total
signals_blocked_total
orders_approved_total
```

**Paper Runner** (`http://localhost:8004/health`):
- Noch keine Prometheus-Metriken, nur JSON health

---

## Nächste Schritte (Optional)

### A) Dashboard für Claire anpassen:
1. Nach Import: Dashboard in Grafana editieren
2. Panels anpassen auf unsere Metrik-Namen
3. Export als `claire_dashboard_v1.json`

### B) Prometheus-Metriken erweitern:
- Paper Runner: `/metrics` Endpoint hinzufügen
- Metrics: paper_trades_total, win_rate, exposure_used, etc.

### C) Alerts konfigurieren:
- Zero-Activity-Detection (keine Signale > 24h)
- High Exposure Warning (> 40% des Limits)
- Risk-Approval-Rate zu niedrig (< 5%)

---

## Troubleshooting

### 5-Step "No Data" Checklist
1. **Datasource**: Panel uses correct datasource (Prometheus vs. PostgreSQL).
2. **Targets UP**: Prometheus targets show `UP=1` for the job/service.
3. **Metric exists**: Query returns data in Prometheus (Graph tab).
4. **Service exports**: `/metrics` (or SQL table) is present and reachable.
5. **Time/vars**: Time range + dashboard variables include real data windows.

**Problem: "No data points"**
- Check: Prometheus scraping läuft (`http://localhost:19090/targets`)
- Check: Services exportieren Metriken (`curl localhost:8001/metrics`)

**Problem: "Dashboard import failed"**
- JSON-Format validieren: https://jsonlint.com
- Grafana Version prüfen (Dashboard ist für v8.0.6)

**Problem: "Datasource not found"**
- Prometheus DS manuell hinzufügen:
  - URL: `http://cdb_prometheus:9090`
  - Access: `Server (default)`

---

## Status

- ✅ Dashboard-JSON im Repo
- ✅ Import-Anleitung verfügbar
- ⏳ Metrik-Mapping (Future Work)
- ⏳ Dashboard-Anpassung für Claire (Future Work)

Generated: 2025-11-30 (3-Tage-Paper-Trading-Block, Tag 1)
