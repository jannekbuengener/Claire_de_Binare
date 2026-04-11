---
name: Meta Issue – Governance / Policy
about: Policies, Regeln, System-Governance (Entscheidung + Adoption)
title: "[META][GOV] <Thema>"
labels: []
assignees: []
---

## Context
Governance-/Policy-Thema mit systemweiter Relevanz.

---

## Scope
- Betroffene Bereiche:
  - Docs
  - Prozesse
  - Agenten / Rollen
  - CI / Quality Gates (nur konzeptionell im Issue)

---

## Related Issues / Docs
- #<Issue-ID>
- `docs/<pfad>.md`

---

## Analysis (Agent)
- Problem
- Policy-Ansatz
- Risiken

**Decision Line:**  
`Status: READY FOR ADOPTION` **oder** `BLOCKED — <Grund>`

---

## Governance Actions
- Append-only Ledger-Eintrag (Entscheidung)
- Doku-Update (Adoption)
- `CURRENT_STATUS.md` aktualisieren, wenn sich der Repo-/Engineering-Stand ändert
- `knowledge/CURRENT_STATUS.md` aktualisieren, wenn der historische Mirror nachgezogen werden muss
- `docs/runbooks/CONTROL_REGISTER.md` nur dann aktualisieren, wenn die Policy Control-Board-Stage, Operating Focus oder Control-Surfaces betrifft
- Kommunikation (falls nötig)

---

## Definition of Done
- Policy beschlossen und die Adoption ist in den Ziel-Branch gemerged
- Dokumentiert
- Referenziert (Backlinks in relevanten Docs)
- Ledger konsistent und append-only gepflegt
- `CURRENT_STATUS.md` synchronisiert

---

## Meta
- **Owner:** <Name>
- **Agent:** claude / codex
