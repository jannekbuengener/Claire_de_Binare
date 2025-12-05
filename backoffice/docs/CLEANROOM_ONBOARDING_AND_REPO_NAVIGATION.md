# CLEANROOM ONBOARDING AND REPO NAVIGATION
# Claire de Binare – Repository Guide

**Version**: 1.0
**Last Updated**: 2025-01-18
**Status**: Active
**Repository**: `Claire_de_Binare_Cleanroom`

---

## Welcome to Claire de Binare

This document provides a comprehensive orientation for new contributors to the Claire de Binare project. The repository represents the **canonical baseline** (established 2025-01-17 via ADR-039) for all code and documentation.

---

## Quick Start

### Essential Reading (in order)

1. **This document** – Repository structure and navigation
2. `backoffice/docs/KODEX – Claire de Binare.md` – Project principles and architecture philosophy
3. `backoffice/docs/architecture/N1_ARCHITEKTUR.md` – Current phase architecture (Paper-Test)
4. `backoffice/docs/DECISION_LOG.md` – Architectural Decision Records (ADR-001 through ADR-039+)
5. `backoffice/docs/provenance/EXECUTIVE_SUMMARY.md` – Project history and canonicalization status

### First Actions

1. Read the KODEX to understand project philosophy
2. Review N1_ARCHITEKTUR to understand the current system scope
3. Check PROJECT_STATUS.md for current work items
4. Set up your development environment (see "Development Setup" below)

---

## Repository Structure

### Top-Level Overview

```
Claire_de_Binare_Cleanroom/
├── backoffice/              # Active codebase and canonical documentation
│   ├── docs/                # Single Source of Truth for all documentation
│   ├── services/            # Service implementations (signal_engine, risk_manager, execution_service)
│   ├── templates/           # Reusable templates (.env, infrastructure docs)
│   └── PROJECT_STATUS.md    # Current project phase and status
│
├── scripts/                 # Utility scripts (migration templates, tooling)
├── tests/                   # Test code (unit/ and integration/)
├── archive/                 # Historical artifacts (DO NOT EDIT - read-only reference)
├── CLAUDE.md                # AI assistant instructions and workflows
└── README.md                # Project overview

```

---

## Documentation Map (`backoffice/docs/`)

All canonical documentation lives here. This is the **Single Source of Truth**.

### Core Documents

| Document | Purpose | When to Read |
|----------|---------|--------------|
| **KODEX – Claire de Binare.md** | Project principles, architecture philosophy | First time, before major decisions |
| **DECISION_LOG.md** | Architectural Decision Records (ADRs) | When making architectural choices |
| **SYSTEM_REFERENCE.md** | Consolidated system reference | Understanding overall architecture |
| **Single Source of Truth.md** | Naming conventions, authority structure | When uncertain about conventions |
| **PROJECT_STATUS.md** | Current phase, work items, roadmap | Weekly, before planning |

### Documentation Subdirectories

#### `architecture/`
System design and architecture documents
- **N1_ARCHITEKTUR.md** – Paper-Test phase architecture (current)
- **SYSTEM_FLUSSDIAGRAMM.md** – System flow diagrams
- **STRUCTURE_CLEANUP_PLAN.md** – Planned repository cleanups

