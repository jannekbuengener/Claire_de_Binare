# Branch Protection Drift Report (main)

Timestamp (Europe/Berlin): `2026-10-18T12:04:10+02:00`
Timestamp (UTC): `2026-10-18T10:04:10Z`
Repo: `jannekbuengener/Claire_de_Binare`  
Branch: `main`  
State: **NO DRIFT**

## Inputs

- Baseline file: `docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json`
- Current source: `live gh api`
- Normalization: sorted keys; unordered-list normalization for known set-like arrays; GitHub repository casing normalized only on known branch-protection URL fields; volatile-field stripping: none

## Hashes (SHA256)

- Baseline snapshot hash: `84a663b7401f1d66bc3cd6e2fa90d853ff4beb80c81c5e4b84b755aeb43119c8`
- Current snapshot hash: `84a663b7401f1d66bc3cd6e2fa90d853ff4beb80c81c5e4b84b755aeb43119c8`

## Drift Summary

- none

## Unified Diff (normalized JSON)

```diff
(no diff)
```

## Manual Apply Commands (maintainer only, never auto-executed)

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection > artifacts/reports/governance/BRANCH_PROTECTION_CURRENT_main.json
gh api --method PUT repos/jannekbuengener/Claire_de_Binare/branches/main/protection --input docs/evidence/reports/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json
gh api --method DELETE repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_signatures
```

Safety note: this checker is read-only and does not run apply commands.
