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
