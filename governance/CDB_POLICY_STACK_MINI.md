# CDB_POLICY_STACK_MINI
**Mini-Policy-Stack – Kanonischer Governance- & Safety-Kern**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel & Verbindlichkeit

Dieser Mini-Policy-Stack definiert die **kleinste kanonische, stabile und verbindliche Basis**
für Governance, Safety und Kontrolle in *Claire de Binare (CDB)*.

Alle enthaltenen Dokumente sind:
- deterministisch wirksam,
- technisch durchgesetzt,
- auditierbar,
- versionsstabil.

Es existiert **kein weiterer impliziter Regelraum** außerhalb dieses Stacks.

---

## 2. Dateien (kanonisch, technisch verankert)

Die folgenden Dateien bilden gemeinsam den **kanonischen Policy-Kern**.  
Eine Datei gilt nur dann als *kanonisch*, wenn sie:

- den Status **Canonical** trägt,
- versioniert ≥ **1.0.0** ist,
- durch CI/Review-Gates geschützt ist.

**Kanonischer Satz:**

1. `CDB_CONSTITUTION.md` – höchste Instanz (Prinzipien & Grenzen)
2. `CDB_GOVERNANCE.md` – Rollen, Zonen, Change-Control
3. `CDB_AGENT_POLICY.md` – KI-/Agentenregeln, Write-Gates
4. `CDB_INFRA_POLICY.md` – IaC, GitOps, Eventing, K8s-Readiness
5. `CDB_RL_SAFETY_POLICY.md` – RL-Guardrails, Action Masking, Kill-Switch
6. `CDB_TRESOR_POLICY.md` – Tresor-Zone & Human-Only-Kontrollen
7. `CDB_PSM_POLICY.md` – Portfolio & State Manager (Single Source of Truth)

Nicht-kanonische oder als *Draft* markierte Dateien **dürfen nicht** Bestandteil dieses Stacks sein.

---

## 3. Lesereihenfolge (bindend)

1) Constitution  
2) Governance  
3) Agent Policy  
4) Infra Policy  
5) RL Safety Policy  
6) Tresor Policy  
7) PSM Policy

Diese Reihenfolge ist verbindlich für Reviews, Audits und Onboarding.

---

## 4. Änderungsregel (TECHNISCH ERZWUNGEN)

Änderungen an **irgendeinem Dokument dieses Stacks** sind ausschließlich über
den folgenden, technisch verankerten Prozess zulässig:

1. **Proposal**
   - Eintrag im `CDB_KNOWLEDGE_HUB.md`
   - eindeutige Änderungs-ID

2. **Review**
   - Konsistenzprüfung gegen Constitution & Governance
   - dokumentiertes Review-Ergebnis

3. **Explizite User-Freigabe**
   - manuelle Bestätigung (kein Delegieren an KI)

4. **Versionierter Merge**
   - Branch / Pull Request
   - CI-Gates:
     - Schutz der Policy-Dateien
     - Blockade direkter Commits
     - Hash-Vergleich vor/nach Merge

**Durchsetzung:**
- Branch-Protection ist Pflicht.
- Direkte Änderungen im Default-Branch sind technisch blockiert.
- Jeder Verstoß gilt als Governance-Bruch.

---

## 5. Gültigkeit

Dieser Mini-Policy-Stack ist **kanonisch und abschließend**.  
Er definiert die minimale stabile Basis für Betrieb, Audit und Weiterentwicklung.

Keine stillen Änderungen.  
Keine Ausnahmen.
