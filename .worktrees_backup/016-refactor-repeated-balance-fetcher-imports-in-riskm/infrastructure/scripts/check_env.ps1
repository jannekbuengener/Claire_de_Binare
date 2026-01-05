# check_env.ps1 - ENV Variable Validation für Claire de Binare
# Purpose: Validiert .env gegen erwartete Variablen und Werte

param(
    [string]$EnvFile = ".env"
)

# ANSI Colors
$RED = "`e[31m"
$GREEN = "`e[32m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

Write-Host "${BLUE}=== ENV Validation für Claire de Binare ===${RESET}`n"

# Check if .env exists
if (-not (Test-Path $EnvFile)) {
    Write-Host "${RED}[ERROR]${RESET} $EnvFile nicht gefunden!"
    Write-Host "${YELLOW}[INFO]${RESET} Kopiere .env.template zu .env und fülle Werte aus."
    exit 1
}

Write-Host "${GREEN}[OK]${RESET} $EnvFile gefunden`n"

# Parse .env
$envVars = @{}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        $envVars[$key] = $value
    }
}

Write-Host "${BLUE}Found $($envVars.Count) variables in $EnvFile${RESET}`n"

# Expected Variables mit Validierung
$expectedVars = @{
    # Database
    "POSTGRES_HOST" = @{ Required = $true; Type = "string"; Default = "cdb_postgres" }
    "POSTGRES_PORT" = @{ Required = $true; Type = "int"; Default = "5432" }
    "POSTGRES_USER" = @{ Required = $true; Type = "string"; Default = "claire_user" }
    "POSTGRES_PASSWORD" = @{ Required = $true; Type = "secret"; MinLength = 8 }
    "POSTGRES_DB" = @{ Required = $true; Type = "string"; Default = "claire_de_binare" }

    # Redis
    "REDIS_HOST" = @{ Required = $true; Type = "string"; Default = "cdb_redis" }
    "REDIS_PORT" = @{ Required = $true; Type = "int"; Default = "6379" }
    "REDIS_PASSWORD" = @{ Required = $false; Type = "secret" }

    # Risk Limits
    "MAX_POSITION_PCT" = @{ Required = $true; Type = "float"; Min = 0.01; Max = 1.0; Default = "0.10" }
    "MAX_DAILY_DRAWDOWN_PCT" = @{ Required = $true; Type = "float"; Min = 0.01; Max = 0.5; Default = "0.05" }
    "MAX_TOTAL_EXPOSURE_PCT" = @{ Required = $true; Type = "float"; Min = 0.1; Max = 1.0; Default = "0.30" }
    "CIRCUIT_BREAKER_THRESHOLD_PCT" = @{ Required = $true; Type = "float"; Min = 0.05; Max = 0.5; Default = "0.10" }
    "MAX_SLIPPAGE_PCT" = @{ Required = $true; Type = "float"; Min = 0.001; Max = 0.1; Default = "0.02" }

    # System
    "DATA_STALE_TIMEOUT_SEC" = @{ Required = $true; Type = "int"; Min = 10; Max = 300; Default = "60" }
    "LOG_LEVEL" = @{ Required = $false; Type = "enum"; Values = @("DEBUG", "INFO", "WARNING", "ERROR"); Default = "INFO" }
    "ENVIRONMENT" = @{ Required = $false; Type = "enum"; Values = @("development", "staging", "production"); Default = "development" }

    # MEXC API (Optional für N1 Paper-Test)
    "MEXC_API_KEY" = @{ Required = $false; Type = "secret"; MinLength = 16 }
    "MEXC_API_SECRET" = @{ Required = $false; Type = "secret"; MinLength = 32 }
}

# Validation Results
$errors = @()
$warnings = @()
$ok = 0

