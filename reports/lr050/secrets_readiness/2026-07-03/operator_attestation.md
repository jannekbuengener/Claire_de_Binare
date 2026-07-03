# LR-050 Operator Secrets & Account Readiness Attestation (#2983)

## Scope

Operator-GO slice for [#2983](https://github.com/jannekbuengener/Claire_de_Binare/issues/2983):
redacted attestation of local SSOT presence, permission scope, IP allowlist posture,
and account binding — without secret values, IPs, account IDs, or venue API calls.

## Proof window

| Field | Value (UTC) |
|-------|-------------|
| `proof_window_utc_start` | `2026-07-03T20:25:00Z` |
| `proof_window_utc_end` | `2026-07-03T20:32:05Z` |

## S1–S3 — Local SSOT and env

| Field | Attestation |
|-------|-------------|
| `ssot_path_status` | `PRESENT` |
| `ssot_path_ref` | `[REDACTED_LOCAL_SSOT]` |
| `secrets_path_env` | `SET` |

## S2 — Required secret files (names only)

Operator verified file presence via local `Test-Path` on **names** only.
Agent did **not** read secret file contents.

| Secret name | Status |
|-------------|--------|
| `REDIS_PASSWORD` | `PRESENT` |
| `POSTGRES_PASSWORD` | `PRESENT` |
| `MEXC_API_KEY.txt` | `PRESENT` |
| `MEXC_API_SECRET.txt` | `PRESENT` |
| `POSTGRES_PASSWORD_DSN` | `PRESENT` |
| `GRAFANA_PASSWORD` | `PRESENT` |
| `SMTP_USER` | `PRESENT` |
| `SMTP_PASSWORD` | `PRESENT` |
| `SMTP_FROM` | `PRESENT` |
| `ALERT_EMAIL_TO` | `PRESENT` |

## S5 — Forbidden permissions (venue dashboard, enum only)

| Permission | Status |
|------------|--------|
| `withdrawal` | `disabled` |
| `transfer` | `disabled` |
| `admin` | `disabled` |

## S6 — Trading permission scope

| Field | Value |
|-------|-------|
| `permission_scope_class` | `trade_limited` |

## S7 — IP allowlist / egress binding

| Field | Value |
|-------|-------|
| `ip_allowlist_status` | `unknown` |
| `ip_allowlist_entry_count` | `unknown` |

**Note:** Operator initially indicated `configured` but corrected to `unknown` when
entry count could not be attested without disclosing policy detail. Gate S7 remains
**not reviewed** for aggregate purposes.

## S8 — Account / channel binding

| Field | Value |
|-------|-------|
| `account_binding_status` | `verified` |
| `account_channel_ref` | `[REDACTED_VENUE_ACCOUNT_CHANNEL]` |
| `testnet_mainnet_separation` | `verified` |

## S11 — Designated key class

| Field | Value |
|-------|-------|
| `designated_key_class` | `undecided` |

Gap acknowledged pending [#2976](https://github.com/jannekbuengener/Claire_de_Binare/issues/2976);
does not substitute S7 review.

## Agent / proof boundaries

| Field | Value |
|-------|-------|
| `agent_read_credentials` | `false` |
| `exchange_api_called` | `false` |
| `lr_verdict` | `NO-GO` |
| `live_go` | `false` |
| `echtgeld_go` | `false` |

## Verification method (operator-local, redacted)

- File presence: local name-only checks under `[REDACTED_LOCAL_SSOT]`
- Permission scope and forbidden flags: venue dashboard review (no API calls, no proof orders)
- Account binding and testnet/mainnet separation: venue dashboard review (enum only)
- IP allowlist: **not conclusively reviewed** in this window (S7 `unknown`)

## Boundaries (unchanged)

- LR verdict remains **NO-GO**
- No Live-Go, no Echtgeld-Go, no trading authorization
- No secret values, IP addresses, account IDs, emails, API keys, tokens, or PII in this artifact
