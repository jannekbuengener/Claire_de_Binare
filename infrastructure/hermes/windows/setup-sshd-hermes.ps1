#Requires -Version 5.1
<#
.SYNOPSIS
  Install/configure dedicated loopback OpenSSH + Tailscale Serve bridge (#4289).

.DESCRIPTION
  Windows host TCP after Wintun injection does not SYN-ACK for peer traffic
  (live evidence 2026-08-03). Architecture:

  - sshd-hermes listens ONLY on 127.0.0.1:22 (and ::1).
  - Tailscale Serve raw TCP forwarder: tailnet:22 → tcp://127.0.0.1:22 (--bg).
  - No inbound Windows Firewall allow for sshd (Serve is the only remote path).
  - Funnel is forbidden and must stay off.
  - Default system sshd Disabled; public OpenSSH-Server-In-TCP Disabled.

  Docs gate (Tailscale 1.98+):
    tailscale serve --bg --tcp=22 tcp://127.0.0.1:22
    tailscale serve --tcp=22 off
    tailscale serve status --json
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$HermesUser = 'hermes-win',
    [string]$ServiceName = 'sshd-hermes',
    [string]$ConfigPath = 'C:\ProgramData\ssh\sshd_hermes_config',
    [string]$HostKeyPath = 'C:\ProgramData\ssh\ssh_host_ed25519_key',
    [int]$ListenPort = 22,
    [string]$LegacyFirewallRuleName = 'CDB-Hermes-sshd-hermes-Tailscale'
)

$ErrorActionPreference = 'Stop'

function Assert-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'setup-sshd-hermes.ps1 must run elevated (Administrator).'
    }
}

function Resolve-SshdExe {
    $candidates = @(
        'C:\Windows\System32\OpenSSH\sshd.exe',
        'C:\Program Files\OpenSSH\sshd.exe',
        "${env:SystemDrive}\OpenSSH\sshd.exe",
        'C:\Program Files (x86)\OpenSSH\sshd.exe'
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Install-OpenSSHServerCapability {
    $existing = Resolve-SshdExe
    if ($existing) {
        Write-Host "OpenSSH Server already present: $existing"
        return $existing
    }
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        $packageId = 'Microsoft.OpenSSH.Preview'
        if ($PSCmdlet.ShouldProcess($packageId, 'winget install OpenSSH Server')) {
            Write-Host "Installing OpenSSH Server via winget ($packageId, no DISM)..."
            & winget.exe install --id $packageId -e --source winget `
                --accept-package-agreements --accept-source-agreements `
                --disable-interactivity *>$null
            $wingetExit = $LASTEXITCODE
            if ($wingetExit -notin @(0, -1978335189, -1978335135)) {
                throw "winget install $packageId failed exit=$wingetExit"
            }
        }
        Start-Sleep -Seconds 2
        $existing = Resolve-SshdExe
        if ($existing) { return $existing }
    }
    throw 'OpenSSH Server not found after install attempt'
}

function Disable-DefaultPublicSshd {
    $svc = Get-Service -Name 'sshd' -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -eq 'Running') { Stop-Service -Name 'sshd' -Force -ErrorAction SilentlyContinue }
        Set-Service -Name 'sshd' -StartupType Disabled -ErrorAction SilentlyContinue
    }
    $pub = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
    if ($pub -and $pub.Enabled) {
        Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'
    }
    Get-NetFirewallRule -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq 'OpenSSH SSH Server Preview (sshd)' -and $_.Enabled } |
        ForEach-Object { Disable-NetFirewallRule -Name $_.Name }
}

function Remove-LegacyExternalSshFirewall {
    param([string]$RuleName)
    foreach ($n in @($RuleName, 'CDB-Hermes-sshd-program', 'CDB-Hermes-sshd-TailscaleIF', 'CDB-Hermes-DIAG-tcp22-any-TEMP')) {
        $existing = Get-NetFirewallRule -Name $n -ErrorAction SilentlyContinue
        if ($existing) {
            Remove-NetFirewallRule -Name $n
            Write-Host "Removed legacy/external firewall rule: $n"
        }
    }
}

