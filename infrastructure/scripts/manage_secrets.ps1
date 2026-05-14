#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Manage Docker secrets for Claire de Binare
.DESCRIPTION
    Create, rotate, and validate secrets for production deployment
.PARAMETER Action
    Action to perform: setup, rotate, validate
.PARAMETER SecretName
    Name of secret (mexc_api_key, mexc_api_secret, etc.)
.EXAMPLE
    .\manage_secrets.ps1 -Action setup
    .\manage_secrets.ps1 -Action rotate -SecretName mexc_api_key
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("setup", "rotate", "validate", "list")]
    [string]$Action,

    [Parameter(Mandatory=$false)]
    [ValidateSet(
        "mexc_api_key",
        "mexc_api_secret",
        "redis_password",
        "postgres_password",
        "grafana_password",
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "POSTGRES_PASSWORD_DSN",
        "GRAFANA_PASSWORD",
        "MEXC_API_KEY.txt",
        "MEXC_API_SECRET.txt",
        "POSTGRES_READONLY_PASSWORD",
        "POSTGRES_READONLY_PASSWORD_DSN"
    )]
    [string]$SecretName,

    [Parameter(Mandatory=$false)]
    [string]$Value
)

$ErrorActionPreference = "Stop"

# Canonical secrets directory (Single Source of Truth)
# Canonical: ~/Documents/.secrets/.cdb  (matches SECRETS_PATH in compose.blue.yml / compose.red.yml)
$secretDir = Join-Path $env:USERPROFILE "Documents\.secrets\.cdb"

function Resolve-SecretFileName {
    param([string]$Name)

    switch ($Name) {
        "redis_password" { return "REDIS_PASSWORD" }
        "REDIS_PASSWORD" { return "REDIS_PASSWORD" }
        "postgres_password" { return "POSTGRES_PASSWORD" }
        "POSTGRES_PASSWORD" { return "POSTGRES_PASSWORD" }
        "postgres_password_dsn" { return "POSTGRES_PASSWORD_DSN" }
        "POSTGRES_PASSWORD_DSN" { return "POSTGRES_PASSWORD_DSN" }
        "grafana_password" { return "GRAFANA_PASSWORD" }
        "GRAFANA_PASSWORD" { return "GRAFANA_PASSWORD" }
        "mexc_api_key" { return "MEXC_API_KEY.txt" }
        "MEXC_API_KEY" { return "MEXC_API_KEY.txt" }
        "MEXC_API_KEY.txt" { return "MEXC_API_KEY.txt" }
        "mexc_api_secret" { return "MEXC_API_SECRET.txt" }
        "MEXC_API_SECRET" { return "MEXC_API_SECRET.txt" }
        "MEXC_API_SECRET.txt" { return "MEXC_API_SECRET.txt" }
        "POSTGRES_READONLY_PASSWORD" { return "POSTGRES_READONLY_PASSWORD" }
        "POSTGRES_READONLY_PASSWORD_DSN" { return "POSTGRES_READONLY_PASSWORD_DSN" }
        default { return $Name }
    }
}

function Initialize-SecretDirectory {
    if (-not (Test-Path $secretDir)) {
        Write-Host "📁 Creating secrets directory: $secretDir" -ForegroundColor Cyan
        New-Item -ItemType Directory -Path $secretDir -Force | Out-Null

        # Set restrictive permissions (Windows)
        $acl = Get-Acl $secretDir
        $acl.SetAccessRuleProtection($true, $false)  # Disable inheritance
        $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $env:USERNAME, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
        )
        $acl.AddAccessRule($accessRule)
        Set-Acl $secretDir $acl

        Write-Host "✅ Secrets directory created with restricted permissions" -ForegroundColor Green
    }
}

function Set-Secret {
    param(
        [string]$Name,
        [string]$SecretValue
    )

    $secretFileName = Resolve-SecretFileName $Name
    $secretPath = Join-Path $secretDir $secretFileName

    if (Test-Path $secretPath) {
        $backup = "${secretPath}.bak.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item $secretPath $backup
        Write-Host "📦 Backed up existing secret to: $backup" -ForegroundColor Yellow
    }

    # Write secret
    $SecretValue | Out-File -FilePath $secretPath -NoNewline -Encoding utf8

    # Set restrictive permissions
    $acl = Get-Acl $secretPath
    $acl.SetAccessRuleProtection($true, $false)
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $env:USERNAME, "FullControl", "None", "None", "Allow"
    )
    $acl.AddAccessRule($accessRule)
    Set-Acl $secretPath $acl

    Write-Host "✅ Secret '$secretFileName' saved securely" -ForegroundColor Green
}

