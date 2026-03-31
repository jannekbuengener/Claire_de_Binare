# Secrets Management Policy

**Issue:** #316
**Status:** Implemented
**Last Updated:** 2026-03-31

---

## Overview

Claire de Binare stores secrets **outside the repository** to prevent accidental exposure.

## Secret Locations

### Local Development
```
C:\Users\<username>\Documents\.secrets\.cdb\
├── REDIS_PASSWORD
├── POSTGRES_PASSWORD
├── GRAFANA_PASSWORD
└── MEXC_API_KEY (optional)
```

### Docker Services
Services read secrets as Docker secrets mounted at `/run/secrets/<name>` at startup.
Compose files reference the host-side secrets directory via the `SECRETS_PATH` variable
(default: `~/Documents/.secrets/.cdb/`).

## Setup Instructions

### Windows (canonical)
```powershell
.\tools\cdb.ps1 secrets init
```
This creates `~/Documents/.secrets/.cdb/`, generates secure random passwords for all
required secrets, and sets restrictive file permissions.

### Linux / macOS
```bash
mkdir -p ~/Documents/.secrets/.cdb
openssl rand -base64 24 > ~/Documents/.secrets/.cdb/REDIS_PASSWORD
openssl rand -base64 24 > ~/Documents/.secrets/.cdb/POSTGRES_PASSWORD
openssl rand -base64 24 > ~/Documents/.secrets/.cdb/GRAFANA_PASSWORD
chmod 700 ~/Documents/.secrets/.cdb
```

### Verify
```bash
ls ~/Documents/.secrets/.cdb/
# Should list: REDIS_PASSWORD  POSTGRES_PASSWORD  GRAFANA_PASSWORD
```

## What's Allowed in Git

| File | Status | Purpose |
|------|--------|---------|
| `core/secrets.py` | ✅ Tracked | Secret loading logic (no values) |
| `core/domain/secrets.py` | ✅ Tracked | Domain-level secret reader |
| `~/Documents/.secrets/.cdb/*` | ❌ Never | Runtime secrets (host-side) |
| `/run/secrets/*` | ❌ Never | Mounted Docker secrets (container-side) |

## Git History Warning

⚠️ Previous versions of this repository contained secrets in git history.
These have been removed from tracking but remain in history.

**Recommendation:** Rotate all secrets after clone.

## CI/CD Secrets

GitHub Actions secrets are stored in:
- Repository Settings → Secrets and variables → Actions

Required secrets:
- `GEMINI_API_KEY` - For Gemini AI agent
- `CLAUDE_API_KEY` - For Claude AI agent

## Kubernetes (Future)

For production deployment, use:
- Kubernetes Secrets
- HashiCorp Vault
- External Secrets Operator

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
