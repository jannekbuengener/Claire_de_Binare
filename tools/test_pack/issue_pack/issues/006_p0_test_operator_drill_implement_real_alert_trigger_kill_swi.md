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
