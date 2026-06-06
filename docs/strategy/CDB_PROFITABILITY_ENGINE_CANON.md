# CDB Profitability Engine Canon

**Status:** Canonical (Draft)
**Issue Reference:** #3032, #3033
**Authority:** Strategy / Docs-Only
**Live-Readiness:** NO-GO (Echtgeld-Blocker aktiv)

---

## 1. Purpose / Status
Dieses Dokument definiert den kanonischen Rahmen für die Weiterentwicklung von Claire de Binare (CDB) zu einer **Profitability Engine**. Es dient als strategischer SSoT für die Einordnung von Strategy Candidates, Evidence-Anforderungen und den Übergang von Research zu Paper-Trading. 

**Status:** Dieses Dokument ist rein deklarativ. Es autorisiert keinen Live-Go und keine automatische Kapitalallokation.

---

## 2. Management Summary
CDB wird von einem reinen Trading-Bot zu einer systematischen **Profitability Engine** ausgebaut. Der Fokus verschiebt sich von "wie man tradet" (Core Execution) zu "was man tradet und warum" (Profitability Validation). Die Engine nutzt die ARVP (Automated Replay & Validation Pipeline) als zentrales Beweis-Werkzeug, um eine Pipeline von validierten Handelsstrategien (Candidates) aufzubauen.

---

## 3. Current Operating Boundary
- **Core Protection:** Der bestehende Trading-Core (BLUE/RED Stack) bleibt als stabiles Fundament geschützt.
- **Stage:** `trade-capable` (Board-Stage) erlaubt technischen Paper-Betrieb.
- **LR-050:** Bleibt `NO-GO`. Kein Echtgeld-Handel.
- **Data Blocker:** #3031 (Datenqualität) bleibt der primäre operative Blocker für verlässliche ARVP-Läufe.

---

## 4. Profitability Engine Zielbild
Die Profitability Engine ist eine Schicht *über* dem Core. Sie ist eine Fabrik für renditeorientierte Entscheidungen.
- **Input:** Rohdaten, Strategy Models.
- **Prozess:** Candidate Lifecycle -> ARVP Evidence -> League Table.
- **Output:** Validierte Evidence Packets, die eine statistische Erwartung von Rendite belegen.

---

## 5. Business-Ziel: Strategy Candidate Pipeline
Das primäre Ziel ist nicht "der eine Algorithmus", sondern eine **Pipeline**.
- Wir suchen Strategien, die unter verschiedenen Marktbedingungen (Regimes) stabil performen.
- Ein Candidate muss erst beweisen, dass er die "Execution Economics" (Gebühren, Spread, Slippage) schlägt, bevor er im Ranking aufsteigt.

---

## 6. Rendite-Stufenmodell
Wir klassifizieren Strategien nach ihrem Renditeziel und dem erforderlichen Evidence-Grad:
- **Tier 10:** 10% p.a. (Low Risk, High Stability).
- **Tier 20:** 20% p.a. (Standard Alpha).
- **Tier 30:** 30% p.a. (Aggressive Alpha, höhere Drawdown-Toleranz).
- **Tier 50+:** 50%+ p.a. (High Frequency / High Risk; nur für spezialisierte Sleeves).

---

## 7. Learning Loop vs. Trading Loop
- **Learning Loop (Offline):** Research -> Backtest -> ARVP -> Evidence. Hier findet die Optimierung statt.
- **Trading Loop (Runtime):** Signal -> Risk -> Execution. Hier findet nur die strikte Ausführung statt.
- **Regel:** Die Trading Loop lernt nicht autonom. Änderungen an der Logik müssen den Learning Loop vollständig durchlaufen.

---

## 8. Core Protection / No-Touch-Core
Der Trading-Core ist die "Black Box" der Ausführung. 
- Änderungen für die Profitability Engine dürfen die Stabilität des Core-Execution-Pfades nicht gefährden.
- Neue Logik wird bevorzugt als unabhängige Services oder Side-Cars implementiert.

---

## 9. Authority Rules
1. **Signal != Trade:** Ein Signal ist nur ein Vorschlag; Risk entscheidet (INV-002).
2. **AI != Authority:** KI-Vorschläge sind Research; nur Code/Config im Canon ist Wahrheit.
3. **Dashboard != Freigabe:** Visualisierungen sind Information; Governance-Dateien sind Autorität.
4. **Docs != Approval:** Dieses Dokument ist Plan; das Human Gate (`DELIVERY_APPROVED.yaml`) bleibt das Schloss.

---

