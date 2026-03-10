# Evidence Spec for Issue #741 — Postgres Least-Privilege + RLS Hardening

Purpose:
- Provide a reproducible path to capture live Postgres role, grant, and RLS evidence without changing runtime behavior.
- Keep the DB-layer governance anchor open until deployed environments prove the writer/reader split and any future RLS posture with attached artifacts.

Pass criteria:
- [ ] A live dump was generated with `scripts/audit/postgres_privilege_dump.sql`.
- [ ] The offline diff was run with `scripts/audit/postgres_least_privilege_report.py`.
- [ ] Dump artifacts were attached outside the repo (Issue/PR/Run artifact), not committed.
- [ ] Remaining live-environment gaps are documented explicitly.

Current status:
- Evidence status: OPEN
- GitHub issue state observed during implementation: CLOSED
- Date: 2026-03-01

---

## Scope

- Postgres roles: `cdb_reader`, `cdb_writer`, `cdb_admin`, `claire_user`
- Effective table privileges for the least-privilege writer/reader split
- RLS table flags and policy inventory for the tracked `public` tables
- Offline desired-vs-observed diff against `scripts/audit/desired_privileges.json`

## Secret Policy

- Canonical Secret Store: `C:\Users\janne\Documents\.secrets\.cdb`
- Rotation / changes: rotator-only via `infrastructure/scripts/manage_secrets.ps1`; do not hand-edit secret files or stage secret material in the repo.
- Connection env: export or load `POSTGRES_DSN`, `DATABASE_URL`, and related connection settings via the rotator workflow before running the dump or report commands.
- Rotator proof-of-use: use `pwsh -File infrastructure/scripts/manage_secrets.ps1 -Action list` and `pwsh -File infrastructure/scripts/manage_secrets.ps1 -Action validate` as the non-mutating evidence commands. There is no separate `status` or `dry-run` verb in the current script.

## How to Generate Live Evidence

- Follow [postgres_least_privilege_rls.md](../../runbooks/postgres_least_privilege_rls.md) to dump live CSV artifacts and run the offline report.
- Generate the evidence bundle in a local or external path outside the repo, then upload the ZIP via GitHub UI attachment as the standard path. If UI upload is unavailable, use an external artifact store and paste the resulting link into the Issue.
- Do not commit live dumps, ZIP bundles, DSNs, passwords, or other environment-specific secrets to the repository.

## Evidence Placeholders

- Dump timestamp (UTC): `TBD`
- Environment: `TBD`
- Local / external evidence bundle path: `TBD`
- Dump artifact links: `TBD`
- Offline report artifact links: `TBD`
- Issue comment permalink: `TBD`
- Operator notes: `TBD`

## Current Gaps

- Live deployment proof is still missing for the `claire_user` -> `cdb_writer` handoff and the absence of direct runtime privileges.
- RLS remains evidence-only in this phase; no runtime enforcement, trigger hardening, or policy rollout is introduced here.
- Ownership-bypass and live grant drift remain possible until operator evidence confirms the deployed state.

## Crosslinks

- DB-layer governance anchor: `#744`
- Related Task G slices: `#750`, `#752`, `#753`
- Follow-up hardening / operational proof target: `#741`
