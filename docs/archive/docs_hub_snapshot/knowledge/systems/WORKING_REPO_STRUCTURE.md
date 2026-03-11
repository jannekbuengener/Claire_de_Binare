# Working Repo Structure Documentation

**Purpose:** Technical layout and structure documentation for Claire de Binare Working Repository  
**Domain:** knowledge/systems  
**Status:** canonical  
**Migrated from:** Working Repo WORKING_REPO_INDEX.md

## Overview

This documents the technical structure of the Claire de Binare Working Repository. The Working Repo contains the active code for various services, infrastructure definitions, tests, and development tools. The focus is on executability and the technical components of the system.

**Canon Reference:** For governance, knowledge, agent definitions, and comprehensive documentation, refer to the Docs Hub (this repository).

## STRUCTURE (Technical, non-governance)

**Purpose:** This section describes the *technical* layout of the Working Repo only.  
**Canonical governance:** Lives exclusively in the Docs Hub (not mirrored in Working Repo).

### Repo Map (Mental Model)
- `core/` → Shared Python package for cross-service domain + utilities (single source inside Working Repo)
- `services/<name>/` → Independently runnable service modules; no local `core/` allowed
- `infrastructure/` → Deploy/runtime assets (compose/k8s/ops), not business logic
- `tools/` → Developer tooling and maintenance scripts
- `scripts/` → Automation and pipeline scripts

### Hard Rules
- ❌ **No `knowledge/governance/` content** in Working Repo
- ❌ **No `services/*/core`** directories  
- ❌ **No agent definition files** in Working Repo root
- ❌ **No knowledge/documentation files** in Working Repo root
- ✅ **Execution/infrastructure only** in Working Repo

### Root Baseline Enforcement
- **Script:** `tools/enforce-root-baseline.ps1`
- **Purpose:** Prevent governance drift, maintain execution-only principle
- **Integration:** CI/CD pipeline validation

## Technical Directories

### `/services/`
- **execution/** → Order execution service
- **risk/** → Risk management service  
- **signal/** → Signal processing service
- **market/** → Market data service
- **psm/** → Position sizing & money management
- **db_writer/** → Database writing service

### `/infrastructure/`
- **compose/** → Docker compose configurations
- **k8s/** → Kubernetes manifests
- **monitoring/** → Observability configurations
- **scripts/** → Infrastructure automation

### `/tools/`
- **Developer tooling** and maintenance scripts
- **Validation scripts** (MCP config, etc.)
- **Sync and automation** utilities

### `/tests/`
- **Unit tests** for services
- **Integration tests** for system components
- **E2E tests** for full workflows

## Configuration Files (Root Level)

### Build & Infrastructure
- `Makefile` → Build and task automation
- `docker-compose*.yml` → Container orchestration
- `requirements*.txt` → Python dependencies
- `pytest.ini` → Testing configuration

### CI/CD & Git
- `.gitlab-ci.yml` → CI/CD pipeline definition
- `.gitignore`, `.gitleaksignore` → Git configuration
- `.github/` → GitHub Actions workflows

### Tool Integration (Operational)
- `.mcp.json` → MCP server registry for Claude Desktop
- `mcp-config*.toml` → MCP configuration (local/CI)

## Governance Separation

**Working Repo contains:** Code, infrastructure, operational configuration  
**Docs Hub contains:** Governance, knowledge, agent definitions, documentation

This strict separation ensures:
- ✅ **Clean execution environment**
- ✅ **No governance drift**  
- ✅ **Single source of truth** for knowledge
- ✅ **Deterministic agent behavior**

---

**Canonical Location:** `Claire_de_Binare_Docs/knowledge/systems/WORKING_REPO_STRUCTURE.md`  
**Working Repo Reference:** Root baseline enforced by `tools/enforce-root-baseline.ps1`
