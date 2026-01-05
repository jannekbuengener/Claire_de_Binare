# Secrets Management Policy

**Issue:** #316
**Status:** Implemented
**Last Updated:** 2025-12-28

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

### Docker Compose
Secrets are loaded via environment file:
```
.cdb_local/.secrets/.env.compose
```

This file is **gitignored** and must be created locally.

## Setup Instructions

### 1. Create Secrets Directory
```bash
mkdir -p ~/.secrets/.cdb
```

### 2. Generate Secrets
```bash
# Generate secure passwords
openssl rand -base64 24 > ~/.secrets/.cdb/REDIS_PASSWORD
openssl rand -base64 24 > ~/.secrets/.cdb/POSTGRES_PASSWORD
openssl rand -base64 24 > ~/.secrets/.cdb/GRAFANA_PASSWORD
```

### 3. Create Docker Compose Env File
```bash
cat > .cdb_local/.secrets/.env.compose << EOF
REDIS_PASSWORD=$(cat ~/.secrets/.cdb/REDIS_PASSWORD)
POSTGRES_PASSWORD=$(cat ~/.secrets/.cdb/POSTGRES_PASSWORD)
GRAFANA_PASSWORD=$(cat ~/.secrets/.cdb/GRAFANA_PASSWORD)
EOF
```

### 4. Verify
```bash
# Ensure secrets are not tracked
git check-ignore .cdb_local/.secrets/.env.compose
# Should output: .cdb_local/.secrets/.env.compose
```

## What's Allowed in Git

| File | Status | Purpose |
|------|--------|---------|
| `.env.example` | ✅ Tracked | Template with placeholder paths |
| `.secrets/*_password` | ❌ Never | Actual secrets |
| `.cdb_local/.secrets/*` | ❌ Never | Runtime secrets |
| `core/secrets.py` | ✅ Tracked | Secret loading logic (no values) |

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
