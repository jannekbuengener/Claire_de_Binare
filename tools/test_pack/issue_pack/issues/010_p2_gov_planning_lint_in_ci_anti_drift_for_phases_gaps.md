## ISSUE 10 — [P2][GOV] Planning Lint in CI (anti-drift for phases/gaps)
Labels: prio:p2, type:gov, type:infra, scope:ci
Scope:
- Run `planning_lint.py` on chosen planning docs folders
Description:
- Keep planning docs consistent and enforce phase/gap conventions (optional strictness).
Acceptance Criteria:
- CI job runs on PR
- Outputs JSON report artifact
- Fails PR on phase inconsistency (and optionally gap violations)
Dependencies:
- None

---

Execution instructions for Codex (how to create issues)
1) Use GitHub Issues API or CLI (gh) to create issues in `jannekbuengener/Claire_de_Binare`.
2) Apply labels exactly as listed above.
3) For each issue, include “Links/Refs” with placeholders if missing and add a checklist for artifacts/evidence.
4) After creating all issues, post a final summary comment in the last issue:
   - Issue numbers + titles
   - Dependency graph (P0 first)
   - Immediate next action recommendation: start with Issue 1 (metrics) and Issue 3 (branch protection restore)

Output required
- List of created issue URLs
- Any labels that had to be created
- Notes on anything blocked (and the proposed default)
