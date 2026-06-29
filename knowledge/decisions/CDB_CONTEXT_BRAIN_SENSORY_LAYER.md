# Context Brain Sensory Layer

| Field | Value |
| --- | --- |
| Status | **accepted** / **active** |
| Date | 2026-06-29 |
| Issue | GitHub issue #3480 |
| Parent | GitHub issue #3479 |
| Principle | `empfindsamer, nicht schlauer` |

## Scope

This canon defines the CDB Context Brain as a **Sensorik-Schicht** for agent and
developer orientation. It sharpens the already active read-only posture without
changing runtime, DB, MCP, LR, or trading behavior.

Out of scope:

- #3484 graph operationalization
- #3486 vector / embedding pipeline
- #3487 hybrid retrieval / sensory fusion
- runtime logic, Graph/Vector/Hybrid implementation, or policy expansion

## Core principle

Context Brain makes agents **empfindsamer, nicht schlauer**.

It improves perception and orientation before action. It does **not** grant
autonomy, authority, or execution rights.

## Layer model

Canonical tool/order separation:

`Sensory -> Evidence -> Action`

- **Sensory** gathers orientation signals and surfaces proximity, relevance,
  drift, decision context, evidence pointers, and memory hints.
- **Evidence** validates or rejects claims with concrete repo/live/tool/query/record proof.
- **Action** remains separately gated and never follows from Context Brain output alone.

## Truth order

Canonical priority:

`GitHub > Repo > Context > Memory`

Interpretation:

1. GitHub live — issues, PRs, checks, branches, comments
2. Repo live — canon docs, code, contracts, runbooks
3. Context — read-only context tooling only when separately evidenced
4. Memory — session or stored memory hints, never authority

`CURRENT_STATUS.md` stays a **ledger, not live truth**.

## Separation boundaries

These surfaces must stay explicitly separate:

- GitHub live
- Repo live
- Ledger / `CURRENT_STATUS.md`
- PR body
- local staged files

None of these lower-authority surfaces may be upgraded into DB truth, live truth,
or closure truth by narrative alone.

## Perception contract

The Context Brain sensory layer is expected to surface:

`Naehe, Relevanz, Drift, Decisions, Evidence, Memory`

This is perception support only. It is not autonomous reasoning authority.

## Evidence contract

No DB-backed claim is allowed without Tool/Query/Record evidence.

Repo text, ledger text, PR body text, or local staged files are not enough to
claim DB-backed proof by themselves.

## Forbidden zone

The sensory layer must not cross these boundaries:

- keine Autonomie
- keine Live-Entscheidung
- kein Echtgeld
- keine Trading-Freigabe
- keine produktiven DB-Writes
- keine MCP-Mutation

LR remains NO-GO. Board stage stays orthogonal to Live-Go.

## Roadmap placement

- #3479 remains the parent epic for the sensory roadmap.
- #3480 defines the canonical sensory-layer baseline in documentation.
- #3484, #3486, and #3487 remain explicit follow-on work and are not delivered by this file.

## References

- [CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md)
- [ADR-002-context-intelligence-canon.md](ADR-002-context-intelligence-canon.md)
- [docs/onboarding/repo_brain_context_intelligence.md](../../docs/onboarding/repo_brain_context_intelligence.md)
