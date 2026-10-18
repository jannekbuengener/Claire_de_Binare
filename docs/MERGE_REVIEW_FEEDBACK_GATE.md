# Universal Merge Policy - Review Feedback Gate

**Status:** ACTIVE_CANON
**Issue:** `#4602`
**Purpose:** Mandatory pre-merge process gate on the final PR head. Complements the live `main-strict` ruleset and required checks; it does not replace them.

## Rule

A PR must **not** be merged while relevant review feedback is unread, unanswered, or unresolved. An untreated technical comment is a merge blocker.

Before merge, recheck on the **final head SHA**:

- PR conversation / top-level comments
- Inline review comments and threads
- Submitted reviews
- Bot / automated reviews
- New comments since the last fix/review round

Every relevant point needs an explicit disposition: `FIXED`, `ANSWERED` / `EXPLAINED`, `NOT_APPLICABLE`, or `DUPLICATE`. Reviewer feedback is evidence to verify, not automatic truth.

## Inline threads

Before merge every inline thread must be read, technically assessed, fixed or answered as needed, and resolved.

**No open review threads at merge.**

## Final merge gate

Merge only when all are true on the final head:

1. ALL REVIEW FEEDBACK SEEN
2. ALL FEEDBACK DISPOSITIONED
3. ALL INLINE THREADS RESOLVED
4. NO NEW UNREVIEWED COMMENTS
5. Required ruleset checks are green on the exact final head
6. No blocking `CHANGES_REQUESTED` review remains
7. PR is mergeable under the live `main-strict` ruleset

A separate GitHub `APPROVE` review is **not** required by the merge contract when the live ruleset has `required_approving_review_count = 0`. The process gate requires technical review disposition, not an approval-provider token. If the live ruleset later requires approvals, the merge path must fail closed and require that live review evidence.

Before merge, report:

```text
REVIEW COMMENTS:
  total=<n>
  fixed=<n>
  answered_or_na=<n>
  unreviewed=0
  unresolved_threads=0
```

If the final head changes, restart this gate and recheck required checks. GitHub live state wins over cached evidence.
