# tools/drills/trigger-operator-drill.ps1
<#
Operator Kill-Switch Drill:
  - emits a local console alert (Write-Warning) to prompt the operator
  - waits for operator to activate the kill-switch (manual step)
  - verifies kill-switch state via get_kill_switch_details()
  - optionally runs LR-003 repo-local gate drill for fail-closed evidence
  - captures docker compose logs under service_logs/
  - writes timeline.json with real timestamps
  - writes machine-readable verification artifacts under reports/

BLOCKER NOTE — Alert Trigger:
  The Alertmanager config (infrastructure/monitoring/alertmanager.yml) is
  documented as "NOT used" in docs/operations/ALERTING_FIX_SUMMARY.md.
  Current alerting runs via Grafana UI (not provisioned in the repo).
  This drill therefore uses a local console alert as trigger.
  A real external alert channel (webhook/email/PagerDuty) requires
  upstream work outside #661 scope.

BLOCKER NOTE — Order Flow Stop (Runtime):
  Verifying "order flow actually stopped" at runtime (e.g. via metrics
  or live log markers) requires a running stack with active order flow.
  This drill verifies kill-switch state (the canonical gate).
  The LR-003 drill provides deterministic proof that the fail-closed
  gates (risk + execution) block when kill-switch is active.
  Full runtime verification depends on #657.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$EvidenceDir,
  [string]$ComposeFile = "docker-compose.yml",
  [string]$RepoRoot = "",
  [switch]$SkipLr003,
  [switch]$SkipStackLogs,
  [int]$WaitSeconds = 0
)

$ErrorActionPreference = "Stop"

# --- Helpers ---

function Stamp([System.Collections.ArrayList]$Timeline, [string]$Event, [string]$Detail) {
  $entry = [ordered]@{
    ts    = (Get-Date -Format "o")
    event = $Event
  }
  if ($Detail) { $entry["detail"] = $Detail }
  $null = $Timeline.Add([pscustomobject]$entry)
}

# --- Resolve repo root ---

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")).Path
}
$PackRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..") -ErrorAction SilentlyContinue
$ReadmeTemplate = Join-Path $PackRoot "templates\evidence_pack_README.md"

# --- Evidence directory structure ---

New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceDir "screenshots") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceDir "service_logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceDir "reports") | Out-Null

# Copy README template if available
if (Test-Path $ReadmeTemplate) {
  Copy-Item -Force $ReadmeTemplate (Join-Path $EvidenceDir "README.md")
}

$timeline = New-Object System.Collections.ArrayList

# --- Write run_config.json ---

$runConfig = [ordered]@{
  ts_utc       = (Get-Date -Format "o")
  drill_type   = "operator_kill_switch"
  evidence_dir = $EvidenceDir
  repo_root    = $RepoRoot
  compose_file = $ComposeFile
  skip_lr003   = [bool]$SkipLr003
  skip_stack_logs = [bool]$SkipStackLogs
  wait_seconds = $WaitSeconds
}
$runConfig | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "run_config.json") -Encoding utf8

# --- Write sources_manifest.txt ---

$sources = @()
$drillScript = $PSCommandPath
if ($drillScript -and (Test-Path $drillScript)) {
  $sources += [ordered]@{ path = $drillScript; sha256 = (Get-FileHash $drillScript).Hash }
}
$killSwitchPy = Join-Path $RepoRoot "core\safety\kill_switch.py"
if (Test-Path $killSwitchPy) {
  $sources += [ordered]@{ path = $killSwitchPy; sha256 = (Get-FileHash $killSwitchPy).Hash }
}
$lr003Script = Join-Path $RepoRoot "scripts\drills\lr003_kill_switch_limit_controls_runner.py"
if (Test-Path $lr003Script) {
  $sources += [ordered]@{ path = $lr003Script; sha256 = (Get-FileHash $lr003Script).Hash }
}
$sources | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "sources_manifest.txt") -Encoding utf8

# === DRILL START ===

Stamp $timeline "DRILL_START"

# --- Step 1: Alert Trigger (local console) ---

$alertPayload = [ordered]@{
  type       = "OPERATOR_DRILL_ALERT"
  severity   = "critical"
  message    = "Kill-Switch Drill: Activate the kill-switch NOW"
  source     = "trigger-operator-drill.ps1"
  timestamp  = (Get-Date -Format "o")
  action_required = "Activate kill-switch via CLI, then return to this terminal"
  instruction = "python -c `"from core.safety.kill_switch import activate_kill_switch, KillSwitchReason; activate_kill_switch(KillSwitchReason.MANUAL, 'Operator drill', 'drill-operator')`""
}

Write-Warning "================================================================"
Write-Warning "  OPERATOR DRILL ALERT - Kill-Switch Drill"
Write-Warning "================================================================"
Write-Warning "  ACTION REQUIRED: Activate the kill-switch NOW."
Write-Warning ""
Write-Warning "  Run this command from the repo root:"
Write-Warning "    python -c `"from core.safety.kill_switch import activate_kill_switch, KillSwitchReason; activate_kill_switch(KillSwitchReason.MANUAL, 'Operator drill', 'drill-operator')`""
Write-Warning ""
Write-Warning "  Then return to this terminal."
Write-Warning "================================================================"

$alertPayload | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "alert_trigger.json") -Encoding utf8
Stamp $timeline "ALERT_TRIGGERED" "Local console alert emitted; payload written to alert_trigger.json"

# --- Step 2: Wait for operator action ---

