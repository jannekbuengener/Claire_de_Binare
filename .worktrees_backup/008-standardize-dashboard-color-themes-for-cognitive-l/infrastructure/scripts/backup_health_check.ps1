# Enhanced Backup Status Check
Write-Host "🔍 COPILOT SMART BACKUP ENHANCEMENT" -ForegroundColor Green
$backupDir = "F:\Claire_Backups"
if (Test-Path $backupDir) {
    $latestBackup = Get-ChildItem $backupDir | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $age = (Get-Date) - $latestBackup.LastWriteTime
    if ($age.TotalHours -lt 2) {
        Write-Host "✅ Backup system healthy - Latest: $($latestBackup.Name)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Backup potentially stale - Age: $($age.TotalHours.ToString(\"F1\")) hours" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Backup directory not accessible" -ForegroundColor Red
}
