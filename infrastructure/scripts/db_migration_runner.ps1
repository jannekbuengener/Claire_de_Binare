<#
.SYNOPSIS
Audit and apply repo-managed PostgreSQL schema migrations.

.DESCRIPTION
Provides a repo-side audit for the database schema and migration inventory, and
optionally applies SQL files to a running Postgres container via `docker exec`
and `psql`.

Safe default:
- no arguments => audit only

Execution modes:
- `-AuditOnly` => inventory + compose auto-init coverage audit
- `-ApplyMigrations` => apply all SQL files from `infrastructure/database/migrations`
- `-BootstrapFreshSchema` => apply destructive `schema.sql` first, then all migrations

IMPORTANT:
`schema.sql` contains `DROP TABLE IF EXISTS` statements and is therefore only
safe for empty/fresh databases or explicit destructive rebuilds.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$AuditOnly,
    [switch]$ApplyMigrations,
    [switch]$BootstrapFreshSchema,
    [string]$ContainerName = 'cdb_postgres',
    [string]$Database = 'claire_de_binare',
    [string]$User = 'claire_user'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $AuditOnly -and -not $ApplyMigrations -and -not $BootstrapFreshSchema) {
    $AuditOnly = $true
}

$selectedModes = @($AuditOnly, $ApplyMigrations, $BootstrapFreshSchema) |
    Where-Object { $_ } |
    Measure-Object |
    Select-Object -ExpandProperty Count

