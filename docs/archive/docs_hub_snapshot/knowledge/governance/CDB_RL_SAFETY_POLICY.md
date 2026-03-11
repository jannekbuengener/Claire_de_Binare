---
# ✅ FINALER TEXT – `knowledge/governance/CDB_RL_SAFETY_POLICY.md`  
*(vollständig ersetzen; konsistent mit Tresor & Governance)* :contentReference[oaicite:2]{index=2}

```md
---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_TRESOR_POLICY.md
    - knowledge/governance/CDB_PSM_POLICY.md
  downstream: []
  status: canonical
  tags: [rl, safety, policy]
---
# CDB_RL_SAFETY_POLICY
**Safe Reinforcement Learning – Canonical Safety Policy**

Version: 1.1  
Status: Canonical

---

## 1. Ziel & Sicherheitsgarantie

RL darf ausschließlich innerhalb **deterministischer, technisch erzwungener Guardrails**
operieren.

Garantien:
- keine autonome Ausführung ohne deterministische Prüfung
- keine probabilistische Sicherheitslogik
- Sicherheit > Profit > Lernfortschritt

---

## 2. Deterministische Guardrails (Definition)

Guardrails sind reine, deterministische Funktionen:

(State × Action × Limits) → erlaubte Aktion

Eigenschaften:
- kein Zufall
- kein Modell
- keine Seiteneffekte
- replay-identisch

Nachweis:
- identischer Input → identischer Output
- CI-Replay-Tests erzwingen Determinismus

---

## 3. Verantwortlichkeitstrennung (hart)

Pipeline:
RL Policy → Risk/Constraint Layer → Action Masking → Execution

Durchsetzung:
- RL-Service besitzt **keinen Netzwerkpfad** zur Execution
- nur Risk-Layer darf Orders erzeugen
- Execution akzeptiert nur validierte Actions

---

## 4. Action Masking (nicht umgehbar)

- Aktionsraum wird vor Auswahl reduziert
- Default-Aktion: `HOLD`
- Mask basiert ausschließlich auf:
  - PSM-State (read-only)
  - Hard Risk Limits (read-only)

Integrität:
- Hash-Prüfung der Input-States
- Abweichung → HOLD + Audit-Event

---

## 5. Kill-Switch Stufen (durchgesetzt)

Stufen:
1. REDUCE_ONLY
2. HARD_STOP
3. EMERGENCY

Trigger:
- Drawdown / Daily Loss
- Risk-Limit-Verletzung
- Systemfehler / Latenz
- Dateninkonsistenz

Durchsetzung:
- Kill-Switch läuft außerhalb der Trading-Pipeline
- Status wird als Event persistiert
- Rücknahme nur mit User-Freigabe

---

## 6. Shadow & Canary (verifiziert)

Shadow:
- 0 Kapital
- identische Inputs
- Vergleich RL vs Referenzstrategie

Canary:
- hart begrenztes Kapital
- getrennte Accounts/Limits
- Auto-Abbruch bei Metrik-Verletzung

Promotion:
- Metrics-Gates erfüllt
- explizites User-Go
- versionierter Wechsel

---

## 7. Audit & Explainability (immutable)

Pro Entscheidung:
- Input-State (Hash)
- Proposed Action
- Action Mask
- Executed Action
- Guardrail-Version
- RL-Policy-Version
- Timestamp

Speicherung:
- append-only Event-Store
- manipulationssicher
- replay-fähig

---

## 8. Tresor-Regel (absolut)

RL darf niemals:
- Hard Limits ändern
- Keys / Custody berühren
- Governance mutieren

Durchsetzung:
- kein Schreibzugriff
- kein API-Zugriff
- CI- & Runtime-Guards

---

## 9. Durchsetzung

CI prüft:
- Guardrail-Determinismus
- Masking-Korrektheit
- Kill-Switch-Reaktionen

Verstöße blockieren Releases.

---

## 10. Gültigkeit

Diese Policy ist kanonisch.  
Autonomie ohne diese Garantien ist verboten.
