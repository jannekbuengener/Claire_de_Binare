---
id: CDB-DR-C3
title: 'Hybride Policy-Architekturen'
subtitle: 'Integration von regelbasierten und ML-Komponenten für adaptive Trading-Bots'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Refactored'
tags:
  - Policy-Architektur
  - Hybride Strategien
  - Machine Learning
  - Regelbasiertes System
  - Microservices
---

# Hybride Policy-Architekturen

> **Management Summary**
>
> Hybride Policy-Architekturen kombinieren klassische, regelbasierte Logik mit Machine-Learning (ML)-Komponenten, um robuste und adaptive Entscheidungsfindung in Trading-Bots zu ermöglichen. Typische Muster sind **Policy-Switcher** (zentrale Wechselsteuereinheit), **Hybrid-Controller** oder **Rule+NN-Architekturen**.
>
> Dieses Dokument analysiert verschiedene Architekturmuster, die dynamische Steuerung über Redis-Keys oder Umgebungsvariablen nutzen und Agenten klare Rollen zuweisen. Ein strukturierter Paper-Trading-Modus ist essentiell. Die Microservice-Trennung von `signal_engine`, `risk_manager` und `execution_service` bildet die Grundlage für skalierbare und fehlertolerante Systeme.

---

## 1. Architekturmuster und Komponenten

Hybride Policy-Systeme sind modular aufgebaut und trennen Verantwortlichkeiten klar.

### 1.1. Modulare 3-Schichten-Architektur

-   **Konzept:** Ähnlich wie bei **Freqtrade**, trennt man die Trading-Engine (Marktzugang, Order-Ausführung), das Strategie-Modul (Indikatorlogik) und die optionale ML-Komponente (z.B. *FreqAI*) strikt voneinander.[^1, ^2]
-   **Vorteil:** Das Regelwerk bleibt isoliert und stabil, während ML nur Zusatzsignale oder adaptive Schwellen liefert. Die ML-Komponente kann unabhängig trainiert oder aktualisiert werden.

### 1.2. Agentenbasierte Pipeline

-   **Konzept:** Mehrere spezialisierte Agenten (z.B. Technical-Analyst, Sentiment-Analyst, Risk-Manager, Portfolio-Manager) arbeiten parallel und koordinieren sich über einen Nachrichtenbus oder einen State-Store.
-   **Beispiel:** Technik- und Sentiment-Agenten kombinieren ihre Signale zu einem Konsens, der an einen **Risk-Agenten** weitergeleitet wird, bevor ein Portfolio-Agent final über Kauf/Verkauf entscheidet.[^3]
-   **Vorteil:** Fördert Skalierbarkeit, Fehlertoleranz und eine klare Trennung von Verantwortlichkeiten.

### 1.3. Policy-Switcher / Hybrid-Controller

-   **Konzept:** Ein Meta-Agent wechselt je nach Marktbedingungen oder Konfigurations-Flag zwischen verschiedenen Regel- oder ML-Policies.
-   **Beispiel:** Ein `Rule+NN`-Muster, bei dem ein klassisches RSI-Signal nur dann gehandelt wird, wenn ein neuronaler Confidence-Score es als zuverlässig einstuft.
-   **Vorteil:** Adaptive Anpassung der Strategie an dynamische Marktbedingungen.

---

## 2. Dynamische Steuerbarkeit per Redis/ENV

Zur Laufzeit lassen sich nahezu alle Policy-Parameter über Redis-Keys oder Umgebungsvariablen ändern, was sofortige Anpassungen an Marktbedingungen erlaubt.

-   **Redis als State-Manager:** Redis wird für den zentralen Status und die Kommunikation zwischen Agenten in Echtzeit genutzt.[^3, ^6] Pub/Sub oder Streams können Signale und Schwellenwerte disseminieren.
-   **ENV-Flags und Konfigurationsdateien:** Umgebungsvariablen (`.env`) oder Konfigurationsdateien (`.json/.yaml`) steuern Enable/Disable-Funktionen und Parameter, die zur Laufzeit angepasst werden können.[^7, ^8]
-   **Risk-Toggles und Volatility-Flags:** Dynamische Flags können Volatilitätscluster erkennen und die Trading-Aggressivität drosseln (z.B. automatisierte De-Risking-Schalter bei steigenden Volatilitäts-Indizes).[^11]

