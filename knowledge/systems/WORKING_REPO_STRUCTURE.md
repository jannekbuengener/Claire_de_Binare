# Working Repo Structure Documentation

Purpose: technical layout for the consolidated Claire de Binare repository
Status: canonical

## Overview

This document describes the technical structure of the working repo after the
Docs-Hub consolidation. The repo now contains both executable assets and the
active supporting canon required to operate them.

## Core Layout

- `core/` shared domain logic and utilities
- `services/` runnable service modules
- `infrastructure/` compose, monitoring, database, and deployment scaffolding
- `tests/` verification suites
- `tools/` and `scripts/` automation and governance tooling
- `agents/`, `knowledge/`, `docs/` active local documentation surfaces

## Hard Rules

- no external docs repo is required for normal navigation
- keep long-form docs out of root unless they are deliberate entrypoints
- keep archive material under explicit archive paths
- update local docs when behavior, operations, or governance meaning changes

## Validation

- `tools/enforce-root-baseline.ps1` checks entrypoint drift
- local policy and schema guards validate critical governance contracts

## Legacy Note

Older versions of this file described the repo as execution-only and delegated
canon to an external docs repo. That model is retired.
