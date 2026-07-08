# POSTGRES_ALPINE_REBUILD_PROBE — libcurl digest refresh

**Date:** 2026-07-08 (UTC+2)  
**Status:** DONE_MERGED  
**Merge:** PR [#3921](https://github.com/jannekbuengener/Claire_de_Binare/pull/3921) @ `384de27b`  
**LR:** NO-GO (unchanged)

---

## Brain Evidence

| Feld | Wert |
|------|------|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| context_brain_used | false |
| context_available | false |
| repo_fallback_used | true |
| repo_fallback_reason | insufficient_evidence |
| context_tool_status | available |
| context_trust_level | none |
| records_found | none |
| tools_or_queries | `docker buildx imagetools inspect`, `trivy image`, `gh issue/pr view`, `cdb_context_briefing` |
| records_or_results | old pin 12 libcurl HIGH → new pin 0 alpine HIGH/CRITICAL |
| repo_crosscheck | compose base/blue, security-scan.yml |
| impact_on_plan | digest PR authorized and merged |
| limitations | GitHub alert count delta pending security-scan workflow |

---

## Digest Probe

| | Old | New |
|---|-----|-----|
| Tag | `postgres:18.4-alpine` | same |
| Index digest | `1b1689b…` | `ecafd342…` |
| Built | 2026-06-16 | 2026-07-07 |
| libcurl version | `8.20.0-r1` | `8.21.0-r0` (patched) |

---

## Trivy (local 0.72.0)

- Old: 12 libcurl HIGH + 14 gosu HIGH/CRITICAL
- New: 0 alpine HIGH/CRITICAL + 14 gosu HIGH/CRITICAL (upstream-blocked)

---

## Delivered

- Digest refresh: `base.yml`, `compose.blue.yml`, `security-scan.yml`
- Evidence: `docs/evidence/security/CDB_SECURITY_POSTGRES_ALPINE_LIBCURL_REBUILD_2026-07-08.md`
- Issue comments: #2933, #2513

---

## Boundaries

- No alert dismissals
- No runtime / compose up
- #3755 untouched
- gosu residual open under #2933
