# CDB Profitability Engine Canon

**Status:** Canonical (Draft)
**Issue Reference:** #3032, #3033
**Authority:** Strategy / Docs-Only
**Live-Readiness:** NO-GO (Echtgeld-Blocker aktiv)

---

## 1. Purpose / Status
Dieses Dokument definiert den kanonischen Rahmen fÃ¼r die Weiterentwicklung von Claire de Binare (CDB) zu einer **Profitability Engine**. Es dient als strategischer SSoT fÃ¼r die Einordnung von Strategy Candidates, Evidence-Anforderungen und den Ãœbergang von Research zu Paper-Trading.

**Status:** Dieses Dokument ist rein deklarativ. Es autorisiert keinen Live-Go und keine automatische Kapitalallokation.

---

## 2. Management Summary
CDB wird von einem reinen Trading-Bot zu einer systematischen **Profitability Engine** ausgebaut. Der Fokus verschiebt sich von "wie man tradet" (Core Execution) zu "was man tradet und warum" (Profitability Validation). Die Engine nutzt die ARVP (Automated Replay & Validation Pipeline) als zentrales Beweis-Werkzeug, um eine Pipeline von validierten Handelsstrategien (Candidates) aufzubauen.

---

## 3. Current Operating Boundary
- **Core Protection:** Der bestehende Trading-Core (BLUE/RED Stack) bleibt als stabiles Fundament geschÃ¼tzt.
- **Stage:** `trade-capable` (Board-Stage) erlaubt technischen Paper-Betrieb.
- **LR-050:** Bleibt `NO-GO`. Kein Echtgeld-Handel.
- **Data Blocker:** #3031 (DatenqualitÃ¤t) bleibt der primÃ¤re operative Blocker fÃ¼r verlÃ¤ssliche ARVP-LÃ¤ufe.

---

## 4. Profitability Engine Zielbild
Die Profitability Engine ist eine Schicht *Ã¼ber* dem Core. Sie ist eine Fabrik fÃ¼r renditeorientierte Entscheidungen.
- **Input:** Rohdaten, Strategy Models.
- **Prozess:** Candidate Lifecycle -> ARVP Evidence -> League Table.
- **Output:** Validierte Evidence Packets, die eine statistische Erwartung von Rendite belegen.

---

## 5. Business-Ziel: Strategy Candidate Pipeline
Das primÃ¤re Ziel ist nicht "der eine Algorithmus", sondern eine **Pipeline**.
- Wir suchen Strategien, die unter verschiedenen Marktbedingungen (Regimes) stabil performen.
- Ein Candidate muss erst beweisen, dass er die "Execution Economics" (GebÃ¼hren, Spread, Slippage) schlÃ¤gt, bevor er im Ranking aufsteigt.

---

## 6. Rendite-Stufenmodell
Wir klassifizieren Strategien nach ihrem Renditeziel und dem erforderlichen Evidence-Grad:
- **Tier 10:** 10% p.a. (Low Risk, High Stability).
- **Tier 20:** 20% p.a. (Standard Alpha).
- **Tier 30:** 30% p.a. (Aggressive Alpha, hÃ¶here Drawdown-Toleranz).
- **Tier 50+:** 50%+ p.a. (High Frequency / High Risk; nur fÃ¼r spezialisierte Sleeves).

---

## 7. Learning Loop vs. Trading Loop
- **Learning Loop (Offline):** Research -> Backtest -> ARVP -> Evidence. Hier findet die Optimierung statt.
- **Trading Loop (Runtime):** Signal -> Risk -> Execution. Hier findet nur die strikte AusfÃ¼hrung statt.
- **Regel:** Die Trading Loop lernt nicht autonom. Ã„nderungen an der Logik mÃ¼ssen den Learning Loop vollstÃ¤ndig durchlaufen.

---

## 8. Core Protection / No-Touch-Core
Der Trading-Core ist die "Black Box" der AusfÃ¼hrung.
- Ã„nderungen fÃ¼r die Profitability Engine dÃ¼rfen die StabilitÃ¤t des Core-Execution-Pfades nicht gefÃ¤hrden.
- Neue Logik wird bevorzugt als unabhÃ¤ngige Services oder Side-Cars implementiert.

---

