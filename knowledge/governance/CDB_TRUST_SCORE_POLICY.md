---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
  downstream:
    - knowledge/agent_trust/
    - knowledge/governance/policy_cards/
  status: canonical
  tags: [trust, scoring, governance, agents, audit]
---
# CDB_TRUST_SCORE_POLICY
**Trust Score & Decision Governance – Canonical Policy**

Version: 1.0  
Status: Canonical  
Gültig ab: 2025-12-28

---

## 1. Zweck

Dieses Dokument definiert ein **einheitliches, auditierbares Trust- & Score-System**
für **alle Agenten** im Projekt *Claire de Binare (CDB)*:

- Claude
- Codex
- Gemini
- Copilot
- alle OpenCode-Agenten (und weitere Tools/Agenten)

Ziel: **kontrollierte Autonomie ohne Mikromanagement**.

---

## 2. Grundprinzip (bindend)

1) **Policies schlagen Agenten.**  
2) **Score steuert Autonomie, nicht Wahrheit.**  
3) **Unsicherheit ist erlaubt – Verschweigen ist ein Verstoß.**  
4) **Outcome zählt:** Rework, Revert, Reopen, Policy-Bruch → negative Wirkung.

Dieses System ersetzt keine User-Autorität und umgeht keine Gates.

---

## 3. Begriffe

### 3.1 Decision Event
Ein Decision Event ist eine **strukturierte, persistente** Aufzeichnung einer
Agenten-Entscheidung oder -Aktion mit Wirkung auf Systemzustand, Governance,
Issue/Branch-Lifecycle oder Deliverables.

Decision Events werden als YAML unter `knowledge/agent_trust/ledger/` abgelegt.

### 3.2 Uncertainty Marker (Pflicht bei Unsicherheit)
Pflicht-Flag: `uncertainty: true`

Unsicherheit liegt vor, sobald eine Entscheidung auf Annahmen basiert oder
die Policy-Lage nicht eindeutig ist.

### 3.3 Evidence
Verweise auf konkrete Artefakte (Dateipfade, PR/Issue-Links, Logs, Checks).

---

## 4. Score-Modell (3 Achsen)

Jeder Agent besitzt drei Scores (0–100):

- **Compliance (C):** Policy-/Governance-Konformität
- **Quality (Q):** Nachvollziehbarkeit, Evidence, Reversibilität, saubere Diffs
- **Safety (S):** Risiko- und Schadensbegrenzung, Kill-/Guardrail-Respekt

Ein **Composite Trust** wird aus C/Q/S berechnet (Gewichte in `TRUST_SCORE_CONFIG.yaml`).

---

## 5. Autonomie-Tiers (wirken auf Overhead & Eskalation)

Autonomie wird in Tiers gesteuert (Details/Schwellenwerte in `TRUST_SCORE_CONFIG.yaml`):

- **T3 (High Trust):** Standard-Autonomie (Zone A/B) mit minimalem Overhead
- **T2 (Normal):** Standardbetrieb (Zone A/B + Review-Hinweise, wenn nötig)
- **T1 (Restricted):** Pflicht-Begründung + Review-Flag für relevante Aktionen
- **T0 (Freeze):** Vorschlagspflicht bei allen risikobehafteten Aktionen (Zone C)

**Wichtig:** Tiers ändern keine Write-Gates, Tresor-Verbote oder Delivery-Gates.

---

## 6. Policy Cards (maschinenlesbar, erzwingbar)

Governance-Regeln werden als **Policy Cards** unter `knowledge/governance/policy_cards/`
formalisiert (YAML, versioniert).

Jede Card definiert:
- Trigger (wann gilt sie)
- Pflichtverhalten (MUST/SHOULD)
- Severity bei Verstoß
- Score-Impact (C/Q/S)

---

## 7. Eskalation & Enforcement (Human-in-the-Loop)

Bei Schwellenwerten oder bei Policy-Verstößen gilt:

- Agent markiert **Review Required**
- Agent stoppt **nur**, wenn eine Policy das verlangt (z. B. Delivery-Gate, Tresor)
- Agent liefert Optionen + Risiken + Evidence

Eskalationskanäle:
- Issue-Comment
- Session-Log
- Trust-Ledger Event (Pflicht)

---

## 8. Mindestpflichten je Aktionstyp

Decision Event ist verpflichtend für:
- Issue close/reopen/label changes
- Branch/PR Lifecycle Aktionen (Create/Merge/Delete-Entscheidungen)
- Änderungen an Governance-/Policy-Texten (auch als Vorschlag)
- Deaktivierung/Bypass von Checks/Guards
- „Obsolete“-Einstufungen oder DoD-Interpretationen

---

## 9. Gültigkeit

Diese Policy ist kanonisch.  
Verstöße werden als **Governance-Bruch** behandelt und im Trust-Ledger erfasst.
