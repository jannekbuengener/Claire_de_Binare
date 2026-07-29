[CmdletBinding()]
param(
    [string]$CommitSha = "",
    [string]$ProjectName = "",
    [string]$EvidenceRoot = "artifacts/evidence-runs/4184",
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$actualSha = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Cannot resolve git HEAD."
}
if ($CommitSha -and $CommitSha -ne $actualSha) {
    throw "SHA mismatch: requested=$CommitSha actual=$actualSha"
}
$CommitSha = $actualSha

$dirtyLines = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw "Cannot inspect worktree state."
}
$dirty = $dirtyLines.Count -gt 0
if ($dirty -and -not $AllowDirty) {
    throw "Dirty worktree: commit the exact drill surface first."
}

$sha8 = $CommitSha.Substring(0, 8)
if (-not $ProjectName) {
    $ProjectName = "cdb_4184_$sha8"
}
if ($ProjectName -notmatch '^[a-z0-9][a-z0-9_-]{2,40}$') {
    throw "Unsafe Compose project name: $ProjectName"
}

$runId = "4184_${sha8}_$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))"
$evidenceDir = Join-Path $repoRoot (Join-Path $EvidenceRoot $runId)
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
$evidenceDir = (Resolve-Path $evidenceDir).Path

$baseFile = Join-Path $repoRoot "infrastructure\compose\base.yml"
$testFile = Join-Path $repoRoot "infrastructure\compose\test.yml"
$overlayFile = Join-Path $repoRoot "infrastructure\compose\issue-4182-kill-unwind.yml"
$composeFiles = @("-f", $baseFile, "-f", $testFile, "-f", $overlayFile)

$secretRoot = Join-Path ([IO.Path]::GetTempPath()) "cdb-4184-$([Guid]::NewGuid())"
New-Item -ItemType Directory -Path $secretRoot | Out-Null
Set-Content -LiteralPath (Join-Path $secretRoot "REDIS_PASSWORD") -Value "cdb-4184-redis-only" -NoNewline
Set-Content -LiteralPath (Join-Path $secretRoot "POSTGRES_PASSWORD") -Value "cdb-4184-postgres-only" -NoNewline

$env:STACK_NAME = $ProjectName
$env:SECRETS_PATH = $secretRoot
$env:REDIS_PASSWORD = "cdb-4184-redis-only"
$env:POSTGRES_PASSWORD = "cdb-4184-postgres-only"
$env:POSTGRES_USER = "claire_user"
$env:CDB_GIT_COMMIT = $CommitSha
$env:CDB_POLICY_VERSION = "issue-4184-drill"
# Reuse the #4182 overlay mount without creating a parallel stack surface.
$env:CDB_4182_EVIDENCE_DIR = $evidenceDir

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$Capture
    )
    if ($Capture) {
        $result = & docker compose -p $ProjectName @composeFiles @Arguments 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose failed: $($Arguments -join ' ')"
        }
        return @($result)
    }
    & docker compose -p $ProjectName @composeFiles @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
}

