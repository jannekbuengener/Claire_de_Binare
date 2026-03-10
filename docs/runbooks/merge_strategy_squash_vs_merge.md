# Runbook: Merge Strategy for Proof/Slice PRs

## Purpose

Define one default merge method for this repository and keep exceptions explicit.
Scope: proof/slice PRs, evidence PRs, and CI/governance changes.

## Default

- Default merge method: `SQUASH`
- Rationale:
  - Keeps `main` linear and easy to audit.
  - Reduces noisy intermediate commits from slice work.
  - Matches evidence-first workflow (evidence lives in PR/issue links, not commit chains).

CLI default:

```bash
gh pr merge <number> --auto --squash --delete-branch
```

## Decision Rules

| PR shape | Merge method | Why |
|---|---|---|
| Proof/slice implementation (`core/**`, `services/**`, `tests/**`) | `SQUASH` | 1 logical slice -> 1 audit-friendly commit |
| Evidence/docs PR (`docs/**`, reports, runbooks) | `SQUASH` | Keeps narrative changes compact |
| CI/governance PR (`.github/workflows/**`, policy docs) | `SQUASH` | Clear rollback point and linear governance history |
| Explicit evidence-chain PR with independent commits that must stay separate | `MERGE COMMIT` (exception) | Preserve commit-level provenance |
| Rebase merge | Not default | Use only when explicitly requested |

## Exception Policy: Merge Commit

Use `MERGE COMMIT` only when at least one is true:

1. The PR intentionally carries multiple independent commits that are referenced as a required evidence chain.
2. A downstream integration/tool explicitly depends on merge commits.

Required PR body note for exceptions:

- `Merge method exception: merge-commit`
- Short rationale (1-3 lines) + link to evidence/tooling requirement.

Exception CLI:

```bash
gh pr merge <number> --merge --delete-branch
```

## Rebase Guidance

- Rebase merge is opt-in only.
- Do not use by default for proof/slice PRs.
- If used, state in PR body: `Merge method exception: rebase`.

Rebase CLI:

```bash
gh pr merge <number> --rebase --delete-branch
```

## Proof/Slice Conventions

- Rule: `1 PR = 1 Slice = 1 Squash`.
- PR title should encode domain + outcome (for example `lr021: ...`, `security: ...`, `governance: ...`).
- If policy-gate category prefixes are used (`docs-only:`, `workflows-only:`, `infra-only:`), keep them consistent with changed files.
- Put evidence links in PR body and/or linked issue comments.
- Do not rely on commit history as the primary evidence carrier.

## Notes

- Historical governance evidence may contain merge commits from older rulesets.
- Current default for new proof/slice work is `SQUASH` unless an explicit exception is documented.
