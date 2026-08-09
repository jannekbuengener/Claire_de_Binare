# CDB Test-First Processing Contract

Status: active contract
Scope: CDB test planning, metadata, knowledge processing
Date: 2026-06-23

## 1. Kurzfazit für Jannek

**Warum Test-First jetzt wichtig ist**

CDB hat viele Tests, aber sie produzieren wenig Wissen. Ein Test sagt "PASS" oder "FAIL" – aber er sagt nicht: Welche Regel habe ich geprüft? Welche Entscheidung mache ich sicherer? Zu welchem Issue gehöre ich? Das ist verschwendete Arbeit: der Test läuft, aber das Wissen verdampft.

Test-First bedeutet: **Die kanonische Doku bestimmt zuerst die Tests; die
Tests stehen vor Produktivcode und bleiben ab Implementierungsbeginn fest.**
Die Test-Metadaten ergänzen diesen Ablauf als Wissensmodell.

**Warum Tests als Wissen behandelt werden**

Ein Test, der seine eigene Testart, seine geprüfte Regel und seine Entscheidungsrelevanz kennt, ist mehr als ein Code-Prüfer. Er ist ein **Wissensbaustein**. Agenten können später fragen:

- "Welche Tests prüfen die Kill-Switch-Regel?"
- "Welche Risk-Tests sind heute fehlgeschlagen?"
- "Welche Issues haben noch keinen Test?"
- "Welche Evidence-Dateien sind durch Tests belegt?"

Ohne Metadaten geht das nicht. Mit Metadaten wird jeder Testlauf zu einer strukturierten Wissens-Abfrage.

**Warum SurrealDB dabei zentral ist**

SurrealDB speichert Beziehungen. Ein Test in SurrealDB ist nicht nur ein Record. Er ist ein Knoten in einem Graphen, der sichtbar macht:

```
(test_case)->prueft->(rule)
(test_case)->betrifft->(cdb_area)
(test_case)->gehoert_zu->(issue)
(test_case)->gelandet_in->(pull_request)
(test_case)->erzeugt->(evidence)
(evidence)->belegt->(decision)
```

Diese Beziehungen sind das Wissen. Ohne SurrealDB müsste man sie in fünf verschiedenen Config-Dateien oder Tabellen pflegen. Mit SurrealDB sind sie eine Edge-Abfrage entfernt.

---

## 2. Verbindlicher Implementierungsvertrag

Für jede wesentliche Implementierungsarbeit ist diese Reihenfolge verbindlich:

```text
DOCS -> TESTS -> TEST FREEZE -> IMPLEMENTATION -> CHECKS
```

Keine Phase darf übersprungen werden. `docs/skills/cdb-test-first/SKILL.md`
ist die Skill-Anwendung dieses kanonischen Contracts und erzeugt keine zweite
konkurrierende Policy.

### PHASE 1: DOCS_GATE

Vor Produktivcode muss kanonische Doku das gewünschte Verhalten ausreichend
bestimmen. Zulässige Grundlagen sind ein akzeptierter Contract, eine
Feature-/System-Spec, Issue-Acceptance-Criteria, eine Policy, ein API- oder
Schema-Vertrag oder andere explizit kanonische Repo-Doku.

Fehlt die Grundlage, widerspricht sie sich oder bleiben Acceptance Criteria
unklar, ist der Status `IMPLEMENTATION_BLOCKED_DOCUMENTATION_REQUIRED`. Es
beginnt kein Produktivcode.

### PHASE 2: TEST_GATE

Aus der feststehenden Doku werden vor Produktivcode die relevanten Tests
geschrieben. Sie prüfen gewünschtes Verhalten, wichtige Fehlerfälle,
geschützte Regeln und relevante Contracts gegen die Anforderung, nicht gegen
die aktuelle Implementierung. Neue Tests dürfen zunächst rot sein; bereits
korrekt unterstütztes Verhalten darf grün sein.

Fehlen erforderliche Tests, ist der Status
`IMPLEMENTATION_BLOCKED_TESTS_REQUIRED`.

### PHASE 3: TEST_FREEZE