function Wait-ContainerReady {
    param([string]$ContainerName)
    $deadline = [DateTime]::UtcNow.AddMinutes(3)
    while ([DateTime]::UtcNow -lt $deadline) {
        $state = (& docker inspect --format "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}" $ContainerName 2>$null)
        if ($LASTEXITCODE -eq 0 -and $state -match '^running\|(healthy)?$') {
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "Container did not become ready: $ContainerName"
}

$initialExit = 1
$setupExit = 1
$restartExit = 1
$cleanupPass = $false
$runtimeSafeModeVerified = $false
$containerIds = [ordered]@{}
$runError = $null
$remainingContainers = @()
$remainingVolumes = @()
$remainingNetworks = @()

try {
    $configJson = (Invoke-Compose -Arguments @("config", "--format", "json") -Capture) -join "`n"
    $resolved = $configJson | ConvertFrom-Json

    foreach ($serviceName in @(
        "cdb_execution_test",
        "cdb_risk_test",
        "cdb_test_runner"
    )) {
        $service = $resolved.services.$serviceName
        if ($null -eq $service) {
            throw "Resolved Compose is missing $serviceName."
        }
        if ($service.environment.DRY_RUN -notin @("1", "true")) {
            throw "$serviceName does not enforce DRY_RUN."
        }
        if ($service.environment.MOCK_TRADING -ne "true") {
            throw "$serviceName does not enforce MOCK_TRADING=true."
        }
        if ($service.environment.USE_REAL_BALANCE -ne "false") {
            throw "$serviceName does not enforce USE_REAL_BALANCE=false."
        }
    }
    foreach ($serviceProperty in $resolved.services.PSObject.Properties) {
        if (
            $serviceProperty.Value.PSObject.Properties.Name -contains "ports" -and
            $serviceProperty.Value.ports
        ) {
            throw "$($serviceProperty.Name) exposes host ports."
        }
    }
    $resolvedText = $configJson.ToLowerInvariant()
    if ($resolvedText.Contains("compose.blue.yml") -or $resolvedText.Contains("compose.red.yml")) {
        throw "BLUE/RED activation detected."
    }
    foreach ($serviceProperty in $resolved.services.PSObject.Properties) {
        $serviceSecrets = @()
        if ($serviceProperty.Value.PSObject.Properties.Name -contains "secrets") {
            $serviceSecrets = @($serviceProperty.Value.secrets)
        }
        if (
            @(
                $serviceSecrets |
                    Where-Object {
                        $_.source -in @("mexc_api_key", "mexc_api_secret")
                    }
            ).Count -gt 0
        ) {
            throw "Productive exchange credentials detected."
        }
    }
    $redactedConfig = $configJson.Replace(
        "cdb-4184-redis-only", "<REDACTED>"
    ).Replace(
        "cdb-4184-postgres-only", "<REDACTED>"
    ).Replace(
        $secretRoot.Replace("\", "\\"), "<TEMP_SECRET_PATH>"
    )
    Set-Content -LiteralPath (Join-Path $evidenceDir "compose.resolved.redacted.json") -Value $redactedConfig

    Invoke-Compose -Arguments @("build", "cdb_execution_test", "cdb_test_runner")
    Invoke-Compose -Arguments @(
        "up", "-d", "cdb_redis", "cdb_postgres", "cdb_execution_test"
    )
    foreach ($container in @(
        "${ProjectName}_redis",
        "${ProjectName}_postgres",
        "${ProjectName}_execution"
    )) {
        Wait-ContainerReady -ContainerName $container
        $containerIds[$container] = (& docker inspect --format "{{.Image}}" $container).Trim()
    }
    $runtimeFlags = (
        & docker exec "${ProjectName}_execution" python -c `
            "from services.execution import config; print(f'{int(config.DRY_RUN)}|{int(config.MOCK_TRADING)}')"
    ).Trim()
    if ($LASTEXITCODE -ne 0 -or $runtimeFlags -ne "1|1") {
        throw "Execution runtime did not load DRY_RUN=1 and MOCK_TRADING=true."
    }
    $runtimeSafeModeVerified = $true

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $initialOutput = & docker compose -p $ProjectName @composeFiles run --rm cdb_test_runner `
        python -m pytest -q tests/e2e/test_reduce_only_unwind_drill.py `
        -k "not test_r9_prepare_partial_before_restart and not test_r9_restart_after_partial_does_not_reapply_fill" `
        --junitxml=/app/evidence/r1-r8-r10.xml 2>&1
    $initialExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    Set-Content -LiteralPath (Join-Path $evidenceDir "r1-r8-r10.log") -Value $initialOutput
    if (Test-Path (Join-Path $evidenceDir "scenarios.json")) {
        Move-Item -LiteralPath (Join-Path $evidenceDir "scenarios.json") -Destination (Join-Path $evidenceDir "scenarios-initial.json")
    }

    $ErrorActionPreference = "Continue"
    $setupOutput = & docker compose -p $ProjectName @composeFiles run --rm cdb_test_runner `
        python -m pytest -q tests/e2e/test_reduce_only_unwind_drill.py `
        -k "test_r9_prepare_partial_before_restart" `
        --junitxml=/app/evidence/r9-setup.xml 2>&1
    $setupExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    Set-Content -LiteralPath (Join-Path $evidenceDir "r9-setup.log") -Value $setupOutput
    if (Test-Path (Join-Path $evidenceDir "scenarios.json")) {
        Move-Item -LiteralPath (Join-Path $evidenceDir "scenarios.json") -Destination (Join-Path $evidenceDir "scenarios-setup.json")
    }

    Invoke-Compose -Arguments @("restart", "cdb_execution_test")
    Wait-ContainerReady -ContainerName "${ProjectName}_execution"

    $ErrorActionPreference = "Continue"
    $restartOutput = & docker compose -p $ProjectName @composeFiles run --rm cdb_test_runner `
        python -m pytest -q tests/e2e/test_reduce_only_unwind_drill.py `
        -k "test_r9_restart_after_partial_does_not_reapply_fill" `
        --junitxml=/app/evidence/r9.xml 2>&1
    $restartExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    Set-Content -LiteralPath (Join-Path $evidenceDir "r9.log") -Value $restartOutput
    if (Test-Path (Join-Path $evidenceDir "scenarios.json")) {
        Move-Item -LiteralPath (Join-Path $evidenceDir "scenarios.json") -Destination (Join-Path $evidenceDir "scenarios-restart.json")
    }
}
catch {
    $runError = $_.Exception.Message
}
finally {
    try {
        & docker compose -p $ProjectName @composeFiles down --volumes --remove-orphans
        $downExit = $LASTEXITCODE
        $remainingContainers = @(
            & docker ps -a --filter "label=com.docker.compose.project=$ProjectName" -q
        )
        $remainingVolumes = @(
            & docker volume ls --filter "label=com.docker.compose.project=$ProjectName" -q
        )
        $remainingNetworks = @(
            & docker network ls --filter "label=com.docker.compose.project=$ProjectName" -q
        )
        $cleanupPass = (
            $downExit -eq 0 -and
            $remainingContainers.Count -eq 0 -and
            $remainingVolumes.Count -eq 0 -and
            $remainingNetworks.Count -eq 0
        )
    }
    catch {
        $cleanupPass = $false
        if (-not $runError) {
            $runError = "Cleanup failed: $($_.Exception.Message)"
        }
    }
    if (Test-Path -LiteralPath $secretRoot) {
        Remove-Item -LiteralPath $secretRoot -Recurse -Force
    }
}

$scenarioResults = [ordered]@{}
foreach ($scenarioFile in @(
    "scenarios-initial.json",
    "scenarios-setup.json",
    "scenarios-restart.json"
)) {
    $path = Join-Path $evidenceDir $scenarioFile
    if (Test-Path $path) {
        $parsed = Get-Content -Raw $path | ConvertFrom-Json -AsHashtable
        foreach ($key in $parsed.Keys) {
            $scenarioResults[$key] = $parsed[$key]
        }
    }
}

$requiredScenarios = @(
    "R1_LONG_FULL_EXIT",
    "R2_SHORT_FULL_EXIT",
    "R3_LONG_PARTIAL_FILL",
    "R4_SHORT_PARTIAL_FILL",
    "R5_OVERSIZED_LONG_EXIT",
    "R6_OVERSIZED_SHORT_EXIT",
    "R7_ADAPTER_REJECTION",
    "R8_DUPLICATE_RESULT",
    "R9_RESTART_AFTER_PARTIAL",
    "R10_UNKNOWN_POSITION"
)
foreach ($scenario in $requiredScenarios) {
    if (-not $scenarioResults.Contains($scenario)) {
        $scenarioResults[$scenario] = [ordered]@{
            status = "NOT_RUN"
            position_increase_observed = $false
            side_flip_observed = $false
        }
    }
}

$allPass = @(
    $requiredScenarios |
        Where-Object { $scenarioResults[$_].status -ne "PASS" }
).Count -eq 0
$positionIncrease = @(
    $requiredScenarios |
        Where-Object { $scenarioResults[$_].position_increase_observed -eq $true }
).Count -gt 0
$sideFlip = @(
    $requiredScenarios |
        Where-Object { $scenarioResults[$_].side_flip_observed -eq $true }
).Count -gt 0
$overall = if (
    $initialExit -eq 0 -and
    $setupExit -eq 0 -and
    $restartExit -eq 0 -and
    $cleanupPass -and
    $runtimeSafeModeVerified -and
    $allPass -and
    -not $positionIncrease -and
    -not $sideFlip -and
    -not $dirty -and
    -not $runError
) {
    "PASS_REDUCE_ONLY_PROVEN_MOCK_SHADOW"
}
else {
    "INCOMPLETE"
}

$artifactHashes = [ordered]@{}
Get-ChildItem -LiteralPath $evidenceDir -File |
    Where-Object { $_.Name -ne "manifest.json" } |
    Sort-Object Name |
    ForEach-Object {
        $artifactHashes[$_.Name] = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }

$composeHashes = [ordered]@{}
foreach ($file in @($baseFile, $testFile, $overlayFile)) {
    $composeHashes[(Resolve-Path -Relative $file)] = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $file
    ).Hash.ToLowerInvariant()
}

$manifest = [ordered]@{
    schema_version = "1.0"
    issue = 4184
    proof_type = "reduce_only_unwind_contract"
    run_id = $runId
    tested_commit_sha = $CommitSha
    branch = (git branch --show-current).Trim()
    base_sha = (git merge-base HEAD origin/main).Trim()
    contract_version = "execution_reduce_only_v1"
    position_sign_convention = "long_positive_short_negative"
    quantity_unit = "base_asset"
    safe_mode_flags = [ordered]@{
        dry_run = $true
        mock_trading = $true
        use_real_balance = $false
        blue_red_activated = $false
        productive_credentials = $false
        execution_runtime_verified = $runtimeSafeModeVerified
    }
    scenario_results = $scenarioResults
    position_increase_observed = $positionIncrease
    side_flip_observed = $sideFlip
    reason_codes = @(
        "REDUCE_ONLY_POSITION_UNKNOWN",
        "REDUCE_ONLY_NO_POSITION",
        "REDUCE_ONLY_INVALID_QUANTITY",
        "REDUCE_ONLY_QUANTITY_CLAMPED",
        "REDUCE_ONLY_SIDE_MISMATCH",
        "REDUCE_ONLY_REJECTED",
        "REDUCE_ONLY_PARTIAL_FILL",
        "REDUCE_ONLY_DUPLICATE_RESULT",
        "REDUCE_ONLY_POSITION_INCREASE_BLOCKED"
    )
    artifact_sha256 = $artifactHashes
    compose_sha256 = $composeHashes
    image_ids = $containerIds
    cleanup_result = [ordered]@{
        pass = $cleanupPass
        containers_remaining = $remainingContainers.Count
        volumes_remaining = $remainingVolumes.Count
        networks_remaining = $remainingNetworks.Count
    }
    limitations = @(
        "Mock/shadow proof only; productive adapter reduce-only support remains unproven.",
        "Crash after preparation and before finalization remains fail-closed and requires reconciliation.",
        "Stop-loss protection remains UNAVAILABLE.",
        "LR remains NO-GO."
    )
    verdict = $overall
    run_error = $runError
}
$manifest |
    ConvertTo-Json -Depth 12 |
    Set-Content -LiteralPath (Join-Path $evidenceDir "manifest.json") -Encoding utf8

Write-Host "Evidence: $evidenceDir"
Write-Host "Verdict: $overall"
if ($overall -ne "PASS_REDUCE_ONLY_PROVEN_MOCK_SHADOW") {
    exit 1
}
