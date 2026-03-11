---
id: CDB-DR-F2
title: 'Market State Replay Layer'
subtitle: 'Spezifikation für die Aufzeichnung und das Replay von Marktdaten für Backtesting und Simulation'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Replay-Layer
  - Backtesting
  - Simulation
  - Parquet
  - Gymnasium
---

# Market State Replay Layer

> **Management Summary**
>
> Dieses Dokument spezifiziert den **Market State Replay Layer**, eine kritische Komponente für das Backtesting, die Simulation und das Training von RL-Agenten im *Claire de Binare*-System. Der Layer ist dafür verantwortlich, relevante System-Events persistent aufzuzeichnen und sie bei Bedarf deterministisch wiederzugeben.
>
> Die Architektur sieht die Aufzeichnung wichtiger Event-Streams in komprimierten **Parquet-Dateien** vor. Eine **Replay Engine** ermöglicht das "Abspielen" dieser historischen Daten in verschiedenen Modi (Echtzeit, Turbo, Schritt-für-Schritt). Zusätzlich wird ein Mechanismus zur automatisierten Extraktion spezifischer Marktszenarien (z.B. Drawdown-Phasen, Volatilitätsspitzen) für das Training von `gymnasium`-Umgebungen definiert.

---

## 1. Speicherformat und Rotation

-   **Speicherformat:** `parquet`. Bietet spaltenorientierte Speicherung, die für analytische Abfragen hocheffizient ist.
-   **Kompression:** `snappy`. Bietet einen guten Kompromiss zwischen hoher Kompressionsrate und schneller Lese-/Schreibgeschwindigkeit.
-   **File-Rotation-Policy:** Um die Dateigrößen handhabbar zu halten, werden die Logs rotiert:
    -   **Intervall:** Jede Stunde (`60` Minuten).
    -   **Maximale Dateigröße:** `500 MB`.
    -   **Namensmuster:** `cdb_events_{year}{month}{day}_{hour}.parquet`.

```json
{
  "module": "market_replay",
  "storage_format": "parquet",
  "compression": "snappy",
  "file_rotation_policy": {
    "interval_minutes": 60,
    "max_file_size_mb": 500,
    "naming_pattern": "cdb_events_{year}{month}{day}_{hour}.parquet"
  }
}
```

## 2. Aufzuzeichnende Event-Topics

Um eine vollständige Rekonstruktion des Systemzustands zu ermöglichen, werden folgende Event-Streams aufgezeichnet:

-   `market_data:*:candle:1m` (1-Minuten-Kerzen für alle Symbole)
-   `market_data:*:ticker` (Alle Ticker-Daten)
-   `market_data:*:depth_snapshot` (Snapshots des Orderbuchs)
-   `signals:*:output` (Alle generierten Handelssignale)
-   `risk:*:decision` (Alle Entscheidungen der Risk Engine)
-   `system:regime_change` (Alle erkannten Marktregime-Wechsel)

```json
{
  "topics_to_record": [
    "market_data:*:candle:1m",
    "market_data:*:ticker",
    "market_data:*:depth_snapshot",
    "signals:*:output",
    "risk:*:decision",
    "system:regime_change"
  ]
}
```

## 3. Replay Engine Spezifikation

Die Replay Engine ist das Herzstück des Backtesting-Frameworks. Sie liest die Parquet-Dateien und publiziert die historischen Events erneut auf dem Message Bus, als ob sie in Echtzeit geschehen würden.

-   **Replay-Modi:**
    1.  `realtime`: Spielt die Events mit ihrem originalen Zeitstempelabstand ab.
    2.  `turbo`: Spielt die Events so schnell wie möglich ab (für schnelle Backtests).
    3.  `step_by_step`: Pausiert nach jedem Event und wartet auf ein Kommando, um fortzufahren (für Debugging).
-   **Uhr-Quelle (`clock_source`):** Eine `virtual_event_time` sorgt dafür, dass das gesamte System die Zeitstempel der wiedergegebenen Events nutzt, um deterministisches Verhalten zu garantieren.
-   **Mock Execution:** `mock_execution: true` stellt sicher, dass während des Replays keine echten Orders an eine Börse gesendet werden.

```json
{
  "replay_engine_spec": {
    "modes": ["realtime", "turbo", "step_by_step"],
    "clock_source": "virtual_event_time",
    "mock_execution": true
  }
}
```

## 4. Extraktion von Trainings-Szenarien für Gymnasium

Für das Training von Reinforcement-Learning-Agenten ist es essenziell, interessante oder schwierige Marktphasen gezielt extrahieren zu können.

-   **Trigger-Bedingungen:** Definieren, welche Ereignisse eine interessante Trainings-Episode darstellen.
    -   `drawdown_pct >= 0.03`: Extrahiere Szenarien, in denen ein Drawdown von 3% oder mehr auftrat.
    -   `volatility_atr_spike >= 3.0`: Extrahiere Szenarien, in denen die Volatilität (gemessen am ATR) um den Faktor 3 anstieg.
-   **Fenstergröße (`window_size`):** Für jeden Trigger wird ein Fenster von `60` Minuten vor und `60` Minuten nach dem Ereignis extrahiert, um dem Agenten den vollen Kontext zu geben.
-   **Output:** Die extrahierten Szenarien werden in einem separaten Verzeichnis (`data/training_scenarios/`) gespeichert, um sie direkt in `gymnasium`-Umgebungen laden zu können.

```json
{
  "gym_scenario_extraction": {
    "trigger_conditions": [
      "drawdown_pct >= 0.03",
      "volatility_atr_spike >= 3.0"
    ],
    "window_size": {
      "pre_event_minutes": 60,
      "post_event_minutes": 60
    },
    "output_path": "data/training_scenarios/"
  }
}
```