function Get-SecretValue {
    param([string]$Name)

    $secretFileName = Resolve-SecretFileName $Name
    $secretPath = Join-Path $secretDir $secretFileName
    if (Test-Path $secretPath) {
        return Get-Content $secretPath -Raw
    }
    return $null
}

function Test-SecretPresence {
    param(
        [string]$Name,
        [bool]$Required = $true
    )

    $secretFileName = Resolve-SecretFileName $Name
    $secretPath = Join-Path $secretDir $secretFileName
    $exists = Test-Path $secretPath

    if ($exists) {
        $content = Get-Content $secretPath -Raw
        $isEmpty = [string]::IsNullOrWhiteSpace($content)

        if ($isEmpty) {
            if ($Required) {
                Write-Host "  ❌ $secretFileName : EMPTY" -ForegroundColor Red
            } else {
                Write-Host "  ⚠️  $secretFileName : OPTIONAL / EMPTY" -ForegroundColor Yellow
            }
            return $false
        }

        $length = $content.Trim().Length
        if ($Required) {
            Write-Host "  ✅ $secretFileName : SET ($length chars)" -ForegroundColor Green
        } else {
            Write-Host "  ℹ️  $secretFileName : OPTIONAL / SET ($length chars)" -ForegroundColor Cyan
        }
        return $true
    }

    if ($Required) {
        Write-Host "  ⚠️  $secretFileName : NOT FOUND" -ForegroundColor Yellow
    } else {
        Write-Host "  ℹ️  $secretFileName : OPTIONAL / ABSENT" -ForegroundColor Cyan
    }
    return $false
}

function Test-Secrets {
    Write-Host "`n🔍 Validating Secrets" -ForegroundColor Cyan
    Write-Host "=" * 60

    $requiredSecrets = @(
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "GRAFANA_PASSWORD",
        "MEXC_API_KEY.txt",
        "MEXC_API_SECRET.txt"
    )
    $optionalSecrets = @(
        "POSTGRES_PASSWORD_DSN",
        "POSTGRES_READONLY_PASSWORD",
        "POSTGRES_READONLY_PASSWORD_DSN"
    )

    $allValid = $true

    foreach ($secret in $requiredSecrets) {
        if (-not (Test-SecretPresence -Name $secret -Required $true)) {
            $allValid = $false
        }
    }

    if ($optionalSecrets.Count -gt 0) {
        Write-Host ""
        Write-Host "Optional secrets" -ForegroundColor Cyan
        Write-Host "-" * 60
        foreach ($secret in $optionalSecrets) {
            Test-SecretPresence -Name $secret -Required $false | Out-Null
        }
    }

    Write-Host ""
    if ($allValid) {
        Write-Host "✅ All secrets validated successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Some secrets are missing or invalid" -ForegroundColor Yellow
        Write-Host "   Run: .\manage_secrets.ps1 -Action setup" -ForegroundColor White
    }

    return $allValid
}