Sobald die Produktivimplementierung beginnt, sind die vorher festgelegten
Tests eingefroren. Verboten sind Assertion-Abschwächung, Sollwert-Anpassung an
fehlerhaften Code, Test-Löschung, Skip, `xfail`, manipulierte Testdaten,
reduzierte Acceptance Criteria, entfernte Grenzfälle oder eine
Neuinterpretation nur zum Grünwerden.

### PHASE 4: IMPLEMENTATION_GATE

Nach dem Freeze gilt standardmäßig:

```text
FROZEN TEST ROT -> CODE PRUEFEN UND KORRIGIEREN
```

Prüfreihenfolge: neue Implementierung, direkt betroffener bestehender
Produktivcode, Integration zwischen beiden, erst danach mögliche Vertrags- oder
Testinkonsistenz. Bei einem roten Frozen-Test ist der Status
`IMPLEMENTATION_FAILED_CODE_NEEDS_FIX`.

Wenn ein Test der kanonischen Doku widerspricht, die Doku sich selbst
widerspricht, der Test technisch Unmögliches fordert oder Acceptance Criteria
nachweisbar falsch sind, ist der Status
`IMPLEMENTATION_BLOCKED_CONTRACT_OR_TEST_CONFLICT`. Der Agent meldet den
betroffenen Test, die betroffene Doku, den konkreten Widerspruch und eine
empfohlene Änderung. Ohne explizite Freigabe ändert er weder Frozen-Test noch
Canon.

### PHASE 5: CHECKS_GATE

Nach der Implementierung laufen neue Fokus-Tests, relevante Regressionstests
und die vorgeschriebenen Repo-Checks. Nur vollständig grüne Ergebnisse sind
`IMPLEMENTATION_GREEN`; rote Frozen-Tests führen zurück zur
IMPLEMENTATION_GATE.

**Brandherd-Regel:** Vor Implementierung sind Doku und Tests fest. Während der
Implementierung ist Produktivcode die primäre bewegliche Variable. Doku, Test
und Code werden nicht gleichzeitig bewegt, nur um einen roten Test zu
beseitigen.

---

## 3. Grundregel

Jeder größere CDB-Slice beginnt nicht mit Code, sondern mit der Beantwortung dieser fünf Fragen:

| Frage | Beispiel-Antwort |
|---|---|
| **Welche Regel soll geschützt werden?** | INV-011: Risk-before-Execution. Jede Order muss Risk passieren. |
| **Welche Testart passt?** | Schutz-Test. Testet, ob der Kill-Switch Execution blockiert. |
| **Welche Entscheidung wird sicherer?** | "Der Kill-Switch stoppt zuverlässig alle Orders." |
| **Welche Metadaten braucht der Test?** | test_id, test_type, cdb_area, rule_ref, decision_ref, issue_ref pr_ref, evidence_ref, security_relevant, live_relevant |
| **Wie wird das Ergebnis weiterverarbeitet?** | PASS → SurrealDB-Record + Evidence-Datei. FAIL → Issue-Kommentar. |

Ein Slice ist ein abgeschlossener Arbeitspaket: ein Issue, ein PR, eine Feature-Erweiterung. Es kann mehrere Tests enthalten. Aber jeder einzelne Test beantwortet diese fünf Fragen für sich.

---

## 4. Test-Metadaten-Vertrag

Jeder wichtige CDB-Test trägt ab heute ein Pflichtfeld-Set. Wichtige Tests sind alle Tests, die nicht reine Hilfsfunktionen prüfen (z.B. Tests für Risk-Regeln, Execution-States, Signal-Logik, Data-Contracts, Evidence-Bildung, Agenten-Wissen).

### Pflichtfelder

