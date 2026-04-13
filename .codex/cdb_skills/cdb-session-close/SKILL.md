---
name: cdb-session-close
description: >
  Enforce a disciplined Claire_de_Binare session close. Use when Codex must
  turn completed or partially completed local work into a clean closing state:
  determine whether the session was issue-driven, capture actual changes and
  verification, stage only intended files, prepare a scoped commit, account for
  push and issue-status follow-through, and generate an issue-ready closing
  comment without overstating completion. Use after implementation,
  reconciliation, or validation work when the session needs an honest close.
  When a PR was merged during the session, also verifies delivery on main,
  normalizes local main, and classifies temporary git surfaces before marking
  the session complete.
---

# CDB session close

Close a working session so the repo, git state, and issue thread reflect reality instead of intention.

## Inputs

- Current working tree and session context.
- Optional issue number, PR, branch context, or prior session goal.
- Optional prior outputs from `cdb-control-intake`, `cdb-issue-to-session-plan`, or `cdb-shadow-validation`.
- Access to git status, diffs, staged state, and issue or PR context when relevant.

## Workflow

1. Determine session scope before touching git:
   - Decide whether the session was issue-bezogen.
   - Identify the intended deliverable, the files actually changed, and any unrelated local residue.
   - If the issue link is unclear, keep the close-out generic and mark the missing linkage.
2. Reconstruct what was really done:
   - Capture changed files and artifacts.
   - Capture verification actually performed, not verification that was planned.
   - Capture anything intentionally left undone, blocked, or uncertain.
3. Gate the working tree:
   - Inspect `git status`, unstaged diff, and staged diff.
   - Separate intended session changes from unrelated or half-finished residue.
   - Never use `git add .`.
   - Stage only the files or hunks that belong to the session close, using targeted file staging or patch staging.
4. Prepare the commit conservatively:
   - Prefer one small, testable, reversible commit per coherent topic.
   - If the work is not commit-worthy yet, say so explicitly and stop short of artificial closure.
   - Write a commit message that describes what changed and why.
5. Consider push and issue follow-through as part of the close:
   - If a clean commit exists and push is appropriate, include push in the close path.
   - If push is not done, say so explicitly in the rest status.
   - If the issue state should change, describe the correct next state rather than claiming it changed when it did not.
   - If the work is still local-only, make that explicit in the issue-facing close-out instead of implying landed or review-ready state.
   - If a PR was merged during this session, proceed to step 6. If no PR exists or the PR is still open, skip steps 6–7 and record `pending main-verification` or `n.a.` in the rest status.
6. Verify delivery on `main` — only when a PR was merged in this session:

   ```bash
   gh pr view <PR> --json state,mergedAt,mergeCommit
   git fetch origin main
   git log origin/main --oneline -5
   git checkout main
   git merge --ff-only origin/main
   ```

   Determine:
   - PR merged + merge commit visible on `origin/main` + `--ff-only` succeeded → proceed to step 7.
   - PR merged but merge commit absent from `origin/main` → STOP, session = incomplete.
   - `--ff-only` fails → report as pending, do not force.
   - No PR in this session → mark as `n.a.`, skip this step.
7. Classify temporary git surfaces — only when applicable:

   ```bash
   git worktree list                       # any session worktrees?
   git branch -v --merged origin/main      # any merged feature branch?
   ```

   - If a session worktree is present and unambiguously from this session: `git worktree remove <path>`.
   - If a feature branch is merged and clearly tied to this session: `git branch -d <branch>`.
   - Otherwise: record as `n.a.` or `pending` — no blind deletes.
   - Leftover untracked files (session logs, patches): name each one explicitly and state whether it is committed, discarded, or pending. Do not ignore.
8. Produce the close-out summary:
   - State the factual result.
   - Name changed files and artifacts.
   - Name the root cause or central insight if one exists.
   - Name checks that actually ran and their outcomes.
   - Name real remaining work and uncertainties.
   - Set the final status conservatively.

## Decision Rules

- Do not mark a session as complete if verification, staging, commit scope, or issue linkage is still unclear.
- Do not stage unrelated local changes just to get to a clean tree.
- Do not create a commit that mixes logic, docs, refactors, and residue unless they are one coherent change.
- Prefer leaving honest local residue uncommitted over forcing a misleading close.
- Use `bereit fuer Claude Code` only when there is a concrete handoff reason that another agent should continue from.
- Use `erledigt` only when the issue-facing work is actually verified and the claimed git or GitHub state is real.
- Do not imply LR uplift, live approval, or a Board-stage interpretation from a successful session close.
- Respect solo-maintainer reality; do not invent reviewer, approver, or handoff ceremonies.

## Fail-Closed Rules

- If intended session changes cannot be separated from unrelated local changes, stop and report the close as incomplete.
- If verification is missing or ambiguous, report exactly that instead of implying confidence.
- If the session was issue-driven but the issue mapping is uncertain, do not fabricate an issue-ready completion claim.
- If no clean commit boundary exists, do not force a commit.
- If push or issue-status updates were not performed, keep them as pending actions in the close-out.
- If the issue comment would overstate what landed, what was pushed, or what is actually done, downgrade the final status and state the pending step explicitly.
- If a PR was merged but the merge commit cannot be verified on `origin/main`: the session is incomplete; do not set status to `erledigt`.
- If `git merge --ff-only origin/main` fails: report as pending; do not force a merge or ignore the divergence.

## Output

Return the result in this structure:

```md
Session-Befund
- ...

Betroffene Dateien / Artefakte
- ...

Verifikation / Checks
- ...

Reststatus
- ...

Main-Verifikation (nur wenn PR gemergt, sonst n.a.)
- PR-State: gemergt / offen / n.a.
- Merge-Commit auf origin/main: ja / nein / n.a.
- Lokales main normalisiert: ja / nein / pending / n.a.

Surface-Cleanup (nur wenn applicable, sonst n.a.)
- Worktrees: entfernt: <liste> / n.a. / pending
- Feature-Branch: gelöscht: <name> / n.a. / pending
- Leftover-Files: <klassifikation> / keine / n.a.

Issue-Kommentar
Befund
- ...

betroffene Dateien / Artefakte
- ...

Root Cause oder zentrale Erkenntnis
- ...

empfohlene naechste Schritte
- ...

Validierung / Checks
- ...

Restunsicherheiten
- ...

Status
- erledigt | weitere Zuarbeit noetig | bereit fuer Claude Code
```

## Anti-Patterns

- Do not use `git add .`.
- Do not beautify an incomplete session into a finished one.
- Do not claim checks ran when they did not.
- Do not hide uncommitted residue.
- Do not label work as `bereit fuer Claude Code` without a real continuation need.
