# 🐳 Docker & CI/CD Setup - Quick Reference

## 📁 Neue Dateien

### GitHub Actions Workflows

**Working Repo (Claire_de_Binare):**
- \.github/workflows/docker-advanced.yml\ - Erweiterte Docker CI/CD Pipeline

**Docs Repo (Claire_de_Binare_Docs):**
- \.github/workflows/docs-ci.yml\ - Dokumentations CI/CD

### Docker Optimierungen

- \services/risk/Dockerfile.optimized\ - Optimiertes Dockerfile (Beispiel)
- \.dockerignore\ - Verbesserte Docker ignore Regeln
- \Makefile.docker\ - Make-Targets für Docker Operations

### Dokumentation

- \docs/DOCKER_OPTIMIZATION_GUIDE.md\ - Umfassender Optimierungsguide
- \docs/GITHUB_ACTIONS_DOCKER_SETUP.md\ - Implementierungsplan
- \scripts/optimize_dockerfiles.py\ - Automatischer Dockerfile Generator

## 🚀 Quick Start

### 1. Lokale Tests

\\\ash
# Dockerfile Linting
docker run --rm -i hadolint/hadolint < services/risk/Dockerfile

# Optimiertes Dockerfile bauen
docker build -f services/risk/Dockerfile.optimized -t cdb-risk:optimized .

# Size Vergleich
docker images | grep cdb-risk

# Security Scan
trivy image cdb-risk:optimized
\\\

### 2. Makefile verwenden

\\\ash
# Hilfe anzeigen
make -f Makefile.docker help

# Alle Services bauen
make -f Makefile.docker build

# Security Scan
make -f Makefile.docker security-scan

# Image Sizes
make -f Makefile.docker size-report

# Stack starten
make -f Makefile.docker compose-up
\\\

### 3. Optimierte Dockerfiles generieren

\\\ash
# Alle Services optimieren
python scripts/optimize_dockerfiles.py

# Einzelnes Service testen
docker build -f services/ws/Dockerfile.optimized -t cdb-ws:opt .
\\\

### 4. GitHub Actions aktivieren

\\\ash
# Working Repo
git add .github/workflows/docker-advanced.yml
git add .dockerignore
git add Makefile.docker
git add docs/*.md
git commit -m "feat: Add Docker optimization pipeline"
git push

# Docs Repo
cd ../Claire_de_Binare_Docs
git add .github/workflows/docs-ci.yml
git commit -m "feat: Add documentation CI"
git push
\\\

## 📊 Erwartete Verbesserungen

### Image Sizes
- **Vorher:** ~450MB pro Service
- **Nachher:** ~180MB pro Service
- **Ersparnis:** ~60%

### Build Times
- **Mit Cache:** 30-50% schneller
- **Rebuilds:** 40-60% schneller

### Security
- ✅ Hadolint Best Practices
- ✅ Trivy CVE Scanning
- ✅ Docker Scout Integration
- ✅ Non-root User enforced

## 🎯 Workflow Features

### docker-advanced.yml
1. **Dockerfile Linting** - Hadolint für Best Practices
2. **Compose Validation** - Syntax Checks
3. **Multi-Platform Builds** - AMD64 + ARM64
4. **Security Scanning** - Trivy + Docker Scout
5. **Image Analysis** - Size & Layer Inspection
6. **Integration Tests** - Full Stack Testing
7. **Cleanup** - Alte Images entfernen

### docs-ci.yml
1. **Markdown Linting** - Code Style
2. **Link Checking** - Broken Links
3. **Spell Checking** - Rechtschreibung
4. **YAML Validation** - Syntax
5. **Index Generation** - Auto-Documentation
6. **Secret Scanning** - Gitleaks

## 🔧 Konfiguration

### Registry ändern
In \.github/workflows/docker-advanced.yml\:
\\\yaml
env:
  REGISTRY: ghcr.io  # oder docker.io, quay.io, etc.
  IMAGE_NAMESPACE: your-org
\\\

### Services hinzufügen
In \scripts/optimize_dockerfiles.py\:
\\\python
SERVICE_CONFIG = {
    "new_service": {
        "health_port": 8009,
        "expose_port": 8009,
        "title": "New Service",
        "description": "Service description",
        "module_path": "services.new_service.service"
    }
}
\\\

## 📚 Dokumentation

Siehe:
- \docs/DOCKER_OPTIMIZATION_GUIDE.md\ - Detaillierte Optimierungen
- \docs/GITHUB_ACTIONS_DOCKER_SETUP.md\ - Implementierungsplan

## 🐛 Troubleshooting

### Build Fehler
\\\ash
# BuildKit aktivieren
export DOCKER_BUILDKIT=1

# Cache löschen
docker builder prune -af
\\\

### Workflow Fehler
\\\ash
# Lokal validieren
act -l  # List workflows
act -j dockerfile-lint  # Test job
\\\

### Image zu groß
\\\ash
# Layer analysieren
dive your-image:tag

# Optimiertes Dockerfile verwenden
docker build -f Dockerfile.optimized .
\\\

## ✅ Checkliste

- [ ] Neue Workflows committen
- [ ] .dockerignore erstellen
- [ ] Lokales Hadolint testen
- [ ] Optimiertes Dockerfile testen
- [ ] Image Sizes vergleichen
- [ ] Security Scans überprüfen
- [ ] GitHub Actions triggern
- [ ] Multi-Platform Build testen

---

**Fragen?** Siehe Hauptdokumentation oder kontaktiere das Team.