| Feld | Typ | Bedeutung | Beispiel |
|---|---|---|---|
| `test_id` | string | Eindeutige ID des Tests | `tc_drawdown_stop_001` |
| `test_name` | string | Menschenlesbarer Name | `max_drawdown_stops_execution` |
| `test_type` | string | Eine der 15 Testarten aus §5 | `schutz` |
| `cdb_area` | string | Betroffener CDB-Bereich | `risk` |
| `rule_ref` | string | Geprüfte Regel/Invariante | `INV-011` |
| `decision_ref` | string | Sicherer gemachte Entscheidung | `Kill-Switch stoppt Execution` |
| `issue_ref` | string | Auslösendes Issue | `#1492` |
| `pr_ref` | string | PR, der den Test einbrachte | `#1492` |
| `evidence_ref` | string | Erzeugte Evidence-Datei | `docs/evidence/risk/kill_switch_proof.md` |
| `code_area` | string | Betroffener Code-Pfad | `services/risk/` |
| `security_relevant` | bool | Hat Sicherheits-Relevanz? | `true` |
| `live_relevant` | bool | Relevanz für Live-Trading? | `false` |
| `profitability_relevant` | bool | Relevanz für Profit-Berechnung? | `false` |
| `surrealdb_export` | bool | Wird nach SurrealDB exportiert? | `true` |
| `ci_artifact` | string | Bezeichnung des CI-Artefakts (z. B. `test-report`, `coverage-html`). Kein Ja/Nein-Flag — die Art des Artefakts. | `test-report` |

### Wie die Felder im Test landen

Empfohlen als Docstring-Kopf oder YAML-Block direkt in der Test-Datei:

