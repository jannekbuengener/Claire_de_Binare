# Codex Prompt — Create GitHub Issue Pack (CDB: Live-Trading Readiness)

Context
- Work **local → remote**.
- Repo: `jannekbuengener/Claire_de_Binare`
- Target: Create a prioritized Issue Pack (P0/P1/P2) based on the agreed readiness plan.
- IMPORTANT: Use existing local artifacts whenever available. Do not “reinvent” branch protection.

New input (Branch Protection assets)
- Branch protection saved files are located at:
  `D:\Dev\Workspaces\Worktrees\branch-protection files`
- During execution, you MUST:
  1) Read those files first
  2) Re-apply branch protection using **Playwright via MCP** (web UI automation) rather than manual clicking
  3) Reference the folder path in the issue(s) as the source of truth for settings

General rules
- Do NOT edit canonical governance docs unless explicitly requested.
- Each issue must include: Title, Labels, Scope, Description, Acceptance Criteria, Dependencies/Links.
- If an issue is blocked by unknown details, still create it with explicit “Open Questions” and a proposed default.
- Prefer “enforceable” mechanisms: CI gates, required checks, branch rules, audit-friendly artifacts.

Labels (use consistently)
- Priority: `prio:p0`, `prio:p1`, `prio:p2`
- Type: `type:infra`, `type:obs`, `type:gov`, `type:test`, `type:safety`, `type:sim`
- Scope: `scope:ci`, `scope:repo`, `scope:metrics`, `scope:drills`, `scope:security`

Create the following issues (in this order)

---

## ISSUE 1 — [P0][OBS] Metrics Overhaul: fix Prometheus targets + “No Data” dashboards + main panel restore
Labels: prio:p0, type:obs, scope:metrics
Scope:
- Prometheus scrape targets
- Grafana datasource
- Dashboard queries/variables
Description:
- Panels showing “No Data” and the broken main panel must be fixed. This is a prerequisite for chaos assertions and kill-switch verification.
Acceptance Criteria:
- Prometheus targets: all core services `UP=1` (stable, no flapping)
- Main dashboard loads without errors
- 0 broken panels; “No Data” either fixed or explicitly marked as “expected empty” with explanation
- Golden Signals section exists: throughput, error rate, latency, backlog/queue, orders/fills, risk blocks, kill-switch state
- Add a 5-step “No Data” troubleshooting checklist to docs
Links/Refs:
- Add links to the dashboards/panels in the issue once identified

---

## ISSUE 2 — [P0][SAFETY] Kill-Switch “One Button”: trigger + live status + verifiable stop of order flow
Labels: prio:p0, type:safety, scope:drills
Scope:
- Implement/standardize a single action to HALT
- Surface clear state: SAFE/HALT/FAILSAFE
Description:
- Kill-switch must be usable under stress: one action + immediate effect + clear verification.
Acceptance Criteria:
- One action (CLI/UI/shortcut) toggles SAFE↔HALT
- In HALT: no new orders are sent; any open orders canceled/frozen per design
- Status is visible (endpoint/metric) and auditable (who/when)
- Verification procedure exists and is automated where possible (metric or state endpoint)
Dependencies:
- Depends on Issue 1 for reliable metrics

---

## ISSUE 3 — [P0][GOV][ENFORCEMENT] Re-apply Branch Protection from saved files using Playwright (MCP)
Labels: prio:p0, type:gov, scope:repo, scope:security
Scope:
- Restore branch protection rules for `main`
- Required checks and review requirements
Description:
- Branch protection must be restored from the previously saved configuration.
- Use Playwright via MCP to apply settings through GitHub UI (automation), referencing local saved files.
Implementation Notes:
- Source of truth folder: `D:\Dev\Workspaces\Worktrees\branch-protection files`
- Codex must inspect this folder and translate it into exact GitHub settings
Acceptance Criteria:
- Branch protection for `main` active and matches saved config
- Direct pushes blocked; PR required
- Required checks set and enforced
- Admin bypass disabled or explicitly controlled (document choice)
- A proof artifact is produced: screenshot(s) or exported settings summary in an evidence folder
Dependencies:
- None (but coordinate with CI checks from Issue 4)

