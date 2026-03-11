---
id: CDB-DR-E1-4
title: 'Policy Engine und Begleitmodule'
subtitle: 'Design einer adaptiven Entscheidungsarchitektur für autonome Trading-Bots'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-07' # Aus Metadaten im Original
status: 'Running' # Aus Metadaten im Original
version: '1.0.0' # Aus Metadaten im Original
tags:
  - Policy Engine
  - Microservices
  - Event-Driven Architecture
  - KI-Trading
  - gRPC
  - NLP
---

# Policy Engine und Begleitmodule

> **Management Summary**
>
> Dieser Bericht befasst sich mit dem Design und der Implementierung einer **Policy Engine** und ihrer begleitenden Module innerhalb des *Claire de Binare* Trading-Bots. Es wird eine modulare Microservice-Architektur mit Redis Pub/Sub als Message Bus vorgeschlagen, um hohe Skalierbarkeit und lose Kopplung zu gewährleisten.
>
> Der Bericht analysiert den Einsatz von **gRPC** für latenzkritische interne APIs, die Notwendigkeit **dynamischer Konfiguration** via ENV/Feature-Flags und die Erkennung von **Marktregimen** durch Clustering von Momentum- und Risikofaktoren. Weiterhin werden dynamische **Trading-Profile** zur Steuerung von Positionsgrößen und Risikolimits sowie ein **NLP-Frontend** zur sicheren Steuerung von Services mittels natürlicher Sprache untersucht. Ziel ist die Schaffung einer robusten, adaptiven und deterministischen Entscheidungsarchitektur.

---

## 1. Hypothesen & Forschungsfragen

### 1.1. Hypothesen

-   Eine modulare Microservice-Architektur mit Redis Pub/Sub ermöglicht hohe Skalierbarkeit und lose Kopplung.[^1, ^2]
-   gRPC ist für latenzkritische interne APIs besser geeignet als REST.[^4]
-   Dynamische Konfiguration via ENV/Feature-Flags ermöglicht Policy-Updates ohne Neustart.[^3, ^5]
-   Marktregime folgen zyklischen Mustern und können durch Clustering von Momentum- und Risikofaktoren erkannt werden.[^6, ^7]
-   Dynamische Trading-Profile steuern Positionsgrößen und Risikogrenzen je nach Performance/Drawdown.[^8, ^9]
-   Ein NLP-Frontend mit deterministischem Intent-Parser kann interne Services sicher steuern.[^10]

### 1.2. Forschungsfragen

-   **Policy Engine Design:** Wie wird die Policy-Engine als eigenständiger Microservice mit Redis Pub/Sub und ENV-Konfiguration implementiert?
-   **API-Architektur:** Wann ist gRPC gegenüber REST vorteilhaft? Wie strukturieren wir Redis-Topics und ENV-Keys für Policies?
-   **Entscheidungslogik:** Welche Vor- und Nachteile haben regelbasierte, Score-/Tier-Systeme versus lernende (RL-)Policies?
-   **Systemintegration:** Wie bindet sich die Policy-Engine an Signal Engine, Risk Manager und Execution Layer an?
-   **Regime-Erkennung (E2):** Welche Merkmale indizieren einen Regime-Wechsel? Wie implementieren wir State-Machines oder HMM/Clustering?
-   **Profile Manager (E3):** Welche Trigger verändern das Risiko-Profil? Wie wirken sich Profile auf Positionsgrößen, Approval-Logik und Circuit Breaker aus?
-   **NLP-Frontend (E4):** Wie mappt man deutschsprachige Kommandos sicher auf interne Befehle?

## 2. Methodik

-   **Literatur- und Technik-Review:** Analyse von State-of-the-Art zu Policy Engines, Regime Detection, Profil-Management und NLP-Parsing.
-   **Architektur-Design:** Erstellung von Microservice-Blueprints mit Redis, Docker und ENV-Standards.
-   **Prototyping:** Vergleich gRPC vs. REST (Performance-Tests), Implementierung von Beispiel-Regel-Sets und ML-basierten Policies.
-   **Backtesting & Simulation:** Historische Marktdaten nutzen für Regime-Wechsel-Erkennung (z.B. HMM/GMM) und Profilanpassungen.
-   **Governance-Audit:** Prüfung von Code und Konfiguration nach GEMINI/CLAUDE-Regeln (keine Geheimnisse, ENV-Matrix, Audit-Trails).

## 3. Datenquellen und Feature-Spezifikation

-   **Marktdaten:** Echtzeit-Feeds von MEXC (WebSocket: Preis, Volumen), historische Preisdaten.
-   **Regime-Features:** Rollierende Volatilität (z.B. 10-Tage-STD), gleitende Renditen (Momentum über 5–50 Tage), Korrelations-Indikatoren, Change-Point-Statistiken (z.B. CUSUM).
-   **Policy/Profil-Features:** Portfolio-Leistung (aktueller PnL, ROI), Gesamt-Drawdown, Rest-Budget (Exposure), Positionsgrößen, Sharpe-Ratio.
-   **NLP-Features:** Tokenisierung deutschsprachiger Befehle, Whitelists mit erlaubten Intents/Entities (z.B. „policy”, „vorsichtig”, „setzen”, „profil”, „aggressiv”).

