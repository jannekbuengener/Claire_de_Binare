# Claire de Binare Enhanced Time Tracker
# Usage: .\time-tracker-enhanced.ps1 [start|stop|status|report|estimate|reset]

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "status",
    
    [Parameter(Mandatory=$false)]
    [int]$MinutesPerCommit = 30,
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectPath = "..\Claire_de_Binare"
)

$TrackerFile = "$PSScriptRoot\.timetrack.json"
$ProjectName = "Claire de Binare"

function Get-TrackerData {
    if (Test-Path $TrackerFile) {
        return Get-Content $TrackerFile | ConvertFrom-Json
    } else {
        return @{
            sessions = @()
            totalMinutes = 0
            estimatedMinutes = 0
            lastUpdate = ""
            projectStart = ""
            commitCount = 0
        }
    }
}

function Save-TrackerData($data) {
    $data.lastUpdate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $data | ConvertTo-Json -Depth 10 | Set-Content $TrackerFile
}

function Get-GitStats {
    if (-not (Test-Path $ProjectPath)) {
        Write-Host "⚠️  Project path not found: $ProjectPath" -ForegroundColor Yellow
        return $null
    }
    
    Push-Location $ProjectPath
    try {
        # Check if it's a git repo
        $gitCheck = git rev-parse --git-dir 2>$null
        if (-not $gitCheck) {
            Write-Host "⚠️  Not a git repository: $ProjectPath" -ForegroundColor Yellow
            return $null
        }
        
        # Get commit count
        $commitCount = (git log --oneline --all | Measure-Object).Count
        
        # Get first commit date
        $firstCommit = git log --reverse --format="%ad" --date=short | Select-Object -First 1
        
        # Get last commit date
        $lastCommit = git log --format="%ad" --date=short | Select-Object -First 1
        
        # Get commits per day
        $commitsByDay = git log --format="%ad" --date=short --all | Group-Object | Measure-Object
        $activeDays = $commitsByDay.Count
        
        return @{
            commitCount = $commitCount
            firstCommit = $firstCommit
            lastCommit = $lastCommit
            activeDays = $activeDays
        }
    }
    finally {
        Pop-Location
    }
}

function Calculate-EstimatedTime {
    $gitStats = Get-GitStats
    if (-not $gitStats) {
        return 0
    }
    
    # Base estimation: commits * minutes per commit
    $baseEstimate = $gitStats.commitCount * $MinutesPerCommit
    
    # Project duration in days
    if ($gitStats.firstCommit -and $gitStats.lastCommit) {
        $startDate = [DateTime]::Parse($gitStats.firstCommit)
        $endDate = [DateTime]::Parse($gitStats.lastCommit)
        $projectDays = ($endDate - $startDate).Days + 1
        
        # Adjust based on activity density
        $activityRatio = $gitStats.activeDays / [Math]::Max($projectDays, 1)
        $densityMultiplier = 1 + ($activityRatio * 0.5) # More active days = more time
        
        $adjustedEstimate = $baseEstimate * $densityMultiplier
    } else {
        $adjustedEstimate = $baseEstimate
    }
    
    return [math]::Round($adjustedEstimate, 0)
}

function Start-Tracking {
    $data = Get-TrackerData
    
    # Check if already tracking
    $activeSession = $data.sessions | Where-Object { $_.endTime -eq $null }
    if ($activeSession) {
        Write-Host "⚠️  Already tracking since $($activeSession.startTime)" -ForegroundColor Yellow
        return
    }
    
    $session = @{
        startTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        endTime = $null
        description = ""
    }
    
    $data.sessions += $session
    Save-TrackerData $data
    
    Write-Host "✅ Started tracking $ProjectName at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
}

function Stop-Tracking {
    $data = Get-TrackerData
    
    $activeSession = $data.sessions | Where-Object { $_.endTime -eq $null }
    if (-not $activeSession) {
        Write-Host "❌ No active tracking session found" -ForegroundColor Red
        return
    }
    
    $startTime = [DateTime]::ParseExact($activeSession.startTime, "yyyy-MM-dd HH:mm:ss", $null)
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    $activeSession.endTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $activeSession.durationMinutes = [math]::Round($duration.TotalMinutes, 1)
    
    $data.totalMinutes += $activeSession.durationMinutes
    Save-TrackerData $data
    
    Write-Host "⏹️  Stopped tracking. Session duration: $($activeSession.durationMinutes) minutes" -ForegroundColor Blue
    
    # Update and show combined time
    Update-EstimatedTime
}

