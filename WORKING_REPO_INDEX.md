# WORKING_REPO_INDEX.md

## Overview
This is the index of the Claire de Binare Working Repository. It contains the active code for the various services, infrastructure definitions, tests, and development tools. The focus is on executability and the technical components of the system.

For canonical governance, knowledge, agent definitions, and comprehensive documentation, refer to the Docs Hub.

## STRUCTURE (Technical, non-governance)

**Purpose:** This section describes the *technical* layout of the Working Repo only.
**Canonical governance:** lives exclusively in the Docs Hub (not mirrored here).

### Repo Map (mental model)
- `core/` = shared Python package for cross-service domain + utilities (single source inside this repo)
- `services/<name>/` = independently runnable service modules; no local `core/` allowed
- `infrastructure/` = deploy/runtime assets (compose/k8s/ops), not business logic
- `tools/` = developer tooling and maintenance scripts
- `AGENTS.md` = read-only execution charter for agents (do not treat as governance)

### Hard rules
- No `governance/` content in this repo.
- No `services/*/core` directories.
- If a service is empty, mark it explicitly as `Skeleton/Pending` in the index.
---

## Folders & Files

### .cdb_local/
- Type: Folder
- Purpose: Local configuration and working files, ignored by Git.

### .github/
- Type: Folder
- Purpose: GitHub-specific configurations, CI/CD workflows, and issue templates.

### .pytest_cache/
- Type: Folder
- Purpose: Cache directory for Pytest executions.

### .secrets/
- Type: Folder
- Purpose: Contains secrets files used by Docker Compose and local scripts.

### .vscode/
- Type: Folder
- Purpose: Visual Studio Code-specific settings and recommended extensions.

### core/
- Type: Folder
- Purpose: Shared core logic, domain models, and utilities for all services.

### core/config/
- Type: Folder
- Purpose: Configuration handling for core components.

### core/domain/
- Type: Folder
- Purpose: Definitions for domain models, events, and secrets management.

### core/domain/__init__.py
- Type: File
- Purpose: Initializes the 'core.domain' Python package.

### core/domain/event.py
- Type: File
- Purpose: Defines the base class for events in the event-sourcing system.

### core/domain/models.py
- Type: File
- Purpose: Defines canonical domain models such as Signal, Order, and OrderResult.

### core/domain/secrets.py
- Type: File
- Purpose: Helper function for reading secrets from Docker secrets or environment variables.

### core/utils/
- Type: Folder
- Purpose: General utilities like clock abstraction and UUID generation.

### core/utils/__init__.py
- Type: File
- Purpose: Initializes the 'core.utils' Python package.

### core/utils/clock.py
- Type: File
- Purpose: Implements a clock abstraction for deterministic time measurement.

### core/utils/seed.py
- Type: File
- Purpose: Manages the seed for deterministic random number generation.

### core/utils/uuid_gen.py
- Type: File
- Purpose: Generates deterministic UUIDs for event-sourcing replays.

### AGENTS.md
- Type: File
- Purpose: Bootstrap charter for agents (read-only mirror, non-authoritative).

### STRUCTURE.md
- Type: File
- Purpose: Defines the target structure of this repository, optimized for development and operations.

### infrastructure/
- Type: Folder
- Purpose: Infrastructure definitions, deployment scripts, and monitoring facilities.

### infrastructure/database/
- Type: Folder
- Purpose: Definitions for the database schema and migration scripts.

### infrastructure/database/migrations/
- Type: Folder
- Purpose: Database migration scripts.

### infrastructure/monitoring/
- Type: Folder
- Purpose: Configuration files for Prometheus and Grafana.

### infrastructure/monitoring/grafana/
- Type: Folder
- Purpose: Grafana-specific configurations, including dashboards and provisioning.

### infrastructure/monitoring/grafana/dashboards/
- Type: Folder
- Purpose: Grafana dashboard JSON files.

### infrastructure/monitoring/grafana/provisioning/
- Type: Folder
- Purpose: Grafana provisioning configurations for data sources and dashboards.

### infrastructure/scripts/
- Type: Folder
- Purpose: Collection of scripts for operational infrastructure tasks.

### infrastructure/scripts/archive/
- Type: Folder
- Purpose: Archive for older infrastructure scripts.

### infrastructure/scripts/backup_postgres.ps1
- Type: File
- Purpose: PowerShell script for creating and managing PostgreSQL backups.

### infrastructure/scripts/daily_check.py
- Type: File
- Purpose: Script for daily health checks and reports during operation.

### infrastructure/scripts/query_analytics.py
- Type: File
- Purpose: Script for querying analytics data.

### infrastructure/scripts/run-tests.ps1
- Type: File
- Purpose: PowerShell script to run tests.

### infrastructure/scripts/security_audit.sh
- Type: File
- Purpose: Shell script for security auditing.

### infrastructure/scripts/setup_backup_task.ps1
- Type: File
- Purpose: PowerShell script to set up backup tasks.

### infrastructure/scripts/systemcheck.py
- Type: File
- Purpose: Script for pre-flight checks to verify system status.

### infrastructure/scripts/archive/migration_2025_11_16/cleanroom_migration_script.ps1
- Type: File
- Purpose: Cleanroom migration script.

### infrastructure/scripts/archive/migration_2025_11_16/pre_migration_tasks.ps1
- Type: File
- Purpose: Pre-migration tasks script.

### infrastructure/scripts/archive/migration_2025_11_16/pre_migration_validation.ps1
- Type: File
- Purpose: Pre-migration validation script.

### logs/
- Type: Folder
- Purpose: Storage of runtime logs and daily reports.

### logs/daily_reports/
- Type: Folder
- Purpose: Stores daily Markdown reports from the Daily Check Script.

