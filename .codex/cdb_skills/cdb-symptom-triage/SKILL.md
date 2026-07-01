<!--
Canonical Skill Source: docs/skills/cdb-symptom-triage/SKILL.md
Surface: codex
Sync Status: mirrored-from-canon
Last Verified: 2026-07-02
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-symptom-triage
description: >
  Turn a raw symptom, error suspicion, or debug signal into a clearly framed CDB
  debug case: classify affected area, affected paths, status class, blast radius,
  and first evidence, then route to the right existing skills and subagents
  (primarily cdb-root-cause). Use at the very start of a debug flow when the cause
  is not yet isolated. This skill does not prove a root cause and does not apply a
  fix; it frames and routes. Not for forward change-validation
  (cdb-shadow-validation) and not for canon or doc drift (cdb-drift-reconcile).
disable-model-invocation: true
---

# CDB Symptom-Triage Skill

Turn a raw symptom, error suspicion, or debug signal into a clearly framed CDB
debug case, then route it to the right existing skill or subagent. This skill is
the entry gear of the CDB debug skill family: it does not prove a root cause and
it does not apply a fix - it classifies, scopes the blast radius, names the first
evidence to collect, and hands off (primarily to `cdb-root-cause`).

Standalone: it works from a bare symptom with no prior record. Composable: if a
Debug-Record (`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`) already
exists, extend it instead of starting a new one.

## When to trigger

Use at the very start of a debug flow, when the cause is not yet isolated and the
right next step is unclear. Typical inputs:

- red or flaky CI check
- a failing test
- a log anomaly
- a wrong value or unexpected output
- a replay-vs-paper delta
- an unexpected risk block or reason-code
- nondeterminism / flake
- a system-design suspicion
- a contract or dataflow suspicion

## Delimitation (what this skill is not)

- vs `cdb-root-cause`: root-cause proves the underlying cause with deterministic
  evidence; symptom-triage only frames and routes, it proves nothing.
- vs `cdb-shadow-validation`: shadow-validation works forward from a planned
  change to its validation path; symptom-triage works backward from an observed
  symptom to a framed investigation.
- vs `cdb-drift-reconcile`: drift-reconcile checks canon / doc / surface drift;
  symptom-triage frames debug signals in general.

## Method

1. Restate the raw `symptom_or_signal` in one or two precise sentences.
2. Classify: `affected_area`, `affected_paths`, `status_class`, `blast_radius`,
   `suspected_gap_or_bug`. Keep Stage / LR / CI / Runtime classes distinct - do
   not read a board stage as an LR verdict.
3. Name `first_evidence_to_collect`: the minimal artefacts, logs, files, or checks
   needed before real analysis.
4. Route: pick `route_to` (skills + subagents) with a short `reason_for_route`.
   Prefer the single best next step, not all at once.
5. Set `next_recommended_step` (usually `cdb-root-cause`).

`blast_radius` is a rough, honest scope estimate (single file / one service /
cross-service / contract-wide / repo-wide), not a precise metric.

## Routing

| Signal class | Route to (skill) | Route to (subagent) |
|---|---|---|
| Red / flaky CI check | `gh-fix-ci`, `cdb-ci-cd-guard` | `cdb-ci-debugger` |
| Failing test / wrong value / logic defect | `cdb-root-cause` | `cdb-code-reviewer` |
| Replay / paper / determinism / evidence | `cdb-root-cause` | `cdb-validation-evidence-analyst` |
| Service boundary / dataflow / design | `cdb-root-cause` | `cdb-system-architect` |
| Contract / envelope / no-float suspicion | `cdb-contract-evidence-gatekeeper` | `cdb-code-reviewer` |
| Canon / doc / surface drift | `cdb-drift-reconcile` | `cdb-repository-auditor` |
| Missing test / regression risk | `cdb-test-first` | - |
| Runtime / stack behaviour | - | `cdb-stack-ops-auditor` |
| Secret / security signal | - | `cdb-security-triage` (stop, secret-safe) |
| GitHub PR / issue / API routing | `cdb-github-api-ops` | - |

Default next step when unsure: `cdb-root-cause`.

## Output

Populate the Debug-Record fields per
`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`: `symptom_or_signal`,
`affected_area`, `affected_paths`, `status_class`, `suspected_gap_or_bug`,
`first_evidence_to_collect`, `route_to` (skills + subagents), `reason_for_route`,
`stop_condition`, `next_recommended_step`. Leave anything you cannot yet support
empty. These triage fields are additive per the contract (section 4.3 / 8).

## Stop conditions

- Unbounded symptom (cannot be scoped or reproduced) -> stop and request a tighter
  description or a reproduction.
- A secret / live / LR / DB / runtime boundary appears -> stop and route to
  secret-safe or gated handling; do not proceed casually.
- Required first evidence is missing -> name it and stop before routing deeper.
- Scope starts growing into a fix or a multi-cause investigation -> stop and hand
  off to `cdb-root-cause`.

## Anti-patterns

- Selling the symptom as the cause.
- Fixing directly instead of routing.
- Firing all subagents at once instead of the best next step.
- Reading a board stage as an LR verdict, or a red CI check as a runtime outage.

## Standalone value and family fit

Standalone, this is a fast "what is this and where does it go" pass for any debug
signal. In the debug skill family it is the entry gear: it optionally consumes a
signal, produces a framed Debug-Record, and routes onward - normally into
`cdb-root-cause`. It never requires another skill to have run first.

## Canon sources

- `docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md` - shared Debug-Record.
- `docs/skills/cdb-root-cause/SKILL.md` - primary downstream skill.
- `knowledge/governance/SYSTEM_INVARIANTS.md` - INV-011 evidence format.
- `.cursor/agents/` - delegated read-only subagents.