---

## ISSUE 4 — [P0][CI] Required Checks: “Green or Stop” (CI gates stabilized)
Labels: prio:p0, type:infra, scope:ci
Scope:
- Define the minimal set of required workflows
- Ensure failures are actionable
Description:
- CI must be a real gate. “Green” must mean safe to merge.
Acceptance Criteria:
- Required checks list documented (name → purpose)
- 3 consecutive green runs on `main` without manual reruns
- Failure logs are readable and point to the root cause
Dependencies:
- Works together with Issue 3 (required checks are referenced by branch protection)

---

## ISSUE 5 — [P0][TEST] Wire Test Pack v2: ingestion hook + metrics snapshot + assertions evaluator
Labels: prio:p0, type:test, scope:drills
Scope:
- Take the Test Pack v2 skeleton and make it runnable end-to-end
Description:
- The harness currently has TODO hooks for ingestion + metrics/assertions. Implement them so the chaos drill produces PASS/FAIL automatically.
Acceptance Criteria:
- One supported ingestion path is implemented end-to-end (choose one; document):
  - HTTP ingest endpoint OR message bus publish OR file adapter replay
- Drill produces artifacts:
  - metrics_snapshot.json
  - assertions_result.json (overall_pass, per-assertion evidence links)
- Evidence pack structure produced per template (README + sources manifest + logs + reports)
Dependencies:
- Depends on Issue 1 (metrics snapshot source)
Links/Refs:
- Reference `cdb_test_pack_v2.zip` integration path in repo (if already imported)

---

## ISSUE 6 — [P0][TEST] Operator Drill: implement real alert trigger + kill-switch verification + timeline evidence
Labels: prio:p0, type:test, type:safety, scope:drills
Scope:
- Turn the operator drill skeleton into a real drill
Description:
- Implement a real alert trigger (webhook/email/alertmanager) and a verifiable kill-switch check.
Acceptance Criteria:
- Trigger produces a captured payload/message inside evidence pack
- Verification uses one canonical source (metric/state endpoint/log marker) and is automated
- timeline.json produced with key stamps
Dependencies:
- Depends on Issue 2 (kill-switch state + verification method)
- Depends on Issue 1 if verification uses metrics

---

## ISSUE 7 — [P1][CI] Jules AI Reviewer: PR comment PASS/FAIL + findings (no merge rights)
Labels: prio:p1, type:infra, scope:ci
Scope:
- Automated PR review comment
Description:
- Jules runs on PR events and posts/updates a structured comment with verdict PASS/FAIL + risk flags.
Acceptance Criteria:
- Runs on PR open/sync
- Posts exactly one updatable “Jules Review” comment (no spam)
- Contains: verdict, key findings, suggested checks for human signer
- No write access beyond commenting
Dependencies:
- None

---

## ISSUE 8 — [P1][GOV] Enforce “Six-Eyes”: Human Signoff only after Jules PASS
Labels: prio:p1, type:gov, scope:repo
Scope:
- Process + gating rule
Description:
- Human signer (second account) merges only when Jules verdict is PASS.
Acceptance Criteria:
- PR template fields: Builder, Jules Review link, Human Signer
- Clear policy documented: Jules FAIL => no merge
- Dry-run PR proves the flow
Dependencies:
- Depends on Issue 7
- Pairs with Issue 3 (branch protection reviews)

---

## ISSUE 9 — [P2][SIM] Mock Exchange / Execution Simulator (market-like feedback without real market)
Labels: prio:p2, type:sim
Scope:
- Local service or module that mimics exchange API semantics
Description:
- Accept orders; simulate fills/rejects/partial fills/latency/rate limits; deterministic seed mode.
Acceptance Criteria:
- Scenarios: full fill, partial fill, reject, timeout, rate limit, delayed fill
- Deterministic mode (seed) + chaos mode
- Produces order_result events compatible with execution/risk pipeline
Dependencies:
- Enables stronger chaos drills later

---

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
