# CDB_CONSTITUTION
**Claire de Binare – Systemverfassung (Mini-Stack)**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Scope & Rangordnung

1. Diese Verfassung ist die **höchste Instanz** für Regeln und Prioritäten im Projekt *Claire de Binare (CDB)*.
2. Im Konfliktfall gilt strikt folgende Rangordnung:
   1) `CDB_CONSTITUTION.md`  
   2) `CDB_GOVERNANCE_MASTER.md`  
   3) Spezifische Policies (`CDB_*_POLICY.md`)  
   4) Implementierung (Code / Config / IaC)  
   5) KI-Vorschläge / Tool-Empfehlungen

---

## 2. Systemziel (nicht verhandelbar)

1. CDB ist ein **deterministisches, event-getriebenes Trading-System**  
   *(market → signal → risk → order → result)*.
2. Jeder Systemzustand muss **reproduzierbar** sein:
   ```bash
   git clone <repo>
   docker compose up
   ```
3. Das System darf **niemals** zur Blackbox werden.

---

## 3. Souveränität, Dezentralisierung & Grundrechte

### 3.1 Souveränität des Nutzers (TECHNISCH ERZWUNGEN)

- Self-Custody: Keys & Signing außerhalb aller Services
- Tresor-Zone: nicht mountbar, human-only
- Dual-Control bei Kapitalbewegungen
- Read-only State-Mirrors für Services
- Kill-Switch außerhalb der Trading-Pipeline

---

### 3.2 Dezentralisierung (ARCHITEKTURELL)

- Event-Sourcing als Source of Truth
- Austauschbare Runtime (Docker → K8s)
- Keine SaaS/KI-Abhängigkeiten im Kern
- Offene Protokolle & Formate

---

### 3.3 Transparenz (VERIFIZIERBAR)

- Append-only Event-Logs
- Replay-fähige Zustandsrekonstruktion
- Versionierte Schemas & Configs
- Klare Trennung öffentlich / privat

---

### 3.4 Resilienz (FAILURE-AWARE)

- Stateless Services
- Idempotente Verarbeitung
- Graceful Degradation
- Kill-Switch-Level
- Safe-Fallbacks

---

### 3.5 Auditierbarkeit & Reversibilität

- Git als SoT für Änderungen
- Deterministische Replays
- Rollback durch Replay + Revert

---

## 4. Governance & Konsens

### 4.1 Konsensmechanismus

- Proposal → Review → User-Freigabe → PR-Merge
- Kein automatischer Konsens
- Keine KI-Delegation

---

### 4.2 Offene Entwicklung

- Git (self-hosted / GitHub / GitLab)
- Apache 2.0 (Code), CC BY-SA 4.0 (Governance)
- PR-basierter Review-Prozess

---

### 4.3 Meritorische Entscheidungen

- Qualität, Sicherheit, Nachvollziehbarkeit > Geschwindigkeit

---

## 5. KI-Governance

- KI ist Werkzeug
- Kein autonomer Betrieb
- Strikte Write-Gates

---

## 6. Gültigkeit

Diese Verfassung ist **kanonisch**.
