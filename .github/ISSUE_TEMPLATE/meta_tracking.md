---
name: Meta Issue – Tracking
about: Reines Koordinations- und Fortschritts-Tracking (minimal)
title: "[META][TRACKING] <Thema>"
labels: []
assignees: []
---

## Ziel
Transparente Übersicht ohne inhaltliche Steuerung.

---

## Items
- [ ] #<Issue-ID>
- [ ] #<Issue-ID>

---

## Fortschritt
- ⏳ In Arbeit
- ✅ Erledigt
- ❌ Blockiert

---

## Notes
- …

---

## Closure / Bookkeeping
- Das Tracking-Issue bleibt offen, bis die getrackten Punkte erfolgreich gemerged und geschlossen sind.
- Lokale Fertigstellung oder reine Fortschrittsmarkierung zaehlen nicht als Done.
- `CURRENT_STATUS.md` aktualisieren, wenn sich der sichtbare Repo-/Engineering-Stand aendert.
- `knowledge/CURRENT_STATUS.md` nur dann aktualisieren, wenn der historische Mirror bewusst nachgezogen wird.
- Einen append-only Ledger-Eintrag unter `knowledge/agent_trust/ledger/` anhaengen, wenn Tracking-Status oder Zuordnung aendert.
- `docs/runbooks/CONTROL_REGISTER.md` nur dann aktualisieren, wenn das Tracking Control-Board-Stage, Operating Focus oder Control-Surfaces betrifft.

---

## Definition of Done
- Alle Items erfolgreich gemerged und abgeschlossen
- `CURRENT_STATUS.md` synchronisiert, falls der sichtbare Stand betroffen ist
- Ledger konsistent und append-only gepflegt
- Meta-Issue erst nach Merge-Stand geschlossen
