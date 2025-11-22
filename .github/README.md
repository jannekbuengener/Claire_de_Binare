# GitHub Workflows - Claire de Binare

## CI/CD Pipeline

**Status**: ✅ Active
**Version**: 2.0
**Config**: [`.github/workflows/ci.yaml`](./workflows/ci.yaml)

### Quick Start

Die CI/CD-Pipeline läuft automatisch bei:
- Pull Requests (alle Branches)
- Push auf `main`
- Manuell via Workflow Dispatch

### Pipeline-Übersicht

```
Code Quality → Tests → Security → Docs → Summary
```

**Jobs:**
1. **Linting** (Ruff) - Code-Style-Check
2. **Format Check** (Black) - Formatierung
3. **Type Check** (mypy) - Type-Hints
4. **Tests** (pytest) - Unit + Integration (Python 3.11 & 3.12)
5. **Secret Scan** (Gitleaks) - Keine Secrets im Code
6. **Security Audit** (Bandit) - Sicherheitsprüfung
7. **Dependency Audit** (pip-audit) - Vulnerable Dependencies
8. **Docs Check** (markdownlint) - Markdown-Qualität

### Lokale Simulation

```bash
# Quick-Check (vor Commit)
ruff check .
black --check .
pytest -q -m "not e2e"

# Full-Check (vor PR)
pytest -v -m "not e2e" --cov=services
gitleaks detect --no-git --source .
```

### Artefakte

**Verfügbar für 30 Tage:**
- Coverage Reports (HTML + XML)
- Security Reports (Bandit, pip-audit)

**Download:**
`Actions` → `Workflow Run` → `Artifacts`

### Dokumentation

**Vollständige Anleitung:**
[`backoffice/docs/CI_CD_GUIDE.md`](../backoffice/docs/CI_CD_GUIDE.md)

### Troubleshooting

**Pipeline schlägt fehl?**

1. **Linting/Format-Fehler:**
   ```bash
   ruff check . --fix
   black .
   ```

2. **Test-Fehler:**
   ```bash
   pytest -v -m "not e2e"
   ```

3. **Secret-Scan-Fehler:**
   - Secrets in `.env` verschieben
   - `.env` in `.gitignore`

**Weitere Hilfe:**
Siehe [CI_CD_GUIDE.md](../backoffice/docs/CI_CD_GUIDE.md#troubleshooting)

---

**Projekt**: Claire de Binare - Autonomous Crypto Trading Bot
**Maintainer**: Jannek
