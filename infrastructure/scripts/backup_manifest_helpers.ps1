# backup_manifest_helpers.ps1 - Shared manifest reconciliation for backup_all.ps1

function Test-BackupArtifactPresent {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $false
    }

    return ((Get-Item $Path).Length -gt 0)
}

function Set-BackupComponentEvidence {
    param(
        [hashtable]$ComponentEvidence,
        [string]$ComponentName,
        [string]$Artifact,
        [int64]$SizeBytes
    )

    $ComponentEvidence[$ComponentName] = @{
        Artifact = $Artifact
        SizeBytes = $SizeBytes
    }
}

function Sync-BackupComponentManifest {
    param(
        [string]$WorkDir,
        [hashtable]$ComponentStatus,
        [hashtable]$ComponentEvidence
    )

    $postgresFile = Join-Path $WorkDir "postgres_dump.sql"
    if (Test-BackupArtifactPresent -Path $postgresFile) {
        $ComponentStatus.Postgres = $true
        Set-BackupComponentEvidence `
            -ComponentEvidence $ComponentEvidence `
            -ComponentName "Postgres" `
            -Artifact "postgres_dump.sql" `
            -SizeBytes ([int64](Get-Item $postgresFile).Length)
    } else {
        $ComponentStatus.Postgres = $false
        $ComponentEvidence.Postgres = @{}
    }

    $redisFile = Join-Path $WorkDir "redis_dump.rdb"
    if (Test-BackupArtifactPresent -Path $redisFile) {
        $ComponentStatus.Redis = $true
        Set-BackupComponentEvidence `
            -ComponentEvidence $ComponentEvidence `
            -ComponentName "Redis" `
            -Artifact "redis_dump.rdb" `
            -SizeBytes ([int64](Get-Item $redisFile).Length)
    } else {
        $ComponentStatus.Redis = $false
        $ComponentEvidence.Redis = @{}
    }

    $surrealBackupPath = Join-Path $WorkDir "surrealdb_data"
    if (Test-Path $surrealBackupPath) {
        $files = @(Get-ChildItem -Path $surrealBackupPath -File -Recurse -Force -ErrorAction SilentlyContinue)
        $totalBytes = 0
        if ($files.Count -gt 0) {
            $totalBytes = [int64](($files | Measure-Object -Property Length -Sum).Sum)
        }

        if ($files.Count -gt 0 -and $totalBytes -gt 0) {
            $ComponentStatus.SurrealDB = $true
            if (-not $ComponentEvidence.ContainsKey("SurrealDB")) {
                $ComponentEvidence.SurrealDB = @{}
            }
            $ComponentEvidence.SurrealDB.FileCount = [int64]$files.Count
            $ComponentEvidence.SurrealDB.TotalBytes = $totalBytes
            if (-not $ComponentEvidence.SurrealDB.ContainsKey("Artifact")) {
                $ComponentEvidence.SurrealDB.Artifact = "surrealdb_data"
            }
        }
    }
}

function Resolve-BackupComponentInclusion {
    param(
        [string]$BackupRoot,
        [bool]$ManifestFlag,
        [string]$ComponentName,
        [string]$ArtifactPattern,
        [string]$ArtifactLabel
    )

    $artifact = Get-ChildItem -Path $BackupRoot -Filter $ArtifactPattern -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.Length -gt 0 } |
        Select-Object -First 1

    if ($ManifestFlag) {
        return @{
            Included = $true
            Artifact = $artifact
            DriftCorrected = $false
        }
    }

    if ($artifact) {
        Write-Warning "Manifest drift: $ComponentName=false but $ArtifactLabel present - treating as included"
        return @{
            Included = $true
            Artifact = $artifact
            DriftCorrected = $true
        }
    }

    return @{
        Included = $false
        Artifact = $null
        DriftCorrected = $false
    }
}
