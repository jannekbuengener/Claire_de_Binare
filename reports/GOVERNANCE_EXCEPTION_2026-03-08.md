# Governance Exception: Temporary Review-Count Override

- Date: 2026-03-08
- Author: jannekbuengener (via Claude Code)
- Scope: `required_approving_review_count` on `main` branch protection

## Rationale

Single-maintainer deadlock: PRs #1112 and #1111 were code-ready with all
CI checks green, but `required_approving_review_count=2` blocked merge
because the sole CODEOWNER is also the PR author (self-approval impossible).

## Timeline

| Time (UTC)     | Action                                            |
| -------------- | ------------------------------------------------- |
| ~14:40         | `required_approving_review_count` set from 2 to 0 |
| ~14:41         | PR #1112 merged (squash, branch deleted)          |
| ~14:46         | PR #1111 branch updated with main                 |
| ~14:48         | PR #1111 merged (squash, branch deleted)          |
| ~14:48         | `required_approving_review_count` restored to 2   |

## What changed

- Only `required_approving_review_count`: 2 -> 0 -> 2
- No other branch protection settings were modified
- Admin enforcement remained enabled throughout
- `dismiss_stale_reviews`, `require_code_owner_reviews`, `strict` unchanged

## Verification (post-restore)

```
required_approving_review_count: 2
dismiss_stale_reviews: true
require_code_owner_reviews: true
enforce_admins: true
required_checks: [ci (Unit/Integration + Lint gesammelt), policy-gate]
```

## PRs merged under exception

- #1112: fix(risk): harden decision contract enforcement (LR-762)
- #1111: feat(lr-042): network latency + packet loss chaos drill
