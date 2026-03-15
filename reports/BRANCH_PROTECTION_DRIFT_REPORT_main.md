# Branch Protection Drift Report (main)

Timestamp (Europe/Berlin): `2026-03-15T22:16:32+01:00`  
Timestamp (UTC): `2026-03-15T21:16:32Z`  
Repo: `jannekbuengener/Claire_de_Binare`  
Branch: `main`  
State: **NO DRIFT**

## Inputs

- Baseline file: `reports/BRANCH_PROTECTION_BASELINE_main.json`
- Current source: `live gh api`
- Normalization: sorted keys; unordered-list normalization for known set-like arrays; volatile-field stripping: none

## Hashes (SHA256)

- Baseline snapshot hash: `e987fc8d7369348df2bdfaa1fbc964029af693254b7a243a6c9a429eb4f32b28`
- Current snapshot hash: `e987fc8d7369348df2bdfaa1fbc964029af693254b7a243a6c9a429eb4f32b28`

## Drift Summary

- none

## Unified Diff (normalized JSON)

```diff
(no diff)
```

## Manual Apply Commands (maintainer only, never auto-executed)

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection > reports/BRANCH_PROTECTION_CURRENT_main.json
gh api --method PUT repos/jannekbuengener/Claire_de_Binare/branches/main/protection --input reports/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json
gh api --method DELETE repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_signatures
```

Safety note: this checker is read-only and does not run apply commands.
