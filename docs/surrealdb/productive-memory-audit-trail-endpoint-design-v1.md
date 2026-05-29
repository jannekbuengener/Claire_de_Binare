# Productive Memory Audit Trail Endpoint Design v1 (#2735)

**Issue:** [#2735](https://github.com/jannekbuengener/Claire_de_Binare/issues/2735)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606) (stays OPEN)  
**Builds on:** G0 contract [#2730](https://github.com/jannekbuengener/Claire_de_Binare/issues/2730) — [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)  
**Status:** **DESIGN ONLY — T3 NOT ACTIVATED**  
**LR:** NO-GO ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md))  
**Board stage:** `trade-capable` is orthogonal; not live authorization.

---

## 1. Purpose and non-goals

This document defines the **governed non-localhost SurrealDB endpoint** for
future **T3 productive audit trail** persist (`audit_observation` only). It is
the G1 deliverable in the activation ladder (§9 of the G0 contract).

**In scope (G1 design only):**

- Endpoint topology, transport security, namespace isolation, credential policy
- Config contract shape (git-safe placeholders)
- T2 → T3 field mapping and adapter boundary (design)
- HG-P prerequisites and fail-closed defaults
- Required evidence before a future G3 runtime slice

**Out of scope (explicit):**

- Runtime code, compose, infra, or workflow changes
- SQL execution against a productive endpoint
- Flipping `PERSIST_ALLOWED` (remains `False` on `main`; G3 is a separate issue)
- MCP mutation (`MUTATION_ALLOWED` remains `False`)
- Productive `agent_memory` write (T4 / G4)
- Closing parent epic #2606
- LR upgrade, Echtgeld-go, or BLUE/RED runtime mutation

**Rule:** G1 authorizes **documentation only**. T3 remains **NOT ACTIVATED**
until G2+ implementation issues with HG-P and activation evidence land.

---

## 2. T2 vs T3 comparison

| Dimension | T2 (active on `main`) | T3 (G1 design; not activated) |
| --- | --- | --- |
| Tier name | Local `audit_observation` | Productive audit trail |
| Host | `127.0.0.1:8010` only | Governed non-localhost endpoint |
| Human-GO tier | **HG-L** (local operator) | **HG-P** (productive audit) |
| Env gate | `CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT=1` | Future: `CDB_PERSIST_PRODUCTIVE_AUDIT_TRAIL=1` (name TBD at G3) |
| Mode | `audit_persist_local` | Future: `audit_persist_productive` |
| Tables written | `audit_observation` only | `audit_observation` only |
| `agent_memory` | **No** | **No** |
| Row cleanup | Run-scoped DELETE allowed | **Forbidden** (status transitions only) |
| Canon doc | [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md) | **This document** + G0 contract |
| Adapter | `memory_write_path_v1.py` + injectable SQL client | Future: `memory_write_path_productive/v1` (G3) |

Local dev sidecar semantics are unchanged. T3 must **not** reuse localhost guards
or env flags as implicit authorization.

---

## 3. Endpoint architecture

### 3.1 Topology (design default)

```text
Operator / CI runner (HG-P + env gate)
    → memory_write_path (future productive mode)
    → SurrealDB HTTP(S) /sql API
    → Governed context runtime (non-localhost)
    → Namespace / Database (§4)
    → audit_observation table only
```

**Deployment options (operator choice at provisioning — not fixed in G1):**

| Option | Description | When to prefer |
| --- | --- | --- |
| **A — Private sidecar** | SurrealDB on private network/VPN; not bound to `127.0.0.1` | Solo-maintainer lab with network controls |
| **B — Managed SurrealDB** | Vendor-hosted instance with private endpoint | Reduced ops burden; vendor SLA |
| **C — Dedicated VM/container** | Single-tenant host in operator-controlled zone | Middle ground |

**Design default for documentation:** Option A or C on a **private network**
reachable only from operator-controlled hosts (not internet-facing, not BLUE/RED
trading stack).

### 3.2 Separation from local dev and trading runtime

