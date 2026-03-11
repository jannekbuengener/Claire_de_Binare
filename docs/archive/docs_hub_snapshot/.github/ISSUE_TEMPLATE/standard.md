---
name: Standard Issue (Governance)
about: Einheitliches Issue-Template mit Analyse, Ledger-Gate und Implementierungslogik
title: "[PAINPOINT|TASK] <kurze, präzise Beschreibung>"
labels: []
assignees: []
---

## Context
- **Quelle (lokal):** `D:\Dev\Workspaces\Prompts\PAINPOINTS`
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
2. **Ledger-Eintrag**, sobald Status = `READY_FOR_IMPLEMENTATION`  
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
- Relevante PR(s) gemerged
- Issue geschlossen
- Ledger konsistent & vollständig

---

## Meta
- **Agent:** codex / claude / gemini / opencode
- **Labels:** `painpoint`, `agent:<x>`, `phase:<analysis|implementation|governance>`
- **Owner:** <Name>
