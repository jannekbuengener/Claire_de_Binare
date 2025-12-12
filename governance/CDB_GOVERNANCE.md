# CDB_GOVERNANCE
**Rollen, Rechte, Zonen, Change-Control (Mini-Stack)**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Zweck & Verankerung

Dieses Dokument **operationalisiert verbindlich** die `CDB_CONSTITUTION.md`.

Jede Regel in dieser Datei besitzt:
- einen **technischen Durchsetzungsmechanismus**
- eine **auditierbare Spur**
- eine **klare Eskalationsinstanz**

Governance ist kein Prozesspapier, sondern **Systemvertrag**.

---

## 2. Rollenmodell (technisch verankert)

### 2.1 User (Owner / Operator)

**Rechte & Durchsetzung**
- **Tresor-Rechte:** Keys, Limits, Custody liegen außerhalb aller Runtime-Mounts.
- **Kill-Switch:** Separater Control-Pfad (nicht Teil der Trading-Pipeline).
- **Delivery-Freigabe:** explizites User-Go als persistiertes Flag (`DELIVERY_APPROVED=true`).

**Technische Sicherung**
- Kein Service besitzt Schreibrechte auf Tresor-Zonen.
- Kill-Switch ist unabhängig deployt.
- Delivery ohne gesetztes Flag ist technisch blockiert.

---

### 2.2 Session Lead (Primary Orchestrator)

**Mandat**
- Orchestriert Modelle.
- Konsolidiert Ergebnisse.
- Prüft Governance-Compliance.

**Technische Kontrolle**
- Einziger Sprecherkanal.
- Write-Zugriff ausschließlich:
  - `CDB_KNOWLEDGE_HUB.md`
  - `.cdb_agent_workspace/*`
- Kein Commit-/Merge-Recht.

---

### 2.3 Peer-Modelle (Gemini, GPT, Copilot, Codex)

**Einschränkungen (hart)**
- Kein Sprecherstatus (kein Output an User).
- Kein Delivery-Recht.
- Keine direkten Repo-Writes.

**Durchsetzung**
- Modelle laufen ohne Commit-Credentials.
- Filesystem read-only.
- Writes nur via Session Lead erlaubt.

---

## 3. Zonenmodell (Write-Gates)

### 3.1 Zonen (unverändert)
- Core-Zone: `/core`, `/services`, `/infrastructure`, `/tests`
- Governance-Zone: `/governance/*.md`
- Knowledge-Zone: `CDB_KNOWLEDGE_HUB.md`
- Workspace-Zone: `.cdb_agent_workspace/*` (lokal, gitignored)
- Tresor-Zone: Secrets/Keys/Limits/Custody (außerhalb Repo)

---

### 3.2 Schreibregeln (technisch erzwungen)

- **Analysis Mode**
  - Repo global read-only
  - Persistenz nur in Knowledge- oder Workspace-Zone

- **Delivery Mode**
  - Aktiv nur bei `DELIVERY_APPROVED=true`
  - Writes ausschließlich via Branch/PR
  - Pre-Commit & CI blockieren:
    - Governance/Core-Writes ohne Flag
    - neue Top-Level-Strukturen
    - Änderungen an Tresor-Referenzen

- **Tresor-Zone**
  - Kein Mount
  - Kein Netzwerkpfad
  - Human-only

➡️ Empfehlungen wurden entfernt. Nur Zwang.

---

## 4. Arbeitsmodi

### 4.1 Analysis Mode (Default)

**Technische Regeln**
- Filesystem: read-only
- Kein Git-Write
- Knowledge Hub ist einziger persistenter Kanal

**Audit**
- Analyse-Ergebnisse mit Timestamp + Modell-ID

---

### 4.2 Delivery Mode (Explizit)

**Aktivierung**
- Manuelles Setzen von `DELIVERY_APPROVED=true`

**Sicherungen**
- Alle Änderungen als Diff/PR
- Kein Auto-Merge
- Hash-Vergleich vor/nach Merge
- CI prüft Write-Zonen

➡️ Silent Changes technisch unmöglich.

---

## 5. Dev-Freeze (KI-Ausfall)

**Trigger**
- Coding-KI nicht verfügbar oder nicht verifizierbar
- Health-Check / Capability-Check schlägt fehl

**Durchsetzung**
- CI blockiert alle strukturellen Merges
- Branch-Protection aktiv
- Nur Betriebsparameter erlaubt

**Nachweis**
- Freeze-Status im Knowledge Hub geloggt

---

## 6. Konfliktlösung (auditierbar)

**Priorität (hart codiert)**
1. Sicherheit
2. Determinismus
3. Performance
4. Komfort

**Mechanismus**
- Session Lead konsolidiert
- User entscheidet
- Entscheidung wird versioniert dokumentiert

---

## 7. Change-Flow (technisch gebunden)

1) Knowledge Hub Proposal  
2) Analyse + Akzeptanzkriterien  
3) Plan + Tests + Rollback  
4) User-Go → Flag  
5) Branch/PR  
6) CI-Enforcement  
7) Merge  
8) Post-Check & Log

---

## 8. Gültigkeit

Diese Governance ist **kanonisch**.  
Abweichungen gelten als Verfassungsbruch.

Keine Ausnahmen.
