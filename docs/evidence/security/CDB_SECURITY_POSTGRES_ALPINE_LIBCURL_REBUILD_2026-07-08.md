# Postgres 18.4-alpine Digest Refresh — libcurl CVE Cluster

**Stand:** 2026-07-08 (UTC+2)  
**Probe:** POSTGRES_ALPINE_REBUILD_PROBE  
**Parent tracker:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Cluster tracker:** [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933)  
**Scope guard:** Digest-only refresh. No alert dismissals. No runtime start. LR remains **NO-GO**.

---

## Executive summary

| Item | Value |
|------|-------|
| Image tag | `postgres:18.4-alpine` (unchanged) |
| Old index digest | `sha256:1b1689b20d16a014a3d195653381cf2caa75a41a92d93b255a9d6ea29fd353aa` |
| New index digest | `sha256:ecafd34249b5c248f3cb6ebe339584ee6448b36fad3f0a827ae5e8efbae6afda` |
| Upstream rebuild | `2026-07-07T17:43:40Z` (`docker-library/postgres` commit `4f9ced003ba58a854656ba150d146243d27ae3ac`) |
| libcurl before | `8.20.0-r1` — **12 HIGH** Trivy findings |
| libcurl after | **0** alpine-layer HIGH/CRITICAL findings |
| FixedVersion target | `8.21.0-r0` (scan-verified) |
| Residual on new pin | `usr/local/bin/gosu` — 14 HIGH/CRITICAL (upstream-blocked, out of scope) |

**Verdict:** `FIX_VERIFIED_DIGEST_REFRESH` — narrow digest PR authorized.

---

## Probe method

1. `docker buildx imagetools inspect postgres:18.4-alpine` — detected new index digest vs repo pin.
2. `trivy image --severity HIGH,CRITICAL` on old and new digests (local Trivy `0.72.0`, DB `2026-07-06`).
3. Repo pin convention: **OCI index digest** (same pattern as prior postgres digest-only PRs).

---

## Trivy evidence

### Old pin (`1b1689b…`)

| Target | HIGH | CRITICAL |
|--------|------|----------|
| alpine OS (`libcurl` cluster) | 12 | 0 |
| `usr/local/bin/gosu` | 13 | 1 |

libcurl CVEs (all `FixedVersion: 8.21.0-r0`): CVE-2026-11352, CVE-2026-11586, CVE-2026-12064, CVE-2026-8286, CVE-2026-8925, CVE-2026-8927, CVE-2026-8932, CVE-2026-9079, CVE-2026-9080, CVE-2026-9545, CVE-2026-9546, CVE-2026-9547.

### New pin (`ecafd342…`)

| Target | HIGH | CRITICAL |
|--------|------|----------|
| alpine OS | **0** | **0** |
| `usr/local/bin/gosu` | 13 | 1 |

---

## Files changed

| File | Change |
|------|--------|
| `infrastructure/compose/base.yml` | Postgres digest refresh |
| `infrastructure/compose/compose.blue.yml` | Postgres digest refresh |
| `.github/workflows/security-scan.yml` | `trivy-scan-base` + `scan-base-images` matrix sync |

---

## Non-goals

- No Grafana / Prometheus / Redis image changes.
- No `cdb_*` service image changes.
- No alert dismissals or SARIF suppression.
- No gosu upstream-blocked remediation (tracked under #2933).
- No runtime `docker compose up` or DB migration in this slice.

---

## Expected GitHub Code Scanning impact

After merge + next `security-scan.yml` run, **12** `library/postgres` libcurl HIGH alerts should clear on scan-verified digest. gosu residuals remain open until upstream rebuild.

---

## References

- Read-only triage: `knowledge/logs/sessions/2026-07-08-security-retriage-readonly-report.md`
- Prior gosu residual doc: `docs/evidence/security/CDB_SECURITY_RESIDUALS_3694-3695_2026-07-03.md`
- Runbook: `docs/security/TRIAGE_RUNBOOK.md`
- Control note: `docs/runbooks/CONTROL_REGISTER.md` (PR #3921 workflow-control entry; reconcile #3922)
