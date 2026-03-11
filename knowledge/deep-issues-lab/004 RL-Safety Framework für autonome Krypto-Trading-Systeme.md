---
id: CDB-DR-004
title: 'CDB RL-Safety Framework'
subtitle: 'Ein Framework für sicheres, auditierbares Reinforcement Learning im Krypto-Handel'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Refactored'
tags:
  - Reinforcement Learning
  - RL
  - Safety
  - Risk-Management
  - Architektur
  - MiFID II
  - AI Act
---

# CDB RL-Safety Framework

> **Management Summary**
>
> Reinforcement Learning (RL) bietet enormes Potenzial für autonomes Trading, birgt aber systemische Risiken. Dieses Framework definiert die Sicherheitsarchitektur für den Einsatz von RL-Agenten im Projekt *Claire de Binare*, speziell für den Handel mit Perpetual Futures.
>
> Die Kernphilosophie ist **"Autonomie mit Leitplanken"**: Das System darf eigenständig handeln, aber niemals außerhalb definierter und auditierbarer Sicherheitsgrenzen. Das Framework kombiniert akademische Safe-RL-Methoden (CMDPs), deterministische Hard-Limits (Action Masking) und infrastrukturelle Safeguards (Kill-Switches), um ein robustes, produktionsreifes und regulatorisch konformes System zu gewährleisten.

---

## 1. Architektur-Übersicht: Das dreistufige Sicherheitsmodell

Das Framework basiert auf einem **dreischichtigen Sicherheitsmodell**, das mathematische, logische und infrastrukturelle Kontrollen kombiniert. Diese Trennung der Verantwortlichkeiten ermöglicht unabhängige Skalierung, Tests und Audits jeder Komponente.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CDB RL-SAFETY ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: POLICY LAYER (Soft Constraints via Lagrangian Methods)            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  RL Policy Engine (PPO-Lag / CPO)                                   │    │
│  │  • Objective: max E[R] s.t. E[C] ≤ d (z.B. CVaR, Drawdown)         │    │
│  │  • Distributional RL (IQN/QR-DQN) für Tail-Risk                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                        │
│  LAYER 2: CONSTRAINT LOGIC ENGINE (Hard Constraints via Action Masking)     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Action Masking Layer (Deterministische Filterung)                  │    │
│  │  • Position Limits, Margin Requirements, Order Size                 │    │
│  │  • PPAM für temporale Constraints (z.B. Trade-Frequenz)             │    │
│  │  • Latenz: < 2ms (in-memory)                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                        │
│  LAYER 3: RISK GATEKEEPER (Infrastructure Safeguards)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Pre-Trade Risk Layer + Kill-Switch                                 │    │
│  │  • Circuit Breakers (Exchange, Model, Data)                         │    │
│  │  • AI-NOT-AUS (Soft/Hard Kill)                                      │    │
│  │  • Durchsetzung der "Tresor-Regel"                                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Mathematische Grundlagen: Constrained Reinforcement Learning

**Constrained Markov Decision Processes (CMDPs)** erweitern klassische MDPs um explizite Kostenfunktionen, was für das Risikomanagement im Trading unerlässlich ist.

-   **Optimierungsziel:** Maximiere den erwarteten Return `J(π)` unter der Nebenbedingung, dass die erwarteten Kosten `E[C(π)]` einen Schwellenwert `d` nicht überschreiten.
    `max J(π)  s.t.  E[C(π)] ≤ d`

-   **Constraint-Typen für das Trading:**

| Constraint-Typ | Mathematik | Trading-Anwendung |
| :--- | :--- | :--- |
| **State-wise Hard** | `c(s,a) = 0 ∀t` | Position Limits, Margin Requirements |
| **Expected Soft** | `E[C(π)] ≤ d` | Durchschnittlicher Value-at-Risk (VaR) |
| **CVaR Risk** | `CVaR_α(R) ≥ -threshold` | Tail-Risk-Management ("Tresor-Regel") |

-   **Algorithmen:**
    -   **PPO-Lagrangian:** Empfohlener Startpunkt. Kombiniert stabile Policy-Updates mit adaptiver Gewichtung der Constraints.
    -   **Distributional RL (IQN/QR-DQN):** Zur Modellierung der vollständigen Return-Verteilung. Erlaubt die direkte Berechnung des CVaR aus den gelernten Quantilen, was für das Management von Extremrisiken entscheidend ist.

