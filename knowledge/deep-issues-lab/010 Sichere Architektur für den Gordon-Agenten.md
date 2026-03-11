---
id: CDB-DR-010
title: 'Sicherheitsarchitektur für KI-Agenten'
subtitle: 'Ein "Defense in Depth"-Ansatz für autonome Handelssysteme'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Refactored'
tags:
  - Architektur
  - Sicherheit
  - Sandboxing
  - API-Gateway
  - RL-Safety
---

# Sicherheitsarchitektur für KI-Agenten

> **Management Summary**
>
> Dieses Dokument analysiert und vergleicht Sicherheitsarchitekturen für autonome KI-Komponenten ("Agenten") innerhalb des *Claire de Binare (CDB)*-Systems. Es adressiert zwei fundamentale und komplementäre Sicherheitsebenen, um eine ganzheitliche "Defense in Depth"-Strategie zu definieren:
>
> 1.  **Infrastruktur-Sicherheit (Die "Festung"):** Wie kann der Agent sicher in der Systemumgebung ausgeführt werden? Dies betrifft die Isolation des Agenten (Sandboxing) und die Kontrolle seiner Kommunikationswege (API-Gateway vs. direkte Integration).
> 2.  **Algorithmische Sicherheit (Das "Gewissen"):** Wie stellen wir sicher, dass der Agent selbst keine gefährlichen oder unerwünschten Aktionen ausführt? Dies betrifft die interne Logik des Agenten, seine Entscheidungsfindung und die Einhaltung von vordefinierten Regeln.

---

## 1. Infrastruktur- & Umfeld-Sicherheit ("Die Festung")

Diese Ebene definiert die äußere Hülle und kontrolliert, wie der Agent mit seiner Umgebung interagiert.

### 1.1. Grundlegende Architektur-Designs

#### Design A: Der integrierte Agent
-   **Beschreibung:** Der Agent ist tief in das Docker-Ökosystem integriert und nutzt ein internes Protokoll (z.B. MCP Toolkit) für die Werkzeugnutzung.
-   **Kommunikation:** Der Agent verbindet sich mit einem Gateway, das den Zugriff auf verschiedene Werkzeuge (z.B. Datenbank-Connectors) steuert, die als separate Container laufen.
-   **Vorteil:** Hohe Flexibilität und potenziell geringere Latenz für interne Kommunikation.
-   **Hauptrisiko:** **Elevation of Privilege.** Ein Container-Ausbruch könnte vollen Host-Zugriff ermöglichen.

#### Design B: Der entkoppelte API-Client
-   **Beschreibung:** Der Agent ist bewusst von der internen Systemkomplexität entkoppelt.
-   **Kommunikation:** Der Agent kommuniziert ausschließlich über Standard-HTTPS mit einem zentralen **API-Gateway** (z.B. Kong, Traefik), das als einziger Eingangspunkt in den CDB-Stack fungiert.
-   **Vorteil:** Maximale Kontrolle und Sicherheit. Direkter Zugriff auf interne Systeme ist ausgeschlossen.
-   **Hauptrisiko:** Gering. Ein Angriff ist auf die von der API explizit erlaubten Aktionen beschränkt.

### 1.2. Härtung durch Advanced Sandboxing

Das Hauptrisiko des integrierten Modells (Container-Ausbruch) kann durch fortgeschrittene Sandboxing-Technologien entscheidend gemindert werden.

| Technologie | Funktionsweise | Sicherheit | Overhead |
| :--- | :--- | :--- | :--- |
| **Standard Container** | Nutzt Linux Namespaces & Cgroups zur Prozessisolation. | Gering (geteilter Kernel) | Gering |
| **gVisor (Google)** | Ein User-Space-Kernel, der als "Proxy" zwischen Container und Host-Kernel agiert. | Hoch | Mittel (I/O) |
| **Firecracker (AWS)** | Eine Micro-Virtual-Machine (µVM), die Hardware-Virtualisierung nutzt. | **Sehr Hoch** | Mittel (Ressourcen)|

### 1.3. Empfehlung: Hybride "Zero-Trust"-Architektur

Die robusteste Lösung kombiniert die Stärken beider Modelle:
1.  **Isolation:** Der Agent läuft in einer **maximal sicheren Sandbox (z.B. Firecracker-µVM)**.
2.  **Kommunikation:** Innerhalb der Sandbox kommuniziert der Agent ausschließlich mit einem **lokalen API-Proxy**.
3.  **Kontrolle:** Nur dieser lokale Proxy darf mit dem zentralen **API-Gateway** des Stacks kommunizieren, idealerweise über mTLS (mutual TLS).

Dieser Ansatz setzt ein Zero-Trust-Prinzip um, bei dem selbst interner Traffic als nicht vertrauenswürdig behandelt wird, und bietet so höchste Sicherheit.

---

## 2. Algorithmische Sicherheit ("Das Gewissen")

Diese Ebene stellt sicher, dass der Agent gar nicht erst versucht, gefährliche Aktionen auszuführen. Sie läuft *innerhalb* der sicheren Infrastruktur.

