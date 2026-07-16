# Claire de Binare repository Structure Documentation

Purpose: technical layout for the consolidated Claire de Binare repository
Status: canonical

## Overview

This document describes the technical structure of the Claire de Binare repository after the
historical documentation material consolidation. The repo now contains both executable assets and the
active supporting canon required to operate them.

## Core Layout

- `core/` shared domain logic and utilities
- `services/` runnable service modules
- `infrastructure/` active compose, monitoring, database, TLS, and deployment surfaces
- `config/` repository, ARVP campaign, and readiness configuration
- `tests/` verification suites
- `tools/` and `scripts/` automation and governance tooling
- `agents/`, `knowledge/`, `docs/` active local documentation surfaces
- `artifacts/` generated local/CI outputs; reviewed evidence lives under `docs/evidence/`

## Hard Rules

- no external docs repo is required for normal navigation
- keep long-form docs out of root unless they are deliberate entrypoints
- keep archive material under explicit archive paths
- do not recreate retired root paths such as `reports/`, `manifests/`, `k8s/`, or
  `mcp_navpack_claire_de_binare_repository/`
- keep executable infrastructure in `infrastructure/`; Knowledge records decisions
  but does not host deployable manifests
- update local docs when behavior, operations, or governance meaning changes

## Validation

- `python -m tools.validate_root_layout` checks the tracked root allowlist
- `tools/enforce-root-baseline.ps1` wraps root and entrypoint drift checks
- local policy and schema guards validate critical governance contracts

See `docs/meta/ROOT_INFORMATION_ARCHITECTURE.md` for the complete decision matrix.

## Legacy Note

Older versions of this file described the repo as execution-only and delegated
canon to an external docs repo. That model is retired.