if ($WaitSeconds -gt 0) {
  Stamp $timeline "OPERATOR_WAIT_START" "Waiting ${WaitSeconds}s for operator to activate kill-switch"
  Write-Host "Waiting ${WaitSeconds} seconds for operator to activate kill-switch..."
  Start-Sleep -Seconds $WaitSeconds
  Stamp $timeline "OPERATOR_WAIT_END"
} else {
  Stamp $timeline "OPERATOR_WAIT_SKIPPED" "WaitSeconds=0; proceeding to verification immediately"
}

# --- Step 3: Kill-Switch Verification via get_kill_switch_details() ---

Stamp $timeline "VERIFY_KILL_SWITCH_START"

$verifyPy = @"
import json, sys, os
sys.path.insert(0, os.environ.get('CDB_REPO_ROOT', '.'))
try:
    from core.safety.kill_switch import get_kill_switch_details
    active, reason, message, activated_at = get_kill_switch_details(create_if_missing=False)
    result = {
        'kill_switch_active': active,
        'reason': reason,
        'message': message,
        'activated_at': activated_at,
        'verification_source': 'get_kill_switch_details()',
        'verified_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if active else 1)
except Exception as e:
    result = {
        'kill_switch_active': None,
        'error': str(e),
        'verification_source': 'get_kill_switch_details()',
        'verified_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(2)
"@

$verifyReport = Join-Path $EvidenceDir "reports\kill_switch_verification.json"
$env:CDB_REPO_ROOT = $RepoRoot
try {
  $verifyOutput = python -c $verifyPy 2>&1
  $verifyExitCode = $LASTEXITCODE
  $verifyOutput | Out-File -FilePath $verifyReport -Encoding utf8

  if ($verifyExitCode -eq 0) {
    Stamp $timeline "VERIFY_KILL_SWITCH_ACTIVE" "Kill-switch confirmed ACTIVE"
    Write-Host "Kill-switch verification: ACTIVE (PASS)"
  } elseif ($verifyExitCode -eq 1) {
    Stamp $timeline "VERIFY_KILL_SWITCH_INACTIVE" "Kill-switch is INACTIVE — operator did not activate"
    Write-Warning "Kill-switch verification: INACTIVE (operator did not activate)"
  } else {
    Stamp $timeline "VERIFY_KILL_SWITCH_ERROR" "Verification failed with exit code $verifyExitCode"
    Write-Warning "Kill-switch verification: ERROR (exit code $verifyExitCode)"
  }
} catch {
  Stamp $timeline "VERIFY_KILL_SWITCH_ERROR" $_.Exception.Message
  @{ error = $_.Exception.Message; verified_at = (Get-Date -Format "o") } |
    ConvertTo-Json -Depth 6 |
    Out-File -FilePath $verifyReport -Encoding utf8
}

# --- Step 4: Optional LR-003 fail-closed gate drill ---

if (-not $SkipLr003) {
  Stamp $timeline "LR003_DRILL_START"
  $lr003OutDir = Join-Path $EvidenceDir "reports\lr003"
  try {
    $lr003Output = python (Join-Path $RepoRoot "scripts\drills\lr003_kill_switch_limit_controls_runner.py") --output-dir $lr003OutDir 2>&1
    $lr003Exit = $LASTEXITCODE
    if ($lr003Exit -eq 0) {
      Stamp $timeline "LR003_DRILL_PASS" "All fail-closed gates verified"
    } else {
      Stamp $timeline "LR003_DRILL_FAIL" "Exit code $lr003Exit"
    }
  } catch {
    Stamp $timeline "LR003_DRILL_ERROR" $_.Exception.Message
    $_.Exception.Message | Out-File -FilePath (Join-Path $EvidenceDir "reports\lr003_error.txt") -Encoding utf8
  }
} else {
  Stamp $timeline "LR003_DRILL_SKIPPED"
}

# --- Step 5: Capture stack logs ---

if (-not $SkipStackLogs) {
  try {
    Stamp $timeline "CAPTURE_STACK_LOGS"
    docker compose -f $ComposeFile logs --no-color > (Join-Path $EvidenceDir "service_logs\stack.log")
    Stamp $timeline "CAPTURE_STACK_LOGS_OK"
  } catch {
    Stamp $timeline "CAPTURE_STACK_LOGS_FAILED" $_.Exception.Message
    $_.Exception.Message | Out-File -FilePath (Join-Path $EvidenceDir "service_logs\stack_logs_error.txt") -Encoding utf8
  }
} else {
  Stamp $timeline "CAPTURE_STACK_LOGS_SKIPPED"
}

# === DRILL END ===

Stamp $timeline "DRILL_END"
$timeline | ConvertTo-Json -Depth 6 | Out-File (Join-Path $EvidenceDir "timeline.json") -Encoding utf8

# --- Summary output ---

Write-Host ""
Write-Host "=== Operator Drill Complete ==="
Write-Host "Evidence directory: $EvidenceDir"
Write-Host "Timeline events:   $($timeline.Count)"
Write-Host ""
Write-Host "Evidence artifacts:"
Write-Host "  timeline.json"
Write-Host "  alert_trigger.json"
Write-Host "  reports/kill_switch_verification.json"
if (-not $SkipLr003) { Write-Host "  reports/lr003/ (fail-closed gate evidence)" }
Write-Host "  service_logs/"
Write-Host "  screenshots/ (manual operator screenshots)"
Write-Host "  run_config.json"
Write-Host "  sources_manifest.txt"
