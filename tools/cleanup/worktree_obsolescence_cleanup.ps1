<#
.SYNOPSIS
    Safe local worktree obsolescence cleanup for Claire de Binare.

.DESCRIPTION
    Scans local git worktrees and classifies each entry into:
    - cleanup_ready
    - report_only
    - unclear

    Guardrails:
    - Dry-run by default.
    - Execute mode requires explicit ApprovalIssue.
    - Never deletes the current worktree path.
    - Never performs blind recursive deletion.
    - Designed for local/manual execution only.

.PARAMETER Mode
    dry_run (default) or execute.

.PARAMETER RepoPath
    Path to the local git repository.

.PARAMETER BaseBranch
    Base branch used for merged checks (default: main).

.PARAMETER ReportPath
    JSON report output path.

.PARAMETER ApprovalIssue
    Required in execute mode. Numeric issue id documenting manual approval.

.EXAMPLE
    .\tools\cleanup\worktree_obsolescence_cleanup.ps1

.EXAMPLE
    .\tools\cleanup\worktree_obsolescence_cleanup.ps1 -Mode execute -ApprovalIssue 1589
#>

[CmdletBinding()]
param(
    [ValidateSet("dry_run", "execute")]
    [string]$Mode = "dry_run",
    [string]$RepoPath = ".",
    [string]$BaseBranch = "main",
    [string]$ReportPath = "artifacts\local-worktree-cleanup\report.json",
    [string]$ApprovalIssue = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [string[]]$Args,
        [switch]$AllowFail
    )

    $output = & git -C $ResolvedRepoPath @Args 2>&1
    $exitCode = $LASTEXITCODE
    if (-not $AllowFail -and $exitCode -ne 0) {
        throw "git $($Args -join ' ') failed: $output"
    }
    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = ($output -join "`n")
    }
}

