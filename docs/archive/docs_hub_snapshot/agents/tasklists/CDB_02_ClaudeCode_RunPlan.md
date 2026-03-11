# CDB Office Pack — Claude Code Run-Plan (Copy/Paste)
Stand: 2025-12-16

> Zweck: 1:1 in Claude Code einfügen, damit Claude als Session Lead sauber orchestriert.

## Inputs
- WORKING_REPO = `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare`
- DOCS_HUB_REPO = **per Suche** (siehe Phase 0) — nicht raten.

## Operating Rules (kurz)
- Repo-Split strikt einhalten: Docs Hub = Canon/Knowledge/Reports; Working Repo = Execution Code/Compose/Runtime.
- Hardening: REPORT zuerst, DIFF danach (separate Phase).
- Keine Secrets, kein Live-Trading aktivieren.
- Nach jeder Phase: Status + geänderte Dateien + Next Step.

---

## Prompt für Claude Code

```text
ROLE: Claude (Session Lead) — Office Execution Pack

HARD RULES:
- Respect repo split (Docs Hub vs Working Repo). No Canon duplication into Working Repo.
- Hardening must be REPORT first; DIFF only after explicit go.
- No secrets. No live trading activation.

INPUTS:
- WORKING_REPO = C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare
- DOCS_HUB_REPO = <resolve by searching for DOCS_HUB_INDEX.md under C:\Users\janne\Documents\GitHub\Workspaces>

PHASE 0 — RESOLVE DOCS HUB PATH + BASELINE
1) Find DOCS_HUB_REPO by locating DOCS_HUB_INDEX.md
2) For BOTH repos: git status, branch, last commit, list untracked
ACCEPTANCE:
- Output absolute DOCS_HUB_REPO path + baseline snapshot for both repos.

PHASE 1 — DOCS HUB: PROMPT MIGRATION (.txt → .md)
Scope: agents/prompts/*.txt, root copilot.txt, gemini.txt
Tasks:
- Migrate 1:1 to .md, add minimal frontmatter + H1 title.
- Mark originals as DEPRECATED with link to new .md.
- Update DOCS_HUB_INDEX references from .txt to .md.
ACCEPTANCE:
- New .md files exist; originals preserved; index updated; no rewriting.
STOP:
- If unclear agent attribution, stop and list files needing decision.

PHASE 2 — DOCS HUB: BUERO FILES SCAN
Tasks:
- Enumerate new Büro files and classify: OK / OK+Hint / Conflict potential.
- Flag potential duplicates (e.g. governance/CONSTITUTION.md vs governance/CDB_CONSTITUTION.md) but do NOT resolve.
Deliverable: BUERO_FILES_REVIEW.md
ACCEPTANCE:
- Report exists; factual; no governance decision-making.

PHASE 3 — DOCS HUB: WEEKLY DIGEST
Tasks:
- Ensure knowledge/logs/weekly_reports/
- Create weekly_report_TEMPLATE.md (max 1 page)
- Create example weekly_report_20251216.md
ACCEPTANCE:
- Template + example exist; no API/token assumptions.

PHASE 4 — WORKING REPO: M7 SKELETON
Tasks:
- Create M7_SKELETON.md with 5–8 clusters
- 3–7 subtasks per cluster; each with acceptance criteria; mark dependencies.
ACCEPTANCE:
- Actionable skeleton, no architecture decisions.

PHASE 5 — WORKING REPO: DOCKER HARDENING REPORT (NO CHANGES)
Tasks:
- Inventory Dockerfiles + compose files
- Check: non-root, pinned bases, minimal deps, no secrets, healthchecks
- Compose: read_only, cap_drop, security_opt, resource limits, network segmentation suggestions
Deliverable: DOCKER_HARDENING_REPORT.md with MUST/SHOULD/NICE + suggested diffs (text blocks)
ACCEPTANCE:
- Report exists; repo unchanged beyond report file.

PHASE 6 — WORKING REPO: PAPERTRADING OPS SETUP (SAFE DEFAULTS)
Tasks:
- Extend .env.example with paper/live flags & execution toggles (safe defaults = paper/dry-run)
- Create knowledge/operating_rules/runbook_papertrading.md with start/stop/health/smoke steps
- Provide validation commands: make docker-up, make docker-health, minimal smoke
ACCEPTANCE:
- Runbook + .env.example update; no live trading activation; no secrets.

OUTPUT AFTER EACH PHASE:
- STATUS: DONE/INPROGRESS/BLOCKED
- CHANGED FILES: list
- NEXT STEP: one line
```
