# Skill Valley – Test-Upgrade-Plan

Status: active upgrade plan
Scope: Skill-Valley-Regeln für den Test-First Processing Contract
Date: 2026-06-23

## 1. Kurzfazit

Skill Valley wird vor der Testskalierung aktualisiert. Der Grund: Ein Agent, der den Test-First Processing Contract nicht kennt, schreibt Tests, die grün werden, aber kein Wissen produzieren. Das ist der Fehler, den wir vermeiden.

Die Reihenfolge ist:
1. **Skill Valley aktualisieren** (dieser Plan)
2. Agenten lernen die neuen Regeln
3. Dann erst Tests skalieren

Der Plan definiert 8 neue/erweiterte Skill-Regeln. Jede Regel sagt: Was muss ein Agent wissen, bevor er einen Test schreibt, der den Processing Contract erfüllt?

---

## 2. Neue oder erweiterte Skill-Regeln

### R1: Test-First Denken (neu)

**Erklärung:** Bevor du einen Test schreibst, beantworte die 5 Fragen aus dem Processing Contract: Regel, Testart, Entscheidung, Metadaten, Weiterverarbeitung.

**Wann Agenten sie anwenden:** Bei jedem neuen Test, jedem Issue mit Test-Bedarf, jedem Feature, das Tests braucht.

**Beispiel:** "Issue #1500 braucht einen Schutz-Test für `max_drawdown`. Die Regel ist INV-011. Die Entscheidung ist: Der Kill-Switch stoppt Execution zuverlässig."

**Betroffener CDB-Bereich:** Alle.

**Passende Testarten:** Alle.

**SurrealDB-Bezug:** Die 5 Fragen erzeugen genau die Felder, die später im SurrealDB-Record landen.