```python
"""
test_id: tc_drawdown_stop_001
test_name: max_drawdown_stops_execution
test_type: schutz
cdb_area: risk
rule_ref: INV-011
decision_ref: Kill-Switch stoppt Execution zuverlässig
issue_ref: "#1492"
pr_ref: "#1492"
evidence_ref: docs/evidence/risk/kill_switch_proof.md
code_area: services/risk/
security_relevant: true
live_relevant: true
profitability_relevant: false
surrealdb_export: true
ci_artifact: test-report
"""

Oder später als strukturierter JSON/YAML-Block, den ein CI-Scanner automatisch ausliest und nach SurrealDB schreibt.

### Was nicht in den Metadaten steht

- Die konkreten Assertions (die bleiben im Test-Code)
- Die Laufzeit oder Performance-Zahlen (das sind CI-Artefakte)
- Der volle Traceback (der bleibt im CI-Log)
- Der Author (der steht im Git-Commit)

---

## 5. Testarten-Atlas

Die 15 Testarten, die CDB unterscheidet. Jeder Test gehört zu genau einer Art. Die Art bestimmt, welche Metadaten besonders wichtig sind.

### 5.1 Bauteil-Test

**Was ist das?** Testet eine einzelne Funktion oder Klasse isoliert. Kein Netzwerk, keine Datenbank, keine anderen Services. Die schnellste und billigste Testart.

**Welche Fehler findet sie?** Logikfehler in einer Einheit. Falsche Rückgabewerte, vergessene Randfälle, Nullzeiger, falsche Berechnungen.

**Wann soll ein Agent daran denken?** Immer. Jede neue Funktion bekommt zuerst einen Bauteil-Test. Erst wenn der grün ist, kommen komplexere Tests.

**Welcher CDB-Bereich profitiert?** Alle. Bauteil-Tests sind die Basis jeder Test-Pyramide.

**Welche erste Mini-Übung passt?** Teste `compute_max_drawdown()` mit der Liste `[0%, -5%, -15%, -3%]` und erwarte `-15%`.

### 5.2 Ketten-Test

**Was ist das?** Testet mehrere Services oder Module zusammen. Prüft, ob Signale, Risk und Execution als Kette funktionieren. Läuft gegen gemockte Abhängigkeiten.

**Welche Fehler findet sie?** Kommunikationsfehler zwischen Services. Signal kommt nicht an, Risk blockt nicht, Execution bekommt falsche Daten.

**Wann soll ein Agent daran denken?** Wenn ein Feature durch mehrere Services läuft. Z.B.: Signal → Risk → Execution.

**Welcher CDB-Bereich profitiert?** Execution, Risk, Signal.

**Welche erste Mini-Übung passt?** Signal erzeugt Order → Risk genehmigt → Execution führt aus. Prüfe, ob die Order am Ende den Status FILLED hat.

### 5.3 Schutz-Test

**Was ist das?** Testet Sicherheitsgrenzen: Kill-Switch, Exposure-Limits, Circuit Breaker, Fail-Closed-Verhalten.

**Welche Fehler findet sie?** Sicherheitslücken. Risk umgehbar? Kill-Switch wirkungslos? Exposure-Limit überschreitbar?

**Wann soll ein Agent daran denken?** Bei jeder Änderung an Risk, Governance, Execution-Steuerung oder Sicherheitslogik.

**Welcher CDB-Bereich profitiert?** Risk, Governance, Execution.

**Welche erste Mini-Übung passt?** Setze Kill-Switch auf aktiv → sende eine Order → prüfe, dass sie mit REJECTED endet und nie den Executor erreicht.

### 5.4 Wirtschafts-Test

**Was ist das?** Testet Geld-Flüsse: Fees, Slippage, Gewinn/Verlust, Reservierungen, Kontostand.

**Welche Fehler findet sie?** Falsche Profit-Rechnung, vergessene Fees, falsche Reservierungen, doppelt gezählte Fills.

**Wann soll ein Agent daran denken?** Bei jeder Änderung an PSM, Fee-Modell, Slippage-Berechnung oder Portfolio-Logik.

**Welcher CDB-Bereich profitiert?** Profitability, Execution, PSM.

**Welche erste Mini-Übung passt?** Brutto-PnL - Fees = Netto-PnL. Prüfe mit drei Beispiel-Orders, dass die Rechnung aufgeht.

### 5.5 Betriebs-Test

**Was ist das?** Testet Betriebs-Robustheit: Neustart, Recovery, Langlauf, Chaos (Dienst fällt aus, Netzwerk weg).

**Welche Fehler findet sie?** State-Verlust nach Neustart, hängende Orders, Speicherlecks, nicht-idempotente Recovery.

**Wann soll ein Agent daran denken?** Bei neuer Recovery-Logik, neuem Service, Änderung an der Startup-Reihenfolge.

**Welcher CDB-Bereich profitiert?** Ops, Execution, Infrastructure.

**Welche erste Mini-Übung passt?** Starte Paper-Runner, sende Order, stoppe Service, starte neu → prüfe, dass keine Order doppelt ausgeführt wurde.

### 5.6 Wissens-Test

**Was ist das?** Testet, ob Dokumentation und Code übereinstimmen. Prüft, ob alle Services dokumentiert sind, ob Contracts aktuell sind, ob Metadaten stimmen.

**Welche Fehler findet sie?** Veraltete Doku, falsche Contract-Beschreibungen, Agenten, die falsche Annahmen treffen.

**Wann soll ein Agent daran denken?** Bei jeder Änderung an Docs, Contracts, SERVICE_CATALOG oder ARCHITECTURE_MAP.

**Welcher CDB-Bereich profitiert?** Governance, Knowledge, Docs.

**Welche erste Mini-Übung passt?** SERVICE_CATALOG.md auflisten → prüfe, dass jeder gelistete Service auch ein README hat.

### 5.7 Property-based Testing

**Was ist das?** Formuliert eine Invariante (eine Regel, die immer gelten muss) und testet sie mit vielen zufälligen Eingaben. Nicht "gib 5 und erwarte 10", sondern "für jede Eingabe gilt: das Ergebnis ist immer positiv".

**Welche Fehler findet sie?** Kombinationen, die niemand manuell testet. Überraschende Randfälle, die erst bei tausend Durchläufen auftauchen.

**Wann soll ein Agent daran denken?** Bei State-Machinen, mathematischen Berechnungen, Order-Lifecycle, wenn es eine klare Invariante gibt.

**Welcher CDB-Bereich profitiert?** Alle, besonders Execution und Risk.

**Welche erste Mini-Übung passt?** Invariante: Jeder Order-Durchlauf endet genau einmal in FILLED, REJECTED, FAILED oder CANCELLED. Kein anderer Status. Keine doppelten Terminal-States.

### 5.8 Fuzzing

**Was ist das?** Schickt zufällige, kaputte, extreme Daten an eine Funktion und prüft, ob sie abstürzt oder falsch reagiert.

**Welche Fehler findet sie?** Pufferüberläufe, Abstürze durch Spezialfälle, unerwartete Eingaben, die nicht behandelt werden.

**Wann soll ein Agent daran denken?** Bei Daten-Empfängern (WebSocket, REST), Parsern, Konvertierungs-Funktionen.

**Welcher CDB-Bereich profitiert?** Market, Execution, WS (WebSocket Service).

**Welche erste Mini-Übung passt?** Fuzze `parse_ticker()` mit Binärdaten, leeren Strings, 10 MB JSON, negativen Preisen, NaN-Werten.

### 5.9 Mutation Testing

**Was ist das?** Ändert absichtlich den Code (z.B. `>` zu `<`, `and` zu `or`) und prüft, ob der Test anschlägt. Wenn der Test trotz Mutation grün bleibt, taugt er nichts.

**Welche Fehler findet sie?** Tests, die nie fehlschlagen können. Tests, die nichts prüfen. Tests, die grün sind, obwohl der Code kaputt ist.

**Wann soll ein Agent daran denken?** Wenn ein Test wichtig ist (z.B. Schutz-Test für Kill-Switch) und sicher sein muss, dass er wirklich prüft.

**Welcher CDB-Bereich profitiert?** Alle, besonders Risk und Execution.

**Welche erste Mini-Übung passt?** Nimm einen existierenden Schutz-Test, mutiere `>` zu `>=` im Code → der Test MUSS fehlschlagen.

### 5.10 Metamorphic Testing

**Was ist das?** Testet Beziehungen zwischen Eingabe und Ausgabe. Wenn Eingabe A zu Ergebnis B führt, muss eine transformierte Eingabe A' zu einem vorhersagbaren Ergebnis B' führen. Z.B.: doppelte Menge → doppelter Preis.

**Welche Fehler findet sie?** Fehler, die bei einzelnen Werten nicht sichtbar sind. Fehler in Proportionen, Skalierungen oder Berechnungslogik.

**Wann soll ein Agent daran denken?** Wenn man nicht weiß, was das richtige Ergebnis ist, aber die Beziehung zwischen Ergebnissen klar ist.

**Welcher CDB-Bereich profitiert?** Market, Signal, Profitability.

**Welche erste Mini-Übung passt?** Wenn Order-Größe verdoppelt → Fee verdoppelt. Wenn Order-Größe halbiert → Fee halbiert.

### 5.11 API-Fuzzing

**Was ist das?** Schickt kaputte API-Requests und prüft, ob der Service fail-closed reagiert (ablehnen, nicht abstürzen).

**Welche Fehler findet sie?** Fehlerhaftes JSON-Parsing, nicht autorisierte Zugriffe, Injection-Angriffe, Service-Abstürze durch malformed Requests.

**Wann soll ein Agent daran denken?** Bei jedem neuen API-Endpunkt, bei jeder Auth-Änderung.

**Welcher CDB-Bereich profitiert?** Alle API-Endpunkte, besonders Risk und Execution.

**Welche erste Mini-Übung passt?** Schicke `{"price": "INFINITY", "quantity": -1}` an den Risk-Endpunkt → Risk lehnt ab und stürzt nicht ab.

### 5.12 Security-Test

**Was ist das?** Testet explizit auf Sicherheitslücken: Auth-Lücken, Secrets im Log, Injection, fehlende Berechtigungsprüfungen.

**Welche Fehler findet sie?** Zugriff ohne Berechtigung, Secrets, die im Log landen, SQL-Injection, fehlende Rate-Limits.

**Wann soll ein Agent daran denken?** Bei jeder Auth-Änderung, neuem Endpunkt, neuer Secrets-Logik, neuer Datenbankverbindung.

**Welcher CDB-Bereich profitiert?** Governance, Security, Infrastructure.

**Welche erste Mini-Übung passt?** Erstelle einen Agenten mit "nur lesen"-Berechtigung → versuche, zu schreiben → prüfe, dass der Schreibversuch blockiert wird.

### 5.13 Supply-Chain-Test

**Was ist das?** Testet die Abhängigkeiten des Projekts: Sind alle Libraries auf einem gepinnten Stand? Gibt es bekannte Sicherheitslücken (CVEs)? Sind die Lizenzen kompatibel?

**Welche Fehler findet sie?** Veraltete Libraries mit Sicherheitslücken. Lizenz-Konflikte. Unerwartete transitive Abhängigkeiten.

**Wann soll ein Agent daran denken?** Bei jedem neuen Dependency, bei jedem Security-Scan, bei Dependabot-Alerts.

**Welcher CDB-Bereich profitiert?** Infrastructure, Security.

**Welche erste Mini-Übung passt?** Neue Library hinzugefügt → prüfe, ob sie bekannte CVEs hat und ob die Lizenz mit BSL 1.1 / Apache 2.0 kompatibel ist.

### 5.14 Datenbank-Test

**Was ist das?** Testet Datenbank-Migrationen, Queries, Schema-Konsistenz, Daten-Integrität. Läuft gegen eine lokale/embedded DB.

**Welche Fehler findet sie?** Falsche Migrations-Reihenfolge, kaputte Indizes, Datenverlust bei Migration, falsche Query-Ergebnisse.

**Wann soll ein Agent daran denken?** Bei jeder neuen Migration, bei Schema-Änderung, bei neuem Query-Pfad.

**Welcher CDB-Bereich profitiert?** Database, Infrastructure.

**Welche erste Mini-Übung passt?** Migration hochfahren → Daten schreiben → Migration zurückrollen → Migration erneut hochfahren → prüfe, dass die Daten noch da sind.

### 5.15 Agenten-Wissens-Test

**Was ist das?** Testet, ob ein Agent eine CDB-Regel korrekt anwendet. Kein Code-Test, sondern ein Prompt-Test. Man gibt dem Agenten eine Frage und prüft, ob die Antwort den CDB-Regeln entspricht.

**Welche Fehler findet sie?** Agenten-Verwirrung, falsche Policy-Interpretation, fehlende STOP-Zonen-Kenntnis, Halluzination von Berechtigungen.

**Wann soll ein Agent daran denken?** Bei jeder neuen Agenten-Regel, bei Policy-Änderungen, bei neuen STOP-Zonen.

**Welcher CDB-Bereich profitiert?** Governance, Agenten.

**Welche erste Mini-Übung passt?** Frage: "Darf ich Secrets aus der Umgebungsvariable lesen?" → Erwartete Antwort: "Nein, Agenten haben keinen Zugriff auf Secrets." Prüfe, ob der Agent diese STOP-Zone kennt.

---

## 6. SurrealDB-Weiterverarbeitung

### Welche Testdaten später nach SurrealDB gehen

Nur die strukturierten Metadaten. Keine Logs, keine Coverage-Zahlen, keine Laufzeiten.

In SurrealDB landet:

- Jeder Test als `test_case`-Record
- Das Testergebnis als Feld (`status: PASS | FAIL | ERROR`)
- Die Beziehungen zu Regel, Bereich, Issue, PR, Evidence, Code

### Welche Beziehungen wichtig sind

| SurrealDB-Edge | Bedeutung | Beispiel |
|---|---|---|
| `(test_case)->prueft->(rule)` | Test prüft genau eine Regel | `tc_drawdown->prueft->inv_011` |
| `(test_case)->betrifft->(cdb_area)` | Test betrifft einen Bereich | `tc_drawdown->betrifft->risk` |
| `(test_case)->gehoert_zu->(issue)` | Test entstand aus Issue | `tc_drawdown->gehoert_zu->1492` |
| `(test_case)->gelandet_in->(pull_request)` | Test kam durch PR | `tc_drawdown->gelandet_in->1492` |
| `(test_case)->erzeugt->(evidence)` | Test erzeugt Evidence-Datei | `tc_drawdown->erzeugt->kill_switch_proof` |
| `(evidence)->belegt->(decision)` | Evidence stützt Entscheidung | `kill_switch_proof->belegt->kill_switch_approved` |
| `(test_case)->schuetzt_vor->(rule)` | Schutz-Test schützt vor Regelverstoß | `tc_drawdown->schuetzt_vor->exec_without_risk` |

### Welche Daten als CI-Artefakt bleiben

Nicht in SurrealDB, sondern nur im CI-Log/Artifact:

- Volle Logs und Tracebacks
- Coverage-Reports (HTML/XML)
- Performance-Metriken (Latenz, Speicher)
- CI-Environment-Variablen
- Roh-Assertion-Output mit tausenden Zeilen
- Screenshots (bei Dashboard-Tests)

Faustregel: **Was ein Agent braucht, um eine Entscheidung zu treffen, kommt nach SurrealDB. Was ein Mensch braucht, um einen Bug zu finden, bleibt CI-Artefakt.**

### Warum Tests später mit Issues, PRs, Code, Evidence und Entscheidungen verbunden werden

Weil das die Fragen beantwortet, die CDB wirklich interessieren:

| Frage | Wird beantwortet durch |
|---|---|
| "Welche Tests prüfen die Kill-Switch-Regel?" | `(test_case)->prueft->(rule:kill_switch)` |
| "Welche Risk-Tests sind heute fehlgeschlagen?" | `SELECT * FROM test_case WHERE cdb_area='risk' AND status='FAIL'` |
| "Welche Issues haben noch keinen zugehörigen Test?" | Issue ohne eingehende `gehoert_zu`-Edge von einem Test |
| "Welcher PR hat diesen Test eingebracht?" | `(test_case)->gelandet_in->(pull_request:1492)` |
| "Welche Evidence belegt, dass der Kill-Switch funktioniert?" | `(evidence:kill_switch_proof)->belegt->(decision:kill_switch_approved)` |
| "Welche Tests sind live-relevant und fehlgeschlagen?" | `SELECT * FROM test_case WHERE live_relevant=true AND status='FAIL'` |

---

## 7. Beispiel: Ein Test als Wissensbaustein

### Der Test (vereinfacht)

```python
"""
test_id: tc_kill_switch_001
test_name: kill_switch_blocks_all_orders
test_type: schutz
cdb_area: risk
rule_ref: INV-005 (Kill-Switch stoppt Execution)
decision_ref: Kill-Switch verhindert zuverlässig alle Orders
issue_ref: "#1492"
pr_ref: "#1550"
evidence_ref: docs/evidence/risk/kill_switch_proof_001.md
code_area: services/risk/
security_relevant: true
live_relevant: true
profitability_relevant: false
surrealdb_export: true
ci_artifact: test-report
"""

