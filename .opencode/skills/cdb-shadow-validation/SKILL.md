---
name: cdb-shadow-validation
description: >
  Decide the conservative validation path for Claire_de_Binare strategy,
  signal, execution, dataflow, contract, persistence, observability, or
  shadow-relevant changes. Use when Codex must classify a change, assess blast
  radius and risk against current control status, and choose exactly one
  outcome: unit tests only, replay needed, mock exchange or emulator needed,
  shadow evidence needed, or stop and do not release. Use after planning or
  before session close when a concrete change needs a validation decision.
---

# CDB shadow validation

Use this after planning narrows to a concrete change or before `cdb-session-close` when validation depth is still undecided. Choose the minimum safe validation path for a concrete change and fail closed when the evidence is incomplete.

## Inputs

- A concrete change, diff, PR, issue, commit, or scoped work description.
- Working repo at `D:\Dev\Workspaces\Repos\Claire_de_Binare`.
- Access to `docs/runbooks/CONTROL_REGISTER.md`, `CURRENT_STATUS.md`, and `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.

## Required Outcomes

Choose exactly one:

- `nur Unit Tests`
- `Replay noetig`
- `MockExchange / Emulator noetig`
- `Shadow-Evidence noetig`
- `stoppen / nicht freigeben`

## Workflow

1. Read control status first, before looking at the change details in depth:
   - Read `docs/runbooks/CONTROL_REGISTER.md`.
   - Read `CURRENT_STATUS.md`.
   - Read `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
   - Extract the current control boundary: Board stage may be `trade-capable`, but LR remains `NO-GO` and work stays shadow/mock only unless an explicit source proves otherwise.
2. Determine the change class from evidence, not from intent:
   - Strategy or signal logic.
   - Execution, order, trade, routing, or exchange path.
   - Interface, API, schema, or contract boundary.
   - Data model, persistence, storage, or migration path.
   - Observability, alerting, monitoring, or operator signal path.
   - Purely local and isolated internal logic.
3. Identify affected systems and contracts:
   - Name the touched services, modules, adapters, reports, or persistence layers.
   - Name any producer-consumer or request-response contracts affected.
   - Name whether the change can influence orders, fills, positions, balances, signals, or operator decisions.
4. Assess risk and blast radius conservatively:
   - Low: isolated internal logic with no contract, execution, persistence, or control-signal effect.
   - Medium: cross-module or contract-adjacent change without direct execution exposure.
   - High: strategy, signal, execution, order, trade, persistence, or operator control path.
   - Critical: ambiguous or multi-surface change, or any change where the blast radius cannot be bounded confidently.
5. Select the validation path:
   - `nur Unit Tests` only for low-risk isolated logic with no shadow, LR, contract, persistence, execution, or observability relevance.
   - `Replay noetig` for strategy, signal, deterministic decision logic, contract-adjacent, or dataflow changes that can be validated offline without exchange behavior.
   - `MockExchange / Emulator noetig` for execution, order lifecycle, adapter, fill-handling, or exchange-facing changes.
   - `Shadow-Evidence noetig` for changes that can alter operational behavior, confidence, or release posture beyond replay or emulation alone, especially when strategy, signal, execution, observability, or cross-service interactions remain behaviorally relevant.
   - `stoppen / nicht freigeben` if the change is ambiguous, unbounded, under-specified, conflicts with control status, or needs validation evidence that is unavailable.
6. Escalate upward when uncertain:
   - If two outcomes seem plausible, choose the stricter one.
   - If the required validation environment or evidence cannot be confirmed, choose `stoppen / nicht freigeben`.
   - If LR or shadow relevance is uncertain, treat the change as shadow-relevant.

## Decision Rules

- Never infer LR-GO from Board stage, repo status, or successful local tests.
- Never allow live-capital reasoning or live-release implications.
- Never mix unrelated scope into the validation decision.
- Derive test depth from blast radius and risk, not from developer convenience.
- Treat strategy and signal changes as behavior changes even when the diff looks small.
- Treat contract, persistence, and observability changes as potentially cross-service until proven otherwise.
- Treat missing evidence as increased risk, not as neutral.
- Treat current `trade-capable` Board stage as orthogonal to validation strictness; it does not justify a lighter path.
- If the selected path is anything other than `nur Unit Tests` for a truly isolated internal change, default the operational posture to shadow/mock only.

## Fail-Closed Rules

- If any required control file cannot be read, stop and return `stoppen / nicht freigeben`.
- If the change scope cannot be bounded confidently, stop and return `stoppen / nicht freigeben`.
- If execution, order, or trade paths may be touched but the boundary is unclear, require at least `MockExchange / Emulator noetig`; if even that scope is unclear, stop.
- If cross-service contracts or persistence may be affected and offline evidence is insufficient, require at least `Replay noetig`; escalate to `Shadow-Evidence noetig` when behavior remains operationally relevant.
- If observability or alerting changes could alter operator understanding, do not downgrade below the highest validation level justified by the affected operational path.
- If the change has possible LR or shadow relevance and that relevance cannot be excluded, keep it shadow/mock only.

## Output

Return the result in this structure:

```md
Befund
- ...

Aenderungsklasse
- ...

Empfohlener Validierungspfad
- one of: nur Unit Tests | Replay noetig | MockExchange / Emulator noetig | Shadow-Evidence noetig | stoppen / nicht freigeben

Notwendige Checks
- ...

Stop-Kriterien
- ...

Restunsicherheiten
- ...

Shadow/mock only
- yes/no + why
```

## Anti-Patterns

- Do not guess the lightest validation path.
- Do not reduce validation depth because the diff is small.
- Do not treat passing unit tests as sufficient for strategy, signal, execution, contract, persistence, or observability changes.
- Do not imply deployment or release approval from a validation-path decision.
- Do not blur replay, emulation, and shadow evidence into one bucket.
