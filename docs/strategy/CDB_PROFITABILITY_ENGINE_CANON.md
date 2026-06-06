# CDB Profitability Engine Canon

**Status:** Canonical
**Mode:** Docs-only
**Issue Reference:** #3032, #3033
**Authority:** Strategy / Governance / Docs
**Live-Readiness:** NO-GO
**Implementation Approval:** none

## 1. Zweck und Status

Dieses Dokument definiert den kanonischen Rahmen fuer Claire de Binare als **Profitability Engine**.
Es bringt die neue Business- und Governance-Schicht offiziell ins Repo und dient als Grundlage fuer:

- #3034 Candidate Contract + Evidence Packet v1
- #3035 Dataset Quality Gate

Das Dokument ist strikt:

- docs-only
- kein Live-Go
- kein Echtgeld-Go
- keine Runtime-Aenderung
- keine DB-Migration
- keine Implementierungsfreigabe
- keine automatische Promotion
- keine Risk-/Execution-/Allocation-Aenderung

Board-Stage `trade-capable` bleibt orthogonal und autorisiert kein Live-Kapital, keinen Echtgeldbetrieb und keine Strategie-Freigabe.
LR bleibt NO-GO.

## 2. Executive Summary

CDB wird zur Profitability Engine.

Ziel ist eine wiederholbare Strategie-Fabrik:

Ideen rein -> Kandidatenkarte -> Evidence Sheet -> Data Quality Gate -> ARVP/Replay -> Ranking -> Paper-Kandidat -> spaeter Micro-Live-Kandidat nur ueber separate Live-Readiness-Gates.

Der bestehende Core bleibt geschuetzt.
Die Profitability Engine sitzt ueber bzw. neben dem Core.

Wichtig:

- Learning verbessert Wissen.
- Trading fuehrt nur kontrolliert gepruefte Kandidaten aus.
- ARVP ist Evidence, keine Freigabe.
- Backtest ist kein Live-Beweis.
- Paper ist kein Live-Beweis.

## 3. Business-Zielbild

Die Profitability Engine verfolgt ein klares Business-Ziel:

- Renditeorientierung
- Marktreife vorbereiten
- mehrere Strategiekandidaten parallel pruefen
- schlechte Kandidaten schnell verwerfen
- gute Kandidaten haerter validieren
- Paper-Portfolio vorbereiten
- Kapitalsteuerung spaeter ueber eigene Gates fuehren

Die Rendite entsteht nicht durch:

- Core-Umbau
- Live-Abkuerzung
- KI-Autoritaet
- Dashboard-Freigaben
- automatische Promotion

Rendite entsteht ueber:

- Strategy Candidate Pipeline
- Evidence
- Data Quality
- ARVP
- Execution Economics
- Ranking
- Paper-Portfolio
- spaetere Capital Sleeves

## 4. Rendite-Stufenmodell

Die Stufen sind Forschungs- und Validierungsziele, keine Garantie und kein Live-Go.

| Stufe | Ziel | Bedeutung |
|---|---|---|
| Stage A | 10 % Monatsziel | Forschungs- und Validierungsziel |
| Stage B | 20 % Monatsziel | nur mit mehreren Kandidaten, Symbolen und Regimen |
| Stage C | 30 % Monatsziel | opportunistische Hochleistungsstufe |
| Stage D | 50 % Monatsziel | nur Experimental Sleeve, stark limitiert, High Risk |

Regeln:

- keine Renditegarantie
- kein Echtgeld-Go
- kein Live-Go
- keine direkte Ableitung von Backtest-Erfolgen auf Live-Kapital

## 5. No-Touch-Core

Der Core ist nicht das Experimentierfeld.

Nicht anfassbar fuer diese Schicht:

- Signal
- Risk
- Execution
- DB Writer
- Risk-Layer
- KillSwitch
- Circuit Breaker
- Execution Gate
- LR-SSOT

Zusatzregeln:

- keine produktiven Orders, Fills, Positions, Secrets oder Live Risk State in neue Research-/Brain-/Profitability-Schichten
- keine automatische Promotion
- kein Dashboard-Approval
- keine AI-Approval
- keine Docs-Approval
- keine Umgehung von Risk, KillSwitch oder LR-Gates

