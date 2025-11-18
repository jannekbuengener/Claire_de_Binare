# Test-Setup Validierung fuer Claire de Binaire
# Dieses Script prueft, ob alles korrekt installiert und konfiguriert ist

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Claire de Binaire - Test Setup Check" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$python = "C:\Users\janne\AppData\Local\Programs\Python\Python312\python.exe"
$errors = @()
$warnings = @()

# 1. Python-Version
Write-Host "[1/6] Python-Version pruefen..." -ForegroundColor Yellow
try {
    $pythonVersion = & $python --version 2>&1
    Write-Host "  OK $pythonVersion" -ForegroundColor Green
} catch {
    $errors += "Python nicht gefunden oder nicht ausfuehrbar"
    Write-Host "  FEHLER Python nicht gefunden" -ForegroundColor Red
}

# 2. pytest installiert
Write-Host "`n[2/6] pytest pruefen..." -ForegroundColor Yellow
try {
    $pytestVersion = & $python -m pytest --version 2>&1 | Select-String "pytest"
    Write-Host "  OK $pytestVersion" -ForegroundColor Green
} catch {
    $errors += "pytest nicht installiert"
    Write-Host "  FEHLER pytest nicht gefunden" -ForegroundColor Red
}

# 3. Dependencies
Write-Host "`n[3/6] Dependencies pruefen..." -ForegroundColor Yellow
$required = @("pytest", "pytest-cov", "pytest-mock", "pytest-asyncio", "black", "faker", "redis", "psycopg2-binary")
foreach ($pkg in $required) {
    $check = & $python -m pip show $pkg 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $pkg" -ForegroundColor Green
    } else {
        $warnings += "$pkg fehlt"
        Write-Host "  FEHLER $pkg fehlt" -ForegroundColor Red
    }
}

# 4. pytest.ini vorhanden
Write-Host "`n[4/6] pytest.ini pruefen..." -ForegroundColor Yellow
if (Test-Path "pytest.ini") {
    Write-Host "  OK pytest.ini existiert" -ForegroundColor Green
} else {
    $errors += "pytest.ini fehlt"
    Write-Host "  FEHLER pytest.ini fehlt" -ForegroundColor Red
}

# 5. Test-Ordner-Struktur
Write-Host "`n[5/6] Test-Struktur pruefen..." -ForegroundColor Yellow
if (Test-Path "tests\conftest.py") {
    Write-Host "  OK tests\conftest.py existiert" -ForegroundColor Green
} else {
    $errors += "conftest.py fehlt"
    Write-Host "  FEHLER conftest.py fehlt" -ForegroundColor Red
}

if (Test-Path "tests\test_risk_engine_core.py") {
    Write-Host "  OK tests\test_risk_engine_core.py existiert" -ForegroundColor Green
} else {
    $warnings += "test_risk_engine_core.py fehlt"
    Write-Host "  FEHLER test_risk_engine_core.py fehlt" -ForegroundColor Yellow
}

# 6. Test-Run durchfuehren
Write-Host "`n[6/6] Test-Run durchfuehren..." -ForegroundColor Yellow
try {
    $testResult = & $python -m pytest tests/test_risk_engine_core.py -v --tb=no 2>&1
    if ($testResult -match "4 skipped") {
        Write-Host "  OK Tests gefunden (4 skipped - bereit fuer Implementierung)" -ForegroundColor Green
    } elseif ($testResult -match "passed") {
        Write-Host "  OK Tests laufen und bestehen!" -ForegroundColor Green
    } else {
        $warnings += "Test-Run hatte Warnungen"
        Write-Host "  WARNUNG Test-Run mit Warnungen" -ForegroundColor Yellow
    }
} catch {
    $errors += "Test-Run fehlgeschlagen"
    Write-Host "  FEHLER Test-Run fehlgeschlagen" -ForegroundColor Red
}

# Zusammenfassung
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Zusammenfassung" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "OK Setup komplett! Alle Checks bestanden." -ForegroundColor Green
    Write-Host "`nBereit fuer Claude Code:" -ForegroundColor Cyan
    Write-Host "  1. pytest -v                    # Alle Tests" -ForegroundColor White
    Write-Host "  2. pytest -v -m unit           # Nur Unit-Tests" -ForegroundColor White
    Write-Host "  3. pytest --cov=services       # Mit Coverage" -ForegroundColor White
    exit 0
} else {
    if ($errors.Count -gt 0) {
        Write-Host "FEHLER gefunden ($($errors.Count)):" -ForegroundColor Red
        foreach ($e in $errors) {
            Write-Host "  - $e" -ForegroundColor Red
        }
    }
    if ($warnings.Count -gt 0) {
        Write-Host "`nWARNUNGEN ($($warnings.Count)):" -ForegroundColor Yellow
        foreach ($w in $warnings) {
            Write-Host "  - $w" -ForegroundColor Yellow
        }
    }
    Write-Host "`nFix:" -ForegroundColor Cyan
    Write-Host "  pip install -r requirements-dev.txt" -ForegroundColor White
    exit 1
}
