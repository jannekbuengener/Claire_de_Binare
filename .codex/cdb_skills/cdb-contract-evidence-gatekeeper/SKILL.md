---
name: cdb-contract-evidence-gatekeeper
description: 'Hard gatekeeper for Claire_de_Binare acceptance and evidence decisions. Use when the task is deciding `freigabefaehig`, `closure-ready`, `wirklich erledigt`, `go/no-go`, `accept/reject`, `PASS/BLOCKED`, blocker vs non-blocking gap, report artifact vs real defect, canon drift vs evidence gap, Stage-System vs LR-System vs Repo/Engineering-Status, or cross-service contract ambiguity around producer, owner, unit, metadata, persistence, or proof. Do not use for broad implementation work.'
---

# CDB Contract Evidence Gatekeeper

## Purpose
Use this skill for hard gate decisions, not for implementation.

This skill exists to decide whether a claim, issue, PR, report, status change, or proposed conclusion is actually justified under the current Claire_de_Binare canon.

Use it to stop:
- fake closure
- status inflation
- stage/LR confusion
- narrative replacing evidence
- contract claims passing without producer, owner, unit, or persistence clarity

## Use this skill when
- the user asks `freigabefaehig?`
- the user asks `closure-ready?`
- the user asks `wirklich erledigt?`
- the user asks for go/no-go, accept/reject, PASS/BLOCKED
- the user asks whether something is a blocker or only a non-blocking gap
- the user asks to separate Stage-System, LR-System, and Repo/Engineering-Status
- the user asks whether a claim is repo-backed or only narrative
- the user asks whether a problem is canon drift, contract drift, evidence gap, policy ambiguity, or only a reporting artifact
- the user asks whether cross-service metadata, payload, producer, owner, unit, or persistence claims are actually proven

## Do NOT use this skill when
- the task is mainly feature implementation
- the task is broad coding work without a gate decision
- the task is routine documentation editing without an acceptance question
- the task is a straightforward CI repair with no canon, evidence, or gate ambiguity
- the task is future architecture brainstorming without a current closure or acceptance decision

If the hard decision is complete and the remaining work becomes implementation, hand off to the relevant execution skill.

## Mandatory canon sources
Before making a gate decision, use this control-first order:

1. `#1445`
2. newest weekly comment in `#1445`
3. `#1492` only when Stage-/`trade-capable`-context is involved
4. `docs/runbooks/CONTROL_REGISTER.md`
5. `CURRENT_STATUS.md`
6. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
7. only then directly relevant issues, PRs, files, tests, and committed evidence artifacts

If the task does not touch GitHub, stage, LR, or status claims, scale this down conservatively. If it does touch those surfaces, skipping the canon is forbidden.

## Hard rules
### 1. Status-class first
Classify every decision surface before judging it:
- Stage-System
- LR-System
- Repo/Engineering-Status
- Runtime/Operator-Reality
- CI/Workflow-Reality
- Data-contract/persistence-reality
- Documentation/reporting quality

If more than one class is involved, split them. Never let one system silently overwrite another.

### 2. SSOT boundaries are mandatory
- `CURRENT_STATUS.md` = repo and engineering status
- `docs/runbooks/CONTROL_REGISTER.md` = control-board focus, stage context, cockpit memory
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` = LR verdict and LR phase status
- `#1445` = operational control umbrella
- `#1492` = ratified stage context only when `trade-capable` is relevant

Never derive LR go/no-go from Board stage.
Never read `trade-capable` as implicit live-readiness.
Never treat issue closure by itself as proof.

### 3. Evidence over narrative
Split every claim into these buckets:
- direct repo-backed evidence
- indirect evidence
- policy decision
- assumption or interpretation
- missing evidence

Do not blend them into one soft conclusion.

### 4. Fail closed on unresolved ambiguity
Do not produce a fake PASS if any required gate depends on unresolved ambiguity such as:
- unclear producer
- unclear owner of truth
- unclear units or semantics
- unclear source of truth
- unclear Stage-vs-LR scope
- ambiguous evidence wording
- memory-backed criteria with no repo anchor

