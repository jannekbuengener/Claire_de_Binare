<#
.SYNOPSIS
Enforce the consolidated Claire de Binare repository baseline.

.DESCRIPTION
Validates that the Claire de Binare repository exposes the required local documentation canon
and that key entrypoints no longer use the external historical documentation material as the default path.

.EXAMPLE
.\tools\enforce-root-baseline.ps1

.EXAMPLE
.\tools\enforce-root-baseline.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$RepositoryPath,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $RepositoryPath) {
    $RepositoryPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$requiredDirectories = @(
    'agents',
    'artifacts',
    'config',
    'core',
    'docs',
    'infrastructure',
    'knowledge',
    'scripts',
    'services',
    'tests',
    'tools'
)

$requiredFiles = @(
    'README.md',
    'AGENTS.md',
    'config/repository/root_layout.json',
    'docs/index.md',
    'docs/meta/ROOT_INFORMATION_ARCHITECTURE.md',
    'docs/meta/REPOSITORY_CANON.md',
    'docs/navigation/mcp-navpack/ENTRYPOINTS.yaml',
    'docs/navigation/mcp-navpack/CHEATSHEET.md'
)

$legacyPathPatterns = @(
    '\.\./historical_documentation_source',
    '[A-Za-z]:\\.*historical_documentation_source',
    'canonical agent registry lives in the separate historical documentation material repo',
    'Claire de Binare repository relies on the historical documentation material canonical registry'
)

$legacyScanFiles = @(
    'README.md',
    'AGENTS.md',
    'docs/navigation/mcp-navpack/ENTRYPOINTS.yaml',
    'docs/navigation/mcp-navpack/CHEATSHEET.md',
    'docs/navigation/mcp-navpack/REPO.map.json'
)

Write-Host "Checking consolidated Claire de Binare repository baseline..." -ForegroundColor Cyan
Write-Host "Claire de Binare repository: $RepositoryPath" -ForegroundColor Gray

if (-not (Test-Path $RepositoryPath)) {
    throw "Claire de Binare repository path not found: $RepositoryPath"
}

Push-Location $RepositoryPath
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

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $pythonArguments = @()
    if (-not $pythonCommand) {
        $pythonCommand = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $pythonCommand) {
        $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
        if ($pythonCommand) {
            $pythonArguments += '-3'
        }
    }

    if (-not $pythonCommand) {
        $violations.Add([PSCustomObject]@{
            Type = 'Missing validator runtime'
            Path = 'python'
            Detail = 'Python is required to validate config/repository/root_layout.json.'
        })
    } else {
        $layoutOutput = & $pythonCommand.Source @pythonArguments -m tools.validate_root_layout --repo-root $RepositoryPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            $violations.Add([PSCustomObject]@{
                Type = 'Root layout violation'
                Path = 'config/repository/root_layout.json'
                Detail = ($layoutOutput | Out-String).Trim()
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
    Write-Host "Fix the root-layout contract or restore local canon paths before committing." -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "Dry run only; no changes were made." -ForegroundColor Gray
    }

    exit 1
}
finally {
    Pop-Location
}