---

## 3. Agentenbasiertes Design und Rollen

Eine klare Trennung der Verantwortlichkeiten ist für hybride Architekturen entscheidend.

-   **Signal Engine / Datenagent:** Beschafft Marktdaten und generiert erste Handelssignale (indikatorell oder ML-basiert).
-   **Kombinations- und Bewertungsagenten:** Aggregieren und bewerten mehrere Signale (TA, Sentiment, ML-Vorhersagen).
-   **Risk Manager:** Prüft vor Ausführung jedes Vorschlags Risikokriterien (Positionsgröße, max. Exposure, Korrelation) und fungiert als Gatekeeper.[^3, ^5]
-   **Portfolio-/Order Manager:** Nimmt genehmigte Signale und sendet Transaktionen an Broker-API.
-   **DB-Writer / Logger:** Schreibt alle Signale, Positionen und Trades in eine Datenbank zur Analyse und Auditing.
-   **Paper-Trading-Agent:** Schaltet die Order-Pipeline in den Testmodus um, um Strategien ohne reales Kapital zu testen.

Alle Agenten kommunizieren via Messaging (Redis, Message-Queue) und lassen sich unabhängig skalieren, was Fehlertoleranz und Erweiterbarkeit erhöht.[^3, ^6]

---

## 4. Papermodus-Kompatibilität

Ein zuverlässiger Backtesting/Papermodus ist in produktionsnahen Umgebungen Pflicht.

-   **Ansatz:** Die gleichen Services werden für Live- und Test-Trading genutzt, nur die Order-Pipeline wird in den Testmodus geschaltet.
-   **Implementierung:**
    -   **Freqtrade** bietet einen `dry-run`-Modus.[^13, ^14]
    -   Ein Konfigurations-Toggle (ENV-Flag) kann zwischen Testnet und Live-Modus wechseln.[^9, ^10]
    -   Eine separate Schnittstelle kann den Execution-Service je nach Modus an eine simulierte oder echte Börse senden.
-   **Audit und Logging:** Auch im Paper-Modus werden alle Trades und Signale in der Datenbank erfasst, um eine spätere Analyse zu ermöglichen.

---

## 5. Vergleich ausgewählter Systeme

| System / Framework | Sprache / Stack | Architektur-Pattern | Regelbasiert + ML | Dynamische Steuerung | Paper-/Backtest-Modus |
| :----------------- | :---------------- | :------------------ | :---------------- | :------------------- | :-------------------- |
| **Freqtrade (mit FreqAI)** | Python, Redis, Postgres, Docker | 3-Schichten-Modular | JA | Über Config/ENV | JA |
| **AI-Trading-System (Saurabh Jain)** | Python, Redis, Docker | Agentenbasiert | JA | Über Redis-Keys | JA |
| **Crypto-Trading-Bot (Khushi)** | Python | Modulares Skript, Config-basiert | JA | ENV/Config-Flags | JA |
| **MBATS (Microservices)** | Python, Docker | Microservices | JA | Über Service-Konfiguration | JA |
| **Lux (Trading Beispiel)** | Elixir | Agentenbasiert | JA | Nur über Code-Änderung | Nein / nicht integriert |

---

## 6. Empfehlungen für Claire de Binare

1.  **Agenten-Rollen klar abgrenzen:** Services mit klar definierten Aufgaben (Signal-Generierung, Risiko, Ausführung, DB).
2.  **Modularer Aufbau:** Übernahme der 3-Schichten-Architektur (Engine / Strategy / ML) zur Trennung von ML-Logik vom Hauptflow.
3.  **Dynamische Flags:** Nutzung von Redis-Keys oder ENV-Variablen für die Laufzeitsteuerung von Policy-Parametern (z.B. `use_ml_signals`, `max_daily_trades`).
4.  **Paper-Trading zuerst:** Implementierung eines robusten Backtest-/Simulations-Modus von Anfang an.
5.  **Erfahrungen adaptieren:** Profitieren Sie von Open-Source-Frameworks wie Freqtrade und MBATS für Architektur-Insights.

Durch die Kombination dieser Muster entsteht ein flexibles, produktionsreifes System, das den Anforderungen an *Claire de Binare* entspricht und modernste Best Practices nutzt.

---