function Update-EstimatedTime {
    $data = Get-TrackerData
    $gitStats = Get-GitStats
    
    if ($gitStats) {
        $data.estimatedMinutes = Calculate-EstimatedTime
        $data.commitCount = $gitStats.commitCount
        $data.projectStart = $gitStats.firstCommit
        Save-TrackerData $data
        
        $totalTime = $data.totalMinutes + $data.estimatedMinutes
        Write-Host "📊 Combined time estimate: $([math]::Round($totalTime / 60, 1)) hours" -ForegroundColor Cyan
        Write-Host "   (Tracked: $([math]::Round($data.totalMinutes / 60, 1))h + Estimated: $([math]::Round($data.estimatedMinutes / 60, 1))h)" -ForegroundColor Gray
    }
}

function Show-Estimate {
    Write-Host "`n🔮 $ProjectName Time Estimation" -ForegroundColor Magenta
    Write-Host "===============================" -ForegroundColor Magenta
    
    $gitStats = Get-GitStats
    if (-not $gitStats) {
        Write-Host "❌ Cannot access git repository for estimation" -ForegroundColor Red
        return
    }
    
    Write-Host "`n📈 Git Statistics:" -ForegroundColor Cyan
    Write-Host "  Total commits: $($gitStats.commitCount)" -ForegroundColor White
    Write-Host "  Project start: $($gitStats.firstCommit)" -ForegroundColor White
    Write-Host "  Last commit: $($gitStats.lastCommit)" -ForegroundColor White
    Write-Host "  Active days: $($gitStats.activeDays)" -ForegroundColor White
    
    if ($gitStats.firstCommit -and $gitStats.lastCommit) {
        $startDate = [DateTime]::Parse($gitStats.firstCommit)
        $endDate = [DateTime]::Parse($gitStats.lastCommit)
        $projectDays = ($endDate - $startDate).Days + 1
        Write-Host "  Project span: $projectDays days" -ForegroundColor White
        Write-Host "  Activity ratio: $([math]::Round(($gitStats.activeDays / $projectDays) * 100, 1))%" -ForegroundColor White
    }
    
    $estimated = Calculate-EstimatedTime
    Write-Host "`n⏱️  Estimation Model:" -ForegroundColor Cyan
    Write-Host "  Base rate: $MinutesPerCommit minutes per commit" -ForegroundColor White
    Write-Host "  Raw estimate: $([math]::Round(($gitStats.commitCount * $MinutesPerCommit) / 60, 1)) hours" -ForegroundColor White
    Write-Host "  Adjusted estimate: $([math]::Round($estimated / 60, 1)) hours" -ForegroundColor Yellow
    
    $data = Get-TrackerData
    if ($data.totalMinutes -gt 0) {
        $combined = $data.totalMinutes + $estimated
        Write-Host "`n🎯 Combined Time:" -ForegroundColor Green
        Write-Host "  Tracked time: $([math]::Round($data.totalMinutes / 60, 1)) hours" -ForegroundColor White
        Write-Host "  Estimated time: $([math]::Round($estimated / 60, 1)) hours" -ForegroundColor White
        Write-Host "  Total project time: $([math]::Round($combined / 60, 1)) hours" -ForegroundColor Green
    }
}

