---
id: CDB-DR-G2
title: 'Spezifikation für Volatilitäts-Stress-Szenarien'
subtitle: 'Generierung von Marktbedingungen für Robustheitstests'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Stresstest
  - Volatilität
  - Marktszenarien
  - Markov-Switching
  - GARCH
---

# Spezifikation für Volatilitäts-Stress-Szenarien

> **Management Summary**
>
> Dieses Dokument spezifiziert den **Stress-Generator**, ein Modul zur Erzeugung synthetischer, aber plausibler Markt-Stress-Szenarien. Ziel ist es, die Robustheit der Handelsstrategien und Risikomanagement-Systeme von *Claire de Binare* unter extremen Bedingungen zu testen.
>
> Die Methodik basiert auf einem **Markov-Switching GARCH-Modell**, das verschiedene Marktregime (z.B. "ruhig", "Trend", "Panik") mit jeweils unterschiedlichen Drift- und Volatilitätsparametern simuliert. Durch die Definition von Übergangswahrscheinlichkeiten zwischen diesen Regimen können komplexe Szenarien wie "Flash Crashs" oder langanhaltende Bärenmärkte ("Slow Bleed") nachgebildet werden, um die Belastbarkeit des Systems zu quantifizieren.

---

## 1. Methode: Markov-Switching GARCH

-   **Modell:** `markov_switching_garch`
-   **Funktionsweise:** Das Modell kombiniert ein **GARCH-Modell** zur Beschreibung der Volatilitäts-Clusterbildung mit einem **Markov-Switching-Modell**, um abrupte Wechsel zwischen verschiedenen Marktregimen zu ermöglichen. Jedes Regime hat seine eigenen GARCH-Parameter.

## 2. Regime-Definitionen

Drei grundlegende Marktregime werden definiert, um ein breites Spektrum von Marktbedingungen abzudecken:

### 2.1. REGIME_0_CALM (Ruhiger Markt)

-   **Drift (`mu_drift`):** `0.0` (keine gerichtete Bewegung).
-   **Basis-Volatilität (`sigma_base`):** `0.002` (sehr niedrig).
-   **GARCH-Parameter:** Niedrige Reaktion auf Schocks (`garch_alpha: 0.05`), hohe Persistenz der Volatilität (`garch_beta: 0.90`).

### 2.2. REGIME_1_TREND (Trend-Markt)

-   **Drift (`mu_drift`):** `0.0010` (leichter positiver Trend).
-   **Basis-Volatilität (`sigma_base`):** `0.008` (moderat).
-   **GARCH-Parameter:** Moderate Reaktion auf Schocks (`garch_alpha: 0.10`).

### 2.3. REGIME_2_PANIC (Panik-Markt)

-   **Drift (`mu_drift`):** `-0.0050` (starker negativer Drift).
-   **Basis-Volatilität (`sigma_base`):** `0.030` (sehr hoch).
-   **GARCH-Parameter:** Starke Reaktion auf Schocks (`garch_alpha: 0.20`), geringere Persistenz (`garch_beta: 0.70`).
-   **Spread-Multiplikator:** `5.0` (Bid-Ask-Spreads werden um den Faktor 5 erweitert, um Illiquidität zu simulieren).

## 3. Übergangsmatrix (Transition Matrix)

Die Matrix definiert die Wahrscheinlichkeit eines Wechsels von einem Regime in ein anderes pro Zeitschritt. Die hohe Wahrscheinlichkeit auf der Diagonalen (`0.90`, `0.90`, `0.80`) sorgt für eine gewisse Persistenz der Regime.

```json
"transition_matrix_default": [
  [0.90, 0.09, 0.01],  // Von Ruhig zu [Ruhig, Trend, Panik]
  [0.05, 0.90, 0.05],  // Von Trend zu [Ruhig, Trend, Panik]
  [0.10, 0.10, 0.80]   // Von Panik zu [Ruhig, Trend, Panik]
]
```

## 4. Vordefinierte Stress-Szenarien

### 4.1. Flash Crash (V-Shape)

-   **Sequenz:**
    1.  `REGIME_0_CALM` (100 Zeitschritte)
    2.  `REGIME_2_PANIC` (15 Zeitschritte)
    3.  `REGIME_1_TREND` (50 Zeitschritte)
-   **Beschreibung:** Simuliert einen plötzlichen, scharfen Markteinbruch, gefolgt von einer schnellen Erholung. Testet die Reaktionsfähigkeit der Circuit Breaker und die Fähigkeit, von der Erholung zu profitieren.

### 4.2. Slow Bleed Death (Langanhaltender Bärenmarkt)

-   **Sequenz:**
    1.  `REGIME_1_TREND` (20 Zeitschritte)
    2.  `REGIME_2_PANIC` (2 Zeitschritte als "Trigger")
    3.  Modifiziertes `REGIME_2_PANIC` (500 Zeitschritte) mit überschriebenem Drift (`-0.001`) und reduzierter Volatilität (`0.01`).
-   **Beschreibung:** Simuliert einen langen, zermürbenden Bärenmarkt mit konstantem, leicht negativem Drift. Testet die Fähigkeit des Systems, Verluste über einen langen Zeitraum zu begrenzen und nicht in "Chop"-Märkten kontinuierlich Kapital zu verbrennen.

## 5. Impact-Metriken

Die Ergebnisse der Stress-Szenarien werden anhand der folgenden Metriken bewertet:

-   **Benötigter Überlebenspuffer (`required_survival_buffer_pct`):** `20 %`. Das System muss das Szenario überleben, ohne mehr als 80 % seines Kapitals zu verlieren.
-   **Maximales Drawdown-Limit (`max_drawdown_limit_pct`):** `15 %`. Der während des Tests erlittene maximale Drawdown darf 15 % nicht überschreiten.

```json
{
  "impact_metrics": {
    "required_survival_buffer_pct": 0.20,
    "max_drawdown_limit_pct": 0.15
  }
}
```

