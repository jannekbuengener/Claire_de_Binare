# Main Ruleset Drift Report (compatibility artifact: BRANCH_PROTECTION_*)

Timestamp (Europe/Berlin): `2026-10-18T14:06:17+02:00`
Timestamp (UTC): `2026-10-18T12:06:17Z`
Repo: `jannekbuengener/Claire_de_Binare`
Branch: `main`
State: **NO DRIFT**

## Inputs

- Baseline file: `docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json`
- Current source: `live gh api`
- Normalization: sorted keys; unordered-list normalization for known set-like arrays; rules/rule-parameter set normalization; GitHub-generated ruleset metadata stripped

## Hashes (SHA256)

- Baseline snapshot hash: `cf3cc293252120bee885c28bcf860e1a8ba49a2584ae78bcd98ac3cc2bff907a`
- Current snapshot hash: `cf3cc293252120bee885c28bcf860e1a8ba49a2584ae78bcd98ac3cc2bff907a`

## Drift Summary

- none

## Unified Diff (normalized JSON)

```diff
(no diff)
```

## Manual Apply Commands (maintainer only, never auto-executed)

```bash
gh api repos/jannekbuengener/Claire_de_Binare/rulesets/11617228 > artifacts/reports/governance/BRANCH_PROTECTION_CURRENT_main.json
gh api --method PUT repos/jannekbuengener/Claire_de_Binare/rulesets/11617228 --input docs/evidence/reports/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json
```

Safety note: this checker is read-only and does not run apply commands.
