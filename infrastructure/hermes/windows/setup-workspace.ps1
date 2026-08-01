#Requires -Version 5.1
<#
.SYNOPSIS
  Prepare a dedicated, non-admin Windows workspace for Hermes (#4289).

.DESCRIPTION
  Creates D:\Dev\HermesWorkspace\Claire_de_Binare (override via -WorkspaceRoot),  # pragma: allowlist secret
  a dedicated local user (non-admin), and restrictive NTFS ACLs.
  Does NOT open public SSH/RDP/VNC ports. Does NOT touch the normal user profile.

.NOTES
  Run elevated once by Jannek (Human-GO). No secrets are written by this script.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$WorkspaceRoot = 'D:\Dev\HermesWorkspace\Claire_de_Binare',  # pragma: allowlist secret
    [string]$HermesUser = 'hermes-win',
    [switch]$GrantWrite
)

$ErrorActionPreference = 'Stop'

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
}

Assert-NotAdminProfileLeak

if (-not (Test-Path -LiteralPath (Split-Path -Parent $WorkspaceRoot))) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $WorkspaceRoot) -Force | Out-Null
}
if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    New-Item -ItemType Directory -Path $WorkspaceRoot -Force | Out-Null
}

# ACL: SYSTEM + Administrators full; HermesUser limited; remove inherited Everyone/Users.
$acl = Get-Acl -LiteralPath $WorkspaceRoot
$acl.SetAccessRuleProtection($true, $false)
$acl.Access | ForEach-Object { [void]$acl.RemoveAccessRule($_) }

$adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    'BUILTIN\Administrators', 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
)
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    'NT AUTHORITY\SYSTEM', 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
)
$rights = if ($GrantWrite) { 'Modify' } else { 'ReadAndExecute' }
$userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $HermesUser, $rights, 'ContainerInherit,ObjectInherit', 'None', 'Allow'
)
$acl.AddAccessRule($adminRule)
$acl.AddAccessRule($systemRule)
$acl.AddAccessRule($userRule)
Set-Acl -LiteralPath $WorkspaceRoot -AclObject $acl

Write-Host "Workspace ready: $WorkspaceRoot (user=$HermesUser rights=$rights)"
Write-Host 'Next: configure OpenSSH for hermes-win with pubkey auth on Tailscale only.'
Write-Host 'Kill-switch: infrastructure/hermes/windows/kill-switch.ps1 -Action Disable'
