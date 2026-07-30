# Example: First Issue To PR Flow

Status: Orientation
Issue: #3238

This example shows a conservative CDB docs-slice delivery path. Adjust paths,
issue numbers, validation, and closure wording to the actual task.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## 1. Read The Issue And Canon First

Start with the issue, but do not trust issue prose alone.

Required shape:

1. Resolve the bootloader: `AGENTS.md` -> `agents/AGENTS.md` -> full Read Order.
2. Read `CDB_AGENT_POLICY.md` section 4 before write-zone work.
3. Read `docs/runbooks/CONTROL_REGISTER.md`, `CURRENT_STATUS.md`, and
   `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` as separate status
   surfaces.
4. Pull GitHub live state for the target issue, related issues, and open PRs.

Governance reminders:

- GitHub live comes before ledger state.
- `CURRENT_STATUS.md` is a ledger, not live truth.
- Board stage `trade-capable` is not Live-Go.
- LR bleibt NO-GO.

## 2. Verify The Clean Start Surface

Example command shape:

```bash
git fetch origin --prune
git status -sb
git rev-parse HEAD
git rev-parse origin/main
git branch --show-current
gh issue view <issue> --json number,title,state,labels,body,comments
gh pr list --state open --limit 20
```

Stop if the repo is not on `main`, local `main` differs from `origin/main`, the
issue is closed, a matching open PR already exists, or scope drifts into GUI,
runtime, Docker, trading, live, DB write, memory write, or LR changes.

## 3. Branch, Change, And PR Lock

Before writing, check the target issue and open PRs for an active writer. If a
matching open PR already exists, inspect its comments first and stop if another
agent owns the `LOCK:`.

If no matching PR exists, create the branch from current `main` and make the
smallest local change:

```bash
git switch -c docs/<short-scope>-<issue>
```

After pushing and creating the PR, post the exact single-writer lock as the
first PR comment before any further push, PR update, or follow-up GitHub
mutation:

```text
LOCK: agent=<agent-id> issue=#<issue> ts=<ISO8601> mode=single-writer
```

An issue-level `START:` comment is useful for status, but it does not satisfy
the PR lock requirement from `CDB_AGENT_POLICY.md` section 4.1.

Example status comment on the issue:

```text
START: <one-sentence scoped task and safety boundary; PR lock will be first PR comment>
```

Make the smallest docs change that satisfies the issue. Avoid opportunistic
cleanup in adjacent docs unless the issue explicitly asks for it.

## 4. Validate Locally

Use the validation required by the issue. For docs-only slices this often means:

```bash
git diff --check
rg -n "Live-Go|Echtgeld-Go|LR bleibt NO-GO|Docs/UI sind Orientierung" docs/<scope>
ruff check .
```

Run the repo's agreed sensitive-term scan for the changed docs path as a
separate validation step, and investigate any hit before publishing.

If a validation failure is caused by known unrelated untracked files, document it
as scope-fremd and do not fix it inside the issue unless explicitly instructed.

## 5. Commit, Push, And Open PR

Use a narrow commit message:

```bash
git add docs/<scope>
git commit -m "docs(onboarding): add visual developer start pack"
git push -u origin docs/<short-scope>-<issue>
gh pr create --base main --head docs/<short-scope>-<issue>
gh pr comment <pr-number> --body "LOCK: agent=<agent-id> issue=#<issue> ts=<ISO8601> mode=single-writer"
```

PR body should include summary, changed files, validation, scope boundaries,
Safety/LR statement, and issue links. Use
[`../templates/pr_body_template.md`](../templates/pr_body_template.md) as the
starting point.

## 6. Wait For Required Status And Merge Only If Capable

Before merge (SSOT: [`docs/runbooks/merge_policy_ci_gate.md`](../../runbooks/merge_policy_ci_gate.md)):

1. Live `cdb-local-ci` SUCCESS on the exact PR head SHA (Commit Status).
2. Diff remains in scope; local Fast-CI evidence bound to that head.
3. No new stop condition appeared in comments or checks.
4. No live, runtime, Docker, trading, DB write, memory write, or LR change was
   introduced.
5. Session can perform regular squash merge (capability gate). Hosted Actions
   red due to billing/lock is not automatically a merge blocker.

Use squash merge when the capability gate is proven:

```bash
gh pr merge <pr-number> --squash --delete-branch
```

If the session lacks publisher/merge rights: leave the PR open and report
`DONE_PR_OPEN_MERGE_HANDOFF`. Never use `--admin` as a bypass. Do not
re-push a remote branch deleted after squash merge.

## 7. Comment And Close

After a **live-verified** merge (`DONE_MERGED_CLOSED`), comment on the target
issue with the PR link, commit, validation, and scope boundary. Close the
issue only when the merged PR satisfies the issue acceptance.

If the issue is part of a parent chain, add a short parent status comment with
the next recommended slice.
