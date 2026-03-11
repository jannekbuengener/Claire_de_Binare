<#
.SYNOPSIS
Enforce the consolidated Working Repo baseline.

.DESCRIPTION
Validates that the Working Repo exposes the required local documentation canon
and that key entrypoints no longer use the external Docs Hub as the default path.

.EXAMPLE
.\tools\enforce-root-baseline.ps1

.EXAMPLE
.\tools\enforce-root-baseline.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$WorkingRepoPath = 'D:\Dev\Workspaces\Repos\Claire_de_Binare',
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$requiredDirectories = @(
    'agents',
    'docs',
    'governance',
    'knowledge',
    'mcp_navpack_working_repo',
    'services',
    'infrastructure',
    'tests',
    'tools',
    'scripts'
)

$requiredFiles = @(
    'README.md',
    'AGENTS.md',
    'docs/index.md',
    'docs/meta/WORKING_REPO_CANON.md',
    'mcp_navpack_working_repo/ENTRYPOINTS.yaml',
    'mcp_navpack_working_repo/CHEATSHEET.md'
)

$legacyPathPatterns = @(
    '\.\./Claire_de_Binare_Docs',
    'D:\\Dev\\Workspaces\\Repos\\Claire_de_Binare_Docs',
    'canonical agent registry lives in the separate Docs Hub repo',
    'Working Repo relies on the Docs Hub canonical registry'
)

$legacyScanFiles = @(
    'README.md',
    'AGENTS.md',
    'mcp_navpack_working_repo/ENTRYPOINTS.yaml',
    'mcp_navpack_working_repo/CHEATSHEET.md',
    'mcp_navpack_working_repo/DOCS_HUB.pointer.md'
)

Write-Host "Checking consolidated Working Repo baseline..." -ForegroundColor Cyan
Write-Host "Working Repo: $WorkingRepoPath" -ForegroundColor Gray

if (-not (Test-Path $WorkingRepoPath)) {
    throw "Working repo path not found: $WorkingRepoPath"
}

Push-Location $WorkingRepoPath
try {
    $violations = [System.Collections.Generic.List[object]]::new()

    foreach ($relativePath in $requiredDirectories) {
        if (-not (Test-Path $relativePath -PathType Container)) {
            $violations.Add([PSCustomObject]@{
                Type = 'Missing directory'
                Path = $relativePath
                Detail = 'Required local canon directory is missing.'
            })
        }
    }

    foreach ($relativePath in $requiredFiles) {
        if (-not (Test-Path $relativePath -PathType Leaf)) {
            $violations.Add([PSCustomObject]@{
                Type = 'Missing file'
                Path = $relativePath
                Detail = 'Required local canon entrypoint is missing.'
            })
        }
    }

    foreach ($relativePath in $legacyScanFiles) {
        if (-not (Test-Path $relativePath -PathType Leaf)) {
            continue
        }

        $content = Get-Content -Path $relativePath -Raw -Encoding UTF8
        foreach ($pattern in $legacyPathPatterns) {
            if ($content -match $pattern) {
                $violations.Add([PSCustomObject]@{
                    Type = 'Legacy split reference'
                    Path = $relativePath
                    Detail = "Matched pattern: $pattern"
                })
            }
        }
    }

    if ($violations.Count -eq 0) {
        Write-Host "PASS: consolidated baseline verified" -ForegroundColor Green
        exit 0
    }

    Write-Host "FAIL: consolidated baseline violations found" -ForegroundColor Red
    Write-Host ""
    foreach ($violation in $violations) {
        Write-Host " - [$($violation.Type)] $($violation.Path)" -ForegroundColor Red
        Write-Host "   $($violation.Detail)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Fix by restoring local canon paths and removing external Docs-Hub defaults from key entrypoints." -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "Dry run only; no changes were made." -ForegroundColor Gray
    }

    exit 1
}
finally {
    Pop-Location
}