Use `BLOCKED` or `NON-BLOCKING GAP` instead.

### 5. Separate policy from proof
A maintainer policy decision can be valid, but it is not the same as repo-backed proof.
If the conclusion depends on policy, say so explicitly.

### 6. No fake closure
Do not recommend full closure when the truthful result is one of these:
- closure-ready with explicit limits
- stage-ratified but LR-still-partial
- fixed in code but not evidenced enough
- report corrected, underlying system unchanged
- non-blocking residual still needs to stay explicit

### 7. Cross-service claims require contract checking
If the task touches payload propagation, metadata, persistence, replayability, or cross-service meaning, inspect explicitly:
- producer
- consumer
- owner of truth
- units and semantics
- propagation path
- persisted surface
- test coverage
- fail-closed behavior

Do not accept a cross-service claim just because one layer mentions the field.

## Decision workflow
1. Classify the decision surface.
2. State the exact claim under review.
3. Pull the canon and only the artifacts that can change the verdict.
4. Build the evidence map.
5. Classify each gap exactly once.
6. Issue one verdict from the allowed verdict classes.
7. Recommend exactly one next move.

## Allowed verdict classes
- `PASS`
- `PASS WITH EXPLICIT LIMITS`
- `NON-BLOCKING GAP`
- `BLOCKED`
- `OUT OF SCOPE`

Use the narrowest truthful verdict.

## Required output format
1. `Decision surface`
2. `Claim under review`
3. `Canon anchors`
4. `Evidence map`
5. `Verdict`
6. `Why`
7. `Recommended next move`

Optional:
8. `Issue comment draft`

## Special decision patterns
### Report vs real system defect
If the problem is only wording or reporting, say so directly.
Use the smallest truthful label:
- reporting artifact
- canon drift
- runtime defect
- contract defect
- evidence gap
- policy ambiguity

### Stage vs LR
If Stage and LR diverge:
- state both statuses explicitly
- state which one is under review
- forbid implicit promotion from one system into the other

Typical pattern:
- Stage: ratified or acceptable
- LR: still partial or still NO-GO
- conclusion: stage decision may pass with limits while LR cannot be upgraded

### Code fixed, proof incomplete
If implementation exists but proof for the claimed status is incomplete:
- do not call it fully done
- prefer `PASS WITH EXPLICIT LIMITS` or `NON-BLOCKING GAP`

### Contract ambiguity
If a field exists somewhere but producer, owner, unit, or meaning is unclear:
- treat it as contract ambiguity
- do not pass the claim as canonically clean

## Repo-specific guardrails
- `trade-capable` is a stage label, not live-capital authorization
- `LR-050` remaining `NO-GO` is orthogonal to stage ratification
- Grafana is not automatically a gate surface
- Solo-maintainer reality applies; do not invent teams, reviewers, or escalation chains
- evidence beats storytelling
- non-blocking residuals must remain explicit instead of disappearing into comments
- the working repo is canon
- historical docs are not active proof unless explicitly relevant

## Tooling posture
- read-only first
- inspect before action
- prefer file reads, grep, issue reads, PR reads, tests, and committed artifacts
- only propose writes, updates, or closure after the verdict is stable

This skill should feel like a gate review, not like opportunistic implementation.

## Anti-patterns
Do not:
- claim `PASS` because wording sounds convincing
- treat issue closure as proof by itself
- use remembered thresholds with no repo match
- merge Stage, LR, and Repo status into one blended judgement
- call something a blocker without naming the blocking system
- call something done when it is really a non-blocking residual
- accept field propagation without producer, owner, unit, and semantics clarity
- rewrite scope just to avoid a hard verdict

## References
- Read [references/CDB_DECISION_SURFACE_MATRIX.md](references/CDB_DECISION_SURFACE_MATRIX.md) when the task spans multiple status classes.
- Read [references/CDB_VERDICT_CLASSES.md](references/CDB_VERDICT_CLASSES.md) when the verdict boundary is tight.
- Read [references/CDB_ISSUE_COMMENT_PATTERNS.md](references/CDB_ISSUE_COMMENT_PATTERNS.md) when the result should be posted back to GitHub.
