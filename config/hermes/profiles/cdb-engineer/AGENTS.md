# Project context — cdb-engineer

Claire de Binare engineering profile for Hermes on Hetzner (#4289).

## Authority
- May prepare branches/PRs according to CDB PR-Flow when tokens allow.
- May **not** publish `cdb-local-ci`, admin-merge, or alter branch protection.
- May **not** claim Live-Go, Echtgeld-Go, or strategy promotion.
- Board stage `trade-capable` ≠ Live-Go. LR SSOT remains authoritative.

## Workspace
- Windows path allowlist only: `D:\Dev\HermesWorkspace\Claire_de_Binare`  <!-- pragma: allowlist secret -->
- Default tool posture: read-only; write only inside the dedicated workspace.
- Kill-switch OFF required for Windows tools; otherwise `WORKSTATION_UNAVAILABLE`.

## Canon pointers (repo)
- `AGENTS.md` / `agents/AGENTS.md`
- `docs/runbooks/merge_policy_ci_gate.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- Auth lineage: #4170 / #4195 — reuse App credentials; do not create a second authenticator.

## Secrets
- PEM/App credentials live outside agent-readable workspaces.
- Use `python -m tools.hermes_ops mint-token` — never embed tokens in prompts/memory.