## 6. Learning Loop vs Trading Loop

### Learning Loop

Candidate -> Backtest -> ARVP -> Scenario Stress -> Evidence -> Lessons -> Ranking -> Promotion Recommendation

Zweck:

- Wissen aufbauen
- Kandidaten vergleichen
- Drift sichtbar machen
- schlechte Kandidaten verwerfen

### Trading Loop

Candidate nur nach Gates -> Strategy Context -> Scope/Capital -> Risk -> KillSwitch -> Execution Gate -> Operator/Human Gate -> moeglicher Trade

Zweck:

- nur kontrolliert gepruefte Kandidaten ausfuehren
- keine experimentelle Kurzschlussschleife

Kernsatz:

Learning verbessert Wissen. Trading fuehrt nur kontrolliert gepruefte Kandidaten aus.

## 7. Candidate Lifecycle

Mindestens folgende Status gehoeren zum kanonischen Lifecycle:

- IDEA
- SPECIFIED
- BACKTESTED
- ARVP_VALIDATED
- STRESS_TESTED
- PAPER_CANDIDATE
- PAPER_VALIDATED
- MICRO_LIVE_CANDIDATE
- CAPITAL_SCALING_CANDIDATE
- REJECTED
- PARKED
- UNSAFE
- SUPERSEDED
- STALE

### Terminal- und Sonderstatus

| Status | Bedeutung |
|---|---|
| REJECTED | Kandidat ist fachlich oder evidenzseitig verworfen |
| PARKED | Kandidat bleibt moeglich, aber ohne aktiven Deliveryschritt |
| UNSAFE | Kandidat verletzt Risk-, Data- oder Safety-Grenzen |
| SUPERSEDED | Kandidat wurde durch eine neuere Variante ersetzt |
| STALE | Kandidat ist veraltet oder muss neu bewertet werden |

## 8. Promotion Gate Matrix

Jede Stufe braucht:

- Entry Criteria
- Evidence Required
- Stop Criteria
- Allowed Next Gate
- Reject / Park / Unsafe Gruende

| Von -> Nach | Entry Criteria | Evidence Required | Stop Criteria | Allowed Next Gate | Reject / Park / Unsafe Gruende |
|---|---|---|---|---|---|
| IDEA -> SPECIFIED | Problem, Hypothese, Strategy Family, Symbol Universe, Timeframe, Direction sind benannt | kurze Spezifikation, erste Risiko- und Execution-Annahmen | unklare Hypothese, Duplikat, unbounded scope, Safety-Konflikt | SPECIFIED | REJECTED bei fehlender Begrenzung, PARKED bei fehlendem Hebel, UNSAFE bei Risk-Konflikt |
| SPECIFIED -> BACKTESTED | Contract ist vollstaendig genug fuer einen reproduzierbaren Test | Backtest-Report, Parameter-Set, Dataset-Fingerprint, Netto-Sicht | Daten fehlen, Contract ist lueckenhaft, Test ist nicht reproduzierbar | BACKTESTED | REJECTED bei unvollstaendigem Contract, UNSAFE bei nicht erlaubten Daten oder Bias |
| BACKTESTED -> ARVP_VALIDATED | Backtest bestand mit Kostenannahmen und klares Zielbild ist vorhanden | ARVP/Replay-Trace, deterministischer Lauf, Fingerprint, Kosten- und Friction-Sicht | Replay driftet, Daten sind nicht vergleichbar, ARVP fehlt | ARVP_VALIDATED | REJECTED bei fehlender Evidence, PARKED bei offener Datenlage, UNSAFE bei deterministischer Verletzung |
| ARVP_VALIDATED -> STRESS_TESTED | ARVP ist nachvollziehbar und ein Szenario-Paket ist definiert | Scenario Stress, Sensitivity, Worst-Case, Lessons, Ranking-Signale | zu optimistische Annahmen, fehlende Stressvarianz, instabile Ergebnisse | STRESS_TESTED | REJECTED bei fragiler Performance, PARKED bei fehlender Szenariodeckung |
| STRESS_TESTED -> PAPER_CANDIDATE | Stress ist akzeptabel und Unsafe-Zonen sind ausgeschlossen oder klar begrenzt | Stress-Report, Recommendation, Loss-Profile, Drift-Befund | Drawdown zu hoch, Slippage zu hoch, Execution-Gap zu gross | PAPER_CANDIDATE | REJECTED bei fragiler oder unrentabler Kostenstruktur, UNSAFE bei Safety-Konflikt |
| PAPER_CANDIDATE -> PAPER_VALIDATED | Paper-Betrieb oder Paper-Accounting ist als realistische Naeherung belegbar | Paper-Ledger, Replay-vs-Paper-Compare, Operator-Notizen, Fingerprints | Paper-Daten sind nicht vergleichbar, Event-Kette ist unvollstaendig | PAPER_VALIDATED | PARKED bei unklarer Vergleichbarkeit, REJECTED bei klar negativem Befund |
| PAPER_VALIDATED -> MICRO_LIVE_CANDIDATE | Separate Live-Readiness-Gates sind bestanden und ein explizites Human Approval liegt vor | Cleared LR-SSOT, Human Approval, Live-Readiness-Paket, Capital-Sleeve-Konzept, Risk- und KillSwitch-SSOT | irgendein Live-Go- oder Echtgeld-Go wird impliziert, LR-Grenzen sind offen oder nicht freigegeben | MICRO_LIVE_CANDIDATE | UNSAFE bei direktem Live-Bezug ohne freigegebene LR-Gates, REJECTED bei fehlender readiness |

