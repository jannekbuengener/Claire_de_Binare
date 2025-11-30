# N1 – Systemarchitektur für die Paper-Test-Phase

**Projekt:** Claire de Binare  
**Phase:** N1 – Post-Cleanroom / Paper-Test-Vorbereitung  
**Status:** Entwurf stabil, für weitere N1-Spezifikationen freigegeben  

---

## 1. Zweck & Scope

Dieses Dokument beschreibt die **logische Systemarchitektur** von Claire de Binare für die **Paper-Test-Phase** (Backtest / Mock Trading ohne Live-Exchange).

Ziele:

- Klare, modulare Beschreibung der Services / Komponenten.
- Definition der Events, Topics und Datenflüsse, die für einen vollständigen Paper-Test benötigt werden.
- Verknüpfung von Strategy-, Risk- und Execution-Layer in einem konsistenten End-to-End-Modell.
- Abgrenzung gegenüber produktionsnahen Themen (Docker, Monitoring, echte MEXC-Integration).

Nicht-Ziele:

- Vollständige Docker-/Infrastruktur-Dokumentation.
- Konkrete MEXC-Live- oder Testnet-Anbindung.
- Performance-/Skalierungsdesign.
- Vollständige physische Datenbankschemata (SQL-Details).

---

## 2. Systemkontext & Zielbild

**Zielbild:**  
Ein System, das historische Marktdaten oder simulierte Feeds verarbeitet, Signale erzeugt, Risiko-Regeln anwendet, Orders simuliert und alle Schritte so loggt, dass Strategien und Risikoregeln im **Paper-Test** nachvollziehbar ausgewertet werden können.

Hauptschritte:

1. Marktdaten einspeisen (historisch oder Mock-Feed).
2. Strategy Engine erzeugt Signale.
3. Risk Engine validiert Signale und entscheidet über Größe / Zulässigkeit.
4. Execution Simulator führt genehmigte Orders virtuell aus.
5. Portfolio & State Manager aktualisiert Positionen und Kennzahlen.
6. Logging & Analytics persistiert alle Events und States für Auswertungen.

---

## 3. Logische Systemmodule

### 3.1 Übersicht

| Modul                      | Kürzel | Verantwortung                                                                      |
|----------------------------|--------|------------------------------------------------------------------------------------|
| Market Data Ingestion      | MDI    | Marktdaten-Feed (historisch / Mock) als geordnete Eventquelle                     |
| Strategy Engine            | SE     | Ableitung von Signalen aus Marktdaten                                             |
| Risk Engine                | RE     | Risikoprüfung von Signalen, Entscheidung über Zulässigkeit & Größe                |
| Execution Simulator        | XS     | Simulation von Orders/Trades, Ableitung von Fills                                 |
| Portfolio & State Manager  | PSM    | Verwaltung von Positionen, Portfolio, Exposure, Drawdown & RiskState              |
| Logging & Analytics        | LA     | Logging aller Events/States, Reporting- und Auswertungsgrundlage                  |
| Dashboard / Reporting UI   | UI     | Visualisierung von Equity, Drawdown, Trades, Alerts                               |
| Monitoring / Health        | MON    | (optional) Status- und Health-Checks der Komponenten                              |

Diese Module sind **logische Einheiten**. Physische Deployments (Container, Prozesse) sind ein späteres Thema und nicht Teil von N1.

---

### 3.2 Modulbeschreibungen

#### Market Data Ingestion (MDI)

- Quelle für `MarketDataEvent`-Events (z. B. Candles).
- Kann historisch (Backtest-Daten) oder „quasi-live“ aus einem Export gespeist werden.
- Zeitlich strenger, sequentieller Output.

#### Strategy Engine (SE)

- Eingabe: `MarketDataEvent`.
- Ausgabe: `StrategySignal` (z. B. BUY/SELL/FLAT, mit Reason und optionaler Stärke).
- Kennt weder Kontostand noch Exposure-Limits.
- Nutzt parametrisierte Strategie-Logik (siehe Strategy-Interface-Doku).

#### Risk Engine (RE)

- Eingaben: `StrategySignal`, `RiskState`, `PortfolioSnapshot`, `RiskConfig`.
- Ausgabe: `RiskDecision` (approved / abgelehnt + Größe + Reason-Code).
- Implementiert konfigurierbare Risikoregeln (pro Trade, pro Symbol, Gesamtportfolio, Drawdown, Frequenz etc.).
- Siehe **`docs/Risikomanagement-Logik.md`** für Details.

