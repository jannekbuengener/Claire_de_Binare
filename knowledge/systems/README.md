# System Documentation

**Purpose:** Documentation for implemented systems and features  
**Domain:** `knowledge/systems/`  
**Status:** active  

## Overview

Index für produktionsnahe Systemdokumentation im Working Repo. Dieses Verzeichnis ist **kein** Status-SSOT.

## Contents

| File | Topic |
|---|---|
| [`STACK_LIFECYCLE.md`](STACK_LIFECYCLE.md) | BLUE+RED stack lifecycle, startup/shutdown canon |
| [`PAPER_TRADING_ARCHITECTURE.md`](PAPER_TRADING_ARCHITECTURE.md) | Paper-trading runner and shadow path |
| [`TRADING_MODES.md`](TRADING_MODES.md) | Trading mode matrix (mock/shadow/paper) |
| [`WORKING_REPO_STRUCTURE.md`](WORKING_REPO_STRUCTURE.md) | Repo layout and navigation |
| [`K8S_OVERVIEW.md`](K8S_OVERVIEW.md) | Kubernetes scaffold overview (pending GO) |
| [`SDK_OVERVIEW.md`](SDK_OVERVIEW.md) | **Historical** — `cdb_agent_sdk/` removed from repo; see `.codex/cdb_skills/` |

## Related entrypoints

- Runtime compose: `infrastructure/compose/README.md`
- Services index: `services/README.md`
- Tools / PowerShell v1: `tools/README.md`
- Agent registry: `agents/AGENTS.md`

## SSOT boundary

| Topic | Canonical source |
|---|---|
| Board stage / operating focus | `docs/runbooks/CONTROL_REGISTER.md` |
| Repo / engineering ledger | `CURRENT_STATUS.md` |
| Live-Readiness / Echtgeld | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` |

Stage `trade-capable` autorisiert kein Live-Trading. LR bleibt **NO-GO**.