### Gate-Logik

- Ein Kandidat darf nur in den naechsten Zustand wechseln, wenn die Evidence den aktuellen Zustand eindeutig traegt.
- Ein Kandidat wird geparkt, wenn der naechste Schritt sinnvoll ist, aber ein externer Blocker fehlt.
- Ein Kandidat wird verworfen, wenn er fachlich, technisch oder riskseitig nicht tragfaehig ist.
- Ein Kandidat wird als unsafe markiert, wenn er Risiken, Data-Grenzen oder LR-/Live-Grenzen verletzt.

## 9. Evidence-Grundsatz

Brutto-Rendite reicht nicht.

Netto zaehlt nach:

- Fees
- Spread
- Slippage
- Rejections
- Latency-Verlusten

Evidence muss sein:

- reproduzierbar
- deterministisch
- hash- oder fingerprint-faehig
- auditierbar

Pflichtregeln:

- Data Quality Gate ist vor ernsthafter Bewertung Pflicht
- Replay-vs-Paper-Drift muss sichtbar werden
- ARVP ist Evidence, keine Freigabe
- Backtest und Paper sind keine Live-Beweise

## 10. Geplante Profitability-Epics

Kanonische Roadmap fuer die Profitability-Schicht:

- #3032 Parent
- #3033 Canon
- #3034 Candidate Contract + Evidence Packet
- #3035 Dataset Quality Gate
- spaetere Child-Slices:
  - ARVP Batch Runner
  - Scenario Pack Library
  - Execution Economics v1
  - Strategy League Table v1
  - Capital Sleeves Spec / Paper Accounting
  - Profitability Control Room
  - Paper-to-Micro-Live Ramp

## 11. Mapping zu vorhandenen Issues

| Issue | Einordnung |
|---|---|
| #3031 | aktueller operativer ARVP/Data-Blocker fuer replaybare 1m-Candles |
| #1900 | ARVP North-Star / Paper-Phase-Multiplier |
| #2961 | Replay-vs-Paper Calibration Batch Anker |
| #2971 | Batch Compare Anker fuer Window Bank |
| #1784 | Paper-Betriebsfaden / operativer Kontrollfaden |
| #1445 | spaeterer Cockpit- oder Profitability-Control-Room-Anker |
| #205 | geparkt, spaeterer Multi-Strategy-Routing-Anker |
| #211 | geparkt, spaeterer Multi-Asset- und Portfolio-Anker |
| #2985 | getrennte Live-Roadmap |

## 12. Open-Source Tooling Policy

Entscheidungsmuster:

- BUILD: CDB-spezifische Governance, Candidate Lifecycle, Evidence-Semantik, Promotion Gates, Capital-Sleeve-Regeln
- USE: kleine lizenzsaubere Libraries nach eigener Tooling-Entscheidung
- BORROW: Muster aus bestehenden Quant-/Reporting-/Datenqualitaets-Tools
- REFERENCE_ONLY: grosse Frameworks als Lernquelle
- REJECT: fremde Bot-Cores, fremde Live-Execution, unklare Lizenz, zu viel Magic, Overfitting-Risiko

