# LR-050 Secrets & Account Readiness Preflight — Operator Attestation (#2983)

## Purpose

Read-only preflight for [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983):
define how secret-file presence, permission scope, IP allowlist, and account binding
can be verified **safely** and **redacted**, without Live-Go, venue API calls, or secret
values in repo artifacts.

This document is a **Preflight / Evidence-Design slice only**. It does **not** read
credentials, start Docker, call exchanges, or close #2983.

## Scope

In scope:

- Repo-backed inventory of required secret **names**, allowed verification tiers, and
  fail-closed gates.
- Safe operator checklist, redaction rules, attestation schema, and evidence format for a
  future **Operator-GO** slice.
- Preflight decision for #2983.

Out of scope:

- No reading of files under `SECRETS_PATH`, `~/Documents/.secrets/.cdb/`, or `.env`.
- No venue/exchange REST/WebSocket/API-key validation.
- No Docker recreate, stack start, or runtime restart.
- No Live-Go, Echtgeld-Go, LR status change, or #2983 closure.

## Control State

| Surface | State |
|---|---|
| LR-050 verdict | **NO-GO** ([`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)) |
| Blocker row | Secret / permission / IP / account-binding readiness — [`LR-050-FINAL-RECONCILE.md`](./LR-050-FINAL-RECONCILE.md) §3 |
| Refresh matrix | [`LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md`](./LR-050-BLOCKER-REFRESH-MATRIX-2026-07-03.md) row 7 → #2983 **OPEN** |
| Gate SSOT | [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) §3–§10 |
| Venue names SSOT | [`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) §5 (names only) |
| Upstream evidence patterns | #2978 dry-run, #2981 receiver, #2984 kill-switch — attestation/redaction only |
| Preflight date | 2026-07-03 |
| Repo anchor | `origin/main` @ preflight session |

---

## Preflight Decision

| Field | Value |
|---|---|
| **Decision (preflight)** | **`BLOCKED_NEEDS_OPERATOR_ATTESTATION`** |
| **Decision (post-doc merge)** | **`READY_FOR_OPERATOR_SECRETS_ATTESTATION`** — checklist + evidence format defined |
| Operator-GO required for proof? | **Yes** — agents cannot verify permission scope, IP allowlist, or account binding |
| Exchange API allowed in proof? | **No** — operator venue dashboard attestation only |
| #2983 status after preflight PR | **Stays OPEN** — no operator evidence pack on `main` yet |

### Why not `PASS`

No redacted operator attestation exists for permission scope, IP allowlist, or
testnet/mainnet account binding. Gate matrix #2530 is `docs_only`.

### Why not `INCONCLUSIVE`

Repo evidence is sufficient to name required secret files, verification tiers, redaction
rules, and a concrete operator path. Gaps are specific and actionable.

---

## Verification Tiers (mandatory)

| Tier | Actor | Allowed | Forbidden |
|---|---|---|---|
| **A — Agent / repo** | Agent or CI | Doc review; compose/manifest name inventory; `git ls-files`; PR diff pattern scan; cite `gitleaks` posture | Read SSOT secret files; `cat`/`Get-Content` of credentials; venue API; publish values |
| **B — Operator local** | Human operator | `Test-Path` per secret **name**; attest `PRESENT`/`ABSENT`; venue dashboard permission review | Paste keys, IPs, account IDs, or emails into repo/GitHub |
| **C — Operator evidence commit** | Operator + scoped docs commit | Redacted pack under `docs/evidence/reports/lr050/secrets_readiness/YYYY-MM-DD/` | Any tier-A forbidden action in evidence artifacts |

**Fail-closed:** If a check requires tier B but only tier A was performed → gate
**INCONCLUSIVE**, not PASS.

---

## Required Secret Names (repo-backed inventory)

Cross-reference: [`compose.blue.yml`](../../infrastructure/compose/compose.blue.yml),
[`compose.red.yml`](../../infrastructure/compose/compose.red.yml),
[`SECRETS_POLICY.md`](../../knowledge/governance/SECRETS_POLICY.md),
[`tools/secrets/secrets.manifest.json`](../../tools/secrets/secrets.manifest.json).

### BLUE stack (trading core)

| Secret file (under `SECRETS_PATH`) | Compose mount | Rotation manifest |
|---|---|---|
| `REDIS_PASSWORD` | yes | yes (`auto`) |
| `POSTGRES_PASSWORD` | yes | yes (`auto`) |
| `MEXC_API_KEY.txt` | yes | **no** (manual / venue policy) |
| `MEXC_API_SECRET.txt` | yes | **no** (manual / venue policy) |

### RED stack (monitoring / alerts)

| Secret file (under `SECRETS_PATH`) | Compose mount | Rotation manifest |
|---|---|---|
| `REDIS_PASSWORD` | yes | yes |
| `POSTGRES_PASSWORD` | yes | yes |
| `POSTGRES_PASSWORD_DSN` | yes | yes |
| `GRAFANA_PASSWORD` | yes | yes (`GRAFANA_ADMIN_PASSWORD` manual in manifest) |
| `SMTP_USER` | yes | no |
| `SMTP_PASSWORD` | yes | no |
| `SMTP_FROM` | yes | no |
| `ALERT_EMAIL_TO` | yes | no |

### Documented but not loaded on active execution path today

| Name | Source | Note |
|---|---|---|
| `MEXC_TRADE_API_KEY.txt` | [`.env.example`](../../.env.example) | Separate trade-key naming; canary key class **TBD** (#2976) |
| `MEXC_TRADE_API_SECRET.txt` | `.env.example` | Same |

**Manifest gap:** [`tools/secrets/secrets.manifest.json`](../../tools/secrets/secrets.manifest.json)
lists infra secrets only — exchange file rotation remains operator-manual until aligned
([`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) §10).

---

## Prüfmatrix (PASS / FAIL / INCONCLUSIVE)

**Legend — owner:** `Agent` = tier A only; `Operator` = tier B/C.
**Gate:** `PASS` | `FAIL` | `INCONCLUSIVE`.

| ID | Requirement | Owner | Agent-safe method | Operator method | PASS | FAIL | INCONCLUSIVE |
|---|---|---|---|---|---|---|---|
| S1 | Local SSOT directory exists | Operator | Doc ref [`SECRETS_POLICY.md`](../../knowledge/governance/SECRETS_POLICY.md) | `Test-Path` on SSOT dir — attest `PRESENT`/`ABSENT` only; path as `[REDACTED_LOCAL_SSOT]` in evidence | `PRESENT` | `ABSENT` | Not run |
| S2 | Required stack secret files by **name** | Operator | Cross-check compose tables above | Per-name `Test-Path`; table name → `PRESENT`/`ABSENT` | All required for intended stack scope `PRESENT` | Any required `ABSENT` | Partial |
| S3 | `SECRETS_PATH` env set for stack ops | Operator | Compose requires `:?SECRETS_PATH` | Operator attests `SET`/`UNSET` — no path dump if sensitive | `SET` | `UNSET` | Unknown |
| S4 | No secret **values** in repo / PR artifacts | Agent | `git ls-files` excludes external SSOT; PR diff scan per [`docs-hub-guard.yml`](../../.github/workflows/docs-hub-guard.yml) patterns; CI `gitleaks` posture | N/A | No unmitigated value-like hits in changed files | Value leak in artifact | Scan skipped |
| S5 | Forbidden permissions off (withdrawal / transfer / admin) | Operator | Policy [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) §6 | Venue dashboard — attest each `disabled`/`enabled` (must be **disabled**) | All forbidden **disabled** | Any forbidden **enabled** | Not reviewed |
| S6 | Trading permission scope minimal | Operator | Policy §6 | Attest class: `read_only` / `trade_limited` / `excessive` — no key material | Matches intended canary scope (#2976) | `excessive` or withdrawal-capable | Not reviewed |
| S7 | IP allowlist / egress binding | Operator | No repo SSOT for egress IP ([`LR-050-VENUE-AUDIT.md`](./LR-050-VENUE-AUDIT.md) §5.2) | Attest `configured` / `not_configured` / `not_required`; optional integer `entry_count` only — **no IP literals** | Policy satisfied | Required but missing | Unknown |
| S8 | Account / subaccount binding | Operator | Names in venue audit §5 | Attest `verified` / `not_verified`; channel `[REDACTED_VENUE_ACCOUNT_CHANNEL]`; testnet/mainnet separation `verified` / `not_verified` | Separation verified | Unbound or shared key | Not reviewed |
| S9 | Agent did not read credentials | Agent | Session boundary statement in evidence template | Operator confirms agent had no SSOT file access | `agent_read_credentials: false` | Agent read files | N/A |
| S10 | Exchange API not used for this proof | Both | No HTTP to venue in agent scope | Operator uses dashboard only — no proof orders / auth calls | `exchange_api_called: false` | Live auth or order proof in pack | Ambiguous |
| S11 | Read-only vs trade key separation | Operator | `.env.example` TRADE_* vs compose mounts | Attest designated key class + matching files `PRESENT` | Documented + consistent | Wrong class for intent | Undecided (#2976) |
| S12 | Manifest / rotation alignment | Agent | Read [`tools/secrets/secrets.manifest.json`](../../tools/secrets/secrets.manifest.json) | Operator notes exchange keys manual until manifest gap closed | Gap acknowledged in evidence | False auto-rotation claim for MEXC | N/A |

### Aggregate gate (#2983 execution slice — not this preflight PR)

| Result | Condition |
|---|---|
| **PASS** | S1–S3 PASS; S4 PASS; S5 all forbidden disabled; S6–S8 PASS; S9–S10 PASS; redacted pack on `main` |
| **FAIL** | S4 FAIL; any S5 forbidden enabled; secret value in any artifact |
| **INCONCLUSIVE** | Operator attestation missing; S7 or S8 not reviewed; partial S2 |

Closing [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983) requires
aggregate **PASS** with committed evidence — **not** preflight doc merge alone.

---

## Operator Attestation Schema

**Target directory (execution):** `docs/evidence/reports/lr050/secrets_readiness/YYYY-MM-DD/`

**Files:**

| File | Content |
|---|---|
| `manifest.json` | Structured metadata (schema below) |
| `operator_attestation.md` | Human-readable attestation (enum fields only) |
| `redaction_review.md` | Tier-A/B boundary + scan result (no values) |
| `summary.md` | PASS/FAIL/INCONCLUSIVE + explicit NO-GO statement |

### `operator_attestation.md` — required fields

| Field | Allowed values / format |
|---|---|
| `proof_window_utc_start` / `proof_window_utc_end` | ISO-8601 UTC |
| `ssot_path_status` | `PRESENT` / `ABSENT` |
| `ssot_path_ref` | `[REDACTED_LOCAL_SSOT]` only |
| `secrets_path_env` | `SET` / `UNSET` |
| `required_files` | Table: secret **name** → `PRESENT` / `ABSENT` |
| `permission_scope_class` | `read_only` / `trade_limited` / `excessive` |
| `forbidden_permissions.withdrawal` | `disabled` / `enabled` (must be disabled) |
| `forbidden_permissions.transfer` | `disabled` / `enabled` |
| `forbidden_permissions.admin` | `disabled` / `enabled` |
| `ip_allowlist_status` | `configured` / `not_configured` / `not_required` |
| `ip_allowlist_entry_count` | non-negative integer only (optional) |
| `account_binding_status` | `verified` / `not_verified` |
| `account_channel_ref` | `[REDACTED_VENUE_ACCOUNT_CHANNEL]` |
| `testnet_mainnet_separation` | `verified` / `not_verified` |
| `designated_key_class` | `read_only` / `trade` / `undecided` |
| `agent_read_credentials` | **false** (mandatory for agent-delivered slices) |
| `exchange_api_called` | **false** (mandatory for this gate) |
| `lr_verdict` | **NO-GO** (unchanged) |
| `live_go` / `echtgeld_go` | **false** |

### `manifest.json` — minimum schema

```json
{
  "proof_type": "lr050_secrets_account_readiness",
  "issue": "2983",
  "lr_verdict_at_proof": "NO-GO",
  "live_go": false,
  "echtgeld_go": false,
  "proof_ts_utc": "2026-07-03T00:00:00Z",
  "ssot_path_status": "PRESENT",
  "secrets_path_env": "SET",
  "ssot_files": {
    "REDIS_PASSWORD": "PRESENT",
    "POSTGRES_PASSWORD": "PRESENT",
    "MEXC_API_KEY.txt": "PRESENT",
    "MEXC_API_SECRET.txt": "PRESENT"
  },
  "permission_scope_class": "trade_limited",
  "forbidden_permissions": {
    "withdrawal": "disabled",
    "transfer": "disabled",
    "admin": "disabled"
  },
  "ip_allowlist_status": "configured",
  "ip_allowlist_entry_count": 0,
  "account_binding_status": "verified",
  "testnet_mainnet_separation": "verified",
  "designated_key_class": "undecided",
  "agent_read_credentials": false,
  "exchange_api_called": false,
  "aggregate_gate": "PASS",
  "redaction_policy": "LR-050-SECRETS-READINESS.md §9 + LR-050-SECRETS-ACCOUNT-READINESS-PREFLIGHT-2026-07-03.md",
  "notes": "LR-050 readiness attestation only. Does not clear LR-050 or authorize live capital."
}
```

Replace example timestamps and enum values with operator-observed facts. **Never** store
IP addresses, API key material, account IDs, or email addresses in JSON values.

---

## Redaction Rules (mandatory)

Consolidated from [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) §9,
[`.github/workflows/docs-hub-guard.yml`](../../.github/workflows/docs-hub-guard.yml), and
[`docs/evidence/reports/lr050/runtime_dry_run/2026-06-04/redaction_report.md`](../evidence/reports/lr050/runtime_dry_run/2026-06-04/redaction_report.md).

| Field | In repo evidence? |
|---|---|
| Secret **name** (e.g. `MEXC_API_KEY.txt`) | **Yes** |
| `PRESENT` / `ABSENT` / `SET` / `DISABLED` / permission **class** | **Yes** |
| Integer `ip_allowlist_entry_count` | **Yes** (count only) |
| UTC timestamps, proof slice label | **Yes** |
| Operator attestation (no PII) | **Yes** |
| Secret **value**, partial key material | **No** |
| IP addresses (v4/v6) | **No** — use `configured` + count or `[REDACTED_EGRESS_POLICY]` |
| Account IDs, subaccount names, emails | **No** — use `[REDACTED_VENUE_ACCOUNT_CHANNEL]` |
| Full SSOT path if sensitive | **No** — use `[REDACTED_LOCAL_SSOT]` |
| DSN passwords, SMTP credentials | **No** |
| PEM blocks; tokens `ghp_`, `github_pat_`, `AKIA`, `xoxb-` | **No** |
| Venue dashboard screenshots with visible keys/IPs | **No** — hash redacted copy offline or omit |

**False positives:** Literal identifiers such as `MEXC_API_KEY` in docs/code are names,
not leaks. Values adjacent to `=` or resembling key material require HOLD until redacted.

**HOLD rule:** If redaction certainty is missing → **do not commit** evidence; mark gate
**INCONCLUSIVE** and fix before #2983 closure consideration.

---

## Recommended Operator Path (after preflight merge)

### Step 0 — Planning (before Operator-GO)

1. Confirm canary key class with #2976 context (`read_only` vs `trade` file set).
2. Read [`LR-050-SECRETS-READINESS.md`](./LR-050-SECRETS-READINESS.md) §6 forbidden
   permissions — withdrawal must stay **disabled** on any future canary key.
3. Coordinate with #2979 venue slice for endpoint semantics; #2983 proof is **permission /
   binding / SSOT presence**, not REST/WS verification.

### Step 1 — Operator-GO preconditions

- Explicit Operator-GO for **attestation-only** slice (no stack recreate required).
- Operator performs tier-B checks locally; agent performs tier-A repo checks only.
- LR remains **NO-GO** throughout.

### Step 2 — Operator executes checklist S1–S8

- File presence via `Test-Path` on **names** only (PowerShell example — operator-local,
  not logged to repo):

```powershell
# Operator-local only — do not paste output containing paths/values into GitHub
$names = @(
  'REDIS_PASSWORD','POSTGRES_PASSWORD','MEXC_API_KEY.txt','MEXC_API_SECRET.txt',
  'SMTP_USER','SMTP_PASSWORD','SMTP_FROM','ALERT_EMAIL_TO','GRAFANA_PASSWORD'
)
# foreach ($n in $names) { Test-Path (Join-Path $env:SECRETS_PATH $n) }
```

- Venue dashboard: confirm permission scope and forbidden flags — attest enums only.
- IP allowlist: attest status + optional count — **no IP strings** in evidence.

### Step 3 — Agent/repo tier-A (optional companion PR)

- Redaction review on evidence pack before merge.
- `git diff --check`; docs-hub-guard-style pattern scan on new files only.

### Step 4 — Commit evidence + #2983 comment

- Post summary on #2983 linking `docs/evidence/reports/lr050/secrets_readiness/YYYY-MM-DD/`.
- Close #2983 only when aggregate gate **PASS** and acceptance criteria met.

---

## Relationship to sibling gates

| Issue | Relationship |
|---|---|
| [#2978](https://github.com/jannekbuengener/Claire_de_Binare/issues/2978) | Runtime dry-run proved stack path without agent credential reads — precedent for S9/S10 |
| [#2981](https://github.com/jannekbuengener/Claire_de_Binare/issues/2981) | SMTP secret **names** verified operator-local for receiver proof; same redaction class |
| [#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984) | Kill-switch drill independent; does not substitute S5–S8 |
| [#2979](https://github.com/jannekbuengener/Claire_de_Binare/issues/2979) | Venue endpoint semantics — complements but does not replace IP/account attestation |
| [#2976](https://github.com/jannekbuengener/Claire_de_Binare/issues/2976) | Canary caps / key class selection — S11 may stay `undecided` until resolved |

---

## Validation (this preflight slice)

```powershell
git fetch origin --prune
git status -sb
git rev-parse origin/main
gh issue view 2983 2976 2979 2985 2978 2981 2984
rg "secret|credential|allowlist|account|IP|MEXC|Binance|LR-050|2983" docs infrastructure .github
git diff --check
```

Content review:

- No SSOT secret files read in this slice.
- No venue/exchange API calls.
- No Docker/runtime mutation.
- No Live-Go / Echtgeld-Go language.
- #2983 remains **OPEN** after preflight doc merge.

---

## Document Metadata

| Field | Value |
|---|---|
| Issue | [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983) |
| Refs | [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530), [#2977](https://github.com/jannekbuengener/Claire_de_Binare/issues/2977), [#2978](https://github.com/jannekbuengener/Claire_de_Binare/issues/2978), [#2981](https://github.com/jannekbuengener/Claire_de_Binare/issues/2981), [#2984](https://github.com/jannekbuengener/Claire_de_Binare/issues/2984), [#2976](https://github.com/jannekbuengener/Claire_de_Binare/issues/2976), [#2979](https://github.com/jannekbuengener/Claire_de_Binare/issues/2979), [#2985](https://github.com/jannekbuengener/Claire_de_Binare/issues/2985) |
| Status target | `DONE_LR050_SECRETS_PREFLIGHT_2983` |
| LR verdict | **NO-GO** (unchanged) |
| Preflight date | 2026-07-03 |
