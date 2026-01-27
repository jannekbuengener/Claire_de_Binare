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
