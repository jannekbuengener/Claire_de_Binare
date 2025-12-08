# Work Intake Process - Engineering Manager

**Version:** 1.0
**Gültig ab:** 2025-12-07
**Owner:** Engineering Manager
**Review-Zyklus:** Monatlich oder bei Prozess-Feedback

---

## 🎯 Zweck

Dieser Prozess definiert, wie Arbeitsanfragen (Tasks, Features, Incidents, Optimierungen) vom User zum Engineering Manager gelangen und wie sie zu den richtigen Crews (F-Crew, C-Crew, Mixed) geroutet werden.

**Ziel:** Klare, strukturierte Aufnahme aller Engineering-Arbeit mit sofortiger Priorisierung und Crew-Zuweisung.

---

## 📥 Schritt 1: Task Brief vom User

Der User beschreibt die Anfrage entweder:

- **Frei formuliert** (z.B. "Das System hat keine Signale mehr generiert")
- **Strukturiert** mit dem Task Brief Template (siehe unten)

### Task Brief Template (Optional, aber empfohlen)

```markdown
**Task Title:** [Kurze Zusammenfassung]

**Business Goal / Why Now:**
- Was soll erreicht werden?
- Warum ist es jetzt wichtig?

**Scope (In) / Out-of-Scope:**
- Was gehört zur Aufgabe?
- Was explizit nicht?

**Desired Workflow (if known):**
- Hat der User bereits eine Vorstellung, wie es umgesetzt werden soll?

**Constraints:**
- Performance, Security, Data, Compatibility

**Risk Sensitivity / Mode:**
- Paper-Trading (aktuell N1) / Testnet-Live (M7) / Production-Live (nicht aktiv)

**Success Criteria / KPIs:**
- Woran erkennen wir Erfolg?

**Testing Expectations:**
- Welche Tests müssen laufen?

**Dependencies / Impacted Areas:**
- Welche Services/Komponenten sind betroffen?

**Timeline / Priority:**
- ASAP / Diese Woche / Nächster Block / Backlog

**Attachments / Links:**
- Logs, Screenshots, Grafana-Links, etc.
```

**Quelle:** `.claude/agents/prompts/PROMPT_Task_Brief_Template.md`

---

## 🔍 Schritt 2: Engineering Manager Triage

Der Engineering Manager analysiert die Anfrage entlang dieser Dimensionen:

### 2.1 Klassifizierung

**Task-Typ:** (Wähle eine Kategorie)

- **Feature:** Neue Funktionalität oder Erweiterung bestehender Features
- **Incident:** System-Problem, Bug, Zero-Activity, Flow-Bruch
- **Optimization:** Performance-Tuning, Config-Anpassung, Refactoring
- **Governance:** Dokumentation, Decision-Log-Update, Prozess-Änderung

### 2.2 Crew-Routing

**Routing:** (Wähle eine Option)

| Routing | Beschreibung | Typische Use Cases |
|---------|--------------|-------------------|
| **F-Crew Only** | Nur Feature-Crew involviert | Neue Features ohne Risk-Impact, Code-Refactoring, Dokumentation, Test-Coverage-Improvements |
| **C-Crew Only** | Nur Customer/Stability-Crew involviert | Incident Response, System-Monitoring, Risk-Config-Tuning, Performance-Optimierung |
| **Mixed-Crew** | Beide Crews koordiniert involviert | Neue Features mit Trading-Logic, Architektur-Änderungen (Event-Flow, Service-Boundaries), Risk-Mode-Changes (Paper → Testnet-Live), Post-Incident-Fixes (Code + Risk-Validation) |

**Entscheidungshilfe:**

```
Betrifft es Trading-Logic, Risk-Modell oder Live-System?
  ├─ JA → Mixed-Crew (F-Crew implementiert, C-Crew validiert)
  └─ NEIN
      ├─ Ist es ein Incident oder System-Problem?
      │   └─ JA → C-Crew Only
      └─ Ist es ein neues Feature oder Code-Improvement?
          └─ JA → F-Crew Only
```

### 2.3 Priorisierung

**Priority:** (Wähle eine Stufe)

| Stufe | Beschreibung | Response Time | Beispiele |
|-------|--------------|---------------|-----------|
| **BLOCKER** | Verhindert aktuellen Block/Deployment | Sofort (0-2h) | Live-Trading aktiviert (Incident!), Test-Suite komplett rot, Event-Flow komplett unterbrochen |
| **HIGH** | Beeinträchtigt Funktionalität oder Block-Erfolg | Selber Tag (2-8h) | Zero-Activity >24h, Risk-Approval-Rate <1%, kritische Bug-Reports |
| **MEDIUM** | Wichtig, aber nicht blockierend | Nächste 1-3 Tage | Feature-Request mit klarem Business-Value, bekannte Bugs ohne Workaround, Monitoring-Lücken |
| **LOW** | Nice-to-Have, Backlog-Material | Nächster Block oder später | Kosmetische Issues, Doku-Verbesserungen, Performance-Optimierungen ohne akuten Bedarf |

