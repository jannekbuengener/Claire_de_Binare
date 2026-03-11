---
id: CDB-DR-F3
title: 'Risiko-KPIs als Systemweite Metriken'
subtitle: 'Spezifikation für Definition, Routing und Alarmierung von Risiko-Leistungskennzahlen'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Risiko-KPIs
  - Metriken
  - Monitoring
  - Prometheus
  - TimescaleDB
  - Alerting
---

# Risiko-KPIs als Systemweite Metriken

> **Management Summary**
>
> Dieses Dokument spezifiziert das Modul **`risk_metrics`**, das für die Definition, Berechnung und Verteilung systemweiter Risiko-Leistungskennzahlen (KPIs) im *Claire de Binare*-System verantwortlich ist. Ziel ist es, ein robustes Monitoring- und Alarmierungssystem zu etablieren, das in Echtzeit über den Gesundheitszustand des Handelssystems informiert.
>
> Die Architektur basiert auf einer **hybriden Push/Pull-Pipeline**. Kritische Metriken werden über einen "Fast Path" ereignisgesteuert in Redis für Echtzeit-Zugriffe bereitgestellt, während sie für historische Analysen aggregiert über einen "Slow Path" in einer TimescaleDB gespeichert werden. Ein Regelwerk für die Alarmierung stellt sicher, dass bei Überschreitung kritischer Schwellenwerte automatisch Aktionen ausgelöst werden (z.B. Benachrichtigungen, Umschaltung in einen defensiven Modus).

---

## 1. Pipeline-Architektur

-   **Typ:** `hybrid_push_pull`. Eine Kombination aus ereignisgesteuerten Updates (Push) und aggregierten Batches (Pull).
-   **Fast Path:**
    -   **Ziel:** Redis.
    -   **Update-Frequenz:** Ereignisgesteuert (`event_driven`).
    -   **Zweck:** Bereitstellung von Echtzeit-Metriken für latenzkritische Komponenten.
    -   **Key-Muster:** `metrics:risk:{scope}`
-   **Slow Path:**
    -   **Ziel:** TimescaleDB (eine Zeitreihen-Datenbank auf PostgreSQL-Basis).
    -   **Update-Frequenz:** Aggregiert pro Minute (`1m_aggregate`).
    -   **Zweck:** Historische Analyse und langfristiges Monitoring.
    -   **Tabelle:** `risk_metrics_1m`

```json
{
  "module": "risk_metrics",
  "pipeline_type": "hybrid_push_pull",
  "routing_rules": {
    "fast_path": {
      "target": "redis",
      "key_pattern": "metrics:risk:{scope}",
      "update_frequency": "event_driven"
    },
    "slow_path": {
      "target": "timescale",
      "table": "risk_metrics_1m",
      "update_frequency": "1m_aggregate"
    }
  }
}
```

## 2. Definition der Risiko-Metriken (KPIs)

Die folgenden KPIs werden als zentrale Messgrößen für das Risikomanagement definiert:

### 2.1. `drawdown_pct` (Maximaler Drawdown in Prozent)

-   **Typ:** `gauge` (ein einzelner Wert, der steigen und fallen kann).
-   **Quelle:** `equity_calc` (aus der Equity-Kurven-Berechnung).
-   **Beschreibung:** Prozentualer Rückgang vom letzten "High Water Mark" (Höchststand des Portfolios).
-   **Kritische Schwelle:** `-0.10` (10 %).

### 2.2. `exposure_ratio` (Exposure-Verhältnis)

-   **Typ:** `gauge`.
-   **Quelle:** `position_sum` (Summe der Positionen).
-   **Beschreibung:** Verhältnis des gesamten gehebelten Positionswertes (`Total Notional Value`) zum Eigenkapital (`Equity`).
-   **Warn-Schwelle:** `2.5` (Hebel von 2.5x).
-   **Kritische Schwelle:** `5.0` (Hebel von 5x).

### 2.3. `approval_rate_1h` (Genehmigungsrate pro Stunde)

-   **Typ:** `histogram` (verteilte Messwerte).
-   **Quelle:** `risk_engine_events`.
-   **Beschreibung:** Verhältnis der von der Risk Engine akzeptierten zu den abgelehnten Orders.
-   **Buckets:** `[0.1, 0.5, 0.9]` (Messintervalle für das Histogramm).

### 2.4. `var_95_1h` (Value at Risk)

-   **Typ:** `gauge`.
-   **Quelle:** `timescale_aggregation` (Berechnung in der Datenbank).
-   **Beschreibung:** Value at Risk mit 95 % Konfidenz über einen 1-Stunden-Horizont.
-   **Berechnung:** `parametric_ewma` (parametrisch mittels EWMA-Volatilität).

```json
"metric_definitions": {
  "drawdown_pct": {
    "type": "gauge",
    "source": "equity_calc",
    "description": "Percentage decline from High Water Mark",
    "critical_threshold": -0.10
  },
  "exposure_ratio": {
    "type": "gauge",
    "source": "position_sum",
    "description": "Total Notional Value / Equity",
    "warning_threshold": 2.5,
    "critical_threshold": 5.0
  },
  "approval_rate_1h": {
    "type": "histogram",
    "source": "risk_engine_events",
    "description": "Ratio of accepted vs. rejected orders",
    "bucket_sizes": [0.1, 0.5, 0.9]
  },
  "var_95_1h": {
    "type": "gauge",
    "source": "timescale_aggregation",
    "description": "Value at Risk (95% Conf, 1h Horizon)",
    "calculation": "parametric_ewma"
  }
}
```

## 3. Alarmierungs-Regeln (Alerting)

Die folgenden Regeln definieren automatische Aktionen bei der Überschreitung von Schwellenwerten:

-   **Drawdown-Warnung:**
    -   **Bedingung:** `drawdown_pct < -0.05` (5 % Drawdown).
    -   **Stufe:** `warning`.
    -   **Aktion:** Benachrichtigung an einen Slack-Kanal (`notify_slack`).

-   **Drawdown-Kritisch:**
    -   **Bedingung:** `drawdown_pct < -0.10` (10 % Drawdown).
    -   **Stufe:** `critical`.
    -   **Aktion:** Automatisches Umschalten des Handelsprofils auf "defensiv" (`trigger_profile_defensive`).

-   **Metriken-Verzögerung:**
    -   **Bedingung:** `metrics_staleness_sec > 15` (Metriken sind älter als 15 Sekunden).
    -   **Stufe:** `critical`.
    -   **Aktion:** Automatisches Pausieren des gesamten Systems (`system_pause`), da der Systemzustand als unsicher gilt.

```json
{
  "alerting_rules": [
    {
      "condition": "drawdown_pct < -0.05",
      "severity": "warning",
      "action": "notify_slack"
    },
    {
      "condition": "drawdown_pct < -0.10",
      "severity": "critical",
      "action": "trigger_profile_defensive"
    },
    {
      "condition": "metrics_staleness_sec > 15",
      "severity": "critical",
      "action": "system_pause"
    }
  ]
}
```

