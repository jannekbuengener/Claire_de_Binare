## Transfer-Regeln

**Definiert von**: claire-architect
**Ziel**: Konsolidierte, strukturierte Referenzdokumentation f�r System-Architektur und Risk-Engine

### �bertragungslogik

1. **H2-�berschriften �bernehmen**: Alle Hauptabschnitte (##) aus input.md werden als H2 in output.md �bernommen
2. **H3-Unterabschnitte selektiv**: Nur H3-Abschnitte mit technischer Substanz (Service-Listen, Parameter-Tabellen, Workflow-Beschreibungen) �bernehmen
3. **Strukturierte Listen bevorzugen**: Wo input.md Flie�text verwendet, in Aufz�hlungen oder Tabellen umwandeln
4. **Code-Bl�cke beibehalten**: Alle Bash/Code-Beispiele 1:1 �bernehmen
5. **Prosa reduzieren**: Einleitende S�tze k�rzen, direkt zur Sache kommen

### Ausschlusskriterien

- Redundante Erkl�rungen zu bereits dokumentierten Konzepten
- Vage Formulierungen wie "kann dauern", "sollte sein" � pr�zise Angaben
- Deployment-Prozeduren (geh�ren in separates Ops-Dokument)

### Zielstruktur

```
## Systemarchitektur
  ### Services
  ### Event-Topics
  ### Infrastruktur

## Risk-Engine-Workflow
  ### Schutzschichten
  ### Alert-Codes

## Konfiguration
  ### Secrets
  ### Risk-Parameter
```

---

## Systemarchitektur

Ereignisgesteuerte Architektur mit autonomen Services, Kommunikation via Redis Pub/Sub.

### Services

| Service | Funktion |
|---------|----------|
| Bot Screener (WS/REST) | Sammelt Marktdaten von MEXC Exchange |
| Signal Engine | Generiert Handelssignale (Momentum-Strategien) |
| Risk Manager | Prüft Signale gegen mehrlagige Risikogrenzen |
| Execution Service | Führt genehmigte Orders aus (Paper Trading) |

### Event-Topics

| Topic | Producer | Consumer | Inhalt |
|-------|----------|----------|--------|
| `market_data` | Bot Screener | Signal Engine | Marktdaten |
| `signals` | Signal Engine | Risk Manager | Trading-Signale |
| `orders` | Risk Manager | Execution Service | Genehmigte Orders |
| `order_results` | Execution Service | Risk Manager, Dashboard, PostgreSQL | Ausführungsergebnisse |

### Infrastruktur

| Komponente | Port (Host) | Port (Container) | Funktion |
|------------|-------------|------------------|----------|
| Redis | 6379 | 6379 | Message Broker |
| PostgreSQL | 5432 | 5432 | Persistenz (Orders, Trades, Risk Events) |
| Prometheus | 19090 | 9090 | Metriken (Scrape-Intervall: 15s) |
| Grafana | 3000 | 3000 | Visualisierung |

**Hinweis**: Prometheus Host-Port 19090 gemappt auf Container-Port 9090 (Standard-Prometheus-Port).

## Risk-Engine-Workflow

Priorisierte Schutzschichten mit sequenzieller Prüfung eingehender Signale.

### Schutzschichten

| Priorität | Check | ENV-Variable | Schwellwert | Aktion bei Verletzung |
|-----------|-------|--------------|-------------|----------------------|
| 1 | Daily Drawdown | `MAX_DAILY_DRAWDOWN_PCT` | Default: 0.05 (5%) | Trading-Stopp, manuelle Freigabe erforderlich |
| 2 | Marktanomalien | `MAX_SLIPPAGE_PCT`, `MAX_SPREAD_MULTIPLIER` | 0.01 (1%), 5.0 | Circuit Breaker, Pause bis Normalisierung |
| 3 | Datenstille | `DATA_STALE_TIMEOUT_SEC` | 30 | Neue Orders pausieren, Positionen halten |
| 4 | Portfolio Exposure | `MAX_EXPOSURE_PCT` | Default: 0.50 (50%) | Neue Orders blockieren, bestehende laufen |
| 5 | Einzelposition | `MAX_POSITION_PCT` | Default: 0.10 (10%) | Order trimmen auf Limit (nicht ablehnen) |
| 6 | Stop-Loss | `STOP_LOSS_PCT` | Default: 0.02 (2%) | Automatischer Exit, Alert RISK_LIMIT/WARNING |

**Verarbeitungslogik**: Signal durchläuft alle Checks sequenziell. Ablehnung, Trimming oder Pause je nach Verstoß.

**Recovery-Verhalten**:
- Daily Drawdown: Reset um 00:00 UTC, manuelle Freigabe via Admin-Befehl erforderlich
- Marktanomalien: Automatischer Retry alle 60s, max. 10 Versuche
- Datenstille: Automatische Wiederaufnahme bei neuem `market_data` Event

### Alert-Codes

| Code | Level | Trigger | Beispiel |
|------|-------|---------|----------|
| `RISK_LIMIT` | CRITICAL | Daily Drawdown, Exposure >80% | `{"code": "RISK_LIMIT", "level": "CRITICAL", "message": "Daily drawdown limit exceeded: 5.2%"}` |
| `RISK_LIMIT` | WARNING | Stop-Loss ausgelöst, Position-Limit getrimmt | `{"code": "RISK_LIMIT", "level": "WARNING", "message": "Position trimmed: BTC_USDT 0.10 → 0.08"}` |
| `CIRCUIT_BREAKER` | WARNING | Marktanomalien (Slippage >1%, Spread >5x) | `{"code": "CIRCUIT_BREAKER", "level": "WARNING", "message": "High slippage detected: 1.8%"}` |
| `DATA_STALE` | WARNING | Keine Marktdaten >30s | `{"code": "DATA_STALE", "level": "WARNING", "message": "No market data for 35s"}` |

**Level-Regel**:
- CRITICAL: Trading-Stopp oder harte Limits (Drawdown, Exposure >80%)
- WARNING: Weiche Limits, Trimming, temporäre Pausen

Alerts via `alerts` Topic publiziert, Anzeige in Grafana Dashboard-Statusleiste.

## Konfiguration

### Secrets

**Pflicht-Variablen** (nie committen, nur in `.env`):
- `REDIS_PASSWORD`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `MEXC_API_KEY`, `MEXC_API_SECRET`
- `GRAFANA_PASSWORD`

### Risk-Parameter

| Variable | Standard | Min | Max | Format | Beschreibung |
|----------|----------|-----|-----|--------|--------------|
| `MAX_POSITION_PCT` | 0.10 | 0.01 | 0.25 | Dezimal | Positionsgröße (10% des Kapitals) |
| `MAX_EXPOSURE_PCT` | 0.50 | 0.10 | 1.00 | Dezimal | Gesamt-Exposure (50% des Kapitals) |
| `MAX_DAILY_DRAWDOWN_PCT` | 0.05 | 0.01 | 0.20 | Dezimal | Tagesverlust-Limit (5%) |
| `STOP_LOSS_PCT` | 0.02 | 0.005 | 0.10 | Dezimal | Stop-Loss pro Trade (2%) |
| `MAX_SLIPPAGE_PCT` | 0.01 | 0.001 | 0.05 | Dezimal | Marktanomalien-Grenze (1%) |
| `MAX_SPREAD_MULTIPLIER` | 5.0 | 2.0 | 10.0 | Float | Spread-Multiplikator (5x normal) |
| `DATA_STALE_TIMEOUT_SEC` | 30 | 10 | 120 | Integer | Datenstille-Timeout (Sekunden) |

**Format-Regel**: Prozentangaben als Dezimalwerte (0.10 = 10%).

**Validierung**:
- `backoffice/automation/check_env.ps1` prüft auf Duplikate und fehlende Variablen
- Range-Checks beim Service-Start (außerhalb Min/Max → WARN-Log, Fallback auf Standard)

**Laufzeit-Verhalten**: Parameter werden nur beim Start geladen, keine Laufzeit-Änderung möglich.

**Startup-Verhalten**:
- Fehlende Pflicht-Variablen → Container crasht mit Exit Code 1
- Fehlerhafte Secrets (z.B. falsches Redis-Passwort) → Retry-Loop mit exponential backoff (max. 5 Versuche, dann Crash)

**Secret-Rotation**: Manuelle Rotation erforderlich, `.env` aktualisieren und Container neustarten (`docker compose restart <service>`).

## Usage

### Zielgruppe

Dieses Dokument dient als **technische Referenz** für:
- **Backoffice/Operations**: Verständnis der Risk-Engine-Logik und Parameter-Tuning
- **Entwickler**: Integration neuer Services in die Event-Architektur
- **DevOps/Infra**: Deployment, Monitoring-Setup, Troubleshooting
- **Neue Contributors**: Onboarding und Systemverständnis

### Verwendung durch Rollen

| Rolle | Nutzungsszenario | Relevante Abschnitte |
|-------|------------------|----------------------|
| **Operations** | Parameter-Anpassung, Risk-Tuning | Risk-Parameter, Schutzschichten, Alert-Codes |
| **Entwickler** | Event-Integration, Service-Entwicklung | Event-Topics, Services, Alert-Codes |
| **DevOps** | Deployment, Health-Checks, Secrets-Management | Infrastruktur, Secrets, Startup-Verhalten |
| **Contributors** | System-Überblick, Architektur-Verständnis | Systemarchitektur, Risk-Engine-Workflow |

### Integration mit anderen Dokumenten

- **`backoffice/docs/ARCHITEKTUR.md`**: Detaillierte System-Architektur, Port-Mappings, Container-Topologie
- **`backoffice/docs/Risikomanagement-Logik.md`**: Pseudocode und Entscheidungslogik der Risk-Engine
- **`backoffice/docs/EVENT_SCHEMA.json`**: Vollständige Event-Payload-Spezifikationen
- **`.env.template`**: Vollständige Liste aller ENV-Variablen mit Beispielwerten
- **`docker-compose.yml`**: Deployment-Konfiguration, Health-Checks, Volumes

### Wartung

**Update-Frequenz**: Bei strukturellen Änderungen (neue Services, Events, Risk-Parameter)

**Verantwortlich**: Architektur-Team (claire-architect) in Abstimmung mit DevOps

**Changelog**: Änderungen in `backoffice/docs/DECISION_LOG.md` (ADR-Format) dokumentieren
