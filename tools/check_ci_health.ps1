#Requires -Version 5.1
<#
.SYNOPSIS
    Checks recent GitHub Actions runs for CI health and billing-related failures.
.DESCRIPTION
    Uses gh CLI to list recent workflow runs, summarizes success/failure ratio,
    and scans failed runs for billing/spending limit indicators.
.PARAMETER Limit
    Number of recent workflow runs to inspect.
.PARAMETER Verbose
    Show per-run details and billing scan output.
.EXAMPLE
    pwsh -File tools/check_ci_health.ps1
.EXAMPLE
    pwsh -File tools/check_ci_health.ps1 -Limit 50 -Verbose
#>
param(
    [int]$Limit = 10,
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($text) { Write-Host "`n== $text ==" -ForegroundColor Blue }
function Write-Info($text)    { Write-Host "[INFO]  $text" -ForegroundColor Cyan }
function Write-Success($text) { Write-Host "[OK]    $text" -ForegroundColor Green }
function Write-Warning($text) { Write-Host "[WARN]  $text" -ForegroundColor Yellow }
function Write-Failure($text) { Write-Host "[FAIL]  $text" -ForegroundColor Red }

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Failure "Missing required command: $name"
        exit 2
    }
}

Require-Command gh

Write-Section "CI Health Check"
Write-Info "Inspecting last $Limit workflow runs..."

$auth = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Failure "gh auth status failed. Run 'gh auth login' first."
    exit 2
}

$runJson = gh run list --limit $Limit --json databaseId,workflowName,displayTitle,status,conclusion,createdAt 2>$null
if ($LASTEXITCODE -ne 0 -or -not $runJson) {
    Write-Failure "Failed to fetch workflow runs."
    exit 2
}

$runs = $runJson | ConvertFrom-Json
if (-not $runs -or $runs.Count -eq 0) {
    Write-Warning "No workflow runs found."
    exit 1
}

$completed = $runs | Where-Object { $_.status -eq 'completed' }
$success = $completed | Where-Object { $_.conclusion -eq 'success' }
$failed = $completed | Where-Object { $_.conclusion -ne 'success' }

$billingPattern = '(?i)billing|spending|payment|account.*restricted'
$billingFindings = @()

foreach ($run in $failed) {
    try {
        $details = gh run view $run.databaseId 2>$null
        if ($details -match $billingPattern) {
            $billingFindings += $run
            if ($Verbose) {
                Write-Warning "Billing signal in run $($run.databaseId) ($($run.workflowName))"
            }
        } elseif ($Verbose) {
            Write-Info "Failed run $($run.databaseId): $($run.workflowName) - $($run.displayTitle)"
        }
    } catch {
        if ($Verbose) {
            Write-Warning "Unable to inspect run $($run.databaseId)"
        }
    }
}

Write-Section "CI Health Report"
Write-Info "Total Runs: $($runs.Count)"
Write-Info "Completed: $($completed.Count)"
Write-Success "Success: $($success.Count)"
if ($failed.Count -gt 0) {
    Write-Warning "Failed: $($failed.Count)"
} else {
    Write-Success "Failed: 0"
}

if ($billingFindings.Count -gt 0) {
    Write-Failure "Billing issues detected in $($billingFindings.Count) run(s)."
}

$failureRatio = if ($runs.Count -gt 0) { [Math]::Round($failed.Count / $runs.Count, 2) } else { 1 }
Write-Info "Failure ratio: $failureRatio"

$degraded = ($failureRatio -gt 0.5) -or ($billingFindings.Count -gt 0)
if ($degraded) {
    Write-Failure "CI is degraded (>50% failure rate or billing issues)."
    exit 1
}

Write-Success "CI is healthy."
exit 0