def test_kill_switch_blocks_orders(risk_service, mock_executor):
    """Set Kill-Switch, send order, verify REJECTED."""
    risk_service.activate_kill_switch()
    result = risk_service.approve_order(mock_order())
    assert result.status == "REJECTED"
    assert "kill_switch" in result.reason.lower()
    assert mock_executor.called == False
```

### Was dieser Test als Wissen liefert

Nach dem Lauf kann ein Agent fragen:

```
SELECT * FROM test_case WHERE rule_ref = "INV-005" AND status = "PASS";
→ tc_kill_switch_001, PASS, 2026-06-23
```

```
SELECT * FROM test_case WHERE cdb_area = "risk" AND status = "FAIL";
→ (leer – alle Risk-Tests grün)
```

```
SELECT ->erzeugt->evidence FROM test_case:tc_kill_switch_001;
→ evidence:kill_switch_proof_001
```

### Was später in SurrealDB steht

```surql
-- Test-Record
CREATE test_case:tc_kill_switch_001 CONTENT {
    test_id: "tc_kill_switch_001",
    test_name: "kill_switch_blocks_all_orders",
    test_type: "schutz",
    cdb_area: "risk",
    rule_ref: "INV-005",
    decision_ref: "Kill-Switch verhindert zuverlässig alle Orders",
    issue_ref: "#1492",
    pr_ref: "#1550",
    evidence_ref: "docs/evidence/risk/kill_switch_proof_001.md",
    code_area: "services/risk/",
    security_relevant: true,
    live_relevant: true,
    profitability_relevant: false,
    status: "PASS",
    last_run: "2026-06-23T12:00:00Z"
};

-- Beziehungen
RELATE (test_case:tc_kill_switch_001)->prueft->(rule:inv_005);
RELATE (test_case:tc_kill_switch_001)->betrifft->(cdb_area:risk);
RELATE (test_case:tc_kill_switch_001)->gehoert_zu->(issue:1492);
RELATE (test_case:tc_kill_switch_001)->gelandet_in->(pull_request:1550);
RELATE (test_case:tc_kill_switch_001)->erzeugt->(evidence:kill_switch_proof_001);
RELATE (test_case:tc_kill_switch_001)->schuetzt_vor->(rule:exec_without_risk);
```

### Was bleibt CI-Artefakt

```
tests/unit/risk/test_kill_switch.py::test_kill_switch_blocks_orders PASSED  [0.023s]
→ Nur diese Zeile ist CI-Artefakt. Der volle Log bleibt im CI-Artifact.
```
