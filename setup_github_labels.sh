#!/bin/bash
# Setup GitHub Labels for Claire de Binaire
# Run: ./setup_github_labels.sh

set -e

echo "🏷️  Creating GitHub Labels for Claire de Binaire..."

# Architektur / Governance
gh label create codex \
  --description "Kanonische Regeln und Standards für Architektur und Projekt." \
  --color "0E8A16" || echo "⚠️  Label 'codex' already exists"

# Sprache / Tech
gh label create python \
  --description "Python-Code, Module, Typisierung, Abhängigkeiten und Runtime-Bugs." \
  --color "3572A5" || echo "⚠️  Label 'python' already exists"

# Qualität / Tests
gh label create testing \
  --description "Unit-, Integrations- und E2E-Tests, Coverage und Teststabilität." \
  --color "FBCA04" || echo "⚠️  Label 'testing' already exists"

# Allgemeine Entwicklung
gh label create development \
  --description "Allgemeine Entwicklungsaufgaben: Features, Refactoring, Bugfixes." \
  --color "5319E7" || echo "⚠️  Label 'development' already exists"

# Pipeline / Delivery
gh label create ci-cd \
  --description "Build-, Test- und Deploy-Pipelines, Linting und Release-Automation." \
  --color "B60205" || echo "⚠️  Label 'ci-cd' already exists"

gh label create github-actions \
  --description "GitHub Actions Workflows, Runner, Secrets und Pipeline-Orchestrierung." \
  --color "0052CC" || echo "⚠️  Label 'github-actions' already exists"

# Claire de Binaire – Services
gh label create cdb_core \
  --description "Signal-Engine: Strategien, Momentum-Logik und Event-Verarbeitung." \
  --color "1D76DB" || echo "⚠️  Label 'cdb_core' already exists"

gh label create cdb_risk \
  --description "Risk-Engine: Limits, Drawdown, Exposure, Stop-Loss und Alerts." \
  --color "D93F0B" || echo "⚠️  Label 'cdb_risk' already exists"

gh label create cdb_execution \
  --description "Execution-Service: Orderflow, Fills, Latenz und Fehlertoleranz." \
  --color "5319E7" || echo "⚠️  Label 'cdb_execution' already exists"

echo ""
echo "✅ GitHub Labels Setup Complete!"
echo ""
echo "📊 Label Overview:"
gh label list --limit 20