## 10. Candidate Lifecycle
1. **Inception:** Rohe Idee / Research.
2. **Backtest:** Erste statistische Prüfung.
3. **ARVP Candidate:** Integration in die ARVP; technischer Contract-Check.
4. **Validated Candidate:** Evidence Packet liegt vor (ARVP-Läufe über mehrere Regimes).
5. **Paper Active:** Betrieb im Paper-Trading zur Echtzeit-Validierung.
6. **Sleeve-Ready:** Bereit für (zukünftige) Kapitalallokation.

---

## 11. Promotion Gate Matrix
| Von | Nach | Bedingung |
|---|---|---|
| Backtest | ARVP | Dataset Quality Gate PASS (#3035) |
| ARVP | Validated | Evidence Packet vollständig (min. 3 Regimes) |
| Validated | Paper | Human Approval + Technical Readiness |

---

## 12. Evidence Requirements
Ein Evidence Packet MUSS enthalten:
- **Deterministic Trace:** Jede Entscheidung im Testzeitraum ist nachvollziehbar.
- **Regime Scorecard:** Performance-Metriken pro Marktphase.
- **Execution Realism:** Simulation von Fees, Slippage und Latenz.
- **Dataset Fingerprint:** Eindeutiger Bezug auf die verwendeten Quelldaten.

---

## 13. Dataset Quality as Business Gate
Datenqualität ist kein technisches Detail, sondern ein **Business-Risiko**. 
- Lückenhafte oder falsche Daten führen zu "Halluzinationen" der Profitabilität.
- Das Dataset Quality Gate (#3035) blockt jede Promotion eines Candidates, dessen Datenbasis nicht verifiziert ist.

---

## 14. Open-Source Tooling Posture
Wir folgen dem Prinzip: **Build the Core, Borrow the Tools.**

| Posture | Tools / Frameworks |
|---|---|
| **Build (Core)** | Event-Bus, Risk-Engine, Replay-Loop, Audit-Ledger. |
| **Use (P0 Candidates)** | **Pydantic/jsonschema** (Contracts), **Pandera** (Data Quality), **Rich/Jinja2** (Reporting). |
| **Borrow (Patterns)** | CCXT (nur Fee/Metadata Referenz), Freqtrade, Hummingbot, LEAN, Backtrader (Reference/Borrow only). |
| **Reject (Core-Dep)** | Keine tiefen Abhängigkeiten von monolithischen Trading-Frameworks im Core. |

---

## 15. Roadmap Phase 0-8

- **Phase 0:** #3031 Datenblocker sichtbar halten (Calibration/Data Quality).
- **Phase 1:** #3033 Profitability Canon (Dieses Dokument).
- **Phase 2:** #3034 Candidate Contract + Evidence Packet (Definition der Schnittstellen).
- **Phase 3:** #3035 Dataset Quality Gate (Automatisierte Datenprüfung).
- **Phase 4:** ARVP Batch Runner + Scenario Packs (Skalierung der Tests).
- **Phase 5:** Execution Economics (Integration von Fees/Slippage-Modellen).
- **Phase 6:** Strategy League Table (Vergleich und Ranking der Candidates).
- **Phase 7:** Paper Portfolio + Capital Sleeves Spec (Multi-Strategie-Simulation).
- **Phase 8:** Control Room + Micro-Live-Readiness-Pfad (Monitoring, kein Auto-Live).

---

## 16. Mapping to Existing Issues
- **Parent:** #3032 (Profitability Engine Parent)
- **Active Blockers:** #3031 (Data Blocker), #1900 (ARVP North-Star)
- **Parked / Scaling:** #205 (Multi-Strategy), #211 (Multi-Asset) – Bleiben geparkt bis Phase 6/7.
- **Live Roadmap:** #2985 (Separate Live-Readiness-Schiene).

---

## 17. Stop Criteria
Die Engine stoppt oder wird zurückgestuft, wenn:
- Die Datenqualität unter die Grenzwerte fällt.
- Replay-Determinismus verloren geht.
- "Execution Realism" eine signifikante Divergenz zu Paper-Ergebnissen zeigt.

---

## 18. Non-Goals
- Automatischer Live-Handel.
- Ersatz von Human-Governance durch Algorithmen.
- Integration von Drittanbieter-Bots als Core-Execution.

---

## 19. Next Slices after #3033
Nach Abschluss von #3033 (Canon) folgen:
1. **#3034:** Technische Spezifikation des Candidate Contracts.
2. **#3035:** Implementierung des Dataset Quality Gates (Pandera-basiert).
