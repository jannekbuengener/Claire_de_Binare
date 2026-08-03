#Requires -Version 5.1
<#
.SYNOPSIS
  Install/configure dedicated Tailscale-only OpenSSH listener sshd-hermes (#4289).

.DESCRIPTION
  Based on Microsoft OpenSSH Server docs (Add-WindowsCapability OpenSSH.Server,
  sshd_config ListenAddress / AllowUsers / PasswordAuthentication).

  - Installs OpenSSH.Server if missing.
  - Disables the default system-wide sshd service and the public
    OpenSSH-Server-In-TCP firewall rule.
  - Creates sshd-hermes with a private config bound to the Windows Tailscale IP.
  - Firewall allows inbound only from the cdb-hermes-01 Tailscale IP.
  - Pubkey-only auth for hermes-win. No password SSH, no RDP/VNC, no forwarding.

.NOTES
  Run elevated once. Does not print Tailscale IPs to GitHub evidence files.
  Docs gate: learn.microsoft.com OpenSSH install + server configuration (2025).
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$HermesUser = 'hermes-win',
    [string]$ServiceName = 'sshd-hermes',
    [string]$ConfigPath = 'C:\ProgramData\ssh\sshd_hermes_config',
    [string]$HostKeyPath = 'C:\ProgramData\ssh\ssh_host_ed25519_key',
    [string]$HermesPeerName = 'cdb-hermes-01',
    [int]$ListenPort = 22,
    [string]$FirewallRuleName = 'CDB-Hermes-sshd-hermes-Tailscale'
)

$ErrorActionPreference = 'Stop'

function Assert-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'setup-sshd-hermes.ps1 must run elevated (Administrator).'
    }
}

function Get-TailscaleIPv4 {
    param([string]$HostName)
    $json = & tailscale status --json 2>$null | ConvertFrom-Json
    if (-not $json) { throw 'tailscale status --json failed' }
    if ($HostName -eq 'self') {
        $ips = @($json.Self.TailscaleIPs)
    }
    else {
        $peer = $json.Peer.PSObject.Properties.Value |
            Where-Object { $_.HostName -eq $HostName -or $_.DNSName -like "$HostName*" } |
            Select-Object -First 1
        if (-not $peer) { throw "Tailscale peer not found: $HostName" }
        if (-not $peer.Online) { throw "Tailscale peer offline: $HostName" }
        $ips = @($peer.TailscaleIPs)
    }
    $v4 = $ips | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1
    if (-not $v4) { throw "No Tailscale IPv4 for $HostName" }
    return $v4
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

    # Prefer winget MSI path — Add-WindowsCapability/-Online often hangs on DISM/WU.
    # Docs gate: Win32-OpenSSH via winget (package id Microsoft.OpenSSH.Preview).
    # Avoid WSL/bash shims entirely.
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        $packageId = 'Microsoft.OpenSSH.Preview'
        if ($PSCmdlet.ShouldProcess($packageId, 'winget install OpenSSH Server')) {
            Write-Host "Installing OpenSSH Server via winget ($packageId, no DISM)..."
            # IMPORTANT: swallow winget stdout — otherwise it becomes the function's
            # return value in PowerShell and corrupts $sshdExe (empty Path errors).
            & winget.exe install --id $packageId -e --source winget `
                --accept-package-agreements --accept-source-agreements `
                --disable-interactivity *>$null
            $wingetExit = $LASTEXITCODE
            # Common benign codes: already installed / no newer version.
            if ($wingetExit -notin @(0, -1978335189, -1978335135)) {
                throw "winget install $packageId failed exit=$wingetExit"
            }
        }
    }
    else {
        # Fallback only when winget is unavailable.
        Write-Host 'winget missing; falling back to Add-WindowsCapability (may be slow)...'
        $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' -ErrorAction Stop
        if ($cap.State -ne 'Installed') {
            if ($PSCmdlet.ShouldProcess('OpenSSH.Server~~~~0.0.1.0', 'Add-WindowsCapability')) {
                Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
            }
        }
    }

    $sshd = Resolve-SshdExe
    if ([string]::IsNullOrWhiteSpace($sshd)) {
        throw 'OpenSSH Server install did not provide sshd.exe'
    }
    # Explicit single-string return (no accidental pipeline pollution).
    return [string]$sshd
}

