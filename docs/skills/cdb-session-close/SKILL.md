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
  normalizes local main, classifies temporary git surfaces, and performs
  mandatory post-close Control-Plane follow-up issue intake, and mandatory
  Residual Work / Restunsicherheits-Intake immediately before final session
  close.
---

# CDB session close

Close a working session so the repo, git state, and issue thread reflect reality instead of intention.

## Inputs

- Current working tree and session context.
- Session start timestamp or last known issue/PR checkpoint.
- Optional issue number, PR, branch context, or prior session goal.
- Merged PR number and merge timestamp when a PR was merged in this session.
- Optional prior outputs from `cdb-control-intake` or `cdb-issue-to-session-plan`.
- Access to git status, diffs, staged state, and issue or PR context when relevant.
- Access to GitHub issues, PRs, workflow runs, and relevant Control-Plane runbooks.
- Optional outputs or artifacts from:
  - `cdb-post-merge-followup-scanner`
  - `cdb-control-followup-classifier`

## Workflow

0. Human-GO gate (hard):
   - Default mode is read-only analysis.
   - Require explicit user GO before any action that mutates repository, working tree, index, branch, remote, GitHub, or worktree state, including:
     - staging changes (any `git add` / patch staging)
     - branch switching or checkout/switch operations
     - pull, merge, rebase, or fast-forward update operations
     - stash/apply operations
     - creating a commit
     - pushing to any remote
     - removing worktrees
     - deleting local or remote branches
     - cleanup/delete operations
     - writing to GitHub (issue/PR comment, review reply/resolve, status update, label/state change)
   - If GO is not granted: stop after producing the close-out summary draft.

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
   - If a PR was merged during this session, proceed to step 6. If no PR
     exists: skip steps 6–7. If the PR is still open because this session
     could not prove the autonomous-merge capability gate (missing
     `statuses:write`, unbound evidence, auth/publisher block): record
     `DONE_PR_OPEN_MERGE_HANDOFF` with the exact missing capability and
     skip steps 6–7. Do not use `--admin` and do not loop retries.
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
   - After squash merge with `--delete-branch`: do **not** re-push or
     recreate the deleted remote branch (anti-repush). Local `[gone]`
     tracking refs may remain historical; clean them with `git fetch
     --prune` / `git branch -d` only when unambiguous.
   - Otherwise: record as `n.a.` or `pending` — no blind deletes.
   - Leftover untracked files (session logs, patches): name each one explicitly and state whether it is committed, discarded, or pending. Do not ignore.
8. Post-close Control-Plane Follow-up Intake — mandatory after steps 6–7 when applicable, or after any issue-driven session close:

   Always after a merged PR or issue-driven session close, sweep for new
   Control-/Drift-/Post-Merge follow-up issues:

   ```bash
   gh issue list --state open --limit 30 --json number,title,createdAt,labels,body,url
   ```

   Identify issues created since session start or PR merge. Search titles,
   labels, and bodies for markers including:

   - `cdb-post-merge-followup-scanner`
   - `CDB Post-Merge Follow-up Scanner`
   - `cdb-control-followup-classifier`
   - `control follow-up`
   - `post-merge follow-up`
   - `drift`
   - `docs after PR`
   - `runbook_evidence_followup_drift`
   - `architecture_service_catalog_drift`
   - `discovery_surface_drift`
   - `canon_terminology_drift`
   - `docker_runtime_rebuild_followup_required`

   Also inspect workflow-run artifacts or comments referencing the above
   scanners when available.

   For each candidate issue, determine whether it was directly triggered by
   this session's PR, merge commit, branch, or changed files. If yes,
   classify as `post-close follow-up candidate`.

   **Candidate rules:**

   - If exactly one candidate exists and it is small and safe:
     - Pull the issue into the next work hop.
     - Apply `cdb-control-intake`, then `cdb-issue-to-session-plan` on that issue.
     - When Plan-GO or routine docs/control/reconcile follow-up autonomy already
       applies: start directly.
     - When no valid GO context exists: emit a concrete next-issue handoff
       instruction instead of auto-starting.
   - If multiple candidates exist, prioritize by direct causality:
     1. explicit mention of this PR/branch/merge
     2. identical changed files
     3. workflow marker with PR number
     4. newest issue
     - Start at most one issue automatically; list the rest under Reststatus.
   - If the candidate is unclear, large, safety-critical, CI-red,
     LR-/Live-/Trading-relevant, or scope-expanding: fail-closed; do not
     auto-start; formulate a clear handoff.

   **Bounded autonomy:**

   - At most one automatic follow-up hop per session close.
   - No recursive endless agent loop.
   - After completing the follow-up issue, run normal `cdb-session-close` again.
   - If the second close finds new issues again: report only; do not auto-start
     unless Jannek grants explicit new GO.

