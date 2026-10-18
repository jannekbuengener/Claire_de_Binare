# Branch Protection

Status: ACTIVE_CANON - live GitHub state wins.
Issue: `#4602`

Claire de Binare protects `refs/heads/main` with the same GitHub enforcement model used by Sample Brain: an active repository ruleset is the merge boundary; classic Branch Protection is not used in parallel.

- Active ruleset: `main-strict` (id `11617228`)
- Classic Branch Protection on `main`: absent
- PR-based delivery required
- `required_approving_review_count = 0`
- `dismiss_stale_reviews_on_push = false`
- `required_review_thread_resolution = false`
- Required linear history
- Deletion and non-fast-forward protection
- Bypass actors empty; `current_user_can_bypass = never`
- Allowed merge methods: squash + rebase
- `strict_required_status_checks_policy = false`

Required status checks (preserve names and integration identities):

- `ci (Unit/Integration + Lint gesammelt)` - GitHub Actions / `integration_id=15368`
- `policy-gate` - GitHub Actions / `integration_id=15368`

The ruleset does **not** require a GitHub approving review. Merge readiness is the conjunction of the live ruleset predicate and [`MERGE_REVIEW_FEEDBACK_GATE.md`](MERGE_REVIEW_FEEDBACK_GATE.md). A same-named Commit Status or Check Run from another integration is not sufficient.

No `--admin` bypass is part of the normal merge path.
