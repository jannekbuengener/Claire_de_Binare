---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
  downstream:
    - knowledge/CDB_KNOWLEDGE_HUB.md
    - agents/
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_TRUST_SCORE_POLICY.md
  status: canonical
  tags: [governance, roles, zones, change_control]
---
# CDB_GOVERNANCE
**Rollen, Rechte, Zonen & Change-Control (Canonical)**

Version: 1.2  
Status: Canonical  
Gültig ab: 2025-12-28

---

## 1. Zweck

Dieses Dokument operationalisiert die `CDB_CONSTITUTION.md` und definiert:
- Rollen & Verantwortlichkeiten
- Entscheidungs- und Change-Control
- Eskalation & Audit

Governance ist ein **Systemvertrag**: klar, erzwingbar, auditierbar.

---

## 2. Rollenmodell (bindend)

### 2.1 User (Owner / Operator)
Der User ist die **höchste Autorität** im System.

**Rechte**
- Tresor-/Custody-Zugriff (Keys, Limits, Kapital)
- Kill-Switch außerhalb der Trading-Pipeline
- finale Entscheidungen (Policy, Architektur, Delivery)

### 2.2 Session Lead
Der Session Lead orchestriert Arbeit, priorisiert und koordiniert Agenten.
Er ist **nicht** oberste Instanz und darf User-Autorität nicht substituieren.

### 2.3 Agents (Claude, Codex, Gemini, Copilot, OpenCode, …)
Agenten sind **Rollen mit Scope**, keine autonomen Betreiber.

Pflichten:
- Policy-Konformität (Mini-Stack)
- Auditierbare Decision Events bei relevanten Aktionen
- Bei Unsicherheit: deklarieren + Optionen liefern

### 2.4 Tools / Automationen
Tools sind exekutiv und dürfen Governance nicht umgehen.
Sie handeln nur innerhalb der von Policies definierten Grenzen.

---

## 3. Betriebsmodi: Analysis vs Delivery (hart)

### 3.1 Default: Analysis Mode
Ohne Delivery-Gate sind Agenten in **Analysis Mode**:
- Vorschläge, Pläne, Reviews
- keine Mutationen an Code/Infra/Canonical Policies

### 3.2 Delivery Mode (human-only Gate)
Delivery ist nur erlaubt, wenn gesetzt:

- `knowledge/governance/DELIVERY_APPROVED.yaml`
  - `delivery.approved: true`

**Regel:** Kein Agent darf das Gate setzen oder verändern.

---

## 4. Autonomie-Zonen (über Agent Policy)

Die Autonomie-Zonen A–D sind in `CDB_AGENT_POLICY.md` definiert und bindend.
Das Trust-System steuert **Overhead & Eskalation**, nicht die Grenzen.

Referenz:
- `knowledge/governance/CDB_AGENT_POLICY.md`
- `knowledge/governance/CDB_TRUST_SCORE_POLICY.md`

---

## 5. Change-Control (verbindliche Reihenfolge)

1) Proposal (klarer Scope + Evidence)  
2) Review (Konsistenz zu Constitution/Governance/Policies)  
3) User-Freigabe (explizit)  
4) PR/Merge (versioniert, auditierbar)  
5) Close von Issues nur nach Lifecycle-Policy

---

## 6. Trust Score, Eskalation & Enforcement

### 6.1 Zweck
Trust Score ist ein **Governance-Control-Layer**:
- reduziert Schema-Entscheidungen
- erzwingt Unsicherheits-Transparenz
- steuert Autonomie-Overhead

### 6.2 Mechanik
- Policies werden als **Policy Cards (YAML)** formalisiert
- Jede relevante Aktion erzeugt ein **Decision Event** (append-only Ledger)
- Score wird ex-post aus Ledger + Outcome abgeleitet

### 6.3 Eskalation
Eskalation ist verpflichtend bei:
- Policy-Edge-Cases
- irreversiblen Effekten
- Tresor-/Limit-Nähe
- Lifecycle-Aktionen (Issue close, Obsolete, Gate-Themen)

---

## 7. Audit & Logging (bindend)

- Decision Events: `knowledge/agent_trust/ledger/`
- Session Logs: `knowledge/logs/sessions/` (oder `logs/` nach Repo-Konvention)
- Incidents: `knowledge/agent_trust/incidents/`

Logs sind:
- deterministisch, nachvollziehbar
- secret-frei
- append-only, wenn als Ledger definiert

---

## 8. Gültigkeit

Diese Governance ist kanonisch.  
Abweichungen sind Governance-Bruch und werden als Trust-/Incident-Events erfasst.
