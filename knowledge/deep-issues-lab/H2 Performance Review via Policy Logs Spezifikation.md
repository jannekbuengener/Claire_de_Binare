---
id: CDB-DR-H2
title: 'Performance Review via Policy Logs'
subtitle: 'Spezifikation des Audit-Logging- und Analyse-Frameworks'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-17'
status: 'Draft'
tags:
  - Audit-Log
  - Logging
  - Performance-Analyse
  - PostgreSQL
  - TimescaleDB
---

# Performance Review via Policy Logs

> **Management Summary**
>
> Dieses Dokument spezifiziert das **Audit-Logging-Modul**, das für die persistente Aufzeichnung aller Policy-Entscheidungen im *Claire de Binare*-System verantwortlich ist. Ziel ist es, einen lückenlosen, analysierbaren und regulatorisch konformen Audit-Trail zu schaffen, der eine tiefgehende Performance-Analyse und Fehlersuche ermöglicht.
>
> Die Architektur basiert auf einer **PostgreSQL-Datenbank mit TimescaleDB-Erweiterung**, um große Mengen an Zeitreihendaten effizient zu speichern und abzufragen. Das Schema ist so konzipiert, dass jede Entscheidung, ihr Kontext und ihr späteres Ergebnis (Outcome) miteinander verknüpft werden können. Dies ermöglicht komplexe Abfragen zur Korrelation von Features und Handelsentscheidungen mit der tatsächlichen Performance.

---

## 1. Speicher-Backend

-   **Technologie:** `postgresql_timescale`
-   **Begründung:** PostgreSQL bietet Robustheit und Transaktionssicherheit. Die TimescaleDB-Erweiterung optimiert die Datenbank für Zeitreihendaten, was zu massiven Leistungsverbesserungen bei Abfragen über Zeitfenster führt.
-   **Tabellenname:** `policy_decisions`

```json
{
  "module": "audit_logging",
  "storage_backend": "postgresql_timescale",
  "table_name": "policy_decisions"
}
```

## 2. Schema-Spezifikation

Die Tabelle `policy_decisions` speichert alle relevanten Informationen zu jeder einzelnen Entscheidung des Systems.

-   **`decision_id` (UUID, Primary Key):** Einzigartiger Identifikator für jede Entscheidung.
-   **`timestamp` (TIMESTAMPTZ, Partition Key):** Zeitstempel der Entscheidung. Dient als Partition Key für TimescaleDB.
-   **`strategy_id` (VARCHAR(32)):** ID der Strategie, die das ursprüngliche Signal generiert hat.
-   **`symbol` (VARCHAR(16)):** Das gehandelte Symbol (z.B. `BTCUSDT`).
-   **`action` (VARCHAR(10)):** Die finale Aktion nach allen Filter- und Risikoprüfungen (`BUY`, `SELL`, `HOLD`, `REJECT`).
-   **`risk_score` (FLOAT):** Ein optionaler Score, der das Risiko der Entscheidung quantifiziert.
-   **`execution_context` (JSONB):** Ein JSON-Objekt, das den vollständigen Kontext der Entscheidung speichert (z.B. alle Feature-Werte, die zur Entscheidung geführt haben, Ablehnungsgründe).
-   **`outcome_metrics` (JSONB, Nullable):** Ein JSON-Objekt, das nachträglich mit den Ergebnissen der Entscheidung befüllt wird (z.B. P&L nach 1h, 24h).

```json
"schema_spec": {
  "decision_id": "UUID (Primary Key)",
  "timestamp": "TIMESTAMPTZ (Partition Key)",
  "strategy_id": "VARCHAR(32)",
  "symbol": "VARCHAR(16)",
  "action": "VARCHAR(10) [BUY, SELL, HOLD, REJECT]",
  "risk_score": "FLOAT",
  "execution_context": "JSONB",
  "outcome_metrics": "JSONB (Nullable)"
}
```

## 3. Indexierungsstrategie

Um schnelle Abfragen zu ermöglichen, werden spezifische Indizes definiert:

-   **GIN-Indizes (`gin_indices`):** Auf das `execution_context`-Feld, um komplexe Abfragen innerhalb des JSON-Objekts zu beschleunigen.
-   **B-Tree-Indizes (`btree_indices`):** Auf häufig gefilterte Spalten wie `strategy_id`, `symbol` und `action`.

```json
{
  "indexing_strategy": {
    "gin_indices": ["execution_context"],
    "btree_indices": ["strategy_id", "symbol", "action"]
  }
}
```

## 4. Aufbewahrungsrichtlinie (Retention Policy)

Die Aufbewahrungsdauer der Daten wird je nach Wichtigkeit gestaffelt:

-   **`trade_decisions`:** `infinite` (Handelsentscheidungen werden für regulatorische Zwecke unbegrenzt aufbewahrt).
-   **`hold_decisions`:** `30_days` (Entscheidungen, nichts zu tun, sind weniger kritisch).
-   **`rejected_decisions`:** `12_months` (Abgelehnte Entscheidungen werden für spätere Analysen zur Strategieverbesserung aufbewahrt).

## 5. Abfragemuster (Query Patterns)

Das Schema ist für typische analytische Abfragen optimiert:

-   **Analyse von Ablehnungsgründen:**
    ```sql
    SELECT execution_context->>'rejection_reason', count(*)
    FROM policy_decisions
    WHERE action='REJECT'
    GROUP BY 1;
    ```

-   **Korrelationsanalyse zwischen Features und Performance:**
    ```sql
    SELECT execution_context->'inputs'->>'feature_X', outcome_metrics->>'pnl_1h'
    FROM policy_decisions
    WHERE action='BUY';
    ```

## 6. Outcome Attribution (Ergebniszuweisung)

Um die Qualität von Entscheidungen bewerten zu können, wird der tatsächliche Erfolg (`Outcome`) nachträglich mit der Entscheidung verknüpft.

-   **Zeitfenster:**
    -   `short_term`: 1 Stunde.
    -   `medium_term`: 24 Stunden.
-   **Metrik:** `realized_and_unrealized_pnl` (Realisierter und unrealisierter Gewinn/Verlust).

Ein separater Prozess aktualisiert das `outcome_metrics`-Feld in der `policy_decisions`-Tabelle für alle offenen Entscheidungen, deren Zeitfenster abgelaufen ist.

