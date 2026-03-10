# Evidence Spec for Issue #744 — P1 — Access Control Matrix & Threat Model (DB Layer)
Purpose:
- Create the governance anchor for DB-layer access control across Postgres and SurrealDB.
- Capture the current permission surface, explicit gaps, and the child-issue trace needed to harden the DB layer without changing runtime behavior.

Pass criteria:
- [x] INDEX metadata is present and aligned to Issue #744.
- [x] Evidence links are concrete where available and explicit where gaps remain.
- [x] Parent, child, and related issue links are traceable from this document.
- [x] Child issue mapping explicitly covers #741, #750, #751, #752, and #753.

Evidence plan:
- This anchor stays open until the remaining live DB UNKNOWN/GAP entries are backed by deployed grant / RLS / actor evidence; the Task G integrity-report slices are delivered, but they do not close that operational proof gap.
- Live privilege evidence is expected from grant dumps, migration verification, and least-privilege validation anchored back to [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741).

Current status:
- Matrix: Open
- GitHub: OPEN
- Date: 2026-03-01

---

## INDEX (Governance Anchor)

- Title: `P1 — Access Control Matrix & Threat Model (DB Layer)`
- Category: `Security Governance (ACM/Threat Model)`
- Gate-Level: `P1 / should`
- Status snapshot:
  - Matrix: `Open`
  - GitHub: `OPEN`
  - updatedAt: `2026-03-01T06:01:34Z`
