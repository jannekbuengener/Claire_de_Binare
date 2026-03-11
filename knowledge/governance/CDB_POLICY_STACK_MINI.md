---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
  downstream:
    - knowledge/governance/CDB_AGENT_POLICY.md
    - knowledge/governance/CDB_TRUST_SCORE_POLICY.md
    - knowledge/governance/CDB_INFRA_POLICY.md
    - knowledge/governance/CDB_RL_SAFETY_POLICY.md
    - knowledge/governance/CDB_TRESOR_POLICY.md
    - knowledge/governance/CDB_PSM_POLICY.md
    - knowledge/governance/DELIVERY_APPROVED.yaml
    - knowledge/CDB_KNOWLEDGE_HUB.md
  status: canonical
  tags: [policy_stack, governance, safety]
---
# CDB_POLICY_STACK_MINI
**Mini-Policy-Stack – Kanonischer Governance- & Safety-Kern**

Version: 1.2  
Status: Canonical

---

## 1. Ziel & Verbindlichkeit

Dieser Mini-Policy-Stack ist die **kleinste stabile, kanonische Basis**
für Betrieb, Audit und Weiterentwicklung von *Claire de Binare (CDB)*.

Alle enthaltenen Dokumente sind:
- deterministisch wirksam
- technisch durchgesetzt
- auditierbar
- versionsstabil

Es existiert **kein** weiterer impliziter Regelraum außerhalb dieses Stacks.

---

## 2. Kanonischer Satz (abschließend)

1. `CDB_CONSTITUTION.md` – höchste Instanz (Prinzipien & Grenzen)
2. `CDB_GOVERNANCE.md` – Rollen, Zonen, Change-Control
3. `CDB_AGENT_POLICY.md` – KI-/Agentenregeln, Write-Gates
4. `CDB_TRUST_SCORE_POLICY.md` – Trust Score, Decision Events, Enforcement
5. `CDB_INFRA_POLICY.md` – IaC, GitOps, Eventing, K8s-Readiness
6. `CDB_RL_SAFETY_POLICY.md` – RL-Guardrails, Action Masking, Kill-Switch
7. `CDB_TRESOR_POLICY.md` – Tresor-Zone & Human-Only-Kontrollen
8. `CDB_PSM_POLICY.md` – Portfolio & State Manager (Single Source of Truth)
9. `DELIVERY_APPROVED.yaml` – human-only Delivery Gate

Nicht-kanonische oder als Draft markierte Dateien gehören **nicht** in diesen Stack.

---

## 3. Lesereihenfolge (bindend)

1) Constitution  
2) Governance  
3) Agent Policy  
4) Trust Score Policy  
5) Infra Policy  
6) RL Safety Policy  
7) Tresor Policy  
8) PSM Policy  
9) Delivery Gate

Diese Reihenfolge ist verbindlich für Reviews, Audits und Onboarding.

---

## 4. Änderungsregel (hart, technisch erzwingbar)

Änderungen an einem Dokument dieses Stacks sind nur zulässig über:

1) **Proposal**  
   - Eintrag im `knowledge/CDB_KNOWLEDGE_HUB.md` (Änderungs-ID, Scope)

2) **Review**  
   - Konsistenzprüfung gegen Constitution & Governance
   - Ergebnis dokumentiert (MUST/SHOULD/NICE)

3) **Explizite User-Freigabe**  
   - Delivery Gate bleibt davon unberührt (separat)

4) **Versionierter Merge**  
   - Branch / PR
   - CI-Gates schützen Policies
   - direkte Änderungen am Default-Branch sind blockiert

Verstoß = Governance-Bruch.

---

## 5. Gültigkeit

Dieser Mini-Stack ist **kanonisch und abschließend**.

Keine stillen Änderungen.  
Keine Ausnahmen.
