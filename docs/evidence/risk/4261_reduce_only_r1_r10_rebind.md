# #4261 Head-bound R1–R10 Reduce-only Rebind Evidence

## Verdict

`PASS_REDUCE_ONLY_PROVEN_MOCK_SHADOW`

Isolierter Mock-/Shadow-Drill auf dem **exakten** PR-#4262-Head nach Main-Integration
(`#4274`). Belegt erneut `execution_reduce_only_v1` inkl. Zero-Fill-Rejection (R7)
und Restart-Grenze (R9).

## FINAL_EVIDENCE_HEAD

`f1fb2e952c8d9df55dd13a603901f9a49bd43582`

| Feld | Wert |
|------|------|
| Issue | #4261 |
| PR | #4262 |
| Branch | `cloud-cursor/blue-012-wiring-4261-f7b2` |
| Base-SHA (`origin/main`) | `c84bcc217810ec774683bdb89075a68ea6b4915f` |
| Run-ID | `4184_f1fb2e95_20260801T074043Z` |
| Raw-Manifest-SHA256 | `a3380719e1605f4b161e6781b75b9250b1897f9b288b5f4e6e1d5bc272dc2ea0` |
| Maschinenlesbar | [`4261_reduce_only_r1_r10_rebind.json`](./4261_reduce_only_r1_r10_rebind.json) |
| Local run dir | `artifacts/evidence-runs/4261/4184_f1fb2e95_20260801T074043Z/` |

> Hinweis (Canon wie #4184): Dieser Report bindet den **getesteten Code-Commit**
> vor dem Evidence-Packaging-Commit. Ein Verification-Re-Run auf dem Packaging-Tip
> ist Pflicht, bevor Ready-for-Review gesetzt wird.

## Command

```powershell
pwsh -File infrastructure/scripts/run_reduce_only_unwind_drill.ps1 `
  -CommitSha f1fb2e952c8d9df55dd13a603901f9a49bd43582 `
  -EvidenceRoot artifacts/evidence-runs/4261
```

## Safe Mode

| Gate | Wert |
|------|------|
| `DRY_RUN` | `1` (Execution-Runtime verifiziert) |
| `MOCK_TRADING` | `true` (Execution-Runtime verifiziert) |
| `USE_REAL_BALANCE` | `false` |
| BLUE/RED aktiviert | `false` |
| Produktive Credentials | `false` |
| Host-Ports | keine |
| Produktive DB | `false` |
| Exchange / Live-Orders | `false` |

## R1–R10

| Szenario | Vorher | Requested | Submitted | Filled | Nachher | Ergebnis |
|----------|--------|-----------|-----------|--------|---------|----------|
| R1 Long Full Exit | `1` | `1` | `1.0` | `1.0` | `0` | PASS |
| R2 Short Full Exit | `-1` | `1` | `1.0` | `1.0` | `0` | PASS |
| R3 Long Partial | `1` | `1` | `1.0` | `0.4` | `0.60000000` | PASS |
| R4 Short Partial | `-1` | `1` | `1.0` | `0.4` | `-0.60000000` | PASS |
| R5 Oversized Long | `1` | `2` | `1.0` | `1.0` | `0` | PASS / Clamp |
| R6 Oversized Short | `-1` | `2` | `1.0` | `1.0` | `0` | PASS / Clamp |
| R7 Rejection (Zero-Fill) | `1` | `1` | `1.0` | `0.0` | `1.00000000` | PASS |
| R8 Duplicate Result | `1` | `0.4` | `0.4` | `0.4` | `0.60000000` | PASS |
| R9 Restart nach Partial | `-1` | `1` | `1.0` | `0.25` | `-0.75` | PASS |
| R10 Unknown Position | `UNKNOWN` | `1` | `0` | `0.0` | `UNKNOWN` | PASS |

Über alle Szenarien:

- `position_increase_observed=false`
- `side_flip_observed=false`
- kein `NOT_RUN` / `INCOMPLETE` / `SKIPPED`

## Zero-Fill / Fill-Quantity Contract (cross-check)

Unit-Contract auf demselben Head (nicht Runtime-Ersatz):

- `FIELD_MISSING` → Legacy-Fallback nur bei fehlendem Primary-Key
- `FIELD_NULL` / `FIELD_INVALID` → fail-closed
- `FIELD_ZERO` → exakt 0; kein Trade-Insert / keine Positionsmutation
- `FIELD_POSITIVE` → normale Persistenz
- Targeted: **57 passed** (`filled_quantity` + claim/retry + BLUE-012 + unwind suites)

## Cleanup

| Metric | Wert |
|--------|------|
| Containers remaining | `0` |
| Volumes remaining | `0` |
| Networks remaining | `0` |
| Verdict | PASS |

## Stale Evidence Superseded

`docs/evidence/risk/4184_reduce_only_unwind_contract.*` @ `dfb8b040…` bleibt historische
#4184-Evidence und ist **nicht** head-bound für #4261/#4262.

## Non-goals / Session Boundaries

- Kein `cdb-local-ci` Publish
- Kein Merge
- Issue #4261 bleibt OPEN
- LR bleibt **NO-GO**
