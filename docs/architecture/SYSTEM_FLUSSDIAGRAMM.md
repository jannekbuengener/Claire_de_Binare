# Claire de Binaire – System-Flussdiagramm

**Letzte Aktualisierung:** 25. Oktober 2025  
**Status:** Phase 5 abgeschlossen, System produktionsbereit

---

## Gesamtarchitektur

```mermaid
flowchart TD
    %% === Externe Datenquellen ===
    MEXC["🌐 MEXC Exchange<br/>(WebSocket + REST)"]
    
    %% === Datenerfassungsschicht ===
    subgraph DATA_LAYER["📊 Datenerfassungsschicht"]
        direction TB
        WS["WS-Screener<br/>(bot_ws)<br/>:9001"]
        REST["REST-Screener<br/>(bot_rest)<br/>:9002<br/>❌ DEAKTIVIERT"]
    end
    
    %% === Nachrichtenbus ===
    REDIS[("🔴 Redis<br/>Nachrichtenbus<br/>:6380<br/>Pub/Sub")]
    
    %% === Verarbeitungsschicht ===
    subgraph PROCESSING["⚙️ Verarbeitungsschicht"]
        direction TB
        SIGNAL["Signal-Engine<br/>(signal_engine)<br/>:8001<br/>Technische Analyse"]
        RISK["Risiko-Manager<br/>(risk_manager)<br/>:8002<br/>Risiko-Prüfung"]
        EXEC["Ausführungs-Service<br/>(execution_service)<br/>:8003<br/>Order-Ausführung"]
    end
    
    %% === Speicherschicht ===
    POSTGRES[("🐘 PostgreSQL<br/>Datenbank<br/>:5432<br/>claire_de_binare")]
    
    %% === Mock Trading ===
    MOCK["🎭 Mock-Executor<br/>Paper Trading<br/>95% Erfolgsrate"]
    
    %% === Überwachungsschicht ===
    subgraph MONITORING["📈 Überwachungsschicht"]
        direction LR
        PROM["Prometheus<br/>:9090<br/>⚠️ Ungesund<br/>(nicht blockierend)"]
        GRAFANA["Grafana<br/>:3001<br/>✅ Gesund<br/>(Dashboard ausstehend)"]
    end
    
    %% === Datenflüsse ===
    MEXC -->|"Marktdaten"| WS
    MEXC -.->|"REST API<br/>(ungenutzt)"| REST
    
    WS -->|"PUBLISH<br/>market_data"| REDIS
    
    REDIS -->|"SUBSCRIBE<br/>market_data"| SIGNAL
    SIGNAL -->|"PUBLISH<br/>signals"| REDIS
    
    REDIS -->|"SUBSCRIBE<br/>signals"| RISK
    RISK -->|"PUBLISH<br/>orders"| REDIS
    
    REDIS -->|"SUBSCRIBE<br/>orders"| EXEC
    EXEC -->|"Persistieren"| POSTGRES
    EXEC -->|"Ausführen"| MOCK
    MOCK -->|"Ergebnis"| EXEC
    EXEC -->|"PUBLISH<br/>order_results"| REDIS
    
    EXEC -->|"Metriken"| PROM
    SIGNAL -->|"Metriken"| PROM
    RISK -->|"Metriken"| PROM
    PROM -.->|"Datenquelle"| GRAFANA
    
    %% === REST API ===
    EXEC -->|"REST API<br/>/health, /orders, /metrics"| CLIENT["👤 Benutzer"]
    
    %% Styling
    classDef external fill:#e1f5ff,stroke:#0288d1,stroke-width:2px
    classDef service fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef monitoring fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    classDef disabled fill:#ffebee,stroke:#f44336,stroke-width:2px,stroke-dasharray: 5 5
    classDef mock fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    
    class MEXC,CLIENT external
    class WS,SIGNAL,RISK,EXEC service
    class REST disabled
    class REDIS,POSTGRES storage
    class PROM,GRAFANA monitoring
    class MOCK mock
```

---

## Event-Fluss im Detail

```mermaid
flowchart LR
    %% === Event Pipeline ===
    MD["📊 Marktdaten<br/>{symbol, price, volume, timestamp}"]
    SIG["🎯 Signale<br/>{symbol, side, strength, indicators}"]
    ORD["📝 Orders<br/>{order_id, symbol, side, quantity, price}"]
    RES["✅ Order-Ergebnisse<br/>{order_id, status, filled_at, entry_price}"]
    
    MD -->|"Signal-Engine<br/>Technische Analyse"| SIG
    SIG -->|"Risiko-Manager<br/>Positions-Check<br/>Risiko-Regeln"| ORD
    ORD -->|"Ausführungs-Service<br/>Mock Trading"| RES
    
    RES -.->|"Feedback-Schleife<br/>(zukünftig)"| SIG
    
    %% Styling
    classDef event fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    class MD,SIG,ORD,RES event
```

---

## Datenbank-Schema

```mermaid
flowchart TD
    %% === Tabellen ===
    ORDERS["📋 orders<br/>-----<br/>order_id (PK)<br/>symbol<br/>side (BUY/SELL)<br/>quantity<br/>price<br/>status<br/>submitted_at (bigint)<br/>filled_at (bigint)<br/>entry_price<br/>stop_loss<br/>take_profit<br/>strategy<br/>risk_score<br/>created_at"]
    
    TRADES["💼 trades<br/>-----<br/>trade_id (PK)<br/>order_id (FK)<br/>symbol<br/>entry_price<br/>entry_time (bigint)<br/>exit_price<br/>exit_time (bigint)<br/>profit_loss<br/>profit_loss_percent<br/>status<br/>created_at"]
    
    ORDERS -->|"1:N<br/>Fremdschlüssel"| TRADES
    
    %% Styling
    classDef table fill:#fff8e1,stroke:#f57c00,stroke-width:2px
    class ORDERS,TRADES table
```