**Erste Trainingsübung:** Wähle ein geschlossenes Issue (z.B. #1492). Beantworte die 5 Fragen für den Test, den dieses Issue gebraucht hätte. Schreibe die Antworten als YAML-Block auf.

---

### R2: Testart-Auswahl (erweitert)

**Erklärung:** Es gibt 15 Testarten. Jeder Test gehört zu genau einer. Die Testart bestimmt, was der Test prüft und wie tief er gehen muss.

**Wann Agenten sie anwenden:** Nachdem die zu prüfende Regel bekannt ist. Aus der Regel folgt die Testart: Risk-Regel → Schutz-Test. Profit-Regel → Wirtschafts-Test. Code-Logik → Bauteil-Test.

**Beispiel:** "Ich prüfe INV-011 (Risk-before-Execution). Das ist eine Sicherheitsgrenze → Schutz-Test."

**Betroffener CDB-Bereich:** Alle.

**Passende Testarten:** Alle 15 – aber Agenten müssen die 6 häufigsten sicher erkennen: Bauteil, Kette, Schutz, Wirtschaft, Betrieb, Wissen.

**SurrealDB-Bezug:** Die Testart ist ein Pflichtfeld im SurrealDB-Record (`test_type`).

**Erste Trainingsübung:** Gegeben sind 10 Regeln aus CDB. Ordne jeder Regel die richtige Testart zu.

---

### R3: Test-Metadaten schreiben (neu)

**Erklärung:** Jeder wichtige Test trägt 15 Metadaten-Felder im Docstring. Die Felder sind im Processing Contract (§3) definiert. Agenten müssen sie vollständig und korrekt ausfüllen.

**Wann Agenten sie anwenden:** Beim Schreiben jedes Tests, der nicht reine Hilfsfunktionen prüft.

**Beispiel:** Siehe Beispiel in `TEST_FIRST_PROCESSING_CONTRACT.md` §6. Der YAML-Block am Anfang jeder Test-Datei.

**Betroffener CDB-Bereich:** Alle.

**Passende Testarten:** Alle, die `surrealdb_export: true` haben (also alle außer reinen CI-Hilfstests).

**SurrealDB-Bezug:** Direkt. Die Metadaten werden 1:1 zu SurrealDB-Feldern.

**Erste Trainingsübung:** Nimm einen existierenden CDB-Test (z.B. aus `tests/unit/risk/`). Schreibe die 15 Metadaten-Felder, die er tragen müsste.

---

### R4: SurrealDB-Testwissen vorbereiten (neu)

**Erklärung:** Agenten müssen wissen, welche Testdaten später nach SurrealDB gehen und welche Beziehungen dort modelliert werden.

- Records: `test_case`, `test_type`, `rule`, `cdb_area`, `code_module`, `issue`, `pull_request`, `evidence`, `decision`, `skill_rule`
- Edges: `prueft`, `betrifft`, `gehoert_zu`, `gelandet_in`, `erzeugt`, `belegt`, `schuetzt_vor`

**Wann Agenten sie anwenden:** Wenn ein Test geschrieben wird und die Frage aufkommt: "Wo landet das später?"

**Beispiel:** Der Test `tc_kill_switch_001` erzeugt später in SurrealDB:
```surql
RELATE (test_case:tc_kill_switch_001)->prueft->(rule:inv_005);
RELATE (test_case:tc_kill_switch_001)->erzeugt->(evidence:kill_switch_proof_001);
```

**Betroffener CDB-Bereich:** Database, Knowledge, alle Testbereiche.

**Passende Testarten:** Alle mit `surrealdb_export: true`.

**SurrealDB-Bezug:** Zentrale Regel. Agenten müssen die 10 Records und 7 Edges auswendig können.

**Erste Trainingsübung:** Zeichne den Graphen für einen Test: `test_case` → `prueft` → `rule`, `test_case` → `betrifft` → `cdb_area`, `test_case` → `erzeugt` → `evidence`. Schreibe die drei SurrealQL-RELATE-Befehle dazu.

---

### R5: MockExchange-Muster erkennen (erweitert)

**Erklärung:** MockExchange hat 5 starke Testmuster, die CDB übernehmen kann, ohne MockExchange selbst zu installieren. Agenten müssen erkennen, wann ein CDB-Problem eines dieser Muster abbildet.

**Wann Agenten sie anwenden:** Bei Execution-, Order- oder Fee-Tests, bei State-Machine-Tests, bei Accounting-Tests.

**Beispiel:** "MockExchange testet Insufficient-Funds nach Reservation. Das gleiche Muster braucht CDB für: Risk genehmigt, aber Geld reicht nicht → Execution muss rejecten."

**Betroffener CDB-Bereich:** Execution, Risk, Profitability.

**Passende Testarten:** Schutz-Test, Wirtschafts-Test, Property-based Test.

**SurrealDB-Bezug:** Der CDB-Test bekommt `mockexchange_inspired: true` als optionales Feld.

**Erste Trainingsübung:** Lies `MOCKEXCHANGE_CDB_TEST_MAP.md` §1-3. Wähle ein MockExchange-Muster und übersetze es in eine CDB-Test-Idee mit vollem Metadaten-Set.

---

### R6: Security-Testarten erkennen (neu)

**Erklärung:** Es gibt 5 Testarten mit Sicherheitsbezug: Schutz-Test, Security-Test, Supply-Chain-Test, API-Fuzzing, Fuzzing. Agenten müssen erkennen, wann eine Änderung eine dieser Testarten braucht.

**Wann Agenten sie anwenden:** Bei jeder Änderung an Auth-Logik, Secrets-Handling, Exposure-Limits, Kill-Switch, neuen Abhängigkeiten, neuen API-Endpunkten.

**Beispiel:** "Ich füge einen neuen API-Endpunkt hinzu → ich brauche API-Fuzzing + Security-Test."

**Betroffener CDB-Bereich:** Risk, Governance, Security, Infrastructure.

**Passende Testarten:** Schutz, Security, Supply-Chain, API-Fuzzing, Fuzzing.

**SurrealDB-Bezug:** Das Feld `security_relevant: true` markiert den Test für Security-Queries.

**Erste Trainingsübung:** Gegeben sind 5 Änderungen. Entscheide für jede: Braucht sie einen Security-Test? Welche Security-Testart passt? Setze `security_relevant` auf true/false.

---

### R7: Wirtschafts-Testarten erkennen (neu)

**Erklärung:** Wirtschafts-Tests prüfen Geld-Flüsse: Fees, Slippage, PnL, Reservierungen. Agenten müssen erkennen, wann eine Änderung einen Wirtschafts-Test braucht.

**Wann Agenten sie anwenden:** Bei jeder Änderung an Fee-Modell, Slippage-Berechnung, PSM, Portfolio-Logik, Profitability-Evidence.

**Beispiel:** "Ich ändere die Fee-Struktur von 0.1% auf 0.05% → ich brauche einen Wirtschafts-Test, der die neuen Fees gegenrechnet."

**Betroffener CDB-Bereich:** Profitability, Execution, PSM.

**Passende Testarten:** Wirtschafts-Test, Property-based Test, Metamorphic Test.

**SurrealDB-Bezug:** Das Feld `profitability_relevant: true` markiert den Test für Profitability-Queries.

**Erste Trainingsübung:** Gib einen Trade mit Entry 100€, Exit 110€, Fee 0.1%, Slippage 0.05%. Berechne Brutto-PnL und Netto-PnL. Schreibe die Assertion für den Wirtschafts-Test.

---

### R8: Agenten-Wissens-Tests schreiben (neu)

**Erklärung:** Ein Agenten-Wissens-Test prüft nicht Code, sondern das Wissen eines Agenten über CDB-Regeln. Man gibt dem Agenten eine Frage und prüft, ob die Antwort den CDB-Regeln entspricht.

**Wann Agenten sie anwenden:** Bei jeder neuen Policy, neuer STOP-Zone, neuem Governance-Dokument. Immer dann, wenn ein Agent eine Regel kennen muss.

**Beispiel:** Frage: "Darfst du Secrets lesen?" → Erwartete Antwort: "Nein, laut CDB_AGENT_POLICY.md und CDB_TRESOR_POLICY.md haben Agenten keinen Zugriff auf Secrets."

**Betroffener CDB-Bereich:** Governance, Agenten.

**Passende Testarten:** Agenten-Wissens-Test.

**SurrealDB-Bezug:** Der Wissens-Test wird als `test_type: agent_wissen` in SurrealDB gespeichert und über `(skill_rule)->lehrt_regel->(test_type)` mit der Skill-Regel verbunden.

**Erste Trainingsübung:** Wähle eine STOP-Zone aus `CDB_AGENT_POLICY.md`. Formuliere eine Frage, die ein Agent korrekt beantworten muss. Schreibe den erwarteten Antwort-String auf.

---

## 3. Reihenfolge

| Schritt | Skill-Regel | Warum zuerst? | MockExchange nötig? | SurrealDB nötig? |
|---|---|---|---|---|
| 1 | **R1: Test-First Denken** | Ohne diese Regel funktioniert der ganze Contract nicht | Nein | Nein |
| 2 | **R2: Testart-Auswahl** | Agent muss die 15 Arten kennen, bevor er Metadaten schreibt | Nein | Nein |
| 3 | **R3: Test-Metadaten schreiben** | Das Herzstück: jeder Test bekommt seinen Wissensteil | Nein | Nein |
| 4 | **R4: SurrealDB-Testwissen vorbereiten** | Agent muss wissen, wo die Metadaten später landen | Nein | Ja (nur Wissen, keine laufende DB) |
| 5 | **R6: Security-Testarten erkennen** | Sicherheitsrelevante Tests sind prioritär | Nein | Nein |
| 6 | **R7: Wirtschafts-Testarten erkennen** | Profitability ist ein CDB-Kernbereich | Nein | Nein |
| 7 | **R5: MockExchange-Muster erkennen** | Fortgeschritten: setzt R1-R4 voraus | Ja (nur lesend) | Nein |
| 8 | **R8: Agenten-Wissens-Tests schreiben** | Fortgeschritten: setzt Governance-Kenntnis voraus | Nein | Nein |

**Warum R5 und R8 erst später?**
- R5 (MockExchange-Muster) setzt voraus, dass Agenten die Basics (R1-R4) bereits sicher anwenden. MockExchange ist Muster-Quelle, nicht Lern-Starter.
- R8 (Agenten-Wissens-Tests) setzt voraus, dass Agenten die Governance-Dokumente (Policy, Tresor, STOP-Zonen) bereits kennen. Das ist Skill-Valley-Stufe 2.

---

## 4. Klare Empfehlung

**Diese Skill-Regel sollte zuerst in Skill Valley landen:**

### R1: Test-First Denken

Begründung:
- Ohne R1 sind alle anderen Regeln nutzlos. Ein Agent, der nicht zuerst die 5 Fragen stellt, schreibt Tests ohne Metadaten.
- R1 ist die einfachste Regel: nur 5 Fragen, kein SurrealDB-Wissen nötig, keine MockExchange-Kenntnis.
- R1 erzeugt sofort sichtbaren Mehrwert: Tests sagen, was sie prüfen.

Konkreter erster Schritt:
1. R1 in den Skill `cdb-session-start` einbauen: nach Control-Intake die Frage "Welche Testart braucht dieser Task?"
2. R1 in den Skill `cdb-shadow-validation` einbauen: nach dem Validierungspfad die Testart empfehlen
3. Beide Skills referenzieren den `TEST_FIRST_PROCESSING_CONTRACT.md` als Canon