### Konkrete Einordnung

| Posture | Beispiele |
|---|---|
| BUILD | Governance, Candidate Lifecycle, Evidence Contract Semantics, Promotion Gates |
| USE | Pydantic, jsonschema, Pandera, Rich, Jinja2 |
| BORROW | Muster aus vectorbt, quantstats oder aehnlichen Analysewerkzeugen |
| REFERENCE_ONLY | Freqtrade, Hummingbot, LEAN, Backtrader, Zipline, NautilusTrader |
| REJECT | fremde Bot-Cores, fremde Live-Execution, nicht saubere Lizenz- oder Magic-Last |

Wichtig:

- Tooling-Entscheidungen gehoeren nicht als Code in #3033.
- Tooling-Entscheidungen werden spaeter als eigene Issue-Slices spezifiziert.

## 13. Stop-Kriterien

Planung oder Umsetzung stoppt, wenn:

- Live- oder Echtgeld-Go impliziert wird
- Risk, KillSwitch oder LR-Gates umgangen werden
- Backtest, Paper oder ARVP als Live-Beweis verkauft werden
- Candidate Registry sofort als produktive DB erzwungen wird
- Capital Sleeves direkt Risk- oder Allocation-Code beruehren, bevor Contracts und Evidence stehen
- Open Source als fremder Bot-Core uebernommen werden soll
- Renditeziele ohne Kosten-, Drawdown- oder Drift-Sicht diskutiert werden
- Scope-Wachstum nicht als eigenes Issue abgegrenzt wird
- Dashboard, AI oder Docs als Approval benutzt werden

## 14. Naechster Arbeitsfluss

Der Arbeitsfluss ist explizit gestuft:

1. Nach #3033 kommt #3034.
2. Nach #3034 kommt #3035.
3. #3031 bleibt parallel und priorisiert als Datenblocker.
4. Erst danach folgen:
   - ARVP Batch Runner
   - Scenario Packs
   - Execution Economics
   - Strategy League Table

## 15. Non-Goals

- kein Code ausser optionaler Docs-Index-Referenz
- keine Dependency-Einfuehrung
- keine Tooling-Implementation
- keine DB
- keine Runtime
- keine Risk-/Execution-/Allocation-Aenderung
- keine Live-Roadmap-Aenderung ausser Referenz
- keine bestehenden Issues schliessen ausser #3033 nach erfolgreichem Merge

## 16. Status-Semantik fuer spaetere Arbeit

Wenn diese Schicht spaeter konkretisiert wird, gelten diese Bedeutungen:

- IDEA: rohe Idee ohne belastbaren Contract
- SPECIFIED: klar begrenzte Spezifikation
- BACKTESTED: erster reproduzierbarer statistischer Check
- ARVP_VALIDATED: replayfaehige Evidence vorhanden
- STRESS_TESTED: Szenario- und Robustheitspruefung bestanden oder explizit geparkt
- PAPER_CANDIDATE: fuer Paper-Betrieb geeignet, aber noch nicht validiert
- PAPER_VALIDATED: Paper-Evidence und Replay-vs-Paper-Compare tragen den Kandidaten
- MICRO_LIVE_CANDIDATE: nur nach separaten Live-Readiness-Gates, clearem LR-SSOT und explizitem Human Approval
- CAPITAL_SCALING_CANDIDATE: spaetere Skalierungsstufe, nie automatisch
- REJECTED: verworfen
- PARKED: belegt, aber momentan nicht weiter verfolgt
- UNSAFE: verletzt Risiko-, Daten- oder Safety-Grenzen
- SUPERSEDED: durch eine neuere Variante ersetzt
- STALE: veraltet oder neu zu bewerten

## 17. Abschlussregel

Dieses Dokument ist der strategische Canon fuer die Profitability Engine.
Es erzeugt keine Freigabe fuer Live-Go, Echtgeld-Go, Runtime-Aenderung oder DB-Mutation.
Es definiert die Begriffe, Grenzen und Reihenfolge fuer die nachfolgenden Issue-Slices.