### scripts/
- Type: Folder
- Purpose: Top-level scripts for validations and general repository tasks.

### scripts/validate_write_zones.sh
- Type: File
- Purpose: Shell script for validating write permissions in specific zones.

### services/
- Type: Folder
- Purpose: Contains the microservices of the application.

### services/db_writer/
- Type: Folder
- Purpose: Service for writing data to the database.

### services/db_writer/db_writer.py
- Type: File
- Purpose: Main logic of the database writer service.

### services/db_writer/Dockerfile
- Type: File
- Purpose: Dockerfile for the DB Writer service.

### services/execution/
- Type: Folder
- Purpose: Service for executing trade orders.

### services/execution/config.py
- Type: File
- Purpose: Configuration for the execution service.

### services/execution/database.py
- Type: File
- Purpose: Database interaction for the execution service.

### services/execution/Dockerfile
- Type: File
- Purpose: Dockerfile for the execution service.

### services/execution/EXECUTION_SERVICE_STATUS.md
- Type: File
- Purpose: Status documentation of the execution service.

### services/execution/mock_executor.py
- Type: File
- Purpose: Mock implementation of the executor.

### services/execution/models.py
- Type: File
- Purpose: Data models for the execution service.

### services/execution/requirements.txt
- Type: File
- Purpose: Python dependencies for the execution service.

### services/execution/service.py
- Type: File
- Purpose: Main logic of the order execution service.

### services/execution/simulator.py
- Type: File
- Purpose: Trade simulator.

### services/market/
- Type: Folder
- Purpose: Service for market data acquisition. (Status: Skeleton/Pending)

### services/market/Dockerfile
- Type: File
- Purpose: Dockerfile for the market service.

### services/market/requirements.txt
- Type: File
- Purpose: Python dependencies for the market service.

### services/psm/
- Type: Folder
- Purpose: Portfolio and Strategy Management service.

### services/risk/
- Type: Folder
- Purpose: Risk management service.

### services/risk/config.py
- Type: File
- Purpose: Configuration for the risk service.

### services/risk/Dockerfile
- Type: File
- Purpose: Dockerfile for the risk service.

### services/risk/models.py
- Type: File
- Purpose: Data models for the risk service.

### services/risk/README.md
- Type: File
- Purpose: README for the risk service.

### services/risk/requirements.txt
- Type: File
- Purpose: Python dependencies for the risk service.

### services/risk/service.py
- Type: File
- Purpose: Main logic of the risk management service.

### services/signal/
- Type: Folder
- Purpose: Signal generation service.

### services/signal/config.py
- Type: File
- Purpose: Configuration for the signal service.

### services/signal/Dockerfile
- Type: File
- Purpose: Dockerfile for the signal service.

### services/signal/models.py
- Type: File
- Purpose: Data models for the signal service.

### services/signal/models.py.backup
- Type: File
- Purpose: Backup of data models for the signal service.

### services/signal/README.md
- Type: File
- Purpose: README for the signal service.

### services/signal/requirements.txt
- Type: File
- Purpose: Python dependencies for the signal service.

### services/signal/service.py
- Type: File
- Purpose: Main logic of the signal service.

### tests/
- Type: Folder
- Purpose: Contains all test suites of the application.

### tests/integration/
- Type: Folder
- Purpose: Integration tests for checking component interaction.

### tests/replay/
- Type: Folder
- Purpose: Replay tests for event sourcing and determinism verification.

### tests/replay/test_deterministic_replay.py
- Type: File
- Purpose: Tests the deterministic repeatability of events.

### tests/unit/
- Type: Folder
- Purpose: Unit tests for individual components and services.

### tests/unit/test_smoke_repo.py.skip
- Type: File
- Purpose: A skipped smoke test for the repository.

### tests/README.md
- Type: File
- Purpose: README for the tests.

### tools/
- Type: Folder
- Purpose: Various scripts and utilities for development and operations.

### tools/cdb-secrets-sync.ps1
- Type: File
- Purpose: PowerShell script for synchronizing secrets.

### tools/cdb-service-logs.ps1
- Type: File
- Purpose: PowerShell script for displaying service logs.

### tools/cdb-stack-doctor.ps1
- Type: File
- Purpose: PowerShell script for Docker stack system diagnostics.

### tools/link_check.py
- Type: File
- Purpose: Python script for checking links in documentation files.

### tools/provenance_hash.py
- Type: File
- Purpose: Python script for generating provenance hashes.

### tools/paper_trading/
- Type: Folder
- Purpose: Tools and scripts for simulated trading.

### tools/paper_trading/email_alerter.py
- Type: File
- Purpose: Python script for email notifications in paper trading.

### tools/paper_trading/service.py
- Type: File
- Purpose: Main logic for the paper trading service.

### tools/research/
- Type: Folder
- Purpose: Scripts and documents for research and analysis tasks.

### tools/research/CDB_TOOL_INDEX.md
- Type: File
- Purpose: Index of developer tools.

### tools/research/portfolio_manager.py
- Type: File
- Purpose: Python script for portfolio management tasks.

### .dockerignore
- Type: File
- Purpose: Lists files and folders to be ignored by Docker builds.

### .env.example
- Type: File
- Purpose: Example template for the `.env` file.

### .gitignore
- Type: File
- Purpose: Lists files and folders to be ignored by Git.

### .secretsignore
- Type: File
- Purpose: Defines patterns for files to be ignored by secret scanning tools.

### docker-compose.yml
- Type: File
- Purpose: Defines and configures the multi-container Docker application.

### Makefile
- Type: File
- Purpose: Automation of build, test, and development tasks.

### pytest.ini
- Type: File
- Purpose: Configuration settings for the Pytest framework.

### README.md
- Type: File
- Purpose: General introduction and overview of the project.