function Write-HermesSshdConfig {
    param(
        [int]$Port,
        [string]$UserName,
        [string]$ConfigFile,
        [string]$HostKey,
        [string]$KeygenExe,
        [string]$SftpServer
    )
    if ([string]::IsNullOrWhiteSpace($ConfigFile)) { throw 'ConfigFile is required' }
    if ([string]::IsNullOrWhiteSpace($HostKey)) { throw 'HostKey is required' }
    if ([string]::IsNullOrWhiteSpace($KeygenExe)) { throw 'KeygenExe is required' }
    $dir = Split-Path -Parent $ConfigFile
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath $HostKey)) {
        & $KeygenExe -t ed25519 -f $HostKey -N '""' -q
    }
    if ([string]::IsNullOrWhiteSpace($SftpServer)) {
        $SftpServer = 'sftp-server.exe'
    }
    $authKeys = "C:/Users/$UserName/.ssh/authorized_keys"
    $content = @"
# CDB Hermes dedicated sshd (#4289). Loopback-only backend.
# Remote access is ONLY via Tailscale Serve TCP forwarder (never Funnel):
#   tailscale serve --bg --tcp=$Port tcp://127.0.0.1:$Port
# Host TCP after Wintun does not SYN-ACK for peer traffic on this Windows build;
# Serve proxies tailnet TCP into loopback where sshd answers.
# Public exposure prevented by:
#   - ListenAddress 127.0.0.1 / ::1 only
#   - no inbound Windows Firewall allow for sshd
#   - OpenSSH-Server-In-TCP disabled
#   - Funnel forbidden
#   - PasswordAuthentication no / AllowUsers $UserName
#   - default system sshd Disabled
Port $Port
ListenAddress 127.0.0.1
ListenAddress ::1
HostKey $HostKey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitEmptyPasswords no
AllowUsers $UserName
AuthorizedKeysFile $authKeys
StrictModes no
AllowTcpForwarding no
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no
GatewayPorts no
MaxAuthTries 3
LoginGraceTime 20
Subsystem sftp $SftpServer
"@
    if ($PSCmdlet.ShouldProcess($ConfigFile, 'Write sshd_hermes_config')) {
        Set-Content -LiteralPath $ConfigFile -Value $content -Encoding ascii
    }
}

