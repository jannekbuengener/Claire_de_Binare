<#
.SYNOPSIS
Initialize secrets for Claire de Binare development environment.

.DESCRIPTION
Creates the secrets directory at ~/Documents/.secrets/.cdb and generates
secure random passwords for all required secrets.

This script should be run ONCE when setting up a new development environment.

.EXAMPLE
.\init-secrets.ps1
#>

param(
    [switch]$Force  # Overwrite existing secrets
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SECRETS_PATH = Join-Path $env:USERPROFILE 'Documents\.secrets\.cdb'

Write-Host "`n=== Claire de Binare - Secrets Initialization ===" -ForegroundColor Cyan
Write-Host "Target: $SECRETS_PATH" -ForegroundColor Gray

# Create directory if it doesn't exist
if (-not (Test-Path $SECRETS_PATH)) {
    New-Item -ItemType Directory -Path $SECRETS_PATH -Force | Out-Null
    Write-Host "  [OK] Created secrets directory" -ForegroundColor Green
}

$secrets = @(
    'REDIS_PASSWORD',
    'POSTGRES_PASSWORD',
    'GRAFANA_PASSWORD'
)

foreach ($secret in $secrets) {
    $secretPath = Join-Path $SECRETS_PATH $secret

    if ((Test-Path $secretPath) -and -not $Force) {
        Write-Host "  [SKIP] $secret exists (use -Force to overwrite)" -ForegroundColor Yellow
        continue
    }

    # Generate secure random password (32 bytes base64 = 44 characters)
    $bytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $password = [Convert]::ToBase64String($bytes)

    # Write to file (no newline, no CRLF - critical for Docker secrets)
    # Use WriteAllBytes to avoid any encoding/line-ending issues
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($password)
    [System.IO.File]::WriteAllBytes($secretPath, $bytes)

    Write-Host "  [OK] Generated $secret" -ForegroundColor Green
}

# Set restrictive permissions (Windows equivalent of chmod 600)
$acl = Get-Acl $SECRETS_PATH
$acl.SetAccessRuleProtection($true, $false)  # Disable inheritance
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
    "FullControl",
    "ContainerInherit,ObjectInherit",
    "None",
    "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl $SECRETS_PATH $acl

Write-Host "`n=== Secrets initialized successfully ===" -ForegroundColor Green
Write-Host @"

Next steps:
1. Run the stack: .\infrastructure\scripts\stack_up.ps1
2. Access Grafana: http://localhost:3000 (admin / <GRAFANA_PASSWORD>)

To view a secret:
  Get-Content $SECRETS_PATH\REDIS_PASSWORD

"@ -ForegroundColor Cyan
