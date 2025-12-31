<#
.SYNOPSIS
    Install git hooks for contract validation.
.DESCRIPTION
    Copies tools/hooks/pre-commit.sh into .git/hooks/pre-commit.
.PARAMETER Force
    Overwrite existing pre-commit hook without prompt.
.EXAMPLE
    pwsh -File tools/install_hooks.ps1
.EXAMPLE
    pwsh -File tools/install_hooks.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$gitHooksDir = ".git/hooks"
$hookSource = "tools/hooks/pre-commit.sh"
$preCommitHook = "$gitHooksDir/pre-commit"

if (-not (Test-Path ".git")) {
    throw "Not in a Git repository root. Run from the repo root."
}
if (-not (Test-Path $hookSource)) {
    throw "Hook source not found: $hookSource"
}
if (-not (Test-Path $gitHooksDir)) {
    New-Item -ItemType Directory -Path $gitHooksDir -Force | Out-Null
}

if (Test-Path $preCommitHook -and -not $Force) {
    $response = Read-Host "Pre-commit hook exists. Overwrite? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Install cancelled."
        exit 0
    }
}

Copy-Item -Path $hookSource -Destination $preCommitHook -Force

if (Get-Command chmod -ErrorAction SilentlyContinue) {
    chmod +x $preCommitHook
}

Write-Host "Pre-commit hook installed at $preCommitHook"
