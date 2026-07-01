<!--
Canonical Skill Source: docs/skills/cdb-regression-gap/SKILL.md
Surface: cursor
Sync Status: mirrored-from-canon
Last Verified: 2026-07-02
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-regression-gap
description: >
  For a confirmed or plausible defect, identify which concrete test, regression
  guard, or evidence is missing so a later fix can be validated and the defect
  cannot silently return. Use after a root cause (or a strong defect suspicion)
  when the question is "what protection is missing", not "what is the cause".
  This skill does not fix the defect and does not write tests; it names the gap,
  its priority, and the minimum validation, then routes onward. Not for planning
  tests of a new change (cdb-test-first) and not for choosing validation depth
  (cdb-shadow-validation).
disable-model-invocation: true
---

# CDB Regression-Gap Skill

For a confirmed or plausible defect, make the MISSING protection visible: which
test, regression guard, or evidence is absent so that a future fix can be
validated and the defect cannot silently return. This skill is a thin router: it
does not repair the defect and it does not write tests - it names the gap, sets a
priority, states the minimum validation, and hands off.

Standalone: it works from a defect description, bug report, PR comment, or red CI
signal. Composable: if a Debug-Record
(`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`) already exists, fill its
`test_gap` and evidence fields instead of starting over.

## When to trigger

- a confirmed root cause needs a durable regression guard
- a plausible defect where you must know what coverage is missing
- a red or newly-fixed test that lacks a protecting invariant
- a replay-vs-paper deviation with no protecting comparison
- nondeterminism / flake with no guard
- a contract break or system-design gap without coverage

## Delimitation (what this skill is not)

- vs `cdb-root-cause`: root-cause finds and proves the cause; regression-gap
  assumes the cause or defect is (plausibly) known and asks what protection is
  missing.
- vs `cdb-test-first`: test-first plans tests forward for a planned change and
  owns the 15 test types plus the 15 metadata fields; regression-gap works
  backward from a defect to the missing guard and reuses that vocabulary.
- vs `cdb-shadow-validation`: shadow-validation chooses the validation depth
  bucket for a change; regression-gap names the concrete missing test or evidence
  and a minimum validation, then defers depth selection to shadow-validation.

## Method

1. State the defect and, if known, its root cause; keep status classes distinct
   (do not read a board stage as an LR verdict).
2. Classify the gap: `missing_test_type`, `missing_evidence_type`,
   `affected_area`, `protected_invariant`, `target_path_or_unknown`, `priority`.
3. Name the missing evidence needed for fix confidence (INV-011 artefact form
   where applicable).
4. Recommend the minimum validation before and after a future fix; defer the
   depth bucket to `cdb-shadow-validation` and the test type plus metadata to
   `cdb-test-first`.
5. State `risk_if_skipped` honestly and set `next_recommended_step`.

Do not design a whole suite; name the single most important missing guard.

## Test-type reference

Map `missing_test_type` to the canonical CDB test taxonomy in
`docs/skills/cdb-test-first/SKILL.md` (15 test types) and its 15-field test
metadata; prefer the narrowest type that actually protects the invariant.

## Routing

| Gap class | Route to (skill) | Route to (subagent) |
|---|---|---|
| Cause not yet proven | `cdb-root-cause` | `cdb-code-reviewer` |
| Missing unit / contract / regression test | `cdb-test-first` | `cdb-code-reviewer` |
| Missing replay / shadow / evidence | `cdb-shadow-validation` | `cdb-validation-evidence-analyst` |
| Red / flaky CI guard | `cdb-ci-cd-guard` | `cdb-ci-debugger` |
| Contract / invariant / closure question | `cdb-contract-evidence-gatekeeper` | `cdb-governance-gatekeeper` |
| Service boundary / design gap | - | `cdb-system-architect` |
| Entry framing (unclear signal) | `cdb-symptom-triage` | - |

## Output

Populate the Debug-Record (`docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md`),
elaborating `test_gap` into a structured block (additive per the contract section
4.3 / 8):

```yaml
test_gap:
  missing_test_type: unit | contract | regression | integration | replay | shadow | smoke | e2e | metadata | unknown
  target_path_or_unknown: <expected test path or unknown>
  protects_against: <bug / gap / invariant this guard protects>
  protected_invariant_or_rule: <INV / RC / rule_ref if known>
  reason_missing: <why current coverage or evidence is insufficient>
  priority: P0 | P1 | P2
missing_evidence:
  type: log | repro | fixture | artifact | trace | report | github_check | shadow_comparison | run_id | config_hash | unknown
  required_for_fix_confidence: true
  reason: <why this evidence is required>
validation_recommendation:
  minimum_before_fix: []
  minimum_after_fix: []
risk_if_skipped: <clear consequence>
next_recommended_step: fix-plan later | root-cause first | shadow-validation | test-first
```

Leave anything you cannot yet support empty.

## Stop conditions

- Cause not plausible enough to name a guard -> route to `cdb-root-cause` first.
- Defect unbounded or unreproducible -> stop and request a tighter defect.
- Required test depth unclear -> defer to `cdb-shadow-validation`, do not guess.
- A runtime / DB / MCP / trading boundary appears -> stop and route to gated
  handling.
- Scope grows into writing the test or a multi-guard redesign -> stop.

## Anti-patterns

- Redesigning the whole test suite instead of naming one guard.
- Bundling several unrelated guards into one gap.
- Selling synthetic or planned evidence as real closure.
- Writing the test instead of describing the gap.
- Reading a board stage as an LR verdict, or a red CI check as a runtime outage.

## Standalone value and family fit

Standalone, this is the "what protection is missing and how bad is it" pass for
any defect. In the debug skill family it is gear 3: it consumes a plausible cause
or a Debug-Record, records the missing guard and the minimum validation, and
routes to `cdb-test-first` / `cdb-shadow-validation` - leaving a later
`cdb-debug-handoff` (not yet built) a clean, evidenced gap. It never requires
another skill to have run first.

## Canon sources

- `docs/skills/_debug_record/DEBUG_RECORD_CONTRACT.md` - shared Debug-Record.
- `docs/skills/cdb-root-cause/SKILL.md` - upstream cause isolation.
- `docs/skills/cdb-test-first/SKILL.md` - 15 test types plus metadata.
- `docs/skills/cdb-shadow-validation/SKILL.md` - validation depth selection.
- `knowledge/governance/SYSTEM_INVARIANTS.md` - INV-011 evidence format.
