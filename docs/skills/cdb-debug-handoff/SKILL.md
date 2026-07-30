---
name: cdb-debug-handoff
description: >
  Package a debug case (a Debug-Record produced by symptom-triage, root-cause,
  and/or regression-gap, or a standalone record) into a clean, honest handoff:
  verify the record is complete enough, list what is still unresolved, and route
  to the right continuation - normally cdb-session-close, a follow-up issue, or
  back to an earlier debug gear. This skill never stages, commits, closes, or
  fixes anything; it only checks completeness and routes. Not the session close
  itself (cdb-session-close) and not the entry framing (cdb-symptom-triage).
disable-model-invocation: true
---

# CDB Debug-Handoff Skill

Package a debug case into a clean, honest handoff and route it onward. This is the
exit gear of the CDB debug skill family: it takes a Debug-Record
(`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`) - built by
`cdb-symptom-triage`, `cdb-root-cause`, and/or `cdb-regression-gap`, or a
standalone record - checks whether it is complete and honest enough to hand off,
names what is still unresolved, and routes to the right continuation. It never
stages, commits, closes a session, writes an issue, or fixes anything.

Standalone: it works on any single Debug-Record, even one filled in by a person.
Composable: it is the natural last step after the earlier debug gears, and its
primary destination is `cdb-session-close`.

## When to trigger

- a debug flow is ending and its Debug-Record must be handed off cleanly
- a root cause plus regression gap are recorded and the work will continue later
- a debug case must move to another session, owner, or a follow-up issue
- a session is being closed and needs honest, non-overstated debug input
- a partial investigation must be parked without pretending it is finished

## Delimitation (what this skill is not)

- vs `cdb-session-close`: session-close performs the real close (git staging,
  commit, push, issue follow-through) behind its own Human-GO gate and mutates
  state; debug-handoff only packages the Debug-Record and names the destination -
  it mutates nothing.
- vs `cdb-symptom-triage`: triage is the entry gear that frames a raw signal;
  handoff is the exit gear that packages a resolved or parked record.
- vs `cdb-regression-gap`: regression-gap names the missing guard; handoff decides
  whether the record (including that gap) is complete enough to hand off and to
  whom.

## Method

1. Read the current Debug-Record; do not invent missing content.
2. Assess completeness honestly: which core fields (`symptom_or_signal`,
   `status_class`, `root_cause`, `fix_plan`, `test_gap`, `residual_risk`,
   `followup_needed`) are filled and which are still empty. Keep status classes
   distinct (a board stage is not an LR verdict).
3. Set `handoff_state`: `ready`, `partial`, or `blocked`.
4. Pick the `destination` and a short `handoff_reason`; carry forward the existing
   INV-011 evidence refs (do not fabricate new ones).
5. State what must NOT be claimed (e.g. cause not proven, LR unchanged) and set
   `next_recommended_step`.

Hand off one coherent debug case at a time; do not bundle unrelated cases.

## Routing

| Handoff situation | Route to (skill) | Route to (subagent) |
|---|---|---|
| Record complete, session ending | `cdb-session-close` | - |
| Work continues in a later session | `cdb-issue-to-session-plan` | - |
| Follow-up issue needed at close | `cdb-session-close` | - |
| Cause not yet proven | `cdb-root-cause` | `cdb-code-reviewer` |
| Missing guard / evidence | `cdb-regression-gap` | `cdb-validation-evidence-analyst` |
| Closure / contract evidence question | `cdb-contract-evidence-gatekeeper` | `cdb-governance-gatekeeper` |
| Signal never actually framed | `cdb-symptom-triage` | - |

## Output

Populate the Debug-Record (`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`),
adding a structured `handoff` block (additive per the contract section 4.3 / 8):

```yaml
handoff:
  handoff_state: ready | partial | blocked
  destination: session-close | follow-up-issue | next-session | root-cause | regression-gap | symptom-triage | contract-evidence-gatekeeper
  handoff_reason: <one line: why this destination>
  unresolved_fields: []            # core Debug-Record fields still empty
  carry_forward_evidence: []       # INV-011 refs carried from earlier gears
  residual_risk_ack: <restate residual_risk, do not minimise>
  do_not_claim: []                 # e.g. "root cause unproven", "LR unchanged"
  next_owner: same-session | next-session | issue
next_recommended_step: session-close | new session plan | back to root-cause | back to regression-gap
```

Leave anything you cannot yet support empty; never fill a core field just to look
complete.

## Stop conditions

- Core fields empty or no evidence -> `handoff_state: blocked`; route back to the
  right gear, do not hand off a hollow record.
- The task would require the actual close (staging, commit, push, issue write) ->
  stop; that is `cdb-session-close` behind its Human-GO gate.
- A runtime / DB / MCP / trading / secret boundary appears -> stop and route to
  gated or secret-safe handling.
- Scope grows into fixing the defect or writing the test -> stop.

## Anti-patterns

- Overstating completion (claiming a proven root cause, a merged fix, or LR uplift
  that did not happen).
- Doing `cdb-session-close`'s job: staging, committing, pushing, or closing here.
- Handing off a record with empty core fields as if it were complete.
- Bundling several unrelated debug cases into one handoff.
- Reading a board stage as an LR verdict, or a red CI check as a runtime outage.
- Treating unclear branch lineage or unproven squash patch/tree equivalence as
  safe cleanup — route those cases to `cdb-session-close` § Safe Post-Merge
  Cleanup with `handoff_state: blocked` / `BLOCKED_CLEANUP_EQUIVALENCE_UNCLEAR`
  rather than deleting worktrees or using `branch -D`.

## Standalone value and family fit

Standalone, this is a fast "is this debug case ready to hand off, and where does it
go" pass for any Debug-Record. In the debug skill family it is the exit gear
(gear 4): it consumes the record left by `cdb-symptom-triage` ->
`cdb-root-cause` -> `cdb-regression-gap`, verifies it is honest and complete
enough, and routes cleanly - normally into `cdb-session-close`. It never mutates
repo, git, or issue state, and it never requires another skill to have run first.

## Canon sources

- `docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md` - shared Debug-Record.
- `docs/skills/cdb-symptom-triage/SKILL.md` - entry gear.
- `docs/skills/cdb-root-cause/SKILL.md` - cause isolation.
- `docs/skills/cdb-regression-gap/SKILL.md` - missing-guard identification.
- `docs/skills/cdb-session-close/SKILL.md` - primary handoff destination.
- `knowledge/governance/SYSTEM_INVARIANTS.md` - INV-011 evidence format.