| System | Relationship to T3 endpoint |
| --- | --- |
| Local context sidecar (`127.0.0.1:8010`) | **Separate** — T2 only; see [`SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md) |
| BLUE/RED Docker stacks | **No coupling** — T3 endpoint is context-intelligence scoped, not trading runtime |
| Governance mirror (`governance`/`governance_mirror`) | **No reuse** — see namespace layout §4 |

### 3.3 Network exposure rules

- Endpoint hostname and port live in **secrets only**, never in git.
- Git-safe config uses placeholders: `https://surrealdb-context.example.internal:443`
- Inbound: allowlist operator runner IPs or VPN CIDR only
- Outbound from endpoint: deny by default; no public internet egress required for audit persist
- DNS must resolve to private addresses; document split-horizon if used

---

## 4. Transport security (TLS / mTLS)

| Rule | T3 productive audit (design) |
| --- | --- |
| Minimum TLS | TLS 1.2+; **prefer TLS 1.3** |
| Plaintext HTTP off-box | **Forbidden** |
| Certificate trust | Operator-managed CA or public CA with private hostname; pin trust store in client config |
| mTLS (writer path) | **Recommended** for audit-writer role — client cert required for persist |
| mTLS (reader path) | Optional TLS-only for read-only audit queries |
| Transport | HTTP(S) POST to `/sql` (aligns with existing local adapter pattern in `context_query.py`) |

**Constraint:** Current read adapters reject non-local URLs and `wss://`. A G3
implementation slice must add a **productive audit adapter** with explicit URL
allowlist (non-localhost only) — inverse of today's localhost guards.

---

## 5. Namespace and database isolation

Target layout authority: [`context-intelligence-namespace-layout.md`](context-intelligence-namespace-layout.md).

### 5.1 Options evaluated

| Option | Namespace | Database | Assessment |
| --- | --- | --- | --- |
| **A (design default)** | `cdb` | `audit_trail` | **Selected:** dedicated DB; `audit_observation` only; lowest blast radius |
| B | `cdb` | `context_intelligence` | Rejected for T3 default: couples audit rows to indexer/importer CIS data |
| C | `cdb_context_local` | `cdb_context_intel` | Rejected: local dev NS only; not productive |

### 5.2 Design default

| Element | Value |
| --- | --- |
| Namespace | `cdb` |
| Database | `audit_trail` |
| Tables allowed for T3 writer | `audit_observation` only |
| Cross-NS queries | **Forbidden** as default (namespace layout §4) |

Schema draft reference: `infrastructure/surrealdb/context_intelligence_v0.surql`
(`audit_observation` table). Productive apply/bootstrap is **out of G1 scope**.

### 5.3 Immutability (productive rows)

Align with G0 contract §3.4:

- **DELETE forbidden** on productive audit rows
- Updates limited to `status` transitions (`open` → `resolved` / `superseded` / `accepted_risk`)
- Retention minimum policy: **TBD at G3**; spec requires **no silent drop**

---

## 6. Identity, credentials, and rotation

### 6.1 Role model (design)

| Role | Permissions | Used by |
| --- | --- | --- |
| `audit_trail_writer` | CREATE/UPSERT on `audit_observation` only; no DELETE | Future productive persist path (G3) |
| `audit_trail_reader` | SELECT on `audit_observation` | Operator evidence queries, read-only audits |
| `admin` | Schema/bootstrap only | Separate maintainer GO; not used by persist path |

Separate credentials from:

- Local dev root (`SURREALDB_ENV` for `127.0.0.1:8010`)
- MCP read credentials
- Trading stack secrets

### 6.2 Secrets layout (design)

| Secret file | Purpose | Example path |
| --- | --- | --- |
| `SURREALDB_ENV` | Local T2 sidecar (unchanged) | `${SECRETS_PATH}/SURREALDB_ENV` |
| `SURREALDB_AUDIT_TRAIL_ENV` | Productive T3 writer/reader (future) | `${SECRETS_PATH}/SURREALDB_AUDIT_TRAIL_ENV` |

`SURREALDB_AUDIT_TRAIL_ENV` must contain at minimum (names illustrative):

- `SURREAL_URL` — HTTPS URL to governed endpoint (non-localhost)
- `SURREAL_NS` / `SURREAL_DB` — `cdb` / `audit_trail`
- `SURREAL_USER` / `SURREAL_PASS` — writer or reader scoped credentials
- Optional: client cert paths for mTLS

**Never** commit credentials or real hostnames to git.

### 6.3 Rotation boundaries (policy)

| Event | Action |
| --- | --- |
| Scheduled rotation | Dual-credential window; update secrets before revoking old |
| Compromise suspected | Revoke writer creds immediately; HG-P re-issue required before persist resumes |
| Rotation SLO | Document target (e.g. 90 days); **not enforced in G1** |

---

## 7. Config contract (git-safe shape)

Future example path (not created in G1 PR unless separately approved):

`infrastructure/config/surrealdb/context_audit_trail.productive.example.yaml`

Illustrative fields:

```yaml
# DESIGN REFERENCE ONLY — not activated; placeholders only
adapter: surrealdb-productive-audit
surreal_url: "https://surrealdb-context.example.internal:443"
namespace: cdb
database: audit_trail
allowed_tables:
  - audit_observation
tls:
  min_version: "1.2"
  verify_server: true
  # client_cert_path / client_key_path when mTLS enabled
url_policy:
  reject_hosts:
    - "127.0.0.1"
    - "localhost"
    - "::1"
human_go_tier_required: HG-P
```

Runtime loaders must fail-closed if URL resolves to localhost or if config file
is missing when productive mode is requested.

---

## 8. Auth, permission, and gate assumptions

| Gate | Requirement |
| --- | --- |
| Human-GO | **HG-P** token matching `GO-YYYY-MM-DD[-suffix]`; HG-L is **insufficient** |
| Gate evaluation | `evaluate_memory_write_gate()` must pass (`approved_dry_run`) before any T3 SQL |
| Module constant | `PERSIST_ALLOWED = False` until G3 issue explicitly flips it (if required for path) |
| Env gate | Explicit opt-in env flag (future G3); default off |
| Invalid GO sources | `DELIVERY_APPROVED.yaml`, `decision_event.human_go`, `context.readiness`, agent self-assertion — all **blocked** per G0 §6 |

MCP write intent remains dry-run only; T3 persist is **not** authorized via MCP
mutation in G1/G2 design.

---

## 9. Data contract — T2 → T3 field mapping

Input: gate envelope from `evaluate_memory_write_gate()` (same as T2).

Materializer baseline: [`audit_observation_from_gate.py`](../../tools/surrealdb/audit_observation_from_gate.py).

| Field | T2 (materializer today) | T3 (productive contract) | Notes |
| --- | --- | --- | --- |
| `observation_id` | Required | Required | Stable; idempotent UPSERT key |
| `observation_type` | `memory_write_gate_evaluation` | Same | Catalog §3 in observation model |
| `subject_ref` | `agent_memory:{id}` or fallback | Same | Runbook §8 convention |
| `severity` | `info` / `blocking` | Same | |
| `message` | Required | Required | No raw token |
| `evidence_refs` | List (may be empty on block) | **Non-empty on pass** | Enforce at persist layer (G3) |
| `observed_by` | e.g. `memory_write_gate/v1` | `memory_write_path_productive/v1` (future) | Versioned path id |
| `observed_at` | ISO-8601 UTC | Same | |
| `status` | `open` on create | Same | Lifecycle per observation model §5 |
| `created_at` | Set at persist | Same | |
| `gate_status` | From envelope | Same | |
| `human_go_token_present` | Boolean only | Same | **Never** raw token |
| `schema_version` | `audit-observation-from-gate/v1` | Bump at G3 if row shape changes | |
| `target_issue` | Not materialized | Required in metadata | e.g. `2606` — via `comment` JSON until schema slice |
| `git_commit_sha` | Not materialized | Required in metadata | Full SHA in evidence pack |
| `authorization_scope` | Not materialized | Required | Must match record scope |
| `run_id` / `workflow_run_id` | Not materialized | Optional | CI/operator correlation |

**Forbidden keys (both tiers):** `human_go_token`, `human_go` — enforced by
materializer and `audit_observation_row_is_redacted()`.

**Response contract (persist success):** return `observation_id`, `path_status:
audit_persisted_productive`, endpoint fingerprint (host hash, not raw URL), and
explicit `agent_memory_written: false`.

---

## 10. Fail-closed behavior matrix

Default when productive-tier gates are not satisfied: **no SQL**.

| Condition | Behavior |
| --- | --- |
| Missing HG-P token | Block; no SQL |
| HG-L token only | Block; no SQL |
| Localhost URL in config | Block; no SQL |
| Missing env opt-in flag | Block; no SQL |
| Gate `blocked_*` status | Block; no SQL |
| Wrong table in SQL | Block; no SQL |
| `agent_memory` in write intent | Block; no SQL |
| Forbidden keys in audit block | Block; materializer raises |
| MCP mutation request | Block; `MUTATION_ALLOWED=False` |
| Endpoint unreachable | Fail; no retry that bypasses gates |

No fallback to T2 localhost path when productive mode is requested.

---

## 11. Trust and evidence model

- `audit_observation` is an **audit signal**, not authorization
  ([`audit-observation-model-v1.md`](audit-observation-model-v1.md) §1).
- Productive rows support **parent #2606 criterion 6** evidence only after G3
  runtime proof — G1 design alone does not satisfy criterion 6.
- Evidence pack: use [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md) §3 with tier **T3** checked as design/spec review only until G3.

---

## 12. Required evidence before G3 runtime activation

Not satisfied by G1. Future G3 issue must prove:

- [ ] Governed endpoint provisioned; TLS verified; mTLS if declared
- [ ] `SURREALDB_AUDIT_TRAIL_ENV` in secrets path; rotation doc updated
- [ ] Productive adapter with non-localhost URL allowlist and localhost denylist
- [ ] HG-P maintainer GO recorded; issue-linked
- [ ] Gate + materializer unit tests green (extended for T3 metadata)
- [ ] Integration proof: one `audit_observation` row on governed endpoint; **no** `agent_memory` write
- [ ] Redaction proof: no raw token in logs or persisted rows
- [ ] Immutability: DELETE attempt rejected or absent from writer role
- [ ] Rollback procedure documented and exercised on non-prod
- [ ] Explicit: **LR remains NO-GO** unless changed via LR SSOT only
- [ ] Parent #2606 re-audit; criterion 6 re-evaluated with runtime evidence

`PERSIST_ALLOWED` flip, if needed for the chosen implementation, remains a **G3**
code change with separate maintainer GO — not implied by G1 or HG-P alone.

---

## 13. Test and validation expectations (future G3 slice)

**CI-safe (every PR touching the path):**

```bash
pytest tests/unit/surrealdb/test_memory_write_gate.py \
  tests/unit/surrealdb/test_memory_write_path_v1.py \
  tests/unit/surrealdb/test_audit_observation_from_gate.py \
  tests/unit/tools/mcp/test_memory_write_intent_tool.py -q
```

**New tests expected at G3:**

| Area | Expectation |
| --- | --- |
| Materializer | T3 metadata fields; forbidden-key rejection |
| URL guard | Productive adapter rejects `127.0.0.1`, `localhost`, `::1` |
| Host guard | Local adapter still rejects non-local (no regression) |
| Table scope | Mock client: only `audit_observation` written |
| Idempotency | Duplicate `observation_id` handling documented |
| Integration | Staging/governed endpoint with HG-P; **not** required CI |

---

## 14. Open risks

| Risk | Mitigation (design) |
| --- | --- |
| Namespace drift (local vs `cdb`) | Design default `cdb`/`audit_trail`; document in operator runbook |
| Schema drift (materializer vs `.surql`) | G3 schema slice or structured `comment` JSON until aligned |
| False activation via env typo | Distinct env flag name; fail-closed loader |
| Secret leakage in evidence | Runbook §5 hygiene; boolean-only token presence |
| Surface creep (MCP read of productive audit) | Separate decision; not in G1 scope |
| Retention undefined | Flag TBD at G3; no silent drop requirement locked in G0 |

---

## 15. Follow-up slices

| Gate | Issue | Scope |
| --- | --- | --- |
| **G1** | **#2735 (this doc)** | Endpoint design — **NOT ACTIVATED** |
| G2 | Future | MCP Phase 2 design — mutation guard + audit wiring spec |
| G3 | Future | Productive audit persist adapter + tests + HG-P operator proof; optional `PERSIST_ALLOWED` flip |
| G4 | Future | Productive `agent_memory` write (HG-W) |
| #2606 | Stays OPEN | Criterion 6 **PARTIAL** until T3 runtime evidence |

---

## 16. LR / Board / parent epic boundaries

| SSOT | Rule |
| --- | --- |
| LR audit status | **NO-GO** — unchanged by G1 |
| Board stage | `trade-capable` is not live authorization |
| #2606 | **NOT_CLOSURE_READY** — G1 does not close epic |
| #2730 | G0 spec CLOSED; G1 complements, does not reopen |

---

## Cross-references

| Document | Role |
| --- | --- |
| [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md) | G0 contract (T3 semantics, gates G0–G4) |
| [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md) | Operator evidence pack |
| [`memory-write-path-v1-runbook.md`](memory-write-path-v1-runbook.md) | T2 local path |
| [`audit-observation-model-v1.md`](audit-observation-model-v1.md) | Row catalog |
| [`context-intelligence-namespace-layout.md`](context-intelligence-namespace-layout.md) | Target NS layout |
| [`db-runtime-ci-proof-path-v1.md`](db-runtime-ci-proof-path-v1.md) | Proof matrix row 3 |
| [`memory-reality-slice1-audit.md`](memory-reality-slice1-audit.md) | §22.2 G1 addendum |

---

## Provenance

| Source | Role |
| --- | --- |
| GitHub #2735 | G1 design delivery issue |
| GitHub #2730 | G0 spec (CLOSED) |
| GitHub #2733 | Parent re-audit — criterion 6 PARTIAL |
| `tools/surrealdb/memory_write_gate.py` | `PERSIST_ALLOWED = False` anchor |
