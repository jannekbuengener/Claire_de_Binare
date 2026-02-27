[CmdletBinding()]
param(
    [switch]$DryRun,
    [string[]]$Only
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$defaultSecretsDir = "C:\Users\janne\Documents\.secrets\.cdb\"
$secretsDir = if ([string]::IsNullOrWhiteSpace($env:CDB_SECRETS_DIR)) {
    $defaultSecretsDir
} else {
    $env:CDB_SECRETS_DIR
}

$manifestPath = Join-Path $secretsDir "secrets.manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Error "Manifest not found: $manifestPath"
    exit 1
}

$manifestRaw = Get-Content -LiteralPath $manifestPath -Raw
$manifestObj = $manifestRaw | ConvertFrom-Json

if (-not $manifestObj -or [string]::IsNullOrWhiteSpace([string]$manifestObj.repo)) {
    Write-Error "Manifest key 'repo' missing or empty."
    exit 1
}
if (-not $manifestObj.secrets) {
    Write-Error "Manifest key 'secrets' missing."
    exit 1
}

$repo = [string]$manifestObj.repo
$secretsMap = @{}
foreach ($p in $manifestObj.secrets.PSObject.Properties) {
    $secretsMap[$p.Name] = [string]$p.Value
}

$optionalSecrets = @(
    "CDB_GH_APP_ID",
    "CDB_GH_APP_PRIVATE_KEY",
    "CDB_GH_APP_INSTALLATION_ID"
)

$selectedNames = @($secretsMap.Keys | Sort-Object)
if ($Only -and $Only.Count -gt 0) {
    $requested = @($Only | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $unknown = @($requested | Where-Object { -not $secretsMap.ContainsKey($_) })
    if ($unknown.Count -gt 0) {
        Write-Error "Unknown secret name(s): $($unknown -join ', ')"
        exit 1
    }
    $selectedNames = @($requested)
}

if ($selectedNames.Count -eq 0) {
    Write-Error "No secrets selected."
    exit 1
}

$failed = 0
$updated = 0
$skipped = 0

foreach ($secretName in $selectedNames) {
    $fileName = [string]$secretsMap[$secretName]
    if ([string]::IsNullOrWhiteSpace($fileName)) {
        Write-Host "FAIL  $secretName (manifest mapping is empty)"
        $failed++
        continue
    }

    $secretPath = Join-Path $secretsDir $fileName
    if (-not (Test-Path -LiteralPath $secretPath)) {
        if ($optionalSecrets -contains $secretName) {
            Write-Host "SKIP  $secretName (optional file missing: $fileName)"
            $skipped++
            continue
        }
        Write-Host "FAIL  $secretName (file missing: $fileName)"
        $failed++
        continue
    }

    $secretValue = (Get-Content -LiteralPath $secretPath -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($secretValue)) {
        if ($optionalSecrets -contains $secretName) {
            Write-Host "SKIP  $secretName (optional file empty: $fileName)"
            $skipped++
            continue
        }
        Write-Host "FAIL  $secretName (file empty: $fileName)"
        $failed++
        continue
    }

    if ($DryRun) {
        Write-Host "DRYRUN $secretName (source: $fileName)"
        $updated++
        continue
    }

    try {
        gh secret set $secretName -b $secretValue -R $repo | Out-Null
        Write-Host "OK    $secretName"
        $updated++
    } catch {
        Write-Host "FAIL  $secretName (gh secret set failed)"
        $failed++
    } finally {
        $secretValue = $null
    }
}

Write-Host "SUMMARY repo=$repo updated=$updated skipped=$skipped failed=$failed dryrun=$($DryRun.IsPresent)"
if ($failed -gt 0) {
    exit 1
}
exit 0
