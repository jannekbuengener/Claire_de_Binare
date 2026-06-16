# Claire de Binare

Claire de Binare (CDB) ist ein deterministisches, governance-first Trading-System im Working Repo Canon.
Diese Root-README ist die GitHub-Haupt-Landingpage. Der aktive Pfad bleibt Shadow/Paper-first; Live-Kapital ist nicht freigegeben.

## Start Here

- Neue Entwickler: [`DEVELOPER_ONBOARDING.md`](DEVELOPER_ONBOARDING.md)
- Kurzer Docs-Index: [`docs/index.md`](docs/index.md)
- Agenten-Bootloader: [`AGENTS.md`](AGENTS.md) -> [`agents/AGENTS.md`](agents/AGENTS.md)
- Repo Brain / Context Intelligence: [`docs/surrealdb/README.md`](docs/surrealdb/README.md)
- GitHub-Control-Plane-Unterdokument: [`.github/CONTROL_PLANE.md`](.github/CONTROL_PLANE.md)
- Repo-/Engineering-Ledger: [`CURRENT_STATUS.md`](CURRENT_STATUS.md)

## Safety / LR Status

- **Control-Board Stage:** `trade-capable` (Board-Kontext, nicht LR-Freigabe)
- **Live-Readiness Verdict:** **NO-GO** (SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`)
- **LR-050 (P5 / Live-Capital):** **NO-GO** — fail-closed; Planning-SSOTs geliefert, Runtime-/Human-Gates offen (SSOT: `docs/live-readiness/LR-050-FINAL-RECONCILE.md`)
- **Context / MCP / DB posture:** `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`; managed/non-local runtime **NOT ACTIVATED**
- **Status-Trennung bleibt hart:**

| Quelle | Zweck |
|---|---|
| `docs/runbooks/CONTROL_REGISTER.md` | Board-Stage und operativer Fokus |
| `CURRENT_STATUS.md` | Repo-/Engineering-Ledger |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Echtgeld Go/No-Go |
| `docs/live-readiness/LR-050-FINAL-RECONCILE.md` | LR-050 P5-Verdikt und offene Live-Capital-Blocker |

Stage und LR sind orthogonale Systeme: `trade-capable` autorisiert kein Live-Trading.

## New Developer Entry

- [`DEVELOPER_ONBOARDING.md`](DEVELOPER_ONBOARDING.md) - lokales Setup, Secrets, Stack-Bootstrap
- [`docs/index.md`](docs/index.md) - kuerzester aktiver Docs-Einstieg
- [`services/README.md`](services/README.md) - Service-Grenzen und Topologie
- [`tests/README.md`](tests/README.md) - Test-Taxonomie und Einstiege
- [`tools/README.md`](tools/README.md) - lokale Helfer, PowerShell Front Door, Diagnosepfade

## Agent Entry

- Bootloader-Reihenfolge: [`AGENTS.md`](AGENTS.md) -> [`agents/AGENTS.md`](agents/AGENTS.md) -> [`agents/OPEN_CODE_AGENTS.md`](agents/OPEN_CODE_AGENTS.md)
- Status-Surfaces zuerst getrennt lesen: [`docs/runbooks/CONTROL_REGISTER.md`](docs/runbooks/CONTROL_REGISTER.md), [`CURRENT_STATUS.md`](CURRENT_STATUS.md), [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

## Repo Brain / Context Intelligence

- Context-/MCP-Docs-Index: [`docs/surrealdb/README.md`](docs/surrealdb/README.md)
- Read-only Preflight fuer lokale Context-Tooling-Pruefung: `make context-doctor`
- Default posture auf `main`: `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`
- GitHub-/Repo-Live-Wahrheit gewinnt gegen Brain-/Ledger-Claims; LR bleibt `NO-GO`

## Current-main Snapshot

Auf `origin/main` sind die juengsten Kern-Cluster gelandet, u. a.:

- **LR-050 Final Reconcile (#2535):** Child-SSOTs #2526–#2534 plus finales Reconcile-Dokument; Verdikt bleibt **NO-GO** / not ready for live capital.
- **SurrealDB / Context Phase-2 closeout (#1976):** Grandparent arc geschlossen; Real-Task-Proofs, Wave-Matrix-Recert und Phase-2-Review auf `main`.
- **Context / MCP tooling hardening (#2847):** Benchmark #2 ratifiziert; Harness PASS / PASS_WITH_LIMITS ohne produktive Writes.
- **CI / Agent surface (#2994):** Canonical PR-Gate wieder `.github/workflows/ci.yml` auf self-hosted Runner; repo-lokale Skills unter `.codex/cdb_skills/` und `.cursor/skills/`.

Operatives Cockpit: GitHub Issue `#1445`. Aktiver Engineering-Fokus (nicht exhaustiv): `#2440` (LR-030 Shadow/Soak), `#2513` (Trivy upstream tracking, orthogonal).

Details und Session-Ledger: `CURRENT_STATUS.md`.

## Docs / Canonical Entrypoints

1. `docs/runbooks/CONTROL_REGISTER.md`
2. GitHub Issue `#1445` (inkl. neuestem Wochenkommentar)
3. `CURRENT_STATUS.md`
4. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
5. `docs/meta/WORKING_REPO_CANON.md`
6. `agents/AGENTS.md`
7. `docs/index.md`
8. `DEVELOPER_ONBOARDING.md`

## Tooling / Tests / Services

- Tooling: [`tools/README.md`](tools/README.md)
- Services: [`services/README.md`](services/README.md)
- Tests: [`tests/README.md`](tests/README.md)

- `core/` - gemeinsame Domain-/Contract-Logik
- `services/` - laufende Runtime-Services (Signal/Risk/Execution/etc.)
- `infrastructure/compose/` - Compose-Canon (`compose.blue.yml` + `compose.red.yml`)
- `docs/runbooks/` - operative Runbooks inkl. Control Register
- `docs/live-readiness/` - LR-Audit- und Gate-Artefakte
- `knowledge/` - aktive Knowledge-/Governance-Flaeche
- `tools/` - PowerShell Front Doors und Ops-Helfer
- `tests/` - Unit/Integration/E2E/Replay/Chaos

## Dev / Test (CI mode, no containers)

```bash
make test                    # unit + integration
ruff check .                 # CI-required lint
pytest -q -k "not test_mcp_time_server_runtime"   # canonical CI pytest slice
```

Coverage gate (optional locally): `make test-coverage` (80% threshold). E2E und `local_only` brauchen laufenden BLUE+RED-Stack.

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

## .github Control Plane

- Landing-page-Regel: diese Root-README bleibt die Repo-Front-Door.
- Preserved control-plane doc: [`.github/CONTROL_PLANE.md`](.github/CONTROL_PLANE.md)
- Deep-dive runbooks: [`docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md`](docs/runbooks/GITHUB_CONTROL_PLANE_RUNBOOK.md) and [`docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`](docs/runbooks/GITHUB_WORKFLOW_REGISTER.md)

## Navigation

- `mcp_navpack_working_repo/ENTRYPOINTS.yaml`
- `mcp_navpack_working_repo/CHEATSHEET.md`
- `docs/meta/WORKING_REPO_CANON.md`

## Boundary

Archiv-/Snapshot-Flaechen (`docs/archive/**`, `knowledge/archive/**`) sind historischer Rueckgriff und kein aktiver Pflegepfad.