#### Execution Simulator (XS)

- Eingabe: genehmigte `RiskDecision`.
- Erzeugt `SimulatedOrder` und `SimulatedTrade`.
- Einfaches Ausführungsmodell für N1/Paper-Test (z. B. Fill zum Candle-Open/Close).
- Aktualisiert keine States direkt, sondern liefert Events an PSM/LA.

#### Portfolio & State Manager (PSM)

- Konsolidiert alle Trades und Positionsänderungen.
- Führt u. a. folgende logische States:
  - `PositionState` (pro Symbol)
  - `PortfolioSnapshot` (Equity, Cash, Drawdown, Exposure)
  - `RiskState` (Flags, Drawdown, Exposure, Cooldown etc.)
- Liefert Daten für Risk Engine und UI.

#### Logging & Analytics (LA)

- Speichert alle zentralen Events:
  - `MarketDataEvent`, `StrategySignal`, `RiskDecision`, `SimulatedOrder`, `SimulatedTrade`, `PortfolioSnapshot`, `BacktestRunMetadata`.
- Basis für:
  - Equity-Kurven
  - Drawdown-Analysen
  - Trade-Statistiken
  - Strategy- und Risk-Tuning

#### Dashboard / Reporting UI (UI)

- Visualisiert die von LA bereitgestellten Daten.
- Muss im N1-Status nicht voll produktionsreif sein, sondern nur die Auswertung unterstützen.

---

## 4. Service-Kommunikation & Events (Paper-Test-Scope)

Die Paper-Test-Architektur nutzt ein Event-basiertes Modell. Ob die Events in N1 als interne Funktionsaufrufe oder über einen Message-Bus laufen, ist flexibel; wichtig sind die **Event-Typen und Payloads**.

### 4.1 Event-Typen & Topics (logisch)

| Topic / Kanal   | Publisher      | Subscriber            | Zweck                          |
|-----------------|----------------|-----------------------|---------------------------------|
| `market_data`   | MDI            | SE                    | Marktdaten-Events              |
| `signals`       | SE             | RE                    | StrategySignale                |
| `orders`        | RE             | XS                    | Genehmigte Orders (logisch)    |
| `order_results` | XS             | PSM, LA, UI           | Resultate simulierte Ausführung|
| `alerts`        | RE/XS          | UI, LA                | Risk-/System-Warnungen         |

### 4.2 Event-Beispiele (Paper-Test-Format)