9. Residual Work / Restunsicherheits-Intake — mandatory, always immediately
   before final session close:

   Run this step **always**, after step 8 (or after steps 6–7 when step 8 is
   n.a.), and **before** producing the final close-out summary. This is the
   last active check before session end.

   The agent must actively review the session and answer each question honestly:

   - Was something visible that lay outside the original scope?
   - Is there residual uncertainty that was not cleanly closed?
   - Is there an assumption that must be verified later?
   - Was a check, test, review, drift reconciliation, or evidence proof
     intentionally not executed?
   - Did the agent's own changes create new follow-up work?
   - Are there stale docs, skill-/surface drift, CI-/workflow drift,
     contract drift, or missing acceptance evidence?
   - Is there a topic that makes sense but must not be secretly pulled into
     the current scope?

   Record each answer. If **at least one** question is **yes**, proceed with
   deduplicated follow-up issue handling:

   **Dedupe search (mandatory when any yes):**

   ```bash
   gh issue list --state open --limit 50 --json number,title,body,labels,url
   ```

   Additionally search open issues and PRs for relevant keywords derived from
   the finding: affected file paths, module names, PR numbers, workflow names,
   drift types, contract names, skill names, and error/check identifiers.

   **When no matching open issue exists — create a focused follow-up issue:**

   - Title: clear, cause-oriented (not a generic “cleanup” or “misc”).
   - Body must include all sections:
     - **Auslöser / Beobachtung**
     - **Warum außerhalb des aktuellen Scopes**
     - **Betroffene Dateien, PRs, Workflows oder Docs**
     - **Evidence / Commands / Befund**
     - **Acceptance Criteria**
     - **Non-goals**
     - **Safety Boundaries**
     - **Vorgeschlagene Skills für die nächste Session**
   - Set labels only when they exist in the repo and fit; do not invent labels.
     Known usable labels (verify live when creating):
     - `follow-up`
     - `docs` or `type:docs` or `scope:docs`
     - `ci`, `scope:ci`, or `ci-cd`
     - `triage:offen` (when triage is needed)
     - `scope:governance` (control-/canon-/policy-adjacent topics)
     Labels **not** registered in repo (do not use unless created separately):
     `drift`, `control-plane`, `needs-triage`.
   - Prefer **multiple deduplicated issues** over one catch-all issue when
     rest points are independent.

   **When a matching open issue exists:**

   - Do **not** create a duplicate.
   - Link the existing issue in the close-out report.
   - When GitHub write is allowed: post a supplementary comment with new
     evidence, commands, and session context.

   **When GitHub write is not available (read-only close, blocked `gh`, or no GO
   for GitHub mutations):**

   - Output issue-ready title, full body, and intended labels in the close-out.
   - Set residual status: `FOLLOW_UP_ISSUE_REQUIRED_BUT_NOT_CREATED`.
   - Do **not** mark the session as fully clean/complete (`erledigt`).

   **Fail-closed rules for this step:**

   - No silent scope expansion to “fix while here”.
   - No automatic Runtime-, Docker-, Secrets-, DB-, LR-, Live-, or Echtgeld
     follow-up execution — issue only, do not run.
   - Safety-/LR-/Runtime-related rest gaps: create or link issue; stop there.
   - No endless loop: create/link follow-up, then close — do not continue
     unbounded extra work in the same session.
   - Residual-work follow-up issue **creation** is allowed without extra
     micro-GO when session-close write path is active (aligned with
     `CDB-Follow-up-Issue-Rule`). In read-only analysis mode (step 0, no GO),
     draft only and mark `FOLLOW_UP_ISSUE_REQUIRED_BUT_NOT_CREATED`.

   **When all questions are no:**

   - Record `Residual Work / Restunsicherheits-Intake: clean`.
   - Proceed to step 10.

10. Produce the close-out summary:
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
- Do not auto-start more than one follow-up issue per session close (step 8
  auto-start hop). Step 9 may create or link **multiple deduplicated** residual
  follow-up issues when rest points are independent.
