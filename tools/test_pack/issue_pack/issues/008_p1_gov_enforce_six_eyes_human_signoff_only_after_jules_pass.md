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
