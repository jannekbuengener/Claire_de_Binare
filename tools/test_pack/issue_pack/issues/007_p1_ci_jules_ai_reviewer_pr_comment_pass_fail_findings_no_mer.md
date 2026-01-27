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
