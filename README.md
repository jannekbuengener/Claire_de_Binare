# Claire de Binare

Deterministisches, governance-first Trading-System im Working Repo Canon.
Der aktive Pfad bleibt Shadow/Paper-first; Live-Kapital ist nicht freigegeben.

## Current Operating Reality (current main)

- **Control-Board Stage:** `trade-capable` (Board-Kontext, nicht LR-Freigabe)
- **Live-Readiness Verdict:** **NO-GO** (SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)
- **Status-Trennung bleibt hart:**

| Quelle | Zweck |
|---|---|
| `docs/runbooks/CONTROL_REGISTER.md` | Board-Stage und operativer Fokus |
| `CURRENT_STATUS.md` | Repo-/Engineering-Ledger |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Echtgeld Go/No-Go |

Stage und LR sind orthogonale Systeme: `trade-capable` autorisiert kein Live-Trading.

## Current-main Landing Snapshot

Auf `origin/main` sind die juengsten Kern-Cluster gelandet, u. a.:

- Strategy-v1-Cluster: `primary_breakout_v1` Signal-Footprint, statische Adapter-Grenze, deterministischer Validation-Pfad, Paper/Shadow-Bridge.
- Repo-/Workflow-/Docs-/Hygiene-Cluster: Root-Minimierung, Workflow-Reconcile, Control-Register-/Status-Nachzuege.

Operativ offen im Control-Kontext: `#1445` sowie die geparkten `#197`, `#205`, `#211`.

## Canonical Entrypoints

1. `docs/runbooks/CONTROL_REGISTER.md`
2. GitHub Issue `#1445` (inkl. neuestem Wochenkommentar)
3. `CURRENT_STATUS.md`
4. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
5. `docs/meta/WORKING_REPO_CANON.md`
6. `agents/AGENTS.md`

## Active Main Paths

- `core/` - gemeinsame Domain-/Contract-Logik
- `services/` - laufende Runtime-Services (Signal/Risk/Execution/etc.)
- `infrastructure/compose/` - Compose-Canon (`compose.blue.yml` + `compose.red.yml`)
- `docs/runbooks/` - operative Runbooks inkl. Control Register
- `docs/live-readiness/` - LR-Audit- und Gate-Artefakte
- `knowledge/` - aktive Knowledge-/Governance-Flaeche
- `tools/` - PowerShell Front Doors und Ops-Helfer
- `tests/` - Unit/Integration/E2E/Replay/Chaos

## Runtime / Ops Entry

Windows/PowerShell v1 Front Door:

```powershell
.\tools\cdb.ps1 secrets init
.\tools\cdb.ps1 runtime up
.\tools\cdb.ps1 stack verify
.\tools\cdb.ps1 runtime smoke
```

Compose Runtime Canon:

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d
docker compose -f infrastructure/compose/compose.red.yml up -d
```

Docker CI Lab Baseline:

```bash
docker compose -f infrastructure/compose/base.yml -f infrastructure/compose/test.yml up --abort-on-container-exit
```

## Navigation

- `mcp_navpack_working_repo/ENTRYPOINTS.yaml`
- `mcp_navpack_working_repo/CHEATSHEET.md`
- `docs/meta/WORKING_REPO_CANON.md`

## Boundary

Archiv-/Snapshot-Flaechen (`docs/archive/**`, `knowledge/archive/**`) sind historischer Rueckgriff und kein aktiver Pflegepfad.