### 2.1. Das Drei-Schichten-Sicherheitsmodell (RL-Safety Framework)

Das Framework basiert auf drei ineinandergreifenden logischen Schichten, die eine Entscheidung von oben nach unten passieren muss:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CDB RL-SAFETY ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: POLICY LAYER (Soft Constraints via Lagrangian Methods)            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  RL Policy Engine (PPO-Lag / CPO)                                   │    │
│  │  • Objective: max E[R] s.t. E[C] ≤ d (z.B. CVaR, Drawdown)         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                        │
│  LAYER 2: CONSTRAINT LOGIC ENGINE (Hard Constraints via Action Masking)     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Action Masking Layer (Deterministische Filterung)                  │    │
│  │  • Position Limits, Margin Requirements, Order Size                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                        │
│  LAYER 3: RISK GATEKEEPER (Infrastructure Safeguards)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Pre-Trade Risk Layer + Kill-Switch                                 │    │
│  │  • AI-NOT-AUS (Soft/Hard Kill)                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

1.  **Layer 1: Policy Layer (Das "Wollen"):** Die RL-Policy (z.B. PPO) wird so trainiert, dass sie nicht nur den Ertrag maximiert, sondern auch weiche Nebenbedingungen (z.B. einen durchschnittlichen Drawdown) einhält.
2.  **Layer 2: Constraint Logic Engine (Das "Dürfen"):** Dies ist der wichtigste Baustein. Eine deterministische `Action Mask` filtert **vor jeder Entscheidung** den Aktionsraum des Agenten. Aktionen, die gegen harte Regeln verstoßen, werden mathematisch unmöglich gemacht.
3.  **Layer 3: Risk Gatekeeper (Die "Notbremse"):** Wenn übergeordnete Systemmetriken kritische Schwellenwerte überschreiten, wird ein unabhängiger **Kill-Switch-Service** aktiviert.

### 2.2. Implementierung der Constraint Logic Engine (CLE)

Die CLE ist das Herzstück der algorithmischen Sicherheit und läuft direkt im Agenten-Container. Sie berechnet für jeden Zustand eine Maske erlaubter Aktionen mit garantierter Latenz von < 2ms.

*Beispiel-Logik der Engine:*
```python
class ConstraintLogicEngine:
    def __init__(self, config: dict):
        # MiFID II RTS 6 konforme Hard Limits
        self.max_position_pct = config.get('max_position_pct', 0.20)
        self.max_drawdown_pct = config.get('max_drawdown_pct', 0.10)
        self.daily_loss_limit = config.get('daily_loss_limit', 0.03)

    def compute_action_mask(self, state: TradingState) -> np.ndarray:
        """Berechnet eine binäre Maske (True = Aktion erlaubt)."""
        mask = np.ones(len(TradingAction), dtype=bool)
        
        # Drawdown-Schutz (Tresor-Regel)
        if state.current_drawdown >= self.max_drawdown_pct:
            mask[:] = False # Alle Aktionen blockieren...
            mask[TradingAction.HOLD] = True # ...außer HOLD...
            if state.position != 0: # ...und Schließen der Position.
                mask[TradingAction.CLOSE_POSITION] = True
            return mask

        # Tägliches Verlustlimit
        if state.daily_pnl <= -self.daily_loss_limit * state.portfolio_value:
            # ... gleiche Logik wie beim Drawdown ...
        
        # ... weitere Checks für Position, Frequenz, etc. ...
        
        mask[TradingAction.HOLD] = True # HOLD ist immer erlaubt
        return mask
```

### 2.3. Kill-Switch als unabhängiger Sicherheitsdienst

Der "AI-NOT-AUS" (Kill-Switch) muss als hochprivilegierter, externer Service implementiert werden, der über das API-Gateway angesprochen wird. Der Agent selbst darf diesen Dienst niemals deaktivieren können; er empfängt dessen Zustand lediglich als Signal.

---

## 3. Abschließende Empfehlung: Ein ganzheitliches Sicherheitsmodell

Infrastruktur-Sicherheit und algorithmische Sicherheit sind keine Alternativen, sondern **zwingend notwendige, komplementäre Schichten**.

**Empfohlene Gesamtarchitektur:**

1.  **Infrastruktur-Basis:** Das **entkoppelte Modell mit API-Gateway** bietet die beste Kombination aus Sicherheit und Skalierbarkeit. Für maximale Sicherheit sollte eine **"Zero-Trust"-Architektur** mit Firecracker-µVMs in Betracht gezogen werden.

2.  **Algorithmische Sicherheit:** Das **RL-Safety Framework** muss *innerhalb* dieser sicheren Infrastruktur implementiert werden:
    -   Die **Constraint Logic Engine (Action Masking)** ist ein integraler Bestandteil des Agenten selbst.
    -   Der **Kill-Switch-Service** läuft als unabhängiger, hochprivilegierter Dienst.

Nur die Kombination aus einer sicheren "Festung" (Infrastruktur) und einem robusten "Gewissen" (Algorithmus) ermöglicht den verantwortungsvollen und resilienten Betrieb eines autonomen Trading-Agenten.