## 4. E1 – Policy Engine

Die **Policy-Engine** ist ein eigenständiger Microservice in Python 3.11, verpackt als Docker-Container mit Redis Pub/Sub zur Kommunikation.[^1, ^2]

### 4.1. API-Architektur

-   **gRPC:** Für interne, hochperformante und latenzkritische Kommunikation (Streaming, Multicast, HTTP/2, Typensicherheit).[^4]
-   **REST/JSON:** Für externe Schnittstellen oder wenn breite Kompatibilität nötig ist.
-   **Redis-Topics:** `policy_engine:commands`, `policy_engine:updates`, `policy_engine:responses`.
-   **Policy-Konfiguration:** ENV-Keys steuern aktive Policies (z.B. `POLICY_MODE`), konsumierbar durch alle Services.

### 4.2. Entscheidungslogik

-   **Regelbasiert:** Klare If/Then-Regeln (Whitelist-Methoden, JSON-Schemata) garantieren Determinismus und Auditierbarkeit.
-   **Score-/Tier-System:** Zuweisung eines Risikoscores oder Profil-Tiers basierend auf Kennzahlen (z.B. Drawdown-Stufen).
-   **Lernende Policies (RL):** Reinforcement Learning kann adaptive Handelsentscheidungen erlernen, wird aber durch Risk-Guardrails begleitet (z.B. fixed risk limits).

### 4.3. Integration und Versionierung

-   **Integration:** Die Signal Engine legt Tradesignale ab (`trading_signals`), die Policy-Engine validiert und kanalisiert diese. Genehmigte Trades gehen an den Risk-Manager und dann an den Execution-Service.
-   **Dynamische Updates:** Policy-Definitionen im Git (Version). ENV-based Flags ermöglichen A/B-Tests und Canary-Releases. Änderungen an Policies können live ausgerollt werden, abgesichert durch Tests und Fallback-Pläne.[^3, ^5]

## 5. E2 – Regime Engine

Die **Regime-Engine** klassifiziert kontinuierlich den Marktstatus eines Symbols in Echtzeit.

### 5.1. Funktionsweise

-   Berechnung laufender Statistiken (Volatilität, Momentum) auf aktuellen Marktdaten.
-   Erkennung signifikanter **Change-Points** (CUSUM, Schwellenüberschreitungen).
-   Verwendung eines diskreten Zustandsautomaten (State-Machine) oder Cluster-Ansatzes zur Modellierung von Zuständen wie *bullisch*, *bärisch*, *volatil*, *panic*.[^6, ^7]
-   **Publishing:** Aktuelles Regime wird unter `market_state:<SYMBOL>` als JSON-Nachricht publiziert.

### 5.2. Integration

-   Das erkannte Regime beeinflusst Policies: Bei "panic" fällt die Policy-Engine in *Safe Mode*, der Profile-Manager schaltet konservativer.
-   Robustheit durch Kombination aus statistischer Erkennung und heuristischen Regeln.

## 6. E3 – Profile Manager

Der **Profile-Manager** (System-Controller) passt dynamisch das Risikoprofil des Systems an: `konservativ`, `neutral` oder `aggressiv`.

### 6.1. Funktionsweise

-   **Trigger:** Automatische Profilschaltung durch Kennzahlen wie Performance, Drawdown, Equity-Trends.[^8, ^9]
-   **Architektur:** Ein zentraler Service oder Scheduler liest Live-KPIs (Equity-Zeitreihe, Drawdown, Sharpe) und setzt über ENV/Redis (`RISK_PROFILE`) das aktuelle Profil.
-   **Auswirkung:** Steuert Positionsgrößen, Approval-Logik im Risk-Manager und Schwellen für Circuit Breaker.

### 6.2. Praxisbeispiele

-   Viele Fonds nutzen feste Tages-Drawdown- oder Gesamt-Drawdown-Limits (z.B. 5 % Tages-Drawdown).[^12]
-   Profilwechsel und Limits werden lückenlos geloggt (Audit-Trail).

## 7. E4 – NLP-Frontend / Natürliche Sprachsteuerung

Ein **NLP-Interface** ermöglicht Bedienern, das System per natürlichsprachlicher Kommandos (z.B. „Policy auf vorsichtig setzen“) zu steuern.

### 7.1. Funktionsweise

-   **Intent-Parsing:** Erkennt einen Intent (z.B. `SET_POLICY_MODE`) und füllt Slots (z.B. `policy_mode: SAFE`).
-   **Determinismus & Sicherheit:** Der Parser arbeitet **whitelist-basiert** und nutzt JSON-Schemas zur Validierung. Es gibt keine unbeaufsichtigten LLM-Outputs.
-   **Frameworks:** **Rasa** (mit spaCy-Tokenizer) oder **spaCy+HF-Transformer** bieten gute Erkennungsraten für deutsche Befehle und können lokal betrieben werden.[^10]

