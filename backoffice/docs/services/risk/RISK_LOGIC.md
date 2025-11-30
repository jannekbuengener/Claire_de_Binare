# Risikomanagement-Logik (synchron zu `.env`)

## 1️⃣ Parameter aus Umgebungsvariablen

| Variable                  | Standard | Wirkung                              |
|---------------------------|----------|--------------------------------------|
| `MAX_POSITION_PCT`        | `0.10`   | Anteil des Kapitals pro Trade        |
| `MAX_EXPOSURE_PCT`        | `0.50`   | Gesamt-Exposure über alle Positionen |
| `MAX_DAILY_DRAWDOWN_PCT`  | `0.05`   | Circuit Breaker pro Handelstag       |
| `STOP_LOSS_PCT`           | `0.02`   | Stop-Loss je Position                |
| `LOOKBACK_MINUTES`        | `15`     | Momentum-Analysefenster              |

## 2️⃣ Priorisierte Schutzschichten

1. **Daily Drawdown** → sofortiger Handelsstopp, Positionen schließen, Alert
2. **Abnormale Märkte** (Slippage >1 %, Spread >5x) → `CIRCUIT_BREAKER` Alert, Handel pausieren
3. **Datenstille** (>30 s ohne neue Marktpreise) → `DATA_STALE` Alert, Handelsloop pausieren
4. **Portfolio Exposure** → keine neuen Orders, Alerts auf `alerts`
5. **Positionsgröße** → Order trimmen oder ablehnen
6. **Stop-Loss je Trade** → Execution-Service initiiert Exit

## 3️⃣ Entscheidungslogik (Pseudocode)

```python
def on_signal(signal):
    if exceeds_drawdown():
        emit_alert(level="CRITICAL", code="RISK_LIMIT")
        halt_trading()
        return Reject(reason="drawdown")
    if abnormal_market():
        emit_alert(level="WARNING", code="CIRCUIT_BREAKER")
        pause_trading()
        return Reject(reason="environment")

    if total_exposure() >= MAX_EXPOSURE_PCT:
        emit_alert(level="INFO", code="RISK_LIMIT")
        return Reject(reason="exposure")

    allowed_size = min(signal.size, max_position_size())
    if allowed_size < signal.size:
        return Approve(size=allowed_size, trimmed=True)

    return Approve(size=signal.size)
```

```python
def on_position_update(position):
    if position.unrealized_loss_pct >= STOP_LOSS_PCT:
        emit_alert(level="WARNING", code="RISK_LIMIT")
        close_position(position)

    if exceeds_drawdown():
        emit_alert(level="CRITICAL", code="CIRCUIT_BREAKER")
        close_all_positions()
        halt_trading()
```

## 4️⃣ Referenzwerte & Maßnahmen

| Ereignis                     | Trigger                           | Alert-Code (Schema) | Aktion                               |
|------------------------------|-----------------------------------|---------------------|--------------------------------------|
| Daily Drawdown überschritten | Verlust ≥ `MAX_DAILY_DRAWDOWN_PCT`| `RISK_LIMIT`        | Handel stoppen, Positions-Abbau     |
| Marktanomalie                | Slippage >1 %, Spread >5x normal  | `CIRCUIT_BREAKER`   | Pause, Alert, manueller Review       |
| Datenstille                  | Keine Marktdaten >30 s            | `DATA_STALE`        | Handels-Loop pausieren, Alert senden |
| Exposure Limit erreicht      | Exposure ≥ `MAX_EXPOSURE_PCT`     | `RISK_LIMIT`        | Neue Orders blockieren               |
| Positionslimit verletzt      | Ordergröße > `MAX_POSITION_PCT`   | `RISK_LIMIT`        | Order trimmen oder ablehnen          |
| Stop-Loss ausgelöst          | Verlust ≥ `STOP_LOSS_PCT`         | `RISK_LIMIT`        | Order Result markieren, Exit         |

## 5️⃣ Monitoring-Kanäle

- Prometheus Counter: `risk_alert_total{level="CRITICAL"}`
- Redis Stream: `alerts` (payload enthält `code`, `message`, `ts`)
- Dashboard V5 Statusleiste: farbige LED (grün/orange/rot)
- Decision-Log: ADR-Referenzen in `docs/DECISION_LOG.md`

## 6️⃣ Security & Dependencies

- Redis-Zugriff: Risk Manager authentifiziert sich mit `REDIS_PASSWORD=REDACTED_REDIS_PW` aus `.env`; `docker-compose.yml` erzwingt `--requirepass` gemäß ADR-023.
- Secrets werden ausschließlich über Environment-Variablen geladen; keine Hardcodes im Codepfad (`config.py` liest `.env`).
- Bei Rotation ist `PROJECT_STATUS.md` zu aktualisieren und `semantic_index.json`-Relation `.env → risk_logic_doc` auf den neuen Wert zu setzen.

## 7️⃣ Validierung

1. `pytest backoffice/services/risk_manager/tests` (falls vorhanden)
2. `docker compose logs cdb_risk --tail 200`
3. `redis-cli -a $REDIS_PASSWORD lrange alerts -10 -1`

## 8) State Sync & Auto-Heal

- Quelle: Postgres `portfolio_snapshots` (jüngster Snapshot = Wahrheit).
- Startup: Snapshot laden → Exposure = `equity * total_exposure_pct` → RiskState setzen → Redis-Key `risk_state:persistence` überschreiben, wenn Drift >5% zwischen DB und Redis.
- Laufzeit: Auto-Heal-Loop prüft Drift >5% und triggert DB→Redis-Reset statt zu blockieren.
- Redis ist Cache/Transport, nicht Truth. Entscheidungen basieren auf dem DB-abgeleiteten State.
- Metriken (Prometheus): `risk_state_inconsistency_total`, `risk_state_resync_total`, `risk_state_recovery_total`, `risk_total_exposure_value`.

## 9) Adaptive Dry/Wet Scoring (Risk-Intensity)

- Modul: `backoffice/services/adaptive_intensity/dry_wet.py`
- Eingang: letzte N=300 Trades aus Postgres (PnL).
- Kennzahlen: Winrate, Profit Factor, max Drawdown.
- Score 0..100 → DRY (0) bis WET (100).
- Mapping auf Parameter: `signal_threshold_pct`, `max_exposure_pct`, `max_position_pct`.
- Publikation: Redis-Key `adaptive_intensity:current_params` (Risk Manager liest dynamische Parameter).
- Metriken: `dry_wet_score` (Gauge, optional), `dry_wet_window_trades_total`, `dry_wet_last_update_timestamp` (bei Bedarf ergänzen).
- Service: `adaptive_intensity/dry_wet_service.py` berechnet/publiziert zyklisch und exponiert `/metrics`, `/status`, `/health`.

---

Stand: 2025-11-02 • Besitzer: Risk-Team Claire de Binare
