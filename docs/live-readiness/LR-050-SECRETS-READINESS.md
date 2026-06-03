# LR-050 Secrets Readiness — Credential Handling for First Live-Capital Canary

- **Control:** `LR-050` (P5 Canary Echtgeld / Live-Kapital)
- **GitHub issue:** [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530)
- **Document role:** Repo-backed SSOT for secret/credential **names**, allowed stores, permission boundaries, redaction, rotation/revocation, and verification matrix (**gate definition only — not activation**)
- **Last updated:** 2026-06-04
- **Companion:** [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md), [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md), [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md), [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md)
- **Verdict authority (unchanged):** [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md)

## Safety boundaries (read first)

| Rule | Status |
|------|--------|
| Global `LR-050` verdict | **NO-GO** until separate explicit Human Approval |
| This document authorizes live trading | **No** — kein Live-Go |
| This document authorizes real-money exposure | **No** — kein Echtgeld-Go |
| Merge of PR that adds this document | **Documentation only** — ersetzt **niemals** Human Approval |
| Automatic activation / auto-live | **Forbidden** — No auto-live |
| Board stage `trade-capable` | **Not** live-capital authorization (orthogonal to LR) |
| Secret values in this document | **None** — nur Namen, Klassen, Status |
| Runtime / secret-store / GitHub-secret mutation via this document | **None** |
| Live API key validation via this document | **None** |

**Canary venue:** Nicht durch #2530 festgelegt. Venue-Audit und bevorzugter Canary-Pfad → [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) only.

---

## 1. Scope and non-goals

### In scope

- Define credential **classes** and repo-known **names** required for a future controlled live-capital/crypto canary.
- Define allowed vs forbidden storage locations, minimal permissions, redaction, rotation/revocation, and fail-closed behavior.
- Provide a **Prüfbarkeits-Matrix** with `ready` | `TBD_BLOCKER_BEFORE_LIVE` | `forbidden` per requirement.
- Hand off proof expectations to [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) (Canary Plan) and [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) (Dry-run Proof).

### Non-goals

- No reading, searching, logging, or validating real secret values.
- No changes to [`LR-AUDIT-STATUS-2026-03-05.md`](./LR-AUDIT-STATUS-2026-03-05.md), `ROADMAP.yaml`, services, core, compose, env files, GitHub Secrets, or local secret stores.
- No venue-specific permission/IP/account-binding claims until [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) delivers repo-backed venue SSOT.
- No replacement of [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) (observability/alert receiver matrix).

---

## 2. Related documents and dependencies

