#Requires -Version 5.1

<#
.SYNOPSIS
    CDB Secret Rotator - Automated secret rotation with governance guardrails.

.DESCRIPTION
    Rotates machine-readable secrets (DB passwords, app keys) while protecting manual secrets (Grafana admin).
    Implements fail-closed validation, safe logging, and two-step plan/apply workflow.
    Uses rotation state tracking to ensure freshness (not just length validation).

.PARAMETER Command
    Operation to perform: plan, apply, or export

.PARAMETER All
    Rotate all auto secrets (exclude_by_default=false)

.PARAMETER Secret
    Rotate specific secret by name

.PARAMETER IncludeManual
    FORBIDDEN - Will cause hard-fail (manual secrets must not be auto-rotated)

.PARAMETER Force
    Force rotation even if state indicates recent rotation (use with caution)

.EXAMPLE
    .\Rotate-Secrets.ps1 plan
    .\Rotate-Secrets.ps1 apply
    .\Rotate-Secrets.ps1 apply -Force
    .\Rotate-Secrets.ps1 export

.NOTES
    Canonical secrets path: C:\Users\janne\Documents\.secrets\.cdb
    Manifest: tools/secrets/secrets.manifest.json
    Rotation state: tools/secrets/.rotation_state.json
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('plan', 'apply', 'export')]
    [string]$Command,

    [switch]$All,
    [string]$Secret,
    [switch]$IncludeManual,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# CONSTANTS
# =============================================================================
$MANIFEST_PATH = Join-Path $PSScriptRoot 'secrets.manifest.json'
$ENV_RUNTIME_PATH = Join-Path $PSScriptRoot '.env.runtime'
$STATE_PATH = Join-Path $PSScriptRoot '.rotation_state.json'
$MAX_AGE_DAYS = 90  # Rotate if older than 90 days

# =============================================================================
# LOGGING (Safe - NO VALUES)
# =============================================================================
function Write-Section($text) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Blue
    Write-Host "  $text" -ForegroundColor Blue
    Write-Host ("=" * 70) -ForegroundColor Blue
}

function Write-Success($text) { Write-Host "[OK]   $text" -ForegroundColor Green }
function Write-Info($text)    { Write-Host "[INFO] $text" -ForegroundColor Cyan }
function Write-Warning($text) { Write-Host "[WARN] $text" -ForegroundColor Yellow }
function Write-Error($text)   { Write-Host "[FAIL] $text" -ForegroundColor Red }

function Write-SecretInfo($name, $mode, $length) {
    # SAFE: Log name, mode, length - NEVER log values
    Write-Info ("Secret: {0,-30} Mode: {1,-8} Length: {2}" -f $name, $mode, $length)
}

# =============================================================================
# ROTATION STATE OPERATIONS
# =============================================================================
function Read-RotationState {
    if (-not (Test-Path $STATE_PATH)) {
        return @{
            version = 1
            secrets = @{}
        }
    }

    try {
        $state = Get-Content $STATE_PATH -Raw | ConvertFrom-Json
        # Convert PSCustomObject to Hashtable for easier manipulation
        $stateHash = @{
            version = $state.version
            secrets = @{}
        }
        if ($state.secrets) {
            $state.secrets.PSObject.Properties | ForEach-Object {
                $stateHash.secrets[$_.Name] = @{
                    last_rotated = $_.Value.last_rotated
                    rotated_by = $_.Value.rotated_by
                    length = $_.Value.length
                    format = $_.Value.format
                }
            }
        }
        return $stateHash
    } catch {
        Write-Warning "Failed to read rotation state: $_"
        Write-Warning "Creating fresh state"
        return @{
            version = 1
            secrets = @{}
        }
    }
}

function Write-RotationState($state) {
    try {
        $state | ConvertTo-Json -Depth 10 | Set-Content -Path $STATE_PATH -Encoding UTF8
    } catch {
        Write-Error "Failed to write rotation state: $_"
        exit 1
    }
}