- Owner metadata from issue body: `scope:core + prio:should + agent:gemini`
- Scope: `Role x Resource x Action (CRUD)` for Postgres and SurrealDB, plus bypass paths and control gaps.
- GitHub labels observed on Issue #744: `documentation`, `security`, `type:docs`, `type:security`, `type:research`, `scope:core`, `scope:docs`, `scope:monitoring`, `stage:proof`, `prio:must`, `agent:gemini`, `agent:copilot`
- Parent: [#749](https://github.com/jannekbuengener/Claire_de_Binare/issues/749) `Governance Core Gap — Strategy & Nexus Overview`
- Child issues:
  - [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741) `Postgres Least-Privilege + RLS Hardening (Writer/Reader Split)`
  - [#750](https://github.com/jannekbuengener/Claire_de_Binare/issues/750) `Core Secrets Domain: Integrity Guards for core_secrets`
  - [#751](https://github.com/jannekbuengener/Claire_de_Binare/issues/751) `Governance Domain: Integrity Guards for audit_trail and governance_events`
  - [#752](https://github.com/jannekbuengener/Claire_de_Binare/issues/752) `Deployment Domain: Integrity Guards for deployment_approvals`
  - [#753](https://github.com/jannekbuengener/Claire_de_Binare/issues/753) `Access Domain: Integrity Guards for system_config and security_policies`
- Related:
  - [#641](https://github.com/jannekbuengener/Claire_de_Binare/issues/641) `Access Rules / RLS hardening`
  - [#663](https://github.com/jannekbuengener/Claire_de_Binare/issues/663) `Six-Eyes enforcement`

## Goal

Define a stable DB-layer governance anchor that records:

- the current Postgres and SurrealDB access model that is actually visible in-repo,
- the intended protection boundaries for audit, governance, access, and secret-adjacent domains,
- the bypass vectors that still exist, and
- the child issues that must close the remaining gaps.

## Scope

- Postgres roles and grants for runtime, governance, and security-adjacent tables.
- SurrealDB governance-mirror table permissions and documented access expectations.
- Comparison of visible `IST` permissions versus intended `SOLL` controls where those differ.
- Explicit documentation of forbidden or risky write paths such as shared credentials, migration/admin bypass, owner bypass, and manual SQL.

## Out of Scope

- Changing grants, migrations, RLS, triggers, or application behavior.
- Live database privilege dumps or environment-specific credential inspection.
- GitHub policy, workflow, or deployment changes.

## Access Control Matrix

### Postgres

| Role / principal | Resources | Create | Read | Update | Delete | Current state / notes |
|---|---|---|---|---|---|---|
| `claire_user` (runtime login before hardening) | `public` schema tables and sequences | CONDITIONAL | CONDITIONAL | CONDITIONAL | CONDITIONAL | `schema.sql` grants broad `ALL PRIVILEGES` to `claire_user`; `enforce_least_privilege.sql` is the compensating script that revokes and rebinds the runtime login to `cdb_writer`. Effective least privilege is therefore deployment-dependent, not guaranteed by schema alone. |
| `cdb_reader` | `signals`, `orders`, `trades`, `positions`, `portfolio_snapshots`, `risk_events`, `correlation_ledger`, `blocked_decisions`, `core_secrets_metadata`, `audit_trail`, `governance_events`, `deployment_approvals_mirror`, `system_config`, `security_policy_refs`, `schema_version` | DENY | ALLOW | DENY | DENY | Explicit `SELECT`-only allowlist in `roles_and_grants.sql`. No write path documented. |
| `cdb_writer` | `signals`, `orders`, `trades`, `portfolio_snapshots`, `risk_events`, `correlation_ledger`, `blocked_decisions` | ALLOW | ALLOW | DENY | DENY | Explicit `SELECT` + `INSERT`; no `UPDATE`, no `DELETE`. Intended for append-style runtime writes. |
| `cdb_writer` | `positions` | ALLOW | ALLOW | ALLOW | DENY | The only table with explicit `UPDATE` for the writer role. |
| `cdb_writer` | `schema_version` | DENY | ALLOW | DENY | DENY | Explicit read-only visibility for schema version checks. |
| `cdb_writer` | `core_secrets_metadata`, `audit_trail`, `governance_events`, `deployment_approvals_mirror`, `system_config`, `security_policy_refs` | DENY | DENY | DENY | DENY | No explicit grants found for the writer role in `roles_and_grants.sql`. This is good for least privilege if the hardening script has actually been enforced. |
| `cdb_admin` (deploy / migration role) | All tables and sequences in `public` | ALLOW | ALLOW | ALLOW | ALLOW | Full-power role intended for deployment and migration tasks. This role remains the main privilege-escalation and ownership-bypass surface. |

Postgres notes:

- `core_secrets` is referenced by child issue #750, but the inspected Postgres schema in-repo exposes `core_secrets_metadata`, not a `core_secrets` table.
- `system_config` exists in the Postgres grant file, but `security_policies` does not; the visible table is `security_policy_refs`.
- No active RLS policies were found in the inspected DB-layer artifacts. The runbook explicitly frames the current work as grant hardening first, not completed RLS enforcement.

### SurrealDB

| Role / scope | Resources | Create | Read | Update | Delete | Current state / notes |
|---|---|---|---|---|---|---|
| Implicit application principal (auth object not defined) | `audit_trail`, `deployment_approvals_mirror`, `system_config`, `security_policy_refs`, `access_matrix` | ALLOW | ALLOW | UNKNOWN (GAP) | UNKNOWN (GAP) | `setup.surql` explicitly spells `CREATE` and `SELECT` but does not declare named principals or explicit `UPDATE NONE` / `DELETE NONE` for these tables. The README describes them as append-only or read-oriented, but the auth boundary is undocumented. |
| Implicit application principal (auth object not defined) | `governance_events` | ALLOW | ALLOW | UNKNOWN (GAP) | UNKNOWN (GAP) | The permission clause in `setup.surql` appears syntactically malformed around `CREATE` / `SELECT`, so the effective permission surface should be treated as unverified until validated. |
| Implicit application principal (auth object not defined) | `ledger_event` | ALLOW | ALLOW | DENY | DENY | `setup.surql` explicitly sets `SELECT FULL`, `CREATE FULL`, `UPDATE NONE`, `DELETE NONE`. This is the clearest append-only control in the SurrealDB snapshot. |
| Namespace / database owner or admin (not defined in repo) | All tables in `governance.governance_mirror` | UNKNOWN (GAP) | UNKNOWN (GAP) | UNKNOWN (GAP) | UNKNOWN (GAP) | No `DEFINE USER`, `DEFINE ACCESS`, `DEFINE SCOPE`, or token configuration is present in the inspected SurrealDB artifacts, so the privileged-actor boundary is not documented here. |

SurrealDB notes:

- The inspected SurrealDB model documents table-level permissions, not authenticated actors. The actor dimension therefore remains partially unresolved by design and must be treated as a governance gap.
- `system_config` is present in SurrealDB, but `security_policies` is not; the visible table is `security_policy_refs`.
- The SurrealDB mirror is documented as governance-oriented and out-of-scope for secrets values, production balances, and live order routing.

## Threat Model (DB Layer)

| Threat / bypass vector | Current exposure | Current or planned control | Tracking |
|---|---|---|---|
| Shared or direct DB credentials (`claire_user`, PAT-backed ops, manual SQL clients) | A single runtime login can be over-privileged if `enforce_least_privilege.sql` has not been applied in the target environment. | Revoke broad grants, bind runtime access to reader/writer split, and verify effective grants from live DB. | [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741), [#641](https://github.com/jannekbuengener/Claire_de_Binare/issues/641) |
| Privilege escalation via migration / deploy role | `cdb_admin` has full schema, table, and sequence power; manual ownership transfer is an explicit step in the runbook. | Keep admin role deploy-only, separate credentials from runtime, and add verifiable least-privilege evidence. | [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741) |
| RLS bypass via owner/admin or absent RLS | No active RLS policies were found in the inspected repo artifacts, and table ownership can bypass grant intent. | Add actual RLS and least-privilege proof rather than relying on grant scripts alone. | [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741), [#641](https://github.com/jannekbuengener/Claire_de_Binare/issues/641) |
| Append-only violations on `audit_trail`, `governance_events`, and deployment mirrors | Writer grants already avoid these Postgres tables, but admin/manual SQL can still mutate them; several SurrealDB tables do not explicitly declare `UPDATE NONE` / `DELETE NONE`. | Add integrity guards and append-only enforcement in the governance and deployment domains. | [#751](https://github.com/jannekbuengener/Claire_de_Binare/issues/751), [#752](https://github.com/jannekbuengener/Claire_de_Binare/issues/752) |
| Out-of-band writes through scripts or manual SQL | Scripts and operator commands can write outside the normal application control path, especially during setup or recovery. | Narrow allowed write principals, document approved operational paths, and verify them with audits. | [#749](https://github.com/jannekbuengener/Claire_de_Binare/issues/749), [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741) |
| Schema drift or missing grant enforcement | `schema.sql`, `roles_and_grants.sql`, `enforce_least_privilege.sql`, and verification comments can diverge across environments. | Treat live grant dump plus migration verification as the source of truth and attach that evidence to the hardening issues. | [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741), [#749](https://github.com/jannekbuengener/Claire_de_Binare/issues/749) |
| Secrets exposure in `system_config`, `security_policy_refs`, and `core_secrets_metadata` adjacency | The inspected schema exposes metadata and policy-reference surfaces, but not a clearly hardened secrets/access domain end state. | Add integrity guards and explicit domain boundaries for secrets and access-policy records. | [#750](https://github.com/jannekbuengener/Claire_de_Binare/issues/750), [#753](https://github.com/jannekbuengener/Claire_de_Binare/issues/753) |
| SurrealDB auth ambiguity | Table permissions exist, but named SurrealDB users/scopes/access methods do not appear in-repo, so actor accountability is incomplete. | Document or implement the auth boundary explicitly, or treat the mirror as internal-only with enforced operational controls. | [#753](https://github.com/jannekbuengener/Claire_de_Binare/issues/753), [#749](https://github.com/jannekbuengener/Claire_de_Binare/issues/749) |

## Crosslinks and Child Mapping

### Parent / meta anchor

| Issue | Status | Relation | What it delivers |
|---|---|---|---|
| [#749](https://github.com/jannekbuengener/Claire_de_Binare/issues/749) | OPEN | Parent / meta | Program-level governance gap overview that links the DB-hardening slices into one roadmap. |

### Child issues

| Issue | Status | What it delivers |
|---|---|---|
| [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741) | Phase-1 Delivered | Delivered via [#1013](https://github.com/jannekbuengener/Claire_de_Binare/pull/1013) with CI evidence in [22537116044](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22537116044), report tooling in `docs/governance/evidence/ISSUE-741-postgres-least-privilege-rls.md`, and a local-docker live evidence comment at [issuecomment-3979218245](https://github.com/jannekbuengener/Claire_de_Binare/issues/741#issuecomment-3979218245). The operational gap is now narrowed to environment-by-environment proof and eventual runtime enforcement decisions. |
| [#750](https://github.com/jannekbuengener/Claire_de_Binare/issues/750) | Delivered | Merged via [#1011](https://github.com/jannekbuengener/Claire_de_Binare/pull/1011) with evidence in `docs/governance/evidence/ISSUE-750-core-secrets-integrity-guards.md`. This now provides modeled + report coverage for `core_secrets_metadata` / `core_secrets` / `service_secrets`, but live grants, ownership, and runtime enforcement gaps still point back to [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741). |
| [#751](https://github.com/jannekbuengener/Claire_de_Binare/issues/751) | CLOSED | Adds integrity guard intent for `audit_trail` and `governance_events`; this closes part of the append-only threat model but not the full DB-layer matrix. |
| [#752](https://github.com/jannekbuengener/Claire_de_Binare/issues/752) | Delivered | Merged via [#1010](https://github.com/jannekbuengener/Claire_de_Binare/pull/1010) with evidence in `docs/governance/evidence/ISSUE-752-deployment-integrity-guards.md`. This now provides modeled + report coverage for `deployment_approvals_mirror`, but live grants, RLS proof, and runtime enforcement gaps still point back to [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741). |
| [#753](https://github.com/jannekbuengener/Claire_de_Binare/issues/753) | Delivered | Merged via [#1009](https://github.com/jannekbuengener/Claire_de_Binare/pull/1009) with evidence in `docs/governance/evidence/ISSUE-753-access-integrity-guards.md`. This now provides modeled + report coverage for `system_config` and `security_policy_refs`, but live grants, RLS proof, and runtime enforcement gaps still point back to [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741). |

### Related issues

| Issue | Status | Why it matters here |
|---|---|---|
| [#641](https://github.com/jannekbuengener/Claire_de_Binare/issues/641) | CLOSED | Earlier least-privilege / append-only / RLS hardening track that informs the intended control model for this anchor. |
| [#663](https://github.com/jannekbuengener/Claire_de_Binare/issues/663) | CLOSED | Six-eyes governance control relevant to who is allowed to approve high-impact changes, even though this anchor stays focused on DB access paths. |

## Evidence

### Issue-linked evidence from #744

- Issue: [#744](https://github.com/jannekbuengener/Claire_de_Binare/issues/744)
- PR: [#911](https://github.com/jannekbuengener/Claire_de_Binare/pull/911) `deps(actions): bump actions/upload-artifact from 4.6.2 to 6.0.0`
- Run: [22291780927](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22291780927) `Claude Code Review`
- Run: [22291780930](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22291780930) `ci`
- Run: [22291780252](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22291780252) `Automatic Dependency Submission`

### Task G delivery evidence linked from this anchor

- [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741) least-privilege phase-1 delivery:
  - PR: [#1013](https://github.com/jannekbuengener/Claire_de_Binare/pull/1013)
  - CI: [22537116044](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22537116044) `ci`
  - Policy gate: [22537116047](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22537116047)
  - Evidence doc: `docs/governance/evidence/ISSUE-741-postgres-least-privilege-rls.md`
  - Live evidence comment: [issuecomment-3979218245](https://github.com/jannekbuengener/Claire_de_Binare/issues/741#issuecomment-3979218245)

- [#753](https://github.com/jannekbuengener/Claire_de_Binare/issues/753) access-domain delivery:
  - PR: [#1009](https://github.com/jannekbuengener/Claire_de_Binare/pull/1009)
  - CI: [22535953931](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22535953931) `ci`
  - Policy gate: [22535953930](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22535953930), [22535956261](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22535956261)
  - Evidence doc: `docs/governance/evidence/ISSUE-753-access-integrity-guards.md`
- [#752](https://github.com/jannekbuengener/Claire_de_Binare/issues/752) deployment-domain delivery:
  - PR: [#1010](https://github.com/jannekbuengener/Claire_de_Binare/pull/1010)
  - CI: [22536495129](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22536495129) `ci`
  - Policy gate: [22536495087](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22536495087)
  - Evidence doc: `docs/governance/evidence/ISSUE-752-deployment-integrity-guards.md`
- [#750](https://github.com/jannekbuengener/Claire_de_Binare/issues/750) core-secrets delivery:
  - PR: [#1011](https://github.com/jannekbuengener/Claire_de_Binare/pull/1011)
  - CI: [22536664457](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22536664457) `ci`
  - Policy gate: [22536664462](https://github.com/jannekbuengener/Claire_de_Binare/actions/runs/22536664462)
  - Evidence doc: `docs/governance/evidence/ISSUE-750-core-secrets-integrity-guards.md`

### Repo artifacts used for the current-state matrix

- `infrastructure/database/roles_and_grants.sql`
- `infrastructure/database/schema.sql`
- `infrastructure/database/enforce_least_privilege.sql`
- `docs/runbooks/postgres_least_privilege_rls.md`
- `infrastructure/surrealdb/setup.surql`
- `infrastructure/surrealdb/README.md`
- `docs/surrealdb/data-ownership-matrix.md`

### Explicit gaps

- Local-docker live Postgres grant and RLS evidence is now attached via [#741 comment evidence](https://github.com/jannekbuengener/Claire_de_Binare/issues/741#issuecomment-3979218245), but deployed environments remain partially unverified until equivalent artifacts are captured per environment. This remains the main gap for [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741).
- No active Postgres RLS policy definitions were found in the inspected repo snapshot. Any "RLS" expectation must therefore be treated as planned or historical unless child evidence proves otherwise.
- No explicit SurrealDB users, scopes, or access tokens are defined in the inspected repo artifacts, so actor attribution in the SurrealDB matrix remains `UNKNOWN (GAP)`.
- The SurrealDB `governance_events` permission line appears malformed in `setup.surql`, so its effective append-only semantics are not yet provable from the checked-in file alone.
- The Task G child deliveries now provide modeled + report coverage for `core_secrets_metadata`, `deployment_approvals_mirror`, `system_config`, and `security_policy_refs`, but they do not replace the missing live grant dump / RLS / runtime-enforcement proof that still needs to be anchored against [#741](https://github.com/jannekbuengener/Claire_de_Binare/issues/741).
- The inspected DB layer still exposes `core_secrets_metadata` and `security_policy_refs` rather than the logical issue names `core_secrets` and `security_policies`. The delivered child docs now record that naming drift explicitly, which closes the documentation gap but not the live-environment verification gap.