| Document / issue | Relationship |
|------------------|--------------|
| [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) | Planning context; §3 lists #2530 — SSOT is this file |
| [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) | Gate #4 requires this SSOT CLOSED before live-capital GO |
| [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) | Numeric limits; unrelated to secret values |
| [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) | Halt/revocation; post-incident secret rotation coupled here |
| [#2527](https://github.com/jannekbuengener/Claire_de_Binare/issues/2527) | **Canary venue**, venue permission model, passphrase, IP allowlist, account binding |
| [#2531](https://github.com/jannekbuengener/Claire_de_Binare/issues/2531) | Monitoring/alerting credentials and receiver proof |
| [#2532](https://github.com/jannekbuengener/Claire_de_Binare/issues/2532) | Canary plan — must reference credential gates below |
| [#2533](https://github.com/jannekbuengener/Claire_de_Binare/issues/2533) | Dry-run — config/auth path without secret exposure |
| [`knowledge/governance/SECRETS_POLICY.md`](../../knowledge/governance/SECRETS_POLICY.md) | Global secrets architecture |
| [`knowledge/governance/SECRET_ROTATION_POLICY.md`](../../knowledge/governance/SECRET_ROTATION_POLICY.md) | Rotation modes (`auto` / `manual`) |
| [`docs/runbooks/cdb_secrets_ssot.md`](../runbooks/cdb_secrets_ssot.md) | Local SSOT + GitHub secret sync (metadata only) |
| [`core/secrets.py`](../../core/secrets.py) | Loader — never logs values |
| [`.env.example`](../../.env.example) | ENV **names** and placeholders only |

---

## 3. Credential classes (generic + repo-known names)

### 3.1 Generic exchange/broker classes (canary — venue TBD)

| Class | Purpose | Canary status |
|-------|---------|---------------|
| Exchange API Key | Authenticate API requests | Name + permission scope → `TBD_BLOCKER_BEFORE_LIVE` until #2527 |
| Exchange API Secret | Sign/authenticate requests | Same |
| Optional Passphrase | Required by some venues | `TBD_BLOCKER_BEFORE_LIVE` until #2527 |
| IP allowlist / egress binding | Restrict key to known IPs | `TBD_BLOCKER_BEFORE_LIVE` until #2527 |
| Account / subaccount binding | Tie key to specific account | `TBD_BLOCKER_BEFORE_LIVE` until #2527 |
| Read-only credentials | Discovery, balances, market metadata without trade | Allowed **only** for pre-GO discovery per operator policy; not a live-capital GO substitute |
| Trading credentials | Place/cancel orders on approved canary scope | **Forbidden** until valid Human Approval §4 + #2532 scope |
| Monitoring / alerting credentials | SMTP, webhook, notification targets | Partially repo-named (CI); live receiver proof → #2531 |

### 3.2 Repo-found names (not a canary-venue claim)

These names appear in repo config/docs as **existing integration identifiers**. They do **not** designate the LR-050 canary venue (see #2527).

| Name / file (under `SECRETS_PATH`) | ENV fallback (if any) | Notes |
|-----------------------------------|----------------------|--------|
| `MEXC_API_KEY.txt` | `MEXC_API_KEY` | Referenced in compose / `.env.example` |
| `MEXC_API_SECRET.txt` | `MEXC_API_SECRET` | Same |
| `MEXC_TRADE_API_KEY.txt` | — | Listed in [`knowledge/context_build/GITHUB_SECRETS_SETUP.md`](../../knowledge/context_build/GITHUB_SECRETS_SETUP.md) |
| `MEXC_TRADE_API_SECRET.txt` | — | Same; separate trade key file naming in docs |

**Stack / infra (not exchange canary keys):**

| Name | Source |
|------|--------|
| `REDIS_PASSWORD` | [`tools/secrets/secrets.manifest.json`](../../tools/secrets/secrets.manifest.json), compose |
| `POSTGRES_PASSWORD`, `POSTGRES_PASSWORD_DSN` | Same |
| `GRAFANA_ADMIN_PASSWORD` (manual rotation) | Same |
| `SURREALDB_ENV` | [`docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md`](../runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md) |

**CI / GitHub Actions (derived from local SSOT, not canary runtime SSOT):**

| GitHub secret name (examples) | Purpose |
|------------------------------|---------|
| `MEXC_API_KEY`, `MEXC_API_SECRET` | E2E workflows — ephemeral `.ci-secrets/` |
| `REDIS_PASSWORD`, `POSTGRES_PASSWORD`, `GRAFANA_PASSWORD` | CI stack |
| `SMTP_*`, `ALERT_EMAIL_TO` | Alert path in E2E |
| `CDB_GH_APP_*`, `ADD_TO_PROJECT_PAT` | Control plane — [`docs/runbooks/cdb_secrets_ssot.md`](../runbooks/cdb_secrets_ssot.md) |

**Not in tracked rotation manifest:** `tools/secrets/secrets.manifest.json` on `main` lists Redis/Postgres/Grafana only — exchange file rotation policy for canary keys remains `TBD_BLOCKER_BEFORE_LIVE` until venue SSOT (#2527) and manifest alignment.

---

## 4. Allowed storage locations

| Location | Role | Canary note |
|----------|------|-------------|
| Local SSOT directory | `~/Documents/.secrets/.cdb/` (Windows: `%USERPROFILE%\Documents\.secrets\.cdb\`) | **Primary** operator store per [`SECRETS_POLICY.md`](../../knowledge/governance/SECRETS_POLICY.md) |
| `SECRETS_PATH` | Points compose/Docker to file-based secrets | Required; fail-closed if unset in compose.blue/red |
| Docker file secrets | `${SECRETS_PATH}/<NAME>` mounted as `/run/secrets/*` | Runtime injection; no values in repo |
| [`core/secrets.py`](../../core/secrets.py) | `/run/secrets/` → env fallback | Never logs values |
| GitHub Repository Secrets | **CI/automation derived copies** only | Sync from local SSOT via `scripts/secrets/sync_cdb_secrets.ps1` (metadata-only output) |
| CI ephemeral dir | `${{ github.workspace }}/.ci-secrets` in workflows | Not operator canary SSOT |
| [`.env.example`](../../.env.example) | **Names and placeholders only** | Tracked; no real values |

---

## 5. Forbidden storage locations

| Location | Status |
|----------|--------|
| Git repository (tracked files, including docs/issues) | **forbidden** |
| GitHub Issues / PR bodies / comments | **forbidden** |
| Application logs / CI logs / debug output | **forbidden** |
| Build artifacts / workflow uploads / evidence packs | **forbidden** (values); names/status OK |
| Screenshots / screen shares | **forbidden** |
| Chat / agent session output | **forbidden** |
| Legacy repo paths (`.cdb_local/.secrets/`, repo `.secrets/`) | **forbidden** — legacy per SECRETS_POLICY |

Fail-closed: if a required credential cannot be loaded without exposing it in a forbidden surface, **halt** live-capital work and keep **NO-GO**.

---

## 6. Minimal permissions (LR-050 canary policy)

| Permission | Status | Notes |
|------------|--------|-------|
| Read-only (market/account discovery) | Allowed for **pre-GO** discovery only; scope from #2527 | Does not imply live-capital GO |
| Trading (place/cancel on approved symbols) | **Forbidden** until valid [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §4 GO + #2532 canary scope | Keys must be provisioned with minimum scope |
| Withdrawal | **forbidden** | Also stated in Human Approval §7 |
| Transfer / subaccount-admin | **forbidden** | |
| Key management / admin API | **forbidden** | |
| Venue permission model (bitmask/scopes UI) | `TBD_BLOCKER_BEFORE_LIVE` | #2527 |

---

## 7. IP allowlisting and account binding

| Requirement | allowed_status | Blocker |
|-------------|----------------|---------|
| Canary venue IP allowlist documented | `TBD_BLOCKER_BEFORE_LIVE` | #2527 |
| Egress IP known and registered at venue | `TBD_BLOCKER_BEFORE_LIVE` | #2527 |
| Account/subaccount binding documented | `TBD_BLOCKER_BEFORE_LIVE` | #2527 |

**Policy:** No live-capital canary without a repo-backed, operator-reviewed IP/access policy from #2527. Until then: fail-closed → **NO-GO**.

---

## 8. Rotation and revocation

### 8.1 When to rotate

| Trigger | Action |
|---------|--------|
| Scheduled | Auto secrets per [`SECRET_ROTATION_POLICY.md`](../../knowledge/governance/SECRET_ROTATION_POLICY.md) (`rotate apply` for `auto` entries in manifest) |
| Suspected leak | Immediate revoke at venue + rotate all affected names; incident record without values |
| Post-halt / Kill Switch / REVOKED | Rotate trading credentials before any resume consideration |
| Clone from repo / new operator machine | Rotate stack secrets per SECRETS_POLICY history warning |
| Human Approval withdrawn | Treat trading keys as compromised until rotated — [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) §9 |

### 8.2 How to revoke (no values in evidence)

1. Disable/delete API key at venue dashboard (operator — #2527 procedure).
2. Remove or overwrite files under local SSOT (operator local action — not documented here).
3. If CI keys affected: `sync_cdb_secrets.ps1` metadata run + GitHub secret rotation from SSOT (separate Runtime-GO).
4. Document evidence as: `REVOKED`, `ROTATED`, `PRESENT`, `ABSENT` — **never** paste values.

### 8.3 After halt or incident

- Global verdict remains **NO-GO** until Human GO still valid ([`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) §7).
- Trading credentials assumed untrusted until rotated.
- Re-check §6 permissions at venue before any new GO.

### 8.4 Before resume (checklist)

| # | Check |
|---|--------|
| 1 | Kill Switch / halt cleared per kill-switch runbook |
| 2 | Human GO still valid (not REVOKED) |
| 3 | Trading keys rotated if halt involved credential exposure risk |
| 4 | #2527 IP/account policy satisfied |
| 5 | #2531 monitoring gates satisfied |
| 6 | #2533 dry-run proof current |

---

## 9. Redaction

### 9.1 Patterns that must never appear in logs / issues / PRs / artifacts

Non-exhaustive (aligned with [`.github/workflows/docs-hub-guard.yml`](../../.github/workflows/docs-hub-guard.yml) and gitleaks posture):

- `api_key`, `api_secret`, `secret`, `token`, `password`, `private_key`
- PEM blocks: `BEGIN RSA PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY`
- GitHub tokens: `ghp_`, `github_pat_`
- AWS keys: `AKIA…`
- Slack tokens: `xoxb-`, `xoxp-`, etc.
- Raw contents of `~/Documents/.secrets/.cdb/*` or `.ci-secrets/*`

### 9.2 Evidence without value disclosure

| Allowed in evidence | Forbidden |
|---------------------|-----------|
| Secret **name** (e.g. `MEXC_API_KEY`) | Secret **value** |
| `PRESENT` / `ABSENT` / `SET` / `INVALID` | Partial key material |
| File path to SSOT dir (no file dump) | `cat` of secret files in PR logs |
| `SECRETS_PATH` set/unset | Export of `.env` with values |
| Sync result `OK`/`FAIL` per name | `gh secret set` echo of payload |

### 9.3 What counts as a secret leak

- Any credential value in git history, PR, issue, log, artifact, or agent output.
- Screenshots showing exchange API settings with visible keys.
- CI logs printing env vars that hold secrets (workflows must use masked secrets).
- False positives in docs-hub-guard still require human review — fail-closed for merge if unmitigated.

---

## 10. Prüfbarkeits-Matrix

**Legend — `allowed_status`:** `ready` | `TBD_BLOCKER_BEFORE_LIVE` | `forbidden`

| requirement | source/mechanism | allowed_status | verification method | requires_secret_value | runtime action required | blocker status | fail-closed behavior |
|-------------|------------------|----------------|---------------------|----------------------|-------------------------|----------------|----------------------|
| No secret values in repo | `gitleaks.yml`; SECRETS_POLICY | ready | CI gitleaks; PR diff review for value-like blobs | no | no | none | Merge blocked on detected leak |
| Local SSOT path defined | `SECRETS_POLICY.md`; `cdb_secrets_ssot.md` | ready | Doc review; operator attests path exists (no read) | no | no | none | Missing SSOT → no live prep |
| `SECRETS_PATH` required in compose | `compose.blue.yml` `:?SECRETS_PATH` | ready | Read compose; doctor/runbook checks | no | yes (stack bring-up) | OPEN until #2533 | Unset → compose fails |
| Secret loader never logs values | `core/secrets.py` | ready | Code review / unit tests | no | no | none | Missing secret → empty string + warning (non-value) |
| `.env.example` names only | `.env.example` tracked | ready | Diff review; no literal keys | no | no | none | Real `.env` must stay gitignored |
| Forbidden surfaces documented | This §5 + SECRETS_POLICY | ready | PR/issue template review | no | no | none | Leak → revoke + NO-GO |
| Withdrawal permission | LR-050 policy §6 | forbidden | Venue dashboard policy (#2527) | no | yes (venue UI) | #2527 | Withdrawal-capable key → do not use |
| Transfer / subaccount-admin | LR-050 policy §6 | forbidden | #2527 venue audit | no | yes | #2527 | Same |
| Key-management / admin API | LR-050 policy §6 | forbidden | #2527 venue audit | no | yes | #2527 | Same |
| Trading permission timing | `LR-050-HUMAN-APPROVAL.md` §4 | ready | Checklist gate #4 + GO block | no | no | until Human GO | Trade keys before GO → forbidden |
| Read-only vs trade key separation | `.env.example` MEXC_* + TRADE_* files | TBD_BLOCKER_BEFORE_LIVE | #2527 defines which set for canary | no | yes | #2527 | Wrong key class → NO-GO |
| Canary venue + permission model | #2527 | TBD_BLOCKER_BEFORE_LIVE | Venue audit SSOT when closed | no | no | #2527 OPEN | No venue claim from #2530 |
| Passphrase requirement | #2527 | TBD_BLOCKER_BEFORE_LIVE | Venue audit | no | no | #2527 OPEN | Assume required until disproven |
| IP allowlist / egress policy | #2527 | TBD_BLOCKER_BEFORE_LIVE | Venue + infra runbook | no | yes | #2527 OPEN | No live canary without policy |
| Account binding | #2527 | TBD_BLOCKER_BEFORE_LIVE | Venue audit | no | yes | #2527 OPEN | Unbound key → NO-GO |
| Exchange keys in rotation manifest | `tools/secrets/secrets.manifest.json` | TBD_BLOCKER_BEFORE_LIVE | Manifest lists infra only today | no | no | manifest gap | Manual rotation until aligned |
| GitHub secrets = CI derivative | `cdb_secrets_ssot.md`; sync script | ready | Dry-run `sync_cdb_secrets.ps1 -DryRun` (metadata) | no | yes (separate GO) | none | Never author canary keys only in GHA |
| CI ephemeral secrets dir | `e2e-tests.yml` `.ci-secrets` | ready | Workflow review | no | yes (CI only) | none | Not operator canary SSOT |
| Redaction in changed docs | `docs-hub-guard.yml` patterns | ready | PR CI / manual rg on diff | no | no | none | Pattern hit → fix or justify |
| Alert/SMTP credential names | `GITHUB_SECRETS_SETUP.md`; e2e workflows | ready | Name inventory; receiver proof → #2531 | no | yes (#2531) | #2531 OPEN | No live GO without alert path |
| Auth path dry-run (no value output) | #2533 | TBD_BLOCKER_BEFORE_LIVE | Dry-run evidence issue | no | yes (#2533) | #2533 OPEN | Auth proof must not log keys |
| Post-halt key rotation | This §8 + kill-switch §7 | ready | Operator checklist + incident template | no | yes | post-incident | Resume without rotate → forbidden |

---

## 11. Handoff to #2532 (Canary Plan)

The canary plan **must** reference (not duplicate values):

| Topic | SSOT section |
|-------|----------------|
| Credential class list (read-only vs trading) | §3, §6 |
| Forbidden permissions | §6 |
| Storage / no-repo rule | §4, §5 |
| IP/account blockers | §7 |
| Rotation on REVOKED/halt | §8 |
| Venue-specific names | **Only** from #2527 — not MEXC-as-canary from this doc |

Plan must state: **no auto-live**, **no orders** via planning issue, Human Approval required before trading credentials are used.

---

## 12. Handoff to #2533 (Dry-run Proof)

| Check | When | requires_secret_value |
|-------|------|----------------------|
| `SECRETS_PATH` / compose secret file **names** resolve | Dry-run | no |
| `read_secret` / config loader returns non-error path with **mock or absent** key | Dry-run | no |
| Logs contain no `MEXC_API_KEY=` value patterns | Dry-run | no |
| `real_money=false` / `dry_run=true` / `MOCK_TRADING` attested | Dry-run | no |
| Live venue auth success | **Only after** Human GO + explicit Runtime-GO | yes (operator — out of #2533 doc scope) |

Fail-closed: dry-run proof **must not** print secrets; auth “success” is not required for #2533 closure if policy forbids live validation.

---

## 13. Acceptance (#2530)

| Criterion | Met by |
|-----------|--------|
| Secret requirements documented | §3–§9 |
| No secrets in repo/issues/logs policy | §5, §9 |
| Trading permissions minimal | §6 |
| Withdrawal forbidden | §6 |
| Matrix with TBD for #2527 blockers | §10 |
| Crosslinks to Decision Pack / Human Approval / Risk / Kill-Switch | §2 + sibling docs |

Closing [#2530](https://github.com/jannekbuengener/Claire_de_Binare/issues/2530) via PR delivers **gate definition only**. It does **not** grant live-capital GO, clear `LR-050`, or authorize real-money exposure.

---

## Related documents

- [`README.md`](./README.md) — live-readiness index
- [`LR-050-DECISION-PACK.md`](./LR-050-DECISION-PACK.md) — [#2526](https://github.com/jannekbuengener/Claire_de_Binare/issues/2526)
- [`LR-050-HUMAN-APPROVAL.md`](./LR-050-HUMAN-APPROVAL.md) — [#2534](https://github.com/jannekbuengener/Claire_de_Binare/issues/2534)
- [`LR-050-RISK-LIMITS.md`](./LR-050-RISK-LIMITS.md) — [#2528](https://github.com/jannekbuengener/Claire_de_Binare/issues/2528)
- [`LR-050-KILL-SWITCH-RUNBOOK.md`](./LR-050-KILL-SWITCH-RUNBOOK.md) — [#2529](https://github.com/jannekbuengener/Claire_de_Binare/issues/2529)
