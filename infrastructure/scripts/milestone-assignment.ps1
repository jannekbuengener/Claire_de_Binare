# Milestone Assignment Script für Claire de Binare
# Systematische Zuordnung von Milestone-Labels und Epic-Labels

param(
    [string]$GitHubToken = $env:GITHUB_TOKEN,
    [string]$Owner = "jannekbuengener", 
    [string]$Repo = "Claire_de_Binare",
    [switch]$DryRun = $false,
    [switch]$CreateMilestones = $false,
    [int[]]$IssueNumbers = @()
)

if (-not $GitHubToken) {
    Write-Error "GitHub Token required. Set GITHUB_TOKEN environment variable or pass -GitHubToken parameter"
    exit 1
}

$headers = @{
    'Authorization' = "Bearer $GitHubToken"
    'Accept' = 'application/vnd.github.v3+json'
    'User-Agent' = 'Claire-de-Binare-Milestone-Script'
}

# Detaillierte Milestone-Zuordnung
$milestoneAssignments = @{
    # M1 - Foundation (Infrastructure, Governance, Basic Setup)
    "M1_Foundation" = @{
        IssueNumbers = @(135, 139, 156, 157, 158, 159, 160, 163, 164, 165, 166, 167, 168, 148, 149, 150, 117, 118, 119, 120)
        MilestoneLabel = "milestone:m1"
        EpicLabel = "epic:stabilization"
        Description = "Foundation - Infrastructure, Governance, Basic Setup"
    }
    
    # M3 - Risk Layer
    "M3_RiskLayer" = @{
        IssueNumbers = @(43) # Risk-specific issues
        MilestoneLabel = "milestone:m3" 
        EpicLabel = $null
        Description = "Risk Layer - Risk Management Implementation"
    }
    
    # M5 - Persistenz
    "M5_Persistenz" = @{
        IssueNumbers = @(43) # Database-specific issues
        MilestoneLabel = "milestone:m5"
        EpicLabel = $null
        Description = "Persistenz - Database and Storage"
    }
    
    # M6 - Docker
    "M6_Docker" = @{
        IssueNumbers = @(98, 101, 103, 140, 121, 122, 123)
        MilestoneLabel = "milestone:m6"
        EpicLabel = $null
        Description = "Docker - Container Infrastructure"
    }
    
    # M7 - Testnet (Paper Trading)
    "M7_Testnet" = @{
        IssueNumbers = @(91, 92, 93, 94, 95, 96, 113, 180, 181)
        MilestoneLabel = "milestone:m7"
        EpicLabel = "epic:paper-trading"
        Description = "Testnet - Paper Trading and Testing"
    }
    
    # M8 - Security  
    "M8_Security" = @{
        IssueNumbers = @(97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 174, 185)
        MilestoneLabel = "milestone:m8"
        EpicLabel = $null
        Description = "Security - Hardening and Penetration Testing"
    }
    
    # M9 - Production (Live Trading)
    "M9_Production" = @{
        IssueNumbers = @(171, 172, 173, 174, 175, 176, 177, 178, 179, 182, 183, 184, 186, 187, 188, 195)
        MilestoneLabel = "milestone:m9"
        EpicLabel = "epic:live-trading"
        Description = "Production - Live Trading Implementation"
    }
    
    # ML Foundation (Epic spanning milestones)
    "ML_Foundation" = @{
        IssueNumbers = @(192, 193, 194, 195, 196, 197, 198, 199, 200)
        MilestoneLabel = $null # Spans multiple milestones
        EpicLabel = "epic:ml-foundation"
        Description = "ML Foundation - Machine Learning Integration"
    }
}

# GitHub Milestones to create if requested
$milestonesToCreate = @(
    @{ Title = "M1 - Foundation"; Description = "Infrastructure, Governance, Basic Setup"; State = "open" },
    @{ Title = "M2 - Core Services"; Description = "Basic Trading Services Implementation"; State = "open" },
    @{ Title = "M3 - Risk Layer"; Description = "Risk Management Implementation"; State = "open" },
    @{ Title = "M4 - Market Data"; Description = "Market Data Pipeline Implementation"; State = "open" },
    @{ Title = "M5 - Persistenz"; Description = "Database and Storage Implementation"; State = "open" },
    @{ Title = "M6 - Docker"; Description = "Container Infrastructure"; State = "open" },
    @{ Title = "M7 - Testnet"; Description = "Paper Trading and Testing"; State = "open" },
    @{ Title = "M8 - Security"; Description = "Security Hardening"; State = "open" },
    @{ Title = "M9 - Production"; Description = "Live Trading Production Deployment"; State = "open" }
)

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

