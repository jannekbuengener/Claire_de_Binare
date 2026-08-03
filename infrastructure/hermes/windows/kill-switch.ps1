#Requires -Version 5.1
<#
.SYNOPSIS
  Immediate Windows bridge kill-switch for Hermes (#4289 Phase B1).

.DESCRIPTION
  Architecture (Serve bridge - host TCP after Wintun does not SYN-ACK):
    Tailscale Serve TCP/22 -> 127.0.0.1:22 <- sshd-hermes (loopback-only)

  Disable:
    1) Remove Tailscale Serve TCP mapping for port 22
    2) Stop sshd-hermes
    3) StartupType Disabled
    4) State DISABLED -> WORKSTATION_UNAVAILABLE
    Remote TCP/SSH must fail immediately. Funnel must never be enabled.

  Enable (ordered, fail-closed):
    1) StartupType Automatic + start sshd-hermes
    2) Local loopback TCP healthcheck PASS
    3) Only then: tailscale serve --bg --tcp=22 tcp://127.0.0.1:22
    4) Verify Serve status
    5) State ENABLED only after local+Serve healthy
       (optional remote SSH proof is operator-side; script stays fail-closed)

  Status:
    Requires ALL of: Running sshd, Serve TCP/22 -> loopback, local listener.
    Any missing/contradictory condition -> UNAVAILABLE.
    Missing/empty/corrupt state file -> UNAVAILABLE.

  Docs gate (Tailscale 1.98+):
    enable:  tailscale serve --bg --tcp=22 tcp://127.0.0.1:22
    disable: tailscale serve --tcp=22 off
    status:  tailscale serve status --json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Disable', 'Enable', 'Status')]
    [string]$Action,
    [string]$StateFile = 'D:\Dev\HermesWorkspace\.hermes_kill_switch.state',
    [string]$ServiceName = 'sshd-hermes',
    [int]$ServeTcpPort = 22,
    [string]$LoopbackHost = '127.0.0.1'
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
        "serve_tcp_port=$ServeTcpPort"
        "updated_utc=$((Get-Date).ToUniversalTime().ToString('o'))"
        'meaning=WORKSTATION_UNAVAILABLE_WHEN_DISABLED'
        'architecture=TAILSCALE_SERVE_LOOPBACK_SSHD'
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

