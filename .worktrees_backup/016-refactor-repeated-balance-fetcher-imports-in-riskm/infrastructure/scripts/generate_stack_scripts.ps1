param(
    [string]$InventoryRelativePath = '..\Claire_de_Binare_Docs\knowledge\stack\CDB_DOCKER_STACK_INVENTORY.md'
)

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
$InventoryPath = Resolve-Path (Join-Path $RepoRoot $InventoryRelativePath)
$Inventory = Get-Content -Path $InventoryPath -Raw -Encoding UTF8

$composeMatch = [regex]::Match($Inventory, "```[\r\n]+(?<cmd>docker compose[^\r\n]+)[\r\n]+```", [System.Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $composeMatch.Success) {
    throw "Unable to extract compose invocation from inventory."
}
$composeCommand = $composeMatch.Groups['cmd'].Value.Trim()

$servicesSectionMatch = [regex]::Match($Inventory, "## Services\s*(?<body>.*?)## Service dependency links", [System.Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $servicesSectionMatch.Success) {
    throw "Unable to locate Services table in inventory."
}

$serviceLines = $servicesSectionMatch.Groups['body'].Value -split '\r?\n'
$collectServices = $false
$serviceNames = [System.Collections.Generic.List[string]]::new()
foreach ($line in $serviceLines) {
    $trimmed = $line.Trim()
    if ($trimmed -like '| ---*') {
        $collectServices = $true
        continue
    }
    if (-not $collectServices) {
        continue
    }
    if ($trimmed -eq '') {
        continue
    }
    if ($trimmed.StartsWith('|')) {
        $parts = $line -split '\|'
        if ($parts.Length -gt 1) {
            $name = $parts[1].Trim()
            if ($name -eq 'Service') {
                continue
            }
            if ($name -match '^`(.+)`$') {
                $name = $Matches[1]
            }
            if ($name) {
                $serviceNames.Add($name)
            }
        }
    }
}

$secretsSectionMatch = [regex]::Match($Inventory, "## Secrets & env contract\s*(?<body>.*?)## Networks", [System.Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $secretsSectionMatch.Success) {
    throw "Unable to locate Secrets table in inventory."
}

$secretsLines = $secretsSectionMatch.Groups['body'].Value -split '\r?\n'
$collectSecrets = $false
$runtimeSecrets = [System.Collections.Generic.List[pscustomobject]]::new()
foreach ($line in $secretsLines) {
    $trimmed = $line.Trim()
    if ($trimmed -like '| ---*') {
        $collectSecrets = $true
        continue
    }
    if (-not $collectSecrets) {
        continue
    }
    if ($trimmed -eq '') {
        continue
    }
    if ($trimmed.StartsWith('|')) {
        $parts = $line -split '\|'
        if ($parts.Length -ge 4) {
            $name = $parts[1].Trim()
            $status = $parts[3].Trim()
            if ($name -match '^`(.+)`$') {
                $name = $Matches[1]
            }
            if ($name -and $status) {
                $runtimeSecrets.Add([pscustomobject]@{
                    Name   = $name
                    Status = $status
                })
            }
        }
    }
}

$servicesLine = ($serviceNames -join ' ')

function EscapeLiteral($value) {
    return ($value -replace "'", "''")
}

$composeLiteral = EscapeLiteral($composeCommand)
$servicesLiteral = EscapeLiteral($servicesLine)

$secretEntries = $runtimeSecrets | ForEach-Object {
    $escapedName = EscapeLiteral($_.Name)
    $escapedStatus = EscapeLiteral($_.Status)
    "  [pscustomobject]@{{ Name = '{0}'; Path = '.\.cdb_local\.secrets\{0}'; Status = '{1}' }}" -f $escapedName, $escapedStatus
}

$secretBlock = ($secretEntries -join "`r`n")

$scriptHeader = "# GENERATED FROM CDB_DOCKER_STACK_INVENTORY.md — DO NOT EDIT MANUALLY"

$stackUpTemplate = @'
$scriptHeader
param([switch]$Rebuild)

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot

$composeCommand = '{0}'
$servicesLine = '{1}'
$envFile = ".\.cdb_local\.secrets\.env.compose"

$runtimeSecrets = @(
{2}
)

$missingSecrets = $runtimeSecrets | Where-Object { $_.Status -match 'MISSING' } | Select-Object -ExpandProperty Name
if ($missingSecrets) {
    Write-Error ("Missing runtime secrets: {0}" -f ($missingSecrets -join ', '))
    exit 1
}

if (-not (Test-Path $envFile)) {
    Write-Error "Env file '$envFile' is missing."
    exit 1
}

if ($Rebuild) {
    Write-Host "Building services: $servicesLine"
    Invoke-Expression ("{0} build {1}" -f $composeCommand, $servicesLine)
}

Write-Host "Starting services: $servicesLine"
Invoke-Expression ("{0} up -d {1}" -f $composeCommand, $servicesLine)

$maxWait = 120
$checkInterval = 5
$elapsed = 0
while ($elapsed -lt $maxWait) {
    $raw = Invoke-Expression ("{0} ps --format json" -f $composeCommand)
    try {
        $payload = ($raw | Out-String) | ConvertFrom-Json
    } catch {
        break
    }
    $pending = $payload | Where-Object { $_.State -ne 'running' -or ($_.Health -and $_.Health.Status -ne 'healthy') }
    if (-not $pending) {
        break
    }
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
}

Write-Host "Final status after waiting $elapsed seconds."
Invoke-Expression ("{0} ps" -f $composeCommand)
'@

$stackDownTemplate = @'
$scriptHeader

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot

$composeCommand = '{0}'
Write-Host "Stopping stack"
Invoke-Expression ("{0} down" -f $composeCommand)
'@

$stackStatusTemplate = @'
$scriptHeader

$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot

$composeCommand = '{0}'

Write-Host "Collecting service status..."
$raw = Invoke-Expression ("{0} ps --format json" -f $composeCommand)
try {
    $payload = ($raw | Out-String) | ConvertFrom-Json
} catch {
    $payload = $null
}

$entries = @()
if ($payload) {
    if ($payload -is [System.Array]) {
        $entries = $payload
    } elseif ($payload) {
        $entries = @($payload)
    }
}

$unhealthy = $entries | Where-Object { $_.State -ne 'running' -or ($_.Health -and $_.Health.Status -ne 'healthy') }
if ($unhealthy) {
    Write-Host "Non-healthy services detected:"
    foreach ($service in $unhealthy) {
        Write-Host " - $($service.Name): state=$($service.State), health=$($service.Health.Status)"
        Invoke-Expression ("{0} logs --no-color --tail 120 {1}" -f $composeCommand, $service.Name)
    }
} else {
    Write-Host "All services running and healthy."
}

Invoke-Expression ("{0} ps" -f $composeCommand)
'@

$generatedScripts = @{
    'stack_up.ps1'    = $stackUpTemplate -f $composeLiteral, $servicesLiteral, $secretBlock
    'stack_down.ps1'  = $stackDownTemplate -f $composeLiteral
    'stack_status.ps1' = $stackStatusTemplate -f $composeLiteral
}

foreach ($entry in $generatedScripts.GetEnumerator()) {
    $path = Join-Path $PSScriptRoot $entry.Key
    Set-Content -Path $path -Value $entry.Value -Encoding UTF8
}
