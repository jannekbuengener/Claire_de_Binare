# DOCKER_HARDENING_REPORT

Date: 2025-12-19
Scope: Dockerfiles and docker-compose files in Working Repo (Claire_de_Binare)
Goal: Security audit report only (no changes)

## Inventory

Dockerfiles:
- services/db_writer/Dockerfile
- services/market/Dockerfile
- services/signal/Dockerfile
- services/execution/Dockerfile
- services/risk/Dockerfile

Compose files:
- docker-compose.yml
- docker-compose.base.yml
- docker-compose.dev.yml

Note:
- docker-compose.yml and docker-compose.base.yml reference a root Dockerfile for cdb_ws, but no root Dockerfile exists in the repo. This prevents full audit of that image build.

## Positive observations
- No plaintext secrets found in Dockerfiles.
- Secrets are used for Redis/Postgres/Grafana in compose files.
- Many services use read_only, cap_drop, and no-new-privileges in docker-compose.base.yml.

## Findings

### MUST
- Non-root user missing in Dockerfiles:
  - services/db_writer/Dockerfile (no USER)
  - services/market/Dockerfile (no USER)

### SHOULD
- Base images are not pinned by digest (all use python:3.11-slim). Pin to immutable digests for supply-chain hardening.
- Healthcheck missing in Dockerfiles:
  - services/market/Dockerfile (no HEALTHCHECK)
  - services/execution/Dockerfile (no HEALTHCHECK)
- docker-compose.yml lacks security hardening for some services that are hardened in docker-compose.base.yml:
  - cdb_db_writer: missing security_opt no-new-privileges, cap_drop ALL, read_only true
  - cdb_paper_runner: missing security_opt no-new-privileges, cap_drop ALL, read_only true
- No resource limits (cpu/memory) are defined in docker-compose.yml or docker-compose.base.yml.
- Single shared network only (cdb_network). Consider segmenting internal services and data stores.
- docker-compose.dev.yml disables read_only for multiple services. Ensure dev overlay is never used in production.
- Missing root Dockerfile for cdb_ws prevents auditing its build; add the file or adjust compose build reference.

### NICE
- Align apt-get usage to --no-install-recommends in Dockerfiles that install system packages (services/signal, services/risk) for smaller surface area.

## Summary
Main security gaps are containers running as root (db_writer, market) and missing healthchecks (market, execution). The production compose file should mirror base hardening settings for db_writer and paper_runner. Resource limits and network segmentation are absent across compose files.
