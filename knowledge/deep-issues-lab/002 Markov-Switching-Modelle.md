---
id: CDB-DR-002
title: 'Analyse von Marktregimen mit HMM'
subtitle: 'Integration von Markov-Switching-Modellen in autonome Handelssysteme'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Refactored'
tags:
  - HMM
  - MSM
  - Marktregime
  - Signal-Engine
  - Architektur
---

# Analyse von Marktregimen mit Hidden Markov Models (HMM)

> **Management Summary**
>
> Dieses Dokument analysiert die Anwendung von Hidden Markov Models (HMM) und Markov-Switching-Modellen (MSM) zur Erkennung von Marktregimen (z.B. Bullen-, Bären-, Seitwärtsphasen) im Krypto-Handel. Ziel ist es, die Performance des Trading-Bots *Claire de Binare* durch adaptive, regime-abhängige Strategien zu verbessern.
>
> Die Analyse umfasst die Methodik, den Modellaufbau, die Datenanforderungen und die Kriterien zur Modellbewertung. Als Ergebnis wird die Implementierung eines eigenständigen **"Regime Engine"-Microservice** empfohlen, der nahtlos in die bestehende Docker- und Redis-basierte Architektur integriert wird. Dieser Ansatz gewährleistet lose Kopplung, Skalierbarkeit und Wartbarkeit, ohne die Latenzanforderungen des Systems zu verletzen.

---

## 1. Problemstellung: Statische Strategien in dynamischen Märkten

In volatilen Finanzmärkten wechseln Phasen mit unterschiedlichen Charakteristika – sogenannte **Marktregime** – einander ab. Typische Regime sind Bullenmärkte, Bärenmärkte und  Für KI-gestützte Trading-Bots wie *Claire de Binare* ist es entscheidend, diese Regimewechsel frühzeitig zu erkennen, da eine starre Handelsstrategie nicht in allen Marktumgebungen gleichermaßen funktioniert. Ein adaptiver Ansatz, der je nach Marktregime unterschiedliche Strategien oder Parameter wählt, kann die Performance deutlich verbessern.[^3, ^4]

Dieses Deep Research untersucht, wie stochastische Marktregime mittels HMM und MSM modelliert und in die Microservice-Architektur eines Trading-Bots integriert werden können.

## 2. Methodik: HMM und MSM zur Regime-Erkennung

### 2.1. Hidden Markov Models (HMM)

HMMs bieten einen probabilistischen Rahmen, um **zeitliche Sequenzen mit verborgenen Zuständen** zu modellieren.[^5] Ein HMM besteht aus:
1.  Einer endlichen Menge **versteckter Zustände** (die Marktregime).
2.  **Übergangswahrscheinlichkeiten** zwischen diesen Zuständen (*Transition-Matrix*).
3.  **Emissionswahrscheinlichkeiten**, welche die Verteilung der beobachteten Daten (z.B. Preisrenditen) in jedem Zustand beschreiben.[^6, ^7]

Im Finanzkontext können HMMs verborgene Marktregime wie volatile vs. ruhige Phasen oder Auf- vs. Abwärtstrends statistisch identifizieren, ohne dass diese vorab explizit markiert werden müssen.[^10, ^11]

### 2.2. Markov-Switching-Modelle (MSM)

MSMs sind eng mit HMMs verwandt und werden in der Ökonometrie verwendet, um strukturelle Wechsel in Zeitreihen abzubilden. Technisch können MSMs als Sonderfall von HMMs aufgefasst werden, bei denen die Parameter eines Zeitreihenmodells (z.B. ein AR-GARCH-Modell) je nach Regime variieren.[^12]

Für unsere Zwecke – das Erkennen von Trend-, Seitwärts- und Volatilitätsphasen – eignen sich HMMs besonders gut, da sie flexibler sind und die Regime nicht exakt vordefiniert werden müssen. Empirische Studien bestätigen, dass HMMs bei Krypto-Daten Übergänge zwischen bullischen, bearischen und neutralen Phasen zuverlässig erkennen können.[^16]

## 3. Modellierung und Implementierung

### 3.1. Modellaufbau

Die Struktur eines HMM wird durch drei zentrale Entscheidungen bestimmt:

1.  **Anzahl der Regime:** In der Praxis genügen oft 2 bis 3 Zustände (z.B. *bullisch*, *bearisch*, *neutral*). Die optimale Anzahl wird mithilfe von Informationskriterien wie **AIC** und **BIC** ermittelt, um Overfitting zu vermeiden.[^15, ^18]
2.  **Emissionsfunktionen:** Beschreiben die statistische Verteilung der Beobachtungen (z.B. Renditen) pro Regime. Gängig sind **Gaußsche Normalverteilungen**, bei denen jedes Regime einen eigenen Mittelwert (Drift) und eine eigene Varianz (Volatilität) besitzt.
3.  **Übergangsmatrix:** Definiert die Wahrscheinlichkeit eines Wechsels von einem Regime in ein anderes. In Finanzmärkten zeigt sich oft **Regime-Persistenz**, d.h., die Wahrscheinlichkeit, in einem Zustand zu bleiben, ist hoch.

