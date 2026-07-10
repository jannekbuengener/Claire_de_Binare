# #2513 Residual Cluster Index — 2026-07-10 Update

**Parent:** [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513)  
**Purpose:** Canonical cluster index for upstream-blocked Trivy residuals (issue-body supplement via comment + repo SSOT)  
**LR:** NO-GO

---

## Active clusters (6)

| # | Issue | Primary CVE(s) | Base / scope | Latest compression |
|---|-------|----------------|--------------|-------------------|
| 1 | [#2932](https://github.com/jannekbuengener/Claire_de_Binare/issues/2932) | perl-base family + **CVE-2026-53615** | `python:3.14-slim-trixie` × 8 | #3945–#3952 → closed 2026-07-10 |
| 2 | [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933) | Grafana/Prometheus/gosu/plugins | upstream images | #3764, #3694–#3695 prior |
| 3 | [#3705](https://github.com/jannekbuengener/Claire_de_Binare/issues/3705) | CVE-2026-11824 / libsqlite3 | 8× Trixie | #3619–#3625 prior |
| 4 | [#3802](https://github.com/jannekbuengener/Claire_de_Binare/issues/3802) | CVE-2026-41992 / gzip | 8× Trixie | #3756–#3763 prior |
| 5 | [#3803](https://github.com/jannekbuengener/Claire_de_Binare/issues/3803) | CVE-2026-54369 / libacl1 | all Trixie | #3953–#3954 → closed 2026-07-10 |
| 6 | [#3936](https://github.com/jannekbuengener/Claire_de_Binare/issues/3936) | CVE-2026-12064 / libcurl4t64 | 7× Trixie cdb | #3926–#3932 prior |

**Note:** Postgres alpine libcurl (same CVE id, different image) cleared by digest refresh PR #3921; Trixie cdb libcurl remains under #3936.

---

## Governance (unchanged)

- All clusters: **UPSTREAM_BLOCKED** on current pins.
- Code Scanning alerts: **OPEN** until scan-verified fix.
- PR [#3755](https://github.com/jannekbuengener/Claire_de_Binare/pull/3755): **HOLD** — not a security remediation.

Evidence: [`CDB_SECURITY_ALERT_COMPRESSION_3945-3954_2026-07-10.md`](CDB_SECURITY_ALERT_COMPRESSION_3945-3954_2026-07-10.md)
