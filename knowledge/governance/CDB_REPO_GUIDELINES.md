---
relations:
  role: doc
  domain: governance
  upstream:
    - knowledge/governance/CDB_REPO_STRUCTURE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
  downstream: []
  status: canonical
  tags: [repository, guidelines, working_repo, consolidated]
---
# CDB_REPO_GUIDELINES

Working-repo guidelines for the consolidated repository.

## 1. Structure

- `core/` shared domain models and deterministic utilities
- `services/` runnable service implementations
- `infrastructure/` compose, monitoring, database, and runtime automation
- `tests/` unit, integration, replay, smoke, and e2e coverage
- `agents/` local agent registry and role docs
- `knowledge/` active knowledge, governance-adjacent docs, and evidence
- `docs/` navigation, templates, runbooks, and archives
- `.github/` community files and GitHub automation

## 2. Working Rule

This repository is no longer execution-only. It is the active runtime repo and
the active documentation canon. Changes should therefore keep code, governance,
and supporting docs coherent in one reviewable place.

## 3. Build And Test Commands

- `pytest -q`
- targeted `pytest` runs for touched areas
- service- or stack-specific commands documented in local runbooks
- `pwsh -File tools/enforce-root-baseline.ps1 -DryRun` for navigation drift

## 4. Style And Determinism

- prefer deterministic helpers and explicit config
- avoid hidden timestamps, randomness, or environment coupling
- keep secret handling outside git-tracked files
- document behavior changes in the local canon when they alter operations

## 5. Pull Requests

Each PR should make the code path, docs path, and verification story line up:

- what changed
- how it was verified
- what risks remain
- which local canon docs were updated, if behavior changed

## 6. Open Marker Lifecycle

This rule applies to active working-repo paths such as `core/`, `services/`,
`infrastructure/`, `scripts/`, `tests/`, `knowledge/`, `docs/`, `.github/`, and
`agents/`. Archive and snapshot trees such as `knowledge/archive/**` and
`docs/archive/**` are evidence-only and are not the default cleanup target.

### Allowed marker classes in active paths

- `TODO(#<issue>): ...`
  - deferred code, test, script, or doc work with an explicit tracking issue
- `PLACEHOLDER(#<issue>): ...`
  - non-final dashboards, runbooks, or docs that must state what is missing
- explicit checklists (`- [ ] ...`)
  - allowed in operational docs when the document is clearly a checklist or
    readiness gate, not finished guidance
- domain terms such as `stub`
  - allowed when they describe a real test fixture, protocol mode, or fallback,
    not an untracked implementation gap

### Forbidden marker states in active paths

- unreferenced `TODO`, `FIXME`, `XXX`, `TBD`, or `Issue #TBD`
- placeholders that look implemented or operationally ready without naming the
  missing evidence, metric, or implementation gap
- skipped or placeholder tests without an explicit tracking issue in the skip
  reason or nearby note

### Path-specific hard rules

- active code, scripts, and tools must not carry untracked open-work markers;
  use `TODO(#<issue>): ...` or remove the marker
- placeholder tests are only allowed when they are explicitly non-executing
  (`skip`, `skipif`, or equivalent) and tied to a real issue
- runbooks and operating docs may keep open checklist items, but those items
  must stay in clearly open checklist/readiness sections and must not be used to
  imply that the procedure is already complete
- dashboards and monitoring assets may expose missing KPI/instrumentation gaps
  only when the panel or dashboard text makes the placeholder state explicit and
  links it to a tracking issue

### Review expectation

- when touching a file with an active open-work marker, either normalize it to
  the allowed form, remove it, or carry the mismatch into the review/issue
  record explicitly
- markers without a live issue reference are stale by default and should be
  treated as cleanup or backlog-clarification work before merge
