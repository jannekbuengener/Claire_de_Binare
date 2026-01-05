# Bulk Issue Labeling Script für Claire de Binare
# Systematisches Labeling aller offenen Issues basierend auf Analyse

param(
    [string]$GitHubToken = $env:GITHUB_TOKEN,
    [string]$Owner = "jannekbuengener", 
    [string]$Repo = "Claire_de_Binare",
    [switch]$DryRun = $false,
    [int[]]$IssueNumbers = @()
)

if (-not $GitHubToken) {
    Write-Error "GitHub Token required. Set GITHUB_TOKEN environment variable or pass -GitHubToken parameter"
    exit 1
}

$headers = @{
    'Authorization' = "Bearer $GitHubToken"
    'Accept' = 'application/vnd.github.v3+json'
    'User-Agent' = 'Claire-de-Binare-Labeling-Script'
}

# Umfassende Issue-Kategorisierung basierend auf Analyse
$labelingRules = @{
    # ML/Research Issues (192-200)
    "ML_Research" = @{
        IssueNumbers = @(192, 193, 194, 195, 196, 197, 198, 199, 200)
        Labels = @("type:research", "scope:core", "prio:should")
        TitlePatterns = @("ML Foundation", "Machine Learning", "Deep Research", "Feature Engineering")
    }
    
    # Stabilization Issues (156-160)
    "Stabilization" = @{
        IssueNumbers = @(156, 157, 158, 159, 160)
        Labels = @("prio:must", "stabilization", "type:bug")
        TitlePatterns = @("STABILIZATION", "Infrastructure Emergency", "Code Reality", "Governance")
    }
    
    # Security Issues (97-106)
    "Security" = @{
        IssueNumbers = @(97, 98, 99, 100, 101, 102, 103, 104, 105, 106)
        Labels = @("security", "scope:security", "milestone:m8", "type:security")
        TitlePatterns = @("Security", "Hardening", "Penetration", "OWASP", "Trivy")
    }
    
    # Trading Core Issues (171-187) 
    "Trading" = @{
        IssueNumbers = @(171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188)
        Labels = @("prio:must", "scope:core", "trading")
        TitlePatterns = @("Trading", "MEXC", "Live Trading", "Paper Trading", "Execution")
    }
    
    # Testing Issues (91-95, 113)
    "Testing" = @{
        IssueNumbers = @(91, 92, 93, 94, 95, 113)
        Labels = @("testing", "type:testing", "prio:should", "milestone:m7")
        TitlePatterns = @("E2E", "Test", "Performance", "Resilience")
    }
    
    # Documentation Issues (108, 117-120)
    "Documentation" = @{
        IssueNumbers = @(108, 117, 118, 119, 120)
        Labels = @("type:docs", "scope:docs", "prio:should")
        TitlePatterns = @("docs:", "Documentation", "Guide", "Template")
    }
    
    # Infrastructure Issues (114, 121-123, 135, 139, 140)
    "Infrastructure" = @{
        IssueNumbers = @(114, 121, 122, 123, 135, 139, 140)
        Labels = @("infrastructure", "scope:infra", "prio:should")
        TitlePatterns = @("Docker", "CI/CD", "GitHub", "DevOps")
    }
    
    # Governance Issues (143, 150, 163, 165-167)
    "Governance" = @{
        IssueNumbers = @(143, 150, 163, 165, 166, 167)
        Labels = @("governance", "type:docs", "prio:should")
        TitlePatterns = @("GOVERNANCE", "Canonical", "Violations", "Compliance")
    }
    
    # Monitoring Issues (96)
    "Monitoring" = @{
        IssueNumbers = @(96)
        Labels = @("monitoring", "scope:infra", "prio:should")
        TitlePatterns = @("Grafana", "Monitoring", "Dashboards")
    }
    
    # Workflow/Automation Issues (144, 145, 146, 169, 170)
    "Automation" = @{
        IssueNumbers = @(144, 145, 146, 169, 170)
        Labels = @("github-actions", "type:feature", "prio:should")
        TitlePatterns = @("AUTOMATION", "Workflow", "Smart", "PR")
    }
    
    # Analysis/Research Issues (147, 151)
    "Analysis" = @{
        IssueNumbers = @(147, 151)
        Labels = @("type:research", "prio:should")
        TitlePatterns = @("AI-RESEARCH", "Analysis", "Research")
    }
    
    # CDB Hygiene Issues (136-139)
    "Hygiene" = @{
        IssueNumbers = @(136, 137, 138)
        Labels = @("type:docs", "prio:nice", "governance")
        TitlePatterns = @("CDB-HYGIENE", "Migrate", "Remove")
    }
}