function Normalize-Path {
    param([string]$PathValue)
    try {
        return (Resolve-Path -LiteralPath $PathValue -ErrorAction Stop).Path
    } catch {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
}

function Parse-WorktreeList {
    param([string]$RawText)
    $entries = @()
    $current = [ordered]@{}

    foreach ($line in ($RawText -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            if ($current.Count -gt 0) {
                $entries += [pscustomobject]$current
                $current = [ordered]@{}
            }
            continue
        }

        if ($line.StartsWith("worktree ")) {
            $current["path"] = $line.Substring(9).Trim()
            continue
        }
        if ($line.StartsWith("HEAD ")) {
            $current["head"] = $line.Substring(5).Trim()
            continue
        }
        if ($line.StartsWith("branch ")) {
            $branchRef = $line.Substring(7).Trim()
            $current["branch"] = $branchRef.Replace("refs/heads/", "")
            continue
        }
        if ($line.StartsWith("prunable")) {
            $current["prunable"] = $true
            continue
        }
    }

    if ($current.Count -gt 0) {
        $entries += [pscustomobject]$current
    }

    return $entries
}

$ResolvedRepoPath = Normalize-Path -PathValue $RepoPath
if (-not (Test-Path -LiteralPath $ResolvedRepoPath)) {
    throw "RepoPath not found: $ResolvedRepoPath"
}

$repoCheck = Invoke-Git -Args @("rev-parse", "--is-inside-work-tree") -AllowFail
if ($repoCheck.ExitCode -ne 0 -or $repoCheck.Output.Trim() -ne "true") {
    throw "RepoPath is not a git repository: $ResolvedRepoPath"
}

if ($Mode -eq "execute" -and ($ApprovalIssue -notmatch "^\d+$")) {
    throw "ApprovalIssue must be numeric in execute mode."
}

Write-Host "=== Local Worktree Obsolescence Cleanup ===" -ForegroundColor Cyan
Write-Host "RepoPath: $ResolvedRepoPath"
Write-Host "Mode: $Mode"
Write-Host "BaseBranch: $BaseBranch"

Invoke-Git -Args @("fetch", "origin", "--prune") | Out-Null

$currentPath = Normalize-Path -PathValue $ResolvedRepoPath
$worktreeRaw = Invoke-Git -Args @("worktree", "list", "--porcelain")
$worktrees = Parse-WorktreeList -RawText $worktreeRaw.Output
$candidates = @()
$executedActions = @()
$needsPrune = $false

foreach ($entry in $worktrees) {
    $entryPath = [string]$entry.path
    $entryBranch = if ($entry.PSObject.Properties.Name -contains "branch") { [string]$entry.branch } else { "" }
    $entryPrunable = ($entry.PSObject.Properties.Name -contains "prunable") -and [bool]$entry.prunable
    $entryPathExists = Test-Path -LiteralPath $entryPath
    $normalizedEntryPath = Normalize-Path -PathValue $entryPath
    $isCurrent = ($normalizedEntryPath -eq $currentPath)

    $cleanupState = "report_only"
    $evidence = "No cleanup action required."

    if ($isCurrent) {
        $cleanupState = "report_only"
        $evidence = "Current worktree path is always excluded from cleanup."
    } elseif ($entryPrunable) {
        $cleanupState = "cleanup_ready"
        $evidence = "Git marks this worktree as prunable."
    } elseif (-not $entryPathExists) {
        $cleanupState = "unclear"
        $evidence = "Worktree path is missing but not marked prunable."
    } else {
        $statusResult = & git -C $entryPath status --porcelain 2>&1
        $statusExit = $LASTEXITCODE
        if ($statusExit -ne 0) {
            $cleanupState = "unclear"
            $evidence = "Could not inspect worktree status."
        } elseif (-not [string]::IsNullOrWhiteSpace(($statusResult -join "`n"))) {
            $cleanupState = "unclear"
            $evidence = "Worktree has local modifications and is not safe to remove automatically."
        } elseif ([string]::IsNullOrWhiteSpace($entryBranch)) {
            $cleanupState = "unclear"
            $evidence = "Worktree has no branch metadata; keep for manual inspection."
        } elseif ($entryBranch -in @($BaseBranch, "main", "master")) {
            $cleanupState = "report_only"
            $evidence = "Base/default branch worktree is excluded from cleanup."
        } else {
            $mergeCheck = & git -C $ResolvedRepoPath merge-base --is-ancestor "refs/heads/$entryBranch" "refs/remotes/origin/$BaseBranch" 2>&1
            $mergeExit = $LASTEXITCODE
            if ($mergeExit -eq 0) {
                $cleanupState = "cleanup_ready"
                $evidence = "Worktree is clean and branch is fully merged into origin/$BaseBranch."
            } else {
                $cleanupState = "report_only"
                $evidence = "Branch is not merged into origin/$BaseBranch."
            }
        }
    }

    $candidate = [ordered]@{
        path          = $entryPath
        branch        = $entryBranch
        prunable      = $entryPrunable
        cleanup_state = $cleanupState
        evidence      = $evidence
    }
    $candidates += [pscustomobject]$candidate

    if ($Mode -eq "execute" -and $cleanupState -eq "cleanup_ready") {
        if ($isCurrent) {
            continue
        }
        if ($entryPrunable -and -not $entryPathExists) {
            $needsPrune = $true
            continue
        }
        if ($entryPathExists) {
            Invoke-Git -Args @("worktree", "remove", $entryPath) | Out-Null
            $executedActions += "git worktree remove $entryPath"
        }
    }
}

if ($Mode -eq "execute" -and $needsPrune) {
    Invoke-Git -Args @("worktree", "prune", "--verbose") | Out-Null
    $executedActions += "git worktree prune --verbose"
}

$summary = [ordered]@{
    cleanup_ready = (@($candidates | Where-Object { $_.cleanup_state -eq "cleanup_ready" })).Count
    report_only   = (@($candidates | Where-Object { $_.cleanup_state -eq "report_only" })).Count
    unclear       = (@($candidates | Where-Object { $_.cleanup_state -eq "unclear" })).Count
}

$report = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    repo_path        = $ResolvedRepoPath
    base_branch      = $BaseBranch
    mode             = $Mode
    approval_issue   = $(if ($Mode -eq "execute") { $ApprovalIssue } else { $null })
    boundary_note    = "This script is local/manual by design. Hosted GitHub Actions cannot manage D:\\Dev\\... workstation worktrees."
    summary          = $summary
    candidates       = $candidates
    executed_actions = $executedActions
}

$reportDirectory = Split-Path -Parent $ReportPath
if ($reportDirectory) {
    New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
}
$report | ConvertTo-Json -Depth 8 | Set-Content -Path $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "Summary: cleanup_ready=$($summary.cleanup_ready), report_only=$($summary.report_only), unclear=$($summary.unclear)" -ForegroundColor Yellow
Write-Host "Report written to: $ReportPath"
if ($Mode -eq "dry_run") {
    Write-Host "Dry-run only. Re-run with -Mode execute -ApprovalIssue <issue> to apply cleanup-ready actions." -ForegroundColor Green
} else {
    Write-Host "Execute mode completed. Actions: $($executedActions.Count)" -ForegroundColor Green
}
