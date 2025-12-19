<#
.SYNOPSIS
Install Git hooks for Working Repo governance enforcement.

.DESCRIPTION
Sets up pre-commit hook to enforce root baseline compliance.
Prevents commits that violate the "Execution Only" principle.

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

Write-Host "🔧 Installing Git hooks for governance enforcement..." -ForegroundColor Cyan

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
# Pre-commit hook: Working Repo root baseline enforcement
# Prevents commits that violate the "Execution Only" principle

echo "🔍 Checking Working Repo root baseline compliance..."

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
    echo "🚫 COMMIT BLOCKED: Root baseline violation detected!"
    echo ""
    echo "📋 Common violations:"
    echo "   • Agent files: AGENTS.md, CLAUDE.md, CODEX.md, etc."
    echo "   • Documentation: *_SETUP.md, *_GUIDE.md, QUICKSTART*.md"
    echo "   • Knowledge files: *_AUDIT.md, *_REPORT.md, *_REVIEW.md"
    echo "   • Session files: DISCUSSION_*.md, FINAL_*.md"
    echo "   • Governance dirs: docs/, knowledge/, governance/, agents/"
    echo "   • Deprecated: *.txt files (except requirements.txt)"
    echo ""
    echo "🎯 Working Repo Rule: EXECUTION ONLY"
    echo "   ✅ Allowed: services/, tools/, scripts/, infrastructure/"
    echo "   ✅ Allowed: Makefile, docker-compose.yml, .gitlab-ci.yml"
    echo "   ❌ Forbidden: Governance, knowledge, documentation files"
    echo ""
    echo "📚 Migration Guide:"
    echo "   • Agent files → Workspace: /agents/roles/"
    echo "   • Documentation → Docs Hub: Claire_de_Binare_Docs/agents/setup/"
    echo "   • Knowledge → Docs Hub: Claire_de_Binare_Docs/knowledge/"
    echo "   • Session logs → Docs Hub: Claire_de_Binare_Docs/_legacy_quarantine/sessions/"
    echo ""
    echo "🔧 To fix:"
    echo "   1. Move governance files to canonical locations"
    echo "   2. Run: pwsh tools/enforce-root-baseline.ps1 -DryRun"
    echo "   3. Verify: pwsh tools/enforce-root-baseline.ps1"
    echo "   4. Retry commit after cleanup"
    echo ""
    echo "⚠️  Bypass (NOT recommended): git commit --no-verify"
    
    exit 1
fi

echo "✅ Root baseline compliance verified - commit allowed"
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
Write-Host "   Purpose: Enforces 'Execution Only' principle" -ForegroundColor Gray
Write-Host ""
Write-Host "🧪 Test the hook:" -ForegroundColor Cyan
Write-Host "   pwsh tools/enforce-root-baseline.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "🚫 To bypass (emergency only):" -ForegroundColor Yellow
Write-Host "   git commit --no-verify" -ForegroundColor Gray