# Agent-spezifische Labels
$agentRules = @{
    "agent:codex" = @(113, 116, 136, 137, 138, 139, 148, 149, 156, 175)
    "agent:copilot" = @(114, 118, 119, 120, 121, 122, 123, 124, 144, 145)
    "agent:gemini" = @(110, 115, 117, 143, 150, 151, 157, 165, 166)  
    "agent:claude" = @(107, 108, 109, 128, 158, 167)
}

function Get-AllOpenIssues {
    try {
        $url = "https://api.github.com/repos/$Owner/$Repo/issues?state=open&per_page=100"
        $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
        return $response | Where-Object { $_.pull_request -eq $null }
    } catch {
        Write-Error "Failed to fetch issues: $($_.Exception.Message)"
        return @()
    }
}

function Add-LabelsToIssue {
    param(
        [int]$IssueNumber,
        [string[]]$Labels
    )
    
    if ($DryRun) {
        Write-Host "DRY RUN: Would add labels [$($Labels -join ', ')] to issue #$IssueNumber" -ForegroundColor Yellow
        return $true
    }
    
    try {
        $url = "https://api.github.com/repos/$Owner/$Repo/issues/$IssueNumber/labels"
        $body = @{ labels = $Labels } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Post -Body $body -ContentType "application/json"
        Write-Host "✅ Added labels [$($Labels -join ', ')] to issue #$IssueNumber" -ForegroundColor Green
        return $true
    } catch {
        Write-Error "❌ Failed to add labels to issue #$IssueNumber: $($_.Exception.Message)"
        return $false
    }
}

function Get-ExistingLabels {
    param([int]$IssueNumber)
    
    try {
        $url = "https://api.github.com/repos/$Owner/$Repo/issues/$IssueNumber"
        $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
        return $response.labels.name
    } catch {
        Write-Warning "Could not fetch existing labels for issue #$IssueNumber"
        return @()
    }
}

# Main execution
Write-Host "🏷️  Claire de Binare Bulk Issue Labeling" -ForegroundColor Cyan
Write-Host "Repository: $Owner/$Repo" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Get issues to process
$issuesToProcess = @()
if ($IssueNumbers.Count -gt 0) {
    $issuesToProcess = $IssueNumbers
    Write-Host "Processing specified issues: $($IssueNumbers -join ', ')" -ForegroundColor Gray
} else {
    $openIssues = Get-AllOpenIssues
    $issuesToProcess = $openIssues.number
    Write-Host "Processing all $($issuesToProcess.Count) open issues" -ForegroundColor Gray
}

$totalProcessed = 0
$totalLabeled = 0

# Apply category-based rules
foreach ($category in $labelingRules.Keys) {
    $rule = $labelingRules[$category]
    Write-Host "`n📋 Processing $category issues..." -ForegroundColor Cyan
    
    foreach ($issueNumber in $rule.IssueNumbers) {
        if ($issuesToProcess -contains $issueNumber) {
            $totalProcessed++
            
            # Get existing labels
            $existingLabels = Get-ExistingLabels -IssueNumber $issueNumber
            
            # Determine new labels needed
            $newLabels = $rule.Labels | Where-Object { $existingLabels -notcontains $_ }
            
            if ($newLabels.Count -gt 0) {
                Write-Host "  Issue #$issueNumber needs labels: $($newLabels -join ', ')" -ForegroundColor Gray
                
                if (Add-LabelsToIssue -IssueNumber $issueNumber -Labels $newLabels) {
                    $totalLabeled++
                }
            } else {
                Write-Host "  Issue #$issueNumber already properly labeled" -ForegroundColor Green
            }
        }
    }
}

# Apply agent-specific labels
Write-Host "`n👥 Processing agent assignments..." -ForegroundColor Cyan
foreach ($agentLabel in $agentRules.Keys) {
    $issueNumbers = $agentRules[$agentLabel]
    
    foreach ($issueNumber in $issueNumbers) {
        if ($issuesToProcess -contains $issueNumber) {
            $existingLabels = Get-ExistingLabels -IssueNumber $issueNumber
            
            if ($existingLabels -notcontains $agentLabel) {
                Write-Host "  Issue #$issueNumber needs agent label: $agentLabel" -ForegroundColor Gray
                
                if (Add-LabelsToIssue -IssueNumber $issueNumber -Labels @($agentLabel)) {
                    $totalLabeled++
                }
            }
        }
    }
}

# Summary
Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "  Total issues processed: $totalProcessed" -ForegroundColor Gray
Write-Host "  Issues labeled: $totalLabeled" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "`n💡 Run without -DryRun to apply changes" -ForegroundColor Yellow
} else {
    Write-Host "`n✅ Bulk labeling completed!" -ForegroundColor Green
}

# Verwendung:
# .\bulk-issue-labeling.ps1 -DryRun                    # Test run
# .\bulk-issue-labeling.ps1                           # Label all issues  
# .\bulk-issue-labeling.ps1 -IssueNumbers @(192,193) # Label specific issues