foreach ($var in $expectedVars.Keys) {
    $config = $expectedVars[$var]
    $value = $envVars[$var]

    # Check if required var exists
    if ($config.Required -and [string]::IsNullOrWhiteSpace($value)) {
        $errors += "[MISSING] $var (Required)"
        Write-Host "${RED}[ERROR]${RESET} $var ist required aber fehlt!"
        continue
    }

    # Skip if optional and not set
    if (-not $config.Required -and [string]::IsNullOrWhiteSpace($value)) {
        if ($config.Default) {
            Write-Host "${YELLOW}[INFO]${RESET} $var nicht gesetzt, Default: $($config.Default)"
        }
        continue
    }

    # Type Validation
    switch ($config.Type) {
        "int" {
            try {
                $intValue = [int]$value
                if ($config.Min -and $intValue -lt $config.Min) {
                    $warnings += "$var zu klein (Min: $($config.Min), Ist: $intValue)"
                    Write-Host "${YELLOW}[WARN]${RESET} $var = $intValue (Min: $($config.Min))"
                } elseif ($config.Max -and $intValue -gt $config.Max) {
                    $warnings += "$var zu groß (Max: $($config.Max), Ist: $intValue)"
                    Write-Host "${YELLOW}[WARN]${RESET} $var = $intValue (Max: $($config.Max))"
                } else {
                    Write-Host "${GREEN}[OK]${RESET} $var = $intValue"
                    $ok++
                }
            } catch {
                $errors += "$var ist kein gültiger Integer: $value"
                Write-Host "${RED}[ERROR]${RESET} $var = '$value' (kein Integer)"
            }
        }

        "float" {
            try {
                $floatValue = [float]$value
                if ($config.Min -and $floatValue -lt $config.Min) {
                    $warnings += "$var zu klein (Min: $($config.Min), Ist: $floatValue)"
                    Write-Host "${YELLOW}[WARN]${RESET} $var = $floatValue (Min: $($config.Min))"
                } elseif ($config.Max -and $floatValue -gt $config.Max) {
                    $warnings += "$var zu groß (Max: $($config.Max), Ist: $floatValue)"
                    Write-Host "${YELLOW}[WARN]${RESET} $var = $floatValue (Max: $($config.Max))"
                } else {
                    Write-Host "${GREEN}[OK]${RESET} $var = $floatValue"
                    $ok++
                }
            } catch {
                $errors += "$var ist kein gültiger Float: $value"
                Write-Host "${RED}[ERROR]${RESET} $var = '$value' (kein Float)"
            }
        }

        "secret" {
            if ($config.MinLength -and $value.Length -lt $config.MinLength) {
                $errors += "$var zu kurz (Min: $($config.MinLength) Zeichen)"
                Write-Host "${RED}[ERROR]${RESET} $var zu kurz ($($value.Length) < $($config.MinLength))"
            } else {
                $masked = "*" * [Math]::Min(8, $value.Length)
                Write-Host "${GREEN}[OK]${RESET} $var = $masked (Length: $($value.Length))"
                $ok++
            }
        }

        "enum" {
            if ($config.Values -contains $value) {
                Write-Host "${GREEN}[OK]${RESET} $var = $value"
                $ok++
            } else {
                $errors += "$var hat ungültigen Wert: $value (Erlaubt: $($config.Values -join ', '))"
                Write-Host "${RED}[ERROR]${RESET} $var = '$value' (Erlaubt: $($config.Values -join ', '))"
            }
        }

        "string" {
            Write-Host "${GREEN}[OK]${RESET} $var = $value"
            $ok++
        }
    }
}

# Summary
Write-Host "`n${BLUE}=== Validation Summary ===${RESET}"
Write-Host "${GREEN}OK:${RESET} $ok"
Write-Host "${YELLOW}Warnings:${RESET} $($warnings.Count)"
Write-Host "${RED}Errors:${RESET} $($errors.Count)"

if ($errors.Count -gt 0) {
    Write-Host "`n${RED}[FAILED]${RESET} ENV Validation fehlgeschlagen!`n"
    Write-Host "Errors:"
    $errors | ForEach-Object { Write-Host "  - $_" }
    exit 1
} elseif ($warnings.Count -gt 0) {
    Write-Host "`n${YELLOW}[WARN]${RESET} ENV Validation mit Warnings bestanden`n"
    Write-Host "Warnings:"
    $warnings | ForEach-Object { Write-Host "  - $_" }
    exit 0
} else {
    Write-Host "`n${GREEN}[SUCCESS]${RESET} ENV Validation bestanden! ✅`n"
    exit 0
}
