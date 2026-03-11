# ISSUE_AND_BRANCH_LIFECYCLE.md

## Claire de Binare – Issue & Branch Lifecycle Policy  
**Status:** Canonical  
**Zweck:** Verhindert Issue- und Branch-Explosion, erzwingt saubere Delivery-Flows  
**Gültig für:** Alle Agenten, Tools, Humans

---

## 1. Grundprinzip (bindend)

**Issues sind langfristige Verträge.**  
**Branches sind langfristige Arbeitsräume.**

Dieses Projekt nutzt **keine kurzlebigen Issues** und **keine Wegwerf-Branches**.

---

## 2. Issue-Regeln (hart)

1. **KEINE neuen Issues**, wenn bereits ein Issue für das Thema existiert.  
2. Jedes Issue bleibt **offen**, bis die **ursprüngliche Definition of Done (DoD)** vollständig erfüllt ist.  
3. Fortschritt, Teilergebnisse, Fehlschläge und Verifikationen werden **als Kommentare im bestehenden Issue** dokumentiert.  
4. **Keine Sub-Issues**, keine Aufspaltung.  
5. Bei fehlgeschlagener Verifikation:
   - FAIL + Evidence **als Kommentar**
   - **kein neues Issue**
6. Ein Issue wird **ausschließlich dann geschlossen**, wenn:
   - DoD erfüllt ist **und**
   - der Code nach `main` gemergt wurde.

**Ein Issue ist ein Vertrag – kein Sprint-Artefakt.**

---

## 3. Branch-Regeln (hart)

1. **KEIN neuer Branch**, wenn bereits ein Branch für das Issue existiert.  
2. Jedes Issue hat **genau einen** zugehörigen Arbeits-Branch.  
3. Auf diesem Branch wird **die gesamte Issue-Lebenszeit** gearbeitet:
   - Initiale Implementierung
   - Fixes
   - Rework
   - E2E
   - Finalisierung
4. Branches sind **kontinuierlich**, nicht iterativ.

---

## 4. PR-Regeln

1. Alle PRs **referenzieren dasselbe Issue**, solange es offen ist.  
2. Mehrere PRs pro Issue sind erlaubt.  
3. PRs ohne Issue-Referenz sind **ungültig**.  
4. Kein Merge ohne:
   - Tests
   - Evidence
   - erfüllte DoD

---

## 5. Abschluss-Workflow (verbindlich)

Wenn die Arbeit an einem Issue abgeschlossen ist:

1. **Merge** des Branches nach `main`  
2. **Schließen** des GitHub-Issues  
3. **Löschen** des Feature-Branches  

**Verboten:**  
- Issue schließen ohne Merge  
- Branch offen lassen nach Issue-Closure  
- Branch löschen, solange Issue offen ist  

---

## 6. Erzwungene Reihenfolge

```
Issue offen
   ↓
Arbeit auf bestehendem Branch
   ↓
PR(s) mit Evidence
   ↓
DoD erfüllt
   ↓
Merge nach main
   ↓
Issue schließen
   ↓
Branch löschen
```

---

## 7. Agenten-Pflicht (MANDATORY FIRST STEP)

Bevor ein Agent arbeitet, MUSS er:

1. Alle **aktiven Issues** auflisten  
2. Die **existierenden Branches** zuordnen  
3. Explizit bestätigen:
   - welches Issue
   - welcher Branch

Ohne diese Bestätigung → **STOP**.

---

## 8. Verstöße

Ein Verstoß gegen diese Policy gilt als:
- Governance-Verletzung  
- Prozessfehler  
- Grund für Review / Revert  

---

## Abschluss

**Ein Issue = ein Thema.**  
**Ein Branch = ein Arbeitsraum.**  
**Main = der einzige Abschlusszustand.**


---

## 9. Trust Score Integration (Audit)

Jede Lifecycle-Aktion ist ein **Decision Event** und muss im Trust-Ledger erfasst werden:
`knowledge/agent_trust/ledger/`

Pflicht-Events u. a.:
- `issue.close`, `issue.reopen`
- `branch.create`, `branch.delete`
- PR Merge-Entscheidung (inkl. Evidence)

**Compliance-Regel (Policy Card PC-ISSUE-001):**
Issue schließen ohne Merge-Evidence gilt als **Verstoß** und reduziert den Compliance-Score.

Bei Unsicherheit:
- Issue bleibt offen
- Agent kommentiert Evidence + Optionen
- `uncertainty: true` im Decision Event
