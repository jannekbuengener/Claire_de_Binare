<#
.SYNOPSIS
Install Git hooks for Working Repo baseline enforcement.

.DESCRIPTION
Sets up pre-commit hook to enforce the consolidated repo baseline.
Prevents commits that keep the old split-repo defaults alive in key entrypoints.

.EXAMPLE
.\tools\install-git-hooks.ps1
.EXAMPLE
.\tools\install-git-hooks.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$gitHooksDir = ".git/hooks"
$preCommitHook = "$gitHooksDir/pre-commit"

Write-Host "🔧 Installing Git hooks for consolidated baseline enforcement..." -ForegroundColor Cyan

# Check if .git directory exists
if (-not (Test-Path ".git")) {
    throw "Not in a Git repository root. Run from Working Repo root directory."
}

# Check if hooks directory exists
if (-not (Test-Path $gitHooksDir)) {
    New-Item -ItemType Directory -Path $gitHooksDir -Force | Out-Null
    Write-Host "   Created hooks directory: $gitHooksDir" -ForegroundColor Gray
}

# Check if pre-commit hook already exists
if (Test-Path $preCommitHook -and -not $Force) {
    $response = Read-Host "Pre-commit hook already exists. Overwrite? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "   Installation cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# Create pre-commit hook content
$hookContent = @'
#!/bin/sh
# Pre-commit hook: consolidated Working Repo baseline enforcement
# Prevents commits that reintroduce split-repo defaults in key entrypoints

echo "Checking consolidated Working Repo baseline..."

# Run the PowerShell baseline enforcement script
if command -v pwsh >/dev/null 2>&1; then
    pwsh -File "tools/enforce-root-baseline.ps1"
elif command -v powershell >/dev/null 2>&1; then
    powershell -File "tools/enforce-root-baseline.ps1"
else
    echo "❌ PowerShell not found - cannot validate root baseline"
    echo "💡 Install PowerShell or run manually: pwsh tools/enforce-root-baseline.ps1"
    exit 1
fi

baseline_result=$?

if [ $baseline_result -ne 0 ]; then
    echo ""
    echo "🚫 COMMIT BLOCKED: Consolidated baseline violation detected!"
    echo ""
    echo "📋 Common violations:"
    echo "   • Missing local canon dirs such as agents/, docs/, or knowledge/"
    echo "   • Missing key entrypoints such as docs/meta/WORKING_REPO_CANON.md"
    echo "   • Stale references to the retired external docs repo in navigation or guards"
    echo ""
    echo "🎯 Working Repo Rule: LOCAL CANON"
    echo "   ✅ Active docs live in this repo"
    echo "   ✅ Root pointers must resolve internally"
    echo "   ❌ External Docs-Hub paths are legacy-only"
    echo ""
    echo "📚 Migration Guide:"
    echo "   • Canon matrix → docs/meta/WORKING_REPO_CANON.md"
    echo "   • Agent registry → agents/AGENTS.md"
    echo "   • Governance canon → knowledge/governance/"
    echo "   • Archive-only legacy docs → docs/archive/docs_hub_snapshot/"
    echo ""
    echo "🔧 To fix:"
    echo "   1. Restore local canon files and directories"
    echo "   2. Run: pwsh tools/enforce-root-baseline.ps1 -DryRun"
    echo "   3. Verify: pwsh tools/enforce-root-baseline.ps1"
    echo "   4. Retry commit after cleanup"
    echo ""
    echo "⚠️  Bypass (NOT recommended): git commit --no-verify"
    
    exit 1
fi

echo "✅ Consolidated baseline verified - commit allowed"
exit 0
'@

# Write hook file
Set-Content -Path $preCommitHook -Value $hookContent -Encoding UTF8

# Make executable (cross-platform)
if ($IsLinux -or $IsMacOS) {
    chmod +x $preCommitHook
} else {
    # On Windows, set executable attribute
    $file = Get-Item $preCommitHook
    $file.Attributes = $file.Attributes -bor [System.IO.FileAttributes]::ReadOnly
}

Write-Host "✅ Pre-commit hook installed successfully!" -ForegroundColor Green
Write-Host "   Location: $preCommitHook" -ForegroundColor Gray
Write-Host "   Purpose: Enforces the local-canon baseline" -ForegroundColor Gray
Write-Host ""
Write-Host "🧪 Test the hook:" -ForegroundColor Cyan
Write-Host "   pwsh tools/enforce-root-baseline.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "🚫 To bypass (emergency only):" -ForegroundColor Yellow
Write-Host "   git commit --no-verify" -ForegroundColor Gray
