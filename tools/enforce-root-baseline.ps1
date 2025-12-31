<#
.SYNOPSIS
Enforce Working Repo root baseline - prevent governance files from polluting execution-only workspace.

.DESCRIPTION
Validates that the Working Repo root contains ONLY execution/infrastructure files.
Detects governance violations (agent files, documentation, knowledge files) and provides cleanup options.
Supports dry-run mode for validation and live cleanup mode for enforcement.

.EXAMPLE
.\tools\enforce-root-baseline.ps1
.EXAMPLE
.\tools\enforce-root-baseline.ps1 -DryRun
.EXAMPLE
.\tools\enforce-root-baseline.ps1 -AutoCleanup -Force
#>
[CmdletBinding()]
param(
    [string]$WorkingRepoPath = 'D:\Dev\Workspaces\Repos\Claire_de_Binare',
    [string]$DocsHubPath = 'D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs',
    [switch]$DryRun,
    [switch]$AutoCleanup,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Define allowed files in Working Repo root (execution/infrastructure only)
$allowedFiles = @(
    # Build & Infrastructure
    'Makefile', 'docker-compose*.yml', '.dockerignore', 'requirements*.txt', 'pytest.ini'
    
    # Git & CI/CD
    '.gitignore', '.gitlab-ci.yml', '.github', '.gitleaksignore', '.gitmodules', '.secretsignore'
    
    # Configuration (operational, not governance)
    '.mcp.json', 'mcp-config*.toml'
    
    # Project essentials
    'README.md'  # Brief project description, not governance
    
    # PowerShell scripts
    'run-pipeline.ps1'
)

# Define allowed directories (execution/infrastructure only)
$allowedDirectories = @(
    # Core execution
    'services', 'core', 'infrastructure', 'tests', 'tools', 'scripts'
    
    # Git/IDE
    '.git', '.vscode', '.github'
    
    # Cache/temp
    '.ruff_cache', '__pycache__', 'node_modules', '.venv'
    
    # Agent workspaces (if needed for execution)
    '.claude', '.gemini'
)

# Define governance violation patterns
$governanceViolations = @(
    # Agent definition files
    'AGENTS.md', 'CLAUDE.md', 'CODEX.md', 'COPILOT.md', 'GEMINI.md'
    
    # Documentation files (belong in Docs Hub)
    '*_SETUP.md', '*_GUIDE.md', 'QUICKSTART*.md', '*HANDOFF*.md'
    
    # Session/governance files
    'DISCUSSION_*.md', 'FINAL_*.md', 'ISSUE_RESOLUTION*.md'
    
    # Knowledge files
    '*_AUDIT*.md', '*_REPORT*.md', '*_REVIEW*.md'
    
    # Deprecated formats
    '*.txt' # (except requirements.txt which is allowed)
)

Write-Host "🔍 Enforcing Working Repo Root Baseline..." -ForegroundColor Cyan
Write-Host "Working Repo: $WorkingRepoPath" -ForegroundColor Gray

if (-not (Test-Path $WorkingRepoPath)) {
    throw "Working repo path not found: $WorkingRepoPath"
}

Push-Location $WorkingRepoPath
try {
    # Get all items in root
    $rootItems = Get-ChildItem -Force | Where-Object { -not $_.Name.StartsWith('.git/') }
    
    $violations = @()
    $validItems = @()
    
    foreach ($item in $rootItems) {
        $itemName = $item.Name
        $isAllowed = $false
        
        if ($item.PSIsContainer) {
            # Check directories
            $isAllowed = $allowedDirectories -contains $itemName -or 
                        ($allowedDirectories | Where-Object { $itemName -like $_ })
        } else {
            # Check files
            $isAllowed = $allowedFiles -contains $itemName -or 
                        ($allowedFiles | Where-Object { $itemName -like $_ })
            
            # Check for governance violations
            $isViolation = $governanceViolations | Where-Object { $itemName -like $_ }
            if ($isViolation -and $itemName -ne 'requirements.txt' -and $itemName -ne 'requirements-dev.txt') {
                $isAllowed = $false
                $violations += [PSCustomObject]@{
                    Name = $itemName
                    Type = if ($item.PSIsContainer) { 'Directory' } else { 'File' }
                    Reason = 'Governance violation - belongs in Docs Hub'
                    SuggestedLocation = Get-SuggestedLocation $itemName
                }
            }
        }
        
        if ($isAllowed) {
            $validItems += $itemName
        } elseif ($itemName -notin ($violations | ForEach-Object { $_.Name })) {
            $violations += [PSCustomObject]@{
                Name = $itemName
                Type = if ($item.PSIsContainer) { 'Directory' } else { 'File' }
                Reason = 'Not in allowed execution/infrastructure files'
                SuggestedLocation = 'Review if needed or remove'
            }
        }
    }
    
    # Report results
    if ($violations.Count -eq 0) {
        Write-Host "✅ Root baseline verified: CLEAN" -ForegroundColor Green
        Write-Host "   All $($validItems.Count) items are execution/infrastructure compliant" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ Root baseline violated: $($violations.Count) governance violations found" -ForegroundColor Red
        Write-Host ""
        
        foreach ($violation in $violations) {
            Write-Host "  🚫 $($violation.Name) ($($violation.Type))" -ForegroundColor Red
            Write-Host "     Reason: $($violation.Reason)" -ForegroundColor Yellow
            Write-Host "     Suggested: $($violation.SuggestedLocation)" -ForegroundColor Gray
            Write-Host ""
        }
        
        if ($DryRun) {
            Write-Host "🔍 DRY-RUN mode - no changes made" -ForegroundColor Cyan
            exit 1
        }
        
        if ($AutoCleanup -and $Force) {
            Write-Host "🧹 Auto-cleanup enabled - removing violations..." -ForegroundColor Yellow
            # Implementation for auto-cleanup would go here
            Write-Host "⚠️  Auto-cleanup not yet implemented - manual action required" -ForegroundColor Yellow
            exit 1
        } else {
            Write-Host "💡 To fix: Move governance files to Docs Hub or remove them" -ForegroundColor Cyan
            Write-Host "   Run with -DryRun to see violations without changes" -ForegroundColor Gray
            exit 1
        }
    }
}
finally {
    Pop-Location
}

function Get-SuggestedLocation {
    param($fileName)
    
    switch -Wildcard ($fileName) {
        '*AGENTS.md' { return 'Workspace: /agents/AGENTS.md' }
        '*CLAUDE.md' { return 'Workspace: /agents/roles/CLAUDE.md' }
        '*CODEX.md' { return 'Workspace: /agents/roles/CODEX.md' }
        '*COPILOT.md' { return 'Workspace: /agents/roles/COPILOT.md' }
        '*GEMINI.md' { return 'Workspace: /agents/roles/GEMINI.md' }
        '*SETUP*.md' { return 'Docs Hub: /agents/setup/' }
        '*GUIDE*.md' { return 'Docs Hub: /knowledge/operating_rules/' }
        'DISCUSSION_*.md' { return 'Docs Hub: /knowledge/systems/' }
        '*HANDOFF*.md' { return 'Docs Hub: /_legacy_quarantine/sessions/' }
        '*AUDIT*.md' { return 'Docs Hub: /knowledge/reviews/' }
        '*REPORT*.md' { return 'Docs Hub: /knowledge/reviews/' }
        '*.txt' { return 'Docs Hub: /_legacy_quarantine/prompts/' }
        default { return 'Docs Hub: /knowledge/ (review category)' }
    }
}