### 2.4 Aufwandsschätzung

**Effort:** (Grobe Einschätzung)

- **Quick Win:** < 2 Stunden (z.B. Config-Änderung, kleine Doku-Anpassung)
- **Medium:** 0.5-2 Tage (z.B. Bug-Fix mit Tests, Feature-Enhancement)
- **Large:** >2 Tage (z.B. Architektur-Änderung, Multi-Service-Refactoring)

---

## 🎯 Schritt 3: Crew-Delegation

### F-Crew Delegation (Feature-Work)

Der Engineering Manager delegiert an die passenden F-Crew-Agents:

| Agent | Wann einsetzen? | Deliverable |
|-------|-----------------|-------------|
| **Software Architect** | System-Design, Architektur-Entscheidungen, Service-Boundaries | Architecture Decision Record (ADR) |
| **Refactoring Engineer** | Code-Quality-Improvements, Struktur-Optimierung | Refactoring-Plan + Code-Changes |
| **Code Reviewer** | Quality Assurance, Standards-Compliance-Check | Code-Review-Report |
| **Test Engineer** | Test-Strategie, Coverage-Improvements, Validation-Pläne | Test-Plan + Test-Implementation |
| **Data Architect** | Schema-Design, Data-Flow-Optimierung | Data-Model + Migration-Plan |
| **Documentation Engineer** | Doku-Updates, Knowledge-Base-Management | Updated Docs (Markdown) |
| **Project Planner** | Roadmap-Planung, Milestone-Tracking | Project-Plan + Timeline |

### C-Crew Delegation (Stability/Risk-Work)

Der Engineering Manager delegiert an die passenden C-Crew-Agents:

| Agent | Wann einsetzen? | Deliverable |
|-------|-----------------|-------------|
| **Risk Engineer** | Risk-Analyse, Exposure-Management, Circuit-Breaker-Design | Risk-Assessment-Report |
| **Stability Engineer** | Incident-Response, Live-Site-Reliability, Event-Flow-Analysis | Incident-Report (6-Layer-Analysis) |
| **DevOps Engineer** | CI/CD, Container-Orchestration, Infrastructure-Änderungen | Deployment-Plan + Infrastructure-Config |
| **Market Analyst** | Market-Data-Analysis, Trend-Identifikation | Market-Analysis-Report |
| **Derivatives Analyst** | Komplexe Derivatives, Hedging-Strategien | Derivatives-Strategy-Report |
| **Sentiment Analyst** | Social-Media-Analysis, News-Flow-Tracking | Sentiment-Report |
| **Data Engineer** | Data-Source-Evaluation, External-Data-Integration | Data-Source-Recommendation |

### Mixed-Crew Delegation

Bei Mixed-Crew-Tasks koordiniert der Engineering Manager:

1. **F-Crew** implementiert Feature/Fix in sicherer Umgebung
2. **C-Crew** validiert Risk-Model und Live-Site-Impact
3. **Engineering Manager** synchronisiert Outputs und präsentiert konsolidierte Empfehlung

**Beispiel-Flow:**

```
User: "Neues Momentum-Signal hinzufügen"
  ↓
Engineering Manager: Mixed-Crew Task
  ├─ F-Crew: Software Architect designt Signal-Logic
  ├─ F-Crew: Test Engineer erstellt Test-Plan
  ├─ C-Crew: Risk Engineer validiert Risk-Impact
  └─ Engineering Manager: Konsolidiert → User-Approval → Delivery
```

---

## 📊 Schritt 4: Tracking & Transparenz

### Task-Dokumentation

Jede Task wird dokumentiert in:

- **Engineering Dashboard:** `backoffice/docs/engineering/ENGINEERING_DASHBOARD.md`
  - Abschnitt "Active Work Streams" (F-Crew, C-Crew, Mixed)
- **Decision Log:** `backoffice/docs/DECISION_LOG.md`
  - Für ADR-würdige Entscheidungen (Architektur, Risk-Mode-Changes)
- **Block Retrospective:** `backoffice/docs/engineering/BLOCK_RETROSPECTIVE_TEMPLATE.md`
  - Nach Block-Ende: Was wurde gemacht, was gelernt?

### Status-Updates

Der Engineering Manager updated:

- **Täglich:** Dashboard-Abschnitt "Active Work Streams"
- **Bei Blocker:** Sofortige Eskalation an User + Dashboard-Update
- **Block-Ende:** Vollständige Retrospective

---

## 🚨 Schritt 5: Escalation an User

Der Engineering Manager eskaliert **sofort** an den User bei:

