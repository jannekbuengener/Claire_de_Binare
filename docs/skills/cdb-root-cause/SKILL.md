<!--
Canonical Skill Source: docs/skills/cdb-root-cause/SKILL.md
Surface: docs (canonical)
Sync Status: canonical
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-root-cause
description: >
  Separate symptom from root cause for a concrete CDB debug case and produce a
  minimal, reversible fix plan backed by deterministic, artefact-referenced
  evidence. Use when a confirmed symptom (failing test, wrong value,
  replay-vs-paper delta, unexpected block or reason-code, flaky check,
  nondeterminism, contract or dataflow suspicion) must have its underlying cause
  isolated before any fix. Delegates analysis to existing CDB subagents and
  records findings in the shared Debug-Record. Not for planning new features and
  not for executing the fix itself.
disable-model-invocation: true
---

# CDB Root-Cause Skill

Isolate the **root cause** behind a confirmed symptom, prove it with
deterministic evidence, and hand back a minimal, reversible fix plan. This skill
is a thin router: it does not re-implement analysis that existing CDB subagents
already do - it frames the investigation, enforces symptom-vs-cause discipline,
and demands artefact-based evidence.

This skill is **standalone**: it can start from a raw symptom with no prior
record. If a Debug-Record (`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`)
already exists, it continues that record instead of starting a new one.

## When to trigger

- A confirmed symptom needs its cause isolated (after triage or standalone).
- A recurring bug that previous fixes only moved, not removed.
- Nondeterminism / flaky behaviour (determinism suspicion; see
  `knowledge/governance/SYSTEM_INVARIANTS.md`).
- A contract, boundary, or dataflow divergence (e.g. replay-vs-paper delta,
  wrong `Decimal` quantization, regime misclassification, broken envelope chain).
- An unexpected block or reason-code that is not yet explained.

Do **not** trigger for: planning brand-new features (use `cdb-test-first`),
choosing forward validation depth for a planned change (use
`cdb-shadow-validation`), or a pure gate PASS/BLOCKED verdict (use
`cdb-contract-evidence-gatekeeper`).

## Inputs

- A confirmed symptom description, or an existing partially-filled Debug-Record.
- Optional artefacts: error text, `run_id`, `report.json` /
  `shadow_comparison.json`, failing check log, diff, affected paths.
- Claire de Binare repository checkout (read-only analysis; this skill does not mutate runtime).

## Delegation (reuse, do not rebuild)

Route the deep analysis to the existing read-only CDB subagents and consume
their findings:

| Symptom class | Delegate to |
|---|---|
| CI / pipeline red or flaky | `cdb-ci-debugger` |
| Code / diff / logic defect | `cdb-code-reviewer` |
| Replay / paper / shadow / evidence | `cdb-validation-evidence-analyst` |
| Service boundary / dataflow / design | `cdb-system-architect` |
| Runtime / stack behaviour | `cdb-stack-ops-auditor` |

This skill owns the **synthesis** (symptom vs cause, evidence, fix plan); the
subagents own their domain analysis.

## What it reads (typical)

- `core/replay/determinism.py`, `core/replay/replay_vs_paper_compare.py`,
  `core/replay/shadow_compare.py`, `core/replay/counterfactual.py` - for
  deterministic reproduction and delta evidence.
- `knowledge/governance/SYSTEM_INVARIANTS.md` - invariant references (especially
  INV-011 evidence format; determinism invariants).
- `core/contracts/decision_contract_v1.py` - order-path contract / no-float rule.
- The failing tests, artefacts, or logs named in the symptom.

## Method

1. **Frame:** restate the symptom precisely; set `affected_area` and
   `status_class` (do not conflate Stage vs LR vs CI vs Runtime).
2. **Hypotheses:** list candidate causes; mark each as open.
3. **Eliminate:** for each hypothesis, find confirming or refuting evidence.
   Prefer a deterministic reproduction (`core/replay` runners,
   `determinism.py`) over narrative reasoning.
4. **Evidence:** every retained claim carries an INV-011 artefact reference
   (`git:<sha>:<path>#L..`, `snapshot://..`, `sha256:..`, `run_id:..`).
5. **Root cause:** state the single underlying cause and make the
   `symptom_vs_cause` distinction explicit.
6. **Fix plan:** propose the smallest reversible change. Describe it; do **not**
   implement it here. Note the residual risk.

## Output

Populate / update the Debug-Record fields: `hypotheses`, `evidence`,
`root_cause`, `symptom_vs_cause`, `fix_plan`, `residual_risk`, and
`followup_needed`. Keep unproven fields empty.

## Stop conditions

- Root cause not deterministically provable -> return **INCONCLUSIVE** and name
  the exact evidence still required. Never ship a guessed fix.
- Fix requires scope growth, runtime/DB/MCP mutation, or a boundary crossing
  (LR / live / echtgeld / secrets) -> STOP and hand off; propose only.
- Symptom cannot be reproduced or bounded -> STOP and request a tighter repro.

## Anti-patterns

- Selling a symptom patch as the root cause.
- Narrative instead of artefact-referenced evidence.
- "Green by skip" (muting a check instead of explaining the cause).
- Bundling several unrelated fixes into one plan.
- Conflating status classes (a red CI check is not a runtime outage).

## Standalone value and family fit

Standalone, this is the most-used single debug pass: from a symptom to a proven
cause and a minimal fix plan. Within the debug skill family it is the central
gear - it consumes an optional upstream signal/triage record and leaves a
Debug-Record that a downstream regression-gap or handoff step can pick up. It
never requires another skill to have run first.

## Canon sources

- `docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md` - shared Debug-Record.
- `knowledge/governance/SYSTEM_INVARIANTS.md` - INV-011 evidence format and
  determinism invariants.
- `core/replay/` - deterministic reproduction and comparison runners.
- `.cursor/agents/` - delegated read-only subagents (ci-debugger, code-reviewer,
  validation-evidence-analyst, system-architect, stack-ops-auditor).