function Test-LoopbackListener {
    try {
        $tnc = Test-NetConnection -ComputerName $LoopbackHost -Port $ServeTcpPort `
            -WarningAction SilentlyContinue
        return [bool]$tnc.TcpTestSucceeded
    }
    catch {
        return $false
    }
}

function Get-ServeTcpForward {
    # Returns hashtable: Present, TargetLoopback, Raw (redact-safe length only)
    $result = [ordered]@{
        Present         = $false
        TargetLoopback  = $false
        FunnelForbidden = $true
    }
    try {
        $json = & tailscale serve status --json 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
            return $result
        }
        $obj = $json | ConvertFrom-Json
        $key = "$ServeTcpPort"
        if ($obj.TCP -and $obj.TCP.$key -and $obj.TCP.$key.TCPForward) {
            $result.Present = $true
            $fwd = [string]$obj.TCP.$key.TCPForward
            if ($fwd -match '127\.0\.0\.1:' -or $fwd -match '\[::1\]:') {
                $result.TargetLoopback = $true
            }
        }
        # Funnel must never be the path; Web/HTTPS public would be a hard fail.
        if ($obj.AllowFunnel) {
            foreach ($prop in $obj.AllowFunnel.PSObject.Properties) {
                if ($prop.Value -eq $true) {
                    $result.FunnelForbidden = $false
                }
            }
        }
    }
    catch {
        return $result
    }
    return $result
}

function Disable-ServeTcpMapping {
    try {
        & tailscale serve --tcp=$ServeTcpPort off *>$null
    }
    catch {
        Write-Host "WARN: serve disable: $($_.Exception.Message)"
    }
}

function Enable-ServeTcpMapping {
    # Never Funnel. Exact CLI from serve --help (1.98+).
    & tailscale serve --bg --yes --tcp=$ServeTcpPort "tcp://$LoopbackHost`:$ServeTcpPort" *>$null
    if ($LASTEXITCODE -ne 0) {
        throw "tailscale serve enable failed exit=$LASTEXITCODE"
    }
    $serve = Get-ServeTcpForward
    if (-not $serve.Present -or -not $serve.TargetLoopback) {
        throw 'Serve TCP mapping missing or not loopback after enable'
    }
    if (-not $serve.FunnelForbidden) {
        Disable-ServeTcpMapping
        throw 'Funnel must stay OFF; refused Serve enable with AllowFunnel'
    }
}

function Write-MachineStatus {
    param(
        [string]$ServiceStatus,
        [string]$KillSwitch,
        [string]$Meaning,
        [bool]$ServePresent = $false,
        [bool]$LoopbackOk = $false
    )
    Write-Host "service=$ServiceStatus"
    Write-Host "kill_switch=$KillSwitch"
    Write-Host "status=$KillSwitch"
    Write-Host "service_name=$ServiceName"
    Write-Host "serve_tcp=$ServePresent"
    Write-Host "loopback_tcp=$LoopbackOk"
    Write-Host "meaning=$Meaning"
    $obj = [ordered]@{
        service_name = $ServiceName
        service      = $ServiceStatus
        kill_switch  = $KillSwitch
        status       = $KillSwitch
        serve_tcp    = $ServePresent
        loopback_tcp = $LoopbackOk
        meaning      = $Meaning
        state_file   = $StateFile
        architecture = 'TAILSCALE_SERVE_LOOPBACK_SSHD'
    }
    $obj | ConvertTo-Json -Compress | Write-Host
}

function Test-LiveBridgeTriple {
    # Live-only: Running sshd + Serve TCP loopback + local listener. No state-file gate.
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        return @{ Ok = $false; ServiceStatus = 'Missing'; ServePresent = $false; LoopbackOk = $false }
    }
    $serve = Get-ServeTcpForward
    $loop = Test-LoopbackListener
    $running = ($svc.Status -eq 'Running')
    $ok = $running -and $serve.Present -and $serve.TargetLoopback -and $loop -and $serve.FunnelForbidden
    return @{
        Ok            = $ok
        ServiceStatus = "$($svc.Status)"
        ServePresent  = $serve.Present
        LoopbackOk    = $loop
        FunnelOk      = $serve.FunnelForbidden
    }
}

