# Setup Hourly Backup Task - Claire de Binare
# Muss als Administrator ausgeführt werden

$ErrorActionPreference = "Stop"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Claire de Binare - Backup Task Setup" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ""
    Write-Host "[ERROR] Dieses Script muss als Administrator ausgefuhrt werden!" -ForegroundColor Red
    Write-Host ""
    Write-Host "So geht's:" -ForegroundColor Yellow
    Write-Host "  1. PowerShell als Administrator offnen" -ForegroundColor Yellow
    Write-Host "  2. Zu diesem Verzeichnis navigieren" -ForegroundColor Yellow
    Write-Host "  3. Script erneut ausfuhren" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "[INFO] Administrator-Rechte erkannt" -ForegroundColor Green

# Task Configuration
$taskName = "Claire_Hourly_Backup"
$scriptPath = Join-Path $PSScriptRoot "backup_postgres.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""

# Trigger: Every hour, starting at midnight
$trigger = New-ScheduledTaskTrigger -Once -At "00:00" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

# Principal (User to run as)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Write-Host ""
Write-Host "[INFO] Erstelle Scheduled Task: $taskName" -ForegroundColor Cyan

try {
    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

    if ($existingTask) {
        Write-Host "[WARN] Task '$taskName' existiert bereits. Losche alte Version..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }

    # Register new task
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Stundliche PostgreSQL Backups fur Claire de Binare Paper Trading (14 Tage)"

    Write-Host ""
    Write-Host "[OK] Task erfolgreich erstellt!" -ForegroundColor Green
    Write-Host ""

    # Show task details
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  Name:        $taskName" -ForegroundColor White
    Write-Host "  Script:      $scriptPath" -ForegroundColor White
    Write-Host "  Frequenz:    Stundlich (ab Mitternacht)" -ForegroundColor White
    Write-Host "  Benutzer:    SYSTEM" -ForegroundColor White
    Write-Host ""

    # Test run
    Write-Host "[INFO] Mochtest du jetzt ein Test-Backup ausfuhren? (j/n)" -ForegroundColor Yellow
    $response = Read-Host

    if ($response -eq "j" -or $response -eq "J" -or $response -eq "y" -or $response -eq "Y") {
        Write-Host ""
        Write-Host "[INFO] Fuhre Test-Backup aus..." -ForegroundColor Cyan
        & $scriptPath
    }

    Write-Host ""
    Write-Host "[OK] Setup abgeschlossen!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Nachste Schritte:" -ForegroundColor Cyan
    Write-Host "  - Task prufen:        Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host "  - Task manuell starten: Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host "  - Backups ansehen:     dir F:\Claire_Backups" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "[ERROR] Task konnte nicht erstellt werden:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    exit 1
}

pause
