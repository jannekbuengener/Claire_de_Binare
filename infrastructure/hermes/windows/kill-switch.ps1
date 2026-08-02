#Requires -Version 5.1
<#
.SYNOPSIS
  Immediate Windows bridge kill-switch for Hermes (#4289).

.DESCRIPTION
  Disable = stop sshd (or dedicated listener) and mark WORKSTATION_UNAVAILABLE.
  Enable  = restore sshd if previously managed by this script.
  Fail-closed: a stopped bridge means unavailable, never auto-fallback.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Disable', 'Enable', 'Status')]
    [string]$Action,
    [string]$StateFile = 'D:\Dev\HermesWorkspace\.hermes_kill_switch.state',
    [string]$ServiceName = 'sshd'
)

$ErrorActionPreference = 'Stop'

function Write-State([string]$status) {
    $dir = Split-Path -Parent $StateFile
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    @(
        "status=$status"
        "updated_utc=$((Get-Date).ToUniversalTime().ToString('o'))"
        'meaning=WORKSTATION_UNAVAILABLE_WHEN_DISABLED'
    ) | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-State 'UNAVAILABLE'
    Write-Host 'WORKSTATION_UNAVAILABLE (sshd service missing)'
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
        Write-Host 'Kill-switch ON: WORKSTATION_UNAVAILABLE'
    }
    'Enable' {
        Set-Service -Name $ServiceName -StartupType Manual
        Start-Service -Name $ServiceName
        Write-State 'ENABLED'
        Write-Host 'Kill-switch OFF: workstation bridge enabled (still private-net only)'
    }
    'Status' {
        $state = if (Test-Path -LiteralPath $StateFile) {
            Get-Content -LiteralPath $StateFile -Raw
        } else {
            'status=UNKNOWN'
        }
        Write-Host "service=$($svc.Status)"
        Write-Host $state
    }
}
