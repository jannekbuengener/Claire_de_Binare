# Setup GitHub Labels for Claire de Binaire
# PowerShell Script für Windows
# Run: .\setup_github_labels.ps1

# Zum Claire de Binaire Repository wechseln
Set-Location "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Cleanroom"

Write-Host "🏷️  Creating GitHub Labels for Claire de Binaire..." -ForegroundColor Cyan
Write-Host ""

# Funktion zum Erstellen von Labels (mit Fehlerbehandlung)
function Create-Label {
    param(
        [string]$Name,
        [string]$Description,
        [string]$Color
    )

    try {
        gh label create $Name --description $Description --color $Color 2>$null
        Write-Host "✅ Created label: $Name" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  Label '$Name' already exists" -ForegroundColor Yellow
    }
}

# Architektur / Governance
Create-Label -Name "codex" `
    -Description "Kanonische Regeln und Standards für Architektur und Projekt." `
    -Color "0E8A16"

# Sprache / Tech
Create-Label -Name "python" `
    -Description "Python-Code, Module, Typisierung, Abhängigkeiten und Runtime-Bugs." `
    -Color "3572A5"

# Qualität / Tests
Create-Label -Name "testing" `
    -Description "Unit-, Integrations- und E2E-Tests, Coverage und Teststabilität." `
    -Color "FBCA04"

# Allgemeine Entwicklung
Create-Label -Name "development" `
    -Description "Allgemeine Entwicklungsaufgaben: Features, Refactoring, Bugfixes." `
    -Color "5319E7"

# Pipeline / Delivery
Create-Label -Name "ci-cd" `
    -Description "Build-, Test- und Deploy-Pipelines, Linting und Release-Automation." `
    -Color "B60205"

Create-Label -Name "github-actions" `
    -Description "GitHub Actions Workflows, Runner, Secrets und Pipeline-Orchestrierung." `
    -Color "0052CC"

# Claire de Binaire – Services
Create-Label -Name "cdb_core" `
    -Description "Signal-Engine: Strategien, Momentum-Logik und Event-Verarbeitung." `
    -Color "1D76DB"

Create-Label -Name "cdb_risk" `
    -Description "Risk-Engine: Limits, Drawdown, Exposure, Stop-Loss und Alerts." `
    -Color "D93F0B"

Create-Label -Name "cdb_execution" `
    -Description "Execution-Service: Orderflow, Fills, Latenz und Fehlertoleranz." `
    -Color "5319E7"

Write-Host ""
Write-Host "✅ GitHub Labels Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Label Overview:" -ForegroundColor Cyan
gh label list --limit 20
