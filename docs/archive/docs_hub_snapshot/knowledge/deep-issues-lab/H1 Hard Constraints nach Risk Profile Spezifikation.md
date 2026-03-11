---
id: CDB-DR-H1
title: 'Spezifikation für Harte Constraints nach Risikoprofil'
subtitle: 'Design der Pre-Execution Blocking Engine'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Hard Constraints
  - Risikoprofil
  - Risikomanagement
  - Pre-Execution
---

# Spezifikation für Harte Constraints nach Risikoprofil

> **Management Summary**
>
> Dieses Dokument spezifiziert die **Hard Constraints Engine**, eine kritische Sicherheitskomponente im *Claire de Binare*-System. Ihre Aufgabe ist es, vor der Ausführung jeder Order eine Reihe von unveränderlichen, harten Regeln zu überprüfen und die Order bei einer Verletzung zu blockieren (`pre_execution_blocking`).
>
> Die Constraints sind dynamisch an das aktuell aktive **Risikoprofil** (`CONSERVATIVE`, `MODERATE`, `AGGRESSIVE`) des Systems gekoppelt. Dies ermöglicht eine flexible, aber streng durchgesetzte Risikosteuerung. Im Fehlerfall oder bei inkonsistenten Daten greift ein `fail_safe_mode`, der alle Transaktionen ablehnt.

---

## 1. Modul-Spezifikation

-   **Modul:** `hard_constraints_engine`
-   **Durchsetzungsebene:** `pre_execution_blocking` (Blockierung vor der Order-Ausführung).
-   **Fail-Safe-Modus:** `reject_all` (Alle Orders ablehnen, wenn ein Fehler auftritt).

## 2. Constraint-Definitionen nach Risikoprofil

Die folgenden Constraints werden basierend auf dem aktiven Risikoprofil durchgesetzt.

### 2.1. `max_leverage` (Maximaler Hebel)

-   **Beschreibung:** Absolut maximal erlaubter Hebel pro Position.
-   **Scope:** `per_order` (wird für jede Order geprüft).
-   **Profile:**
    -   `CONSERVATIVE`: **1x**
    -   `MODERATE`: **3x**
    -   `AGGRESSIVE`: **5x**

### 2.2. `max_position_size_equity_pct` (Maximale Positionsgröße)

-   **Beschreibung:** Maximaler gehebelter Wert einer Position im Verhältnis zum Gesamtkapital.
-   **Scope:** `portfolio_state` (berücksichtigt den gesamten Portfoliozustand).
-   **Profile:**
    -   `CONSERVATIVE`: **10 %** des Kapitals.
    -   `MODERATE`: **25 %** des Kapitals.
    -   `AGGRESSIVE`: **50 %** des Kapitals.

### 2.3. `daily_drawdown_lockout_bps` (Tagesverlust-Sperre)

-   **Beschreibung:** Wenn der realisierte + unrealisierte Tagesverlust diesen Wert in Basispunkten überschreitet, wird das Eröffnen neuer Positionen gesperrt.
-   **Scope:** `accumulated_daily` (wird über den Tag akkumuliert).
-   **Reset-Zeit:** Täglich um `00:00 UTC`.
-   **Profile:**
    -   `CONSERVATIVE`: **200 bps** (-2.0 %)
    -   `MODERATE`: **500 bps** (-5.0 %)
    -   `AGGRESSIVE`: **1000 bps** (-10.0 %)

### 2.4. `min_stop_loss_distance_pct` (Minimale Stop-Loss-Distanz)

-   **Beschreibung:** Eine Order wird abgelehnt, wenn kein Stop-Loss gesetzt ist oder dieser weiter entfernt ist als der definierte Prozentsatz.
-   **Scope:** `per_order`.
-   **Profile:**
    -   `CONSERVATIVE`: **5 %**
    -   `MODERATE`: **10 %**
    -   `AGGRESSIVE`: `null` (Kein hartes Limit, wird durch eine weiche Policy geregelt).

### 2.5. `symbol_whitelist` (Handelbare Symbole)

-   **Beschreibung:** Erlaubt den Handel nur mit den in der Whitelist definierten Symbolen.
-   **Scope:** `static_config` (statische Konfiguration).
-   **Profile:**
    -   `CONSERVATIVE`: `["BTCUSDT", "ETHUSDT"]`
    -   `MODERATE`: `["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]`
    -   `AGGRESSIVE`: `["ALL_TOP_20"]` (Alle 20 größten Assets nach Marktkapitalisierung).

## 3. Fehlercodes (Error Codes)

Wenn ein Constraint verletzt wird, gibt die Engine einen spezifischen Fehlercode zurück, um eine genaue Analyse zu ermöglichen.

-   **RC_001:** "Leverage exceeds profile limit"
-   **RC_002:** "Position size too large for equity"
-   **RC_003:** "Daily loss limit reached (Cool-down active)"
-   **RC_004:** "Symbol not in whitelist"
-   **RC_005:** "Risk State Data Stale (>5s)"

