@echo off
REM Setup GitHub Labels for Claire de Binaire
REM Windows CMD Script
REM Run: setup_github_labels.bat

cd /d "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Cleanroom"

echo.
echo ============================================================
echo   Creating GitHub Labels for Claire de Binaire
echo ============================================================
echo.

REM Architektur / Governance
gh label create codex --description "Kanonische Regeln und Standards fuer Architektur und Projekt." --color "0E8A16" 2>nul && echo [OK] codex || echo [EXISTS] codex

REM Sprache / Tech
gh label create python --description "Python-Code, Module, Typisierung, Abhaengigkeiten und Runtime-Bugs." --color "3572A5" 2>nul && echo [OK] python || echo [EXISTS] python

REM Qualitaet / Tests
gh label create testing --description "Unit-, Integrations- und E2E-Tests, Coverage und Teststabilitaet." --color "FBCA04" 2>nul && echo [OK] testing || echo [EXISTS] testing

REM Allgemeine Entwicklung
gh label create development --description "Allgemeine Entwicklungsaufgaben: Features, Refactoring, Bugfixes." --color "5319E7" 2>nul && echo [OK] development || echo [EXISTS] development

REM Pipeline / Delivery
gh label create ci-cd --description "Build-, Test- und Deploy-Pipelines, Linting und Release-Automation." --color "B60205" 2>nul && echo [OK] ci-cd || echo [EXISTS] ci-cd

gh label create github-actions --description "GitHub Actions Workflows, Runner, Secrets und Pipeline-Orchestrierung." --color "0052CC" 2>nul && echo [OK] github-actions || echo [EXISTS] github-actions

REM Claire de Binaire Services
gh label create cdb_core --description "Signal-Engine: Strategien, Momentum-Logik und Event-Verarbeitung." --color "1D76DB" 2>nul && echo [OK] cdb_core || echo [EXISTS] cdb_core

gh label create cdb_risk --description "Risk-Engine: Limits, Drawdown, Exposure, Stop-Loss und Alerts." --color "D93F0B" 2>nul && echo [OK] cdb_risk || echo [EXISTS] cdb_risk

gh label create cdb_execution --description "Execution-Service: Orderflow, Fills, Latenz und Fehlertoleranz." --color "5319E7" 2>nul && echo [OK] cdb_execution || echo [EXISTS] cdb_execution

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Label Overview:
gh label list --limit 20

pause
