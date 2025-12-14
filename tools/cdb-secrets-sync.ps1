#Requires -Version 5.1

<#
.SYNOPSIS
    Synchronizes vault secrets into the workspace.
.DESCRIPTION
    Copies vault files from .cdb_local/.secrets/ into .secrets/ and keeps .env entries aligned.
    Prevents credential mismatches for Redis, PostgreSQL, and Grafana.
.PARAMETER DryRun
    Shows what would be changed without writing files.
.EXAMPLE
    ./tools/cdb-secrets-sync.ps1
    ./tools/cdb-secrets-sync.ps1 -DryRun
#>

param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Section($text) {
    Write-Host ''
    Write-Host ('== {0} ==' -f $text) -ForegroundColor Blue
}

function Write-Success($text) { Write-Host ('[OK]    {0}' -f $text) -ForegroundColor Green }
function Write-Info($text)    { Write-Host ('[INFO]  {0}' -f $text) -ForegroundColor Cyan }
function Write-Warning($text) { Write-Host ('[WARN]  {0}' -f $text) -ForegroundColor Yellow }
function Write-Failure($text) { Write-Host ('[FAIL]  {0}' -f $text) -ForegroundColor Red }

$vaultDirectory = '.cdb_local/.secrets'
$workspaceSecrets = '.secrets'
$envFile = '.env'

$secretMapping = @{
    'redis_password'    = 'REDIS_PASSWORD'
    'postgres_password' = 'POSTGRES_PASSWORD'
    'grafana_password'  = 'GRAFANA_PASSWORD'
}

Write-Section 'Secrets sync start'
if ($DryRun) {
    Write-Warning 'Dry run mode active; no files will be modified.'
}

foreach ($path in @($vaultDirectory, $envFile)) {
    if (-not (Test-Path $path)) {
        Write-Failure ('Required path missing: {0}' -f $path)
        exit 1
    }
}

if (-not (Test-Path $workspaceSecrets)) {
    if ($DryRun) {
        Write-Info ('[DryRun] Would create {0}' -f $workspaceSecrets)
    } else {
        New-Item -ItemType Directory -Path $workspaceSecrets -Force | Out-Null
        Write-Success ('Created {0}' -f $workspaceSecrets)
    }
}

$plans = @()
foreach ($secretName in $secretMapping.Keys) {
    $sourcePath = Join-Path $vaultDirectory $secretName
    if (-not (Test-Path $sourcePath)) {
        Write-Warning ('Vault secret missing: {0}' -f $secretName)
        continue
    }

    $sourceContent = (Get-Content $sourcePath -Raw).Trim()
    if ([string]::IsNullOrEmpty($sourceContent)) {
        Write-Warning ('Vault secret {0} is empty; skipping.' -f $secretName)
        continue
    }

    $targetPath = Join-Path $workspaceSecrets $secretName
    $action = 'Create'
    if (Test-Path $targetPath) {
        $existing = (Get-Content $targetPath -Raw).Trim()
        if ($existing -eq $sourceContent) {
            $action = 'Skip'
        } else {
            $action = 'Update'
        }
    }

    $plans += [PSCustomObject]@{
        SecretName = $secretName
        TargetPath = $targetPath
        Action     = $action
        Content    = $sourceContent
        VarName    = $secretMapping[$secretName]
    }

    Write-Info ('Plan: {0} {1}' -f $action, $secretName)
}

if ($plans.Count -eq 0) {
    Write-Warning 'No secrets were available for synchronization.'
}

$pendingWrites = @($plans | Where-Object { $_.Action -ne 'Skip' })
if ($pendingWrites.Count -gt 0) {
    Write-Section 'Writing secret files'
    foreach ($plan in $pendingWrites) {
        if ($DryRun) {
            Write-Info ('[DryRun] Would write {0}' -f $plan.SecretName)
            continue
        }
        $plan.Content | Out-File -FilePath $plan.TargetPath -Encoding ASCII -NoNewline -Force
        Write-Success ('{0} {1}' -f $plan.Action, $plan.SecretName)
    }
} else {
    Write-Info 'Secret files already match the vault.'
}

Write-Section 'Updating .env'
$envLines = [System.Collections.Generic.List[string]]::new()
Get-Content $envFile | ForEach-Object { [void]$envLines.Add($_) }
$envChanged = $false

foreach ($plan in $plans) {
    if (-not $plan.Content) { continue }
    $varName = $plan.VarName
    $lineTemplate = ('{0}=' -f $varName)
    $matchIndex = -1
    for ($i = 0; $i -lt $envLines.Count; $i++) {
        if ($envLines[$i].TrimStart().StartsWith($lineTemplate)) {
            $matchIndex = $i
            break
        }
    }

    if ($matchIndex -ge 0) {
        $currentValue = $envLines[$matchIndex].Substring($lineTemplate.Length).Trim()
        if ($currentValue -ne $plan.Content) {
            $envLines[$matchIndex] = ('{0}{1}' -f $lineTemplate, $plan.Content)
            $envChanged = $true
            Write-Info ('Updated {0}' -f $varName)
        } else {
            Write-Success ('{0} already aligned' -f $varName)
        }
    } else {
        $envLines.Add(('{0}{1}' -f $lineTemplate, $plan.Content))
        $envChanged = $true
        Write-Info ('Appended {0} to .env' -f $varName)
    }
}

if ($envChanged) {
    if ($DryRun) {
        Write-Info '[DryRun] Would persist .env updates'
    } else {
        $envLines | Set-Content -Path $envFile -Encoding ASCII
        Write-Success '.env updated with vault values'
    }
} else {
    Write-Success '.env is already aligned with the vault'
}

Write-Section 'Summary'
if ($DryRun) {
    Write-Warning 'Dry run complete; no files were modified.'
}
if (($pendingWrites.Count -eq 0) -and (-not $envChanged)) {
    Write-Success 'Secrets and .env already synchronized.'
}

exit 0
