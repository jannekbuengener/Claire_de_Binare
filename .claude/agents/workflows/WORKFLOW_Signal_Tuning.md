# WORKFLOW_Signal_Tuning – Handelsfrequenz & Signalqualität

## Ziel

Anpassung der Signalkonfiguration (z. B. Momentum-Schwellen, Filter wie RSI) mit dem Ziel:

- Handelsfrequenz moderat erhöhen,
- Winrate ≥ 50 % beibehalten,
- bestehende Risikoarchitektur respektieren.

---

## Preconditions

- Aktuelle Signalkonfig im Repo vorhanden (z. B. `backoffice/services/signal_engine/config.py`).
- Analyse-Dokument „Handelsfrequenz und Signalqualität“ liegt im Backoffice vor.
- MCP-Server aktiv: `filesystem`, `agents-sync`, `github-official`, `cdb-logger`.

---

## Phase A – Analyse

1. Governance & Rolle
   - Orchestrator zieht Definition für „Strategy/Signal Engineer“ aus `AGENTS.md` via `agents-sync`.
2. Input-Dokumente
   - `filesystem.read_file`:
     - Signalkonfig (z. B. `signal_engine/config.py`),
     - Analyse-Dokument zu Handelsfrequenz/Signalqualität.
3. Daten / Kennzahlen (optional)
   - Falls vorhanden: Analytics-Skripte / Metriken aus Tests/Backtests einbeziehen.
4. Vorschlag erarbeiten
   - Ableitung eines Parameter-Sets:
     - neue Schwellenwerte,
     - zusätzliche Filter (RSI, Trendfilter, Volumenfilter),
     - Schutzmechanismen gegen zu aggressive Frequenz.
5. Logging
   - `cdb-logger.log_event` – `SIGNAL_TUNING_ANALYSIS_COMPLETED`.
6. Output
   - Analyse-Report:
     - IST-Parameter,
     - SOLL-Parameter,
     - erwartete Auswirkungen (Trades/Tag, Winrate, Drawdown),
     - Rollback-Plan.

---

## Phase B – Delivery (nach Freigabe)

1. Branching
   - Branch-Name: `signal-tuning-YYYYMMDD`.
2. Änderungen im Repo
   - `filesystem.write_file`:
     - Anpassung der Signalkonfiguration gemäß Change-Plan.
   - Optional: ergänzende Doku in:
     - `Risikomanagement-Logik.md`,
     - Service-README des Signal-Engines.
3. Commit & PR
   - `github-official`:
     - Commit mit Message „Signal engine parameter tuning (frequency & quality)“.
     - PR Richtung `main` inkl.:
       - Parameterdiff,
       - Verweis auf Analyse-Dokument,
       - geplanten Monitoring-/Backtest-Step nach Merge.
4. Logging
   - `cdb-logger.log_event` – `SIGNAL_TUNING_PR_CREATED` + PR-URL.

---

## Phase C – Beobachtung (optional)

- Nach Deploy / Papertrading:
  - Orchestrator kann in einem Follow-up-Workflow
    - neue Performance-Metriken sammeln,
    - Abweichungen dokumentieren,
    - ggf. Rollback oder weitere Feintuning-Schritte vorschlagen.

---

## Erfolgsindikatoren

- Mehr Trades/Tag innerhalb des definierten Zielkorridors.
- Winrate bleibt ≥ 50 %.
- Kein Verstoß gegen bestehende Risikolimits.
