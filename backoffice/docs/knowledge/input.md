# Input-Dokument für Transfer-Pipeline

## Systemarchitektur

Das Claire-de-Binare-System basiert auf einer ereignisgesteuerten Architektur mit mehreren unabhängigen Services. Die Kommunikation erfolgt über Redis Pub/Sub. Jeder Service hat seine eigene Verantwortlichkeit und operiert autonom.

### Service-Übersicht

- **Bot Screener (WS/REST)**: Sammelt Marktdaten von MEXC Exchange
- **Signal Engine**: Generiert Handelssignale basierend auf Momentum-Strategien
- **Risk Manager**: Prüft Signale gegen mehrlagige Risikogrenzen
- **Execution Service**: Führt genehmigte Orders aus (Paper Trading)

Die Services kommunizieren über folgende Event-Topics:
- `market_data`: Marktdaten vom Screener zur Signal Engine
- `signals`: Trading-Signale von Signal Engine zum Risk Manager
- `orders`: Genehmigte Orders vom Risk Manager zum Execution Service
- `order_results`: Ausführungsergebnisse zurück an alle Interessierten

### Infrastruktur-Komponenten

Redis dient als Message Broker (Port 6379). PostgreSQL speichert persistente Daten wie Orders, Trades, Risk Events (Port 5432). Prometheus scraped Metriken alle 15 Sekunden. Grafana visualisiert die Metriken im Dashboard.

## Risk-Engine-Workflow

Der Risk Manager arbeitet mit priorisierten Schutzschichten. Die wichtigste Regel ist der Daily Drawdown Limit - wenn dieser überschritten wird, stoppt das gesamte Trading sofort.

### Schutzschichten-Priorität

1. Daily Drawdown Check (MAX_DAILY_DRAWDOWN_PCT)
2. Marktanomalien-Erkennung (Slippage, Spread)
3. Datenstille-Überwachung
4. Portfolio Exposure Limit (MAX_EXPOSURE_PCT)
5. Einzelpositions-Limit (MAX_POSITION_PCT)
6. Stop-Loss pro Trade (STOP_LOSS_PCT)

Wenn ein Signal eingeht, durchläuft es alle diese Checks sequenziell. Bei Verletzung einer Regel wird das Signal entweder abgelehnt, getrimmt oder das Trading pausiert.

### Alert-Mechanismus

Alerts werden über das `alerts` Topic publiziert. Jeder Alert hat einen Code (`RISK_LIMIT`, `CIRCUIT_BREAKER`, `DATA_STALE`) und ein Level (CRITICAL, WARNING, INFO). Das Dashboard zeigt Alerts in Echtzeit in der Statusleiste an.

## Config- und ENV-Regeln

Alle sensiblen Daten werden über Environment-Variablen geladen. Die `.env`-Datei darf niemals committed werden und ist in `.gitignore` eingetragen.

### Pflicht-Variablen

Folgende Variablen müssen gesetzt sein:
- REDIS_PASSWORD
- POSTGRES_USER, POSTGRES_PASSWORD
- MEXC_API_KEY, MEXC_API_SECRET
- GRAFANA_PASSWORD

### Risk-Parameter

Die Risk-Engine benötigt folgende Parameter:
- MAX_POSITION_PCT (Standard: 0.10)
- MAX_EXPOSURE_PCT (Standard: 0.50)
- MAX_DAILY_DRAWDOWN_PCT (Standard: 0.05)
- STOP_LOSS_PCT (Standard: 0.02)

Alle Prozentangaben sind als Dezimalwerte anzugeben (z.B. 0.10 für 10%).

### Service-Konfiguration

Jeder Service lädt seine Config beim Start aus der Umgebung. Fehlende Variablen führen zu einem Startup-Fehler. Es gibt ein Validierungsskript unter `backoffice/automation/check_env.ps1`, das Duplikate und fehlende Variablen erkennt.

## Deployment-Prozeduren

Der gesamte Stack wird über Docker Compose verwaltet. Alle Container nutzen das `cdb_` Präfix für einheitliche Benennung.

### Standard-Deployment

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Nach dem Start sollten alle Health-Checks grün sein. Das kann 10-15 Sekunden dauern.

### Health-Check-Strategie

Jeder Service muss einen `/health` Endpoint bereitstellen, der mit HTTP 200 und JSON `{"status": "ok"}` antwortet. Die Docker Compose Health-Checks verwenden `curl -fsS http://localhost:PORT/health`.

Zusätzlich haben die MVP-Services `/metrics` Endpoints für Prometheus. Redis nutzt `redis-cli ping`, PostgreSQL nutzt `pg_isready`.

### Rollback-Verfahren

Bei Problemen: `docker compose down`, alte Version aus Git checkout, `docker compose up -d --build`. Volumes bleiben dabei erhalten, außer man nutzt `docker compose down -v` (Achtung: löscht alle Daten!).