function Show-Status {
    $data = Get-TrackerData
    
    Write-Host "`n🕒 $ProjectName Time Tracker Status" -ForegroundColor Magenta
    Write-Host "=================================" -ForegroundColor Magenta
    
    $activeSession = $data.sessions | Where-Object { $_.endTime -eq $null }
    if ($activeSession) {
        $startTime = [DateTime]::ParseExact($activeSession.startTime, "yyyy-MM-dd HH:mm:ss", $null)
        $currentDuration = (Get-Date) - $startTime
        Write-Host "🟢 Currently tracking since: $($activeSession.startTime)" -ForegroundColor Green
        Write-Host "⏱️  Current session: $([math]::Round($currentDuration.TotalMinutes, 1)) minutes" -ForegroundColor Yellow
    } else {
        Write-Host "🔴 Not currently tracking" -ForegroundColor Red
    }
    
    # Update estimation
    Update-EstimatedTime
    $data = Get-TrackerData
    
    Write-Host "📈 Total sessions: $($data.sessions.Count)" -ForegroundColor Cyan
    Write-Host "⏳ Tracked time: $([math]::Round($data.totalMinutes / 60, 1)) hours" -ForegroundColor Cyan
    
    if ($data.estimatedMinutes -gt 0) {
        $combined = $data.totalMinutes + $data.estimatedMinutes
        Write-Host "🔮 Estimated time: $([math]::Round($data.estimatedMinutes / 60, 1)) hours" -ForegroundColor Yellow
        Write-Host "🎯 Combined total: $([math]::Round($combined / 60, 1)) hours" -ForegroundColor Green
        Write-Host "📊 Based on $($data.commitCount) commits since $($data.projectStart)" -ForegroundColor Gray
    }
    
    if ($data.lastUpdate) {
        Write-Host "🔄 Last update: $($data.lastUpdate)" -ForegroundColor Gray
    }
}

function Show-Report {
    $data = Get-TrackerData
    
    Write-Host "`n📊 $ProjectName Time Report" -ForegroundColor Magenta
    Write-Host "============================" -ForegroundColor Magenta
    
    # Show estimation first
    if ($data.estimatedMinutes -gt 0) {
        Write-Host "`n🔮 Project Overview:" -ForegroundColor Cyan
        Write-Host "  Project started: $($data.projectStart)" -ForegroundColor White
        Write-Host "  Commits analyzed: $($data.commitCount)" -ForegroundColor White
        Write-Host "  Estimated time: $([math]::Round($data.estimatedMinutes / 60, 1)) hours" -ForegroundColor Yellow
        Write-Host "  Tracked time: $([math]::Round($data.totalMinutes / 60, 1)) hours" -ForegroundColor Cyan
        $combined = $data.totalMinutes + $data.estimatedMinutes
        Write-Host "  Total project time: $([math]::Round($combined / 60, 1)) hours" -ForegroundColor Green
    }
    
    $completedSessions = $data.sessions | Where-Object { $_.endTime -ne $null }
    
    if ($completedSessions.Count -eq 0) {
        Write-Host "`nNo tracked sessions found." -ForegroundColor Yellow
        return
    }
    
    Write-Host "`n⏱️  Recent Tracked Sessions:" -ForegroundColor Cyan
    $completedSessions | Sort-Object startTime -Descending | Select-Object -First 10 | ForEach-Object {
        $start = [DateTime]::ParseExact($_.startTime, "yyyy-MM-dd HH:mm:ss", $null)
        $end = [DateTime]::ParseExact($_.endTime, "yyyy-MM-dd HH:mm:ss", $null)
        Write-Host "  $($start.ToString('dd.MM HH:mm')) - $($end.ToString('HH:mm')) ($($_.durationMinutes) min)" -ForegroundColor White
    }
}

function Reset-Tracker {
    if (Test-Path $TrackerFile) {
        $confirm = Read-Host "Are you sure you want to reset all tracking data? (y/N)"
        if ($confirm -eq 'y' -or $confirm -eq 'Y') {
            Remove-Item $TrackerFile
            Write-Host "🗑️  Tracker data reset" -ForegroundColor Red
        }
    } else {
        Write-Host "No tracker data to reset" -ForegroundColor Yellow
    }
}

# Main execution
switch ($Action.ToLower()) {
    "start" { Start-Tracking }
    "stop" { Stop-Tracking }
    "status" { Show-Status }
    "report" { Show-Report }
    "estimate" { Show-Estimate }
    "reset" { Reset-Tracker }
    default { 
        Write-Host "Usage: .\time-tracker-enhanced.ps1 [start|stop|status|report|estimate|reset]" -ForegroundColor Yellow
        Write-Host "Parameters: -MinutesPerCommit (default: 30) -ProjectPath (default: ..\Claire_de_Binare)" -ForegroundColor Gray
        Show-Status
    }
}