## 9. Authority Rules
1. **Signal != Trade:** Ein Signal ist nur ein Vorschlag; Risk entscheidet (INV-002).
2. **AI != Authority:** KI-VorschlÃ¤ge sind Research; nur Code/Config im Canon ist Wahrheit.
3. **Dashboard != Freigabe:** Visualisierungen sind Information; Governance-Dateien sind AutoritÃ¤t.
4. **Docs != Approval:** Dieses Dokument ist Plan; das Human Gate (`DELIVERY_APPROVED.yaml`) bleibt das Schloss.

---

## 10. Candidate Lifecycle
1. **Inception:** Rohe Idee / Research.
2. **Backtest:** Erste statistische PrÃ¼fung.
3. **ARVP Candidate:** Integration in die ARVP; technischer Contract-Check.
4. **Validated Candidate:** Evidence Packet liegt vor (ARVP-LÃ¤ufe Ã¼ber mehrere Regimes).
5. **Paper Active:** Betrieb im Paper-Trading zur Echtzeit-Validierung.
6. **Sleeve-Ready:** Bereit fÃ¼r (zukÃ¼nftige) Kapitalallokation.

---

## 11. Promotion Gate Matrix
| Von | Nach | Bedingung |
|---|---|---|
| Backtest | ARVP | Dataset Quality Gate PASS (#3035) |
| ARVP | Validated | Evidence Packet vollstÃ¤ndig (min. 3 Regimes) |
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
DatenqualitÃ¤t ist kein technisches Detail, sondern ein **Business-Risiko**.
- LÃ¼ckenhafte oder falsche Daten fÃ¼hren zu "Halluzinationen" der ProfitabilitÃ¤t.
- Das Dataset Quality Gate (#3035) blockt jede Promotion eines Candidates, dessen Datenbasis nicht verifiziert ist.

---

## 14. Open-Source Tooling Posture

Wir folgen dem Prinzip: **Build the Core, Borrow the Tools**.

- **P0-Kandidaten fÃ¼r Candidate/Evidence Contracts:** `Pydantic`, `jsonschema`
- **P0-Kandidat fÃ¼r Dataset Quality Gates:** `Pandera`
- **P0-Kandidaten fÃ¼r Markdown/CLI-Reporting:** `Rich`, `Jinja2`
- **SpÃ¤tere Referenz fÃ¼r Fee-/Exchange-Metadaten:** `ccxt`
- **Nur Reference/Borrow-Pattern oder Reject, keine Core-Dependency:** `Freqtrade`, `Hummingbot`, `LEAN`, `Backtrader`, `Zipline`, `NautilusTrader`

| Posture | Einordnung |
|---|---|
| **Build (Core)** | Event-Bus, Risk-Engine, Replay-Loop, Audit-Ledger |
| **P0 Use** | Pydantic/jsonschema, Pandera, Rich/Jinja2 |
| **Later Reference** | ccxt |
| **Reject / Borrow only** | Freqtrade, Hummingbot, LEAN, Backtrader, Zipline, NautilusTrader |

---

## 15. Roadmap Phase 0-8

- **Phase 0:** `#3031` Datenblocker sichtbar halten.
- **Phase 1:** `#3033` Profitability Canon.
- **Phase 2:** `#3034` Candidate Contract + Evidence Packet.
- **Phase 3:** `#3035` Dataset Quality Gate.
- **Phase 4:** ARVP Batch Runner + Scenario Packs.
- **Phase 5:** Execution Economics.
- **Phase 6:** Strategy League Table.
- **Phase 7:** Paper Portfolio + Capital Sleeves Spec.
- **Phase 8:** Control Room + Micro-Live-Readiness-Pfad, ohne Live-Go.

## 16. Mapping to Existing Issues
- **Parent:** #3032 (Profitability Engine Parent)
- **Active Blockers:** #3031 (Data Blocker), #1900 (ARVP North-Star)
- **Parked / Scaling:** #205 (Multi-Strategy), #211 (Multi-Asset) â€“ Bleiben geparkt bis Phase 6/7.
- **Live Roadmap:** #2985 (Separate Live-Readiness-Schiene).

---

## 17. Stop Criteria
Die Engine stoppt oder wird zurÃ¼ckgestuft, wenn:
- Die DatenqualitÃ¤t unter die Grenzwerte fÃ¤llt.
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
