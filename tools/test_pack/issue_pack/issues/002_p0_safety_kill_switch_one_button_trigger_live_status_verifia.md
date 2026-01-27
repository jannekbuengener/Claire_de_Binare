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