#### `services/`
Service-specific documentation (12+ services)
- Individual service docs: `cdb_advisor.md`, `cdb_execution.md`, `cdb_signal.md`, etc.
- **SERVICE_DATA_FLOWS.md** – Cross-service event flows
- **risk/** – Risk management logic and documentation

#### `schema/`
Data models and canonical schemas
- **canonical_schema.yaml** – Master data model
- **canonical_model_overview.md** – Schema explanations
- **audit_schema.yaml** – Audit validation rules

#### `provenance/`
Project history, migration records, baselines
- **EXECUTIVE_SUMMARY.md** – Canonicalization status
- **CLEANROOM_BASELINE_SUMMARY.md** – Nullpunkt definition summary
- **CANONICAL_SOURCES.yaml** – Provenance declarations
- **NULLPUNKT_DEFINITION_REPORT.md** – Baseline establishment report

#### `runbooks/`
Operational procedures and checklists
- **MIGRATION_READY.md** – Historical migration record (completed 2025-11-16)
- Pre-migration checklists (historical templates)

#### `security/`
Security hardening and infrastructure conflicts
- **HARDENING.md** – Security requirements
- **infra_conflicts.md** – Known infrastructure issues

#### `infra/`
Infrastructure and repository metadata
- **repo_map.md** – Repository file index
- **env_index.md** – Environment variable documentation
- **file_index.md** – File purpose index
- **infra_knowledge.md** – Infrastructure knowledge base

#### `audit/`
Audit documentation and validation
- **AUDIT_CLEANROOM.md** – Cleanroom audit findings
- **AUDIT_PLAN.md** – Audit procedures

#### `meetings/`
Meeting notes and session summaries
- **MEETINGS_SUMMARY.md** – Consolidated meeting notes
- **MEETINGS_INDEX.md** – Meeting index

#### `tests/`
Test documentation (NOT test code)
- Test strategies, test plans, coverage documentation
- Actual test code lives in `/tests/` at repo root

---

## Naming Conventions

### Project Name

**Official Name**: **Claire de Binare**
- Use "Binare" (NOT "Binaire")
- Historical documents may use "Binaire" – this is deprecated

**Technical IDs**: `claire_de_binare`
- Database names, Docker volumes, container prefixes use underscores

### File Naming

- Markdown: `UPPERCASE_WITH_UNDERSCORES.md` for major docs, `lowercase_with_underscores.md` for service docs
- YAML: `snake_case.yaml`
- Python: `snake_case.py`
- Directories: `snake_case/`

---

## Current Phase: N1 – Paper-Test

**Status**: Active development phase
**Focus**: Simulated trading environment (no live broker connection)

### N1 Scope

The system currently implements:
- Market Data Interface (MDI) – simulated price feeds
- Signal Engine – strategy signal generation
- Risk Manager – 6-layer risk validation
- Execution Service – simulated order execution
- Portfolio Tracker – position and PnL tracking
- Logging & Monitoring – observability infrastructure

**NOT in N1**: Live broker API, real capital deployment

See `backoffice/docs/architecture/N1_ARCHITEKTUR.md` for details.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- PostgreSQL client (optional, for direct DB access)

### Environment Configuration

1. Copy template:
   ```bash
   cp backoffice/templates/.env.template .env
   ```

2. Edit `.env` with your configuration (see `backoffice/docs/infra/env_index.md` for variable documentation)

3. Never commit `.env` (already in `.gitignore`)

### Running Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Stop services
docker-compose down
```

---

## Code vs. Documentation Separation

### Where Code Lives
- `/backoffice/services/` – Service implementations
- `/tests/` – Test code (unit and integration)
- `/scripts/` – Utility scripts

### Where Documentation Lives
- `/backoffice/docs/` – ALL documentation
- `/backoffice/docs/tests/` – Test strategies and plans (NOT code)
- `/backoffice/templates/` – Reusable templates

---

## Archive Structure

**Location**: `/archive/`
**Status**: **Historical reference only – DO NOT EDIT**

### What's in Archive

- `archive/backoffice_original/` – Pre-migration backup
- `archive/docs_original/` – Old documentation versions
- `archive/sandbox_backups/` – Historical sandbox environment
- `archive/meeting_archive/` – Historical session memos
- `archive/security_audits/` – Historical security reports

**Policy**: Archive is read-only. For forensics, audits, and historical reconstruction only.

---

## How to Contribute

### Making Changes

1. **Check the DECISION_LOG** – See if an ADR already covers your area
2. **Read relevant service docs** – Understand current implementation
3. **Create a branch** – Use descriptive names: `feat/risk-correlation-limits`, `fix/execution-timeout`
4. **Write tests** – Unit tests required, integration tests recommended
5. **Update documentation** – Change docs in `backoffice/docs/` to match code changes
6. **Create ADR if needed** – For architectural decisions, add to DECISION_LOG.md

### Commit Message Format

Follow conventional commits:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

Examples:
- `feat(risk): add correlation limit checks`
- `fix(execution): handle timeout edge case`
- `docs(services): update cdb_risk architecture`
- `chore: remove __pycache__ directories`

### Documentation Updates

When you change code, you MUST update:
1. Service documentation in `backoffice/docs/services/`
2. If schema changes: `backoffice/docs/schema/canonical_schema.yaml`
3. If architectural: Add ADR to `DECISION_LOG.md`

---

## Common Tasks

### Finding a Service

All services documented in: `backoffice/docs/services/`

Example: To understand the risk manager
1. Read `backoffice/docs/services/risk/cdb_risk.md`
2. Read `backoffice/docs/services/risk/RISK_LOGIC.md`
3. Review code in `backoffice/services/risk_manager/`

### Understanding Event Flows

See: `backoffice/docs/services/SERVICE_DATA_FLOWS.md`

### Checking Environment Variables

See: `backoffice/docs/infra/env_index.md`

### Understanding the Database Schema

See: `backoffice/docs/schema/canonical_schema.yaml`

---

## Key Principles (from KODEX)

1. **Event-Driven Architecture** – Services communicate via Redis pub/sub
2. **Risk-First Design** – All orders pass through 6-layer risk validation
3. **Single Source of Truth** – Documentation in `backoffice/docs/` is authoritative
4. **Immutable History** – Archive is preserved, never modified
5. **Paper-Test Phase** – N1 uses simulated execution (no live capital)

---

## Getting Help

### Documentation Issues

If documentation is unclear or contradictory:
1. Check `backoffice/docs/provenance/EXECUTIVE_SUMMARY.md` for context
2. Check `DECISION_LOG.md` for relevant ADRs
3. Open an issue describing the ambiguity

### Technical Questions

1. Check service-specific docs in `backoffice/docs/services/`
2. Review `N1_ARCHITEKTUR.md` for system design
3. Check `backoffice/docs/infra/infra_knowledge.md` for infrastructure details

---

## Migration History

**Note**: The Cleanroom repository represents the **canonical baseline** as of 2025-11-16.

All migration from backup repositories is **complete**. Documents referencing "sandbox" or "migration to cleanroom" describe historical processes, not future actions.

See:
- `backoffice/docs/runbooks/MIGRATION_READY.md` (historical record)
- `backoffice/docs/provenance/CLEANROOM_BASELINE_SUMMARY.md` (nullpunkt summary)
- ADR-039 in `DECISION_LOG.md` (establishes Cleanroom as canonical)

---

## Roadmap Phases

### Phase 0: Migration (COMPLETED 2025-11-16)
Established Cleanroom as canonical repository

### Phase N1: Paper-Test (CURRENT)
Simulated trading environment with risk validation

### Phase N2: Shared Modules (PLANNED)
Create `backoffice/common/` for shared models and utilities
See: `backoffice/docs/architecture/STRUCTURE_CLEANUP_PLAN.md`

### Phase N3: Live Integration (FUTURE)
Broker API integration, real capital deployment

---

## Reference Quick Links

| Topic | Document |
|-------|----------|
| **Architecture Philosophy** | `backoffice/docs/KODEX – Claire de Binare.md` |
| **Current System Design** | `backoffice/docs/architecture/N1_ARCHITEKTUR.md` |
| **Decision History** | `backoffice/docs/DECISION_LOG.md` |
| **Project Status** | `backoffice/PROJECT_STATUS.md` |
| **Service Documentation** | `backoffice/docs/services/` |
| **Data Schema** | `backoffice/docs/schema/canonical_schema.yaml` |
| **Environment Config** | `backoffice/docs/infra/env_index.md` |
| **Repository Structure** | `backoffice/docs/infra/repo_map.md` |

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2025-01-18 | 1.0 | Initial creation as part of Phase 1 Naming Normalization |

---

**Last Updated**: 2025-01-18
**Maintained by**: Claire de Binare Project Team
**Status**: Active – Single Source of Truth for onboarding
