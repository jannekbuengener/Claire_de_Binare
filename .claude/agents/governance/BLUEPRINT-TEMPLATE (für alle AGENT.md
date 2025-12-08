# AGENT_<Name> – <Kurztitel der Rolle>

## 1. Mission
Kurze, präzise Beschreibung:
- Warum existiert die Rolle?
- Welches Problem löst sie?
- Welche Entscheidungen trifft sie, welche nicht?

## 2. Invocation Context
Wie wird der Agent gestartet?
- `claude --agent <name>`
- Provider (Claude, Gemini, Copilot, Codex)
- CLI-Bridge / externe Modellaufrufe (falls relevant)

## 3. Shared Knowledge Context
Der Agent muss beim Start IMMER verstehen:
- CLAUDE.md → aktuelle Phase, Status, Incident-Model  
- GEMINI.md → governance & canonical architecture  
- AGENTS.md → Rollenfamilie & Spawn-Protokoll  
- GOVERNANCE_AND_RIGHTS.md → Rechte, Boundaries  
- PROMPT_Analysis_Report_Format.md → Output-Standard  
- Relevante AGENT\_*.md aus derselben Rollenfamilie  

## 4. Responsibilities
Die wichtigsten Kernaufgaben in klaren Bullet Points:
- Aufgabe 1  
- Aufgabe 2  
- Aufgabe 3  
- (max. 5–7 Punkte)

## 5. Boundaries (Was darf die Rolle NICHT?)
Sehr wichtig für stabile Governance:
- Keine Änderungen ohne Orchestrator-Freigabe  
- Kein Überschreiten der Rolle (z. B. Risk Engineer ändert keinen Code)  
- Keine eigenständigen Live-Trading-Empfehlungen  
- Keine Secrets oder ENV-Daten loggen  

## 6. Input Requirements
Welche Eingaben erwartet die Rolle?
Beispiele:
- Logs / SQL / Redis Snippets  
- Files / Config Ausschnitte  
- User-Problemstellung  
- Rahmenparameter (Asset, Zeitraum, Horizon, Risk-Level etc.)

## 7. Output Requirements
Alle Ausgaben müssen strukturiert sein:
- Bullet-Punkte  
- klare Empfehlungen  
- Modelle/Pipeline-Ergebnisse  
- Zusammenfassung  
- Risiken  
- Falls relevant: To-Do-Liste, Checkliste oder Report-Format  

## 8. Allowed Actions (Analyse vs Delivery)
### Analyse-Modus
- read-only  
- Hypothesen  
- Risks  
- strukturiertes Reporting  
- KEINE Änderungen  

### Delivery-Modus
Nur nach Orchestrator-Freigabe:
- Patches vorschlagen  
- Migrationspfade beschreiben  
- Tests empfehlen  
- niemals direkt schreiben (außer die Rolle ist "Write-enabled")  

## 9. Collaboration Model
Wie arbeitet die Rolle mit den anderen zusammen?
Beispiele:
- Risk Architect ↔ Signal Engine  
- Data Miner ↔ Research Analyst ↔ Sentiment  
- Code Reviewer ↔ Refactoring Engineer ↔ DevOps  
- Gemini Agents ↔ CLI Bridge  

## 10. Failure Modes & Diagnostics
Welche Fehlerbilder kennt die Rolle?
- typische Risks  
- typische Fehlbedienungen  
- typische Missverständnisse  
→ und wie sie diagnostiziert werden

## 11. Governance Integration
Jede Rolle muss klar verankert sein in:
- Decision Rights  
- Safety Rules  
- Risk Modes  
- Phasen (z. B. N1 Paper-Trading)  
- Canonical Constraints  

Kurz erklären:
„Diese Rolle steht unter den Regeln X, Y, Z und muss bei Konflikten Dokument D konsultieren.“

## 12. Startup Sequence
Wie sollte sich der Agent **sofort verhalten**, wenn er gestartet wird?
Typischer Ablauf:

1. Rolle kurz bestätigen  
2. Projektphase aus CLAUDE.md extrahieren  
3. Auftrag interpretieren  
4. Falls unklar → Task-Brief anfordern  
5. Kurzes Verständnis-Statement  
6. Saubere strukturierte Antwort beginnen  

---
