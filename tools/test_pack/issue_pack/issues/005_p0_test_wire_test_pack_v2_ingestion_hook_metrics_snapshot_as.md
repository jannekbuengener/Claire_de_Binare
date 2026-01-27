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
