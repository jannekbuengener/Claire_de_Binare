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
    [ValidateSet("mexc_api_key", "mexc_api_secret", "redis_password", "postgres_password", "grafana_password")]
    [string]$SecretName,

    [Parameter(Mandatory=$false)]
    [string]$Value
)

$ErrorActionPreference = "Stop"

# Secret directory
$secretDir = Join-Path $PSScriptRoot ".." ".." ".cdb_local" ".secrets"

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

    $secretPath = Join-Path $secretDir $Name

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

    Write-Host "✅ Secret '$Name' saved securely" -ForegroundColor Green
}

function Get-SecretValue {
    param([string]$Name)

    $secretPath = Join-Path $secretDir $Name
    if (Test-Path $secretPath) {
        return Get-Content $secretPath -Raw
    }
    return $null
}

function Test-Secrets {
    Write-Host "`n🔍 Validating Secrets" -ForegroundColor Cyan
    Write-Host "=" * 60

    $requiredSecrets = @(
        "redis_password",
        "postgres_password",
        "grafana_password",
        "mexc_api_key",
        "mexc_api_secret"
    )

    $allValid = $true

    foreach ($secret in $requiredSecrets) {
        $secretPath = Join-Path $secretDir $secret
        $exists = Test-Path $secretPath

        if ($exists) {
            $content = Get-Content $secretPath -Raw
            $isEmpty = [string]::IsNullOrWhiteSpace($content)

            if ($isEmpty) {
                Write-Host "  ❌ $secret : EMPTY" -ForegroundColor Red
                $allValid = $false
            } else {
                $length = $content.Trim().Length
                Write-Host "  ✅ $secret : SET ($length chars)" -ForegroundColor Green
            }
        } else {
            Write-Host "  ⚠️  $secret : NOT FOUND" -ForegroundColor Yellow
            $allValid = $false
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
        if (-not (Get-SecretValue "redis_password")) {
            $redis_pw = Read-Host "Enter Redis password (or press Enter to generate)"
            if ([string]::IsNullOrWhiteSpace($redis_pw)) {
                $redis_pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
            }
            Set-Secret "redis_password" $redis_pw
        } else {
            Write-Host "  ℹ️  redis_password already exists" -ForegroundColor Cyan
        }

        # PostgreSQL password
        if (-not (Get-SecretValue "postgres_password")) {
            $pg_pw = Read-Host "Enter PostgreSQL password (or press Enter to generate)"
            if ([string]::IsNullOrWhiteSpace($pg_pw)) {
                $pg_pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
            }
            Set-Secret "postgres_password" $pg_pw
        } else {
            Write-Host "  ℹ️  postgres_password already exists" -ForegroundColor Cyan
        }

        # Grafana password
        if (-not (Get-SecretValue "grafana_password")) {
            $grafana_pw = Read-Host "Enter Grafana password (or press Enter to generate)"
            if ([string]::IsNullOrWhiteSpace($grafana_pw)) {
                $grafana_pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object {[char]$_})
            }
            Set-Secret "grafana_password" $grafana_pw
        } else {
            Write-Host "  ℹ️  grafana_password already exists" -ForegroundColor Cyan
        }

        # MEXC API credentials
        Write-Host "`n🔑 MEXC API Credentials" -ForegroundColor Yellow
        Write-Host "   Get from: https://testnet.mexc.com/ (testnet) or https://www.mexc.com/ (live)" -ForegroundColor White

        if (-not (Get-SecretValue "mexc_api_key")) {
            $mexc_key = Read-Host "Enter MEXC API Key (or leave empty for now)"
            if (-not [string]::IsNullOrWhiteSpace($mexc_key)) {
                Set-Secret "mexc_api_key" $mexc_key.Trim()
            } else {
                "" | Out-File -FilePath (Join-Path $secretDir "mexc_api_key") -NoNewline
                Write-Host "  ⚠️  mexc_api_key left empty - configure before production!" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ℹ️  mexc_api_key already exists" -ForegroundColor Cyan
        }

        if (-not (Get-SecretValue "mexc_api_secret")) {
            $mexc_secret = Read-Host "Enter MEXC API Secret (or leave empty for now)"
            if (-not [string]::IsNullOrWhiteSpace($mexc_secret)) {
                Set-Secret "mexc_api_secret" $mexc_secret.Trim()
            } else {
                "" | Out-File -FilePath (Join-Path $secretDir "mexc_api_secret") -NoNewline
                Write-Host "  ⚠️  mexc_api_secret left empty - configure before production!" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ℹ️  mexc_api_secret already exists" -ForegroundColor Cyan
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
        Write-Host "   docker-compose up -d --no-deps --force-recreate cdb_execution cdb_risk" -ForegroundColor White
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
