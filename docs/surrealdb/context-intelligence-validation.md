# CDB Context Intelligence — Static Validation Checklist

**Status**: Draft (Wave 7)
**Authority**: Issue #2039 / Epic #1976
**Guardrail**: Kein Trading-State, keine Secrets, kein Live-Go, keine Runtime-Änderung.

---

## 1. Zweck

Dieses Dokument dient als statische Guardrail-Checkliste für alle Context Intelligence Artefakte im Working Repo.
Agenten MÜSSEN dieses Dokument vor Änderungen an Context-Intelligence-Dokumenten, Schema-Drafts oder Ontologien lesen.

---

## 2. Scope und Nicht-Ziele

### Scope
- Validierung von `docs/surrealdb/context-intelligence-system.md` (#2035)
- Validierung von `docs/surrealdb/context-intelligence-roadmap.md` (#2036)
- Gate-Checkliste für Schema-Draft (#2037 — noch nicht gelandet)
- Validierung von `docs/surrealdb/context-ontology-v0.yaml` (#2038)
- Validierung künftiger Context-Intelligence-Artefakte

### Nicht-Ziele
- Kein Schema-Implementations-Ersatz
- Kein automatisches "Go" für Implementierungswellen
- Kein Live-Readiness-Upgrade
- Keine Runtime-Änderung

---

## 3. Quellen / Provenance

| Quelle | Typ | Status |
|--------|-----|--------|
| Epic #1976 | Parent Epic | OPEN |
| Issue #2034 | Wave-7 Landing | OPEN |
| Issue #2035 | Architecture Doc | MERGED |
| Issue #2036 | Roadmap Doc | MERGED |
| Issue #2037 | Schema Draft | **OPEN** |
| Issue #2038 | Ontology Seed | MERGED |
| Issue #2039 | Validation Checklist (dieses Dokument) | IN PROGRESS |
| `docs/surrealdb/context-intelligence-system.md` | Architektur | Exists |
| `docs/surrealdb/context-intelligence-roadmap.md` | Roadmap | Exists |
| `docs/surrealdb/context-ontology-v0.yaml` | Ontologie | Exists |

---

## 4. Globale Context-Intelligence-Guardrails

Jedes Context-Intelligence-Artefakt MUSS folgende Guardrails erfüllen:

| # | Guardrail | Prüfkriterium (Ja/Nein) |
|---|-----------|------------------------|
| G1 | Kein Trading-State | Enthält das Artefakt Tabellen/Felder für Orders, Positions, Fills, Balances? → **NEIN** |
| G2 | Keine Secrets | Enthält das Artefakt API-Keys, Passwörter, Private Keys, Broker-Credentials? → **NEIN** |
| G3 | Kein Live-Go | Bezeichnet das Artefakt einen Stage/Schema/Status als Live-Readiness-Go? → **NEIN** |
| G4 | Kein Echtgeld-Go | Leitet das Artefakt eine Freigabe für Echtgeld-Trading ab? → **NEIN** |
| G5 | Keine Runtime-Änderung | Ändert das Artefakt bestehende Trading-Runtime, Execution-Broker, oder Risk-Engine? → **NEIN** |
| G6 | Keine Autonomie ohne Human Gate | Erteilt das Artefakt autonome Freigaben ohne explizites Human-GO? → **NEIN** |
| G7 | Kein Board-Stage-zu-LR-Go-Mapping | Mappt das Artefakt `trade-capable` als LR-Go? → **NEIN** |
| G8 | Kein produktives Apply | Enthält das Artefakt produktive SurrealDB-Apply-Befehle oder Auto-Migration? → **NEIN** |
| G9 | Git/Repo ist SSoT | Deklariert das Artefakt Git/Repo/Issues als alleinige Source of Truth? → **JA** |
| G10 | Hash-Backed Evidence | Fordert das Artefakt Source-Hashes für Context-Antworten? → **JA** |

---

## 5. Architektur-Doku-Checkliste (#2035)

Vor Änderungen an `docs/surrealdb/context-intelligence-system.md`:

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| A1 | Dokument hat "Zweck"-Abschnitt | | |
| A2 | Dokument hat "Nicht-Ziele"-Abschnitt mit explizitem "Kein Trading-Runtime-Ersatz" | | |
| A3 | Dokument hat "Verbotene Datenklassen" (Trading-State, Secrets, PII, Live Risk) | | |
| A4 | SurrealDB-Rolle ist als "read-only Mirror" definiert | | |
| A5 | CDB-MCP-Rolle erzwingt Read-only-Constraints | | |
| A6 | 13 Kernkomponenten sind definiert (Repo Brain, Documentation Brain, ..., Agent OS) | | |
| A7 | Trust-Prinzip "No Evidence, No Trust" ist explizit | | |
| A8 | Human-GO- & Stop-Condition-Prinzip ist definiert | | |
| A9 | Abgrenzung zur Runtime ist dokumentiert (Fail-safe bei CIS-Ausfall) | | |
| A10 | Validierungs-Checkliste im Dokument verweist auf Epic #1976 | | |
| A11 | Provenance/Quellen sind aufgeführt | | |
| A12 | Keine Trading-State-Tabellen spezifiziert | | |
| A13 | Keine Secrets-Ingestion spezifiziert | | |

**STOPP**, wenn einer der Prüfpunkte A1–A13 mit "NEIN" beantwortet wird.

---

## 6. Roadmap-Doku-Checkliste (#2036)

Vor Änderungen an `docs/surrealdb/context-intelligence-roadmap.md`:

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| R1 | Dokument hat "Zweck"-Abschnitt | | |
| R2 | Dokument hat "Scope und Nicht-Ziele" mit "kein automatisches Go" | | |
| R3 | Roadmap-Phasen 1–3 sind definiert (Design, Landing, Implementierung) | | |
| R4 | Wellen 1–14 sind aufgeführt (mindestens als Platzhalter) | | |
| R5 | Issue-Mapping-Tabelle referenziert #1976, #2034, #2035, #2036, #2037, #2038 | | |
| R6 | Abhängigkeitsmodell ist dokumentiert (sequenziell Welle 8–14) | | |
| R7 | Guardrails enthalten: "Kein Runtime-Umbau", "Keine produktive SurrealDB-Aktivierung", "Kein Live-/Echtgeld-Go" | | |
| R8 | "GitHub Live Authority" ist deklariert (Issues gewinnen gegen statisches Dokument) | | |
| R9 | Validierungs-Checkliste im Dokument ist vorhanden | | |
| R10 | Provenance/Quellen referenzieren Epic #1976 und Parent #2034 | | |
| R11 | Keine Implementierungs-Befehle enthalten | | |
| R12 | Keine Live-Readiness-Inferenz | | |

**STOPP**, wenn einer der Prüfpunkte R1–R12 mit "NEIN" beantwortet wird.

---

## 7. Schema-Draft-Gate für #2037

**WICHTIG: Issue #2037 ist noch NICHT gelandet. Dieses Gate gilt für den künftigen Schema-Draft.**

Vor Landung oder Änderung von `infrastructure/surrealdb/context_intelligence_v0.surql` (oder ähnlich):

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| S1 | Datei ist `.surql` und enthält nur Schema-Draft (keine Migration) | | |
| S2 | Tabellen haben COMMENT-Felder (Dokumentation der Zweckbestimmung) | | |
| S3 | Pflichtfelder sind als Draft markiert | | |
| S4 | IDs und Zeitfelder sind konsistent (z.B. `id: record`, `created_at: datetime`) | | |
| S5 | Keine Secrets-Tabellen oder -Felder | | |
| S6 | Keine Trading-State-Tabellen (Orders, Positions, Fills, Risk-State) | | |
| S7 | Keine Orders/Positions/Fills/Risk-State-Daten in Schema | | |
| S8 | Tabelle `repo_artifact` ist definiert | | |
| S9 | Tabelle `code_symbol` ist definiert | | |
| S10 | Tabelle `doc_page` / `doc_section` / `doc_chunk` ist definiert | | |
| S11 | Tabelle `concept` ist definiert | | |
| S12 | Tabelle `dependency_edge` ist definiert | | |
| S13 | Tabelle `evidence_ref` ist definiert | | |
| S14 | Tabelle `claim` ist definiert | | |
| S15 | Tabelle `decision_event` ist definiert | | |
| S16 | Tabelle `agent_memory` ist definiert | | |
| S17 | Tabelle `audit_observation` ist definiert | | |
| S18 | Tabelle `contradiction` ist definiert | | |
| S19 | Tabelle `stale_context` ist definiert | | |
| S20 | Tabelle `scope_drift_event` ist definiert | | |
| S21 | Tabelle `knowledge_quality_score` ist definiert | | |
| S22 | Kein produktives Apply im Dokument beschrieben | | |
| S23 | Schema-Draft referenziert #1981, #2000, #2005, #2007, #2009, #2025 | | |

**STOPP**, wenn #2037 noch nicht gelandet ist und ein Artefakt als "fertig" deklariert wird.
**STOPP**, wenn einer der Prüfpunkte S1–S23 mit "NEIN" beantwortet wird.

---

## 8. Ontology-Seed-Checkliste (#2038)

Vor Änderungen an `docs/surrealdb/context-ontology-v0.yaml`:

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| O1 | YAML hat `schema_version` und `status: "draft"` | | |
| O2 | YAML hat `authority` mit `epic: 1976` und `issue: 2038` | | |
| O3 | Guardrails enthalten: "Board-Stage darf nie als Live-Readiness-Go modelliert werden" | | |
| O4 | Guardrails enthalten: "Keine Echtgeld-/Live-Freigabe ableiten" | | |
| O5 | Guardrails enthalten: "Kein Runtime-Umbau", "Keine produktive SurrealDB-Aktivierung" | | |
| O6 | Guardrails enthalten: "Kein Trading-State", "Keine Secrets" | | |
| O7 | Konzept `Agent Memory` ist definiert mit `must_not_mean` (Kein Trading-State) | | |
| O8 | Konzept `Agent OS` ist definiert mit `must_not_mean` (Kein Trading-Executor) | | |
| O9 | Konzept `Context Briefing` ist definiert mit `must_not_mean` (Kein Live-Trading-Signal) | | |
| O10 | Konzept `Human GO` ist definiert mit `must_not_mean` (Kein automatisches GO durch Board-Stage) | | |
| O11 | Konzept `Live-Readiness` ist definiert mit `must_not_mean` (Kein Board-Stage trade-capable) | | |
| O12 | Konzept `Governance Gate` ist definiert | | |
| O13 | Konzept `Evidence Fabric` ist definiert | | |
| O14 | Konzept `Decision Contract` ist definiert | | |
| O15 | Alle Konzepte haben `required_evidence` | | |
| O16 | Alle Konzepte haben `related_gates` | | |
| O17 | Keine Trading-Signale in Ontologie | | |
| O18 | Keine Live-PnL-Evidenz-Klassen | | |

**STOPP**, wenn einer der Prüfpunkte O1–O18 mit "NEIN" beantwortet wird.

---

## 9. Evidence-/Trust-Checkliste

Für alle Context-Intelligence-Artefakte:

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| E1 | Claims MÜSSEN durch Evidence belegbar sein | | |
| E2 | "No Evidence, No Trust" ist etabliertes Prinzip | | |
| E3 | Evidence-Bundles MÜSSEN Source-Hashes enthalten | | |
| E4 | Decision Events MÜSSEN Audit-Trail haben | | |
| E5 | Weak/Stale/Missing Evidence MUSS sichtbar bleiben | | |
| E6 | Context-Antworten MÜSSEN source-/hash-/evidence-fähig sein | | |
| E7 | Git/Repo/Issues gewinnen gegen statische Dokumente | | |
| E8 | `CURRENT_STATUS.md` ist als Ledger (nicht Live-Wahrheit) deklariert | | |
| E9 | `LR-AUDIT-STATUS-*` ist als operativer Go/No-Go-Status deklariert | | |

**STOPP**, wenn E1–E9 nicht erfüllt sind und eine "Trust-Claim" aufgestellt wird.

---

## 10. Human-GO-/Stop-Condition-Checkliste

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| H1 | Jede substantielle Aktion erfordert explizites Human-GO | | |
| H2 | Stop-Conditions sind identifiziert (z.B. Governance-Verstoß) | | |
| H3 | Human-GO ist NICHT automatisch durch Board-Stage erteilt | | |
| H4 | Human-GO ist NICHT implizit durch Systemstatus erteilt | | |
| H5 | `trade-capable` ist NICHT als Live-Readiness-Go gelesen | | |
| H6 | LR-Verdikt ist ausschließlich in `docs/live-readiness/LR-AUDIT-STATUS-*.md` | | |
| H7 | Stage-Aussagen werden NIEMALS als LR-Go/No-Go gelesen | | |
| H8 | `DELIVERY_APPROVED.yaml` ist human-kontrolliert, Agenten ändern nicht | | |

**STOPP**, wenn ein Artefakt autonome Freigaben ohne Human-GO impliziert.

---

## 11. Anti-Kriterien

Artefakte DÜRFEN NICHT enthalten:

| # | Anti-Kriterium | Prüfung |
|---|----------------|----------|
| AK1 | **Kein Trading-State** | Orders, Positions, Fills, Balances, Risk-State? → **NICHT VORHANDEN** |
| AK2 | **Keine Secrets** | API-Keys, Passwörter, Private Keys, Broker-Credentials? → **NICHT VORHANDEN** |
| AK3 | **Kein Live-Go** | Live-Readiness-Go durch Dokument/Status/Schema? → **NICHT ABLEITBAR** |
| AK4 | **Kein Echtgeld-Go** | Echtgeld-Freigabe durch Dokument/Status? → **NICHT ABLEITBAR** |
| AK5 | **Keine Runtime-Änderung** | Trading-Runtime, Execution, Broker, Risk-Engine geändert? → **NEIN** |
| AK6 | **Keine Autonomie ohne Human Gate** | Autonome Freigabe ohne Human-GO? → **NICHT VORHANDEN** |
| AK7 | **Kein Board-Stage-zu-LR-Go-Mapping** | `trade-capable` als LR-Go gelesen? → **NICHT ZULÄSSIG** |
| AK8 | **Kein produktives Apply aus Docs/YAML** | SurrealQL-Apply, Migration, Auto-Deploy? → **NICHT VORHANDEN** |

---

## 12. Agenten-Review-Prozess

Jeder Agent MUSS vor Änderungen an Context-Intelligence-Artefakten folgenden Prozess durchlaufen:

```
1. [ ] Dieses Dokument lesen (context-intelligence-validation.md)
2. [ ] Betroffenes Artefakt identifizieren (System, Roadmap, Schema, Ontologie)
3. [ ] Passende Checkliste aus Abschnitt 5, 6, 7, 8 wählen
4. [ ] Diff-Scope prüfen: Welche Zeilen ändern sich?
5. [ ] Guardrail-Check gegen Abschnitt 4 (G1-G10)
6. [ ] Anti-Kriterien-Check gegen Abschnitt 11 (AK1-AK8)
7. [ ] Evidence/Trust-Check gegen Abschnitt 9 (E1-E9)
8. [ ] Human-GO/Stop-Check gegen Abschnitt 10 (H1-H8)
9. [ ] Wenn ALLE Checks bestanden: Änderung vornehmen
10. [ ] Wenn EIN Check fehlschlägt: STOPP, Issue-Kommentar schreiben
11. [ ] Nach Änderung: Merge-Gate-Check (Abschnitt 13)
12. [ ] VOR MERGE STOPPEN: Human Review erforderlich
```

---

## 13. Merge-Gate-Checkliste

Vor jedem Merge von Context-Intelligence-Artefakten:

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| M1 | Alle Guardrails (G1-G10) sind erfüllt | | |
| M2 | Alle Anti-Kriterien (AK1-AK8) sind erfüllt | | |
| M3 | Docs-only Scope ist bestätigt (kein Code, kein Schema-Apply) | | |
| M4 | Kein Runtime-Umbau | | |
| M5 | Keine produktive SurrealDB-Aktivierung | | |
| M6 | Kein Live-/Echtgeld-Go | | |
| M7 | Kein Board-Stage-zu-LR-Go-Mapping | | |
| M8 | Abgleich gegen #1984, #1993, #2003, #2013, #2023, #2033 durchgeführt | | |
| M9 | Markdown-Review durchgeführt | | |
| M10 | Fachreview gegen Wave-Validierungs-Issues durchgeführt | | |
| M11 | PR-Body enthält "Refs #2039" und dokumentiert alle Änderungen | | |
| M12 | Branch ist sauber (nur beabsichtigte Dateien geändert) | | |
| M13 | **HUMAN REVIEW ERFORDERLICH — VOR MERGE STOPPEN** | | |

**STOPP**, wenn M1–M12 nicht alle mit "JA" beantwortet sind.
**STOPP**, wenn M13 nicht explizit durch Human bestätigt ist.

---

## 14. Restunsicherheiten und spätere Automatisierung

### Restunsicherheiten
- **#2037 Schema-Draft**: Noch nicht gelandet. Schema-Prüfpunkte in Abschnitt 7 sind als Gate formuliert. Sobald #2037 gelandet ist, muss Abschnitt 7 gegen das tatsächliche Schema validiert werden.
- **SurrealQL-Syntax**: Statische Syntax-Prüfung ist begrenzt ohne laufende DB. Spätere Validierung durch SurrealDB-Import-Tests.
- **Evidence-Integration**: Die Verknüpfung von Claims mit realen Beweisen (Hashes, Logs) ist konzeptionell definiert, aber noch nicht implementiert.

### Spätere Automatisierung (Optional, nicht Teil dieses Slices)
- **Python-Validator**: Ein optionales `tools/surrealdb/validate_context_intelligence.py` kann später geschrieben werden, um diese Checkliste programmatisch zu prüfen.
- **CI-Integration**: Automatische Prüfung der Guardrails über GitHub Actions.
- **MCP-Tools**: Spätere Read-only Context Tools können diese Checkliste als Validierungsgrundlage nutzen.

---

## 15. Validierungs-Checkliste für dieses Dokument selbst

| # | Prüfpunkt | Ja/Nein | Beleg |
|---|-----------|---------|-------|
| V1 | Dokument hat "Zweck"-Abschnitt (Abschnitt 1) | | |
| V2 | Dokument hat "Scope und Nicht-Ziele" (Abschnitt 2) | | |
| V3 | Dokument hat "Quellen / Provenance" (Abschnitt 3) | | |
| V4 | Globale Guardrails (Abschnitt 4) enthalten G1-G10 | | |
| V5 | Architektur-Checkliste (Abschnitt 5) enthält A1-A13 | | |
| V6 | Roadmap-Checkliste (Abschnitt 6) enthält R1-R12 | | |
| V7 | Schema-Draft-Gate (Abschnitt 7) ist als Gate für #2037 formuliert (nicht als erledigt) | | |
| V8 | Ontology-Checkliste (Abschnitt 8) enthält O1-O18 | | |
| V9 | Evidence-Checkliste (Abschnitt 9) enthält E1-E9 | | |
| V10 | Human-GO-Checkliste (Abschnitt 10) enthält H1-H8 | | |
| V11 | Anti-Kriterien (Abschnitt 11) enthalten AK1-AK8 | | |
| V12 | Agenten-Review-Prozess (Abschnitt 12) ist definiert | | |
| V13 | Merge-Gate-Checkliste (Abschnitt 13) enthält M1-M13 | | |
| V14 | Restunsicherheiten (Abschnitt 14) erwähnen #2037 als offen | | |
| V15 | Dieses Dokument enthält keine Trading-State-Tabellen | | |
| V16 | Dieses Dokument enthält keine Secrets | | |
| V17 | Dieses Dokument impliziert kein Live-Go | | |
| V18 | Dieses Dokument ändert keine Runtime | | |
| V19 | Checklisten sind prüfbar (Ja/Nein-Kriterien) | | |
| V20 | Keine weichen Aussagen ("sollte", "empfohlen") in Prüfpunkten | | |

**Dieses Dokument ist valide**, wenn V1–V20 alle mit "JA" beantwortet sind.

---

## Provenance / Quellen

- **Epic**: #1976
- **Parent**: #2034
- **Dependencies**: #2035 (MERGED), #2036 (MERGED), #2037 (OPEN), #2038 (MERGED)
- **Validation Gates**: #1984, #1993, #2003, #2013, #2023, #2033
- **Referenz-Dokumente**:
  - `docs/surrealdb/context-intelligence-system.md`
  - `docs/surrealdb/context-intelligence-roadmap.md`
  - `docs/surrealdb/context-ontology-v0.yaml`
- **Governance**:
  - `docs/runbooks/CONTROL_REGISTER.md`
  - `knowledge/governance/CDB_CONSTITUTION.md`
  - `knowledge/governance/CDB_AGENT_POLICY.md`
