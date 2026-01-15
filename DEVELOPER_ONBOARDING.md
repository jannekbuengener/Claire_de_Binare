# Developer Onboarding Guide

**Welcome to Claire de Binare!** 🚀

This guide will help you set up your local development environment from scratch. Follow these steps to get up and running.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Environment Configuration](#environment-configuration)
4. [Secrets Management](#secrets-management)
5. [Running the Stack](#running-the-stack)
6. [Verification](#verification)
7. [Development Workflow](#development-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

| Tool | Version | Purpose | Installation |
|------|---------|---------|--------------|
| **Docker** | 20.10+ | Container runtime | [Install Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.0+ | Multi-container orchestration | Included with Docker Desktop |
| **Git** | 2.30+ | Version control | [Install Git](https://git-scm.com/downloads) |
| **Python** | 3.12+ | Service development | [Install Python](https://www.python.org/downloads/) |

### Optional Tools (Recommended)

- **Make** - Build automation (included on Linux/Mac, Windows: [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm))
- **jq** - JSON processing ([Install jq](https://stedolan.github.io/jq/download/))
- **gh CLI** - GitHub CLI ([Install gh](https://cli.github.com/))

### System Requirements

- **RAM**: 8GB minimum, 16GB recommended
- **Disk Space**: 20GB free space (for Docker images and data)
- **OS**: Windows 10/11, macOS 11+, or Linux (Ubuntu 20.04+)

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/jannekbuengener/Claire_de_Binare.git
cd Claire_de_Binare
```

### 2. Verify Prerequisites

**Check Docker**:
```bash
docker --version
docker compose version
```

**Check Python**:
```bash
python --version  # or python3 --version
```

**Check Git**:
```bash
git --version
```

If any command fails, install the missing prerequisite before continuing.

---

## Environment Configuration

### 1. Create .env File

Copy the environment template:

```bash
cp .env.example .env
```

### 2. Review .env Configuration

Open `.env` in your editor and review the default values. The most important settings:

```bash
# Secrets path (REQUIRED)
SECRETS_PATH=${HOME}/Documents/.secrets/.cdb  # Linux/Mac
# SECRETS_PATH=C:\Users\<username>\Documents\.secrets\.cdb  # Windows

# Safety settings (CRITICAL)
MEXC_TESTNET=true          # Always true for development
MOCK_TRADING=true          # Use mock executor (no real trades)
DRY_RUN=true               # Log trades without executing
SIGNAL_STRATEGY_ID=paper   # Paper trading mode

# Stack configuration
STACK_NAME=cdb
NETWORK=cdb_network
```

**⚠️ IMPORTANT**: Never set `MEXC_TESTNET=false` or `SIGNAL_STRATEGY_ID=live` in development!

### 3. Update SECRETS_PATH (if needed)

If you want to use a different secrets location, update `SECRETS_PATH` in `.env`:

**Linux/Mac**:
```bash
SECRETS_PATH=${HOME}/Documents/.secrets/.cdb
```

**Windows**:
```bash
SECRETS_PATH=C:\Users\YourUsername\Documents\.secrets\.cdb
```

---

## Secrets Management

CDB uses a **Single Source of Truth** architecture for secrets. All secrets are stored in `~/Documents/.secrets/.cdb/` and read by Docker Compose via the `SECRETS_PATH` environment variable.

### 1. Initialize Secrets

**Linux/Mac**:
```bash
chmod +x infrastructure/scripts/init-secrets.sh
./infrastructure/scripts/init-secrets.sh
```

**Windows (PowerShell)**:
```powershell
.\infrastructure\scripts\init-secrets.ps1
```

This script generates:
- `REDIS_PASSWORD` - Redis authentication
- `POSTGRES_PASSWORD` - PostgreSQL database password
- `GRAFANA_PASSWORD` - Grafana admin password

### 2. Verify Secrets Created

**Linux/Mac**:
```bash
ls -la ~/Documents/.secrets/.cdb/
```

**Windows**:
```powershell
dir $env:USERPROFILE\Documents\.secrets\.cdb\
```

You should see three files:
- `REDIS_PASSWORD`
- `POSTGRES_PASSWORD`
- `GRAFANA_PASSWORD`

### 3. View a Secret (Optional)

**Linux/Mac**:
```bash
cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD
```

**Windows**:
```powershell
Get-Content $env:USERPROFILE\Documents\.secrets\.cdb\REDIS_PASSWORD
```

---

## Running the Stack

### 1. Start the Development Stack

**Option A: Using Docker Compose Directly** (Recommended):
```bash
docker compose -f infrastructure/compose/dev.yml up -d
```

**Option B: Using Makefile** (if Make is installed):
```bash
make docker-up
```

**Option C: Using PowerShell Script** (Windows):
```powershell
.\infrastructure\scripts\stack_up.ps1
```

### 2. Monitor Startup

Watch the containers start:

```bash
docker compose -f infrastructure/compose/dev.yml ps
```

Expected services:
- `cdb_redis` - Redis stream broker
- `cdb_postgres` - PostgreSQL database
- `cdb_prometheus` - Metrics collection
- `cdb_grafana` - Monitoring dashboard
- `cdb_ws` - WebSocket service
- `cdb_signal` - Signal generation
- `cdb_candles` - Candle aggregation
- `cdb_regime` - Regime detection
- `cdb_allocation` - Portfolio allocation
- `cdb_risk` - Risk management
- `cdb_execution` - Order execution
- `cdb_db_writer` - Database persistence

### 3. Wait for Health Checks

Give the stack 2-3 minutes to fully initialize. Check health status:

```bash
docker compose -f infrastructure/compose/dev.yml ps
```

All services should show `healthy` or `running` status.

---

## Verification

### 1. Check Service Health

**Grafana** (Monitoring Dashboard):
```
URL: http://localhost:3000
Username: admin
Password: (see ~/Documents/.secrets/.cdb/GRAFANA_PASSWORD)
```

**Prometheus** (Metrics):
```
URL: http://localhost:9090
```

**WebSocket Service Health**:
```bash
curl http://localhost:8000/health
```

Should return: `{"status": "healthy"}`

### 2. Verify Database Connection

**Check PostgreSQL**:
```bash
docker compose -f infrastructure/compose/dev.yml exec cdb_postgres psql -U claire_user -d claire_de_binare -c "\dt"
```

Should list database tables (signals, orders, fills, etc.).

### 3. Verify Redis Streams

**Check Redis**:
```bash
docker compose -f infrastructure/compose/dev.yml exec cdb_redis redis-cli -a $(cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD) PING
```

Should return: `PONG`

**List Streams**:
```bash
docker compose -f infrastructure/compose/dev.yml exec cdb_redis redis-cli -a $(cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD) KEYS "stream:*"
```

Should show streams like: `stream:candles_1m`, `stream:signals`, `stream:orders`

### 4. Run Smoke Tests

```bash
pytest tests/e2e/test_smoke_pipeline.py -v
```

If tests pass, your environment is correctly configured! ✅

---

## Development Workflow

### 1. Viewing Logs

**All services**:
```bash
docker compose -f infrastructure/compose/dev.yml logs -f
```

**Specific service**:
```bash
docker compose -f infrastructure/compose/dev.yml logs -f cdb_signal
```

**Tail last 100 lines**:
```bash
docker compose -f infrastructure/compose/dev.yml logs --tail=100 -f cdb_risk
```

### 2. Restarting a Service

**After code changes**:
```bash
docker compose -f infrastructure/compose/dev.yml restart cdb_signal
```

**Rebuild and restart**:
```bash
docker compose -f infrastructure/compose/dev.yml up -d --build cdb_signal
```

### 3. Accessing Service Shell

**Execute command in container**:
```bash
docker compose -f infrastructure/compose/dev.yml exec cdb_signal bash
```

**Run Python REPL inside service**:
```bash
docker compose -f infrastructure/compose/dev.yml exec cdb_signal python3
```

### 4. Running Tests

**Unit tests**:
```bash
pytest tests/unit/ -v
```

**Integration tests**:
```bash
pytest tests/integration/ -v
```

**With coverage**:
```bash
make test-coverage
```

### 5. Stopping the Stack

**Stop all services**:
```bash
docker compose -f infrastructure/compose/dev.yml down
```

**Stop and remove volumes** (⚠️ deletes data):
```bash
docker compose -f infrastructure/compose/dev.yml down -v
```

---

## Troubleshooting

### Common Issues

#### 1. **"Missing .env file"**

**Symptom**: `docker compose` fails with "environment file not found"

**Solution**:
```bash
cp .env.example .env
```

---

#### 2. **"Secret file not found"**

**Symptom**: Docker Compose fails with "secrets file not found: REDIS_PASSWORD"

**Solution**: Run secrets initialization script:

**Linux/Mac**:
```bash
./infrastructure/scripts/init-secrets.sh
```

**Windows**:
```powershell
.\infrastructure\scripts\init-secrets.ps1
```

---

#### 3. **"Port already in use"**

**Symptom**: `Error: bind: address already in use` (port 6379, 5432, etc.)

**Solution**: Check for conflicting services:
```bash
# Linux/Mac
sudo lsof -i :6379
sudo lsof -i :5432

# Windows
netstat -ano | findstr :6379
netstat -ano | findstr :5432
```

Stop the conflicting service or change the port in `.env`.

---

#### 4. **"Cannot connect to Docker daemon"**

**Symptom**: `Cannot connect to the Docker daemon`

**Solution**:
1. Ensure Docker Desktop is running
2. Check Docker service status:
   ```bash
   docker info
   ```
3. Restart Docker Desktop if needed

---

#### 5. **"Permission denied: secrets directory"**

**Symptom**: Cannot read secrets files

**Solution**: Fix permissions:

**Linux/Mac**:
```bash
chmod 700 ~/Documents/.secrets/.cdb
chmod 600 ~/Documents/.secrets/.cdb/*
```

**Windows**: Run PowerShell as Administrator and re-run `init-secrets.ps1`

---

#### 6. **"Service unhealthy"**

**Symptom**: `docker compose ps` shows `unhealthy` status

**Solution**: Check service logs:
```bash
docker compose -f infrastructure/compose/dev.yml logs <service_name>
```

Common causes:
- Missing environment variable
- Wrong secret password
- Redis/PostgreSQL not fully started
- Port conflict

---

#### 7. **"Tests fail with connection errors"**

**Symptom**: Tests fail to connect to Redis or PostgreSQL

**Solution**:
1. Ensure stack is running: `docker compose ps`
2. Verify services are healthy
3. Check `.env` has correct connection settings
4. Run tests with verbose output: `pytest -v -s`

---

### Getting Help

If you encounter issues not covered here:

1. **Check stack health**: `./infrastructure/scripts/stack_doctor.ps1` (Windows) or `docker compose ps`
2. **Review logs**: `docker compose logs -f`
3. **Search existing issues**: [GitHub Issues](https://github.com/jannekbuengener/Claire_de_Binare/issues)
4. **Ask for help**: Open a new issue with:
   - Your OS and Docker version
   - Error message and logs
   - Steps to reproduce

---

## Next Steps

### 1. Explore the Codebase

**Service Architecture**: Read `PROJECT_STATUS.md` for service overview
**Dependency Flow**: See service dependency matrix and data flow
**Testing**: Review `tests/README.md` (if exists) for testing guidelines

### 2. Review Documentation

- **Governance**: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`
- **Policies**: `governance/` directory
- **Service READMEs**: `services/*/README.md`
- **API Documentation**: Service-specific API docs

### 3. Development Best Practices

**Pre-commit Hooks**:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

**Test Coverage** (minimum 80%):
```bash
make test-coverage
```

**Code Style**:
- Python: Black formatter, flake8 linter (enforced in pre-commit)
- Commit messages: Conventional Commits format

### 4. Contributing

**Before making changes**:
1. Create a feature branch: `git checkout -b feature/your-feature`
2. Run tests: `make test`
3. Check pre-commit hooks: `pre-commit run --all-files`
4. Create PR following template

**Commit Message Format**:
```
type(scope): description

feat(signal): add RSI indicator support
fix(risk): correct exposure calculation
docs(readme): update setup instructions
test(allocation): add regime change tests
```

---

## Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| **Start stack** | `docker compose -f infrastructure/compose/dev.yml up -d` |
| **Stop stack** | `docker compose -f infrastructure/compose/dev.yml down` |
| **View logs** | `docker compose -f infrastructure/compose/dev.yml logs -f` |
| **Restart service** | `docker compose -f infrastructure/compose/dev.yml restart <service>` |
| **Run tests** | `pytest tests/ -v` |
| **Check coverage** | `make test-coverage` |
| **Service shell** | `docker compose -f infrastructure/compose/dev.yml exec <service> bash` |
| **View secret** | `cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD` |
| **Rebuild service** | `docker compose -f infrastructure/compose/dev.yml up -d --build <service>` |

### Important URLs

- **Grafana**: http://localhost:3000 (admin / see GRAFANA_PASSWORD)
- **Prometheus**: http://localhost:9090
- **WebSocket Health**: http://localhost:8000/health

### Important Files

- `.env` - Environment configuration
- `~/Documents/.secrets/.cdb/` - Secrets directory
- `infrastructure/compose/dev.yml` - Development stack definition
- `PROJECT_STATUS.md` - Service implementation status
- `Makefile` - Build and test targets

---

**Welcome aboard!** 🎉

If you have any questions or run into issues, don't hesitate to ask in the project's communication channels or open a GitHub issue.

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-15
**Maintained By**: Development Team

🤖 Generated with [Claude Code](https://claude.com/claude-code)
