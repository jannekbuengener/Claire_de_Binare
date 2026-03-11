---
id: CDB-DR-003
title: 'Optimierung von Handelsfrequenz und Signalqualität'
subtitle: 'Strategien zur Steigerung der Trade-Anzahl bei konsistenter Win-Rate'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Refactored'
tags:
  - Handelsfrequenz
  - Signalqualität
  - Win-Rate
  - RSI
  - Risk-Management
---

# Optimierung von Handelsfrequenz und Signalqualität

> **Management Summary**
>
> Diese Analyse untersucht Methoden zur Steigerung der Handelsfrequenz des Trading-Bots *Claire de Binare*, ohne dabei die Signalqualität und eine positive Win-Rate (>50 %) zu kompromittieren. Aktuell agiert der Bot konservativ mit wenigen, hoch qualitativen Trades. Das Ziel ist eine höhere Trade-Anzahl unter moderatem Risiko.
>
> Die Kernempfehlung ist, die Momentum-Schwelle zur Signalerkennung zu senken und gleichzeitig zusätzliche Filter wie den **Relative-Stärke-Index (RSI)** und **Trendfilter (Moving Averages)** zu implementieren. Diese Maßnahmen sollen die Anzahl der Handelssignale erhöhen, während Fehlsignale in seitwärts tendierenden oder überkauften/überverkauften Märkten reduziert werden. Die bestehende Risikoarchitektur ist robust genug, um eine höhere Frequenz zu bewältigen. Ein umfassendes Monitoring mittels Prometheus und Grafana ist zur Validierung der Ergebnisse unerlässlich.

---

## 1. Problemstellung: Balance zwischen Frequenz und Qualität

*Claire de Binare* (CDB) ist ein deterministischer Trading-Bot, der auf Momentum-Signalen basiert. Die zentrale Herausforderung ist, die **Handelsfrequenz zu steigern**, ohne die **Signalqualität** – gemessen an einer Win-Rate von über 50 % – zu opfern.

**Ziele der Analyse:**
-   **Signal-zu-Trade-Verhältnis:** Untersuchung der Konversionsrate von Signalen zu profitablen Trades.
-   **Handelsfrequenz vs. Risiko:** Erhöhung der Trade-Anzahl bei Einhaltung moderater Risikogrenzen.
-   **Signal-Qualitätssicherung:** Implementierung von Filtern (z.B. RSI), um die Profitabilität zu stabilisieren.
-   **Monitoring:** Überwachung der Änderungen durch Prometheus/Grafana-Metriken.

## 2. Status Quo und Analysegrundlage

### 2.1. Aktuelle Konfiguration

-   **Handelsfrequenz:** Gering, da die Signal-Engine auf starke Momentum-Änderungen (≥ 3 % über 15 Min.) und ausreichendes Volumen (> 100k) beschränkt ist.[^1, ^2]
-   **Risikoprofil:** Konservativ. Der Risk Manager limitiert das Engagement pro Trade (max. 10 % des Kapitals), das Gesamt-Exposure (max. 50 %) und den maximalen Tagesverlust (5 % Circuit-Breaker).[^9, ^10]

### 2.2. Key Performance Indicators (KPIs)

Die Performance wird durch eine Kette von Prometheus-Metriken messbar:
-   `signals_generated_total`
-   `orders_approved_total` (vom Risk Manager freigegeben)
-   `orders_blocked_total` (vom Risk Manager blockiert)
-   `execution_orders_filled_total` (tatsächlich ausgeführte Trades)

Die **Win-Rate** (Anteil profitabler Trades) ist die entscheidende Metrik für die Signalqualität, muss aktuell aber noch aus der Datenbank oder durch erweiterte Metriken ermittelt werden. Ziel ist es, diese **konstant über 50 %** zu halten.

## 3. Strategien zur Frequenzerhöhung bei moderatem Risiko

Die bestehende Risikoarchitektur (Circuit-Breaker, Exposure-Limits) verhindert eine exponentielle Risikoerhöhung und erlaubt eine maßvolle Steigerung der Trade-Anzahl.

| Strategie-Modus      | Trades pro Tag (ca.) | Win-Rate (erwartet) | Max. Drawdown (Schätzung) |
| :------------------- | :------------------: | :-----------------: | :-----------------------: |
| **Konservativ**      |         1–2          |       ~60 %         |      <2 % (sehr gering)      |
| **Moderates Risiko** |         5–8          |        >50 %        |      <5 % (kontrolliert)     |
| **Aggressiv**        |         15+          |        <50 %        |       >5 % (kritisch)       |