**Empfehlung für den Start:** Ein Modell mit **3 Zuständen**, Gaußschen Emissionen und einer initial leicht persistenten Übergangsmatrix.

### 3.2. Training und Daten

-   **Trainingsverfahren:** Die Modellparameter werden typischerweise durch **Maximum-Likelihood** unter Verwendung des **Baum-Welch-Algorithmus** (eine Form des Expectation-Maximization-Algorithmus) geschätzt.[^21]
-   **Trainingsdaten:** Die Auswahl und Aufbereitung der Daten ist erfolgsentscheidend. Für Krypto-Märkte empfehlen sich:
    -   **Features:** Log-Returns der Preise und ein Maß für die kurzfristige Volatilität (z.B. rollierende Standardabweichung).[^27] Zusätzliche Features wie Handelsvolumen oder technische Indikatoren (RSI) sind denkbar.
    -   **Datenquelle:** Historische Zeitreihen (z.B. 1-Stunden- oder 4-Stunden-Intervalle) über einen langen Zeitraum (3-5 Jahre), um mehrere Regimezyklen abzudecken.
    -   **Aufbereitung:** Die Features müssen normalisiert (standardisiert) werden, um eine vergleichbare Skalierung zu gewährleisten.

### 3.3. Modellbewertung

Die Güte des Modells wird anhand mehrerer Kriterien bewertet:
-   **Log-Likelihood, AIC & BIC:** Zur Beurteilung der Anpassungsgüte und zur Auswahl der Modellkomplexität.
-   **Regime-Plausibilität:** Eine visuelle Prüfung, ob die erkannten Regime mit bekannten Marktphasen (z.B. dem Bullenmarkt 2021) übereinstimmen.
-   **Out-of-Sample-Tests:** Der wichtigste Test, der prüft, ob das Modell auf neuen, ungesehenen Daten verlässliche Vorhersagen trifft. Eine **Walk-Forward-Validierung** ist hierfür die beste Methode.

## 4. Systemarchitektur und Integration

Wir empfehlen die Integration als **eigenständiger "Regime Engine"-Microservice**, anstatt die Logik in die bestehende Signal Engine einzubetten.

### 4.1. Architektur der "Regime Engine"

1.  **Abonnieren:** Der Service abonniert den `market_data`-Stream von Redis.
2.  **Verarbeiten:** Für jede neue Beobachtung wird die aktuelle Regime-Wahrscheinlichkeit mittels des trainierten HMMs berechnet.
3.  **Publizieren:** Bei einem Regimewechsel (oder in festen Intervallen) publiziert der Service ein Event auf einem neuen Redis-Kanal, z.B. `market_regime`.

**Beispiel für ein `market_regime`-Event:**
```json
{
  "type": "market_regime",
  "symbol": "BTC_USDT",
  "regime": "BULLISH",
  "probabilities": {"BULLISH": 0.85, "BEARISH": 0.10, "NEUTRAL": 0.05},
  "timestamp": 1736556000
}
```

### 4.2. Vorteile des Microservice-Ansatzes

-   **Lose Kopplung:** Die Regime-Berechnung ist gekapselt. Ein Ausfall beeinflusst nicht das restliche System.
-   **Skalierbarkeit:** Der Service kann bei hoher Rechenlast unabhängig skaliert werden.
-   **Wartbarkeit:** Änderungen am Regime-Modell erfordern kein Re-Deployment der kritischen Signal Engine.
-   **Flexibilität:** Andere Services (z.B. Risk Management) können die Regime-Information ebenfalls nutzen.

Die zusätzliche Latenz durch die Kommunikation via Redis ist im Millisekundenbereich und für die angestrebte Handelsfrequenz vernachlässigbar.

## 5. Fazit und Empfehlung

Die Integration eines HMM-basierten Regime-Erkennungssystems in *Claire de Binare* ist **technisch machbar und strategisch wertvoll**. Es schafft die Grundlage für adaptive Handelsstrategien und kann die Robustheit und Performance des Systems erheblich steigern.

**Empfehlung:**
Implementierung eines **dedizierten Regime-Engine-Microservice**, der über Redis-Events kommuniziert. Die Entwicklung sollte mit einer erprobten Bibliothek wie `hmmlearn` in Python erfolgen und durch rigorose Offline-Backtests validiert werden, bevor das System live geschaltet wird.
---