```jsonc
// market_data
{
  "type": "market_data",
  "symbol": "BTC_USDT",
  "timestamp": 1730443200000,
  "open": 35210.0,
  "high": 35280.5,
  "low": 35190.0,
  "close": 35250.5,
  "volume": 184.12,
  "interval": "1m"
}

// signal
{
  "type": "signal",
  "symbol": "BTC_USDT",
  "direction": "BUY",
  "strength": 0.82,
  "reason": "MOMENTUM_BREAKOUT",
  "timestamp": 1730443260000,
  "strategy_id": "momentum_v1"
}

// risk_decision (logisch)
{
  "type": "risk_decision",
  "symbol": "BTC_USDT",
  "requested_direction": "BUY",
  "approved": true,
  "approved_size": 0.05,
  "reason_code": "OK",
  "timestamp": 1730443270000
}

// order_result (simuliert)
{
  "type": "order_result",
  "order_id": "SIM_123456",
  "status": "FILLED",
  "symbol": "BTC_USDT",
  "filled_quantity": 0.05,
  "price": 35260.1,
  "timestamp": 1730443280000
}

// alert (Risk / System)
{
  "type": "alert",
  "level": "CRITICAL",
  "code": "DRAWDOWN_LIMIT_HIT",
  "message": "Maximaler Drawdown erreicht. Trading gestoppt.",
  "timestamp": 1730443300000
}
5. End-to-End-Datenfluss (Paper-Test-Pipeline)
5.1 Textueller Ablauf
MDI → SE

MDI liefert MarketDataEvent (z. B. nächste Candle).

SE verarbeitet das Event und erzeugt ggf. StrategySignal.

SE → RE

StrategySignal wird von der Risk Engine konsumiert.

RE zieht RiskState, PortfolioSnapshot und RiskConfig hinzu.

Ergebnis: RiskDecision.

RE → XS

Bei approved = true erstellt XS eine SimulatedOrder.

XS simuliert die Ausführung: Erzeugung eines SimulatedTrade basierend auf definierter N1-Regel (z. B. Fill am nächsten Candle-Open).

XS → PSM & LA

PSM aktualisiert PositionState, PortfolioSnapshot und RiskState.

LA loggt alle Events & States.

PSM/LA → UI

UI liest Snapshot- und Event-Daten und visualisiert Kennzahlen.

5.2 Merkmals-Schema (Mermaid, logisch)
mermaid
Code kopieren
flowchart LR
    MD["📊 MarketDataEvent"]
    SIG["🎯 StrategySignal"]
    RD["🛡 RiskDecision"]
    OR["📝 SimulatedOrder"]
    TRD["💼 SimulatedTrade"]
    PS["📂 PortfolioSnapshot"]
    RS["⚠️ RiskState"]

    MD -->|"Strategy Engine"| SIG
    SIG -->|"Risk Engine"| RD
    RD -->|"Execution Simulator"| OR
    OR -->|"simulierte Ausführung"| TRD
    TRD -->|"update"| PS
    TRD -->|"update"| RS
Logging & Analytics beobachtet alle Pfeile passiv und persistiert die Events.

6. Verknüpfung mit dem Risk-Layer
Die Risk Engine ist im Detail in docs/Risikomanagement-Logik.md beschrieben.
Dieses Architektur-Dokument legt nur die logische Einbettung fest:

RE konsumiert StrategySignal-Events aus der SE.

RE liest RiskState & PortfolioSnapshot aus PSM.

RE nutzt RiskConfig (Paper-Test-Konfiguration).

RE produziert RiskDecision und ggf. alerts.

**State-Konsistenz (N1 Zusatz):**
- Postgres ist Single Source of Truth für Risk/Exposure (Portfolio-Snapshots).
- Beim Start: DB-Snapshot laden, Exposure ableiten und Redis-Cache `risk_state:persistence` überschreiben, falls Drift >5%.
- Laufzeit: Auto-Heal korrigiert Redis-Divergenzen (>5%) ohne Trading zu blockieren; Redis bleibt Cache/Transport.
- Adaptive Risk-Intensity: `adaptive_intensity/dry_wet.py` berechnet aus den letzten Trades einen Score (DRY↔WET) und stellt dynamische Risk-Parameter über Redis bereit.
- Dry/Wet Service: `adaptive_intensity/dry_wet_service.py` looped score/params nach Redis (`adaptive_intensity:current_params`), Prometheus-Metriken exponiert `/metrics`.

Die Details zu:

Pre-Checks (Kill Switch, Cooldown),

Risk per Trade,

Exposure-Regeln,

Drawdown-Regeln,

Frequenzbegrenzung,

werden nicht doppelt beschrieben, sondern ausschließlich dort gepflegt.

7. Datenhaltung im Paper-Test
Für die N1-Phase ist primär das logische Datenmodell relevant.
Physische Schemata (SQL, Tabellenlayout) sind sekundär und werden getrennt dokumentiert.

Wichtige logische Entitäten:

MarketDataEvent

StrategySignal

RiskState

RiskDecision

SimulatedOrder

SimulatedTrade

PositionState

PortfolioSnapshot

BacktestRunMetadata

Physische Umsetzung:

Die bestehenden Schemata für orders und trades (siehe DATABASE_SCHEMA_UEBERSICHT.md und DATABASE_SCHEMA.sql) dienen als Referenz.

Für N1 genügt es, diese Schemata als „physische Skizze“ zu betrachten; Anpassungen an das Paper-Test-Modell können später konsistent nachgezogen werden.

Änderungen am logischen Modell werden in diesem Dokument nachvollzogen, bevor die SQL-Schemata modifiziert werden.

8. Abgrenzung zu späteren Phasen (Live / Docker / Monitoring)
Die in SYSTEM_FLUSSDIAGRAMM.md dokumentierte, dockerisierte Gesamtarchitektur mit:

MEXC Exchange (WS/REST),

Redis Pub/Sub,

PostgreSQL als persistenter Speicher,

Prometheus / Grafana,

Health-Checks & Container-Zuständen,

wird in N1 als Referenzmodell verstanden, aber nicht als harte Vorgabe.

Für N1 / Paper-Test gilt:

Einfache Laufzeitumgebung ist ausreichend (z. B. Single-Process-Runner/Script).

Docker-/Compose-Details, Ports und exakte Container-Landschaft sind ein Thema der späteren Implementierungsphase.

Monitoring (Prometheus, Grafana) ist „Nice to have“, aber kein Pflichtbestandteil der Paper-Test-Architektur.

9. Verknüpfung zu weiteren N1-Dokumenten
Dieses Dokument steht im Zentrum der N1-Architektur und verweist auf folgende weitere Spezifikationen:

Risk-Layer:
docs/Risikomanagement-Logik.md
→ detaillierte Regeln und Entscheidungslogik der Risk Engine.

Strategy-Layer & Interface:
(z. B. docs/ARCHITEKTUR_Strategy_Layer.md, falls vorhanden)
→ genaue Schnittstellenbeschreibung für Strategien.

Service-Kommunikation & Datenflüsse (technische Sicht):
docs/SERVICE_DATA_FLOWS.md
→ detaillierte technische Beschreibung von Topics, Routing und Beispiel-Payloads.

System-Flussdiagramm (Produktionsnähe):
docs/SYSTEM_FLUSSDIAGRAMM.md
→ mermaid-basierte Visualisierung der produktionsnahen Gesamtarchitektur; für N1 als Referenz, nicht als harte Vorgabe.

DB-Schemata (physisch):
docs/DATABASE_SCHEMA_UEBERSICHT.md
docs/DATABASE_SCHEMA.sql
→ physische Tabellenstrukturen für Orders/Trades; initiales Mapping auf das logische N1-Datenmodell.

Stateful Components & Persistence
Das System schreibt persistenten Zustand ausschließlich in dedizierte Infrastruktur-Services:
– PostgreSQL: Order-, Trade-, Signal- und Risk-Daten
– Redis: Kurzfristige Queue- und Cache-Daten (Market-Events, Signals, Orders)
– Prometheus/Grafana/Loki (falls aktiv): Metriken, Dashboards und Logs
Applikations-Container selbst gelten als stateless und können jederzeit neu gebaut und neu gestartet werden, solange diese Stores und Volumes erhalten bleiben.

## 10. Systemparameter & Infrastruktur

### ENV Variablen

| Variable             | Wert               |
|----------------------|--------------------|
| `POSTGRES_DB`        | `claire_de_binare` |
| `POSTGRES_USER`      | `claire`           |
| `POSTGRES_PASSWORD`  | `<secret>`         |
| `REDIS_PASSWORD`     | `<secret>`         |

### Ports

| Bezeichnung    | Port |
|----------------|------|
| `WS_PORT`      | 8000 |
| `SIGNAL_PORT`  | 8001 |
| `RISK_PORT`    | 8002 |
| `EXEC_PORT`    | 8003 |
| `PROM_PORT`    | 9090 |
| `GRAFANA_PORT` | 3000 |
| `REDIS_PORT`   | 6379 |
| `DB_PORT`      | 5432 |

### Volumes

| Volume              |
|---------------------|
| `cdb_postgres_data` |
| `cdb_redis_data`    |
| `cdb_prom_data`     |
| `cdb_grafana_data`  |

### Systemkonstanten

| Konstante        | Wert           |
|------------------|----------------|
| `RTO`            | `≤ 15 Minuten` |
| `RPO`            | `≤ 24 Stunden` |
| `RETENTION_DAYS` | `14`           |

### Pflichtregeln

| Regel |
|-------|
| `DB-Name MUSS exakt "claire_de_binare" sein.` |
| `System erwartet eine ".env" im Projektroot.` |
| `Docker/Compose ist Standard (keine Profiles im MVP).` |

---

## Weiterführende Dokumentation

- **Repository Structure Refactoring**: Details zum geplanten Struktur-Cleanup siehe [STRUCTURE_CLEANUP_PLAN.md](STRUCTURE_CLEANUP_PLAN.md)
- **Project Governance**: Architektur-Prinzipien und Entscheidungen siehe [KODEX – Claire de Binare.md](../KODEX%20–%20Claire%20de%20Binare.md)
- **Architectural Decisions**: Alle ADRs dokumentiert in [DECISION_LOG.md](../DECISION_LOG.md)

Python-Laufzeit
----------------
Das System verwendet **ausschließlich das global installierte Python**, gesteuert über:

- `PYTHON_HOME`
- `SYSTEM_PYTHON_PATH`
- `USE_SYSTEM_PYTHON=true`

Lokale Python-Installationen innerhalb des Projektordners sind deaktiviert.
