---
name: Meta Issue – Cluster
about: Übergeordnetes Meta-Issue zur Bündelung mehrerer Issues (Cluster-Steuerung)
title: "[META][CLUSTER] <Cluster-Name>"
labels: []
assignees: []
---

## Purpose
Übergeordnetes Meta-Issue zur Steuerung eines thematischen Clusters (Painpoints, Initiative, Release-Strang).

---

## Scope
**Enthält**
- #<Issue-ID>
- #<Issue-ID>

**Nicht enthalten**
- …

---

## Child Issues (Single Source of Truth)
- [ ] #<Issue-ID>
- [ ] #<Issue-ID>
- [ ] #<Issue-ID>

---

## Status Overview
| Issue | Status | Ledger | Notes |
|------|--------|--------|------|
| #<id> | TBD | TBD | … |

---

## Governance
- Ledger-Pflicht: **JA** (bei Statuswechseln der Child-Issues)
- Milestone/Cluster: <z. B. post-soak-implementation>

---

## Closure / Bookkeeping
- Das Meta-Issue bleibt offen, bis die relevanten Child-Issues erfolgreich gemerged und danach geschlossen sind.
- Child-Issues, die nur lokal fertig oder review-ready sind, zaehlen nicht als abgeschlossen.
- `CURRENT_STATUS.md` aktualisieren, wenn sich der sichtbare Repo-/Engineering-Stand aendert.
- `knowledge/CURRENT_STATUS.md` nur dann aktualisieren, wenn der historische Mirror bewusst nachgezogen wird.
- Einen append-only Ledger-Eintrag unter `knowledge/agent_trust/ledger/` anhaengen, wenn sich Status oder Zuordnung aendert.
- `docs/runbooks/CONTROL_REGISTER.md` nur dann aktualisieren, wenn das Cluster Control-Board-Stage, Operating Focus oder Control-Surfaces betrifft.

---

## Decisions
- …

---

## Definition of Done
- Alle Child-Issues erfolgreich gemerged und geschlossen
- Ledger vollständig, konsistent und append-only gepflegt
- `CURRENT_STATUS.md` synchronisiert
- `knowledge/CURRENT_STATUS.md` synchronisiert, falls der Mirror betroffen ist
- Meta-Issue erst nach erfolgreichem Merge-Stand geschlossen

---

## Meta
- **Owner:** <Name>
- **Agent:** codex / claude