## 3. Deterministische Kontrolle: Action Masking

Action Masking ist der **deterministische Kern** des Safety-Frameworks. Es garantiert mathematisch, dass vordefinierte, unsichere Aktionen niemals an die Börse weitergeleitet werden, unabhängig davon, was die RL-Policy vorschlägt.

### 3.1. Action Space und State

```python
from enum import IntEnum
import numpy as np
from dataclasses import dataclass

class TradingAction(IntEnum):
    HOLD = 0
    BUY_SMALL = 1
    BUY_MEDIUM = 2
    BUY_LARGE = 3
    SELL_SMALL = 4
    SELL_MEDIUM = 5
    SELL_LARGE = 6
    CLOSE_POSITION = 7

@dataclass
class TradingState:
    position: float
    portfolio_value: float
    available_margin: float
    current_drawdown: float
    daily_pnl: float
    trades_last_hour: int
    volatility_index: float
```

### 3.2. Constraint Logic Engine (CLE)

Die CLE ist eine in-memory Komponente, die für jeden Zeitschritt eine binäre Maske legaler Aktionen berechnet. Ihre Ausführungszeit ist **garantiert < 2ms**.

```python
class ConstraintLogicEngine:
    def __init__(self, config: dict):
        # MiFID II RTS 6 konforme Hard Limits
        self.max_position_pct = config.get('max_position_pct', 0.20)
        self.max_drawdown_pct = config.get('max_drawdown_pct', 0.10)
        self.daily_loss_limit = config.get('daily_loss_limit', 0.03)
        self.max_trades_per_hour = config.get('max_trades_per_hour', 20)
        self.min_margin_ratio = config.get('min_margin_ratio', 0.15)

    def compute_action_mask(self, state: TradingState) -> np.ndarray:
        """Berechnet eine binäre Maske (True = Aktion erlaubt)."""
        mask = np.ones(len(TradingAction), dtype=bool)

        # 1. Drawdown-Schutz (Tresor-Regel)
        if state.current_drawdown >= self.max_drawdown_pct:
            # Bei Limit-Erreichung: Nur noch Positionsschließung erlaubt
            mask[:] = False
            mask[TradingAction.HOLD] = True
            if state.position != 0:
                mask[TradingAction.CLOSE_POSITION] = True
            return mask

        # 2. Tägliches Verlustlimit
        if state.daily_pnl <= -self.daily_loss_limit * state.portfolio_value:
            mask[:] = False
            mask[TradingAction.HOLD] = True
            if state.position != 0:
                mask[TradingAction.CLOSE_POSITION] = True
            return mask
        
        # 3. Positions- und Margin-Limits
        if abs(state.position) / state.portfolio_value >= self.max_position_pct:
            # Keine neuen positionsvergrößernden Trades
            if state.position > 0: mask[TradingAction.BUY_SMALL:TradingAction.BUY_LARGE+1] = False
            else: mask[TradingAction.SELL_SMALL:TradingAction.SELL_LARGE+1] = False
        
        if state.available_margin / state.portfolio_value < self.min_margin_ratio:
             mask[TradingAction.BUY_SMALL:TradingAction.SELL_LARGE+1] = False
        
        # 4. Trade-Frequenz-Limit (Anti-Overtrading)
        if state.trades_last_hour >= self.max_trades_per_hour:
            mask[TradingAction.BUY_SMALL:TradingAction.SELL_LARGE+1] = False
            
        # Fallback: HOLD ist immer erlaubt
        mask[TradingAction.HOLD] = True
        return mask
```

### 3.3. Integration mit Stable-Baselines3 (MaskablePPO)

Die `action_masks()`-Methode des Gym-Environments wird von `MaskablePPO` bei jedem Schritt aufgerufen, um die Logits der Policy vor der Sampling-Aktion zu maskieren.

```python
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy
import gymnasium as gym

class CDBTradingEnv(gym.Env):
    def __init__(self, config: dict):
        super().__init__()
        self.cle = ConstraintLogicEngine(config)
        self.action_space = gym.spaces.Discrete(len(TradingAction))
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(64,))
        self.current_state: TradingState = None

    def action_masks(self) -> np.ndarray:
        """Wird von MaskablePPO vor jeder Aktion aufgerufen."""
        if self.current_state is None:
            return np.ones(self.action_space.n, dtype=bool)
        return self.cle.compute_action_mask(self.current_state)

    def step(self, action: int):
        # ... Logik zur Ausführung des Trades und Berechnung von Reward/Cost
        pass
```

