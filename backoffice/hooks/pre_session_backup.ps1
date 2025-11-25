# Pre-Session Hook - Automatische Backups
# Wird vor jeder Claude Code Session ausgeführt
# Version: 2.0.0
# Sichert: PostgreSQL + Repository

# ANSI Colors
$RED = "`e[31m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

Write-Host "${BLUE}=== Pre-Session: Automatische Backups ===${RESET}`n"

# 1. PostgreSQL Backup
Write-Host "${BLUE}[1/2]${RESET} PostgreSQL Backup..."

$pgBackupScript = Join-Path $PSScriptRoot "..\scripts\backup_postgres.ps1"

if (Test-Path $pgBackupScript) {
    try {
        $pgOutput = & $pgBackupScript 2>&1

        if ($LASTEXITCODE -eq 0) {
            $pgSize = ($pgOutput | Where-Object { $_ -match "Backup erfolgreich:" }) -replace ".*erfolgreich:\s*", ""
            Write-Host "${GREEN}      [✓]${RESET} PostgreSQL: $pgSize"
        } else {
            Write-Host "${YELLOW}      [!]${RESET} PostgreSQL Backup übersprungen (Container nicht running?)"
        }
    } catch {
        Write-Host "${YELLOW}      [!]${RESET} PostgreSQL Backup fehlgeschlagen: $_"
    }
} else {
    Write-Host "${YELLOW}      [!]${RESET} Script nicht gefunden, übersprungen"
}

# 2. Repository Backup
Write-Host "${BLUE}[2/2]${RESET} Repository Backup..."

$repoBackupScript = Join-Path $PSScriptRoot "..\scripts\backup_repository.ps1"

if (Test-Path $repoBackupScript) {
    try {
        # Repository backup OHNE .env (zu riskant für Auto-Backup)
        $repoOutput = & $repoBackupScript 2>&1

        if ($LASTEXITCODE -eq 0) {
            $repoCommit = ($repoOutput | Where-Object { $_ -match "Commit:" }) -replace ".*Commit:\s*", ""
            $repoSize = ($repoOutput | Where-Object { $_ -match "Größe:" }) -replace ".*Größe:\s*", ""
            Write-Host "${GREEN}      [✓]${RESET} Repository: $repoSize | $repoCommit"
        } else {
            Write-Host "${YELLOW}      [!]${RESET} Repository Backup fehlgeschlagen"
        }
    } catch {
        Write-Host "${YELLOW}      [!]${RESET} Repository Backup fehlgeschlagen: $_"
    }
} else {
    Write-Host "${YELLOW}      [!]${RESET} Script nicht gefunden, übersprungen"
}

Write-Host ""
Write-Host "${GREEN}=== Backups Complete ===${RESET}"
Write-Host "Gespeichert: ${BLUE}F:\Claire_Backups\${RESET}"
Write-Host ""
