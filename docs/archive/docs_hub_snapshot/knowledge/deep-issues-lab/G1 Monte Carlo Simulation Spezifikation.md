---
id: CDB-DR-G1
title: 'Monte-Carlo-Simulations-Engine'
subtitle: 'Spezifikation für die stochastische Pfadsimulation von Trading-Strategien'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Monte Carlo
  - JAX
  - Simulation
  - Merton Jump Diffusion
  - Risikomanagement
---

# Monte-Carlo-Simulations-Engine

> **Management Summary**
>
> Dieses Dokument spezifiziert das Design und die Konfiguration der **Monte-Carlo-Simulations-Engine**, einer Kernkomponente für das Backtesting und die Risikobewertung von Trading-Strategien im *Claire de Binare*-System.
>
> Die Engine nutzt **JAX** als hochperformantes Backend, um eine große Anzahl von Preis-Pfaden zu simulieren. Als zugrundeliegender stochastischer Prozess wird ein **Merton-Sprungdiffusionsmodell** verwendet, das sowohl normale Marktschwankungen (Brownsche Bewegung) als auch plötzliche, extreme Ereignisse (Jumps) abbildet. Die Simulationen werden verwendet, um die Verteilung potenzieller Ergebnisse einer Handelsstrategie (z.B. Endkapital, maximaler Drawdown) zu bewerten und so eine robuste Risikoabschätzung zu ermöglichen.

---

## 1. Technologischer Stack

-   **Backend:** `jax`. JAX wird aufgrund seiner Fähigkeit zur Just-in-Time (JIT)-Kompilierung und massiven Parallelisierung auf GPUs/TPUs ausgewählt, um die rechenintensiven Simulationen zu beschleunigen.
-   **Genauigkeit:** `float32`. Bietet einen guten Kompromiss zwischen numerischer Präzision und Performance.

```json
{
  "module": "monte_carlo_engine",
  "backend": "jax",
  "precision": "float32"
}
```

## 2. Stochastischer Prozess: Merton-Sprungdiffusion

Um realistische Marktbedingungen, insbesondere in volatilen Kryptomärkten, abzubilden, wird ein **Merton-Sprungdiffusionsmodell** verwendet.

-   **Typ:** `MERTON_JUMP_DIFFUSION`
-   **Parameter:**
    -   `mu`: Drift des Prozesses (hier: `0.0`, Annahme eines driftlosen Prozesses).
    -   `sigma`: Volatilität, wird **dynamisch** aus den historischen Daten der letzten `90` Tage kalibriert.
    -   `lambda_jumps_per_year`: Erwartete Anzahl von Sprüngen pro Jahr (`12`).
    -   `jump_mean_pct`: Erwarteter Mittelwert eines Sprungs (`-0.08` oder -8 %).
    -   `jump_std_pct`: Standardabweichung der Sprunggröße (`0.05` oder 5 %).

```json
{
  "stochastic_process": {
    "type": "MERTON_JUMP_DIFFUSION",
    "parameters": {
      "mu": 0.0,
      "sigma": "dynamic_from_history",
      "lambda_jumps_per_year": 12,
      "jump_mean_pct": -0.08,
      "jump_std_pct": 0.05
    },
    "calibration_window_days": 90
  }
}
```

## 3. Simulations-Spezifikationen

-   **Anzahl der Pfade (`num_paths`):** `10,000`. Eine ausreichende Anzahl, um eine statistisch signifikante Verteilung der Ergebnisse zu erhalten.
-   **Horizont (`horizon_steps`):** `1440` Schritte.
-   **Zeitschritt (`step_size`):** `1h`. Die Simulation modelliert die Preisentwicklung über 1440 Stunden (60 Tage).
-   **Batch-Größe (`batch_size`):** `5000`. Die Simulation wird in Batches von 5000 Pfaden parallel auf der GPU ausgeführt, um den Speicher effizient zu nutzen.

```json
{
  "simulation_specs": {
    "num_paths": 10000,
    "horizon_steps": 1440,
    "step_size": "1h",
    "batch_size": 5000
  }
}
```

## 4. Policy Snapshot (Handelsstrategie)

Die zu testende Handelsstrategie wird durch einen "Snapshot" ihrer wichtigsten Risikoparameter definiert:

-   **Stop Loss:** `-0.02` (-2 %).
-   **Take Profit:** `0.05` (+5 %).
-   **Trailing Stop Aktivierung:** `0.01` (Trailing Stop wird aktiviert, wenn die Position 1 % im Gewinn ist).
-   **Maximaler Drawdown (Hard Stop):** `-0.10` (-10 %). Bei Erreichen dieses Drawdowns wird die Simulation für diesen Pfad beendet.

```json
{
  "policy_snapshot": {
    "stop_loss_pct": -0.02,
    "take_profit_pct": 0.05,
    "trailing_stop_activation": 0.01,
    "max_drawdown_hard_stop": -0.10
  }
}
```

## 5. Output-Metriken und Ressourcen

-   **Output-Metriken:** Die Simulationsergebnisse werden als Verteilung (Histogramm-Buckets) der folgenden Zielgrößen ausgegeben:
    -   `final_equity` (Endkapital)
    -   `max_drawdown` (Maximaler Drawdown)
    -   `sharpe_ratio` (Sharpe Ratio)
-   **Perzentile:** Es werden die Perzentile `1, 5, 25, 50, 75, 95, 99` berechnet, um ein vollständiges Bild der Risiken (insbesondere Tail-Risiken) zu erhalten.
-   **Ressourcen-Limits:**
    -   **Maximaler Speicher:** `4 GB`.
    -   **GPU-Nutzung:** `true`, wenn verfügbar.

```json
{
  "output_metrics": {
    "percentiles": [1, 5, 25, 50, 75, 95, 99],
    "targets": ["final_equity", "max_drawdown", "sharpe_ratio"],
    "export_format": "histogram_buckets"
  },
  "resource_limits": {
    "max_memory_gb": 4,
    "use_gpu_if_available": true
  }
}
```