---

## 8. Spezifikationen (Anhang)

Die nachfolgenden JSON-Spezifikationen wurden aus dem Originaldokument extrahiert und bieten eine maschinenlesbare Definition der relevanten Datenmodelle.

### 8.1. `state_space_spec` (Zustandsraum)

Definiert den Zustandsraum mit Markt- und Systemkennzahlen.

```json
{
  "market_regime": {"type": "enum", "values": ["volatile", "bullish", "bearish", "panic", "neutral"]},
  "price_change": {"type": "float", "min": -1.0, "max": 1.0, "unit": "percentage"},
  "rolling_volatility": {"type": "float", "min": 0.0, "max": 1.0},
  "performance_trend": {"type": "float", "min": -1.0, "max": 1.0},
  "drawdown": {"type": "float", "min": 0.0, "max": 1.0},
  "current_profile": {"type": "enum", "values": ["conservative", "neutral", "aggressive"]},
  "policy_mode": {"type": "enum", "values": ["SAFE", "STANDARD", "AGGRESSIVE"]},
  "latency": {"type": "float", "min": 0.0, "max": 1.0, "unit": "seconds"}
}
```

### 8.2. `action_space_spec` (Aktionsraum)

Definiert die möglichen Aktionen der Policy Engine.

```json
{
  "actions": [
    { "name": "SET_PROFILE", "params": {"profile": ["conservative", "neutral", "aggressive"]} },
    { "name": "SET_POLICY", "params": {"policy_mode": ["SAFE", "STANDARD", "AGGRESSIVE"]} },
    { "name": "NO_OP", "params": {} }
  ]
}
```

### 8.3. `reward_spec` (Belohnungsfunktion)

Spezifikation der Belohnungsfunktion für RL/Entscheidungsoptimierung.

```json
{
  "components": {
    "profit": {"weight": 1.0},
    "drawdown_penalty": {"weight": -10.0},
    "policy_violation": {"weight": -100.0}
  },
  "aggregation": "weighted_sum",
  "description": "Kombination aus Performance (Profit) und Strafen für Drawdown bzw. Policy-Verstöße"
}
```

### 8.4. `latency_sla` (Latenz-Anforderungen)

Service-Level Agreements (SLAs) in Millisekunden.

```json
{
  "policy_engine_response_ms": 50,
  "risk_check_latency_ms": 10,
  "nlp_command_latency_ms": 100,
  "description": "Maximale Latenzen für Policy-Entscheidungen und Risiko-Prüfungen"
}
```

### 8.5. `risk_budget` (Risikobudget)

Vordefinierte Risikolimits.

```json
{
  "max_drawdown": 0.05,
  "max_exposure": 0.3,
  "circuit_breaker": 0.1,
  "description": "Maximales Tages-Drawdown, Exposure und Circuit-Breaker (Verlust)"
}
```

### 8.6. `decision_rules` (Deterministische Entscheidungsregeln)

Beispielhafte deterministische Regeln zur Policy-/Profilsteuerung.

```json
{
  "rules": [
    { "id": "RULE_CONSERVATIVE_ON_DRAWDOWN", "condition": "drawdown > 0.05", "action": {"type": "SET_PROFILE", "profile": "conservative"} },
    { "id": "RULE_AGGRESSIVE_ON_GAIN", "condition": "performance_trend > 0.02", "action": {"type": "SET_PROFILE", "profile": "aggressive"} },
    { "id": "RULE_SAFE_POLICY_ON_PANIC", "condition": "market_regime == 'panic'", "action": {"type": "SET_POLICY", "policy_mode": "SAFE"} }
  ],
  "description": "Beispielhafte deterministische Entscheidungsregeln für Profile und Policies"
}
```

## 9. Fazit und konkrete Empfehlungen

Das beschriebene Konzept verbindet fortgeschrittene Risiko-Methoden mit einer robusten Event-Architektur.

-   **Technologie-Stack:** Apache Kafka für Kern-Datenströme, NATS JetStream für extrem niedrige Latenz.
-   **Datenmodell & Schema:** Klar strukturierte Event-Schemas (Avro oder Protocol Buffers) für jede Event-Art.
-   **Microservices & Schnittstellen:** Entwicklung getrennter Services für Data Ingestion, Signal Engine, Risk Management, Execution und Portfolio.
-   **Adaptives Risikomanagement:** Integration von Drift-Detection, Bayesian Position Sizing und RL-basierten Parametern in den Risk Service.
-   **Deterministisches Testing:** Intensive Nutzung der Replay-Fähigkeit für Tests und Validierung.
-   **Überwachung und Resilienz:** Umfassendes Monitoring von Latenzen, Alarmierung bei Risikogrenzen und Performance-Tuning.

---

