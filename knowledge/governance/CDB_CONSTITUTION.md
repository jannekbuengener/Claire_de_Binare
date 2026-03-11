---
relations:
  role: policy
  domain: governance
  upstream: []
  downstream:
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_INFRA_POLICY.md
    - knowledge/governance/CDB_POLICY_STACK_MINI.md
    - knowledge/governance/CDB_PSM_POLICY.md
    - knowledge/governance/CDB_REPO_GUIDELINES.md
    - knowledge/governance/CDB_REPO_STRUCTURE.md
    - knowledge/governance/CDB_RL_SAFETY_POLICY.md
    - knowledge/governance/CDB_TRESOR_POLICY.md
    - knowledge/governance/DELIVERY_APPROVED.yaml
  status: canonical
  tags: [constitution, governance, core_principles]
---
# CDB_CONSTITUTION
**Claire de Binare – Systemverfassung (Canonical)**

Version: 1.2  
Status: Canonical  
Gültig ab: 2025-12-12

---

## 1. Scope & Rangordnung (höchste Instanz)

Diese Verfassung ist die **oberste Autorität** für Regeln und Prioritäten im Projekt
*Claire de Binare (CDB)*.

Im Konfliktfall gilt strikt folgende Rangordnung:

1) `CDB_CONSTITUTION.md`  
2) `CDB_GOVERNANCE.md`  
3) Spezifische Policies (`CDB_*_POLICY.md`)  
4) Implementierung (Code / Config / IaC)  
5) KI-Vorschläge / Tool-Empfehlungen

Kein Dokument, kein Agent und kein Tool darf diese Rangordnung umgehen.

---

## 2. Systemziel (nicht verhandelbar)

1) CDB ist ein **deterministisches, event-getriebenes Trading-System**  
   *(market → signal → risk → order → result)*

2) Jeder Systemzustand muss **reproduzierbar** sein:
   - Code & Konfiguration versioniert
   - Zustandsrekonstruktion per Replay möglich
   - keine Blackbox-Entscheidungswege

3) Das System darf **niemals** zur Blackbox werden.

---

## 3. Souveränität, Dezentralisierung & Grundrechte

### 3.1 Souveränität des Users (technisch erzwungen)

- Self-Custody: Keys & Signing außerhalb aller Services
- Tresor-Zone: human-only, nicht mountbar
- Dual-Control bei Kapitalbewegungen
- Read-only State-Mirrors für Services
- Kill-Switch außerhalb der Trading-Pipeline

### 3.2 Dezentralisierung (architekturell)

- Event-Sourcing als Source of Truth
- Austauschbare Runtime (Docker → K8s als Zielbild)
- Keine SaaS-/KI-Abhängigkeiten im Kern
- Offene Protokolle & Formate

### 3.3 Transparenz (verifizierbar)

- Append-only Event-Logs
- Replay-fähige Zustandsrekonstruktion
- Versionierte Schemas & Configs
- Klare Trennung öffentlich / privat

### 3.4 Resilienz (failure-aware)

- Stateless Services, wo möglich
- Idempotente Verarbeitung
- Graceful Degradation
- Safe-Fallbacks
- Kill-Switch-Level

### 3.5 Auditierbarkeit & Reversibilität

- Git als Source of Truth für Änderungen
- Deterministische Replays
- Rollback über Replay + Revert

---

## 4. Governance & Konsens (bindend)

### 4.1 Konsensmechanismus

- Proposal → Review → User-Freigabe → PR/Merge
- Kein automatischer Konsens
- Keine KI-Delegation von Freigaben

### 4.2 Delivery-Gate (human-only)

Delivery Mode ist **nur** zulässig, wenn das explizite Gate gesetzt ist:

- `knowledge/governance/DELIVERY_APPROVED.yaml`  
  - `delivery.approved: true` bedeutet: Delivery Mode erlaubt  
  - `false` oder Datei fehlt bedeutet: Analysis Mode (Default)

Regel:
- Kein Agent darf dieses Gate setzen oder ändern.
- Ohne Gate: **keine Mutationen** an Code/Infra/Policies.

### 4.3 Meritorische Entscheidungen

- Qualität, Sicherheit, Nachvollziehbarkeit > Geschwindigkeit

---

## 5. KI-Governance (grundlegend)

- KI ist Werkzeug, nicht Betreiber
- Kein autonomer Betrieb
- Strikte Write-Gates
- Keine stillen Änderungen
- Keine Ausführung ohne Risk-Layer

Details: `CDB_AGENT_POLICY.md` und `CDB_TRUST_SCORE_POLICY.md`

---

## 6. Gültigkeit

Diese Verfassung ist **kanonisch**.  
Abweichungen sind Systembruch und gelten als Fehlerzustand.
