---
id: CDB-DR-F1
title: 'Feature Store Spezifikation'
subtitle: 'Design für die zentrale Verwaltung und Bereitstellung von Handels-Features'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Feature Store
  - Architektur
  - Daten-Pipeline
  - Redis
  - PostgreSQL
---

# Feature Store Spezifikation

> **Management Summary**
>
> Dieses Dokument spezifiziert das Design und die Implementierung eines **Feature Stores** für das *Claire de Binare* Trading-System. Ein Feature Store ist eine zentrale Komponente, die Trading-Features (z.B. technische Indikatoren) konsistent, versioniert und performant für Trainings- und Inferenz-Zwecke bereitstellt.
>
> Die vorgeschlagene Architektur basiert auf einer **hybriden Speicherung** mit Redis für den Online-Zugriff (geringe Latenz) und PostgreSQL für die Offline-Analyse (historische Daten). Die Feature-Berechnung wird durch eine asynchrone Pipeline getriggert, die auf `market_candles_1m` aus einem Redis Stream lauscht. Das Design stellt sicher, dass sowohl die Trainings- als auch die Inferenz-Pipelines auf dieselben, konsistenten Feature-Werte zugreifen, was das "Training-Serving Skew"-Problem vermeidet.

---

## 1. Architektur und Pipeline-Spezifikation

-   **Implementierung:** Eigenentwicklung (`custom_redis_postgres`), um volle Kontrolle über die Daten-Pipeline und Speicherformate zu gewährleisten.
-   **Trigger:** Die Feature-Berechnung wird ereignisgesteuert durch neue 1-Minuten-Marktdaten (`market_candles_1m`) aus einem Redis Stream ausgelöst.
-   **Verarbeitung:** Die Pipeline läuft mit einer konkurrierenden Verarbeitung von 4 parallelen Konsumenten (`concurrency: 4`), um einen hohen Durchsatz zu gewährleisten.

```json
{
  "module": "feature_store",
  "implementation": "custom_redis_postgres",
  "pipeline_spec": {
    "trigger": "redis_stream:market_candles_1m",
    "processing_window": "stream_consumer",
    "concurrency": 4
  }
}
```

## 2. Datenhaltung und Speicher-Policy

-   **Online-Speicher (Redis):** Features für den Echtzeit-Zugriff (Inferenz) werden für 1 Stunde (`3600` Sekunden) in Redis vorgehalten, um extrem niedrige Latenzen zu garantieren.
-   **Offline-Speicher (PostgreSQL):** Historische Feature-Daten für Trainings- und Analysezwecke werden für 12 Monate aufbewahrt.

```json
{
  "data_windows": {
    "online_retention_ttl_sec": 3600,
    "offline_retention_policy": "12_months"
  }
}
```

## 3. Feature-Definitionen

Die Features sind in logische Gruppen unterteilt und über eine JSON-Konfiguration definiert. Dies ermöglicht eine flexible Erweiterung und Wartung.

### 3.1. Momentum-Features

```json
"momentum_group": [
  {
    "name": "rsi_14",
    "function": "talib.RSI",
    "params": {"timeperiod": 14},
    "dtype": "float32"
  },
  {
    "name": "macd_diff",
    "function": "cdb.features.custom_macd_diff",
    "params": {"fast": 12, "slow": 26, "signal": 9},
    "dtype": "float32"
  }
]
```

### 3.2. Volatilitäts-Features

```json
"volatility_group": [
  {
    "name": "atr_norm_14",
    "function": "cdb.features.normalized_atr",
    "params": {"timeperiod": 14},
    "dtype": "float32",
    "description": "ATR divided by Close price * 100"
  },
  {
    "name": "bb_width_20",
    "function": "cdb.features.bb_width",
    "params": {"timeperiod": 20, "nbdev": 2.0},
    "dtype": "float32"
  }
]
```

### 3.3. Metadaten-Features

Metadaten wie das aktuelle Marktregime werden aus dem Systemzustand (Redis) in den Feature-Vektor integriert.

```json
"metadata": [
  {
    "name": "market_regime",
    "source": "redis_key:market_state:{symbol}",
    "dtype": "int8"
  }
]
```

## 4. Service Level Agreements (SLAs) und Zugriffsmuster

### 4.1. Latenz-Anforderungen

-   **Maximale Berechnungszeit:** Die Berechnung aller Features für einen neuen Datenpunkt darf maximal **10 ms** dauern.
-   **Maximale Ingest-Verzögerung:** Die Verzögerung von der Ankunft der Marktdaten bis zur Verfügbarkeit des Features im Store darf **50 ms** nicht überschreiten.

```json
{
  "latency_sla": {
    "max_calculation_ms": 10,
    "max_ingest_lag_ms": 50
  }
}
```

### 4.2. Zugriffsmuster

-   **Training:** Der Zugriff für das Modelltraining erfolgt über SQL-Abfragen auf die historische PostgreSQL-Datenbank.
    ```sql
    SELECT * FROM features_{frame}_v1 WHERE time BETWEEN :start AND :end
    ```

-   **Inferenz:** Der Zugriff für die Echtzeit-Inferenz erfolgt über `HGETALL`-Befehle auf die Redis-Hashes, um minimale Latenz zu garantieren.
    ```
    HGETALL fs:{symbol}:{frame}:v1
    ```

Dieses Design stellt sicher, dass der Feature Store sowohl die hohen Performance-Anforderungen des Live-Tradings als auch die Flexibilität für Offline-Analysen und Modelltraining erfüllt.