function Ensure-HermesSshService {
    param([string]$Name, [string]$Config, [string]$SshdExe)
    $binPath = "`"$SshdExe`" -f `"$Config`""
    $existing = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        if ($PSCmdlet.ShouldProcess($Name, 'New-Service sshd-hermes')) {
            New-Service -Name $Name -BinaryPathName $binPath `
                -DisplayName 'CDB Hermes OpenSSH (Tailscale Serve backend)' `
                -Description 'Loopback-only Hermes bridge; remote via Tailscale Serve (#4289).' `
                -StartupType Automatic | Out-Null
        }
    }
    else {
        & sc.exe config $Name binPath= $binPath | Out-Null
        Set-Service -Name $Name -StartupType Automatic
    }
}

function Assert-FunnelOff {
    $funnel = & tailscale funnel status 2>&1 | Out-String
    if ($funnel -match '(?i)Funnel on|https://.*ts\.net' -and $funnel -notmatch 'tailnet only') {
        # Funnel status may echo Serve config; require explicit Funnel enablement markers.
        if ($funnel -match '(?i)Funnel on:') {
            throw 'Tailscale Funnel must be OFF for Hermes bridge'
        }
    }
    Write-Host 'Funnel check: not enabled (Serve-only path)'
}

function Enable-TailscaleServeTcp {
    param([int]$Port)
    Assert-FunnelOff
    if ($PSCmdlet.ShouldProcess("tcp/$Port", 'tailscale serve --bg TCP forwarder')) {
        # Docs (1.98): tailscale serve --bg --tcp=<port> tcp://127.0.0.1:<port>
        & tailscale serve --bg --yes --tcp=$Port "tcp://127.0.0.1:$Port" *>$null
        if ($LASTEXITCODE -ne 0) {
            throw "tailscale serve enable failed exit=$LASTEXITCODE"
        }
    }
    $status = & tailscale serve status --json 2>$null | ConvertFrom-Json
    $key = "$Port"
    if (-not $status.TCP -or -not $status.TCP.$key -or -not $status.TCP.$key.TCPForward) {
        throw "tailscale serve status missing TCP/$Port forward"
    }
    $fwd = [string]$status.TCP.$key.TCPForward
    if ($fwd -notmatch '127\.0\.0\.1:' -and $fwd -notmatch '\[::1\]:') {
        throw "Serve TCPForward must target loopback (got redacted length=$($fwd.Length))"
    }
    Write-Host "Tailscale Serve TCP/$Port → loopback READY (Funnel forbidden)"
}

function Ensure-AuthorizedKeysDir {
    param([string]$UserName)
    $userHome = "C:\Users\$UserName"
    if (-not (Test-Path -LiteralPath $userHome)) {
        throw "User profile missing for $UserName (logon once or create profile before keys)."
    }
    $sshDir = Join-Path $userHome '.ssh'
    if (-not (Test-Path -LiteralPath $sshDir)) {
        New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    }
    $acl = Get-Acl -LiteralPath $sshDir
    $acl.SetAccessRuleProtection($true, $false)
    @($acl.Access) | ForEach-Object { [void]$acl.RemoveAccessRule($_) }
    foreach ($sidObj in @(
            (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')),
            (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')),
            (New-Object System.Security.Principal.NTAccount("$env:COMPUTERNAME\$UserName")).Translate([System.Security.Principal.SecurityIdentifier])
        )) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sidObj, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
        )
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $sshDir -AclObject $acl
    $auth = Join-Path $sshDir 'authorized_keys'
    if (-not (Test-Path -LiteralPath $auth)) {
        New-Item -ItemType File -Path $auth -Force | Out-Null
    }
    $acl2 = Get-Acl -LiteralPath $auth
    $acl2.SetAccessRuleProtection($true, $false)
    @($acl2.Access) | ForEach-Object { [void]$acl2.RemoveAccessRule($_) }
    foreach ($sidObj in @(
            (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')),
            (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')),
            (New-Object System.Security.Principal.NTAccount("$env:COMPUTERNAME\$UserName")).Translate([System.Security.Principal.SecurityIdentifier])
        )) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sidObj, 'FullControl', 'None', 'None', 'Allow'
        )
        $acl2.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $auth -AclObject $acl2
    return $auth
}

Assert-Elevated
$sshdExe = [string](Install-OpenSSHServerCapability)
if ([string]::IsNullOrWhiteSpace($sshdExe) -or -not (Test-Path -LiteralPath $sshdExe)) {
    throw "sshd.exe unresolved after install (got='$sshdExe')"
}
$sshDirBin = Split-Path -Parent $sshdExe
$sshKeygen = Join-Path $sshDirBin 'ssh-keygen.exe'
$sftpServer = Join-Path $sshDirBin 'sftp-server.exe'
if (-not (Test-Path -LiteralPath $sshKeygen)) {
    throw "ssh-keygen.exe missing next to $sshdExe"
}
Disable-DefaultPublicSshd
Remove-LegacyExternalSshFirewall -RuleName $LegacyFirewallRuleName

Write-HermesSshdConfig -Port $ListenPort -UserName $HermesUser `
    -ConfigFile $ConfigPath -HostKey $HostKeyPath -KeygenExe $sshKeygen -SftpServer $sftpServer
Ensure-HermesSshService -Name $ServiceName -Config $ConfigPath -SshdExe $sshdExe

try {
    $null = Ensure-AuthorizedKeysDir -UserName $HermesUser
    Write-Host "authorized_keys path prepared for $HermesUser"
}
catch {
    Write-Host "WARN: authorized_keys prep deferred: $($_.Exception.Message)"
}

& $sshdExe -t -f $ConfigPath
if ($LASTEXITCODE -ne 0) {
    throw "sshd -t failed for $ConfigPath"
}

Restart-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
Start-Service -Name $ServiceName
$svc = Get-Service -Name $ServiceName
if ($svc.Status -ne 'Running') {
    throw "Service $ServiceName failed to start"
}

$loop = Test-NetConnection -ComputerName '127.0.0.1' -Port $ListenPort -WarningAction SilentlyContinue
if (-not $loop.TcpTestSucceeded) {
    throw "Local loopback TCP/$ListenPort failed after sshd-hermes start"
}

Enable-TailscaleServeTcp -Port $ListenPort

Write-Host "sshd-hermes READY (ListenAddress=127.0.0.1 port=$ListenPort AllowUsers=$HermesUser; Serve TCP forwarder; Funnel forbidden)"
Write-Host "sshd_exe=$sshdExe"
Write-Host 'PasswordAuthentication no; no external sshd firewall rule; default sshd Disabled.'
Write-Host 'Install pubkey into hermes-win .ssh\authorized_keys; private key only on cdb-engineer profile.'
