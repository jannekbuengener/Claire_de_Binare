---
name: Meta Issue – Phase Gate
about: Phasensteuerung (Analyse / Implementierung / Governance) als Gate-Issue
title: "[META][PHASE] <Phase-Name>"
labels: []
assignees: []
---

## Phase Definition
- **Phase:** analysis | implementation | governance
- **Ziel:** Klarer Übergang zur nächsten Phase

---

## Eingangskriterien
- …

---

## Zugehörige Issues
- [ ] #<Issue-ID>
- [ ] #<Issue-ID>

---

## Gate Status
- Aktuell: OPEN / READY / BLOCKED

---

## Governance Steps
1. Status-Review aller zugehörigen Issues
2. Append-only Ledger-Update (falls Statuswechsel / Entscheidung)
3. Entscheidung: GO / NO-GO

---

## Decision
`Phase Status: READY` **oder** `BLOCKED — <Grund>`

---

## Definition of Done
- Gate offiziell erst nach erfolgreichem Merge der erfuellten Aenderungen abgeschlossen
- Entscheidungen dokumentiert
- Ledger konsistent und append-only gepflegt
- `CURRENT_STATUS.md` synchronisiert, wenn der Gate-Stand den Repo-/Engineering-Stand aendert
- `knowledge/CURRENT_STATUS.md` synchronisiert, wenn der historische Mirror nachgezogen wird
- `docs/runbooks/CONTROL_REGISTER.md` nur dann aktualisieren, wenn das Gate Control-Board-Stage, Operating Focus oder Control-Surfaces betrifft

---

## Meta
- **Owner:** <Name>
- **Agent:** claude / codex