**Ansätze zur Frequenzerhöhung:**

1.  **Momentum-Schwelle senken:** Eine Reduzierung des `SIGNAL_THRESHOLD_PCT` (z.B. von 3.0 % auf 2.0 %) ist die direkteste Methode, um mehr Signale zu generieren. Dies muss durch Qualitätsfilter kompensiert werden.
2.  **Mehr Märkte:** Die Ausweitung auf weitere liquide Handelspaare erhöht die Anzahl potenzieller Signale.

Der Schlüssel liegt darin, nicht nur die Quantität, sondern vor allem die **Qualität der zusätzlichen Signale** zu sichern.

## 4. Signalfilter zur Qualitätssicherung

Um die Win-Rate trotz höherer Frequenz stabil zu halten, sind zusätzliche Filter unerlässlich:

-   **Relative-Stärke-Index (RSI):** Ein RSI-Filter verhindert Trades in momentumschwachen Seitwärtsphasen.
    -   **Regel-Beispiel:** Long-Signale nur bei RSI > 50, Short-Signale nur bei RSI < 50 zulassen.[^15]
    -   **Effekt:** Filtert Fehlsignale heraus und verbessert die Trade-Qualität nachweislich.

-   **Trend-Filter (Gleitende Durchschnitte):** Stellt sicher, dass Trades nur in Richtung des übergeordneten Trends ausgeführt werden (z.B. Kurs über 50-Perioden-MA für Long-Trades).

-   **Volatilitäts-Filter (ATR):** Ignoriert Signale bei extrem niedrigem Markt-Rauschen (niedrige ATR) oder passt die Schwellen in hochvolatilen Phasen dynamisch an, um "Overtrading" zu vermeiden.

-   **Regime-Erkennung (ADX):** Der ADX-Indikator kann helfen, zwischen Trend- (hoher ADX) und Seitwärtsphasen (niedriger ADX) zu unterscheiden und die Strategie entsprechend anzupassen.[^16]

**Empfohlener Kompromiss:** Senkung der Momentum-Schwelle bei gleichzeitiger Einführung eines RSI- und Trend-Filters.

## 5. Implementierung und Monitoring

Die Umsetzung erfolgt in den bestehenden Services:

1.  **Signal Engine (`cdb_signal`):**
    -   Anpassung des `SIGNAL_THRESHOLD_PCT` in der Konfiguration.
    -   Implementierung der RSI- und Trendfilter-Logik innerhalb der `process_market_data`-Methode.

2.  **Risk Manager (`cdb_risk`):**
    -   Die robusten Limits bleiben weitgehend bestehen. Eine leichte Anhebung des `MAX_EXPOSURE_PCT` (z.B. auf 60 %) kann evaluiert werden, falls das Limit häufig erreicht wird.

3.  **Monitoring (Prometheus/Grafana):**
    -   Einrichtung eines Dashboards zur Überwachung der Korrelation von **Trades pro Tag vs. Win-Rate** und **kumulativem P&L**.
    -   Ergänzung neuer Metriken wie `trades_profitable_total`, um die Win-Rate direkt in Grafana visualisieren zu können.
    -   Überwachung der `circuit_breaker_active`-Metrik als Frühwarnsystem für zu hohe Drawdowns.

## 6. Fazit und Handlungsempfehlungen

1.  **Frequenz erhöhen:** Senken Sie `SIGNAL_THRESHOLD_PCT` auf ca. 2 % und zielen Sie auf 5–8 Trades pro Tag.
2.  **Qualität sichern:** Führen Sie zwingend einen **RSI- und Trendfilter** in der Signal Engine ein, um die Win-Rate über 50 % zu halten.
3.  **Risiko kontrollieren:** Behalten Sie die bestehenden Risikolimits bei. Das 5%-Tagesverlust-Limit fungiert als ultimatives Sicherheitsnetz.
4.  **Messen & Validieren:** Führen Sie die Änderungen schrittweise ein und validieren Sie den Erfolg über einen A/B-Test im Paper-Trading. Überwachen Sie die Performance-Metriken (Win-Rate, P&L, Drawdown) kontinuierlich.

Durch diesen ausbalancierten Ansatz kann *Claire de Binare* mehr Marktchancen wahrnehmen, ohne die Stabilität und Profitabilität des Systems zu gefährden.

---

