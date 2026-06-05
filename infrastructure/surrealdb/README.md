# SurrealDB Governance Mirror

Experimentelle Mirror-/Context-Schicht neben Postgres. Postgres bleibt Source of Truth für Trading; produktive Agent-Writes bleiben gate-bound auf `main`.

## What this is
SurrealDB dient als experimentelle Mirror-Schicht neben Postgres, um Governance-, Shadow-Soak- und Ledger-Events zu testen ohne den Trading-Flow zu beeinflussen. Postgres bleibt Source of Truth; SurrealDB liest nur App-Metadaten (keine Secrets / Real Funds).

## Active docs (context / MCP)
*   `docs/surrealdb/` — context contracts, proof matrices, runbooks
*   `docs/runbooks/surrealdb_context_mcp_access.md` — MCP capability matrix
*   `infrastructure/surrealdb/setup.surql` — schema bootstrap

## Schema
Die folgenden Collections (Tables) sind als append-only Mirror definiert:
- `governance_events`: Shadow/Manual Events (event_type, evidence, integrity hash, created_at)  
- `audit_trail`: Service-agnostische Audit-Einträge mit payload JSON  
- `deployment_approvals_mirror`: Mirror der Delivery/YAML-Approvals (pr_id, commit, path)  
- `system_config`: Nicht-sensitive Config-Referenzen/Fingerprints (`value_ref`, `value_hash`, `integrity_*`)  
- `security_policy_refs`: Tatsächlicher Storage für `security_policies` im Repo (Policy-Versionen, Doku-Links, `integrity_*`)  
- `access_matrix`: Optionaler Matrix-Eintrag für Rechte (Prüfung/Reporting)

Alle Tabellen nutzen `PERMISSIONS FOR CREATE, FOR SELECT` und haben keine UPDATE/DELETE-Berechtigungen, wodurch Append-only gewährleistet ist.

## Setup
1. Start SurrealDB (namespace `governance`, database `governance_mirror`).  
2. Lade `infrastructure/surrealdb/setup.surql` via `surreal sql --file=...` oder über Startup-Script.  
3. Schreibzugriff beschränkt auf Append-Only-Agents (z. B. Ledger-Importer).

## What is consciously not mirrored
- Keine personenbezogenen Secrets (z. B. API-Keys) oder realen Kontostände.  
- Keine Produktionszugriffe auf Postgres (nur Postgres → SurrealDB Copy).  
- Keine Real-Time Order-Flows oder Trading-Entscheidungen.

## Rollback notes
- SurrealDB ist unabhängig: `surrealdb_enabled` bleibt `false` (Infra-Flag).  
- Zum Rollback genügt es, die SurrealDB-Instance zu stoppen und `governance_source` auf `postgres`/`git` zu belassen.  
- Schema kann jederzeit neu geladen werden (`surreal sql --file=setup.surql`).

## SSOT boundary
LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`. Managed/non-local runtime **NOT ACTIVATED**.
