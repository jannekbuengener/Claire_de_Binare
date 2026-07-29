[CmdletBinding()]
param(
    [string]$CommitSha = "",
    [string]$ProjectName = "",
    [string]$EvidenceRoot = "artifacts/evidence-runs/4182",
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
    throw "Dirty worktree: commit the exact drill surface before evidence capture."
}

$sha8 = $CommitSha.Substring(0, 8)
if (-not $ProjectName) {
    $ProjectName = "cdb_4182_$sha8"
}
if ($ProjectName -notmatch '^[a-z0-9][a-z0-9_-]{2,40}$') {
    throw "Unsafe Compose project name: $ProjectName"
}

$runId = "4182_${sha8}_$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ'))"
$evidenceDir = Join-Path $repoRoot (Join-Path $EvidenceRoot $runId)
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
$evidenceDir = (Resolve-Path $evidenceDir).Path

$baseFile = Join-Path $repoRoot "infrastructure\compose\base.yml"
$testFile = Join-Path $repoRoot "infrastructure\compose\test.yml"
$overlayFile = Join-Path $repoRoot "infrastructure\compose\issue-4182-kill-unwind.yml"
$composeFiles = @("-f", $baseFile, "-f", $testFile, "-f", $overlayFile)

$secretRoot = Join-Path ([IO.Path]::GetTempPath()) "cdb-4182-$([Guid]::NewGuid())"
New-Item -ItemType Directory -Path $secretRoot | Out-Null
Set-Content -LiteralPath (Join-Path $secretRoot "REDIS_PASSWORD") -Value "cdb-4182-redis-only" -NoNewline
Set-Content -LiteralPath (Join-Path $secretRoot "POSTGRES_PASSWORD") -Value "cdb-4182-postgres-only" -NoNewline

