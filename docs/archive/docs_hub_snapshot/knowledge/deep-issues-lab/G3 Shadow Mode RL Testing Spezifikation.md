---
id: CDB-DR-G3
title: 'Shadow Mode RL Testing Framework'
subtitle: 'Spezifikation für die Validierung von RL-Agenten im Live-Betrieb'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Shadow Mode
  - Reinforcement Learning
  - Backtesting
  - A/B-Testing
  - Validierung
---

# Shadow Mode RL Testing Framework

> **Management Summary**
>
> Dieses Dokument spezifiziert das **Shadow Testing Framework**, eine entscheidende Komponente zur sicheren Validierung und zum Vergleich von Handelsstrategien – insbesondere von Reinforcement Learning (RL)-Agenten – im Live-Betrieb von *Claire de Binare*.
>
> Das Framework ermöglicht es, neue oder experimentelle Agenten (`rl_ppo_alpha`) parallel zu einer etablierten Basisstrategie (`baseline_heuristic`) laufen zu lassen. Die Aktionen der Agenten werden über einen **virtuellen Broker** simuliert, der realistische Marktbedingungen wie Gebühren, Slippage und Latenz berücksichtigt. Die Performance wird anhand definierter Metriken verglichen. Ein Beförderungsprozess (`promotion_criteria`) stellt sicher, dass ein neuer Agent nur dann in den Live-Handel überführt wird, wenn er seine Überlegenheit und Sicherheit über einen definierten Zeitraum bewiesen hat.

---

## 1. Virtueller Broker: Simulation realer Marktbedingungen

Um eine realitätsnahe Simulation zu gewährleisten, konfiguriert der virtuelle Broker die folgenden Markt-Frictions:

-   **Gebühren:**
    -   Maker-Gebühr (`fee_maker`): `-0.0001` (-0.01 %, eine übliche Rückvergütung).
    -   Taker-Gebühr (`fee_taker`): `0.0005` (0.05 %).
-   **Slippage:**
    -   Modell (`slippage_model`): `fixed_pct` (fester prozentualer Abschlag).
    -   Wert (`slippage_value`): `0.0002` (0.02 %).
-   **Latenz (`latency_simulation_ms`):** `50 ms`. Simuliert die durchschnittliche Verzögerung von der Order-Erstellung bis zur Ausführungsbestätigung.
-   **Startkapital (`initial_balance`):** `10,000.0`.

```json
{
  "virtual_broker_config": {
    "fee_maker": -0.0001,
    "fee_taker": 0.0005,
    "slippage_model": "fixed_pct",
    "slippage_value": 0.0002,
    "latency_simulation_ms": 50,
    "initial_balance": 10000.0
  }
}
```

## 2. Agenten-Konfiguration

Das Framework ist für den parallelen Betrieb und Vergleich mehrerer Agenten ausgelegt:

-   **Agent 1 (Herausforderer):**
    -   **ID:** `rl_ppo_alpha`
    -   **Modell:** Ein via ONNX exportiertes PPO-Modell (`models/ppo_v1.onnx`).
    -   **Typ:** `neural_network`.
    -   **Status:** `active: true`.
-   **Agent 2 (Baseline):**
    -   **ID:** `baseline_heuristic`
    -   **Typ:** Eine standardisierte Trendfolge-Strategie (`standard_trend_following`).
    -   **Status:** `active: true` und dient als Referenz (`reference_live: true`).

```json
{
  "agents": [
    {
      "id": "rl_ppo_alpha",
      "model_path": "models/ppo_v1.onnx",
      "policy_type": "neural_network",
      "active": true
    },
    {
      "id": "baseline_heuristic",
      "policy_type": "standard_trend_following",
      "active": true,
      "reference_live": true
    }
  ]
}
```

## 3. Vergleichs-Metriken (Performance-Bewertung)

Die Performance der Agenten wird anhand der folgenden Metriken verglichen:

-   **Primäre Metrik:** `sharpe_ratio_7d` (7-Tage Sharpe Ratio).
-   **Sekundäre Metriken:**
    -   `max_drawdown` (Maximaler Drawdown)
    -   `win_rate` (Gewinnrate)
    -   `profit_factor` (Profit-Faktor)
-   **Korrelationsfenster:** `100`. Misst die Korrelation der Entscheidungen über die letzten 100 Trades.

```json
{
  "comparison_metrics": {
    "primary": "sharpe_ratio_7d",
    "secondary": ["max_drawdown", "win_rate", "profit_factor"],
    "correlation_window": 100
  }
}
```

## 4. Beförderungskriterien (Promotion Criteria)

Ein neuer Agent wird nur dann für den Live-Betrieb "befördert", wenn er die folgenden, strengen Kriterien erfüllt:

-   **Minimale Laufzeit (`min_days_active`):** `14` Tage.
-   **Minimale Anzahl an Trades (`min_trades_count`):** `50`.
-   **Outperformance (`outperformance_pct`):** Muss die primäre Metrik (Sharpe Ratio) der Baseline um mindestens `5 %` übertreffen.
-   **Drawdown-Verhältnis (`max_drawdown_ratio`):** Der maximale Drawdown darf nicht höher sein als der der Baseline (`1.0`).
-   **Aktions-Übereinstimmung (`action_agreement_max`):** Die Aktionen dürfen zu maximal `75 %` mit der Baseline übereinstimmen, um sicherzustellen, dass der neue Agent einen echten Mehrwert und keine reine Kopie ist.

```json
{
  "promotion_criteria": {
    "min_days_active": 14,
    "min_trades_count": 50,
    "outperformance_pct": 0.05,
    "max_drawdown_ratio": 1.0,
    "action_agreement_max": 0.75
  }
}
```

## 5. Datenspeicherung

Alle im Shadow Mode generierten Daten werden für eine spätere Analyse persistent gespeichert:

-   **Trades:** In der Tabelle `shadow_trades`.
-   **Metriken:** In der Tabelle `shadow_metrics`.

```json
{
  "storage": {
    "trades_table": "shadow_trades",
    "metrics_table": "shadow_metrics"
  }
}
```

