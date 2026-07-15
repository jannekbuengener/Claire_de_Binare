# CI Promotion Candidate Tracking (E2E + Trivy)

## Snapshot
- Local timestamp: `2026-02-19 18:22:13 +01:00`
- UTC timestamp: `2026-02-19T17:22:13Z`
- Data source: GitHub CLI (`gh run list`) on `main`, `limit=20` per workflow.

## Fixed Criteria (deterministic)
Applied rules:
1. `READY`:
   - `current_green_streak >= 10` on `main` for events `push` or `workflow_dispatch`
   - and `failures_last_7d == 0` for the same event set
2. `HOLD`:
   - `failures_last_10_main_runs >= 1`
3. `ROLLBACK_READY`:
   - `failures_last_24h >= 2`
   - and `workflow_file_changes_last_24h == 0`

Status precedence:
1. `ROLLBACK_READY`
2. `READY`
3. `HOLD`

## Current Status
| Workflow/Check | current_green_streak | last_failure_at | promotion_status (READY/HOLD/ROLLBACK_READY) | Evidence links (last 3 runs) |
|---|---:|---|---|---|
| `E2E Happy Path` | 6 | `2026-02-19T14:09:56Z` | `HOLD` | [22191851120](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22191851120)<br>[22191024998](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22191024998)<br>[22190634732](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22190634732) |
| `trivy (kritische CVEs/Supply-Chain)` | 1 | `2026-02-16T19:48:10Z` | `HOLD` | [22191868199](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22191868199)<br>[22075680675](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22075680675)<br>[22075488571](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22075488571) |

## Gate Diagnostics (for transparent derivation)
| Workflow/Check | failures_last_10_main_runs | failures_last_7d | failures_last_24h | workflow_file | workflow_file_changes_last_24h |
|---|---:|---:|---:|---|---:|
| `E2E Happy Path` | 2 | 3 | 2 | `.github/workflows/e2e-happy-path.yaml` | 1 |
| `trivy (kritische CVEs/Supply-Chain)` | 9 | 10 | 0 | `.github/workflows/trivy.yml` | 3 |

Interpretation:
- `E2E Happy Path`: not `READY` (streak < 10 and failures in 7d), not `ROLLBACK_READY` (2 failures in 24h but workflow changed in same 24h window), therefore `HOLD`.
- `trivy`: not `READY` (streak < 10 and failures in 7d), not `ROLLBACK_READY` (no 24h failure cluster), therefore `HOLD`.

## Repro Commands (copy/paste)
```bash
# Raw run data (main, N=20)
gh run list --branch main --workflow "E2E Happy Path" --limit 20 --json databaseId,conclusion,createdAt,displayTitle,url,event
gh run list --branch main --workflow "trivy" --limit 20 --json databaseId,conclusion,createdAt,displayTitle,url,event
```

```powershell
# Deterministic evaluation (same logic as this report)
$now = Get-Date; $window24 = $now.AddHours(-24); $window7 = $now.AddDays(-7)
function To-Utc([object]$v) { if ($v -is [datetime]) { $v.ToUniversalTime() } else { [DateTimeOffset]::Parse($v.ToString()).UtcDateTime } }
$targets = @(
  @{ Workflow='E2E Happy Path'; WorkflowFile='.github/workflows/e2e-happy-path.yaml'; Check='E2E Happy Path' },
  @{ Workflow='trivy'; WorkflowFile='.github/workflows/trivy.yml'; Check='trivy (kritische CVEs/Supply-Chain)' }
)
foreach ($t in $targets) {
  $runs = gh run list --branch main --workflow "$($t.Workflow)" --limit 20 --json databaseId,conclusion,createdAt,displayTitle,url,event | ConvertFrom-Json
  $mainRuns = @($runs | Where-Object { $_.event -in @('push','workflow_dispatch') } | Sort-Object createdAt -Descending)
  $greenStreak = 0; foreach ($r in $mainRuns) { if ($r.conclusion -eq 'success') { $greenStreak++ } else { break } }
  $lastFailure = $mainRuns | Where-Object { $_.conclusion -ne 'success' } | Select-Object -First 1
  $failuresLast10 = @($mainRuns | Select-Object -First 10 | Where-Object { $_.conclusion -ne 'success' }).Count
  $failuresLast24h = @($mainRuns | Where-Object { (To-Utc $_.createdAt) -ge $window24.ToUniversalTime() -and $_.conclusion -ne 'success' }).Count
  $failuresLast7d = @($mainRuns | Where-Object { (To-Utc $_.createdAt) -ge $window7.ToUniversalTime() -and $_.conclusion -ne 'success' }).Count
  $wfChanges24h = @((git log origin/main --since="24 hours ago" --pretty=format:%H -- "$($t.WorkflowFile)") | Where-Object { $_ -and $_.Trim() -ne '' }).Count
  if ($failuresLast24h -ge 2 -and $wfChanges24h -eq 0) { $status = 'ROLLBACK_READY' }
  elseif ($greenStreak -ge 10 -and $failuresLast7d -eq 0) { $status = 'READY' }
  elseif ($failuresLast10 -ge 1) { $status = 'HOLD' }
  else { $status = 'HOLD' }
  [PSCustomObject]@{
    workflow = $t.Workflow
    check = $t.Check
    current_green_streak = $greenStreak
    last_failure_at = $(if ($null -eq $lastFailure) { 'none' } else { (To-Utc $lastFailure.createdAt).ToString('yyyy-MM-ddTHH:mm:ssZ') })
    failures_last_10_main_runs = $failuresLast10
    failures_last_7d = $failuresLast7d
    failures_last_24h = $failuresLast24h
    workflow_file_changes_last_24h = $wfChanges24h
    promotion_status = $status
  }
}
```

## No-Change Statement
- No settings changes performed.
- No workflow logic changes performed.
- This update is report-only.