## 4. Infrastruktur-Sicherheit: Kill-Switch ("AI-NOT-AUS")

Der Kill-Switch ist die **letzte, unabhängige Verteidigungslinie** und eine Anforderung nach MiFID II RTS 6.

-   **Dreistufiges System:**
    1.  **REDUCE_ONLY (Soft-Kill):** Keine neuen Positionen, nur Schließung bestehender. Wird bei moderaten Anomalien ausgelöst (z.B. 7 Verlusttrades in Folge, Latenzanstieg).
    2.  **HARD_STOP (Hard-Kill):** Sofortige Stornierung aller offenen Orders und Liquidierung aller Positionen durch Market-Orders. Auslöser: Erreichen des maximalen Drawdowns (10 %).
    3.  **EMERGENCY:** Hard-Stop plus Shutdown der Trading-Services.

-   **Implementierung:** Ein separater, leichtgewichtiger Service (`killswitch-service`), der direkt mit der Börsen-API und einer eigenen Datenbankverbindung kommuniziert, um unabhängig vom restlichen System zu bleiben.
-   **Manueller Override:** Autorisierte Benutzer können jederzeit manuell eingreifen. Jeder Eingriff wird für Audits protokolliert (Anforderung nach EU AI Act, Art. 14).

## 5. Deployment und Validierung

### 5.1. Shadow-Mode

Vor dem Einsatz mit realem Kapital muss jede neue Policy eine **Shadow-Trading-Phase** durchlaufen. Das System generiert "virtuelle" Trades und validiert deren Performance gegen Live-Marktdaten.

-   **Mindestdauer:** 14 Tage.
-   **Promotion-Kriterien:** Positiver Sharpe-Ratio (> 0.5), maximaler Drawdown nicht signifikant höher als im Backtest, hohe Fill-Genauigkeit der Simulation.

### 5.2. Canary Deployment

Nach erfolgreichem Shadowing wird das Kapital schrittweise über mehrere Phasen allokiert:
-   **Phase 1 (1 % Kapital):** 3 Tage, Fokus auf Stabilität.
-   **Phase 2 (5 % Kapital):** 7 Tage, Fokus auf P&L-Konsistenz.
-   **Phase 3 (25-50 % Kapital):** 2-4 Wochen, Fokus auf Performance unter Last.
-   **Full Deployment (100 % Kapital):** Kontinuierliches Monitoring.

Jede Phase hat **automatische Rollback-Trigger**. Bei Verletzung der Schwellenwerte (z.B. Drawdown-Limit der Phase) wird die Kapitalallokation automatisch auf die vorherige Stufe zurückgesetzt.

## 6. Auditierbarkeit und Compliance

Ein lückenloser Audit-Trail ist für die Einhaltung regulatorischer Vorgaben (MiFID II, EU AI Act) entscheidend.

-   **Event Sourcing:** Jede Entscheidung, jeder Ordervorgang und jede Constraint-Verletzung wird als unveränderliches Event in einer TimescaleDB-Datenbank gespeichert.
-   **Protokollierte Daten pro Entscheidung:**
    -   Vollständiger `state_snapshot`
    -   `model_version`
    -   `action_masked` (ja/nein) und `mask_reason`
    -   Inferenz-Latenz

-   **Aufbewahrungsfristen:** 5 Jahre für Handelsentscheidungen, 10 Jahre für Kill-Switch-Events und manuelle Eingriffe.

---

## Empfohlene Technologien

| Komponente  ## | Empfehlung                  ## | Alternative           ## |
| :---           | :---                           | :---                     |
| Constrained RL | OmniSafe (PKU)                 | Custom PPO-Lagrangian    |
| Action Masking | SB3-Contrib MaskablePPO        | Custom CategoricalMasked |
| Environments   | Safety-Gymnasium API           | Custom Gymnasium         |
| Model Serving  | NVIDIA Triton                  | TorchServe, ONNX Runtime |
| Message Queue  | Kafka (Events), NATS (Signale) | Redis Streams            |
| Event Store    | Kafka + TimescaleDB            | EventStoreDB             |
| Monitoring     | Prometheus + Grafana           | Datadog                  |

