# PowerShell Test Runner für Claire de Binare
# Windows-Alternative zum Makefile

param(
    [Parameter(Position=0)]
    [string]$Target = "help"
)

function Show-Help {
    Write-Host "Claire de Binare - Test Commands (PowerShell)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "CI-Tests (schnell, mit Mocks):"
    Write-Host "  .\run-tests.ps1 test                    - Alle CI-Tests (unit + integration)"
    Write-Host "  .\run-tests.ps1 test-unit               - Nur Unit-Tests"
    Write-Host "  .\run-tests.ps1 test-integration        - Nur Integration-Tests (mit Mocks)"
    Write-Host "  .\run-tests.ps1 test-coverage           - Tests mit Coverage-Report"
    Write-Host ""
    Write-Host "Lokale E2E-Tests (mit echten Containern):"
    Write-Host "  .\run-tests.ps1 test-e2e                - Alle E2E-Tests (18 Tests)"
    Write-Host "  .\run-tests.ps1 test-local              - Alle local-only Tests"
    Write-Host "  .\run-tests.ps1 test-local-stress       - Stress-Tests (100+ Events)"
    Write-Host "  .\run-tests.ps1 test-local-performance  - Performance-Tests (Query-Speed)"
    Write-Host "  .\run-tests.ps1 test-local-lifecycle    - Docker Lifecycle-Tests (DESTRUKTIV!)"
    Write-Host "  .\run-tests.ps1 test-full-system        - Komplett: Docker + E2E + Local"
    Write-Host ""
    Write-Host "Docker-Hilfsfunktionen:"
    Write-Host "  .\run-tests.ps1 docker-up               - Starte alle Container"
    Write-Host "  .\run-tests.ps1 docker-down             - Stoppe alle Container"
    Write-Host "  .\run-tests.ps1 docker-health           - Prüfe Health-Status aller Container"
}

function Run-CITests {
    Write-Host "🧪 Führe CI-Tests aus..." -ForegroundColor Yellow
    pytest -v -m "not e2e and not local_only"
}

function Run-UnitTests {
    Write-Host "🧪 Führe Unit-Tests aus..." -ForegroundColor Yellow
    pytest -v -m unit
}

function Run-IntegrationTests {
    Write-Host "🔌 Führe Integration-Tests aus (mit Mocks)..." -ForegroundColor Yellow
    pytest -v -m "integration and not e2e and not local_only"
}

function Run-CoverageTests {
    Write-Host "📊 Führe Tests mit Coverage-Report aus..." -ForegroundColor Yellow
    pytest --cov=services --cov=backoffice/services --cov-report=html --cov-report=term -m "not e2e and not local_only"
    Write-Host "📄 Coverage-Report: htmlcov/index.html"
}

function Run-E2ETests {
    Write-Host "🚀 Führe E2E-Tests aus (benötigt laufende Container)..." -ForegroundColor Yellow
    Write-Host "⚠️  Stelle sicher, dass 'docker compose up -d' läuft!" -ForegroundColor Red
    pytest -v -m e2e
}

function Run-LocalTests {
    Write-Host "🏠 Führe local-only Tests aus..." -ForegroundColor Yellow
    Write-Host "⚠️  Stelle sicher, dass 'docker compose up -d' läuft!" -ForegroundColor Red
    pytest -v -m local_only
}

function Run-LocalStressTests {
    Write-Host "🔥 Führe Stress-Tests aus (100+ Events)..." -ForegroundColor Yellow
    Write-Host "⚠️  Ressourcenintensiv - kann bis zu 60s dauern!" -ForegroundColor Red
    pytest -v -m "local_only and slow" tests/local/test_full_system_stress.py
}

function Run-LocalPerformanceTests {
    Write-Host "⚡ Führe Performance-Tests aus (Analytics Queries)..." -ForegroundColor Yellow
    pytest -v -m local_only tests/local/test_analytics_performance.py
}

function Run-LocalLifecycleTests {
    Write-Host "🔄 Führe Docker Lifecycle-Tests aus..." -ForegroundColor Yellow
    Write-Host "⚠️  DESTRUKTIV - Container werden neu gestartet!" -ForegroundColor Red
    pytest -v -m local_only tests/local/test_docker_lifecycle.py -s
}

function Run-FullSystemTests {
    Write-Host "🚀 Vollständiger System-Test..." -ForegroundColor Yellow
    Docker-Up
    Docker-Health
    Run-E2ETests
    Run-LocalTests
    Write-Host "✅ Vollständiger System-Test erfolgreich" -ForegroundColor Green
}

function Docker-Up {
    Write-Host "🐳 Starte Docker Compose Stack..." -ForegroundColor Yellow
    docker compose up -d
    Write-Host "⏳ Warte 10s bis Container hochgefahren sind..."
    Start-Sleep -Seconds 10
}

function Docker-Down {
    Write-Host "🛑 Stoppe Docker Compose Stack..." -ForegroundColor Yellow
    docker compose down
}

function Docker-Health {
    Write-Host "🏥 Prüfe Health-Status aller Container..." -ForegroundColor Yellow
    docker compose ps
}

# Main switch
switch ($Target) {
    "help" { Show-Help }
    "test" { Run-CITests }
    "test-unit" { Run-UnitTests }
    "test-integration" { Run-IntegrationTests }
    "test-coverage" { Run-CoverageTests }
    "test-e2e" { Run-E2ETests }
    "test-local" { Run-LocalTests }
    "test-local-stress" { Run-LocalStressTests }
    "test-local-performance" { Run-LocalPerformanceTests }
    "test-local-lifecycle" { Run-LocalLifecycleTests }
    "test-full-system" { Run-FullSystemTests }
    "docker-up" { Docker-Up }
    "docker-down" { Docker-Down }
    "docker-health" { Docker-Health }
    default {
        Write-Host "Unknown target: $Target" -ForegroundColor Red
        Show-Help
    }
}