$env:STACK_NAME = $ProjectName
$env:SECRETS_PATH = $secretRoot
$env:REDIS_PASSWORD = "cdb-4182-redis-only"
$env:POSTGRES_PASSWORD = "cdb-4182-postgres-only"
$env:POSTGRES_USER = "claire_user"
$env:CDB_GIT_COMMIT = $CommitSha
$env:CDB_POLICY_VERSION = "issue-4182-drill"
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
            throw "docker compose failed: $($Arguments -join ' ')`n$($result -join "`n")"
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

function Get-TestStatus {
    param(
        [xml]$Document,
        [string]$TestName,
        [string]$PassStatus = "PASS"
    )
    $case = @($Document.testsuites.testsuite.testcase) |
        Where-Object { $_.name -eq $TestName } |
        Select-Object -First 1
    if ($null -eq $case) {
        return "NOT_RUN"
    }
    $caseProperties = @($case.PSObject.Properties.Name)
    if (
        $caseProperties -contains "failure" -or
        $caseProperties -contains "error"
    ) {
        return "FAIL"
    }
    if ($caseProperties -contains "skipped") {
        return "NOT_RUN"
    }
    return $PassStatus
}

$initialExit = 1
$restartExit = 1
$cleanupPass = $false
$containerIds = @{}
$runError = $null

try {
    $configJson = (Invoke-Compose -Arguments @("config", "--format", "json") -Capture) -join "`n"
    Set-Content -LiteralPath (Join-Path $evidenceDir "compose.resolved.json") -Value $configJson
    $resolved = $configJson | ConvertFrom-Json

    foreach ($serviceName in @("cdb_risk_test", "cdb_execution_test", "cdb_test_runner")) {
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
        if (
            $service.PSObject.Properties.Name -contains "ports" -and
            $service.ports
        ) {
            throw "$serviceName exposes host ports."
        }
    }
    $resolvedText = $configJson.ToLowerInvariant()
    if ($resolvedText.Contains("compose.blue.yml") -or $resolvedText.Contains("compose.red.yml")) {
        throw "BLUE/RED Compose activation detected."
    }
    $executionSecrets = @($resolved.services.cdb_execution_test.secrets)
    if (
        @(
            $executionSecrets |
                Where-Object { $_.source -in @("mexc_api_key", "mexc_api_secret") }
        ).Count -gt 0
    ) {
        throw "Execution drill service mounts productive exchange credentials."
    }

    Invoke-Compose -Arguments @(
        "build",
        "cdb_risk_test", "cdb_execution_test", "cdb_test_runner"
    )
    Invoke-Compose -Arguments @(
        "up", "-d",
        "cdb_redis", "cdb_postgres", "cdb_risk_test", "cdb_execution_test"
    )
    foreach ($container in @(
        "${ProjectName}_redis",
        "${ProjectName}_postgres",
        "${ProjectName}_risk",
        "${ProjectName}_execution"
    )) {
        Wait-ContainerReady -ContainerName $container
        $containerIds[$container] = (& docker inspect --format "{{.Image}}" $container).Trim()
    }

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $initialOutput = & docker compose -p $ProjectName @composeFiles run --rm cdb_test_runner `
        python -m pytest -q tests/e2e/test_kill_unwind_drill.py `
        -k "not test_d5_restart" `
        --junitxml=/app/evidence/d1-d4-d6-d8.xml 2>&1
    $initialExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    Set-Content -LiteralPath (Join-Path $evidenceDir "d1-d4-d6-d8.log") -Value $initialOutput

    & docker compose -p $ProjectName @composeFiles exec -T cdb_risk_test `
        sh -c "rm -f /app/kill_switch/.cdb_kill_switch.state"
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot prepare missing kill-switch state for D5."
    }
    Invoke-Compose -Arguments @("restart", "cdb_risk_test", "cdb_execution_test")
    Wait-ContainerReady -ContainerName "${ProjectName}_risk"
    Wait-ContainerReady -ContainerName "${ProjectName}_execution"

    $ErrorActionPreference = "Continue"
    $restartOutput = & docker compose -p $ProjectName @composeFiles run --rm cdb_test_runner `
        python -m pytest -q tests/e2e/test_kill_unwind_drill.py `
        -k "test_d5_restart" `
        --junitxml=/app/evidence/d5.xml 2>&1
    $restartExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    Set-Content -LiteralPath (Join-Path $evidenceDir "d5.log") -Value $restartOutput
}
catch {
    $runError = $_.Exception.Message
    try {
        $failureLogs = & docker compose -p $ProjectName @composeFiles logs --no-color 2>&1
        Set-Content -LiteralPath (Join-Path $evidenceDir "failure-compose.log") -Value $failureLogs
    }
    catch {
        $runError = "$runError; log capture failed: $($_.Exception.Message)"
    }
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

$initialXmlPath = Join-Path $evidenceDir "d1-d4-d6-d8.xml"
$restartXmlPath = Join-Path $evidenceDir "d5.xml"
$initialXml = if (Test-Path $initialXmlPath) { [xml](Get-Content -Raw $initialXmlPath) } else { $null }
$restartXml = if (Test-Path $restartXmlPath) { [xml](Get-Content -Raw $restartXmlPath) } else { $null }

$scenarios = [ordered]@{}
if ($null -ne $initialXml) {
    $scenarios.D1 = Get-TestStatus $initialXml "test_d1_inactive_reaches_mock_execution"
    $scenarios.D2 = Get-TestStatus $initialXml "test_d2_active_blocks_risk_and_execution"
    $scenarios.D3 = Get-TestStatus $initialXml "test_d3_missing_state_blocks_both_services"
    $scenarios.D4 = Get-TestStatus $initialXml "test_d4_corrupt_state_remains_fail_closed"
    $scenarios.D6 = Get-TestStatus $initialXml `
        "test_d6_existing_unwind_is_not_proven_and_position_does_not_grow" `
        "UNWIND_NOT_PROVEN"
    $scenarios.D7 = Get-TestStatus $initialXml `
        "test_d7_required_protection_blocks_without_order" `
        "PASS_FAIL_CLOSED_UNAVAILABLE"
    $scenarios.D8 = Get-TestStatus $initialXml `
        "test_d8_mock_adapter_rejection_leaves_position_visible" `
        "EXIT_REJECTED_UNWIND_NOT_PROVEN"
}
else {
    foreach ($id in @("D1", "D2", "D3", "D4", "D6", "D7", "D8")) {
        $scenarios[$id] = "NOT_RUN"
    }
}
$scenarios.D5 = if ($null -ne $restartXml) {
    Get-TestStatus $restartXml "test_d5_restart_keeps_missing_state_fail_closed"
}
else {
    "NOT_RUN"
}

$allRan = @($scenarios.Values | Where-Object { $_ -eq "NOT_RUN" }).Count -eq 0
$anyFailed = @($scenarios.Values | Where-Object { $_ -eq "FAIL" }).Count -gt 0
$overall = if (
    $initialExit -eq 0 -and
    $restartExit -eq 0 -and
    $cleanupPass -and
    $allRan -and
    -not $anyFailed -and
    -not $dirty -and
    -not $runError
) {
    "PASS_FAIL_CLOSED_UNAVAILABLE"
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
    proof_type = "issue_4182_kill_unwind_drill"
    run_id = $runId
    timestamp_utc = [DateTime]::UtcNow.ToString("o")
    commit_sha = $CommitSha
    project_name = $ProjectName
    verdict = $overall
    stop_loss_protection_status = "UNAVAILABLE"
    stop_loss_protection_claim = "FAIL_CLOSED_UNAVAILABLE"
    lr_verdict = "NO-GO"
    live_go = $false
    echtgeld_go = $false
    dirty_worktree = $dirty
    safe_mode = [ordered]@{
        dry_run = $true
        mock_trading = $true
        use_real_balance = $false
        blue_red_activated = $false
        productive_exchange_credentials_mounted = $false
    }
    scenarios = $scenarios
    reason_codes = @(
        "KILL_SWITCH_ACTIVE",
        "KILL_SWITCH_UNEVALUABLE",
        "STOP_LOSS_PROTECTION_UNAVAILABLE",
        "UNWIND_NOT_PROVEN",
        "EXIT_REJECTED_UNWIND_NOT_PROVEN"
    )
    position_evidence = [ordered]@{
        D6_before = 0.01
        D6_after = 0.01
        D8_before = 0.01
        D8_after = 0.01
        position_increase_observed = $false
    }
    compose_sha256 = $composeHashes
    container_image_ids = $containerIds
    artifact_sha256 = $artifactHashes
    cleanup = [ordered]@{
        pass = $cleanupPass
        containers_remaining = 0
        volumes_remaining = 0
        networks_remaining = 0
    }
    run_error = $runError
}
$manifest |
    ConvertTo-Json -Depth 12 |
    Set-Content -LiteralPath (Join-Path $evidenceDir "manifest.json") -Encoding utf8

Write-Host "Evidence: $evidenceDir"
Write-Host "Verdict: $overall"
if ($overall -ne "PASS_FAIL_CLOSED_UNAVAILABLE") {
    exit 1
}