function Resolve-LiveBridgeHealth {
    # Returns ENABLED only when service Running AND serve loopback AND local listener.
    # Contradictions -> UNAVAILABLE.
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        return @{
            ServiceStatus = 'Missing'
            KillSwitch    = 'UNAVAILABLE'
            Meaning       = 'WORKSTATION_UNAVAILABLE'
            ServePresent  = $false
            LoopbackOk    = $false
        }
    }
    $serve = Get-ServeTcpForward
    $loop = Test-LoopbackListener
    $running = ($svc.Status -eq 'Running')

    if (-not $serve.FunnelForbidden) {
        return @{
            ServiceStatus = "$($svc.Status)"
            KillSwitch    = 'UNAVAILABLE'
            Meaning       = 'WORKSTATION_UNAVAILABLE'
            ServePresent  = $serve.Present
            LoopbackOk    = $loop
        }
    }

    # Contradictions: Serve without sshd, or sshd without Serve, or no listener.
    if ($running -and $serve.Present -and $serve.TargetLoopback -and $loop) {
        $fileStatus = Read-StateStatus
        # Status path: DISABLED file while live bridge is up is contradictory.
        if ($fileStatus -eq 'DISABLED') {
            return @{
                ServiceStatus = "$($svc.Status)"
                KillSwitch    = 'UNAVAILABLE'
                Meaning       = 'WORKSTATION_UNAVAILABLE'
                ServePresent  = $serve.Present
                LoopbackOk    = $loop
            }
        }
        return @{
            ServiceStatus = 'Running'
            KillSwitch    = 'ENABLED'
            Meaning       = 'BRIDGE_PRIVATE_NET_ONLY'
            ServePresent  = $true
            LoopbackOk    = $true
        }
    }

    if (-not $running -and -not $serve.Present -and -not $loop) {
        $fileStatus = Read-StateStatus
        $ks = if ($fileStatus -eq 'DISABLED') { 'DISABLED' } else { 'UNAVAILABLE' }
        return @{
            ServiceStatus = "$($svc.Status)"
            KillSwitch    = $ks
            Meaning       = 'WORKSTATION_UNAVAILABLE'
            ServePresent  = $false
            LoopbackOk    = $false
        }
    }

    # Partial / contradictory
    return @{
        ServiceStatus = "$($svc.Status)"
        KillSwitch    = 'UNAVAILABLE'
        Meaning       = 'WORKSTATION_UNAVAILABLE'
        ServePresent  = $serve.Present
        LoopbackOk    = $loop
    }
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-State 'UNAVAILABLE'
    Write-MachineStatus -ServiceStatus 'Missing' -KillSwitch 'UNAVAILABLE' `
        -Meaning 'WORKSTATION_UNAVAILABLE' -ServePresent:$false -LoopbackOk:$false
    if ($Action -eq 'Status') { exit 0 }
    exit 2
}

switch ($Action) {
    'Disable' {
        # 1) Clear Serve first so remote TCP fails immediately.
        # 2) Stop/disable sshd-hermes (needs elevation).
        # Incomplete stop -> UNAVAILABLE (fail-closed), never claim DISABLED.
        Disable-ServeTcpMapping
        $stopOk = $true
        try {
            if ((Get-Service -Name $ServiceName).Status -eq 'Running') {
                Stop-Service -Name $ServiceName -Force -ErrorAction Stop
            }
            Set-Service -Name $ServiceName -StartupType Disabled -ErrorAction Stop
        }
        catch {
            $stopOk = $false
            Write-Host "WARN: sshd stop/disable failed (elevation?): $($_.Exception.Message)"
        }
        $serve = Get-ServeTcpForward
        $loop = Test-LoopbackListener
        $svcNow = Get-Service -Name $ServiceName
        if ($stopOk -and -not $serve.Present) {
            Write-State 'DISABLED'
            Write-MachineStatus -ServiceStatus 'Stopped' -KillSwitch 'DISABLED' `
                -Meaning 'WORKSTATION_UNAVAILABLE' `
                -ServePresent:$false -LoopbackOk:$loop
            Write-Host 'Kill-switch ON: WORKSTATION_UNAVAILABLE (Serve off + sshd-hermes stopped)'
        }
        else {
            Write-State 'UNAVAILABLE'
            Write-MachineStatus -ServiceStatus "$($svcNow.Status)" `
                -KillSwitch 'UNAVAILABLE' -Meaning 'WORKSTATION_UNAVAILABLE' `
                -ServePresent:$serve.Present -LoopbackOk:$loop
            Write-Host 'Kill-switch PARTIAL->UNAVAILABLE (Serve cleared; elevation needed for full Disable)'
            exit 3
        }
    }
    'Enable' {
        # Ordered: sshd -> loopback -> Serve -> live triple (ignore DISABLED file
        # mid-transition) -> optional remote proof by operator -> ENABLED state.
        # Do NOT call the Status health resolver here: file still DISABLED would
        # wrongly roll back Serve after a successful enable.
        Set-Service -Name $ServiceName -StartupType Automatic
        Start-Service -Name $ServiceName
        Start-Sleep -Seconds 1
        if (-not (Test-LoopbackListener)) {
            Write-State 'UNAVAILABLE'
            throw 'Local loopback healthcheck FAILED; Serve not enabled; state UNAVAILABLE'
        }
        Enable-ServeTcpMapping
        $live = Test-LiveBridgeTriple
        if (-not $live.Ok) {
            Disable-ServeTcpMapping
            Write-State 'UNAVAILABLE'
            throw 'Post-enable live triple FAILED; rolled back Serve; state UNAVAILABLE'
        }
        Write-State 'ENABLED'
        Write-MachineStatus -ServiceStatus 'Running' -KillSwitch 'ENABLED' `
            -Meaning 'BRIDGE_PRIVATE_NET_ONLY' `
            -ServePresent:$true -LoopbackOk:$true
        Write-Host 'Kill-switch OFF: Serve+loopback sshd bridge ENABLED (private Tailnet only; Funnel forbidden)'
    }
    'Status' {
        $health = Resolve-LiveBridgeHealth
        Write-MachineStatus -ServiceStatus $health.ServiceStatus `
            -KillSwitch $health.KillSwitch -Meaning $health.Meaning `
            -ServePresent:$health.ServePresent -LoopbackOk:$health.LoopbackOk
    }
}
