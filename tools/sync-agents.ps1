<#
.SYNOPSIS
Synchronize agent markdown files between the Docs Hub (canonical) and the Working repo.

.DESCRIPTION
Default behavior pulls the canonical Docs Hub agent files into the Working repo root. Use -Push for the reverse direction (requires -Force). Supports -DryRun to show planned actions without writes, and always backups targets before overwriting.

.EXAMPLE
.\tools\sync-agents.ps1
.EXAMPLE
.\tools\sync-agents.ps1 -DryRun
.EXAMPLE
.\tools\sync-agents.ps1 -Push -Force
.EXAMPLE
.\tools\sync-agents.ps1 -DocsHubPath 'D:\Claire_de_Binare_Docs' -WorkingRepoPath 'D:\Claire_de_Binare' -DryRun
#>
[CmdletBinding()]
param(
    [string]$DocsHubPath = 'C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs',
    [string]$WorkingRepoPath = 'C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare',
    [switch]$Push,
    [switch]$DryRun,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$agentFiles = @('AGENTS.md', 'CLAUDE.md', 'CODEX.md', 'COPILOT.md', 'GEMINI.md')
$sourceBase = if ($Push) { $WorkingRepoPath } else { Join-Path $DocsHubPath 'agents' }
$targetBase = if ($Push) { Join-Path $DocsHubPath 'agents' } else { $WorkingRepoPath }

if ($Push -and -not $Force) {
    Write-Error 'Push mode is blocked without -Force because Docs Hub is canonical.'
    exit 2
}

if (-not (Test-Path -LiteralPath $sourceBase)) {
    Write-Error "Source base path not found: $sourceBase"
    exit 2
}

if (-not (Test-Path -LiteralPath $targetBase)) {
    if ($DryRun) {
        Write-Host "Target base path will be created: $targetBase"
    } else {
        New-Item -ItemType Directory -Path $targetBase -Force | Out-Null
    }
}

if (-not $Push) {
    $missingSources = @($agentFiles | Where-Object { -not (Test-Path -LiteralPath (Join-Path $sourceBase $_)) })
    if ($missingSources.Count -gt 0) {
        Write-Error "Missing source files in Docs Hub: $($missingSources -join ', ')"
        exit 2
    }
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $WorkingRepoPath "tools\_backups\agents\$timestamp"
$backupReady = $false

function Initialize-BackupRoot {
    if (-not $script:backupReady) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $script:backupRoot -Force | Out-Null
        }
        $script:backupReady = $true
    }
}

function Backup-Target {
    param([string]$TargetPath)
    if (-not (Test-Path -LiteralPath $TargetPath)) { return }
    Initialize-BackupRoot
    $destination = Join-Path $script:backupRoot (Split-Path -Leaf $TargetPath)
    Copy-Item -LiteralPath $TargetPath -Destination $destination -Force
}

function FilesEqual {
    param(
        [string]$PathA,
        [string]$PathB
    )

    if (-not (Test-Path -LiteralPath $PathA) -or -not (Test-Path -LiteralPath $PathB)) { return $false }
    $hashA = Get-FileHash -LiteralPath $PathA -Algorithm SHA256
    $hashB = Get-FileHash -LiteralPath $PathB -Algorithm SHA256
    return $hashA.Hash -eq $hashB.Hash
}

function Copy-Bytes {
    param(
        [string]$Source,
        [string]$Destination
    )

    $bytes = [System.IO.File]::ReadAllBytes($Source)
    [System.IO.File]::WriteAllBytes($Destination, $bytes)
}

$summary = New-Object System.Collections.Generic.List[object]
$hasErrors = $false

foreach ($file in $agentFiles) {
    $sourcePath = Join-Path $sourceBase $file
    $targetPath = Join-Path $targetBase $file

    if (-not (Test-Path -LiteralPath $sourcePath)) {
        $summary.Add([pscustomobject]@{ File = $file; Action = 'error'; Reason = 'missing' })
        $hasErrors = $true
        continue
    }

    $targetExists = Test-Path -LiteralPath $targetPath
    $isSame = $targetExists -and (FilesEqual -PathA $sourcePath -PathB $targetPath)

    if ($isSame) {
        $summary.Add([pscustomobject]@{ File = $file; Action = 'skip'; Reason = 'same' })
        continue
    }

    $action = if ($targetExists) { 'update' } else { 'copy' }
    $reason = if ($targetExists) { 'changed' } else { 'missing' }

    if ($DryRun) {
        $summary.Add([pscustomobject]@{ File = $file; Action = $action; Reason = $reason })
        continue
    }

    try {
        $targetDir = Split-Path -Parent $targetPath
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        if ($targetExists) {
            Backup-Target -TargetPath $targetPath
        }
        Copy-Bytes -Source $sourcePath -Destination $targetPath
        $summary.Add([pscustomobject]@{ File = $file; Action = $action; Reason = $reason })
    } catch {
        Write-Error "Failed to sync ${file}: $($_.Exception.Message)"
        $summary.Add([pscustomobject]@{ File = $file; Action = 'error'; Reason = 'failed' })
        $hasErrors = $true
    }
}

if ($DryRun) {
    Write-Host 'Dry run: no files were written or backed up.'
}

Write-Host ''
Write-Host 'Sync summary:'
$summary | Select-Object File, Action, Reason | Format-Table -AutoSize | Out-String | Write-Host

$exitCode = if ($hasErrors) { 1 } else { 0 }
exit $exitCode
