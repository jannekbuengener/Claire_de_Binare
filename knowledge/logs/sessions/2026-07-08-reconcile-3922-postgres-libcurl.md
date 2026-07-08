# #3922 — Control docs reconcile after PR #3921

**Date:** 2026-07-08 (UTC+2)  
**Status:** DONE_MERGED_CLOSED (pending merge)  
**Source PR:** [#3921](https://github.com/jannekbuengener/Claire_de_Binare/pull/3921) @ `384de27b`  
**LR:** NO-GO (unchanged)

---

## Drift addressed

| Artifact | Change |
|----------|--------|
| `docs/runbooks/CONTROL_REGISTER.md` | Workflow-control note for PR #3921 postgres digest refresh |
| `docs/evidence/security/CDB_SECURITY_RESIDUALS_3694-3695_2026-07-03.md` | Superseded pin cross-ref (gosu cluster unchanged) |
| `docs/evidence/security/CDB_SECURITY_POSTGRES_ALPINE_LIBCURL_REBUILD_2026-07-08.md` | CONTROL_REGISTER cross-ref |
| `CURRENT_STATUS.md` | #3922 + #3921 ledger entries |
| `knowledge/logs/sessions/2026-07-08-postgres-alpine-rebuild-probe.md` | Session evidence from probe slice |

---

## Boundaries

- Docs/ledger only — no workflow, image, or runtime changes
- #3755 HOLD unchanged
- GitHub alert delta still pending `security-scan.yml` run
