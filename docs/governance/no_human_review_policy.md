# No Human Review Policy

**Status**: Active
**Scope**: All PRs to `main` in `Claire_de_Binare`
**Effective**: 2026-02-23
**Owner**: jannekbuengener (repo owner)

## Context

This is a solo-maintainer repo with AI-assisted development (Claude, Copilot).
Human review gates create a bottleneck with zero security benefit:
GitHub blocks self-approval, and there is no second human reviewer.

The repo already operates this way de facto since 2026-02-15
(see [BRANCH_PROTECTION_LOG.md](BRANCH_PROTECTION_LOG.md) — PR #839, PR #846).
This document makes the practice explicit and auditable.

## Decision

**No human reviews required. Merge gate = required CI checks green.**

A PR may merge when:
1. All required status checks pass (currently: `ci (Unit/Integration + Lint gesammelt)`)
2. All conversation threads are resolved (`required_conversation_resolution: true`)
3. A self-review comment is present (see template below)

No approval from any GitHub user or bot is required.

## Scope and Exceptions

This policy applies to **all PRs** with two explicit exception categories:

| Exception | Trigger | Required action |
|-----------|---------|-----------------|
| System invariant changes | Edits to `SYSTEM_INVARIANTS.md` or enforcement mechanisms | Documented justification + link to DocsHub change |
| Live trading enablement | Changes to `soak_mode`, `paper_mode`, or live exchange credentials | Explicit operator sign-off in PR comment |

Exception PRs follow the same CI gate but **must** include a `## Risk Assessment`
section with rollback steps. No additional human approval is required —
the documentation itself is the control.

## Definition of Done for PRs

- [ ] Required CI checks green
- [ ] Self-review comment posted (see template)
- [ ] Scope statement: what changed, what was NOT changed
- [ ] For infra/security/schema PRs: rollback plan or revert command documented
- [ ] For new features: feature flag (default OFF) or evidence of no runtime impact
- [ ] No secrets in diff (`gitleaks` check passes)

## Self-Review Template

PR authors post this as a comment before merge:

```markdown
## Self-Review

**Scope**: [1-2 sentences: what this PR changes]
**Not touched**: [what was explicitly left unchanged]
**Risk**: [none / low / medium] — [1 sentence justification]
**Tests**: [test command + result summary]
**Rollback**: [revert command or "git revert <sha>" or "feature flag OFF"]
**Evidence**: [link to CI run or paste of test output]
```

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Bad code merges without review | Required CI checks (unit, integration, lint, contract tests, gitleaks) |
| Schema/infra breakage | Runbooks required for infra PRs; enforcement scripts are opt-in operator steps |
| Silent behavioral regression | Decision contract tests (`tests/contract/`), deterministic gate in conftest.py |
| Accidental secret exposure | `gitleaks` workflow as required check |
| Force-push / branch deletion | `enforce_admins: true`, `allow_force_pushes: false`, `allow_deletions: false` |
| Flakey/pre-existing test failures | See "Quarantined Tests" below |

## Quarantined Tests

Tests that fail due to missing dependencies or external services (not code bugs)
are documented here. They do not block merge.

| Test | Reason | Tracked in |
|------|--------|-----------|
| `tests/smoke/test_mcp_runtime.py` | Requires `pytest-twisted` (not in CI deps) | Pre-existing |
| `tests/integration/test_execution_pipeline.py` | Requires `flask` (service dep, not in test env) | Pre-existing |
| `tests/integration/test_mexc_testnet.py` | Requires `requests_mock` | Pre-existing |
| `tests/unit/candles/test_regime_lookup.py` | Requires `flask` | Pre-existing |
| `tests/unit/execution/test_service*.py` | Requires `flask` | Pre-existing |
| `tests/unit/signal/test_service.py` | Requires `flask` | Pre-existing |

When a quarantined test is fixed, remove it from this table and add it
to the required CI check suite.

## Branch Protection Settings (current state)

| Setting | Value | Purpose |
|---------|-------|---------|
| `required_status_checks` | `ci (Unit/Integration + Lint gesammelt)` | CI is the gatekeeper |
| `required_status_checks.strict` | `true` | Branch must be up-to-date |
| `required_approving_review_count` | `0` | No human approval needed |
| `enforce_admins` | `true` | Admins also bound by checks |
| `required_conversation_resolution` | `true` | All threads must be resolved |
| `allow_force_pushes` | `false` | No force-push to main |
| `allow_deletions` | `false` | Cannot delete main |

## References

- [BRANCH_PROTECTION_LOG.md](BRANCH_PROTECTION_LOG.md) — historical decisions
- [GOVERNANCE_AUDIT_RUNBOOK.md](GOVERNANCE_AUDIT_RUNBOOK.md)
- [docs/ci/ACTION_REQUIRED_RUNBOOK.md](../ci/ACTION_REQUIRED_RUNBOOK.md) — bot PR approval flow
