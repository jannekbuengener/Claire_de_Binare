# 2026-02-21 Backlog Cleanup Postmortem

## Context
- Ausgangslage: 30 offene PRs (stale/drafts/duplicates/major deps/runtime mixes)
- Ziel: Repo wieder "mergebar" machen, ohne Scope-Drift

## Actions Taken
- Cleanup: 30 → 0 offene PRs
- Strategie: docs-only zuerst, risk nach hinten, grosse Features splitten (z.B. #764 → #896)
- Solo-Maintainer Merge: admin-merge genutzt, weil Review-Requirement irrelevant

## Key Decisions
- Split statt Feature-Bloat: #764 gesplittet, nur claude-check noop-pass gemerged (#896)
- Konflikt-PRs geschlossen statt "impro-merge" (klarer Grund im Close-Comment)
- Dependabot majors nur nach CI/Smoke (keine Bauchentscheidung)

## Health Check Evidence
- pytest (ohne MCP runtime): 386 passed, 0 failed, 51 skipped
- black 26 / pytest 9 / redis 7 / group bump: OK
- Pre-existing: test_mcp_runtime fails lokal (MCP Time Server fehlt) → keine Regression
- Dependabot ruff recreate: getriggert fuer #845

## Lessons Learned
- Review-required Branch Protection ist Solo-maintainer-friction → bypass oder disable sinnvoll
- Workflow-Changes sind "Feature", nicht "Fix" → immer splitten
- Grosse Bundles (group bumps) nur mit CI + smoke → dann ok

## Follow-ups
- Ruff dependabot (#845) abwarten (recreate) und dann normal review/merge
- Optional: Branch protection so einstellen, dass Solo-Maintainer ohne Review mergen kann