function Test-SecretFreshness($secretName, $state) {
    if (-not $state.secrets.ContainsKey($secretName)) {
        return $false  # Never rotated = not fresh
    }

    $secretState = $state.secrets[$secretName]
    if (-not $secretState.last_rotated) {
        return $false  # No timestamp = not fresh
    }

    try {
        $lastRotated = [DateTime]::Parse($secretState.last_rotated)
        $age = (Get-Date) - $lastRotated
        return $age.TotalDays -lt $MAX_AGE_DAYS
    } catch {
        Write-Warning "Failed to parse rotation timestamp for $secretName"
        return $false  # Invalid timestamp = not fresh
    }
}

# =============================================================================
# MANIFEST OPERATIONS
# =============================================================================
function Read-Manifest {
    if (-not (Test-Path $MANIFEST_PATH)) {
        Write-Error "Manifest not found: $MANIFEST_PATH"
        exit 1
    }

    try {
        $manifest = Get-Content $MANIFEST_PATH -Raw | ConvertFrom-Json
        return $manifest
    } catch {
        Write-Error "Failed to parse manifest: $_"
        exit 1
    }
}

function Validate-Manifest($manifest) {
    Write-Section "Validating Manifest (Fail-Closed)"

    # Check version
    if (-not $manifest.version) {
        Write-Error "Manifest missing 'version' field"
        exit 1
    }
    Write-Success "Manifest version: $($manifest.version)"

    # Check canonical_secrets_path
    if (-not $manifest.canonical_secrets_path) {
        Write-Error "Manifest missing 'canonical_secrets_path' field"
        exit 1
    }

    $secretsPath = $manifest.canonical_secrets_path
    if (-not (Test-Path $secretsPath)) {
        Write-Error "Secrets path does not exist: $secretsPath"
        Write-Info "Create it with: mkdir `"$secretsPath`""
        exit 1
    }
    Write-Success "Secrets path exists: $secretsPath"

    # Check secrets array
    if (-not $manifest.secrets -or $manifest.secrets.Count -eq 0) {
        Write-Error "Manifest has no secrets defined"
        exit 1
    }
    Write-Success "Secrets defined: $($manifest.secrets.Count)"

    # Validate each secret
    foreach ($secret in $manifest.secrets) {
        if (-not $secret.name) {
            Write-Error "Secret missing 'name' field"
            exit 1
        }
        if (-not $secret.rotation_mode) {
            Write-Error "Secret '$($secret.name)' missing 'rotation_mode'"
            exit 1
        }
        if ($secret.rotation_mode -notin @('auto', 'manual')) {
            Write-Error "Secret '$($secret.name)' has invalid rotation_mode: $($secret.rotation_mode)"
            exit 1
        }

        # Auto secrets must have format and bytes
        if ($secret.rotation_mode -eq 'auto') {
            if (-not $secret.format) {
                Write-Error "Auto secret '$($secret.name)' missing 'format'"
                exit 1
            }
            if (-not $secret.bytes) {
                Write-Error "Auto secret '$($secret.name)' missing 'bytes'"
                exit 1
            }
        }
    }

    Write-Success "Manifest validation passed (fail-closed checks OK)"
}

# =============================================================================
# SECRET GENERATION
# =============================================================================
function Generate-Secret($format, $bytes) {
    switch ($format) {
        'base64' {
            # Use .NET crypto for secure random bytes
            $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            $randomBytes = New-Object byte[] $bytes
            $rng.GetBytes($randomBytes)
            $secret = [Convert]::ToBase64String($randomBytes)
            $rng.Dispose()
            return $secret
        }
        default {
            throw "Unsupported format: $format"
        }
    }
}

# =============================================================================
# PLAN COMMAND
# =============================================================================
function Invoke-Plan($manifest) {
    Write-Section "Plan: Secret Rotation Analysis"

    $state = Read-RotationState

    $autoSecrets = @()
    $manualSecrets = @()

    foreach ($secret in $manifest.secrets) {
        if ($secret.rotation_mode -eq 'auto' -and -not $secret.exclude_by_default) {
            $autoSecrets += $secret
        } elseif ($secret.rotation_mode -eq 'manual' -or $secret.exclude_by_default) {
            $manualSecrets += $secret
        }
    }

    Write-Info "AUTO secrets (will be rotated):"
    if ($autoSecrets.Count -eq 0) {
        Write-Warning "  (none)"
    } else {
        foreach ($secret in $autoSecrets) {
            $secretPath = Join-Path $manifest.canonical_secrets_path $secret.name
            $exists = Test-Path $secretPath
            $isFresh = Test-SecretFreshness $secret.name $state

            if (-not $exists) {
                $status = "CREATE"
                $reason = "new secret"
            } elseif ($Force) {
                $status = "UPDATE"
                $reason = "forced rotation"
            } elseif (-not $isFresh) {
                $status = "UPDATE"
                $ageInfo = if ($state.secrets.ContainsKey($secret.name) -and $state.secrets[$secret.name].last_rotated) {
                    $lastRotated = [DateTime]::Parse($state.secrets[$secret.name].last_rotated)
                    $age = (Get-Date) - $lastRotated
                    "age: $([Math]::Round($age.TotalDays, 1)) days"
                } else {
                    "never rotated"
                }
                $reason = "$ageInfo (max: $MAX_AGE_DAYS days)"
            } else {
                $status = "SKIP"
                $lastRotated = [DateTime]::Parse($state.secrets[$secret.name].last_rotated)
                $age = (Get-Date) - $lastRotated
                $reason = "fresh (age: $([Math]::Round($age.TotalDays, 1)) days)"
            }

            Write-Info ("  [{0}] {1,-30} {2} bytes, {3}, restart: {4}" -f $status, $secret.name, $secret.bytes, $reason, ($secret.restart_scope -join ', '))
        }
    }

    Write-Info ""
    Write-Info "MANUAL secrets (will NOT be rotated):"
    if ($manualSecrets.Count -eq 0) {
        Write-Warning "  (none)"
    } else {
        foreach ($secret in $manualSecrets) {
            $note = if ($secret.notes) { $secret.notes } else { "MANUAL" }
            Write-Info ("  [SKIP]   {0,-30} {1}" -f $secret.name, $note)
        }
    }

    Write-Info ""
    Write-Info "Affected services (will need restart):"
    $allServices = @()
    foreach ($secret in $autoSecrets) {
        if ($secret.restart_scope) {
            $allServices += $secret.restart_scope
        }
    }
    $uniqueServices = $allServices | Select-Object -Unique
    if ($uniqueServices.Count -eq 0) {
        Write-Warning "  (none)"
    } else {
        foreach ($service in $uniqueServices) {
            Write-Info "  - $service"
        }
    }

    Write-Section "Plan Complete"
    if ($Force) {
        Write-Warning "Force mode enabled: ALL auto secrets will be rotated regardless of age"
    }
    Write-Info "Next step: Run 'Rotate-Secrets.ps1 apply' to execute rotation"
    if (-not $Force) {
        Write-Info "To force rotation of fresh secrets: 'Rotate-Secrets.ps1 apply -Force'"
    }
}

# =============================================================================
# APPLY COMMAND
# =============================================================================
function Invoke-Apply($manifest) {
    Write-Section "Apply: Rotating Secrets"

    # Fail-closed: Check for forbidden flag
    if ($IncludeManual) {
        Write-Error "FORBIDDEN: --IncludeManual flag detected"
        Write-Error "Manual secrets (like Grafana admin) must NOT be auto-rotated"
        Write-Error "See runbook: knowledge/runbooks/GRAFANA_ADMIN_INCIDENT.md"
        exit 1
    }

    $autoSecrets = $manifest.secrets | Where-Object {
        $_.rotation_mode -eq 'auto' -and -not $_.exclude_by_default
    }

    if ($autoSecrets.Count -eq 0) {
        Write-Warning "No auto secrets to rotate"
        return
    }

    $secretsPath = $manifest.canonical_secrets_path
    $state = Read-RotationState
    $rotated = 0
    $skipped = 0

    if ($Force) {
        Write-Warning "Force mode: Rotating ALL auto secrets regardless of age"
    }

    foreach ($secret in $autoSecrets) {
        $secretFile = Join-Path $secretsPath $secret.name
        $exists = Test-Path $secretFile
        $isFresh = Test-SecretFreshness $secret.name $state

        # Skip if fresh (unless forced)
        if ($exists -and $isFresh -and -not $Force) {
            $lastRotated = [DateTime]::Parse($state.secrets[$secret.name].last_rotated)
            $age = (Get-Date) - $lastRotated
            Write-Info "SKIP   $($secret.name) (fresh, age: $([Math]::Round($age.TotalDays, 1)) days, max: $MAX_AGE_DAYS)"
            $skipped++
            continue
        }

        # Generate new secret
        try {
            $newSecret = Generate-Secret -format $secret.format -bytes $secret.bytes
        } catch {
            Write-Error "Failed to generate secret '$($secret.name)': $_"
            exit 1
        }

        # Write secret (NO newline at end)
        try {
            [System.IO.File]::WriteAllText($secretFile, $newSecret)
            $action = if ($exists) { "UPDATE" } else { "CREATE" }
            $reason = if ($Force) { "forced" } elseif (-not $exists) { "new" } else { "stale" }
            Write-Success "$action $($secret.name) (length: $($newSecret.Length), reason: $reason)"

            # Update rotation state
            $state.secrets[$secret.name] = @{
                last_rotated = (Get-Date).ToString("o")  # ISO 8601
                rotated_by = "Rotate-Secrets.ps1 v1.1"
                length = $newSecret.Length
                format = $secret.format
            }

            $rotated++
        } catch {
            Write-Error "Failed to write secret '$($secret.name)': $_"
            exit 1
        }
    }

    # Persist rotation state
    Write-RotationState $state

    Write-Section "Apply Complete"
    Write-Success "Rotated: $rotated secrets"
    if ($skipped -gt 0) {
        Write-Info "Skipped: $skipped secrets (fresh, age < $MAX_AGE_DAYS days)"
    }
    Write-Info ""
    Write-Info "Next steps:"
    Write-Info "  1. Run 'Rotate-Secrets.ps1 export' to generate .env.runtime"
    Write-Info "  2. Run 'infrastructure/scripts/stack_up.ps1' to restart stack"
}

# =============================================================================
# EXPORT COMMAND
# =============================================================================
function Invoke-Export($manifest) {
    Write-Section "Export: Generating .env.runtime"

    $autoSecrets = $manifest.secrets | Where-Object {
        $_.rotation_mode -eq 'auto' -and -not $_.exclude_by_default
    }

    if ($autoSecrets.Count -eq 0) {
        Write-Warning "No auto secrets to export"
        return
    }

    $secretsPath = $manifest.canonical_secrets_path
    $envLines = @()
    $envLines += "# CDB Runtime Secrets (auto-generated by Rotate-Secrets.ps1)"
    $envLines += "# DO NOT COMMIT - gitignored"
    $envLines += ""

    foreach ($secret in $autoSecrets) {
        $secretFile = Join-Path $secretsPath $secret.name
        if (-not (Test-Path $secretFile)) {
            Write-Warning "Secret file missing: $($secret.name) - run 'apply' first"
            continue
        }

        $secretValue = Get-Content $secretFile -Raw
        $secretValue = $secretValue.Trim()

        # Export with secret name as ENV var
        $envLines += "$($secret.name)=$secretValue"
        Write-Info "Export $($secret.name) (length: $($secretValue.Length))"
    }

    # Write .env.runtime
    try {
        $envLines | Set-Content -Path $ENV_RUNTIME_PATH -Encoding ASCII -NoNewline:$false
        Write-Success "Created: $ENV_RUNTIME_PATH"
    } catch {
        Write-Error "Failed to write .env.runtime: $_"
        exit 1
    }

    Write-Section "Export Complete"
    Write-Info "Next step: Run 'infrastructure/scripts/stack_up.ps1' to load secrets"
}

# =============================================================================
# MAIN
# =============================================================================
function Main {
    Write-Section "CDB Secret Rotator v1.1 (State-Based Rotation)"
    Write-Info "Command: $Command"
    Write-Info "Manifest: $MANIFEST_PATH"
    Write-Info "Rotation state: $STATE_PATH"
    Write-Info "Max age: $MAX_AGE_DAYS days"
    if ($Force) {
        Write-Warning "Force mode: Ignoring rotation state (all secrets will rotate)"
    }

    # Load and validate manifest
    $manifest = Read-Manifest
    Validate-Manifest $manifest

    # Execute command
    switch ($Command) {
        'plan' {
            Invoke-Plan $manifest
        }
        'apply' {
            Invoke-Apply $manifest
        }
        'export' {
            Invoke-Export $manifest
        }
    }

    Write-Host ""
}

# Run
Main
