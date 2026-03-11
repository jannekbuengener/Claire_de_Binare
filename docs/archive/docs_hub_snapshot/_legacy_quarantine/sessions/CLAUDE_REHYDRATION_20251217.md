CLAUDE PROMPT — CONTEXT REHYDRATION + EXECUTION (DETERMINISTIC)

MISSION
Re-enter the project “Claire de Binare (CDB)” after absence, sync to current reality, and immediately execute the next highest-leverage work without drifting. No philosophy, no alternatives, no refactors.

CURRENT STATUS (SOURCE OF TRUTH)
- Date: 2025-12-17 21:37 CET
- Repo: C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare
- HEAD: ae5891d ("test hook") — stale-commit issue fixed, timeline is consistent now
- Branch: main (synced with gitlab/main)
- Working tree: clean (docs submodule modified is normal)
- Safety branches exist: safety/before-fix-20251217, safety/after-gemini-commit
- Root baseline enforcement + tool runner is operational:
  - `python scripts/run_docs_sync.py --dry-run ...` returns “Root baseline verified: True”
  - Tools runner OK (30 tools)

REMOTE SNAPSHOT
- GitHub: 3 open PRs, ~35 active issues
- GitLab: upstream for CI/CD, synchronized

HOT PRS (PRIORITY ORDER)
1) PR #125 Agent Config Fix (Copilot, draft) — MCP config for Codex/Claude, CI/CD support + docs
2) PR #126 Claude GitHub Actions (today)
3) PR #127 Claude Code GitHub Workflow (today) — @claude mention support
4) PR #87 Dependabot updates (requests + cryptography security bump)

TOP ISSUES (PRIORITY ORDER)
1) Issue #128 — “BSDE vs. Stochastic Control Framework Selection”
   - Thread: THREAD_1765959387
   - Status: APPROVED
   - Decision: Hybrid HJB baseline + selective BSDE track
   - Next step: Dimensionality audit (Week 1–2)
2) Issue #123 — Paper Trading Ops Setup (M7 MUST)
   - Defaults: paper mode in .env.example
   - Runbook target: docs/runbook_papertrading.md
   - Validation: make docker-up + health checks
3) Issue #122 — Docker Hardening Report (M8 MUST)
   - Report-only, no runtime changes
   - Audit all Dockerfiles/compose files, categorize MUST/SHOULD/NICE

ARCHITECTURE SNAPSHOT
- services/: execution, risk, signal, market, psm, db_writer
- infrastructure/: compose fragments, database, k8s, monitoring, scripts
- Agents:
  - Claude: Session Lead (CLAUDE.md)
  - Codex: Execution Agent (CODEX.md)
  - Copilot: GitHub Manager (COPILOT.md)
  - Gemini: Audit & Review (GEMINI.md)

HARD RULES
- Do not touch secrets in this session unless explicitly tasked by a security issue.
- Do not refactor or rename modules.
- Do not invent new phases. Operate on existing PRs/issues only.
- Every change must be commit-scoped and test/validate minimally.
- After any code change, run:
  python scripts/run_docs_sync.py --dry-run --relocator-report tools/_relocator_report.json --tools-report tools/_tools_report.json
  (must remain Root baseline verified: True)

HANDSHAKE (HOW WE WORK)
- You execute; I only approve/deny merges and provide missing inputs.
- If you hit ambiguity, choose the safest assumption and continue; only stop on hard blockers.

TASKS FOR THIS SESSION (DO IN THIS ORDER)

STEP 0 — REHYDRATE FAST (READ ONLY)
Read these files in order (no summaries longer than 10 lines each):
- README.md
- CLAUDE.md
- CODEX.md
- COPILOT.md
- GEMINI.md
- DISCUSSION_PIPELINE_COMPLETE.md
- services/ (tree overview)
- infrastructure/compose/ (tree overview)

STEP 1 — PR TRIAGE (DECISION PACK)
Produce a PR decision pack (max 30 lines total):
- For PR #125/#126/#127: which one should be merged first and why (1–2 bullets each)
- Identify conflicts/overlap between #126 and #127; recommend ONE canonical approach.

STEP 2 — EXECUTE THE FASTEST HIGH-IMPACT MERGE PATH
Based on Step 1:
- Prepare the selected PR for merge (fix small issues, docs alignment, workflow triggers)
- Keep scope minimal; commit with clear message.

STEP 3 — ISSUE #128 KICKOFF (NO RESEARCH, ONLY FIRST ACTION)
Implement “Week 1–2 Dimensionality Audit” as a concrete deliverable:
- Create a single audit checklist doc + a skeleton script or notebook entrypoint (if appropriate) that measures dimensionality drivers relevant to our system.
- Output must be actionable and ready for a follow-up issue breakdown.

STEP 4 — STOP CONDITION
Stop after Step 3 and report:
- What was merged/prepared
- What was created for #128
- Any blockers requiring a single yes/no decision from me

OUTPUT FORMAT
- Section headers: REHYDRATION / PR DECISION PACK / EXECUTION LOG / ISSUE #128 DELIVERABLE / BLOCKERS
- No fluff. No extra recommendations.

BEGIN NOW.
---