- **Live-Trading-Mode-Change-Requests** (Paper → Testnet-Live → Production-Live)
- **Kritischen Incidents** (Kapital-Risiko, Datenverlust, schwere Risk-Bugs)
- **Konflikten zwischen F-Crew und C-Crew** (z.B. Feature-Velocity vs. Stability)
- **Architektur-Änderungen mit signifikantem Risiko**
- **Budget- oder Ressourcen-Entscheidungen**

Der Engineering Manager **fragt nach Klarstellung** bei:

- **Ambigen User-Intentionen** (Was genau ist gewünscht?)
- **Mehreren validen Ansätzen** mit unterschiedlichen Trade-offs
- **Anforderungen, die mit Governance kollidieren** (z.B. "Test-Coverage senken")
- **Scope-Expansion** über ursprüngliche Anfrage hinaus

---

## 📋 Beispiel-Workflows

### Beispiel 1: Feature-Request (F-Crew Only)

**User:** "Ich möchte, dass der Bot auch USDC-Pairs handelt, nicht nur USDT."

**Engineering Manager Triage:**
- **Typ:** Feature
- **Routing:** F-Crew Only (kein Risk-Impact, nur neue Pairs)
- **Priority:** MEDIUM (klarer Business-Value, aber nicht blockierend)
- **Effort:** Medium (Config + Tests)

**Delegation:**
1. Software Architect: Design für Multi-Base-Currency-Support
2. Test Engineer: Test-Plan für USDC-Pairs
3. Code Reviewer: Review nach Implementation

**Tracking:** Dashboard → "F-Crew: Multi-Base-Currency-Support (Medium, Medium Effort)"

---

### Beispiel 2: Incident (C-Crew Only)

**User:** "Das System hat seit 24 Stunden keine Signale mehr generiert."

**Engineering Manager Triage:**
- **Typ:** Incident (Zero-Activity-Incident)
- **Routing:** C-Crew Only (System-Problem, kein Feature)
- **Priority:** HIGH (beeinträchtigt Block-Erfolg)
- **Effort:** Medium (Diagnose + Fix + Validation)

**Delegation:**
1. Stability Engineer: 6-Layer-Analysis (Market Data → Signal → Risk → Execution → DB)
2. Risk Engineer: Prüfen, ob Risk-Config Signale blockiert
3. DevOps Engineer: Container-Health + Event-Flow-Pulse

**Tracking:** Dashboard → "C-Crew: Zero-Activity-Incident (HIGH, Medium Effort)"

---

### Beispiel 3: Mixed-Crew Task

**User:** "Ich möchte ein neues Mean-Reversion-Signal implementieren."

**Engineering Manager Triage:**
- **Typ:** Feature
- **Routing:** Mixed-Crew (betrifft Trading-Logic → Risk-Validation nötig)
- **Priority:** MEDIUM (neues Signal, kein Blocker)
- **Effort:** Large (Design + Implementation + Risk-Validation + Tests)

**Delegation:**
1. **F-Crew:**
   - Software Architect: Signal-Engine-Design für Mean-Reversion
   - Test Engineer: Test-Strategie (Unit + Integration + E2E)
2. **C-Crew:**
   - Risk Engineer: Risk-Impact-Analyse (Exposure, Drawdown, Position-Limits)
   - Market Analyst: Backtesting-Empfehlungen für Mean-Reversion

**Koordination:**
- F-Crew implementiert in Paper-Umgebung
- C-Crew validiert Risk-Model
- Engineering Manager konsolidiert → User-Approval → Delivery

**Tracking:** Dashboard → "Mixed-Crew: Mean-Reversion-Signal (MEDIUM, Large Effort)"

---

## ✅ Success Criteria für den Intake-Prozess

Der Work Intake Process ist erfolgreich, wenn:

- ✅ **Jede Task** hat klare Klassifizierung (Typ, Routing, Priority, Effort)
- ✅ **Kein Agent** arbeitet ohne klare Delegation vom Engineering Manager
- ✅ **User** erhält konsolidierte Updates (nicht fragmentierte Agent-Outputs)
- ✅ **Eskalationen** erfolgen rechtzeitig und mit klarer Begründung
- ✅ **Dokumentation** ist vollständig (Dashboard, Decision Log, Retrospectives)

---

## 🔄 Kontinuierliche Verbesserung

### Feedback-Mechanismen

- **Nach jedem Block:** Retrospective-Abschnitt "Was lief gut / Was nicht"
- **Monatlich:** Engineering Manager reviewed Intake-Prozess
- **Bei Blocker:** Root-Cause-Analyse (War Triage korrekt? Routing optimal?)

### Anpassungen

- Prozess-Updates werden in diesem Dokument versioniert
- Änderungen werden im Decision Log dokumentiert (ADR)
- User wird über signifikante Prozess-Änderungen informiert

---

**Prozess-Owner:** Engineering Manager
**Version:** 1.0 (Initial Activation)
**Nächstes Review:** 2026-01-07 oder bei Bedarf
**Feedback an:** Engineering Manager (via User)
