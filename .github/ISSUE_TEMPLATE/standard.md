---
name: Standard Issue (Governance)
about: Einheitliches Issue-Template mit Analyse, Ledger-Gate und Implementierungslogik
title: "[PAINPOINT|TASK] <kurze, präzise Beschreibung>"
labels: []
assignees: []
---

## Context
- **Quelle (Repo):** `CURRENT_STATUS.md`, `docs/templates/README_TEMPLATE_PACK.md`
- **Beschreibung:**  
  Kurz und präzise: Was ist das Problem / Ziel?
- **Warum relevant:**  
  Blocker, Enablement oder Governance – klar benennen.

---

## Scope
**In Scope**
- …

**Out of Scope**
- …

---

## Relations
- **Relates to:** #<Meta-Issue-ID(s)>
- **Dependencies:** #<Issue-ID(s)> (falls vorhanden)
- **Milestone/Cluster:** <z. B. post-soak-implementation>

---

## Closure / Bookkeeping
- Das Issue bleibt offen, bis die erforderlichen Aenderungen erfolgreich in den Ziel-Branch gemerged sind.
- Draft-PRs, lokale Fertigstellung oder Review-Ready-PRs zaehlen nicht als abgeschlossen.
- `CURRENT_STATUS.md` aktualisieren.
- `knowledge/CURRENT_STATUS.md` aktualisieren, wenn die Knowledge-Mirror- oder Snapshot-Lage nachgezogen werden muss.
- Einen append-only Ledger-Eintrag unter `knowledge/agent_trust/ledger/` anhaengen.
- `docs/runbooks/CONTROL_REGISTER.md` nur dann aktualisieren, wenn das Issue Control-Board-Stage, Operating Focus oder dort getrackte Control-Surfaces aendert.

---

## Analysis (Agent – comment-only)
> Wird durch den zuständigen Agenten als **Kommentar** ergänzt.

**Pflichtinhalt im Kommentar:**
- Problem Statement
- Proposed Approach (2–3 Punkte)
- Acceptance Criteria (2–3 Punkte)
- Risiken / Abhängigkeiten

**Decision Line (verpflichtend):**  
`Status: READY FOR IMPLEMENTATION`  
**oder**  
`Status: BLOCKED — <klarer Grund>`

---

## Governance Steps (verpflichtend)
1. Analyse-Kommentar durch Agent
2. **Append-only Ledger-Eintrag**, sobald Status = `READY_FOR_IMPLEMENTATION`
   - Pfad: `knowledge/agent_trust/ledger/`
   - Datei: `<timestamp>__issue_status__<agent>.yaml`
3. Priorisierung festlegen (P0 / P1 / P2)
4. Milestone zuweisen
5. Optional: Draft-PR(s) zur Vorbereitung

---

## Implementation (nach READY)
- Umsetzung **ausschließlich über PRs**
- Jeder PR referenziert dieses Issue
- Abhängigkeiten & Reihenfolge beachten

---

## Definition of Done
- Alle Acceptance Criteria erfüllt
- Relevante PR(s) erfolgreich gemerged
- Issue erst nach erfolgreichem Merge geschlossen
- `CURRENT_STATUS.md` synchronisiert
- `knowledge/CURRENT_STATUS.md` synchronisiert, falls der Mirror betroffen ist
- Ledger konsistent, vollständig und append-only gepflegt
- `docs/runbooks/CONTROL_REGISTER.md` nur aktualisiert, wenn Control-Kontext betroffen ist

---

## Meta
- **Agent:** codex / claude / gemini / opencode
- **Labels:** `painpoint`, `agent:<x>`, `phase:<analysis|implementation|governance>`
- **Owner:** <Name>
