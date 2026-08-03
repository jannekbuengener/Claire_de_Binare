#Requires -Version 5.1
<#
.SYNOPSIS
  Create dedicated non-admin Windows user + Hermes workspace (#4289).

.DESCRIPTION
  - Creates local user hermes-win if missing (non-admin).
  - Creates D:\Dev\HermesWorkspace\Claire_de_Binare (override via -WorkspaceRoot).
  - Removes ACL inheritance; grants SYSTEM/Administrators full, hermes-win limited.
  - Does NOT open public SSH/RDP/VNC. Does NOT touch the normal user profile.

.NOTES
  Run elevated once (UAC / Human-GO). No secrets are written by this script.
  Password: pass -PasswordSecure or set HERMES_WIN_PASSWORD env (SecureString recommended).
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$WorkspaceRoot = 'D:\Dev\HermesWorkspace\Claire_de_Binare',
    [string]$HermesUser = 'hermes-win',
    [SecureString]$PasswordSecure,
    [switch]$GrantWrite
)

$ErrorActionPreference = 'Stop'

function Assert-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'setup-workspace.ps1 must run elevated (Administrator).'
    }
}

function Assert-NotAdminProfileLeak {
    $forbidden = @(
        "$env:USERPROFILE\Documents",
        "$env:USERPROFILE\.ssh",
        "$env:LOCALAPPDATA\Google\Chrome",
        "$env:APPDATA\Mozilla\Firefox"
    )
    foreach ($path in $forbidden) {
        if ($WorkspaceRoot -like "$path*") {
            throw "Refuse workspace under personal/sensitive path: $WorkspaceRoot"
        }
    }
    if ($WorkspaceRoot -match '^[A-Za-z]:\\Users\\') {
        throw "Refuse workspace under C:\\Users profile tree: $WorkspaceRoot"
    }
}

function Ensure-HermesUser {
    param([string]$UserName, [SecureString]$Password)
    $existing = Get-LocalUser -Name $UserName -ErrorAction SilentlyContinue
    if (-not $existing) {
        if (-not $Password) {
            $envPw = $env:HERMES_WIN_PASSWORD
            if ([string]::IsNullOrWhiteSpace($envPw)) {
                throw 'Hermes user missing: pass -PasswordSecure or set HERMES_WIN_PASSWORD for creation.'
            }
            $Password = ConvertTo-SecureString $envPw -AsPlainText -Force
            Remove-Item Env:HERMES_WIN_PASSWORD -ErrorAction SilentlyContinue
        }
        if ($PSCmdlet.ShouldProcess($UserName, 'Create local non-admin user')) {
            New-LocalUser -Name $UserName -Password $Password -PasswordNeverExpires `
                -UserMayNotChangePassword:$false -AccountNeverExpires `
                -Description 'CDB Hermes dedicated workspace user (#4289)' | Out-Null
            Write-Host "Created local user: $UserName"
        }
    }
    else {
        Write-Host "Local user already exists: $UserName"
    }

    # Ensure NOT in Administrators (SID S-1-5-32-544; locale-independent).
    $adminGroup = Get-LocalGroup -SID 'S-1-5-32-544'
    $admins = Get-LocalGroupMember -Group $adminGroup -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*\$UserName" -or $_.Name -eq $UserName }
    if ($admins) {
        Remove-LocalGroupMember -Group $adminGroup -Member $UserName -ErrorAction Stop
        Write-Host "Removed $UserName from Administrators"
    }

    # Ensure Users membership for interactive/SSH baseline (SID S-1-5-32-545).
    $usersGroup = Get-LocalGroup -SID 'S-1-5-32-545'
    $users = Get-LocalGroupMember -Group $usersGroup -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*\$UserName" -or $_.Name -eq $UserName }
    if (-not $users) {
        Add-LocalGroupMember -Group $usersGroup -Member $UserName
    }

    $verify = Get-LocalUser -Name $UserName
    if (-not $verify.Enabled) {
        Enable-LocalUser -Name $UserName
    }
    $stillAdmin = Get-LocalGroupMember -Group $adminGroup -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*\$UserName" -or $_.Name -eq $UserName }
    if ($stillAdmin) {
        throw "FAIL: $UserName is still in Administrators after remediation"
    }
    Write-Host "Verified non-admin user: $UserName (Enabled=$($verify.Enabled))"
}

Assert-Elevated
Assert-NotAdminProfileLeak
Ensure-HermesUser -UserName $HermesUser -Password $PasswordSecure

$parent = Split-Path -Parent $WorkspaceRoot
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    New-Item -ItemType Directory -Path $WorkspaceRoot -Force | Out-Null
}

$acl = Get-Acl -LiteralPath $WorkspaceRoot
$acl.SetAccessRuleProtection($true, $false)
@($acl.Access) | ForEach-Object { [void]$acl.RemoveAccessRule($_) }

# Well-known SIDs: Administrators S-1-5-32-544, SYSTEM S-1-5-18 (locale-safe).
$adminSid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
$systemSid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
$userAccount = New-Object System.Security.Principal.NTAccount("$env:COMPUTERNAME\$HermesUser")

$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $adminSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
)
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $systemSid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
)
$rights = if ($GrantWrite) { 'Modify' } else { 'ReadAndExecute' }
$userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $userAccount, $rights, 'ContainerInherit,ObjectInherit', 'None', 'Allow'
)
$acl.AddAccessRule($adminRule)
$acl.AddAccessRule($systemRule)
$acl.AddAccessRule($userRule)
Set-Acl -LiteralPath $WorkspaceRoot -AclObject $acl

# Deny-list smoke: ensure we did not grant Users/Everyone (SID compare, no Translate).
$acl2 = Get-Acl -LiteralPath $WorkspaceRoot
$usersSidValue = 'S-1-5-32-545'
$worldSidValue = 'S-1-1-0'
$bad = $acl2.Access | Where-Object {
    $id = $_.IdentityReference
    $s = "$id"
    if ($s -match '^(Everyone|Jeder|BUILTIN\\Users|VORDEFINIERT\\Benutzer)$') { return $true }
    if ($id -is [System.Security.Principal.SecurityIdentifier]) {
        return ($id.Value -eq $usersSidValue -or $id.Value -eq $worldSidValue)
    }
    return $false
}
if ($bad) {
    throw 'FAIL: unexpected broad ACE present on workspace'
}

Write-Host "Workspace ready: $WorkspaceRoot (user=$HermesUser rights=$rights)"
Write-Host 'Next: .\infrastructure\hermes\windows\setup-sshd-hermes.ps1 (Tailscale-only sshd-hermes).'
Write-Host 'Kill-switch: infrastructure/hermes/windows/kill-switch.ps1 -Action Disable'
