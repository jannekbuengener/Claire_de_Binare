
---
relations:
  role: doc
  domain: governance
  upstream:
    - governance/CDB_TRUST_SCORE_POLICY.md
  downstream:
    - governance/policy_cards/schema.yaml
  status: canonical
  tags: [policy_cards, governance, machine_readable]
---
# Policy Cards

Policy Cards sind maschinenlesbare Regeln, die:
- Agentenhandeln deterministisch bewerten
- Trust Score Impacts definieren
- Eskalation/Enforcement auslösen

## Konvention
- Jede Card hat eine ID `PC-XXX`.
- Jede Card definiert `severity` und `trust_impact`.
- Cards überschreiben keine Canon-Regeln – sie codieren sie.

## SSOT boundary
Policy cards codify governance; they do not grant LR/live-capital authorization. LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
