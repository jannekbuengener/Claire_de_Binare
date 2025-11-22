<#
Validate local test setup for Claire de Binare.

This script performs static checks only:
- Verifies Python version.
- Confirms required packages are installed.
- Ensures pytest.ini and tests/conftest.py exist.
- Highlights core smoke/unit test files that should be present.

It intentionally does NOT run pytest, docker, or any external services. To run
the suite manually after resolving warnings, execute commands such as:
    - pytest -q
    - pytest -m unit
    - pytest -m integration
    - pytest --cov=services --cov-report=term-missing
#>

$python = "python"
$errors = @()
$warnings = @()
$required = @(
    "pytest",
    "pytest-asyncio",
    "pytest-mock",
    "pytest-cov",
    "black",
    "flake8",
    "mypy",
    "faker",
    "redis",
    "psycopg2-binary",
    "requests"
)

Write-Host "`n=== Claire de Binare :: Validate Test Setup ===`n" -ForegroundColor Cyan

# Python version
Write-Host "[1/6] Checking Python version (expected 3.12.x)..." -ForegroundColor Yellow
try {
    $pythonVersion = & $python --version 2>&1
    if ($pythonVersion -match "3\.12\.") {
        Write-Host "  OK $pythonVersion" -ForegroundColor Green
    } else {
        $warnings += "Python 3.12.x recommended (found: $pythonVersion)"
        Write-Host "  WARN $pythonVersion" -ForegroundColor Yellow
    }
} catch {
    $errors += "Python executable not found"
    Write-Host "  ERROR Python not found" -ForegroundColor Red
}

# Dependencies
Write-Host "`n[2/5] Checking required packages..." -ForegroundColor Yellow
foreach ($pkg in $required) {
    $null = & $python -m pip show $pkg 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $pkg" -ForegroundColor Green
    } else {
        $errors += "$pkg missing"
        Write-Host "  MISSING $pkg" -ForegroundColor Red
    }
}

# pytest.ini
Write-Host "`n[3/5] Verifying pytest.ini..." -ForegroundColor Yellow
if (Test-Path "pytest.ini") {
    Write-Host "  OK pytest.ini present" -ForegroundColor Green
} else {
    $errors += "pytest.ini missing"
    Write-Host "  ERROR pytest.ini missing" -ForegroundColor Red
}

# conftest.py
Write-Host "`n[4/5] Verifying tests/conftest.py..." -ForegroundColor Yellow
if (Test-Path "tests/conftest.py") {
    Write-Host "  OK conftest.py present" -ForegroundColor Green
} else {
    $errors += "tests/conftest.py missing"
    Write-Host "  ERROR tests/conftest.py missing" -ForegroundColor Red
}

# Smoke tests presence
Write-Host "`n[5/5] Checking core test files..." -ForegroundColor Yellow
$files = @("tests/test_smoke_repo.py", "tests/test_compose_smoke.py", "tests/test_risk_engine_core.py")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  OK $file" -ForegroundColor Green
    } else {
        $warnings += "$file missing"
        Write-Host "  MISSING $file" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "All checks passed. Test environment ready." -ForegroundColor Green
    Write-Host "Run tests manually, for example: pytest -q" -ForegroundColor Cyan
    exit 0
}

if ($errors.Count -gt 0) {
    Write-Host "Errors:" -ForegroundColor Red
    foreach ($err in $errors) { Write-Host "  - $err" -ForegroundColor Red }
}

if ($warnings.Count -gt 0) {
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($warn in $warnings) { Write-Host "  - $warn" -ForegroundColor Yellow }
}

if ($errors.Count -gt 0) {
    Write-Host "`nResolve the above items before running the full suite." -ForegroundColor Cyan
    exit 1
}

Write-Host "`nResolve warnings if possible, then run tests manually (e.g. pytest -q)." -ForegroundColor Cyan
exit 0
