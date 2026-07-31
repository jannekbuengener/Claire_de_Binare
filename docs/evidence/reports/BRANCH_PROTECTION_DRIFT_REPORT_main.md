# Branch Protection Drift Report (main)

Timestamp (Europe/Berlin): `2026-07-30T11:50:51+02:00`
Timestamp (UTC): `2026-07-30T09:50:51Z`
Repo: `jannekbuengener/Claire_de_Binare`  
Branch: `main`  
State: **NO DRIFT**

## Inputs

- Baseline file: `docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json`
- Current source: `live gh api`
- Normalization: sorted keys; unordered-list normalization for known set-like arrays; volatile-field stripping: none

## Hashes (SHA256)

- Baseline snapshot hash: `ca793caaf1dc8a3d666749c4eb7d17f97437792d66ce8041f64153ffee103ff2`
- Current snapshot hash: `ca793caaf1dc8a3d666749c4eb7d17f97437792d66ce8041f64153ffee103ff2`

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