- Do not recurse into endless follow-up chains without explicit new GO.
- Do not mark a session `erledigt` when step 9 found residual work requiring a
  follow-up issue that was not created or linked.
- Do not silently expand scope to resolve residual findings during close.

## Fail-Closed Rules

- If any write step would exceed the agreed scope (unexpected files/hunks, scope growth): STOP and ask for clarification + explicit GO.
- If checks are red/failed/unknown for the claimed result: STOP; do not stage/commit/push; report the failing check(s).
- If the PR/review/writer/lock situation is unclear or conflicting: STOP; do not stage/commit/push or write to GitHub; ask for explicit handoff/GO.
- If there is an active PR or lock collision touching the same files/scope: STOP; no further actions until clarified.
- If intended session changes cannot be separated from unrelated local changes, stop and report the close as incomplete.
- If verification is missing or ambiguous, report exactly that instead of implying confidence.
- If the session was issue-driven but the issue mapping is uncertain, do not fabricate an issue-ready completion claim.
- If no clean commit boundary exists, do not force a commit.
- If push or issue-status updates were not performed, keep them as pending actions in the close-out.
- If the issue comment would overstate what landed, what was pushed, or what is actually done, downgrade the final status and state the pending step explicitly.
- If a PR was merged but the merge commit cannot be verified on `origin/main`: the session is incomplete; do not set status to `erledigt`.
- If `git merge --ff-only origin/main` fails: report as pending; do not force a merge or ignore the divergence.
- If new follow-up issues are found but their link to this session is unclear: do not auto-start.
- If more than one equally ranked candidate exists: do not pick blindly; emit a prioritized list.
- If the candidate issue has Runtime-, Docker-rebuild-, Secrets-, Security-, LR-, Live-,
  or Echtgeld impact: no auto-start without explicit GO.
- If GitHub issues or workflow runs cannot be read: Reststatus = `follow-up intake unknown`, not `erledigt`.
- If new Control-Plane issues exist and were not checked: do not mark the session fully complete.
- If step 9 Residual Work intake was skipped: do not mark the session fully complete.
- If step 9 found residual work and no dedupe search was performed: do not mark
  the session fully complete.
- If step 9 requires a follow-up issue but GitHub write failed or was blocked:
  status = `FOLLOW_UP_ISSUE_REQUIRED_BUT_NOT_CREATED`; not `erledigt`.
- If residual findings have Runtime-, Docker-, Secrets-, LR-, Live-, or
  Echtgeld impact: create/link issue only; do not execute remediation in close.

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

Post-Close Follow-up Intake
- GitHub-Issue-Sweep: geprüft / nicht geprüft / pending
- Workflow-Follow-up-Artefakte: geprüft / nicht gefunden / pending
- Neue Follow-up-Issues seit Session-Start/PR-Merge: <liste> / keine / unknown
- Direkt zugehöriger Candidate: #<nr> / keiner / unklar
- Auto-Start nächstes Issue: ja / nein / blocked
- Begründung: ...

Residual Work / Restunsicherheits-Intake
- Out-of-scope erkannt: ja / nein
- Restunsicherheit erkannt: ja / nein
- Nacharbeit nötig: ja / nein
- Dedupe geprüft: ja / nein / n.a.
- Existing Issue: #<nr> / keines / unknown
- Neues Follow-up-Issue erstellt: #<nr> / nein / blocked
- Grund: ...
- Issue-ready Entwurf (nur wenn blocked): <titel + body-summary> / n.a.

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

Post-Close Follow-up
- GitHub-Issue-Sweep: ...
- Candidate: ...
- Auto-Start: ...
- Begründung: ...

Residual Work / Restunsicherheit
- Out-of-scope: ...
- Restunsicherheit: ...
- Nacharbeit: ...
- Dedupe: ...
- Existing Issue: ...
- Neues Issue: ...
- Grund: ...

Status
- erledigt | weitere Zuarbeit noetig | bereit fuer Claude Code | FOLLOW_UP_ISSUE_REQUIRED_BUT_NOT_CREATED
```

## Anti-Patterns

- Do not use `git add .`.
- Do not beautify an incomplete session into a finished one.
- Do not claim checks ran when they did not.
- Do not hide uncommitted residue.
- Do not label work as `bereit fuer Claude Code` without a real continuation need.
