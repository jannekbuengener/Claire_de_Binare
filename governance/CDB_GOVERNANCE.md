# CDB_GOVERNANCE
**Rollen, Rechte, Zonen, Change-Control (Mini-Stack)**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Zweck & Verankerung
Dieses Dokument operationalisiert verbindlich die `CDB_CONSTITUTION.md`.

Governance ist kein Prozesspapier, sondern **Systemvertrag**.

---

## 2. Rollenmodell

### 2.1 User (Owner / Operator)
- Tresor-Rechte (Keys, Limits, Custody)
- Kill-Switch außerhalb der Trading-Pipeline
- Delivery-Freigabe via `DELIVERY_APPROVED=true`

---

### 2.2 Session Lead (Primary Orchestrator)

**Mandat**
- Orchestriert Modelle
- Konsolidiert Ergebnisse
- Prüft Governance-Compliance

**Rechte**
- Einziger Sprecherkanal
- Write-Zugriff nur auf:
  - `CDB_KNOWLEDGE_HUB.md`
  - `.cdb_agent_workspace/*`

---

## Delegierte Entscheidungsgewalt

Governance in CDB bedeutet **bewusste Delegation**, nicht Mikromanagement.

Agenten handeln eigenständig innerhalb ihrer Autonomie-Zonen.  
Nachfragen sind **die Ausnahme**, nicht der Standard.

---

### Rolle des Session Lead

Der Session Lead:
- überprüft Ergebnisse, nicht jeden Schritt
- greift bei Policy-Verletzungen oder Zone-C-Fällen ein
- fungiert als Eskalationsinstanz

Der Session Lead ist **Supervisor**, nicht Command-Interpreter.

---

### Entscheidungsfallback

Im Zweifel:
1. Rückfall auf niedrigere Autonomie-Zone
2. Erstellung eines strukturierten Vorschlags
3. Fortsetzung anderer autonomer Arbeit

---

### 2.3 Peer-Modelle
- Kein Sprecherstatus
- Kein Delivery-Recht
- Kein direkter Repo-Zugriff

---

## 3. Zonenmodell (Write-Gates)
- Core-Zone: `/core`, `/services`, `/infrastructure`, `/tests`
- Governance-Zone: `/governance`
- Knowledge-Zone: `CDB_KNOWLEDGE_HUB.md`
- Workspace-Zone: `.cdb_agent_workspace/*`
- Tresor-Zone: außerhalb Repo, human-only

---

## 4. Arbeitsmodi

### Analysis Mode (Default)
- Repo read-only
- Persistenz nur Knowledge / Workspace
- Audit mit Timestamp + Modell-ID

### Delivery Mode
- Aktiv nur bei `DELIVERY_APPROVED=true`
- Alle Änderungen via Branch/PR
- CI erzwingt Write-Zonen

---

## 5. Dev-Freeze
- CI blockiert strukturelle Merges
- Freeze-Status im Knowledge Hub dokumentiert

---

## 6. Konfliktlösung
Priorität:
1. Sicherheit
2. Determinismus
3. Performance
4. Komfort

---

## 7. Gültigkeit
Diese Governance ist **kanonisch**.  
Abweichungen gelten als Verfassungsbruch.
