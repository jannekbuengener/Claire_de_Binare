---
name: cdb-operator
description: Enforces Claire de Binare operator workflow: bootloader first, live GitHub truth, dry-run planning, strict GO gates, no merge without human approval.
compatibility: opencode
metadata:
  project: claire-de-binare
  workflow: operator
---

# CDB Operator Skill

## Purpose

Use this skill when working on Claire_de_Binare with OpenCode.

## Required workflow

1. Read `AGENTS.md` in the repo root.
2. Follow the pointer to `agents/AGENTS.md`.
3. Read `agents/OPEN_CODE_AGENTS.md` if present.
4. Read the complete repo read order before planning.
5. Pull GitHub issue and PR state live.
6. Treat `CURRENT_STATUS.md` as ledger, not live truth.
7. Produce only Lage, Befund, Plan, Dry-Run, Validierung, Restunsicherheiten.
8. Do not write, commit, push, comment, label, close, or merge without explicit human GO.

## Stop conditions

Stop immediately on missing bootloader, unclear scope, unexpected diff, red checks, pending checks before merge, scope growth, or any live-readiness/echtgeld implication.

