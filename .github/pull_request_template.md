# Pull Request

## Summary
<!-- What changed, in 3-6 lines -->

## Why
<!-- Problem or goal this PR addresses -->

## Validation
<!-- Commands, checks, or evidence -->

## Risk / Rollback
<!-- Risks and how to revert -->

## Checklist
- [ ] Scope is focused
- [ ] Validation evidence included
- [ ] Docs updated (if needed)
- [ ] Breaking changes documented (if any)

## `.github` Control Plane *(skip if this PR does not touch `.github/`)*
- [ ] **Change class:** `doc-only` / `behavior-neutral` / `behavior-change` / `new-surface` / `removal` / `governance-only`
- [ ] **Sync duties** checked per [seal policy](../docs/governance/GITHUB_CONTROL_PLANE_SEAL.md) § 3
- [ ] **Side effects** — any new or changed automation outputs declared in Summary/Validation above

## Merge / Closure Guardrails
- [ ] No auto-merge used (`gh pr merge --auto` is forbidden in this repo)
- [ ] Final human review completed before merge
- [ ] `Closes #...` used only when acceptance is satisfied against merged `main` (`merge_state != completion_state`)

## Breaking Changes
None / list