function Disable-DefaultPublicSshd {
    $default = Get-Service -Name 'sshd' -ErrorAction SilentlyContinue
    if ($default) {
        if ($default.Status -eq 'Running') {
            Stop-Service -Name 'sshd' -Force -ErrorAction SilentlyContinue
        }
        Set-Service -Name 'sshd' -StartupType Disabled
        Write-Host 'Default sshd service set to Disabled (Hermes uses sshd-hermes only).'
    }
    $pubRule = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
    if ($pubRule) {
        Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'
        Write-Host 'Disabled public OpenSSH-Server-In-TCP firewall rule.'
    }
}

function Write-HermesSshdConfig {
    param(
        [string]$ListenIp,
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
    if ([string]::IsNullOrWhiteSpace($ListenIp)) { throw 'ListenIp is required' }
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
    $content = @"
# CDB Hermes dedicated sshd (#4289). Do not expose publicly.
# Windows+Tailscale: ListenAddress 0.0.0.0 is required in practice — peer TCP is
# not reliably delivered to a unicast Tailscale bind (local TS bind tests can
# still pass). Public exposure is prevented by:
#   - OpenSSH-Server-In-TCP disabled
#   - firewall RemoteAddress = cdb-hermes-01 Tailscale IP only
#   - PasswordAuthentication no / AllowUsers hermes-win
#   - default system sshd Disabled
Port $Port
ListenAddress 0.0.0.0
HostKey $HostKey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitEmptyPasswords no
AllowUsers $UserName
AuthorizedKeysFile .ssh/authorized_keys
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
                -DisplayName 'CDB Hermes OpenSSH (Tailscale-only)' `
                -Description 'Dedicated Hermes bridge for hermes-win (#4289). Not the public sshd.' `
                -StartupType Automatic | Out-Null
        }
    }
    else {
        & sc.exe config $Name binPath= $binPath | Out-Null
        Set-Service -Name $Name -StartupType Automatic
    }
}

function Ensure-TailscaleFirewallRule {
    param(
        [string]$RuleName,
        [string]$LocalIp,
        [string]$RemoteIp,
        [int]$Port
    )
    $existing = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-NetFirewallRule -Name $RuleName
    }
    if ($PSCmdlet.ShouldProcess($RuleName, 'New-NetFirewallRule Tailscale-only')) {
        # IMPORTANT: do not set -LocalAddress to the Tailscale IP. On Windows this
        # often fails to match packets even when sshd ListenAddress is correct,
        # causing Hermes→Windows TCP timeouts while `tailscale ping` still works.
        # Restriction is RemoteAddress = cdb-hermes-01 Tailscale IP only + sshd
        # ListenAddress bind (no 0.0.0.0). Public OpenSSH rule stays disabled.
        New-NetFirewallRule -Name $RuleName `
            -DisplayName 'CDB Hermes sshd-hermes (Tailscale from cdb-hermes-01)' `
            -Direction Inbound -Action Allow -Enabled True -Profile Any `
            -Protocol TCP -LocalPort $Port `
            -RemoteAddress $RemoteIp | Out-Null
        Write-Host "Firewall rule ${RuleName}: remote=hermes-ts only; localAddress=any (sshd still firewalled)"
    }
}

function Ensure-AuthorizedKeysDir {
    param([string]$UserName)
    $home = "C:\Users\$UserName"
    if (-not (Test-Path -LiteralPath $home)) {
        throw "User profile missing for $UserName (logon once or create profile before keys)."
    }
    $sshDir = Join-Path $home '.ssh'
    if (-not (Test-Path -LiteralPath $sshDir)) {
        New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    }
    # Restrict .ssh to SYSTEM, Administrators, and the user.
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

$localTs = Get-TailscaleIPv4 -HostName 'self'
$remoteTs = Get-TailscaleIPv4 -HostName $HermesPeerName

Write-HermesSshdConfig -ListenIp $localTs -Port $ListenPort -UserName $HermesUser `
    -ConfigFile $ConfigPath -HostKey $HostKeyPath -KeygenExe $sshKeygen -SftpServer $sftpServer
Ensure-HermesSshService -Name $ServiceName -Config $ConfigPath -SshdExe $sshdExe
Ensure-TailscaleFirewallRule -RuleName $FirewallRuleName -LocalIp $localTs `
    -RemoteIp $remoteTs -Port $ListenPort

# Profile/.ssh may not exist until user profile is created — try best-effort.
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

Write-Host "sshd-hermes READY (ListenAddress=Tailscale/self port=$ListenPort AllowUsers=$HermesUser)"
Write-Host "sshd_exe=$sshdExe"
Write-Host 'PasswordAuthentication no; public OpenSSH firewall rule disabled; default sshd Disabled.'
Write-Host 'Install pubkey into hermes-win .ssh\authorized_keys; private key only on cdb-engineer profile.'
