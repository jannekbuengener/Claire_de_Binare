# CDB Office Pack — Acceptance Criteria, Stop-Regeln, Output-Standard
Stand: 2025-12-16

## Output-Standard (für Claude/Copilot)
Nach jeder Phase immer:
1. **STATUS:** DONE / INPROGRESS / BLOCKED  
2. **CHANGED FILES:** Liste (relative Pfade)  
3. **NOTES:** Risiken/Annahmen (max 5 bullets)  
4. **NEXT STEP:** genau 1 Zeile

---

## Stop-Regeln (hart)
- Unklarer Pfad / Repo-Verwechslung → STOP, Pfad ausgeben, nicht raten.
- Agent-Zuordnung bei Prompts unklar → STOP, Liste der betroffenen Dateien.
- Hardening: **keine** mutierenden Änderungen bevor Report abgenommen ist.
- Papertrading: keine Secrets, keine Live-Keys, keine Live-Execution aktivieren.

---

## Phase-wise Acceptance (Kompakt)
### Phase 0
- WORKING_REPO & DOCS_HUB_REPO sind absolut bekannt + Baseline Snapshot vorhanden.

### Phase 1
- `.md` für jede `.txt` existiert, `.txt` deprecated, Index referenziert `.md`.

### Phase 2
- `BUERO_FILES_REVIEW.md` existiert, Klassifikation OK/OK+Hinweis/Konfliktpotenzial.

### Phase 3
- Weekly Template + Beispielreport vorhanden.

### Phase 4
- `M7_SKELETON.md` issue-ready: Cluster, Subtasks, Acceptance, Dependencies.

### Phase 5
- `DOCKER_HARDENING_REPORT.md` vorhanden, mit MUST/SHOULD/NICE + Diff-Snippets; sonst keine Änderungen.

### Phase 6
- `.env.example` erweitert (safe defaults) + `knowledge/operating_rules/runbook_papertrading.md` vorhanden.

---

## Optional: Commit-Message Vorschläge (wenn du liefern willst)
- docs: migrate prompts txt→md
- docs: add buero files review report
- docs: add weekly digest template
- plan(m7): add paper trading skeleton
- sec(docker): add hardening report (no changes)
- ops(paper): add papertrading runbook + env example