function Create-GitHubMilestones {
    if (-not $CreateMilestones) {
        Write-Host "Skipping milestone creation (use -CreateMilestones to create)" -ForegroundColor Gray
        return
    }
    
    Write-Host "`n🏁 Creating GitHub Milestones..." -ForegroundColor Cyan
    
    foreach ($milestone in $milestonesToCreate) {
        if ($DryRun) {
            Write-Host "DRY RUN: Would create milestone '$($milestone.Title)'" -ForegroundColor Yellow
            continue
        }
        
        try {
            $url = "https://api.github.com/repos/$Owner/$Repo/milestones"
            $body = @{
                title = $milestone.Title
                description = $milestone.Description  
                state = $milestone.State
            } | ConvertTo-Json
            
            $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Post -Body $body -ContentType "application/json"
            Write-Host "✅ Created milestone: $($milestone.Title)" -ForegroundColor Green
        } catch {
            if ($_.Exception.Response.StatusCode -eq 422) {
                Write-Host "ℹ️  Milestone '$($milestone.Title)' already exists" -ForegroundColor Gray
            } else {
                Write-Error "❌ Failed to create milestone '$($milestone.Title)': $($_.Exception.Message)"
            }
        }
    }
}

# Main execution
Write-Host "🏁 Claire de Binare Milestone & Epic Assignment" -ForegroundColor Cyan
Write-Host "Repository: $Owner/$Repo" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Create milestones if requested
Create-GitHubMilestones

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

# Apply milestone assignments
foreach ($milestone in $milestoneAssignments.Keys) {
    $assignment = $milestoneAssignments[$milestone]
    Write-Host "`n📋 Processing $milestone..." -ForegroundColor Cyan
    Write-Host "  $($assignment.Description)" -ForegroundColor Gray
    
    foreach ($issueNumber in $assignment.IssueNumbers) {
        if ($issuesToProcess -contains $issueNumber) {
            $totalProcessed++
            
            # Get existing labels
            $existingLabels = Get-ExistingLabels -IssueNumber $issueNumber
            
            # Determine new labels needed
            $newLabels = @()
            
            # Add milestone label if specified
            if ($assignment.MilestoneLabel -and $existingLabels -notcontains $assignment.MilestoneLabel) {
                $newLabels += $assignment.MilestoneLabel
            }
            
            # Add epic label if specified
            if ($assignment.EpicLabel -and $existingLabels -notcontains $assignment.EpicLabel) {
                $newLabels += $assignment.EpicLabel
            }
            
            if ($newLabels.Count -gt 0) {
                Write-Host "  Issue #$issueNumber needs labels: $($newLabels -join ', ')" -ForegroundColor Gray
                
                if (Add-LabelsToIssue -IssueNumber $issueNumber -Labels $newLabels) {
                    $totalLabeled++
                }
            } else {
                Write-Host "  Issue #$issueNumber already has milestone/epic labels" -ForegroundColor Green
            }
        }
    }
}

# Summary
Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "  Total issues processed: $totalProcessed" -ForegroundColor Gray
Write-Host "  Issues labeled: $totalLabeled" -ForegroundColor Gray

Write-Host "`n🏁 Milestone Distribution:" -ForegroundColor Cyan
Write-Host "  M1 - Foundation: Infrastructure, Governance (Issues 156-168, 117-120)" -ForegroundColor Gray
Write-Host "  M6 - Docker: Container Infrastructure (Issues 98, 101, 103, 140, 121-123)" -ForegroundColor Gray  
Write-Host "  M7 - Testnet: Paper Trading & Testing (Issues 91-96, 113, 180-181)" -ForegroundColor Gray
Write-Host "  M8 - Security: Security Hardening (Issues 97-106, 174, 185)" -ForegroundColor Gray
Write-Host "  M9 - Production: Live Trading (Issues 171-188, 195)" -ForegroundColor Gray
Write-Host "  Epic ML Foundation: Machine Learning (Issues 192-200)" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "`n💡 Run without -DryRun to apply changes" -ForegroundColor Yellow
    Write-Host "💡 Add -CreateMilestones to create GitHub milestones" -ForegroundColor Yellow
} else {
    Write-Host "`n✅ Milestone assignment completed!" -ForegroundColor Green
}

# Verwendung:
# .\milestone-assignment.ps1 -DryRun                              # Test run
# .\milestone-assignment.ps1 -CreateMilestones                   # Create milestones & assign labels
# .\milestone-assignment.ps1 -IssueNumbers @(192,193) -DryRun   # Test specific issues