if ($selectedModes -ne 1) {
    throw 'Choose exactly one mode: -AuditOnly, -ApplyMigrations, or -BootstrapFreshSchema.'
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$schemaPath = Join-Path $repoRoot 'infrastructure\database\schema.sql'
$migrationDir = Join-Path $repoRoot 'infrastructure\database\migrations'

$composeFiles = @(
    [PSCustomObject]@{ Name = 'base.yml'; Path = Join-Path $repoRoot 'infrastructure\compose\base.yml' },
    [PSCustomObject]@{ Name = 'compose.blue.yml'; Path = Join-Path $repoRoot 'infrastructure\compose\compose.blue.yml' },
    [PSCustomObject]@{ Name = 'test.yml'; Path = Join-Path $repoRoot 'infrastructure\compose\test.yml' },
    [PSCustomObject]@{ Name = 'tls.yml'; Path = Join-Path $repoRoot 'infrastructure\compose\tls.yml' }
)

function Get-MigrationFiles {
    param(
        [string]$DirectoryPath
    )

    if (-not (Test-Path $DirectoryPath -PathType Container)) {
        throw "Migration directory not found: $DirectoryPath"
    }

    return Get-ChildItem -Path $DirectoryPath -Filter '*.sql' -File | Sort-Object Name
}

function Get-RelativeRepoPath {
    param(
        [string]$Path
    )

    $resolvedRepoRoot = (Resolve-Path -Path $repoRoot).Path.TrimEnd('\')
    $resolvedPath = (Resolve-Path -Path $Path).Path

    if ($resolvedPath.StartsWith("$resolvedRepoRoot\", [System.StringComparison]::OrdinalIgnoreCase)) {
        return $resolvedPath.Substring($resolvedRepoRoot.Length + 1)
    }

    return $resolvedPath
}

function Get-DuplicatePrefixGroups {
    param(
        [System.IO.FileInfo[]]$Files
    )

    $prefixRows = foreach ($file in $Files) {
        if ($file.BaseName -match '^(\d+)') {
            [PSCustomObject]@{
                Prefix = $Matches[1]
                Name = $file.Name
            }
        }
    }

    return $prefixRows |
        Group-Object Prefix |
        Where-Object { $_.Count -gt 1 }
}

function Get-AutoInitCoverage {
    param(
        [System.IO.FileInfo[]]$Files
    )

    $coverageRows = foreach ($composeFile in $composeFiles) {
        if (-not (Test-Path $composeFile.Path -PathType Leaf)) {
            continue
        }

        $content = Get-Content -Path $composeFile.Path -Raw -Encoding UTF8
        $mountedSchema = $content -match 'infrastructure/database/schema\.sql'

        $mountedMigrations = [regex]::Matches(
            $content,
            'infrastructure/database/migrations/([A-Za-z0-9_.-]+\.sql)'
        ) | ForEach-Object {
            $_.Groups[1].Value
        }

        [PSCustomObject]@{
            ComposeFile = $composeFile.Name
            SchemaMounted = $mountedSchema
            MountedMigrations = @($mountedMigrations)
        }
    }

    $allMounted = $coverageRows |
        ForEach-Object { $_.MountedMigrations } |
        Select-Object -Unique

    $missingFromAutoInit = $Files |
        Where-Object { $_.Name -notin $allMounted } |
        Select-Object -ExpandProperty Name

    return [PSCustomObject]@{
        Rows = $coverageRows
        MissingFromAutoInit = @($missingFromAutoInit)
    }
}

function Invoke-PsqlFile {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "SQL file not found: $Path"
    }

    $relativePath = Get-RelativeRepoPath -Path $Path
    Write-Host "Applying $relativePath" -ForegroundColor Cyan

    if ($PSCmdlet.ShouldProcess("$ContainerName/$Database", "Apply $relativePath")) {
        $sql = Get-Content -Path $Path -Raw -Encoding UTF8
        $sql | docker exec -i $ContainerName psql -v ON_ERROR_STOP=1 -U $User -d $Database
        if ($LASTEXITCODE -ne 0) {
            throw "psql failed while applying $relativePath"
        }
    }
}

$migrationFiles = Get-MigrationFiles -DirectoryPath $migrationDir
$duplicatePrefixes = Get-DuplicatePrefixGroups -Files $migrationFiles
$autoInitCoverage = Get-AutoInitCoverage -Files $migrationFiles
$schemaContent = Get-Content -Path $schemaPath -Raw -Encoding UTF8
$schemaIsDestructive = $schemaContent -match 'DROP TABLE IF EXISTS'

if ($AuditOnly) {
    Write-Host 'DB migration audit' -ForegroundColor Cyan
    Write-Host "Repo root: $repoRoot" -ForegroundColor Gray
    Write-Host "Schema file: $(Get-RelativeRepoPath -Path $schemaPath)" -ForegroundColor Gray
    Write-Host "Migration files: $($migrationFiles.Count)" -ForegroundColor Gray
    foreach ($file in $migrationFiles) {
        Write-Host " - $($file.Name)" -ForegroundColor Gray
    }

    Write-Host ''
    if ($schemaIsDestructive) {
        Write-Warning 'schema.sql contains DROP TABLE IF EXISTS and is destructive. Do not use it for in-place production-like migration.'
    }

    if ($duplicatePrefixes.Count -gt 0) {
        Write-Warning 'Duplicate numeric migration prefixes detected:'
        foreach ($group in $duplicatePrefixes) {
            $names = ($group.Group | ForEach-Object { $_.Name }) -join ', '
            Write-Host " - Prefix $($group.Name): $names" -ForegroundColor Yellow
        }
    } else {
        Write-Host 'No duplicate numeric migration prefixes detected.' -ForegroundColor Green
    }

    Write-Host ''
    Write-Host 'Compose auto-init coverage:' -ForegroundColor Cyan
    foreach ($row in $autoInitCoverage.Rows) {
        $schemaState = if ($row.SchemaMounted) { 'schema mounted' } else { 'schema missing' }
        $migrationState = if ($row.MountedMigrations.Count -gt 0) {
            $row.MountedMigrations -join ', '
        } else {
            '(no migrations mounted)'
        }
        Write-Host " - $($row.ComposeFile): $schemaState; migrations: $migrationState" -ForegroundColor Gray
    }

    if ($autoInitCoverage.MissingFromAutoInit.Count -gt 0) {
        Write-Warning 'Migration files on disk but not mounted into any current compose auto-init path:'
        foreach ($name in $autoInitCoverage.MissingFromAutoInit) {
            Write-Host " - $name" -ForegroundColor Yellow
        }
    } else {
        Write-Host 'All migration files are mounted into at least one compose auto-init path.' -ForegroundColor Green
    }

    Write-Host ''
    Write-Host 'Note: no repo-level migration state table was detected; apply order is file-based and audit coverage is inventory-based.' -ForegroundColor Gray
    exit 0
}

if ($ApplyMigrations) {
    Write-Host "Applying repo migrations to $ContainerName/$Database" -ForegroundColor Cyan
    foreach ($file in $migrationFiles) {
        Invoke-PsqlFile -Path $file.FullName
    }
    Write-Host 'Migration apply complete.' -ForegroundColor Green
    exit 0
}

if ($BootstrapFreshSchema) {
    if ($schemaIsDestructive) {
        Write-Warning 'Bootstrap mode applies destructive schema.sql first. Use this only for empty/fresh databases or explicit rebuilds.'
    }

    Write-Host "Bootstrapping schema + migrations on $ContainerName/$Database" -ForegroundColor Cyan
    Invoke-PsqlFile -Path $schemaPath
    foreach ($file in $migrationFiles) {
        Invoke-PsqlFile -Path $file.FullName
    }
    Write-Host 'Schema bootstrap + migration apply complete.' -ForegroundColor Green
    exit 0
}