---

## Health-Check Ablauf

```mermaid
flowchart TD
    START["🏥 Health-Check"]
    
    START --> CHECK_DB{"PostgreSQL<br/>Verbindung?"}
    CHECK_DB -->|"✅ OK"| CHECK_REDIS{"Redis<br/>Verbindung?"}
    CHECK_DB -->|"❌ Fehler"| UNHEALTHY["❌ 503<br/>Service nicht verfügbar"]
    
    CHECK_REDIS -->|"✅ OK"| CHECK_LOGS{"Logs<br/>schreibbar?"}
    CHECK_REDIS -->|"❌ Fehler"| UNHEALTHY
    
    CHECK_LOGS -->|"✅ OK"| HEALTHY["✅ 200 OK<br/>{status: 'healthy',<br/>uptime: 3600,<br/>version: '0.1.0'}"]
    CHECK_LOGS -->|"❌ Fehler"| UNHEALTHY
    
    %% Styling
    classDef success fill:#c8e6c9,stroke:#4caf50,stroke-width:2px
    classDef fail fill:#ffcdd2,stroke:#f44336,stroke-width:2px
    class HEALTHY success
    class UNHEALTHY fail
```

---

## Order-Verarbeitungs-Pipeline

```mermaid
flowchart TD
    %% === Order Flow ===
    START["📥 Order empfangen<br/>(Redis: orders)"]
    
    START --> VALIDATE{"🔍 Schema-<br/>Validierung"}
    VALIDATE -->|"❌ Ungültig"| REJECT["❌ LOG ERROR<br/>Order abgelehnt"]
    VALIDATE -->|"✅ Gültig"| SAVE_DB["💾 In DB speichern<br/>(status: PENDING)"]
    
    SAVE_DB --> MOCK_EXEC["🎭 Mock-Executor"]
    
    MOCK_EXEC --> RANDOM{"🎲 Zufall<br/>95% Erfolg"}
    RANDOM -->|"5% Fehler"| FAILED["❌ Status: FAILED<br/>filled_at: NULL"]
    RANDOM -->|"95% Erfolg"| FILLED["✅ Status: FILLED<br/>filled_at: Unix-Timestamp"]
    
    FAILED --> UPDATE_DB1["💾 DB aktualisieren"]
    FILLED --> UPDATE_DB2["💾 DB aktualisieren<br/>+ Trade erstellen"]
    
    UPDATE_DB1 --> PUBLISH1["📤 PUBLISH<br/>order_results"]
    UPDATE_DB2 --> PUBLISH2["📤 PUBLISH<br/>order_results"]
    
    PUBLISH1 --> END["🏁 Fertig"]
    PUBLISH2 --> END
    
    REJECT --> END
    
    %% Styling
    classDef success fill:#c8e6c9,stroke:#4caf50,stroke-width:2px
    classDef fail fill:#ffcdd2,stroke:#f44336,stroke-width:2px
    classDef process fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    
    class FILLED,UPDATE_DB2,PUBLISH2 success
    class FAILED,UPDATE_DB1,REJECT fail
    class START,SAVE_DB,MOCK_EXEC,PUBLISH1 process
```

---

## Deployment-Status (Docker Compose)

```mermaid
flowchart TD
    %% === Container-Zustände ===
    subgraph RUNNING["🟢 Läuft (8/9 Container)"]
        direction TB
        C1["redis<br/>✅ gesund"]
        C2["postgres<br/>✅ gesund"]
        C3["prometheus<br/>⚠️ ungesund<br/>(nicht blockierend)"]
        C4["grafana<br/>✅ gesund"]
        C5["bot_ws<br/>✅ gesund"]
        C6["signal_engine<br/>✅ gesund"]
        C7["risk_manager<br/>✅ gesund"]
        C8["execution_service<br/>✅ gesund"]
    end
    
    subgraph STOPPED["🔴 Gestoppt"]
        C9["bot_rest<br/>❌ deaktiviert"]
    end
    
    %% Styling
    classDef healthy fill:#c8e6c9,stroke:#4caf50,stroke-width:2px
    classDef unhealthy fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    classDef stopped fill:#ffcdd2,stroke:#f44336,stroke-width:2px
    
    class C1,C2,C4,C5,C6,C7,C8 healthy
class C3 unhealthy
    class C9 stopped
```

## Stateful Komponenten

- PostgreSQL (`cdb_postgres_data`)
- Redis (`cdb_redis_data`)
- Prometheus (`cdb_prom_data`)
- Grafana (`cdb_grafana_data`)

Diese Komponenten sind für Backup und Restore relevant (vgl. Backupspezifikation / `MANIFEST_BACKUP.json`).

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| 🌐 | Externe Datenquelle |
| 📊 | Datenerfassung |
| 🔴 | Nachrichtenbus (Redis) |
| ⚙️ | Verarbeitungs-Service |
| 🐘 | Datenbank (PostgreSQL) |
| 🎭 | Mock/Simulation |
| 📈 | Überwachung |
| ✅ | Gesund/Erfolgreich |
| ❌ | Fehler/Deaktiviert |
| ⚠️ | Warnung (nicht blockierend) |

---

## Nächste Schritte

1. **Grafana-Dashboard-Setup** (höchste Priorität)
2. **7-Tage Paper-Trading Test**
3. **Prometheus Health-Check Behebung** (optional)
4. **MEXC Testnet-Integration** (zukünftig)

---

**Dokumentiert:** 25. Oktober 2025  
**Agent:** GitHub Copilot  
**Projekt-Phase:** Phase 5 abgeschlossen (100% E2E-Tests erfolgreich)