# Main logic
switch ($Action) {
    "setup" {
        Write-Host "`n🔐 Secret Setup Wizard" -ForegroundColor Cyan
        Write-Host "=" * 60

        Initialize-SecretDirectory

        # Redis password
        if (-not (Get-SecretValue "REDIS_PASSWORD")) {
            $redis_pw = Read-Host "Enter Redis password (or press Enter to generate)"
            if ([string]::IsNullOrWhiteSpace($redis_pw)) {
                $redis_pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
            }
            Set-Secret "REDIS_PASSWORD" $redis_pw
        } else {
            Write-Host "  ℹ️  REDIS_PASSWORD already exists" -ForegroundColor Cyan
        }

        # PostgreSQL password
        if (-not (Get-SecretValue "POSTGRES_PASSWORD")) {
            $pg_pw = Read-Host "Enter PostgreSQL password (or press Enter to generate)"
            if ([string]::IsNullOrWhiteSpace($pg_pw)) {
                $pg_pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
            }
            Set-Secret "POSTGRES_PASSWORD" $pg_pw
        } else {
            Write-Host "  ℹ️  POSTGRES_PASSWORD already exists" -ForegroundColor Cyan
        }

        # Grafana password
        if (-not (Get-SecretValue "GRAFANA_PASSWORD")) {
            $grafana_pw = Read-Host "Enter Grafana password (or press Enter to generate)"
            if ([string]::IsNullOrWhiteSpace($grafana_pw)) {
                $grafana_pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object {[char]$_})
            }
            Set-Secret "GRAFANA_PASSWORD" $grafana_pw
        } else {
            Write-Host "  ℹ️  GRAFANA_PASSWORD already exists" -ForegroundColor Cyan
        }

        # MEXC API credentials
        Write-Host "`n🔑 MEXC API Credentials" -ForegroundColor Yellow
        Write-Host "   Get from: https://testnet.mexc.com/ (testnet) or https://www.mexc.com/ (live)" -ForegroundColor White

        if (-not (Get-SecretValue "MEXC_API_KEY.txt")) {
            $mexc_key = Read-Host "Enter MEXC API Key (or leave empty for now)"
            if (-not [string]::IsNullOrWhiteSpace($mexc_key)) {
                Set-Secret "MEXC_API_KEY.txt" $mexc_key.Trim()
            } else {
                "" | Out-File -FilePath (Join-Path $secretDir "MEXC_API_KEY.txt") -NoNewline
                Write-Host "  ⚠️  MEXC_API_KEY.txt left empty - configure before production!" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ℹ️  MEXC_API_KEY.txt already exists" -ForegroundColor Cyan
        }

        if (-not (Get-SecretValue "MEXC_API_SECRET.txt")) {
            $mexc_secret = Read-Host "Enter MEXC API Secret (or leave empty for now)"
            if (-not [string]::IsNullOrWhiteSpace($mexc_secret)) {
                Set-Secret "MEXC_API_SECRET.txt" $mexc_secret.Trim()
            } else {
                "" | Out-File -FilePath (Join-Path $secretDir "MEXC_API_SECRET.txt") -NoNewline
                Write-Host "  ⚠️  MEXC_API_SECRET.txt left empty - configure before production!" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ℹ️  MEXC_API_SECRET.txt already exists" -ForegroundColor Cyan
        }

        Write-Host "`n✅ Setup complete!" -ForegroundColor Green
        Test-Secrets | Out-Null
    }

    "rotate" {
        if (-not $SecretName) {
            Write-Host "❌ -SecretName required for rotation" -ForegroundColor Red
            exit 1
        }

        Write-Host "`n🔄 Rotating Secret: $SecretName" -ForegroundColor Cyan
        Write-Host "=" * 60

        Initialize-SecretDirectory

        if ($Value) {
            Set-Secret $SecretName $Value
        } else {
            $newValue = Read-Host "Enter new value for $SecretName"
            if (-not [string]::IsNullOrWhiteSpace($newValue)) {
                Set-Secret $SecretName $newValue.Trim()
            } else {
                Write-Host "❌ Value cannot be empty" -ForegroundColor Red
                exit 1
            }
        }

        Write-Host "`n⚠️  Remember to restart services:" -ForegroundColor Yellow
        Write-Host "   .\tools\cdb.ps1 runtime up" -ForegroundColor White
        Write-Host "   (full BLUE+RED stack restart, not targeted; handles network creation)" -ForegroundColor DarkGray
    }

    "validate" {
        Test-Secrets
    }

    "list" {
        Write-Host "`n📋 Secret Files" -ForegroundColor Cyan
        Write-Host "=" * 60

        if (Test-Path $secretDir) {
            Get-ChildItem $secretDir -File | ForEach-Object {
                $size = $_.Length
                Write-Host "  $($_.Name) ($size bytes)" -ForegroundColor White
            }
        } else {
            Write-Host "  ℹ️  No secrets directory found" -ForegroundColor Yellow
            Write-Host "  Run: .\manage_secrets.ps1 -Action setup" -ForegroundColor White
        }
    }
}

Write-Host ""
