<!--
Canonical Skill Source: docs/skills/cdb-external-docs/SKILL.md
Surface: opencode
Sync Status: mirrored-from-canon
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-external-docs
description: CDB External Documentation Lookup Skill. Use when an agent needs to determine which external documentation is relevant for a given task, resolve contradictions between external docs and CDB canon, or handle scenarios where internet/browsing is unavailable. References the canonical external docs index at docs/external-docs/index.md.
---

# CDB External Documentation Lookup

## Purpose

This skill tells agents:
- when external documentation must be consulted
- which external docs are relevant for which problem
- what to do when internet/browsing is not available
- how to handle contradictions between external docs and CDB canon

## Central Index

Canonical external docs list: `docs/external-docs/index.md`

This file contains all known external documentation references grouped by category, with priority levels and CDB usage notes.

## When to use

Load this skill when the task involves any of these external doc dependencies:

| Category | Example triggers |
|----------|-----------------|
| Exchange / Market Data | MEXC WebSocket, Protobuf, REST API, order schemas |
| Docker / Runtime | Docker Compose, Dockerfiles, BLUE/RED stack |
| GitHub / CI | GitHub Actions, rulesets, required checks, gh CLI |
| Security Tools | Gitleaks, Trivy, Bandit, pip-audit |
| Python / Testing | pytest, Ruff, mypy, Black, pre-commit |
| Agent Surfaces | OpenCode, Cursor, Codex, Claude Code, Gemini |
| MCP / Context | Model Context Protocol, SurrealDB |
| SurrealDB Agent Skills / Rules | Offizielle SurrealDB Skills, Rules, Memory SDKs |
| Infrastructure | Redis, PostgreSQL, Prometheus, Grafana |

## How to use

1. Identify the problem domain (e.g., "MEXC WebSocket reconnect").
2. Load this skill.
3. Look up `docs/external-docs/index.md` for the relevant category.
4. Before writing code, fetch the official docs for the tool.
5. If multiple docs apply, read all that are `required` priority first, then `secondary`.

## When internet/browsing is unavailable

If the agent has no internet access or no browsing tools:

- Use local code patterns, docstrings, and type stubs as fallback.
- Check if the repo contains vendored/generated protobuf stubs or similar.
- For agent surfaces (OpenCode/Cursor/Codex/Claude/Gemini): use the info in `.surface/README.md` and `AGENTS.md`.
- Report which external docs could not be verified and flag the gap.
- Do not invent API signatures or behavior from memory when external docs are required but unreachable. Issue a blocker: `EXTERNAL_DOCS_UNVERIFIED`.

## Contradiction handling

When official external docs seem to contradict CDB canon (code, docs, runbooks):

| Priority | Rule |
|----------|------|
| 1 | External official docs win for tool/API behavior |
| 2 | CDB canon (custom wrappers, adapters, policies) defines CDB-specific behavior |
| 3 | Report the contradiction in an evidence snippet |
| 4 | If the mismatch is governance-relevant, create a decision event |
| 5 | Do not silently override external behavior with assumptions |

## Lookup Hooks

This skill is referenced from:
- `cdb-session-start` — for session setup requiring external tool context
- `cdb-docs-ops` — when writing docs that reference external tools
- `cdb-exchange-adapters` — for exchange API and protocol references
- `cdb-ci-cd-guard` — for CI/CD tooling documentation
- `cdb-test-first` — for test framework documentation
- `ctb-docker-stack` — for Docker and compose documentation
- `onboarding` — for new-agent orientation on external references
- `skillforge` — when creating skills that depend on external tools
