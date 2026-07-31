# Session 2026-07-31 — #4061 Dependabot Facts-Normalisierung härten

## Scope

Delivery-Slice für Issue #4061: Report-only Facts-Normalisierung so härten,
dass Phase-0 `FACTS_INVALID`-Fälle (#4046 Range, #4054/#4055 Docker-Compose)
konkrete HOLD-Gründe liefern. Broker bleibt report-only. Kein Merge, kein
Issue-Close, kein Workflow-Dispatch.

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: unavailable
context_tool_status: absent
context_trust_level: none
records_found: none
tools_or_queries:
  - GetMcpTools pattern surreal|context|brain → no matches
  - gh issue view 4061 (Phase-0 Evidence Kommentar)
  - gh api pulls/4046|4054|4055|4162 files+commits
  - python -m tools.pr_routing route --issue 4061
records_or_results:
  - no SurrealDB/MCP context tools in active surface
repo_crosscheck:
  - .github/scripts/dependabot_autopilot_report.py
  - .github/scripts/dependabot_autopilot_classifier.py
  - Issue #4061 Phase-0 Dispatch Run 29236711842
impact_on_plan:
  - Root cause: missing update-type + docker digest regex + multi-file compose
limitations:
  - No DB-backed brain records; live GitHub + repo only
```

## Git / Routing

- Base: `origin/main` @ `e96f724c`
- Branch: `cloud-cursor/dependabot-facts-normalization-e541`
- PR-Router: `CREATE_NEW_BATCH_PR`, lane `ci-tooling`, target would be
  `batch/ci-tooling-issue-4061` (Cloud-Agent-Prefix policy → `cloud-cursor/…-e541`)
- Lock: UNLOCKED

## Delivered

- Docker-Image-Regex akzeptiert `@sha256:` Digests
- Multi-File Docker-Compose-Bumps als eine logische Update-Einheit
- Fehlendes `update-type`/`dependency-type` bei bekannter Identity → Unknown-Sentinel
  (konkreter HOLD), nicht `FACTS_INVALID`
- `date_versioned` aus Versionstext gesetzt
- Anonymisierte Phase-0-Fixtures unter `tests/fixtures/dependabot/`
- Report-only Proof: Live-Queue #4162 → `HOLD` mit `DOCKER_CHANGE`

## Validation

- `pytest` classifier+report: **126 passed**
- `ruff check` PASS
- `black --check` PASS
- `git diff --check` PASS
- `gitleaks protect --staged` PASS (no leaks)
- Live queue report-only: #4162 `DOCKER_CHANGE` (kein FACTS_INVALID)

## Boundaries

- Kein Workflow-Dispatch, keine Dependabot-PR-Mutation
- Kein Full Fast-CI, kein `cdb-local-ci` Publish, kein Merge
- LR bleibt NO-GO
- Forbidden paths unberührt

## Status

`DONE_SLICE_ADDED_TO_BATCH_PR` (nach PR-Handoff)

Refs #4061
