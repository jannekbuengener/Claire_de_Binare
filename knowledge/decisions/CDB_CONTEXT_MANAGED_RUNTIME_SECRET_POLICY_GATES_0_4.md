# Context Managed / Non-Local Runtime Secret Policy (Gates 0–4)

| Field | Value |
| --- | --- |
| Status | **accepted** (design / prerequisite only) |
| Date | 2026-06-02 |
| Issue | GitHub issue [#2821](https://github.com/jannekbuengener/Claire_de_Binare/issues/2821) |
| Lineage | [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) (grandparent), [#2778](https://github.com/jannekbuengener/Claire_de_Binare/issues/2778) (Phase-2 epic, CLOSED), [#2803](https://github.com/jannekbuengener/Claire_de_Binare/issues/2803) (managed/non-local decision), [#2804](https://github.com/jannekbuengener/Claire_de_Binare/issues/2804) (controlled write v2 design) |
| Runtime activation | **NOT ACTIVATED** |
| Satisfies | #2803 Gate 0 prerequisite **G0-4** (documentation evidence) |
| LR | **NO-GO** per [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) |

## Executive decision

**Managed and non-local Context/SurrealDB/MCP runtimes remain NOT ACTIVATED.**

This document is the **design-only secret-handling policy** required before any future
`managed_readonly` or `nonlocal_readonly_mcp` posture from
[`CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md`](CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md).
Closing issue **#2821** records that prerequisite; it does **not** authorize:

- productive SurrealDB writes,
- MCP mutations or registry write tools,
- tunnel/compose/BLUE/RED changes,
- `PERSIST_ALLOWED=True` or `MUTATION_ALLOWED=True`,
- Live-Readiness Go, Echtgeld, or strategy validation.

**Board stage `trade-capable` is orthogonal to LR and does not imply secret-policy activation.**

## Scope and non-goals

**In scope:**

- Secret **classes**, storage boundaries, rotation/revocation **process**, redaction rules
  for Context/MCP/SurrealDB **managed/non-local** postures
- Gate 0–4 semantics (`PASS` / `WARN` / `FAIL` / `BLOCKED`) and evidence checklists
- Alignment with operator `SECRETS_PATH` and context-local secrets directory patterns
- Audit evidence required **before** any separate activation issue receives Jannek-GO

**Out of scope (unchanged by this policy):**

- Implementing adapters, tunnels, MCP config, or compose changes
- Ingesting, copying, or rotating **real** secret values in repo, CI, or agent output
- BLUE/RED trading secrets rotation execution (see
  [`knowledge/governance/SECRETS_POLICY.md`](../governance/SECRETS_POLICY.md) and
  [`knowledge/governance/SECRET_ROTATION_POLICY.md`](../governance/SECRET_ROTATION_POLICY.md))
- Productive T3 audit-trail endpoint activation (issue #2735 lineage — separate HG ladder)
- Grandparent epic **#1976** full wave matrix closeout (only RTP gate satisfied by proof run)

**Related SSOT (do not duplicate):**

| Document | Role |
| --- | --- |
| [`SECRETS_POLICY.md`](../governance/SECRETS_POLICY.md) | Docker/operator file layout under `SECRETS_PATH` |
| [`SECRET_ROTATION_POLICY.md`](../governance/SECRET_ROTATION_POLICY.md) | Local-first rotation modes (`auto` / `manual`) |
| [`CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md`](CDB_CONTEXT_MANAGED_NONLOCAL_RUNTIME_DECISION.md) | Runtime option matrix; G0 table |
| [`CDB_CONTROLLED_WRITE_STRATEGY_V2_DESIGN.md`](CDB_CONTROLLED_WRITE_STRATEGY_V2_DESIGN.md) | Write ladder; L4 secret dependency |
| [`CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md) | `brain_source` / `brain_status` defaults |

## Gate semantics (all gates)

| Verdict | Meaning |
| --- | --- |
| **PASS** | Evidence complete; no blocker for *policy acceptance* (not runtime activation) |
| **WARN** | Documented gap with compensating control and dated follow-up issue |
| **FAIL** | Required evidence missing; managed/non-local activation remains blocked |
| **BLOCKED** | Hard stop (secret leak suspected, LR-Go requested without review, or write gates flipped) |

Policy acceptance on `main` satisfies **#2803 G0-4** only. Gates 1–4 remain operator
checklists for **future** activation slices.

---

## Gate 0 — Local-only baseline and no-secret-in-repo proof

**Purpose:** Prove current `local_only` posture does not depend on secrets in git and
that localhost boundaries hold before discussing managed credentials.

| Check ID | Requirement | PASS evidence |
| --- | --- | --- |
| G0-0a | `PERSIST_ALLOWED=False` on `main` | `tools/surrealdb/memory_write_gate.py` constant |
| G0-0b | `MUTATION_ALLOWED=False` on `main` | Same module / related write gates |
| G0-0c | Adapter factory rejects non-local URLs | `tools/mcp/surrealdb_adapter_factory.py` localhost guards |
| G0-0d | MCP registry read-only | `ContextToolRegistry.register()` blocks `read_only=False` |
| G0-0e | No secret **values** in repo index | `git ls-files` + gitleaks CI posture; no `Documents/.secrets` paths tracked |
| G0-0f | LR SSOT says NO-GO | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` |

**Default verdict for #2821 delivery:** **PASS** when this policy lands on `main` and
checks G0-0a–G0-0f are cited in the Real-Task-Proof artifact (repo crosscheck, not
re-execution of full wave audits).

**FAIL triggers:** Any PR/issue/log contains API keys, passwords, connection strings
with credentials, or private tenant identifiers presented as live values.

---

## Gate 1 — Credential inventory model (no values)

**Purpose:** Define **what classes** of credentials may exist for future managed/non-local
paths without storing values in CDB artifacts.

| Class ID | Description | Typical consumer | Stored where (design) |
| --- | --- | --- | --- |
| `CTX-DB-AUTH` | SurrealDB username/password or token for read-only context namespace | Productive-read adapter (future) | Operator vault / `SECRETS_PATH` extension — **not** repo |
| `CTX-DB-TLS` | TLS client cert/key or CA bundle for managed DB | Adapter TLS config | Operator-controlled files; mount via env — **not** repo |
| `MCP-TRANSPORT` | Bearer/API key for remote read-only MCP bridge (if ever used) | MCP client config | Operator vault — **never** `claire-de-binare.mcp.json` values |
| `TUNNEL-AUTH` | SSH/WireGuard/API token for conduit to OT/IT boundary | Tunnel tooling | Separate security review issue (#2803 G0-5) |
| `VENDOR-API` | Hosted SurrealDB/cloud control-plane API key | Provisioning automation | Out of band; redacted proof only |
| `HG-P-TOKEN` | Human-GO / delivery approval tokens | Write ladder (#2804) | Existing human-controlled stores; never logged raw |

**Inventory rules:**

1. Every future managed credential MUST map to exactly one `Class ID`.
2. Issues and PRs MAY reference class IDs and **redacted** fingerprints (e.g.
   `sha256_prefix=ab12…` of file mtime+size), never raw values.
3. Context tables MUST NOT store secret field values (forbidden data class per #2803).

**PASS for policy slice:** This table is accepted on `main` linked from #2821.  
**FAIL:** Activation issue lists credentials without class ID or proposes repo-stored secrets.

---

## Gate 2 — Storage location policy and `SECRETS_PATH` alignment

**Purpose:** Keep operator-owned filesystem boundary for local stack; extend model for
managed paths without merging trading secrets into context exports.

| Zone | Path pattern (illustrative) | Allowed content | Forbidden |
| --- | --- | --- | --- |
| **Z-LOCAL-OP** | `%USERPROFILE%/Documents/.secrets/.cdb/` (see SECRETS_POLICY) | BLUE/RED Docker secret **files** | Committing files; pasting values in chat |
| **Z-CTX-LOCAL** | Context adapter config dir (operator-local; path via env only) | Localhost Surreal credentials for dev read | Non-localhost URLs without activation GO |
| **Z-MANAGED-READ** (future) | Operator-defined mount; **not** standardized in #2821 | Read-only DB auth for managed endpoint | Write-capable credentials |
| **Z-REPO** | Git working tree | Placeholders, env **names**, manifest keys | Any secret value |
| **Z-GH** | Issues, PRs, comments, Actions logs | Class IDs, PASS/FAIL, redacted proof | Tokens, passwords, `.env` dumps |
| **Z-PROOF** | Session logs, proof packs, MCP JSON responses | Redacted transcripts; structural metadata | Raw URLs with embedded creds |

**SECRETS_PATH alignment:**

- Canonical trading/runtime secrets remain under
  [`SECRETS_POLICY.md`](../governance/SECRETS_POLICY.md) (`SECRETS_PATH` → Docker secrets).
- Context MCP tools that accept `secrets_path` MUST treat it as **operator-local
  directory reference**, not an invitation to echo contents into tool responses
  (see `tools/mcp/context_bridge.py` trust-summary parameters — metadata only).
- Managed/non-local activation MUST document **separate** secret zone `Z-MANAGED-READ`
  in the activation issue; mixing into `Z-LOCAL-OP` files without review → **FAIL**.

**PASS:** Zones documented; no path values committed in #2821 PR.  
**BLOCKED:** Any doc instructs agents to read secret files into prompts or MCP payloads.

---

## Gate 3 — Rotation, revocation, and operator proof

**Purpose:** Before managed/non-local go-live, operators can rotate and revoke without
publishing values to GitHub.

| Step | Action | Evidence |
| --- | --- | --- |
| R3-1 | Classify each credential as `auto` or `manual` per SECRET_ROTATION_POLICY | Issue table |
| R3-2 | Rotation dry-run in isolated environment | Redacted log: "rotated Class X; services restarted" |
| R3-3 | Revocation drill: disable old credential | Redacted log + failed-auth proof (expected) |
| R3-4 | Confirm Context/MCP adapters fail-closed without creds | Adapter status `surrealdb-local-unavailable` or guarded error — no silent fallback to external MCP |
| R3-5 | Update inventory manifest (names only) | Operator attestation comment on activation issue |

**PASS for #2821:** Process defined; no rotation executed in design slice.  
**FAIL:** Activation without R3-1–R3-5 evidence.  
**WARN:** Manual-class secrets with dated compensating control + follow-up.

---

## Gate 4 — Redaction in proof packs, logs, issues, PRs, and MCP outputs

**Purpose:** Ensure managed/non-local proof cannot leak credentials into durable
GitHub or agent-visible channels.

**Forbidden in durable outputs:**

- Passwords, API keys, JWTs, session cookies, private keys, connection strings with
  embedded credentials
- Full `SECRETS_PATH` file contents or base64 secret blobs
- Unredacted `https://user:pass@host/...` URLs
- Raw `human_go_token` or equivalent HG fields (#2704 / #2804 alignment)

**Allowed metadata examples:**

- `secret_class=CTX-DB-AUTH`
- `credential_present=true`
- `rotation_due=2026-Q3` (date only)
- `redaction_applied=true`
- `[REDACTED]` / `[REDACTED_URL]` / `[REDACTED_IP]` markers

**Repo crosscheck (pattern reference, not new runtime):**

- `tools/surrealdb/audit_trail_t3_common.py` — `redact_output()` for proof scripts
- CDB safety boundary rule: no sensitive values in issues, PRs, comments, logs, reports

**Agent/MCP rules:**

- `metadata.source` and `brain_source` from callers are **not** evidence of safe handling
- Context Brain output does **not** authorize posting secrets to GitHub for "debugging"
- Proof packs attached to issues MUST be reviewed with Gate 4 checklist before comment

**PASS:** #2821 PR and proof artifact contain no secret-like strings; rg validation clean.  
**BLOCKED:** Any leak → rotate affected class, revoke GO, incident follow-up.

---

## Managed / non-local activation blockers (after this policy)

Even with Gates 0–4 **accepted**, the following remain **NOT ACTIVATED** until separate
issues + evidence + Jannek-GO:

| Blocker | Source |
| --- | --- |
| G0-5 Security/deployment review (TLS, tenant isolation, egress) | #2803 |
| G0-6 Adapter contract extension (read-only non-local allowlist) | Implementation PR |
| G0-7 Operator proof pack (read OK / write fail-closed) | Session log |
| G0-8 LR-SSOT human review | LR audit files |
| G0-9 Docker/compose change requires explicit Jannek Human-GO (Gordon gate decommissioned) | Explicit GO |
| Write ladder L0–L4 | #2804 |
| MCP/tunnel/compose changes | Scoped issues only |

This policy is **prerequisite only** for G0-4. It does not satisfy G0-5 through G0-9.

---

## Allowed metadata vs forbidden secret values

| Allowed (examples) | Forbidden (examples) |
| --- | --- |
| Env var **names**: `SURREALDB_USER`, `SECRETS_PATH` | Env var **values** |
| File **names**: `REDIS_PASSWORD`, `context_adapter.env` | File **contents** |
| Boolean flags: `has_credential`, `tls_enabled` | JWT strings, `sk-…`, `AKIA…` |
| Redacted markers per Gate 4 | Paste of operator chat with secrets |
| GitHub issue/PR **Refs** without payloads | Screenshots of secret managers |

---

## Audit evidence requirements (pre-activation)

Before any `managed_readonly` or `nonlocal_readonly_mcp` activation issue moves to
implementation:

1. Link to this policy on `main` (merge SHA).
2. Gate 0–4 checklist table in issue comment with PASS/WARN/FAIL per row.
3. Redacted proof pack (session log path) showing adapter boundary tests.
4. Brain Evidence block with honest `brain_source` (no forged surrealdb-local).
5. Explicit non-goals: no LR-Go, no `PERSIST_ALLOWED=True`, no trading data in SurrealDB.
6. LR reviewer sign-off recorded in issue (human; not agent-autonomous).

---

## Rollback / kill-switch posture

On secret incident or policy violation:

1. **Immediate:** Disable managed endpoint env vars and adapter config paths.
2. **Fail-closed:** Revert to `local_only` per #2803; report `brain_status=blocked`.
3. **Do not** flip write gates to "unstick" agents — fix credentials out of band.
4. **Preserve** audit rows already written (compliance); add contradiction note if needed.
5. **Revoke** Jannek-GO on activation issue; new GO required after rotation proof (Gate 3).

---

## Validation checklist

**Operator / agent (before claiming policy complete):**

- [ ] `rg` / review: no secret-like tokens in changed markdown
- [ ] `git diff --check` clean
- [ ] `PERSIST_ALLOWED` / `MUTATION_ALLOWED` still False on `main`
- [ ] LR doc still NO-GO; no "managed runtime enabled" wording
- [ ] Brain Evidence: repo-only unless real adapter record IDs
- [ ] #2821 issue comment cites merge SHA + path to this file

**CI (docs-only PR):**

- [ ] policy-gate + unit CI green
- [ ] gitleaks (repo posture) — no new secrets in diff

---

## Future implementation requirements

Implementation of managed/non-local secrets MUST be tracked in **deduplicated**
follow-up issues (search before create), typically including:

- Adapter/MCP code changes with tests (localhost denylist / non-local allowlist)
- Tunnel and network security review
- Integration with rotation tooling for `auto` classes
- MCP registry and PermissionGuard updates if new tools appear

**#2821 completion does not authorize starting those issues without separate GO.**

---

## Completion statement (#2821)

Landing this document on `main` and closing **#2821** records the **design deliverable**
for managed/non-local secret handling (Gates 0–4). It satisfies **#2803 G0-4**
documentation evidence only. **Managed/non-local runtime remains NOT ACTIVATED.**
