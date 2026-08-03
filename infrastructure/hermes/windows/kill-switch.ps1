#Requires -Version 5.1
<#
.SYNOPSIS
  Immediate Windows bridge kill-switch for Hermes (#4289 Phase B1).

.DESCRIPTION
  Targets the dedicated sshd-hermes listener only (never the generic system sshd
  by default). Disable stops the bridge and marks WORKSTATION_UNAVAILABLE.
  Enable restores Automatic start for reboot persistence.
  Fail-closed: missing service or missing/corrupt state => UNAVAILABLE.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Disable', 'Enable', 'Status')]
    [string]$Action,
    [string]$StateFile = 'D:\Dev\HermesWorkspace\.hermes_kill_switch.state',
    [string]$ServiceName = 'sshd-hermes'
)

$ErrorActionPreference = 'Stop'

function Write-State([string]$status) {
    $dir = Split-Path -Parent $StateFile
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    @(
        "status=$status"
        "service=$ServiceName"
        "updated_utc=$((Get-Date).ToUniversalTime().ToString('o'))"
        'meaning=WORKSTATION_UNAVAILABLE_WHEN_DISABLED'
    ) | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Read-StateStatus {
    if (-not (Test-Path -LiteralPath $StateFile)) {
        return 'UNAVAILABLE'
    }
    $raw = Get-Content -LiteralPath $StateFile -Raw -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return 'UNAVAILABLE'
    }
    if ($raw -notmatch '(?m)^status=(ENABLED|DISABLED|UNAVAILABLE)\s*$') {
        return 'UNAVAILABLE'
    }
    return $Matches[1]
}

function Write-MachineStatus {
    param(
        [string]$ServiceStatus,
        [string]$KillSwitch,
        [string]$Meaning
    )
    Write-Host "service=$ServiceStatus"
    Write-Host "kill_switch=$KillSwitch"
    Write-Host "status=$KillSwitch"
    Write-Host "service_name=$ServiceName"
    Write-Host "meaning=$Meaning"
    $obj = [ordered]@{
        service_name = $ServiceName
        service      = $ServiceStatus
        kill_switch  = $KillSwitch
        status       = $KillSwitch
        meaning      = $Meaning
        state_file   = $StateFile
    }
    $obj | ConvertTo-Json -Compress | Write-Host
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-State 'UNAVAILABLE'
    Write-MachineStatus -ServiceStatus 'Missing' -KillSwitch 'UNAVAILABLE' `
        -Meaning 'WORKSTATION_UNAVAILABLE'
    if ($Action -eq 'Status') { exit 0 }
    exit 2
}

switch ($Action) {
    'Disable' {
        if ($svc.Status -eq 'Running') {
            Stop-Service -Name $ServiceName -Force
        }
        Set-Service -Name $ServiceName -StartupType Disabled
        Write-State 'DISABLED'
        Write-MachineStatus -ServiceStatus 'Stopped' -KillSwitch 'DISABLED' `
            -Meaning 'WORKSTATION_UNAVAILABLE'
        Write-Host 'Kill-switch ON: WORKSTATION_UNAVAILABLE'
    }
    'Enable' {
        # Automatic = reboot-persistent bridge when kill-switch is cleared.
        Set-Service -Name $ServiceName -StartupType Automatic
        Start-Service -Name $ServiceName
        Write-State 'ENABLED'
        Write-MachineStatus -ServiceStatus 'Running' -KillSwitch 'ENABLED' `
            -Meaning 'BRIDGE_PRIVATE_NET_ONLY'
        Write-Host 'Kill-switch OFF: workstation bridge enabled (still private-net only)'
    }
    'Status' {
        $kill = Read-StateStatus
        $meaning = if ($kill -eq 'ENABLED') {
            'BRIDGE_PRIVATE_NET_ONLY'
        } else {
            'WORKSTATION_UNAVAILABLE'
        }
        Write-MachineStatus -ServiceStatus "$($svc.Status)" -KillSwitch $kill `
            -Meaning $meaning
    }
}
